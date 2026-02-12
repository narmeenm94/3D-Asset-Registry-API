"""
Pytest configuration and fixtures for METRO API tests.
"""

import asyncio
import os
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import Settings
from app.db.base import Base
from app.main import app
from app.db.session import get_db
from app.storage import LocalStorageBackend, get_storage

# Test database URL (SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Get test settings."""
    return Settings(
        DATABASE_URL=TEST_DATABASE_URL,
        STORAGE_BACKEND="local",
        LOCAL_STORAGE_PATH="./test_storage",
        DEV_MODE=True,
        DEV_USER_ID="test-user-001",
        DEV_USER_EMAIL="test@metropolia.fi",
        DEV_USER_INSTITUTION="METRO_Finland",
    )


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()
    
    # Cleanup test database file
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def test_storage(tmp_path) -> LocalStorageBackend:
    """Create a test storage backend."""
    storage = LocalStorageBackend(base_path=str(tmp_path / "storage"))
    return storage


@pytest_asyncio.fixture(scope="function")
async def client(db_session, test_storage) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client."""
    
    async def override_get_db():
        yield db_session
    
    def override_get_storage():
        return test_storage
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage] = override_get_storage
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_asset_data() -> dict[str, Any]:
    """Sample asset data for testing."""
    return {
        "name": "test_molecule",
        "description": "A test molecule asset",
        "format": "gltf",
        "triCount": 1000,
        "tags": "UC2,molecule,test",
        "useCase": "UC2",
        "accessLevel": "consortium",
    }


@pytest.fixture
def sample_file_content() -> bytes:
    """Sample file content for testing uploads."""
    return b"fake glTF binary content for testing"


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Authorization headers for authenticated requests."""
    # In dev mode, no real token needed
    return {"Authorization": "Bearer dev-token"}
