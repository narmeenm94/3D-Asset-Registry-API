"""
Abstract storage backend interface.
Defines the contract for all storage implementations.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator

from fastapi import UploadFile


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.
    
    All storage implementations (Local, S3, Azure) must implement
    these methods to ensure consistent behavior across backends.
    """
    
    @abstractmethod
    async def upload(self, file: UploadFile, path: str) -> str:
        """
        Upload a file to storage.
        
        Args:
            file: FastAPI UploadFile object
            path: Destination path in storage (e.g., "assets/{id}/v1/file.glb")
            
        Returns:
            The storage path where the file was saved
            
        Raises:
            StorageException: If upload fails
        """
        pass
    
    @abstractmethod
    async def upload_bytes(self, data: bytes, path: str, content_type: str) -> str:
        """
        Upload raw bytes to storage.
        
        Args:
            data: Raw file bytes
            path: Destination path in storage
            content_type: MIME type of the content
            
        Returns:
            The storage path where the file was saved
            
        Raises:
            StorageException: If upload fails
        """
        pass
    
    @abstractmethod
    async def download(self, path: str) -> AsyncGenerator[bytes, None]:
        """
        Stream download a file from storage.
        
        Args:
            path: Path to the file in storage
            
        Yields:
            File content in chunks
            
        Raises:
            StorageException: If file not found or download fails
        """
        pass
    
    @abstractmethod
    async def download_bytes(self, path: str) -> bytes:
        """
        Download entire file as bytes.
        
        Args:
            path: Path to the file in storage
            
        Returns:
            Complete file content as bytes
            
        Raises:
            StorageException: If file not found or download fails
        """
        pass
    
    @abstractmethod
    async def delete(self, path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            path: Path to the file in storage
            
        Returns:
            True if deleted successfully, False if file didn't exist
            
        Raises:
            StorageException: If deletion fails for other reasons
        """
        pass
    
    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_size(self, path: str) -> int:
        """
        Get the size of a file in storage.
        
        Args:
            path: Path to the file
            
        Returns:
            File size in bytes
            
        Raises:
            StorageException: If file not found
        """
        pass
    
    @abstractmethod
    def get_url(self, path: str) -> str:
        """
        Get a URL for accessing the file.
        
        For local storage, this returns a relative path.
        For cloud storage, this may return a signed URL.
        
        Args:
            path: Path to the file
            
        Returns:
            URL or path to access the file
        """
        pass


# MIME type mapping for supported formats
FORMAT_MIME_TYPES = {
    "gltf": "model/gltf+json",
    "glb": "model/gltf-binary",
    "usdz": "model/vnd.usdz+zip",
    "blend": "application/octet-stream",
    "fbx": "application/octet-stream",
    "obj": "model/obj",
    "stl": "model/stl",
    "ply": "application/x-ply",
}


def get_mime_type(format: str) -> str:
    """Get MIME type for a file format."""
    return FORMAT_MIME_TYPES.get(format.lower(), "application/octet-stream")
