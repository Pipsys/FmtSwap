"""
Core configuration module.
Loads settings from environment variables / .env file.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Security
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CSRF
    CSRF_SECRET: str = "dev-csrf-secret-change-in-production"

    # Database
    DATABASE_URL: str = "sqlite:///./pdf2docx.db"

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # File limits
    MAX_FILE_SIZE_MB: int = 50
    HOSTING_MAX_FILE_SIZE_MB: int = 100
    HOSTING_MAX_FILE_SIZE_AUTH_MB: int = 300
    GUEST_FILE_TTL_MINUTES: int = 15

    # PDF detection and OCR pipeline
    PDF_DETECT_SAMPLE_PAGES: int = 5
    PDF_TEXT_MIN_CHARS_PER_PAGE: int = 50
    PDF_TEXT_MIN_PAGES: int = 1
    ENABLE_SCANNED_OCR: bool = True
    OCR_LANG: str = "eng"
    TESSDATA_PREFIX: str = ""

    # Storage directories
    UPLOAD_DIR: str = "uploads"
    OUTPUT_DIR: str = "outputs"
    HOSTING_DIR: str = "hosting"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
