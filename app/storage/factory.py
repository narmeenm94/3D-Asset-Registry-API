"""
Storage backend factory.
Provides configuration-driven backend selection.
"""

from functools import lru_cache

from app.config import get_settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorageBackend
from app.storage.s3 import S3StorageBackend
from app.storage.azure import AzureStorageBackend

settings = get_settings()


@lru_cache
def get_storage_backend() -> StorageBackend:
    """
    Get the configured storage backend.
    
    Uses LRU cache to ensure only one instance is created.
    Backend selection is based on STORAGE_BACKEND setting.
    
    Returns:
        Configured StorageBackend instance
        
    Raises:
        ValueError: If unknown storage backend is configured
    """
    backend = settings.STORAGE_BACKEND.lower()
    
    if backend == "local":
        return LocalStorageBackend()
    elif backend == "s3":
        return S3StorageBackend()
    elif backend == "azure":
        return AzureStorageBackend()
    else:
        raise ValueError(f"Unknown storage backend: {backend}")


def get_storage() -> StorageBackend:
    """
    Dependency function for FastAPI.
    
    Usage:
        @app.post("/upload")
        async def upload(storage: StorageBackend = Depends(get_storage)):
            ...
    """
    return get_storage_backend()
