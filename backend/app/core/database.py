"""
Database configuration and session management.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator
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


def create_tables() -> None:
    """Create all tables (used for simple SQLite setup without Alembic)."""
    Base.metadata.create_all(bind=engine)

    # Lightweight schema tweak for existing PostgreSQL deployments:
    # guest conversions require conversion_tasks.user_id to be nullable.
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE conversion_tasks ALTER COLUMN user_id DROP NOT NULL"))
