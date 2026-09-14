import os
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR.parent
DEFAULT_DB_FILE = (ROOT_DIR / "ai_study_companion.db").resolve()

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Study Companion"
    API_V1_STR: str = "/api"
    BASE_DIR: Path = BASE_DIR
    ROOT_DIR: Path = ROOT_DIR
    
    # Database
    # Defaults to SQLite absolute root path for immediate local usability; seamlessly points to PostgreSQL when DATABASE_URL is set
    DATABASE_URL: str = f"sqlite:///{DEFAULT_DB_FILE}"
    
    # Security & JWT
    JWT_SECRET: str = "dev_super_secret_key_change_in_production_ai_study_companion"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # CORS
    FRONTEND_URL: str = "http://localhost:5173"
    
    # Uploads
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    
    # AI & Embeddings (Day 1 Prompt 2 & AI Tutor)
    AI_API_KEY: str = ""
    AI_PROVIDER: str = "auto"  # "gemini", "openai", or "auto"
    AI_MODEL: str = "gemini-1.5-flash"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    EMBEDDING_MODEL: str = "text-embedding-004"

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if v in ("sqlite:///./ai_study_companion.db", "sqlite://ai_study_companion.db"):
            return f"sqlite:///{DEFAULT_DB_FILE}"
        return v

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if not v or not v.strip():
            return "dev_super_secret_key_change_in_production_ai_study_companion"
        return v.strip()

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_access_token_expire(cls, v: int) -> int:
        if v is None or v <= 0:
            return 60 * 24
        return v

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )


settings = Settings()


# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
