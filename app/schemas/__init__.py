"""
Pydantic schemas for request/response validation.
Aligned with D9.1 Section 4.2 Data Contracts.
"""

from app.schemas.asset import (
    AssetBase,
    AssetCreate,
    AssetUpdate,
    AssetTagsUpdate,
    AssetResponse,
    AssetListResponse,
    AssetVersionResponse,
    AssetSearchParams,
    AssetAccessControl,
    AssetExtendedMetadata,
    AssetProvenance,
)
from app.schemas.tag import TagResponse, TagListResponse
from app.schemas.error import ErrorResponse, ValidationErrorResponse

__all__ = [
    # Asset schemas
    "AssetBase",
    "AssetCreate",
    "AssetUpdate",
    "AssetTagsUpdate",
    "AssetResponse",
    "AssetListResponse",
    "AssetVersionResponse",
    "AssetSearchParams",
    "AssetAccessControl",
    "AssetExtendedMetadata",
    "AssetProvenance",
    # Tag schemas
    "TagResponse",
    "TagListResponse",
    # Error schemas
    "ErrorResponse",
    "ValidationErrorResponse",
]
