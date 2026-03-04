"""
File hosting endpoints.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_optional_user_id, hash_password, verify_password
from app.models.models import HostedFile, HostedFileVisit
from app.schemas.schemas import (
    HostedFileListResponse,
    HostedFileResponse,
    HostedFileStatsResponse,
    HostedFileStatsPoint,
    HostedFileUpdateRequest,
    HostedUploadResponse,
    MessageResponse,
    SharedFileResponse,
)
from app.services.file_hosting import (
    GUEST_SESSION_COOKIE,
    build_download_url,
    build_share_url,
    cleanup_expired_files,
    get_client_ip,
    get_hosting_dir,
    get_or_set_guest_session_id,
    make_stored_filename,
    remove_file_from_disk,
    resolve_expires_at_from_lifetime,
    sanitize_filename,
)

router = APIRouter(tags=["hosting"])
settings = get_settings()
logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024
MAX_FILES_PER_UPLOAD = 50
MAX_DESCRIPTION_LENGTH = 1000
MIN_PASSWORD_LEN = 4


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hosting_limit_bytes(is_authenticated: bool) -> int:
    mb = settings.HOSTING_MAX_FILE_SIZE_AUTH_MB if is_authenticated else settings.HOSTING_MAX_FILE_SIZE_MB
    return max(1, mb) * 1024 * 1024


def _normalize_description(value: Optional[str]) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return None
    if len(text) > MAX_DESCRIPTION_LENGTH:
        raise HTTPException(400, f"Описание не должно превышать {MAX_DESCRIPTION_LENGTH} символов")
    return text


def _normalize_password(value: Optional[str]) -> Optional[str]:
    pwd = (value or "").strip()
    if not pwd:
        return None
    if len(pwd) < MIN_PASSWORD_LEN:
        raise HTTPException(400, f"Пароль ссылки должен быть не короче {MIN_PASSWORD_LEN} символов")
    return pwd


def _build_file_item(item: HostedFile) -> HostedFileResponse:
    token = item.public_token
    return HostedFileResponse(
        id=item.id,
        original_filename=item.original_filename,
        size_bytes=item.size_bytes,
        created_at=item.created_at,
        expires_at=item.expires_at,
        description=item.description,
        is_password_protected=bool(item.password_hash),
        download_count=item.download_count or 0,
        last_downloaded_at=item.last_downloaded_at,
        token=token,
        share_url=build_share_url(token),
        download_url=build_download_url(token),
    )


def _get_unique_token(db: Session) -> str:
    import secrets

    for _ in range(10):
        token = secrets.token_urlsafe(18)
        exists = db.query(HostedFile.id).filter(HostedFile.public_token == token).first()
        if not exists:
            return token
    raise HTTPException(500, "Не удалось создать уникальную ссылку. Повторите попытку.")


def _resolve_upload_expires_at(user_id: Optional[int], lifetime: str) -> Optional[datetime]:
    if user_id is None:
        return _now() + timedelta(minutes=settings.GUEST_FILE_TTL_MINUTES)

    try:
        return resolve_expires_at_from_lifetime(lifetime, _now())
    except ValueError as exc:
        raise HTTPException(400, str(exc))


async def _save_upload_file(upload: UploadFile, destination: Path, max_bytes: int) -> int:
    size = 0
    try:
        with destination.open("wb") as out:
            while True:
                chunk = await upload.read(CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Файл {upload.filename or ''} превышает лимит {max_bytes // (1024 * 1024)} МБ",
                    )
                out.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    if size == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(400, "Нельзя загрузить пустой файл")

    return size


def _scoped_guest_filter(query, guest_session_id: Optional[str], guest_ip: Optional[str]):
    query = query.filter(HostedFile.user_id.is_(None))
    if guest_session_id:
        return query.filter(HostedFile.guest_session_id == guest_session_id)
    if guest_ip:
        return query.filter(HostedFile.guest_ip == guest_ip)
    return query.filter(HostedFile.id == -1)


def _active_files_query(db: Session):
    now_utc = _now()
    return db.query(HostedFile).filter(or_(HostedFile.expires_at.is_(None), HostedFile.expires_at > now_utc))


def _record_visit(db: Session, item: HostedFile, event_type: str, ip: Optional[str]) -> None:
    visit = HostedFileVisit(hosted_file_id=item.id, event_type=event_type, ip=ip)
    db.add(visit)

    if event_type == "download":
        item.download_count = (item.download_count or 0) + 1
        item.last_downloaded_at = _now()

    db.commit()


def _get_owned_file_or_404(
    db: Session,
    file_id: int,
    user_id: Optional[int],
    guest_session_id: Optional[str],
    guest_ip: Optional[str],
) -> HostedFile:
    query = db.query(HostedFile).filter(HostedFile.id == file_id)
    if user_id is not None:
        query = query.filter(HostedFile.user_id == user_id)
    else:
        query = _scoped_guest_filter(query, guest_session_id, guest_ip)

    item = query.first()
    if not item:
        raise HTTPException(404, "Файл не найден")
    return item


def _get_public_file_or_404(token: str, db: Session) -> HostedFile:
    cleanup_expired_files(db)
    item = db.query(HostedFile).filter(HostedFile.public_token == token).first()
    if not item:
        raise HTTPException(404, "Файл не найден или срок хранения истёк")

    if item.expires_at and item.expires_at <= _now():
        remove_file_from_disk(item.stored_filename)
        db.delete(item)
        db.commit()
        raise HTTPException(404, "Файл не найден или срок хранения истёк")

    return item


@router.post("/upload", response_model=HostedUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_files(
    request: Request,
    response: Response,
    files: list[UploadFile] = File(...),
    lifetime: str = Form("1d"),
    description: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    cleanup_expired_files(db)

    if not files:
        raise HTTPException(400, "Файлы не переданы")
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(400, f"Можно загрузить не более {MAX_FILES_PER_UPLOAD} файлов за раз")

    user_id = get_optional_user_id(request)
    is_authenticated = user_id is not None
    max_bytes = _hosting_limit_bytes(is_authenticated)

    item_description = _normalize_description(description)
    pwd = _normalize_password(password)
    password_hash = hash_password(pwd) if pwd else None

    guest_session_id = None
    if not is_authenticated:
        guest_session_id = get_or_set_guest_session_id(request, response)
    guest_ip = get_client_ip(request)

    storage_dir = get_hosting_dir()
    created_items: list[HostedFile] = []
    created_paths: list[Path] = []

    try:
        for upload in files:
            original_name = sanitize_filename(upload.filename or "file")
            stored_name = make_stored_filename(original_name)
            target_path = storage_dir / stored_name
            size_bytes = await _save_upload_file(upload, target_path, max_bytes)

            token = _get_unique_token(db)
            expires_at = _resolve_upload_expires_at(user_id, lifetime)

            record = HostedFile(
                user_id=user_id,
                guest_session_id=guest_session_id,
                guest_ip=guest_ip,
                public_token=token,
                original_filename=original_name,
                stored_filename=stored_name,
                content_type=(upload.content_type or "application/octet-stream")[:255],
                size_bytes=size_bytes,
                description=item_description,
                password_hash=password_hash,
                expires_at=expires_at,
            )
            db.add(record)
            created_items.append(record)
            created_paths.append(target_path)

        db.commit()
        for item in created_items:
            db.refresh(item)
    except HTTPException:
        db.rollback()
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise
    except Exception:
        db.rollback()
        for path in created_paths:
            path.unlink(missing_ok=True)
        logger.exception("Unexpected error while uploading hosted files")
        raise HTTPException(500, "Не удалось загрузить файлы")

    return {
        "message": "Файлы успешно загружены",
        "items": [_build_file_item(item) for item in created_items],
    }


@router.get("/files", response_model=HostedFileListResponse)
def list_files(request: Request, db: Session = Depends(get_db)):
    cleanup_expired_files(db)

    user_id = get_optional_user_id(request)
    guest_session_id = request.cookies.get(GUEST_SESSION_COOKIE)
    guest_ip = get_client_ip(request)

    query = _active_files_query(db)
    if user_id is not None:
        query = query.filter(HostedFile.user_id == user_id)
    else:
        query = _scoped_guest_filter(query, guest_session_id, guest_ip)

    items = query.order_by(HostedFile.created_at.desc()).all()
    return {
        "items": [_build_file_item(item) for item in items],
        "is_authenticated": user_id is not None,
    }


@router.patch("/files/{file_id}", response_model=HostedFileResponse)
def update_file(
    file_id: int,
    body: HostedFileUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = get_optional_user_id(request)
    guest_session_id = request.cookies.get(GUEST_SESSION_COOKIE)
    guest_ip = get_client_ip(request)

    item = _get_owned_file_or_404(db, file_id, user_id, guest_session_id, guest_ip)

    changed = False

    if body.description is not None:
        item.description = _normalize_description(body.description)
        changed = True

    if body.password is not None:
        pwd = _normalize_password(body.password)
        item.password_hash = hash_password(pwd) if pwd else None
        changed = True

    if body.remove_password:
        item.password_hash = None
        changed = True

    if body.lifetime is not None:
        if user_id is None:
            raise HTTPException(403, "Изменение срока действия доступно только авторизованным пользователям")
        try:
            item.expires_at = resolve_expires_at_from_lifetime(body.lifetime, _now())
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        changed = True

    if not changed:
        return _build_file_item(item)

    db.commit()
    db.refresh(item)
    return _build_file_item(item)


@router.delete("/files/{file_id}", response_model=MessageResponse)
def delete_file(file_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = get_optional_user_id(request)
    guest_session_id = request.cookies.get(GUEST_SESSION_COOKIE)
    guest_ip = get_client_ip(request)

    item = _get_owned_file_or_404(db, file_id, user_id, guest_session_id, guest_ip)
    remove_file_from_disk(item.stored_filename)
    db.delete(item)
    db.commit()
    return {"message": "Файл удалён"}


@router.get("/files/{file_id}/stats", response_model=HostedFileStatsResponse)
def file_stats(
    file_id: int,
    request: Request,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    user_id = get_optional_user_id(request)
    guest_session_id = request.cookies.get(GUEST_SESSION_COOKIE)
    guest_ip = get_client_ip(request)
    item = _get_owned_file_or_404(db, file_id, user_id, guest_session_id, guest_ip)

    now_utc = _now()
    start_dt = now_utc - timedelta(days=days - 1)
    visits = (
        db.query(HostedFileVisit)
        .filter(HostedFileVisit.hosted_file_id == item.id, HostedFileVisit.created_at >= start_dt)
        .all()
    )

    buckets: dict[str, dict[str, int]] = {}
    for v in visits:
        day = v.created_at.date().isoformat()
        if day not in buckets:
            buckets[day] = {"views": 0, "downloads": 0}
        if v.event_type == "download":
            buckets[day]["downloads"] += 1
        else:
            buckets[day]["views"] += 1

    points: list[HostedFileStatsPoint] = []
    total_views = 0
    cursor = start_dt.date()
    end_date = now_utc.date()
    while cursor <= end_date:
        key = cursor.isoformat()
        views = buckets.get(key, {}).get("views", 0)
        downloads = buckets.get(key, {}).get("downloads", 0)
        total_views += views
        points.append(HostedFileStatsPoint(date=key, views=views, downloads=downloads))
        cursor += timedelta(days=1)

    return HostedFileStatsResponse(
        file_id=item.id,
        download_count=item.download_count or 0,
        last_downloaded_at=item.last_downloaded_at,
        total_views=total_views,
        points=points,
    )


@router.get("/share/{token}", response_model=SharedFileResponse)
def get_shared_file(token: str, request: Request, db: Session = Depends(get_db)):
    item = _get_public_file_or_404(token, db)
    _record_visit(db, item, "view", get_client_ip(request))
    db.refresh(item)
    return SharedFileResponse(
        original_filename=item.original_filename,
        size_bytes=item.size_bytes,
        created_at=item.created_at,
        expires_at=item.expires_at,
        description=item.description,
        is_password_protected=bool(item.password_hash),
        token=item.public_token,
        download_url=build_download_url(item.public_token),
    )


@router.get("/share/{token}/download")
def download_shared_file(
    token: str,
    request: Request,
    password: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    item = _get_public_file_or_404(token, db)
    file_path = get_hosting_dir() / item.stored_filename
    if not file_path.exists():
        db.delete(item)
        db.commit()
        raise HTTPException(404, "Файл не найден или срок хранения истёк")

    if item.password_hash:
        if not password:
            raise HTTPException(403, "Файл защищён паролем")
        if not verify_password(password, item.password_hash):
            raise HTTPException(403, "Неверный пароль к файлу")

    _record_visit(db, item, "download", get_client_ip(request))
    return FileResponse(
        path=str(file_path),
        media_type=item.content_type or "application/octet-stream",
        filename=item.original_filename,
    )
