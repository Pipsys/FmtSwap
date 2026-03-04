"""
Helpers for hosted files: token generation, storage paths, and expired-file cleanup.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import re
import secrets
import uuid
from typing import Optional

from fastapi import Request, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.models import HostedFile

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:  # pragma: no cover - optional fallback if apscheduler is not installed
    BackgroundScheduler = None

settings = get_settings()
logger = logging.getLogger(__name__)

GUEST_SESSION_COOKIE = "guest_session_id"
_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._()-]+")
_scheduler = None

LIFETIME_CHOICES = {
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
    "forever": None,
}


def get_hosting_dir() -> Path:
    path = Path(settings.HOSTING_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(filename: str) -> str:
    raw = (filename or "").strip().replace("\\", "/").split("/")[-1]
    raw = _FILENAME_SAFE_RE.sub("_", raw)
    raw = raw.strip("._ ")
    return raw or "file"


def generate_public_token() -> str:
    # URL-safe 22+ chars, difficult to brute-force.
    return secrets.token_urlsafe(18)


def make_stored_filename(original_filename: str) -> str:
    sanitized = sanitize_filename(original_filename)
    suffix = Path(sanitized).suffix.lower()
    return f"{uuid.uuid4().hex}{suffix}"


def get_client_ip(request: Request) -> Optional[str]:
    xff = request.headers.get("x-forwarded-for", "").strip()
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def get_or_set_guest_session_id(request: Request, response: Response) -> str:
    existing = request.cookies.get(GUEST_SESSION_COOKIE)
    if existing:
        return existing

    sid = uuid.uuid4().hex
    response.set_cookie(
        GUEST_SESSION_COOKIE,
        sid,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return sid


def build_share_url(token: str) -> str:
    base = settings.FRONTEND_URL.rstrip("/")
    return f"{base}/share/{token}"


def build_download_url(token: str) -> str:
    return f"/api/share/{token}/download"


def resolve_expires_at_from_lifetime(lifetime: str, now: Optional[datetime] = None) -> Optional[datetime]:
    key = (lifetime or "").strip().lower()
    if key not in LIFETIME_CHOICES:
        raise ValueError("Недопустимый срок действия ссылки")
    delta = LIFETIME_CHOICES[key]
    if delta is None:
        return None
    base = now or datetime.now(timezone.utc)
    return base + delta


def remove_file_from_disk(stored_filename: str) -> None:
    try:
        (get_hosting_dir() / stored_filename).unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove hosted file from disk: %s", stored_filename)


def cleanup_expired_files(db: Session, now: Optional[datetime] = None) -> int:
    now_utc = now or datetime.now(timezone.utc)
    expired_items = (
        db.query(HostedFile)
        .filter(HostedFile.expires_at.is_not(None), HostedFile.expires_at <= now_utc)
        .all()
    )
    if not expired_items:
        return 0

    for item in expired_items:
        remove_file_from_disk(item.stored_filename)
        db.delete(item)

    db.commit()
    return len(expired_items)


def cleanup_expired_files_job() -> None:
    db = SessionLocal()
    try:
        removed = cleanup_expired_files(db)
        if removed:
            logger.info("Expired hosted files removed: %s", removed)
    except Exception:
        logger.exception("Failed to cleanup expired hosted files")
    finally:
        db.close()


def start_hosting_cleanup_scheduler() -> None:
    global _scheduler
    if BackgroundScheduler is None:
        logger.warning("APScheduler is not installed. Hosted file cleanup scheduler is disabled.")
        return

    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        cleanup_expired_files_job,
        trigger="interval",
        minutes=1,
        id="hosted_files_cleanup",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Hosted files cleanup scheduler started")


def stop_hosting_cleanup_scheduler() -> None:
    global _scheduler
    if not _scheduler:
        return
    try:
        _scheduler.shutdown(wait=False)
    except Exception:
        logger.exception("Failed to stop hosting cleanup scheduler")
    finally:
        _scheduler = None
