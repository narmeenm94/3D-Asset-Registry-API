"""
S3-compatible storage backend.
Supports AWS S3 and S3-compatible services like MinIO.
"""

import io
from typing import AsyncGenerator

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.config import get_settings
from app.core.exceptions import StorageException
from app.storage.base import StorageBackend

settings = get_settings()


class S3StorageBackend(StorageBackend):
    """
    S3-compatible object storage implementation.
    
    Supports AWS S3 and S3-compatible services like MinIO.
    Configured via S3_* environment variables.
    """
    
    def __init__(
        self,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket_name: str | None = None,
        region: str | None = None,
    ):
        """
        Initialize S3 storage backend.
        
        Args:
            endpoint_url: S3 endpoint URL (for MinIO, custom S3-compatible services)
            access_key: AWS access key ID
            secret_key: AWS secret access key
            bucket_name: S3 bucket name
            region: AWS region
        """
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL
        self.access_key = access_key or settings.S3_ACCESS_KEY
        self.secret_key = secret_key or settings.S3_SECRET_KEY
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.region = region or settings.S3_REGION
        
        # Create S3 client
        config = Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        )
        
        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=config,
        )
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                try:
                    if self.region and self.region != "us-east-1":
                        self.client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={"LocationConstraint": self.region},
                        )
                    else:
                        self.client.create_bucket(Bucket=self.bucket_name)
                except ClientError as create_error:
                    raise StorageException(
                        message=f"Failed to create bucket: {str(create_error)}",
                        details={"bucket": self.bucket_name},
                    )
    
    async def upload(self, file: UploadFile, path: str) -> str:
        """Upload a file from an UploadFile object."""
        try:
            content = await file.read()
            content_type = file.content_type or "application/octet-stream"
            
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=path,
                Body=content,
                ContentType=content_type,
            )
            
            return path
            
        except ClientError as e:
            raise StorageException(
                message=f"Failed to upload file to S3: {str(e)}",
                details={"path": path, "bucket": self.bucket_name},
            )
    
    async def upload_bytes(self, data: bytes, path: str, content_type: str) -> str:
        """Upload raw bytes to storage."""
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=path,
                Body=data,
                ContentType=content_type,
            )
            
            return path
            
        except ClientError as e:
            raise StorageException(
                message=f"Failed to upload bytes to S3: {str(e)}",
                details={"path": path, "bucket": self.bucket_name},
            )
    
    async def download(self, path: str) -> AsyncGenerator[bytes, None]:
        """Stream download a file in chunks."""
        try:
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=path,
            )
            
            body = response["Body"]
            
            # Read in chunks
            while chunk := body.read(1024 * 1024):  # 1MB chunks
                yield chunk
            
            body.close()
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "NoSuchKey":
                raise StorageException(
                    message=f"File not found: {path}",
                    details={"path": path, "bucket": self.bucket_name},
                )
            raise StorageException(
                message=f"Failed to download file from S3: {str(e)}",
                details={"path": path, "bucket": self.bucket_name},
            )
    
    async def download_bytes(self, path: str) -> bytes:
        """Download entire file as bytes."""
        try:
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=path,
            )
            
            return response["Body"].read()
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "NoSuchKey":
                raise StorageException(
                    message=f"File not found: {path}",
                    details={"path": path, "bucket": self.bucket_name},
                )
            raise StorageException(
                message=f"Failed to download file from S3: {str(e)}",
                details={"path": path, "bucket": self.bucket_name},
            )
    
    async def delete(self, path: str) -> bool:
        """Delete a file from storage."""
        try:
            # Check if exists first
            if not await self.exists(path):
                return False
            
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=path,
            )
            
            return True
            
        except ClientError as e:
            raise StorageException(
                message=f"Failed to delete file from S3: {str(e)}",
                details={"path": path, "bucket": self.bucket_name},
            )
    
    async def exists(self, path: str) -> bool:
        """Check if a file exists."""
        try:
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=path,
            )
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                return False
            raise StorageException(
                message=f"Failed to check file existence: {str(e)}",
                details={"path": path, "bucket": self.bucket_name},
            )
    
    async def get_size(self, path: str) -> int:
        """Get file size in bytes."""
        try:
            response = self.client.head_object(
                Bucket=self.bucket_name,
                Key=path,
            )
            return response["ContentLength"]
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                raise StorageException(
                    message=f"File not found: {path}",
                    details={"path": path, "bucket": self.bucket_name},
                )
            raise StorageException(
                message=f"Failed to get file size: {str(e)}",
                details={"path": path, "bucket": self.bucket_name},
            )
    
    def get_url(self, path: str) -> str:
        """Generate a presigned URL for file access."""
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": path,
                },
                ExpiresIn=3600,  # 1 hour
            )
            return url
        except ClientError:
            # Fallback to direct URL construction
            if self.endpoint_url:
                return f"{self.endpoint_url}/{self.bucket_name}/{path}"
            return f"s3://{self.bucket_name}/{path}"
