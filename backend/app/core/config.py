"""VANTYX Configuration Management.

Loads and validates application settings using Pydantic Settings.
Environment variables can override any default settings safely.
Supports both PostgreSQL (production/docker) and resilient local SQLite fallback.
"""

import os
import socket
from pathlib import Path
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_port_open(host: str, port: int, timeout: float = 0.2) -> bool:
    """Quick check to see if a TCP port is responding."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


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

    # Storage & Data Paths
    DATA_DIR: str = Field(default="./data", description="Base data directory for media and database")
    MEDIA_DIR: str = Field(default="./data/media", description="Directory for video rendering and clip cache")
    EXPORT_DIR: str = Field(default="./data/exports", description="Directory for completed 9:16 vertical shorts")

    # Database Settings
    DB_DIALECT: str = Field(
        default="auto",
        description="Database dialect mode: auto | postgresql | sqlite",
    )
    POSTGRES_SERVER: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_USER: str = Field(default="vantyx_user", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(default="vantyx_password", description="PostgreSQL password")
    POSTGRES_DB: str = Field(default="vantyx", description="PostgreSQL database name")

    # Pre-constructed or override Database URLs
    DATABASE_URL: str = Field(
        default="",
        description="Full async connection string (e.g. postgresql+asyncpg://... or sqlite+aiosqlite:///...)",
    )
    DATABASE_SYNC_URL: str = Field(
        default="",
        description="Full sync connection string for Alembic (e.g. postgresql://... or sqlite:///...)",
    )

    # Database Pool Settings
    DB_POOL_SIZE: int = Field(default=10, description="SQLAlchemy connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="SQLAlchemy connection pool max overflow")
    DB_POOL_TIMEOUT: int = Field(default=30, description="SQLAlchemy connection pool timeout in seconds")

    # External Provider Credentials (Optional / Configurable)
    YOUTUBE_API_KEY: str = Field(default="", description="YouTube Data API v3 key (optional, public feeds used as fallback)")
    YOUTUBE_CLIENT_ID: str = Field(default="", description="Google OAuth2 Client ID for publishing")
    YOUTUBE_CLIENT_SECRET: str = Field(default="", description="Google OAuth2 Client Secret for publishing")
    YOUTUBE_REDIRECT_URI: str = Field(default="http://localhost:5173/distribution/oauth/callback", description="OAuth callback redirect URI")
    MOCK_YOUTUBE_PUBLISHING: bool = Field(default=False, description="Enable simulated publishing provider for safe offline test execution")
    GEMINI_API_KEY: str = Field(default="", description="Gemini API Key for multimodal scene analysis")

    # Channel & Pipeline Configuration
    PRIMARY_CHANNEL_NAME: str = Field(default="Astro Rebel", description="Target YouTube publishing channel")
    TARGET_SHORTS_PER_DAY: int = Field(default=4, description="Target daily scheduled shorts count")
    TIMEZONE: str = Field(default="Asia/Kolkata", description="Platform primary scheduling timezone")
    DEFAULT_PUBLISH_SLOTS: List[str] = Field(
        default=["09:00", "13:00", "17:00", "21:00"],
        description="Daily Shorts publication release schedule in local timezone",
    )

    # Analytics & Feedback Engine Settings
    MOCK_YOUTUBE_ANALYTICS: bool = Field(default=True, description="Enable simulated analytics provider for safe offline test execution")
    ANALYTICS_FEEDBACK_ENABLED: bool = Field(default=False, description="Enable closed-loop feedback engine into moment selection")
    ANALYTICS_FEEDBACK_MAX_IMPACT: float = Field(default=0.15, description="Maximum bounded percentage impact (+/- 15%) from analytics feedback")
    ANALYTICS_MIN_SAMPLE_SIZE: int = Field(default=3, description="Minimum sample size required to apply feedback adjustments")
    ANALYTICS_REPORTING_DELAY_HOURS: int = Field(default=48, description="Standard processing delay window for YouTube Analytics API")

    # Orchestration, Redis & Background Worker Settings
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL for queue coordination")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0", description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/1", description="Celery result backend URL")
    CELERY_ALWAYS_EAGER: bool = Field(default=True, description="Execute Celery tasks in-process for test environments and zero-redis fallback")
    ORCHESTRATION_ENABLED: bool = Field(default=False, description="Master automation toggle (requires explicit operator activation)")
    DAILY_PIPELINE_RUN_TIME: str = Field(default="06:00", description="Daily workflow trigger time in Asia/Kolkata timezone")
    MAX_CONCURRENT_RENDERS: int = Field(default=2, description="Maximum concurrent video render jobs")
    WORKFLOW_RETRY_LIMIT: int = Field(default=3, description="Maximum retries for recoverable workflow steps")

    # Media & Rendering Tools
    FFMPEG_PATH: Optional[str] = Field(
        default=None,
        description="Explicit path to ffmpeg binary. If None, resolves via imageio-ffmpeg or system PATH.",
    )

    def get_ffmpeg_executable(self) -> str:
        """Resolve the active FFmpeg binary path across local and cloud environments."""
        if self.FFMPEG_PATH and os.path.exists(self.FFMPEG_PATH):
            return self.FFMPEG_PATH
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if os.path.exists(exe):
                return exe
        except Exception:
            pass
        import shutil
        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg:
            return sys_ffmpeg
        raise RuntimeError("FFmpeg executable not found. Ensure imageio-ffmpeg is installed or set FFMPEG_PATH.")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    def _get_sqlite_paths(self) -> tuple[str, str]:
        data_path = Path(self.DATA_DIR).resolve()
        data_path.mkdir(parents=True, exist_ok=True)
        db_file = (data_path / "vantyx.db").as_posix()
        return f"sqlite+aiosqlite:///{db_file}", f"sqlite:///{db_file}"

    @property
    def async_database_url(self) -> str:
        """Return the async database connection URL."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.DB_DIALECT == "sqlite":
            async_url, _ = self._get_sqlite_paths()
            return async_url
        if self.DB_DIALECT == "postgresql":
            return (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        # auto mode: check if postgres is reachable
        if _is_port_open(self.POSTGRES_SERVER, self.POSTGRES_PORT):
            return (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        async_url, _ = self._get_sqlite_paths()
        return async_url

    @property
    def sync_database_url(self) -> str:
        """Return the synchronous database connection URL (for migrations/Alembic)."""
        if self.DATABASE_SYNC_URL:
            return self.DATABASE_SYNC_URL
        if self.DB_DIALECT == "sqlite":
            _, sync_url = self._get_sqlite_paths()
            return sync_url
        if self.DB_DIALECT == "postgresql":
            return (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        if _is_port_open(self.POSTGRES_SERVER, self.POSTGRES_PORT):
            return (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        _, sync_url = self._get_sqlite_paths()
        return sync_url


settings = Settings()
