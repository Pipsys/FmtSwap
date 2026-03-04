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
    otp_code: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    twofa_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    message: str
    user: UserResponse


class TaskResponse(BaseModel):
    task_id: str
    conversion_type: Optional[str] = None
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


class UpdateEmailRequest(BaseModel):
    new_email: EmailStr
    current_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Новый пароль должен содержать минимум 8 символов")
        return v


class TwoFactorSetupRequest(BaseModel):
    current_password: str


class TwoFactorSetupResponse(BaseModel):
    secret: str
    otpauth_url: str


class TwoFactorEnableRequest(BaseModel):
    otp_code: str


class TwoFactorDisableRequest(BaseModel):
    current_password: str
    otp_code: str


class HostedFileResponse(BaseModel):
    id: int
    original_filename: str
    size_bytes: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    description: Optional[str] = None
    is_password_protected: bool
    download_count: int
    last_downloaded_at: Optional[datetime] = None
    token: str
    share_url: str
    download_url: str


class HostedFileListResponse(BaseModel):
    items: list[HostedFileResponse]
    is_authenticated: bool


class HostedUploadResponse(BaseModel):
    message: str
    items: list[HostedFileResponse]


class SharedFileResponse(BaseModel):
    original_filename: str
    size_bytes: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    description: Optional[str] = None
    is_password_protected: bool
    token: str
    download_url: str


class HostedFileUpdateRequest(BaseModel):
    description: Optional[str] = None
    lifetime: Optional[str] = None
    password: Optional[str] = None
    remove_password: Optional[bool] = None


class HostedFileStatsPoint(BaseModel):
    date: str
    views: int
    downloads: int


class HostedFileStatsResponse(BaseModel):
    file_id: int
    download_count: int
    last_downloaded_at: Optional[datetime] = None
    total_views: int
    points: list[HostedFileStatsPoint]
