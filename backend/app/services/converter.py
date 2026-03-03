"""
PDF to DOCX conversion service.
Uses pdf2docx library which preserves text, fonts, tables, and basic layout.
"""
import os
import uuid
import asyncio
import logging
import shutil
import subprocess
import sys
import importlib.util
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from app.models.models import ConversionTask, TaskStatus
from app.core.config import get_settings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
settings = get_settings()
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
    Perform the actual PDF→DOCX conversion using pdf2docx.
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
        pages_to_check, text_pages, image_pages, total_chars
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
                "+".join(requested), "+".join(missing), "+".join(available)
            )
        return "+".join(available)

    if "eng" in installed:
        logger.warning(
            "OCR language fallback: requested=%s, available in Tesseract=%s, using=eng",
            "+".join(requested), "+".join(sorted(installed))
        )
        return "eng"

    raise RuntimeError(
        "OCR language data is missing. Requested: "
        f"{'+'.join(requested)}. Installed: {', '.join(sorted(installed)) or 'none'}. "
        "Install language data or set OCR_LANG to an installed language."
    )


def _run_ocrmypdf(
    input_pdf_path: Path,
    output_pdf_path: Path,
    sidecar_path: Optional[Path] = None,
) -> None:
    command = _resolve_ocrmypdf_command()
    if not command:
        raise RuntimeError(
            "Scanned PDF detected but OCR is not configured. "
            "Install ocrmypdf + Tesseract and retry."
        )

    extra_path_dirs = _collect_windows_ocr_tool_dirs()
    env = _build_ocr_env(extra_path_dirs)
    ocr_lang = _resolve_ocr_lang(extra_path_dirs)

    cmd = [
        *command,
        "--force-ocr",
        "--rotate-pages",
        "--deskew",
        "--optimize",
        "0",
        "-l",
        ocr_lang,
        str(input_pdf_path),
        str(output_pdf_path),
    ]
    if sidecar_path is not None:
        cmd.extend(["--sidecar", str(sidecar_path)])
    process = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if process.returncode != 0:
        details = (process.stderr or process.stdout or "unknown OCR error").strip()
        raise RuntimeError(f"OCR step failed: {details}")


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
        if not page:
            continue

        if document.paragraphs:
            document.add_page_break()

        for paragraph in (chunk.strip() for chunk in page.split("\n\n")):
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
            if not page_text:
                continue

            total_chars += len(page_text)
            if document.paragraphs:
                document.add_page_break()

            for paragraph in (chunk.strip() for chunk in page_text.split("\n\n")):
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
            "Scanned PDF detected. OCR is disabled "
            "(set ENABLE_SCANNED_OCR=true)."
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
            "OCR completed, but no text was extracted. "
            "Check image quality (blur/low DPI), language packs, and OCR_LANG."
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


async def convert_pdf_to_docx(
    task_uuid: str,
    pdf_bytes: bytes,
    original_filename: str,
    db: Session,
) -> None:
    """
    Save the uploaded PDF, convert it to DOCX asynchronously,
    and update the task record in the database.
    """
    upload_dir, output_dir = _ensure_dirs()

    # Build file paths
    pdf_filename = f"{task_uuid}.pdf"
    docx_filename = f"{task_uuid}.docx"
    pdf_path = upload_dir / pdf_filename
    docx_path = output_dir / docx_filename

    # Persist the uploaded PDF
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    # Fetch the task row and mark as PROCESSING
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
        # Run blocking conversion in a thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _convert_with_pipeline, pdf_path, docx_path, task_uuid)

        # Success — store output filename and mark DONE
        task.status = TaskStatus.DONE
        task.output_filename = docx_filename
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
        # Clean up the temporary PDF upload
        try:
            os.remove(pdf_path)
        except OSError:
            pass


def create_task_record(
    db: Session,
    user_id: int,
    original_filename: str,
) -> str:
    """Create a new ConversionTask row and return its UUID."""
    from app.models.models import ConversionTask

    task_uuid = str(uuid.uuid4())
    import uuid as _uuid
    uid = _uuid.uuid4()
    task = ConversionTask(
        task_uuid=uid,
        user_id=user_id,
        original_filename=original_filename,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return str(task.task_uuid)  # always return str, not uuid.UUID
