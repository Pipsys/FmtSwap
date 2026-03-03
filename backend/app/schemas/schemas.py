"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models.models import TaskStatus


class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Имя пользователя может содержать только буквы, цифры, дефисы и подчёркивания")
        if len(v) < 3 or len(v) > 32:
            raise ValueError("Имя пользователя должно быть длиной от 3 до 32 символов")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов")
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


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    original_filename: str
    output_filename: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "arbitrary_types_allowed": True,
    }


class HistoryResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    limit: int
    offset: int


class ConvertResponse(BaseModel):
    task_id: str
    message: str


class MessageResponse(BaseModel):
    message: str
