"""
Conversion endpoints.
task_uuid comes from DB as uuid.UUID -> cast to str everywhere via str(task.task_uuid).
"""
import logging
import uuid as _uuid
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
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
from app.schemas.schemas import ConvertResponse, TaskResponse
from app.services.converter import (
    convert_file,
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


def _is_pdf(data: bytes) -> bool:
    return data[:5] == PDF_MAGIC


def _is_jpeg(data: bytes) -> bool:
    return data[:3] == JPEG_MAGIC


def _is_docx(data: bytes) -> bool:
    # DOCX is a ZIP container.
    return data[:4] == ZIP_MAGIC


def _validate_file_bytes(conversion_type: str, payload: bytes) -> None:
    if conversion_type in {"pdf_to_docx", "pdf_to_jpg"} and not _is_pdf(payload):
        raise HTTPException(400, "Файл не является корректным PDF")
    if conversion_type == "jpg_to_pdf" and not _is_jpeg(payload):
        raise HTTPException(400, "Файл не является корректным JPG")
    if conversion_type == "word_to_pdf" and not _is_docx(payload):
        raise HTTPException(400, "Файл не является корректным DOCX")


def _build_download_name(task: ConversionTask) -> str:
    original_stem = Path(task.original_filename).stem
    output_ext = Path(task.output_filename or "").suffix.lower()

    if output_ext == ".zip":
        return f"{original_stem}_jpg.zip"
    if output_ext:
        return f"{original_stem}{output_ext}"
    return task.output_filename or "result.bin"


def _build_media_type(task: ConversionTask) -> str:
    output_ext = Path(task.output_filename or "").suffix.lower()
    return {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".zip": "application/zip",
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
    file: UploadFile = File(...),
    conversion_type: str = Form("pdf_to_docx"),
    db: Session = Depends(get_db),
):
    user_id = get_optional_user_id(request)

    if conversion_type not in get_supported_conversion_types():
        raise HTTPException(400, "Неподдерживаемый тип конвертации")

    expected_exts = get_input_extensions(conversion_type)
    filename = file.filename or ""
    if not filename:
        raise HTTPException(400, "Имя файла отсутствует")

    if not any(filename.lower().endswith(ext) for ext in expected_exts):
        pretty_exts = ", ".join(ext.upper().lstrip(".") for ext in expected_exts)
        raise HTTPException(400, f"Разрешены только файлы: {pretty_exts}")

    source_bytes = await file.read()

    if len(source_bytes) > MAX_BYTES:
        raise HTTPException(413, f"Файл превышает ограничение {settings.MAX_FILE_SIZE_MB} МБ")
    if len(source_bytes) == 0:
        raise HTTPException(400, "Загруженный файл пуст")

    _validate_file_bytes(conversion_type, source_bytes)

    task_uuid = create_task_record(db, user_id, filename)
    background_tasks.add_task(convert_file, task_uuid, source_bytes, filename, conversion_type, db)
    return {"task_id": task_uuid, "message": "Конвертация запущена"}


@router.get("/convert/history", response_model=List[TaskResponse])
def get_history(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    tasks = (
        db.query(ConversionTask)
        .filter(ConversionTask.user_id == user_id)
        .order_by(ConversionTask.created_at.desc())
        .limit(50)
        .all()
    )
    return [_task_to_response(t) for t in tasks]


@router.get("/convert/{task_id}", response_model=TaskResponse)
def get_task_status(task_id: str, request: Request, db: Session = Depends(get_db)):
    user_id = get_optional_user_id(request)
    task = _get_task_or_404(task_id, user_id, db)
    return _task_to_response(task)


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


def _task_to_response(task: ConversionTask) -> TaskResponse:
    return TaskResponse(
        task_id=str(task.task_uuid),
        status=task.status,
        original_filename=task.original_filename,
        output_filename=task.output_filename,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
