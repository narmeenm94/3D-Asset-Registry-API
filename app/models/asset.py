"""
Asset and AssetVersion SQLAlchemy models.
Aligned with D9.1 Section 5.1 Asset Entity Specification.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    BigInteger,
    Text,
    JSON,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.tag import Tag


class AssetFormat(str, enum.Enum):
    """Supported 3D asset file formats per D9.1 Section 4.2.1."""
    GLTF = "gltf"
    GLB = "glb"
    USDZ = "usdz"
    BLEND = "blend"
    FBX = "fbx"
    OBJ = "obj"
    STL = "stl"
    PLY = "ply"


class AccessLevel(str, enum.Enum):
    """
    Asset permission levels per D9.1 Section 8.4.2.
    Hierarchical from most restrictive to most open.
    """
    PRIVATE = "private"              # Only owner can access
    GROUP = "group"                  # Authorized users/institutions
    INSTITUTION = "institution"      # Same institution members
    CONSORTIUM = "consortium"        # All DTRIP4H members
    APPROVAL_REQUIRED = "approval_required"  # Explicit approval needed
    PUBLIC = "public"                # Any authenticated user


class Asset(Base):
    """
    3D Asset entity model.
    
    Combines core properties (D9.1 Section 5.1.1), provenance properties
    (D9.1 Section 5.1.2), access control properties (D9.1 Section 8.4.2),
    and extended metadata from the RDF Document.
    """
    __tablename__ = "assets"

    # ===================
    # Core Properties (D9.1 Section 5.1.1)
    # ===================
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="Globally unique identifier",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Human-readable asset name (1-100 chars)",
    )
    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="",
        comment="Detailed asset description (0-500 chars)",
    )
    format: Mapped[AssetFormat] = mapped_column(
        Enum(AssetFormat),
        nullable=False,
        index=True,
        comment="Primary file format",
    )
    tri_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Triangle/polygon count (0-10,000,000)",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Current version number",
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Storage reference path",
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="File size in bytes",
    )
    checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 hash of file",
    )

    # ===================
    # Provenance Properties (D9.1 Section 5.1.2)
    # ===================
    uploader: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="User identifier from DDTE token (sub claim)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Asset creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last modification timestamp",
    )
    provenance: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment='Generation tool and source data: {"tool": "...", "sourceData": [...]}',
    )
    use_case: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Associated DTRIP4H use case (UC2, UC3, UC4, UC5)",
    )

    # ===================
    # Access Control Properties (D9.1 Section 8.4.2 & RDF Document)
    # ===================
    access_level: Mapped[AccessLevel] = mapped_column(
        Enum(AccessLevel),
        nullable=False,
        default=AccessLevel.PRIVATE,
        index=True,
        comment="Asset permission level",
    )
    owner_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Owner user identifier",
    )
    owner_institution: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Owner institution code (e.g., METRO_Finland)",
    )
    authorized_users: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="Array of user IDs with explicit access",
    )
    authorized_institutions: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="Array of institution codes with access",
    )
    embargo_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Embargo expiration timestamp",
    )
    approval_workflow: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="Approval process configuration",
    )
    license: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="License identifier (e.g., CC-BY-4.0)",
    )
    attribution_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether attribution is mandatory",
    )

    # ===================
    # Lineage & Derivation (RDF Document - Annex A)
    # ===================
    lineage_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
        comment="Stable UUID grouping all versions of the same logical asset across nodes/URLs",
    )
    derived_from_asset: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="URI(s) of parent asset/version when this is a fork/derivative",
    )

    # ===================
    # Extended Metadata (RDF Document Section 4)
    # ===================
    lod_levels: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of level-of-detail variants",
    )
    material_properties: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment='Material info: {"hasTextures": true, "materialCount": 5, "supportsPBR": true}',
    )
    bounding_box: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment='3D dimensions: {"x": 10.5, "y": 8.2, "z": 12.1}',
    )
    quality_metrics: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment='Quality info: {"meshQuality": "high", "topologyValidated": true}',
    )
    scientific_domain: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Scientific domain (pharmaceutical-sciences, neuroscience, etc.)",
    )
    source_data_format: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Original input format (csv, pdb, nc)",
    )
    processing_parameters: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="Generation parameters used",
    )

    # ===================
    # Additional RDF Properties (Annex A)
    # ===================
    project_phase: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Project phase (e.g., prototype, production, archived)",
    )
    theme: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment='DCAT theme classification: {"scheme": "...", "code": "..."}',
    )
    access_scope: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="Array of OAuth scopes required for access",
    )
    geo_restrictions: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment="Array of geographic restriction codes (ISO 3166)",
    )
    usage_constraints: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Usage constraints/limitations description",
    )
    visualization_capabilities: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment='Visualization info: {"supportsVR": true, "supportsAR": false, ...}',
    )
    usage_guidelines: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
        comment='Usage instructions: {"recommended_viewer": "...", "notes": "..."}',
    )
    deployment_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Notes about deployment or integration requirements",
    )

    # ===================
    # Relationships
    # ===================
    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary="asset_tags",
        back_populates="assets",
        lazy="selectin",
    )
    versions: Mapped[list["AssetVersion"]] = relationship(
        "AssetVersion",
        back_populates="asset",
        lazy="selectin",
        order_by="AssetVersion.version_number.desc()",
    )

    def __repr__(self) -> str:
        return f"<Asset(id={self.id}, name={self.name}, format={self.format})>"


class AssetVersion(Base):
    """
    Asset version history model.
    Implements immutable versioning per D9.1 Section 6.3.1.
    """
    __tablename__ = "asset_versions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="Version record ID",
    )
    asset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent asset ID",
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Version number",
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Version-specific file path",
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="File size in bytes",
    )
    checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 hash of file",
    )
    changes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Change description",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Version creation timestamp",
    )
    created_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User who created this version",
    )

    # Relationship
    asset: Mapped["Asset"] = relationship("Asset", back_populates="versions")

    def __repr__(self) -> str:
        return f"<AssetVersion(asset_id={self.asset_id}, version={self.version_number})>"
