"""
Azure Blob Storage backend.
Supports Azure Blob Storage for Azure-based deployments.
"""

from typing import AsyncGenerator

from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import ResourceNotFoundError, AzureError
from fastapi import UploadFile

from app.config import get_settings
from app.core.exceptions import StorageException
from app.storage.base import StorageBackend

settings = get_settings()


class AzureStorageBackend(StorageBackend):
    """
    Azure Blob Storage implementation.
    
    Configured via AZURE_* environment variables.
    """
    
    def __init__(
        self,
        connection_string: str | None = None,
        container_name: str | None = None,
    ):
        """
        Initialize Azure Blob storage backend.
        
        Args:
            connection_string: Azure Storage connection string
            container_name: Blob container name
        """
        self.connection_string = connection_string or settings.AZURE_STORAGE_CONNECTION_STRING
        self.container_name = container_name or settings.AZURE_CONTAINER_NAME
        
        if not self.connection_string:
            raise StorageException(
                message="Azure connection string not configured",
                details={"required": "AZURE_STORAGE_CONNECTION_STRING"},
            )
        
        # Create blob service client
        self.blob_service_client = BlobServiceClient.from_connection_string(
            self.connection_string
        )
        
        # Ensure container exists
        self._ensure_container_exists()
    
    def _ensure_container_exists(self):
        """Create container if it doesn't exist."""
        try:
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            if not container_client.exists():
                container_client.create_container()
        except AzureError as e:
            raise StorageException(
                message=f"Failed to ensure container exists: {str(e)}",
                details={"container": self.container_name},
            )
    
    def _get_blob_client(self, path: str):
        """Get blob client for a path."""
        return self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=path,
        )
    
    async def upload(self, file: UploadFile, path: str) -> str:
        """Upload a file from an UploadFile object."""
        try:
            content = await file.read()
            content_type = file.content_type or "application/octet-stream"
            
            blob_client = self._get_blob_client(path)
            blob_client.upload_blob(
                content,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
            )
            
            return path
            
        except AzureError as e:
            raise StorageException(
                message=f"Failed to upload file to Azure: {str(e)}",
                details={"path": path, "container": self.container_name},
            )
    
    async def upload_bytes(self, data: bytes, path: str, content_type: str) -> str:
        """Upload raw bytes to storage."""
        try:
            blob_client = self._get_blob_client(path)
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
            )
            
            return path
            
        except AzureError as e:
            raise StorageException(
                message=f"Failed to upload bytes to Azure: {str(e)}",
                details={"path": path, "container": self.container_name},
            )
    
    async def download(self, path: str) -> AsyncGenerator[bytes, None]:
        """Stream download a file in chunks."""
        try:
            blob_client = self._get_blob_client(path)
            stream = blob_client.download_blob()
            
            # Read in chunks
            for chunk in stream.chunks():
                yield chunk
                
        except ResourceNotFoundError:
            raise StorageException(
                message=f"File not found: {path}",
                details={"path": path, "container": self.container_name},
            )
        except AzureError as e:
            raise StorageException(
                message=f"Failed to download file from Azure: {str(e)}",
                details={"path": path, "container": self.container_name},
            )
    
    async def download_bytes(self, path: str) -> bytes:
        """Download entire file as bytes."""
        try:
            blob_client = self._get_blob_client(path)
            stream = blob_client.download_blob()
            return stream.readall()
            
        except ResourceNotFoundError:
            raise StorageException(
                message=f"File not found: {path}",
                details={"path": path, "container": self.container_name},
            )
        except AzureError as e:
            raise StorageException(
                message=f"Failed to download file from Azure: {str(e)}",
                details={"path": path, "container": self.container_name},
            )
    
    async def delete(self, path: str) -> bool:
        """Delete a file from storage."""
        try:
            blob_client = self._get_blob_client(path)
            
            if not await self.exists(path):
                return False
            
            blob_client.delete_blob()
            return True
            
        except AzureError as e:
            raise StorageException(
                message=f"Failed to delete file from Azure: {str(e)}",
                details={"path": path, "container": self.container_name},
            )
    
    async def exists(self, path: str) -> bool:
        """Check if a file exists."""
        try:
            blob_client = self._get_blob_client(path)
            return blob_client.exists()
        except AzureError as e:
            raise StorageException(
                message=f"Failed to check file existence: {str(e)}",
                details={"path": path, "container": self.container_name},
            )
    
    async def get_size(self, path: str) -> int:
        """Get file size in bytes."""
        try:
            blob_client = self._get_blob_client(path)
            properties = blob_client.get_blob_properties()
            return properties.size
            
        except ResourceNotFoundError:
            raise StorageException(
                message=f"File not found: {path}",
                details={"path": path, "container": self.container_name},
            )
        except AzureError as e:
            raise StorageException(
                message=f"Failed to get file size: {str(e)}",
                details={"path": path, "container": self.container_name},
            )
    
    def get_url(self, path: str) -> str:
        """Get URL for file access."""
        blob_client = self._get_blob_client(path)
        return blob_client.url
