"""
Configuration management for METRO API.
Uses pydantic-settings for environment-based configuration.
Aligned with D9.1 Architecture Design Document Section 8.5.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "METRO 3D Asset Registry"
    DEBUG: bool = False

    # Database (PostgreSQL - D9.1 Section 3.2)
    DATABASE_URL: str = "postgresql+asyncpg://metro:metro@localhost:5432/metro"
    
    # SQLite fallback for local development (auto-detected if PostgreSQL unavailable)
    USE_SQLITE_FALLBACK: bool = True
    SQLITE_FALLBACK_URL: str = "sqlite+aiosqlite:///./metro_dev.db"

    # Storage Backend Selection
    STORAGE_BACKEND: Literal["local", "s3", "azure"] = "local"

    # Local Storage Settings
    LOCAL_STORAGE_PATH: str = "./storage"

    # S3/MinIO Settings (D9.1 Section 8.5.2)
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_BUCKET_NAME: str = "metro-assets"
    S3_REGION: str = "us-east-1"

    # Azure Blob Settings
    AZURE_STORAGE_CONNECTION_STRING: str | None = None
    AZURE_CONTAINER_NAME: str = "metro-assets"

    # DDTE Authentication (D9.1 Section 4.1)
    DDTE_JWKS_URL: str = "http://localhost:8080/.well-known/jwks.json"
    DDTE_ISSUER: str = "https://auth.ddte.eu"
    DDTE_AUDIENCE: str = "dtrip4h-asset-libraries"

    # Development Mode - bypasses JWT validation for local testing
    DEV_MODE: bool = True
    DEV_USER_ID: str = "dev-user-001"
    DEV_USER_EMAIL: str = "developer@metropolia.fi"
    DEV_USER_INSTITUTION: str = "METRO_Finland"

    # File Upload Limits (D9.1 Section 4.2.2)
    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024  # 500MB

    # Logging
    LOG_LEVEL: str = "INFO"

    # JWKS Cache TTL in seconds
    JWKS_CACHE_TTL: int = 3600  # 1 hour

    # Federated Infrastructure (Annex A / D9.1 Section 8.3)
    HOSTING_NODE: str = "local-dev-node"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()
