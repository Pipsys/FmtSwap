"""
PDF to DOCX conversion service.
Uses pdf2docx library which preserves text, fonts, tables, and basic layout.
"""
import os
import uuid
import asyncio
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.models import ConversionTask, TaskStatus
from app.core.config import get_settings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
settings = get_settings()


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
    from pdf2docx import Converter

    cv = Converter(pdf_path)
    try:
        # parse() extracts text, images, tables, fonts and writes to DOCX
        cv.convert(docx_path, start=0, end=None)
    finally:
        cv.close()


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
        await loop.run_in_executor(None, _do_convert, str(pdf_path), str(docx_path))

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
