"""
Storage abstraction layer for METRO API.
Supports multiple backends: Local filesystem, S3/MinIO, Azure Blob.
"""

from app.storage.base import StorageBackend, get_mime_type, FORMAT_MIME_TYPES
from app.storage.local import LocalStorageBackend
from app.storage.s3 import S3StorageBackend
from app.storage.azure import AzureStorageBackend
from app.storage.factory import get_storage_backend, get_storage

__all__ = [
    "StorageBackend",
    "LocalStorageBackend",
    "S3StorageBackend",
    "AzureStorageBackend",
    "get_storage_backend",
    "get_storage",
    "get_mime_type",
    "FORMAT_MIME_TYPES",
]
