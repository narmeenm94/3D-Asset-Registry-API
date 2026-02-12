"""
Tests for storage backends.
"""

import pytest
from pathlib import Path

from app.storage.local import LocalStorageBackend


class TestLocalStorageBackend:
    """Tests for local filesystem storage."""
    
    @pytest.fixture
    def storage(self, tmp_path) -> LocalStorageBackend:
        """Create a local storage backend for testing."""
        return LocalStorageBackend(base_path=str(tmp_path))
    
    @pytest.mark.asyncio
    async def test_upload_bytes(self, storage: LocalStorageBackend):
        """Test uploading bytes."""
        content = b"test file content"
        path = "test/file.txt"
        
        result = await storage.upload_bytes(content, path, "text/plain")
        
        assert result == path
        assert await storage.exists(path)
    
    @pytest.mark.asyncio
    async def test_download_bytes(self, storage: LocalStorageBackend):
        """Test downloading bytes."""
        content = b"test file content"
        path = "test/file.txt"
        await storage.upload_bytes(content, path, "text/plain")
        
        result = await storage.download_bytes(path)
        
        assert result == content
    
    @pytest.mark.asyncio
    async def test_download_streaming(self, storage: LocalStorageBackend):
        """Test streaming download."""
        content = b"test file content"
        path = "test/file.txt"
        await storage.upload_bytes(content, path, "text/plain")
        
        chunks = []
        async for chunk in storage.download(path):
            chunks.append(chunk)
        
        result = b"".join(chunks)
        assert result == content
    
    @pytest.mark.asyncio
    async def test_exists(self, storage: LocalStorageBackend):
        """Test file existence check."""
        path = "test/file.txt"
        
        assert not await storage.exists(path)
        
        await storage.upload_bytes(b"content", path, "text/plain")
        
        assert await storage.exists(path)
    
    @pytest.mark.asyncio
    async def test_delete(self, storage: LocalStorageBackend):
        """Test file deletion."""
        content = b"test content"
        path = "test/file.txt"
        await storage.upload_bytes(content, path, "text/plain")
        
        result = await storage.delete(path)
        
        assert result is True
        assert not await storage.exists(path)
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, storage: LocalStorageBackend):
        """Test deleting non-existent file."""
        result = await storage.delete("nonexistent/file.txt")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_size(self, storage: LocalStorageBackend):
        """Test getting file size."""
        content = b"test file content with some length"
        path = "test/file.txt"
        await storage.upload_bytes(content, path, "text/plain")
        
        size = await storage.get_size(path)
        
        assert size == len(content)
    
    @pytest.mark.asyncio
    async def test_get_url(self, storage: LocalStorageBackend):
        """Test getting file URL."""
        path = "test/file.txt"
        
        url = storage.get_url(path)
        
        assert url == f"/storage/{path}"
    
    @pytest.mark.asyncio
    async def test_nested_directories(self, storage: LocalStorageBackend):
        """Test creating nested directory structure."""
        content = b"nested content"
        path = "deep/nested/path/to/file.txt"
        
        await storage.upload_bytes(content, path, "text/plain")
        
        assert await storage.exists(path)
        downloaded = await storage.download_bytes(path)
        assert downloaded == content
