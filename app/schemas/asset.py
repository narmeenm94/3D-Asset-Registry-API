"""
Pydantic schemas for Asset request/response validation.
Aligned with D9.1 Section 4.2 Data Contracts and Section 4.2.2 Validation Rules.
"""

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.asset import AccessLevel, AssetFormat


# ===================
# Base Schemas
# ===================

class AssetBase(BaseModel):
    """Base asset properties shared across schemas."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable asset name (1-100 chars, alphanumeric + -_)",
        examples=["CYP3A4_Molecule_vdw"],
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Detailed asset description (0-500 chars)",
    )
    format: AssetFormat = Field(
        ...,
        description="Primary file format",
    )
    tri_count: int = Field(
        default=0,
        ge=0,
        le=10_000_000,
        description="Triangle/polygon count (0-10,000,000)",
    )
    use_case: str | None = Field(
        default=None,
        max_length=50,
        description="Associated DTRIP4H use case (UC2, UC3, UC4, UC5)",
        examples=["UC2", "UC3"],
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name contains only allowed characters."""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Name must contain only alphanumeric characters, underscores, and hyphens")
        return v


class AssetAccessControl(BaseModel):
    """Access control properties for assets."""
    
    access_level: AccessLevel = Field(
        default=AccessLevel.PRIVATE,
        description="Asset permission level",
    )
    authorized_users: list[str] | None = Field(
        default=None,
        description="Array of user IDs with explicit access",
    )
    authorized_institutions: list[str] | None = Field(
        default=None,
        description="Array of institution codes with access",
    )
    embargo_until: datetime | None = Field(
        default=None,
        description="Embargo expiration timestamp",
    )
    license: str | None = Field(
        default=None,
        max_length=100,
        description="License identifier (e.g., CC-BY-4.0)",
    )
    attribution_required: bool = Field(
        default=False,
        description="Whether attribution is mandatory",
    )


class AssetLineage(BaseModel):
    """Lineage and derivation properties from RDF Document Annex A."""
    
    lineage_id: str | None = Field(
        default=None,
        max_length=36,
        description="Stable UUID grouping all versions of the same logical asset across nodes/URLs",
    )
    derived_from_asset: list[str] | str | None = Field(
        default=None,
        description="URI(s) of parent asset/version when this is a fork/derivative",
    )


class AssetExtendedMetadata(BaseModel):
    """Extended metadata from RDF Document Section 4."""
    
    lod_levels: int | None = Field(
        default=None,
        ge=1,
        description="Number of level-of-detail variants",
    )
    material_properties: dict[str, Any] | None = Field(
        default=None,
        description='Material info: {"hasTextures": true, "materialCount": 5}',
    )
    bounding_box: dict[str, Any] | None = Field(
        default=None,
        description='3D bounds: {"min": {"x": 0, "y": 0, "z": 0}, "max": {"x": 10, "y": 8, "z": 12}}',
    )
    quality_metrics: dict[str, Any] | None = Field(
        default=None,
        description='Quality info: {"meshQuality": "high", "topologyValidated": true}',
    )
    scientific_domain: str | None = Field(
        default=None,
        max_length=100,
        description="Scientific domain classification",
    )
    source_data_format: str | None = Field(
        default=None,
        max_length=50,
        description="Original input format (csv, pdb, nc)",
    )
    processing_parameters: dict[str, Any] | None = Field(
        default=None,
        description="Generation parameters used",
    )
    project_phase: str | None = Field(
        default=None,
        max_length=50,
        description="Project phase (e.g., prototype, production, archived)",
    )
    theme: dict[str, Any] | None = Field(
        default=None,
        description='DCAT theme classification: {"scheme": "...", "code": "..."}',
    )
    access_scope: list[str] | None = Field(
        default=None,
        description="Array of OAuth scopes required for access",
    )
    geo_restrictions: list[str] | None = Field(
        default=None,
        description="Array of geographic restriction codes (ISO 3166)",
    )
    usage_constraints: str | None = Field(
        default=None,
        description="Usage constraints/limitations description",
    )
    visualization_capabilities: dict[str, Any] | None = Field(
        default=None,
        description='Visualization info: {"supportsVR": true, "supportsAR": false}',
    )
    usage_guidelines: dict[str, Any] | None = Field(
        default=None,
        description='Usage instructions: {"recommended_viewer": "...", "notes": "..."}',
    )
    deployment_notes: str | None = Field(
        default=None,
        description="Notes about deployment or integration requirements",
    )


class AssetProvenance(BaseModel):
    """Provenance information for asset generation."""
    
    tool: str | None = Field(
        default=None,
        description="Generation tool name and version",
        examples=["METRO ADMET Visualizer v2.0.1"],
    )
    source_data: list[str] | None = Field(
        default=None,
        description="Source data file references",
    )


# ===================
# Request Schemas
# ===================

class AssetCreate(AssetBase, AssetAccessControl, AssetLineage, AssetExtendedMetadata):
    """Schema for creating a new asset (POST /assets)."""
    
    tags: list[str] = Field(
        default=[],
        max_length=20,
        description="Classification and discovery tags (0-20 tags)",
    )
    provenance: AssetProvenance | None = Field(
        default=None,
        description="Generation provenance information",
    )
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate each tag is 1-50 characters."""
        for tag in v:
            if not 1 <= len(tag) <= 50:
                raise ValueError(f"Each tag must be 1-50 characters, got: '{tag}'")
        return v


class AssetUpdate(BaseModel):
    """Schema for updating asset metadata (PATCH /assets/{id})."""
    
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Human-readable asset name",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Asset description",
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Validate name if provided."""
        if v is not None and not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Name must contain only alphanumeric characters, underscores, and hyphens")
        return v
    
    model_config = ConfigDict(extra="forbid")


class AssetTagsUpdate(BaseModel):
    """Schema for replacing asset tags (PUT /assets/{id}/tags)."""
    
    tags: list[str] = Field(
        ...,
        max_length=20,
        description="New tag set for the asset",
    )
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate each tag is 1-50 characters."""
        for tag in v:
            if not 1 <= len(tag) <= 50:
                raise ValueError(f"Each tag must be 1-50 characters, got: '{tag}'")
        return v


# ===================
# Response Schemas
# ===================

class TagResponse(BaseModel):
    """Tag information in asset responses."""
    
    name: str
    category: str
    
    model_config = ConfigDict(from_attributes=True)


class AssetResponse(BaseModel):
    """Standard JSON response for a single asset."""
    
    id: str
    name: str
    description: str
    format: AssetFormat
    tri_count: int = Field(alias="triCount")
    tags: list[str]
    version: int
    uploader: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    provenance: dict[str, Any] | None = None
    use_case: str | None = Field(default=None, alias="useCase")
    file_size: int = Field(alias="fileSize")
    
    # Access control
    access_level: AccessLevel = Field(alias="accessLevel")
    owner_id: str = Field(alias="ownerId")
    owner_institution: str = Field(alias="ownerInstitution")
    license: str | None = None
    attribution_required: bool = Field(alias="attributionRequired")
    
    # Lineage & Derivation
    lineage_id: str | None = Field(default=None, alias="lineageId")
    derived_from_asset: list[str] | str | None = Field(default=None, alias="derivedFromAsset")
    
    # Extended metadata (optional)
    lod_levels: int | None = Field(default=None, alias="lodLevels")
    material_properties: dict[str, Any] | None = Field(default=None, alias="materialProperties")
    bounding_box: dict[str, Any] | None = Field(default=None, alias="boundingBox")
    quality_metrics: dict[str, Any] | None = Field(default=None, alias="qualityMetrics")
    scientific_domain: str | None = Field(default=None, alias="scientificDomain")
    source_data_format: str | None = Field(default=None, alias="sourceDataFormat")
    processing_parameters: dict[str, Any] | None = Field(default=None, alias="processingParameters")
    project_phase: str | None = Field(default=None, alias="projectPhase")
    theme: dict[str, Any] | None = Field(default=None, alias="theme")
    access_scope: list[str] | None = Field(default=None, alias="accessScope")
    geo_restrictions: list[str] | None = Field(default=None, alias="geoRestrictions")
    usage_constraints: str | None = Field(default=None, alias="usageConstraints")
    visualization_capabilities: dict[str, Any] | None = Field(default=None, alias="visualizationCapabilities")
    usage_guidelines: dict[str, Any] | None = Field(default=None, alias="usageGuidelines")
    deployment_notes: str | None = Field(default=None, alias="deploymentNotes")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class AssetListResponse(BaseModel):
    """Paginated list of assets."""
    
    items: list[AssetResponse]
    total: int
    page: int
    size: int
    pages: int


class AssetVersionResponse(BaseModel):
    """Response for asset version information."""
    
    id: str
    version_number: int = Field(alias="versionNumber")
    file_size: int = Field(alias="fileSize")
    checksum: str
    changes: str | None = None
    created_at: datetime = Field(alias="createdAt")
    created_by: str = Field(alias="createdBy")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


# ===================
# Query Parameters
# ===================

class AssetSearchParams(BaseModel):
    """Query parameters for asset search (GET /assets)."""
    
    q: str | None = Field(
        default=None,
        description="Full-text search query",
    )
    tags: str | None = Field(
        default=None,
        description="Comma-separated tag filter",
    )
    format: AssetFormat | None = Field(
        default=None,
        description="File format filter",
    )
    min_tris: int | None = Field(
        default=None,
        ge=0,
        alias="minTris",
        description="Minimum triangle count",
    )
    max_tris: int | None = Field(
        default=None,
        le=10_000_000,
        alias="maxTris",
        description="Maximum triangle count",
    )
    use_case: str | None = Field(
        default=None,
        alias="useCase",
        description="Use case filter (UC2-UC5)",
    )
    access_level: AccessLevel | None = Field(
        default=None,
        alias="accessLevel",
        description="Access level filter",
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Page number",
    )
    size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Page size (max 100)",
    )
    
    model_config = ConfigDict(populate_by_name=True)
