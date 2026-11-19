"""VANTYX Configuration Management.

Loads and validates application settings using Pydantic Settings.
Environment variables can override any default settings safely.
"""

from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core Application Settings
    PROJECT_NAME: str = Field(default="VANTYX", description="Project brand name")
    ENVIRONMENT: str = Field(default="development", description="Runtime environment: development | staging | production")
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Structured logging level")
    SECRET_KEY: str = Field(
        default="development-insecure-secret-key-change-in-production-32chars",
        description="Application secret key for internal token verification and signing",
    )

    # API Routing
    API_V1_PREFIX: str = Field(default="/api/v1", description="Prefix for v1 REST endpoints")
    BACKEND_HOST: str = Field(default="127.0.0.1", description="Backend bind host")
    BACKEND_PORT: int = Field(default=8000, description="Backend bind port")

    # CORS Configuration
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="Allowed CORS origins list or comma-separated string",
    )

    # PostgreSQL Database Settings
    POSTGRES_SERVER: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_USER: str = Field(default="vantyx_user", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(default="vantyx_password", description="PostgreSQL password")
    POSTGRES_DB: str = Field(default="vantyx", description="PostgreSQL database name")

    # Pre-constructed or override Database URLs
    DATABASE_URL: str = Field(
        default="",
        description="Full async connection string (e.g. postgresql+asyncpg://...)",
    )
    DATABASE_SYNC_URL: str = Field(
        default="",
        description="Full sync connection string for Alembic (e.g. postgresql://...)",
    )

    # Database Pool Settings
    DB_POOL_SIZE: int = Field(default=10, description="SQLAlchemy connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="SQLAlchemy connection pool max overflow")
    DB_POOL_TIMEOUT: int = Field(default=30, description="SQLAlchemy connection pool timeout in seconds")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def async_database_url(self) -> str:
        """Return the async database connection URL."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        """Return the synchronous database connection URL (for migrations/Alembic)."""
        if self.DATABASE_SYNC_URL:
            return self.DATABASE_SYNC_URL
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
