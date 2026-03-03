"""
SQLAlchemy ORM models.
task_uuid хранится как нативный UUID в PostgreSQL.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
import enum, uuid
from app.core.database import Base


class TaskStatus(str, enum.Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    DONE       = "done"
    FAILED     = "failed"


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String, unique=True, index=True, nullable=False)
    username        = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tasks = relationship("ConversionTask", back_populates="owner", cascade="all, delete-orphan")


class ConversionTask(Base):
    __tablename__ = "conversion_tasks"

    id                = Column(Integer, primary_key=True, index=True)
    # as_uuid=True → Python получает uuid.UUID; мы сами конвертируем в str при отдаче
    task_uuid         = Column(PG_UUID(as_uuid=True), unique=True, index=True,
                               nullable=False, default=uuid.uuid4)
    user_id           = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_filename = Column(String, nullable=False)
    output_filename   = Column(String, nullable=True)
    status            = Column(
        SAEnum(TaskStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=TaskStatus.PENDING,
        nullable=False,
    )
    error_message = Column(String, nullable=True)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="tasks")
