"""
Conversion endpoints.
task_uuid comes from DB as uuid.UUID — cast to str everywhere via str(task.task_uuid).
"""
import logging
import uuid as _uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.models import ConversionTask, TaskStatus
from app.schemas.schemas import ConvertResponse, TaskResponse
from app.services.converter import convert_pdf_to_docx, create_task_record
from app.core.config import get_settings
from typing import List

router = APIRouter(tags=["convert"])
settings = get_settings()
logger = logging.getLogger(__name__)

MAX_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024
PDF_MAGIC = b"%PDF-"


def _is_pdf(data: bytes) -> bool:
    return data[:5] == PDF_MAGIC


@router.post("/convert", response_model=ConvertResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_and_convert(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user_id = get_current_user_id(request)

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    pdf_bytes = await file.read()

    if len(pdf_bytes) > MAX_BYTES:
        raise HTTPException(413, f"File exceeds {settings.MAX_FILE_SIZE_MB} MB limit")
    if len(pdf_bytes) == 0:
        raise HTTPException(400, "Uploaded file is empty")
    if not _is_pdf(pdf_bytes):
        raise HTTPException(400, "File is not a valid PDF (wrong magic bytes)")

    task_uuid = create_task_record(db, user_id, file.filename)
    background_tasks.add_task(convert_pdf_to_docx, task_uuid, pdf_bytes, file.filename, db)
    return {"task_id": task_uuid, "message": "Conversion started"}


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
    user_id = get_current_user_id(request)
    task = _get_task_or_404(task_id, user_id, db)
    return _task_to_response(task)


@router.get("/download/{filename}")
def download_file(filename: str, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    task = (
        db.query(ConversionTask)
        .filter(
            ConversionTask.output_filename == filename,
            ConversionTask.user_id == user_id,
            ConversionTask.status == TaskStatus.DONE,
        )
        .first()
    )
    if not task:
        raise HTTPException(404, "File not found or access denied")

    file_path = Path(settings.OUTPUT_DIR) / filename
    if not file_path.exists():
        raise HTTPException(404, "File no longer available on server")

    download_name = Path(task.original_filename).stem + ".docx"
    return FileResponse(
        path=str(file_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=download_name,
    )


def _get_task_or_404(task_uuid_str: str, user_id: int, db: Session) -> ConversionTask:
    try:
        uid = _uuid.UUID(task_uuid_str)
    except ValueError:
        raise HTTPException(404, "Task not found")
    task = (
        db.query(ConversionTask)
        .filter(ConversionTask.task_uuid == uid, ConversionTask.user_id == user_id)
        .first()
    )
    if not task:
        raise HTTPException(404, "Task not found")
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
