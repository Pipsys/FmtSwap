"""
Document conversion service.
Supported conversion types:
- pdf_to_docx
- pdf_to_jpg (ZIP archive with JPEG pages)
- jpg_to_pdf
- word_to_pdf
"""
import asyncio
import importlib.util
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import ConversionTask, TaskStatus

logger = logging.getLogger(__name__)
settings = get_settings()

PDF_TO_DOCX = "pdf_to_docx"
PDF_TO_JPG = "pdf_to_jpg"
JPG_TO_PDF = "jpg_to_pdf"
WORD_TO_PDF = "word_to_pdf"

SCANNED = "scanned"
TEXT = "text"


def _ensure_pymupdf_compat() -> None:
    """
    pdf2docx 0.5.x expects Rect.get_area(), which is missing in newer PyMuPDF.
    Add a compatibility shim at runtime.
    """
    try:
        import fitz  # PyMuPDF
    except Exception:
        return

    def _area(rect) -> float:
        return abs((rect.x1 - rect.x0) * (rect.y1 - rect.y0))

    if hasattr(fitz, "Rect") and not hasattr(fitz.Rect, "get_area"):
        fitz.Rect.get_area = _area
    if hasattr(fitz, "IRect") and not hasattr(fitz.IRect, "get_area"):
        fitz.IRect.get_area = _area


def _ensure_dirs() -> tuple[Path, Path]:
    """Ensure upload and output directories exist. Returns (upload_dir, output_dir)."""
    upload_dir = Path(settings.UPLOAD_DIR)
    output_dir = Path(settings.OUTPUT_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir, output_dir


def _do_convert(pdf_path: str, docx_path: str) -> None:
    """
    Perform the actual PDF->DOCX conversion using pdf2docx.
    This is a blocking call, run in a thread pool.
    """
    _ensure_pymupdf_compat()
    from pdf2docx import Converter

    cv = Converter(pdf_path)
    try:
        # parse() extracts text, images, tables, fonts and writes to DOCX
        cv.convert(docx_path, start=0, end=None)
    finally:
        cv.close()


def _detect_pdf_kind(pdf_path: Path) -> str:
    """
    Heuristic PDF detector:
    - text PDF: at least one sampled page has enough extractable text
    - scanned PDF: mostly image pages without selectable text
    """
    _ensure_pymupdf_compat()
    import fitz  # PyMuPDF

    sample_pages = max(1, settings.PDF_DETECT_SAMPLE_PAGES)
    min_chars_per_page = max(1, settings.PDF_TEXT_MIN_CHARS_PER_PAGE)
    min_text_pages = max(1, settings.PDF_TEXT_MIN_PAGES)

    with fitz.open(str(pdf_path)) as doc:
        if doc.page_count == 0:
            return TEXT

        pages_to_check = min(doc.page_count, sample_pages)
        text_pages = 0
        image_pages = 0
        total_chars = 0

        for page_index in range(pages_to_check):
            page = doc.load_page(page_index)
            page_text = page.get_text("text").strip()
            char_count = len(page_text)
            total_chars += char_count

            if char_count >= min_chars_per_page:
                text_pages += 1
            if page.get_images(full=True):
                image_pages += 1

    logger.info(
        "PDF detection: pages=%s text_pages=%s image_pages=%s total_chars=%s",
        pages_to_check,
        text_pages,
        image_pages,
        total_chars,
    )

    if text_pages >= min_text_pages:
        return TEXT
    if total_chars >= min_chars_per_page * min_text_pages:
        return TEXT
    if image_pages >= max(1, pages_to_check // 2):
        return SCANNED
    return SCANNED


def _resolve_ocrmypdf_command() -> Optional[list[str]]:
    if shutil.which("ocrmypdf"):
        return ["ocrmypdf"]
    if importlib.util.find_spec("ocrmypdf") is not None:
        return [sys.executable, "-m", "ocrmypdf"]
    return None


def _collect_windows_ocr_tool_dirs() -> list[str]:
    """
    Try common Windows install locations for OCR tools when PATH is not configured.
    """
    if os.name != "nt":
        return []

    dirs: list[str] = []

    tesseract_dir = Path(r"C:\Program Files\Tesseract-OCR")
    if (tesseract_dir / "tesseract.exe").exists():
        dirs.append(str(tesseract_dir))

    gs_root = Path(r"C:\Program Files\gs")
    if gs_root.exists():
        for version_dir in sorted((p for p in gs_root.iterdir() if p.is_dir()), reverse=True):
            gs_bin = version_dir / "bin"
            if (gs_bin / "gswin64c.exe").exists() or (gs_bin / "gswin32c.exe").exists():
                dirs.append(str(gs_bin))
                break

    return dirs


def _build_ocr_env(extra_path_dirs: list[str]) -> dict[str, str]:
    env = os.environ.copy()
    if extra_path_dirs:
        env["PATH"] = os.pathsep.join(extra_path_dirs + [env.get("PATH", "")])
    if settings.TESSDATA_PREFIX:
        env["TESSDATA_PREFIX"] = settings.TESSDATA_PREFIX
    return env


def _read_installed_tesseract_languages(extra_path_dirs: list[str]) -> set[str]:
    env = _build_ocr_env(extra_path_dirs)

    tesseract_cmd = shutil.which("tesseract", path=env.get("PATH"))
    if not tesseract_cmd:
        return set()

    process = subprocess.run(
        [tesseract_cmd, "--list-langs"],
        capture_output=True,
        text=True,
        env=env,
    )
    if process.returncode != 0:
        return set()

    langs: set[str] = set()
    for line in process.stdout.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("list of available languages"):
            continue
        langs.add(line)
    return langs


def _resolve_ocr_lang(extra_path_dirs: list[str]) -> str:
    requested = [x.strip() for x in settings.OCR_LANG.split("+") if x.strip()]
    if not requested:
        requested = ["eng"]

    installed = _read_installed_tesseract_languages(extra_path_dirs)
    if not installed:
        return "+".join(requested)

    available = [lang for lang in requested if lang in installed]
    missing = [lang for lang in requested if lang not in installed]

    if available:
        if missing:
            logger.warning(
                "OCR language fallback: requested=%s, missing=%s, using=%s",
                "+".join(requested),
                "+".join(missing),
                "+".join(available),
            )
        return "+".join(available)

    if "eng" in installed:
        logger.warning(
            "OCR language fallback: requested=%s, available in Tesseract=%s, using=eng",
            "+".join(requested),
            "+".join(sorted(installed)),
        )
        return "eng"

    raise RuntimeError(
        "Отсутствуют языковые данные OCR. Запрошено: "
        f"{'+'.join(requested)}. Установлено: {', '.join(sorted(installed)) or 'нет'}. "
        "Установите языковые пакеты или задайте OCR_LANG с доступным языком."
    )


def _normalize_ocr_text(text: str) -> str:
    """
    Normalize OCR output to reduce common spacing artifacts:
    - remove hyphenation on line breaks
    - convert single line breaks into spaces
    - keep paragraph breaks
    - insert spaces between glued words in common patterns
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    # Joined words due to line wraps: "сло-\nво" -> "слово"
    normalized = re.sub(r"(?<=\w)-\n(?=\w)", "", normalized)

    # Keep empty line as paragraph delimiter, but join single line wraps with spaces.
    normalized = re.sub(r"(?<!\n)\n(?!\n)", " ", normalized)

    # Insert space in common glued boundaries.
    normalized = re.sub(r"(?<=[a-zа-яё])(?=[A-ZА-ЯЁ])", " ", normalized)
    normalized = re.sub(r"(?<=[A-Za-zА-Яа-яЁё])(?=\d)", " ", normalized)
    normalized = re.sub(r"(?<=\d)(?=[A-Za-zА-Яа-яЁё])", " ", normalized)

    # Normalize whitespace.
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r" *\n{2,} *", "\n\n", normalized)

    return normalized.strip()


def _run_ocrmypdf(
    input_pdf_path: Path,
    output_pdf_path: Path,
    sidecar_path: Optional[Path] = None,
) -> None:
    command = _resolve_ocrmypdf_command()
    if not command:
        raise RuntimeError(
            "Обнаружен сканированный PDF, но OCR не настроен. "
            "Установите ocrmypdf и Tesseract, затем повторите попытку."
        )

    extra_path_dirs = _collect_windows_ocr_tool_dirs()
    env = _build_ocr_env(extra_path_dirs)
    ocr_lang = _resolve_ocr_lang(extra_path_dirs)

    cmd = [
        *command,
        "--force-ocr",
        "--rotate-pages",
        "--deskew",
        "--pdf-renderer",
        "auto",
        "--optimize",
        "0",
        "--tesseract-pagesegmode",
        "6",
        "-l",
        ocr_lang,
        str(input_pdf_path),
        str(output_pdf_path),
    ]
    if sidecar_path is not None:
        cmd.extend(["--sidecar", str(sidecar_path)])
    process = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if process.returncode != 0:
        details = (process.stderr or process.stdout or "неизвестная ошибка OCR").strip()
        raise RuntimeError(f"Ошибка OCR: {details}")


def _build_docx_from_sidecar_text(sidecar_path: Path, docx_path: Path) -> int:
    """
    Build DOCX from OCR sidecar text. This is the most reliable OCR output source.
    """
    if not sidecar_path.exists():
        return 0

    raw_text = sidecar_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not raw_text:
        return 0

    from docx import Document

    document = Document()
    total_chars = 0

    pages = [page.strip() for page in raw_text.split("\f")]
    for page in pages:
        normalized_page = _normalize_ocr_text(page)
        if not normalized_page:
            continue

        if document.paragraphs:
            document.add_page_break()

        for paragraph in (chunk.strip() for chunk in normalized_page.split("\n\n")):
            if paragraph:
                document.add_paragraph(paragraph)
                total_chars += len(paragraph)

    if total_chars == 0:
        return 0

    document.save(str(docx_path))
    return total_chars


def _build_docx_from_pdf_text(pdf_path: Path, docx_path: Path) -> int:
    """
    Build text-first DOCX from PDF text layer.
    Used for scanned PDFs after OCR, because pdf2docx may still keep image-only pages.
    """
    _ensure_pymupdf_compat()
    import fitz  # PyMuPDF
    from docx import Document

    document = Document()
    total_chars = 0

    with fitz.open(str(pdf_path)) as pdf_doc:
        for page_index in range(pdf_doc.page_count):
            page_text = pdf_doc.load_page(page_index).get_text("text").strip()
            normalized_page = _normalize_ocr_text(page_text)
            if not normalized_page:
                continue

            total_chars += len(normalized_page)
            if document.paragraphs:
                document.add_page_break()

            for paragraph in (chunk.strip() for chunk in normalized_page.split("\n\n")):
                if paragraph:
                    document.add_paragraph(paragraph)

    if total_chars == 0:
        return 0

    document.save(str(docx_path))
    return total_chars


def _convert_with_pipeline(pdf_path: Path, docx_path: Path, task_uuid: str) -> None:
    pdf_kind = _detect_pdf_kind(pdf_path)

    if pdf_kind == TEXT:
        logger.info("Task %s: detected text PDF, using direct pdf2docx", task_uuid)
        _do_convert(str(pdf_path), str(docx_path))
        return

    if not settings.ENABLE_SCANNED_OCR:
        raise RuntimeError(
            "Обнаружен сканированный PDF, но OCR отключён "
            "(установите ENABLE_SCANNED_OCR=true)."
        )

    logger.info("Task %s: detected scanned PDF, running OCR pipeline", task_uuid)
    ocr_pdf_path = pdf_path.with_name(f"{pdf_path.stem}.ocr.pdf")
    ocr_sidecar_path = pdf_path.with_name(f"{pdf_path.stem}.ocr.txt")
    try:
        _run_ocrmypdf(pdf_path, ocr_pdf_path, sidecar_path=ocr_sidecar_path)

        sidecar_chars = _build_docx_from_sidecar_text(ocr_sidecar_path, docx_path)
        if sidecar_chars > 0:
            logger.info(
                "Task %s: OCR sidecar text extracted (%s chars)",
                task_uuid,
                sidecar_chars,
            )
            return

        pdf_chars = _build_docx_from_pdf_text(ocr_pdf_path, docx_path)
        if pdf_chars > 0:
            logger.info(
                "Task %s: OCR PDF text layer extracted (%s chars)",
                task_uuid,
                pdf_chars,
            )
            return

        raise RuntimeError(
            "OCR завершён, но текст не извлечён. "
            "Проверьте качество скана (размытие/DPI), языковые пакеты и OCR_LANG."
        )
    finally:
        try:
            os.remove(ocr_pdf_path)
        except OSError:
            pass
        try:
            os.remove(ocr_sidecar_path)
        except OSError:
            pass


def _convert_pdf_to_jpg_archive(pdf_path: Path, zip_path: Path, task_uuid: str) -> None:
    _ensure_pymupdf_compat()
    import fitz

    logger.info("Task %s: converting PDF to JPG archive", task_uuid)

    with fitz.open(str(pdf_path)) as pdf_doc:
        if pdf_doc.page_count == 0:
            raise RuntimeError("PDF не содержит страниц для конвертации")

        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
            for page_index in range(pdf_doc.page_count):
                page = pdf_doc.load_page(page_index)
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
                jpg_name = f"page_{page_index + 1:03d}.jpg"
                jpg_bytes = pix.tobytes("jpg")
                archive.writestr(jpg_name, jpg_bytes)


def _convert_jpg_to_pdf(jpg_path: Path, pdf_path: Path, task_uuid: str) -> None:
    _ensure_pymupdf_compat()
    import fitz

    logger.info("Task %s: converting JPG to PDF", task_uuid)

    image_doc = fitz.open(str(jpg_path))
    try:
        pdf_bytes = image_doc.convert_to_pdf()
    finally:
        image_doc.close()

    pdf_doc = fitz.open("pdf", pdf_bytes)
    try:
        pdf_doc.save(str(pdf_path))
    finally:
        pdf_doc.close()


def _convert_jpg_list_to_pdf(jpg_paths: list[Path], pdf_path: Path, task_uuid: str) -> None:
    _ensure_pymupdf_compat()
    import fitz

    logger.info("Task %s: converting %s JPG files to one PDF", task_uuid, len(jpg_paths))

    if not jpg_paths:
        raise RuntimeError("Не передано ни одного JPG-файла для конвертации")

    merged_pdf = fitz.open()
    try:
        for jpg_path in jpg_paths:
            image_doc = fitz.open(str(jpg_path))
            try:
                pdf_bytes = image_doc.convert_to_pdf()
            finally:
                image_doc.close()

            image_pdf = fitz.open("pdf", pdf_bytes)
            try:
                merged_pdf.insert_pdf(image_pdf)
            finally:
                image_pdf.close()

        if merged_pdf.page_count == 0:
            raise RuntimeError("Не удалось собрать PDF из изображений")

        merged_pdf.save(str(pdf_path))
    finally:
        merged_pdf.close()


def _resolve_unicode_font_file() -> Optional[str]:
    """
    Try to find a system font that supports Cyrillic/Unicode text for fallback rendering.
    """
    candidates: list[Path] = []

    if os.name == "nt":
        win_fonts = Path(r"C:\Windows\Fonts")
        candidates.extend(
            [
                win_fonts / "arial.ttf",
                win_fonts / "calibri.ttf",
                win_fonts / "times.ttf",
                win_fonts / "tahoma.ttf",
                win_fonts / "segoeui.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
                Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
            ]
        )

    for font_path in candidates:
        if font_path.exists():
            return str(font_path)

    return None


def _resolve_soffice_command() -> Optional[str]:
    soffice = shutil.which("soffice")
    if soffice:
        return soffice

    if os.name == "nt":
        candidates = [
            Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
            Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

    return None


def _convert_word_with_libreoffice(word_path: Path, pdf_path: Path) -> None:
    soffice_cmd = _resolve_soffice_command()
    if not soffice_cmd:
        raise RuntimeError("LibreOffice (soffice) не найден в системе")

    with tempfile.TemporaryDirectory(prefix="fmtswap_soffice_") as tmp_dir:
        cmd = [
            soffice_cmd,
            "--headless",
            "--nologo",
            "--nolockcheck",
            "--nodefault",
            "--nofirststartwizard",
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            tmp_dir,
            str(word_path),
        ]
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        if process.returncode != 0:
            details = (process.stderr or process.stdout or "ошибка LibreOffice").strip()
            raise RuntimeError(details)

        converted_path = Path(tmp_dir) / f"{word_path.stem}.pdf"
        if not converted_path.exists():
            generated = sorted(Path(tmp_dir).glob("*.pdf"))
            if not generated:
                raise RuntimeError("LibreOffice не сгенерировал PDF-файл")
            converted_path = generated[0]

        if pdf_path.exists():
            pdf_path.unlink()
        shutil.move(str(converted_path), str(pdf_path))


def _convert_word_with_docx2pdf(word_path: Path, pdf_path: Path) -> None:
    if importlib.util.find_spec("docx2pdf") is None:
        raise RuntimeError("Модуль docx2pdf не установлен")

    from docx2pdf import convert as docx2pdf_convert

    docx2pdf_convert(str(word_path), str(pdf_path))
    if not pdf_path.exists():
        raise RuntimeError("docx2pdf не сгенерировал PDF-файл")


def _convert_docx_to_pdf_fallback(docx_path: Path, pdf_path: Path, task_uuid: str) -> None:
    _ensure_pymupdf_compat()
    import fitz
    from docx import Document

    logger.info("Task %s: converting WORD to PDF via text fallback", task_uuid)

    doc = Document(str(docx_path))
    paragraphs = [p.text.strip() for p in doc.paragraphs]

    if not any(paragraphs):
        raise RuntimeError("Документ Word не содержит текста для конвертации")

    pdf = fitz.open()
    margin = 54
    font_size = 11
    line_height = 16
    max_chars = 95
    font_file = _resolve_unicode_font_file()

    if font_file:
        logger.info("Task %s: WORD fallback uses system font %s", task_uuid, font_file)

    page = pdf.new_page()
    y = margin

    def ensure_space(lines_count: int) -> None:
        nonlocal page, y
        required_height = lines_count * line_height
        if y + required_height > page.rect.height - margin:
            page = pdf.new_page()
            y = margin

    for paragraph in paragraphs:
        wrapped_lines = textwrap.wrap(paragraph, width=max_chars) if paragraph else [""]
        ensure_space(len(wrapped_lines) + 1)

        for line in wrapped_lines:
            insert_kwargs = {
                "fontsize": font_size,
                "color": (0, 0, 0),
            }
            if font_file:
                insert_kwargs.update({"fontname": "fmtswap_unicode", "fontfile": font_file})
            else:
                # Fallback when no Unicode TTF found.
                insert_kwargs.update({"fontname": "helv", "encoding": fitz.TEXT_ENCODING_CYRILLIC})

            page.insert_text((margin, y), line, **insert_kwargs)
            y += line_height

        y += line_height // 2

    pdf.save(str(pdf_path))
    pdf.close()


def _convert_word_to_pdf(word_path: Path, pdf_path: Path, task_uuid: str) -> None:
    logger.info("Task %s: converting WORD to PDF", task_uuid)
    ext = word_path.suffix.lower()
    errors: list[str] = []

    try:
        _convert_word_with_libreoffice(word_path, pdf_path)
        return
    except Exception as exc:
        errors.append(f"LibreOffice: {exc}")

    if ext in {".docx", ".docm", ".dotx", ".dotm"}:
        try:
            _convert_word_with_docx2pdf(word_path, pdf_path)
            return
        except Exception as exc:
            errors.append(f"docx2pdf: {exc}")

        try:
            _convert_docx_to_pdf_fallback(word_path, pdf_path, task_uuid)
            return
        except Exception as exc:
            errors.append(f"fallback: {exc}")

    raise RuntimeError(
        "Не удалось конвертировать Word в PDF. "
        "Рекомендуется установить LibreOffice для качественной конвертации. "
        f"Подробности: {' | '.join(errors)}"
    )


def get_supported_conversion_types() -> set[str]:
    return {
        PDF_TO_DOCX,
        PDF_TO_JPG,
        JPG_TO_PDF,
        WORD_TO_PDF,
    }


def get_input_extensions(conversion_type: str) -> tuple[str, ...]:
    mapping = {
        PDF_TO_DOCX: (".pdf",),
        PDF_TO_JPG: (".pdf",),
        JPG_TO_PDF: (".jpg", ".jpeg", ".jfif"),
        WORD_TO_PDF: (".docx", ".doc", ".docm"),
    }
    return mapping.get(conversion_type, tuple())


def get_output_extension(conversion_type: str) -> str:
    mapping = {
        PDF_TO_DOCX: ".docx",
        PDF_TO_JPG: ".zip",
        JPG_TO_PDF: ".pdf",
        WORD_TO_PDF: ".pdf",
    }
    return mapping.get(conversion_type, ".bin")


def get_output_media_type(conversion_type: str) -> str:
    mapping = {
        PDF_TO_DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        PDF_TO_JPG: "application/zip",
        JPG_TO_PDF: "application/pdf",
        WORD_TO_PDF: "application/pdf",
    }
    return mapping.get(conversion_type, "application/octet-stream")


def _resolve_runner(conversion_type: str):
    mapping = {
        PDF_TO_DOCX: _convert_with_pipeline,
        PDF_TO_JPG: _convert_pdf_to_jpg_archive,
        JPG_TO_PDF: _convert_jpg_to_pdf,
        WORD_TO_PDF: _convert_word_to_pdf,
    }
    return mapping.get(conversion_type)


async def convert_file(
    task_uuid: str,
    source_bytes: bytes,
    original_filename: str,
    conversion_type: str,
    db: Session,
) -> None:
    """
    Save uploaded file, run conversion asynchronously, and update DB status.
    """
    upload_dir, output_dir = _ensure_dirs()

    output_ext = get_output_extension(conversion_type)
    input_ext = Path(original_filename).suffix.lower() or ".bin"

    input_filename = f"{task_uuid}{input_ext}"
    output_filename = f"{task_uuid}{output_ext}"
    input_path = upload_dir / input_filename
    output_path = output_dir / output_filename

    with open(input_path, "wb") as f:
        f.write(source_bytes)

    import uuid as _uuid

    try:
        uid = _uuid.UUID(task_uuid)
    except (ValueError, AttributeError):
        uid = task_uuid

    task = db.query(ConversionTask).filter(ConversionTask.task_uuid == uid).first()
    if not task:
        logger.error("Task %s not found in DB", task_uuid)
        return

    task.status = TaskStatus.PROCESSING
    task.updated_at = datetime.now(timezone.utc)
    db.commit()

    try:
        runner = _resolve_runner(conversion_type)
        if runner is None:
            raise RuntimeError(f"Неподдерживаемый тип конвертации: {conversion_type}")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, runner, input_path, output_path, task_uuid)

        task.status = TaskStatus.DONE
        task.output_filename = output_filename
        task.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Task %s completed successfully", task_uuid)

    except Exception as exc:
        logger.exception("Conversion failed for task %s: %s", task_uuid, exc)
        task.status = TaskStatus.FAILED
        task.error_message = str(exc)
        task.updated_at = datetime.now(timezone.utc)
        db.commit()

    finally:
        try:
            os.remove(input_path)
        except OSError:
            pass


async def convert_images_to_pdf(
    task_uuid: str,
    images: list[tuple[str, bytes]],
    db: Session,
) -> None:
    """
    Convert multiple JPG/JPEG images into a single multi-page PDF.
    """
    upload_dir, output_dir = _ensure_dirs()

    output_filename = f"{task_uuid}.pdf"
    output_path = output_dir / output_filename

    image_paths: list[Path] = []
    for idx, (filename, payload) in enumerate(images, start=1):
        ext = Path(filename).suffix.lower() or ".jpg"
        image_path = upload_dir / f"{task_uuid}_{idx:03d}{ext}"
        with open(image_path, "wb") as f:
            f.write(payload)
        image_paths.append(image_path)

    import uuid as _uuid

    try:
        uid = _uuid.UUID(task_uuid)
    except (ValueError, AttributeError):
        uid = task_uuid

    task = db.query(ConversionTask).filter(ConversionTask.task_uuid == uid).first()
    if not task:
        logger.error("Task %s not found in DB", task_uuid)
        return

    task.status = TaskStatus.PROCESSING
    task.updated_at = datetime.now(timezone.utc)
    db.commit()

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _convert_jpg_list_to_pdf, image_paths, output_path, task_uuid)

        task.status = TaskStatus.DONE
        task.output_filename = output_filename
        task.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Task %s completed successfully", task_uuid)

    except Exception as exc:
        logger.exception("Multi-image conversion failed for task %s: %s", task_uuid, exc)
        task.status = TaskStatus.FAILED
        task.error_message = str(exc)
        task.updated_at = datetime.now(timezone.utc)
        db.commit()

    finally:
        for image_path in image_paths:
            try:
                os.remove(image_path)
            except OSError:
                pass


def create_task_record(
    db: Session,
    user_id: Optional[int],
    original_filename: str,
    conversion_type: str,
) -> str:
    """Create a new ConversionTask row and return its UUID."""
    task = ConversionTask(
        task_uuid=uuid.uuid4(),
        user_id=user_id,
        original_filename=original_filename,
        conversion_type=conversion_type,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return str(task.task_uuid)

