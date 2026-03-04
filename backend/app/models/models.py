"""
SQLAlchemy ORM models.
"""
from datetime import datetime, timezone
import enum
import uuid

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    twofa_enabled = Column(Boolean, nullable=False, default=False)
    twofa_secret = Column(String(128), nullable=True)
    twofa_pending_secret = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tasks = relationship("ConversionTask", back_populates="owner", cascade="all, delete-orphan")
    hosted_files = relationship("HostedFile", back_populates="owner", cascade="all, delete-orphan")


class ConversionTask(Base):
    __tablename__ = "conversion_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_uuid = Column(PG_UUID(as_uuid=True), unique=True, index=True, nullable=False, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    conversion_type = Column(String(32), nullable=False, default="pdf_to_docx", index=True)
    original_filename = Column(String, nullable=False)
    output_filename = Column(String, nullable=True)
    status = Column(
        SAEnum(TaskStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=TaskStatus.PENDING,
        nullable=False,
    )
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    owner = relationship("User", back_populates="tasks")


class HostedFile(Base):
    __tablename__ = "hosted_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    guest_session_id = Column(String(64), nullable=True, index=True)
    guest_ip = Column(String(64), nullable=True, index=True)
    public_token = Column(String(64), unique=True, index=True, nullable=False)
    original_filename = Column(String(512), nullable=False)
    stored_filename = Column(String(512), nullable=False, unique=True)
    content_type = Column(String(255), nullable=True)
    size_bytes = Column(BigInteger, nullable=False)
    description = Column(Text, nullable=True)
    password_hash = Column(String(255), nullable=True)
    download_count = Column(Integer, nullable=False, default=0)
    last_downloaded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    owner = relationship("User", back_populates="hosted_files")
    visits = relationship("HostedFileVisit", back_populates="hosted_file", cascade="all, delete-orphan")


class HostedFileVisit(Base):
    __tablename__ = "hosted_file_visits"

    id = Column(Integer, primary_key=True, index=True)
    hosted_file_id = Column(Integer, ForeignKey("hosted_files.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(16), nullable=False, index=True)  # view/download
    ip = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    hosted_file = relationship("HostedFile", back_populates="visits")
