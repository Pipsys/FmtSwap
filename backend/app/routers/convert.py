"""
Conversion endpoints.
task_uuid comes from DB as uuid.UUID -> cast to str everywhere via str(task.task_uuid).
"""
import logging
import uuid as _uuid
from pathlib import Path
from typing import Optional, List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user_id, get_optional_user_id
from app.models.models import ConversionTask, TaskStatus
from app.schemas.schemas import ConvertResponse, HistoryResponse, MessageResponse, TaskResponse
from app.services.converter import (
    convert_file,
    convert_files_batch,
    convert_images_to_pdf,
    create_task_record,
    get_input_extensions,
    get_supported_conversion_types,
)

router = APIRouter(tags=["convert"])
settings = get_settings()
logger = logging.getLogger(__name__)

MAX_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024
PDF_MAGIC = b"%PDF-"
JPEG_MAGIC = b"\xff\xd8\xff"
ZIP_MAGIC = b"PK\x03\x04"
OLE_DOC_MAGIC = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
GIF_MAGIC_87 = b"GIF87a"
GIF_MAGIC_89 = b"GIF89a"
PSD_MAGIC = b"8BPS"
POSTSCRIPT_MAGIC = b"%!PS-Adobe"
SEVEN_Z_MAGIC = b"7z\xbc\xaf\x27\x1c"
RAR_MAGIC_4 = b"Rar!\x1a\x07\x00"
RAR_MAGIC_5 = b"Rar!\x1a\x07\x01\x00"
MULTI_FILE_TYPES = {"jpg_to_pdf", "arch_zip_pack", "arch_7z_pack", "arch_rar_pack"}


def _is_pdf(data: bytes) -> bool:
    return data[:5] == PDF_MAGIC


def _is_jpeg(data: bytes) -> bool:
    return data[:3] == JPEG_MAGIC


def _is_docx(data: bytes) -> bool:
    # DOCX is a ZIP container.
    return data[:4] == ZIP_MAGIC


def _is_zip(data: bytes) -> bool:
    return data[:4] == ZIP_MAGIC


def _is_legacy_word_doc(data: bytes) -> bool:
    return data[:8] == OLE_DOC_MAGIC


def _is_png(data: bytes) -> bool:
    return data[:8] == PNG_MAGIC


def _is_gif(data: bytes) -> bool:
    return data[:6] in {GIF_MAGIC_87, GIF_MAGIC_89}


def _is_heic(data: bytes) -> bool:
    if len(data) < 12 or data[4:8] != b"ftyp":
        return False
    brand = data[8:12]
    return brand in {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1", b"heim", b"heis"}


def _is_svg(data: bytes) -> bool:
    snippet = data[:2048].decode("utf-8", errors="ignore").lower()
    return "<svg" in snippet


def _is_psd(data: bytes) -> bool:
    return data[:4] == PSD_MAGIC


def _is_ai_like(data: bytes) -> bool:
    return _is_pdf(data) or data[:10] == POSTSCRIPT_MAGIC


def _is_7z(data: bytes) -> bool:
    return data[:6] == SEVEN_Z_MAGIC


def _is_rar(data: bytes) -> bool:
    return data.startswith(RAR_MAGIC_4) or data.startswith(RAR_MAGIC_5)


def _is_extension_allowed(filename: str, expected_exts: tuple[str, ...]) -> bool:
    if not expected_exts or "*" in expected_exts:
        return True
    return any(filename.lower().endswith(ext) for ext in expected_exts)


def _validate_file_bytes(conversion_type: str, payload: bytes) -> None:
    if conversion_type in {"pdf_to_docx", "pdf_to_jpg"} and not _is_pdf(payload):
        raise HTTPException(400, "Файл не является корректным PDF")
    if conversion_type == "jpg_to_pdf" and not _is_jpeg(payload):
        raise HTTPException(400, "Файл не является корректным JPG")
    if conversion_type == "word_to_pdf" and not (_is_docx(payload) or _is_legacy_word_doc(payload)):
        raise HTTPException(400, "Файл не является корректным документом Word")
    if conversion_type in {"png_to_webp", "png_to_ico"} and not _is_png(payload):
        raise HTTPException(400, "Файл не является корректным PNG")
    if conversion_type == "heic_to_jpg" and not _is_heic(payload):
        raise HTTPException(400, "Файл не является корректным HEIC/HEIF")
    if conversion_type == "svg_to_png" and not _is_svg(payload):
        raise HTTPException(400, "Файл не является корректным SVG")
    if conversion_type == "gif_to_mp4" and not _is_gif(payload):
        raise HTTPException(400, "Файл не является корректным GIF")
    if conversion_type in {"psd_ai_to_png", "psd_ai_to_jpg"} and not (_is_psd(payload) or _is_ai_like(payload)):
        raise HTTPException(400, "Файл не является корректным PSD/AI")
    if conversion_type in {"arch_zip_unpack"} and not _is_zip(payload):
        raise HTTPException(400, "Файл не является корректным ZIP")
    if conversion_type in {"arch_7z_unpack"} and not _is_7z(payload):
        raise HTTPException(400, "Файл не является корректным 7Z")
    if conversion_type in {"arch_rar_unpack"} and not _is_rar(payload):
        raise HTTPException(400, "Файл не является корректным RAR")
    if conversion_type in {"comp_pdf"} and not _is_pdf(payload):
        raise HTTPException(400, "Файл не является корректным PDF")


def _build_download_name(task: ConversionTask) -> str:
    original_stem = Path(task.original_filename).stem
    output_ext = Path(task.output_filename or "").suffix.lower()

    if output_ext == ".zip":
        if task.conversion_type == "pdf_to_jpg":
            return f"{original_stem}_jpg.zip"
        return f"{original_stem}.zip"
    if output_ext:
        return f"{original_stem}{output_ext}"
    return task.output_filename or "result.bin"


def _build_media_type(task: ConversionTask) -> str:
    output_ext = Path(task.output_filename or "").suffix.lower()
    return {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".zip": "application/zip",
        ".7z": "application/x-7z-compressed",
        ".rar": "application/vnd.rar",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".avif": "image/avif",
        ".png": "image/png",
        ".ico": "image/x-icon",
        ".mp4": "video/mp4",
        ".mp3": "audio/mpeg",
        ".avi": "video/x-msvideo",
        ".mov": "video/quicktime",
    }.get(output_ext, "application/octet-stream")


def _scoped_task_query(db: Session, user_id: Optional[int]):
    query = db.query(ConversionTask)
    if user_id is None:
        return query.filter(ConversionTask.user_id.is_(None))
    return query.filter(or_(ConversionTask.user_id == user_id, ConversionTask.user_id.is_(None)))


@router.post("/convert", response_model=ConvertResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_and_convert(
    request: Request,
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    conversion_type: str = Form("pdf_to_docx"),
    db: Session = Depends(get_db),
):
    user_id = get_optional_user_id(request)

    if conversion_type not in get_supported_conversion_types():
        raise HTTPException(400, "Неподдерживаемый тип конвертации")

    expected_exts = get_input_extensions(conversion_type)

    uploaded_items: list[UploadFile] = []
    if file is not None:
        uploaded_items.append(file)
    if files:
        uploaded_items.extend(files)
    uploaded_items = [item for item in uploaded_items if item and item.filename]

    if not uploaded_items:
        raise HTTPException(400, "Файл не передан")

    # Multi-file flow (JPG->PDF and archive packers).
    if conversion_type in MULTI_FILE_TYPES:
        if len(uploaded_items) > 50:
            raise HTTPException(400, "Можно загрузить не более 50 файлов за раз")

        uploaded_items.sort(key=lambda item: (item.filename or "").lower())

        batch_payloads: list[tuple[str, bytes]] = []
        total_size = 0
        for uploaded in uploaded_items:
            filename = uploaded.filename or ""
            if not _is_extension_allowed(filename, expected_exts):
                if not expected_exts or "*" in expected_exts:
                    raise HTTPException(400, "Тип файла не поддерживается для этой операции")
                pretty_exts = ", ".join(ext.upper().lstrip(".") for ext in expected_exts)
                raise HTTPException(400, f"Разрешены только файлы: {pretty_exts}")

            payload = await uploaded.read()
            if len(payload) == 0:
                raise HTTPException(400, f"Файл {filename} пуст")
            if len(payload) > MAX_BYTES:
                raise HTTPException(413, f"Файл {filename} превышает ограничение {settings.MAX_FILE_SIZE_MB} МБ")

            _validate_file_bytes(conversion_type, payload)
            batch_payloads.append((filename, payload))
            total_size += len(payload)

        if total_size > MAX_BYTES * 5:
            raise HTTPException(413, f"Суммарный размер файлов не должен превышать {settings.MAX_FILE_SIZE_MB * 5} МБ")

        first_name = batch_payloads[0][0]
        if len(batch_payloads) == 1:
            task_label = first_name
        else:
            task_label = f"{first_name} (+{len(batch_payloads) - 1} файлов)"

        task_uuid = create_task_record(db, user_id, task_label, conversion_type)
        if conversion_type == "jpg_to_pdf":
            background_tasks.add_task(convert_images_to_pdf, task_uuid, batch_payloads, db)
        else:
            background_tasks.add_task(convert_files_batch, task_uuid, batch_payloads, conversion_type, db)
        return {"task_id": task_uuid, "message": "Конвертация запущена"}

    if len(uploaded_items) != 1:
        raise HTTPException(400, "Для этого типа конвертации нужно загрузить один файл")

    uploaded = uploaded_items[0]
    filename = uploaded.filename or ""
    if not _is_extension_allowed(filename, expected_exts):
        if not expected_exts or "*" in expected_exts:
            raise HTTPException(400, "Тип файла не поддерживается для этой операции")
        pretty_exts = ", ".join(ext.upper().lstrip(".") for ext in expected_exts)
        raise HTTPException(400, f"Разрешены только файлы: {pretty_exts}")

    source_bytes = await uploaded.read()
    if len(source_bytes) > MAX_BYTES:
        raise HTTPException(413, f"Файл превышает ограничение {settings.MAX_FILE_SIZE_MB} МБ")
    if len(source_bytes) == 0:
        raise HTTPException(400, "Загруженный файл пуст")

    _validate_file_bytes(conversion_type, source_bytes)

    task_uuid = create_task_record(db, user_id, filename, conversion_type)
    background_tasks.add_task(convert_file, task_uuid, source_bytes, filename, conversion_type, db)
    return {"task_id": task_uuid, "message": "Конвертация запущена"}


@router.get("/convert/history", response_model=HistoryResponse)
def get_history(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    conversion_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None, min_length=1, max_length=120),
):
    user_id = get_current_user_id(request)
    base_query = db.query(ConversionTask).filter(ConversionTask.user_id == user_id)
    if conversion_type:
        if conversion_type not in get_supported_conversion_types():
            raise HTTPException(400, "Неподдерживаемый тип конвертации")
        base_query = base_query.filter(ConversionTask.conversion_type == conversion_type)
    if search:
        pattern = f"%{search.strip()}%"
        base_query = base_query.filter(
            or_(
                ConversionTask.original_filename.ilike(pattern),
                ConversionTask.output_filename.ilike(pattern),
                ConversionTask.conversion_type.ilike(pattern),
            )
        )
    total = base_query.count()
    tasks = (
        base_query
        .order_by(ConversionTask.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [_task_to_response(t) for t in tasks],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/convert/{task_id}", response_model=TaskResponse)
def get_task_status(task_id: str, request: Request, db: Session = Depends(get_db)):
    user_id = get_optional_user_id(request)
    task = _get_task_or_404(task_id, user_id, db)
    return _task_to_response(task)


@router.delete("/convert/{task_id}", response_model=MessageResponse)
def delete_task(task_id: str, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    task = _get_user_task_or_404(task_id, user_id, db)

    if task.status in {TaskStatus.PENDING, TaskStatus.PROCESSING}:
        raise HTTPException(409, "Нельзя удалить задачу, пока она выполняется")

    output_filename = task.output_filename
    db.delete(task)
    db.commit()

    if output_filename:
        output_path = Path(settings.OUTPUT_DIR) / output_filename
        try:
            output_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove output file for deleted task: %s", output_path)

    return {"message": "Запись удалена из истории"}


@router.get("/download/{filename}")
def download_file(filename: str, request: Request, db: Session = Depends(get_db)):
    user_id = get_optional_user_id(request)
    task = (
        _scoped_task_query(db, user_id)
        .filter(
            ConversionTask.output_filename == filename,
            ConversionTask.status == TaskStatus.DONE,
        )
        .first()
    )
    if not task:
        raise HTTPException(404, "Файл не найден или доступ запрещён")

    file_path = Path(settings.OUTPUT_DIR) / filename
    if not file_path.exists():
        raise HTTPException(404, "Файл больше не доступен на сервере")

    return FileResponse(
        path=str(file_path),
        media_type=_build_media_type(task),
        filename=_build_download_name(task),
    )


def _get_task_or_404(task_uuid_str: str, user_id: Optional[int], db: Session) -> ConversionTask:
    try:
        uid = _uuid.UUID(task_uuid_str)
    except ValueError:
        raise HTTPException(404, "Задача не найдена")

    task = _scoped_task_query(db, user_id).filter(ConversionTask.task_uuid == uid).first()
    if not task:
        raise HTTPException(404, "Задача не найдена")
    return task


def _get_user_task_or_404(task_uuid_str: str, user_id: int, db: Session) -> ConversionTask:
    try:
        uid = _uuid.UUID(task_uuid_str)
    except ValueError:
        raise HTTPException(404, "Задача не найдена")

    task = (
        db.query(ConversionTask)
        .filter(ConversionTask.task_uuid == uid, ConversionTask.user_id == user_id)
        .first()
    )
    if not task:
        raise HTTPException(404, "Задача не найдена")
    return task


def _task_to_response(task: ConversionTask) -> TaskResponse:
    return TaskResponse(
        task_id=str(task.task_uuid),
        conversion_type=task.conversion_type,
        status=task.status,
        original_filename=task.original_filename,
        output_filename=task.output_filename,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
