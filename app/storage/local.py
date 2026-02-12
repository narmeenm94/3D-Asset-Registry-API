"""
Local filesystem storage backend.
Stores files on the local filesystem for development and simple deployments.
"""

import os
from pathlib import Path
from typing import AsyncGenerator

import aiofiles
import aiofiles.os
from fastapi import UploadFile

from app.config import get_settings
from app.core.exceptions import StorageException
from app.storage.base import StorageBackend

settings = get_settings()


class LocalStorageBackend(StorageBackend):
    """
    Local filesystem storage implementation.
    
    Files are stored under the configured LOCAL_STORAGE_PATH directory.
    Suitable for development and small-scale deployments.
    """
    
    def __init__(self, base_path: str | None = None):
        """
        Initialize local storage backend.
        
        Args:
            base_path: Base directory for storage. Defaults to settings.LOCAL_STORAGE_PATH
        """
        self.base_path = Path(base_path or settings.LOCAL_STORAGE_PATH)
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_full_path(self, path: str) -> Path:
        """Get full filesystem path for a storage path."""
        return self.base_path / path
    
    async def upload(self, file: UploadFile, path: str) -> str:
        """Upload a file from an UploadFile object."""
        full_path = self._get_full_path(path)
        
        try:
            # Ensure parent directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file in chunks
            async with aiofiles.open(full_path, "wb") as f:
                while chunk := await file.read(1024 * 1024):  # 1MB chunks
                    await f.write(chunk)
            
            return path
            
        except Exception as e:
            raise StorageException(
                message=f"Failed to upload file: {str(e)}",
                details={"path": path},
            )
    
    async def upload_bytes(self, data: bytes, path: str, content_type: str) -> str:
        """Upload raw bytes to storage."""
        full_path = self._get_full_path(path)
        
        try:
            # Ensure parent directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(full_path, "wb") as f:
                await f.write(data)
            
            return path
            
        except Exception as e:
            raise StorageException(
                message=f"Failed to upload bytes: {str(e)}",
                details={"path": path},
            )
    
    async def download(self, path: str) -> AsyncGenerator[bytes, None]:
        """Stream download a file in chunks."""
        full_path = self._get_full_path(path)
        
        if not full_path.exists():
            raise StorageException(
                message=f"File not found: {path}",
                details={"path": path},
            )
        
        try:
            async with aiofiles.open(full_path, "rb") as f:
                while chunk := await f.read(1024 * 1024):  # 1MB chunks
                    yield chunk
                    
        except Exception as e:
            raise StorageException(
                message=f"Failed to download file: {str(e)}",
                details={"path": path},
            )
    
    async def download_bytes(self, path: str) -> bytes:
        """Download entire file as bytes."""
        full_path = self._get_full_path(path)
        
        if not full_path.exists():
            raise StorageException(
                message=f"File not found: {path}",
                details={"path": path},
            )
        
        try:
            async with aiofiles.open(full_path, "rb") as f:
                return await f.read()
                
        except Exception as e:
            raise StorageException(
                message=f"Failed to download file: {str(e)}",
                details={"path": path},
            )
    
    async def delete(self, path: str) -> bool:
        """Delete a file from storage."""
        full_path = self._get_full_path(path)
        
        if not full_path.exists():
            return False
        
        try:
            await aiofiles.os.remove(full_path)
            
            # Try to remove empty parent directories
            parent = full_path.parent
            while parent != self.base_path:
                try:
                    parent.rmdir()  # Only removes if empty
                    parent = parent.parent
                except OSError:
                    break
            
            return True
            
        except Exception as e:
            raise StorageException(
                message=f"Failed to delete file: {str(e)}",
                details={"path": path},
            )
    
    async def exists(self, path: str) -> bool:
        """Check if a file exists."""
        full_path = self._get_full_path(path)
        return full_path.exists()
    
    async def get_size(self, path: str) -> int:
        """Get file size in bytes."""
        full_path = self._get_full_path(path)
        
        if not full_path.exists():
            raise StorageException(
                message=f"File not found: {path}",
                details={"path": path},
            )
        
        stat = await aiofiles.os.stat(full_path)
        return stat.st_size
    
    def get_url(self, path: str) -> str:
        """Get URL/path for file access."""
        # For local storage, return the relative path
        return f"/storage/{path}"
