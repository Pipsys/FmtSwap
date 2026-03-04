"""
Database configuration and session management.
"""
from typing import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# SQLite needs check_same_thread=False; for PostgreSQL remove connect_args
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _backfill_conversion_type(conn) -> None:
    conn.execute(
        text(
            """
            UPDATE conversion_tasks
            SET conversion_type = CASE
                WHEN lower(coalesce(output_filename, '')) LIKE '%.docx' THEN 'pdf_to_docx'
                WHEN lower(coalesce(output_filename, '')) LIKE '%.zip' THEN 'pdf_to_jpg'
                WHEN lower(coalesce(original_filename, '')) LIKE '%.jpg'
                  OR lower(coalesce(original_filename, '')) LIKE '%.jpeg'
                  OR lower(coalesce(original_filename, '')) LIKE '%.jfif' THEN 'jpg_to_pdf'
                WHEN lower(coalesce(original_filename, '')) LIKE '%.doc'
                  OR lower(coalesce(original_filename, '')) LIKE '%.docx'
                  OR lower(coalesce(original_filename, '')) LIKE '%.docm' THEN 'word_to_pdf'
                WHEN lower(coalesce(original_filename, '')) LIKE '%.pdf' THEN 'pdf_to_docx'
                ELSE 'pdf_to_docx'
            END
            WHERE conversion_type IS NULL OR conversion_type = ''
            """
        )
    )


def create_tables() -> None:
    """Create tables and apply lightweight schema updates for existing deployments."""
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    has_tasks = inspector.has_table("conversion_tasks")
    has_users = inspector.has_table("users")
    has_hosted = inspector.has_table("hosted_files")
    has_hosted_visits = inspector.has_table("hosted_file_visits")
    if not has_tasks and not has_users and not has_hosted and not has_hosted_visits:
        return

    task_columns = {column["name"] for column in inspector.get_columns("conversion_tasks")} if has_tasks else set()
    user_columns = {column["name"] for column in inspector.get_columns("users")} if has_users else set()
    hosted_columns = {column["name"] for column in inspector.get_columns("hosted_files")} if has_hosted else set()
    hosted_visit_columns = (
        {column["name"] for column in inspector.get_columns("hosted_file_visits")}
        if has_hosted_visits
        else set()
    )

    with engine.begin() as conn:
        # Guest conversions require nullable user_id in older PostgreSQL schemas.
        if has_tasks and engine.dialect.name == "postgresql" and "user_id" in task_columns:
            conn.execute(text("ALTER TABLE conversion_tasks ALTER COLUMN user_id DROP NOT NULL"))

        if has_tasks and "conversion_type" not in task_columns:
            conn.execute(text("ALTER TABLE conversion_tasks ADD COLUMN conversion_type VARCHAR(32)"))

        if has_tasks:
            _backfill_conversion_type(conn)

        if has_tasks and engine.dialect.name == "postgresql":
            conn.execute(
                text(
                    "ALTER TABLE conversion_tasks ALTER COLUMN conversion_type SET DEFAULT 'pdf_to_docx'"
                )
            )

        if has_tasks:
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_tasks_conversion_type ON conversion_tasks (conversion_type)")
            )

        # 2FA profile fields for existing deployments.
        if has_users and "twofa_enabled" not in user_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN twofa_enabled BOOLEAN NOT NULL DEFAULT FALSE"))
        if has_users and "twofa_secret" not in user_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN twofa_secret VARCHAR(128)"))
        if has_users and "twofa_pending_secret" not in user_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN twofa_pending_secret VARCHAR(128)"))

        # File hosting table fields for existing deployments.
        if has_hosted and "guest_session_id" not in hosted_columns:
            conn.execute(text("ALTER TABLE hosted_files ADD COLUMN guest_session_id VARCHAR(64)"))
        if has_hosted and "guest_ip" not in hosted_columns:
            conn.execute(text("ALTER TABLE hosted_files ADD COLUMN guest_ip VARCHAR(64)"))
        if has_hosted and "public_token" not in hosted_columns:
            conn.execute(text("ALTER TABLE hosted_files ADD COLUMN public_token VARCHAR(64)"))
        if has_hosted and "stored_filename" not in hosted_columns:
            conn.execute(text("ALTER TABLE hosted_files ADD COLUMN stored_filename VARCHAR(512)"))
        if has_hosted and "size_bytes" not in hosted_columns:
            conn.execute(text("ALTER TABLE hosted_files ADD COLUMN size_bytes BIGINT"))
        if has_hosted and "expires_at" not in hosted_columns:
            expires_type = "TIMESTAMPTZ" if engine.dialect.name == "postgresql" else "DATETIME"
            conn.execute(text(f"ALTER TABLE hosted_files ADD COLUMN expires_at {expires_type}"))
        if has_hosted and "description" not in hosted_columns:
            conn.execute(text("ALTER TABLE hosted_files ADD COLUMN description TEXT"))
        if has_hosted and "password_hash" not in hosted_columns:
            conn.execute(text("ALTER TABLE hosted_files ADD COLUMN password_hash VARCHAR(255)"))
        if has_hosted and "download_count" not in hosted_columns:
            conn.execute(text("ALTER TABLE hosted_files ADD COLUMN download_count INTEGER DEFAULT 0"))
        if has_hosted and "last_downloaded_at" not in hosted_columns:
            last_dl_type = "TIMESTAMPTZ" if engine.dialect.name == "postgresql" else "DATETIME"
            conn.execute(text(f"ALTER TABLE hosted_files ADD COLUMN last_downloaded_at {last_dl_type}"))

        if has_hosted:
            conn.execute(text("UPDATE hosted_files SET download_count = 0 WHERE download_count IS NULL"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_hosted_files_user_id ON hosted_files (user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_hosted_files_session ON hosted_files (guest_session_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_hosted_files_ip ON hosted_files (guest_ip)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_hosted_files_token ON hosted_files (public_token)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_hosted_files_expiry ON hosted_files (expires_at)"))

        if has_hosted_visits and "event_type" not in hosted_visit_columns:
            conn.execute(text("ALTER TABLE hosted_file_visits ADD COLUMN event_type VARCHAR(16)"))
        if has_hosted_visits and "ip" not in hosted_visit_columns:
            conn.execute(text("ALTER TABLE hosted_file_visits ADD COLUMN ip VARCHAR(64)"))
        if has_hosted_visits:
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_hosted_visits_file_id ON hosted_file_visits (hosted_file_id)")
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_hosted_visits_created_at ON hosted_file_visits (created_at)")
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_hosted_visits_event_type ON hosted_file_visits (event_type)")
            )
