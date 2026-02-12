"""
FastAPI dependency injection functions.
Provides common dependencies used across endpoints.
"""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_db
from app.storage import StorageBackend, get_storage


# Type aliases for cleaner endpoint signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]
Storage = Annotated[StorageBackend, Depends(get_storage)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_response_format(request: Request) -> str:
    """
    Determine response format based on Accept header.
    
    Returns:
        "jsonld" if client accepts application/ld+json, otherwise "json"
    """
    accept = request.headers.get("accept", "application/json")
    if "application/ld+json" in accept:
        return "jsonld"
    return "json"


ResponseFormat = Annotated[str, Depends(get_response_format)]
