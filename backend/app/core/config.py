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

    # Storage directories
    UPLOAD_DIR: str = "uploads"
    OUTPUT_DIR: str = "outputs"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
