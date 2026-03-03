"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional
from app.models.models import TaskStatus


# ─── Auth schemas ─────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username must contain only letters, digits, hyphens, or underscores")
        if len(v) < 3 or len(v) > 32:
            raise ValueError("Username must be 3–32 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    message: str
    user: UserResponse


# ─── Conversion schemas ────────────────────────────────────────────────────────

class TaskResponse(BaseModel):
    task_id: str           # UUID stored as text in DB, cast to str explicitly
    status: TaskStatus
    original_filename: str
    output_filename: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        # Allow UUID → str coercion automatically
        "arbitrary_types_allowed": True,
    }


class ConvertResponse(BaseModel):
    task_id: str
    message: str


class MessageResponse(BaseModel):
    message: str
