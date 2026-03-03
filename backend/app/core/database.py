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
    if not inspector.has_table("conversion_tasks"):
        return

    columns = {column["name"] for column in inspector.get_columns("conversion_tasks")}

    with engine.begin() as conn:
        # Guest conversions require nullable user_id in older PostgreSQL schemas.
        if engine.dialect.name == "postgresql" and "user_id" in columns:
            conn.execute(text("ALTER TABLE conversion_tasks ALTER COLUMN user_id DROP NOT NULL"))

        if "conversion_type" not in columns:
            conn.execute(text("ALTER TABLE conversion_tasks ADD COLUMN conversion_type VARCHAR(32)"))

        _backfill_conversion_type(conn)

        if engine.dialect.name == "postgresql":
            conn.execute(
                text(
                    "ALTER TABLE conversion_tasks ALTER COLUMN conversion_type SET DEFAULT 'pdf_to_docx'"
                )
            )

        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_tasks_conversion_type ON conversion_tasks (conversion_type)")
        )
