"""
Asset service - Business logic for asset operations.
Handles CRUD operations, search, and version management.
"""

import hashlib
from datetime import datetime
from typing import Sequence
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AssetNotFoundException, ValidationException
from app.models.asset import Asset, AssetVersion, AccessLevel, AssetFormat
from app.models.tag import Tag, TagCategory
from app.schemas.asset import AssetCreate, AssetSearchParams, AssetUpdate


class AssetService:
    """Service class for asset operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, asset_id: str) -> Asset:
        """
        Get asset by ID.
        
        Args:
            asset_id: Asset UUID
            
        Returns:
            Asset model
            
        Raises:
            AssetNotFoundException: If asset not found
        """
        query = (
            select(Asset)
            .options(selectinload(Asset.tags), selectinload(Asset.versions))
            .where(Asset.id == asset_id)
        )
        result = await self.db.execute(query)
        asset = result.scalar_one_or_none()
        
        if not asset:
            raise AssetNotFoundException(asset_id)
        
        return asset
    
    async def search(
        self,
        params: AssetSearchParams,
        user_id: str | None = None,
        user_institution: str | None = None,
        is_consortium_member: bool = False,
    ) -> tuple[Sequence[Asset], int]:
        """
        Search and filter assets with pagination.
        
        Args:
            params: Search parameters
            user_id: Current user ID for access filtering
            user_institution: User's institution for access filtering
            is_consortium_member: Whether user is DTRIP4H consortium member
            
        Returns:
            Tuple of (list of assets, total count)
        """
        # Build base query
        query = select(Asset).options(selectinload(Asset.tags))
        count_query = select(func.count(Asset.id))
        
        conditions = []
        
        # Full-text search on name and description
        if params.q:
            search_term = f"%{params.q}%"
            conditions.append(
                or_(
                    Asset.name.ilike(search_term),
                    Asset.description.ilike(search_term),
                )
            )
        
        # Filter by tags
        if params.tags:
            tag_list = [t.strip() for t in params.tags.split(",")]
            # Subquery to find assets with matching tags
            tag_subquery = (
                select(Asset.id)
                .join(Asset.tags)
                .where(Tag.name.in_(tag_list))
                .group_by(Asset.id)
            )
            conditions.append(Asset.id.in_(tag_subquery))
        
        # Filter by format
        if params.format:
            conditions.append(Asset.format == params.format)
        
        # Filter by triangle count
        if params.min_tris is not None:
            conditions.append(Asset.tri_count >= params.min_tris)
        if params.max_tris is not None:
            conditions.append(Asset.tri_count <= params.max_tris)
        
        # Filter by use case
        if params.use_case:
            conditions.append(Asset.use_case == params.use_case)
        
        # Filter by access level
        if params.access_level:
            conditions.append(Asset.access_level == params.access_level)
        
        # Access control filtering - always add access conditions
        access_conditions = self._build_access_conditions(
            user_id, user_institution, is_consortium_member
        )
        conditions.append(access_conditions)
        
        # Apply conditions
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Get total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Apply pagination
        offset = (params.page - 1) * params.size
        query = query.order_by(Asset.created_at.desc()).offset(offset).limit(params.size)
        
        # Execute query
        result = await self.db.execute(query)
        assets = result.scalars().all()
        
        return assets, total
    
    def _build_access_conditions(
        self,
        user_id: str | None,
        user_institution: str | None,
        is_consortium_member: bool,
    ):
        """Build access control conditions for queries."""
        if not user_id:
            # No user - only public assets
            return Asset.access_level == AccessLevel.PUBLIC
        
        conditions = [
            # User is owner
            Asset.owner_id == user_id,
            # Public assets
            Asset.access_level == AccessLevel.PUBLIC,
        ]
        
        # Group access - user in authorized_users
        conditions.append(
            and_(
                Asset.access_level == AccessLevel.GROUP,
                Asset.authorized_users.contains([user_id]),
            )
        )
        
        # Approval required - user in authorized_users
        conditions.append(
            and_(
                Asset.access_level == AccessLevel.APPROVAL_REQUIRED,
                Asset.authorized_users.contains([user_id]),
            )
        )
        
        if user_institution:
            # Institution access
            conditions.append(
                and_(
                    Asset.access_level == AccessLevel.INSTITUTION,
                    Asset.owner_institution == user_institution,
                )
            )
            # Group access - institution in authorized_institutions
            conditions.append(
                and_(
                    Asset.access_level == AccessLevel.GROUP,
                    Asset.authorized_institutions.contains([user_institution]),
                )
            )
        
        if is_consortium_member:
            # Consortium access
            conditions.append(Asset.access_level == AccessLevel.CONSORTIUM)
        
        return or_(*conditions)
    
    async def create(
        self,
        data: AssetCreate,
        file: UploadFile,
        file_path: str,
        file_size: int,
        checksum: str,
        user_id: str,
        user_institution: str,
    ) -> Asset:
        """
        Create a new asset.
        
        Args:
            data: Asset creation data
            file: Uploaded file
            file_path: Storage path for the file
            file_size: Size of the file in bytes
            checksum: SHA-256 checksum of the file
            user_id: Uploader user ID
            user_institution: Uploader's institution
            
        Returns:
            Created Asset model
        """
        # Get or create tags
        tags = await self._get_or_create_tags(data.tags)
        
        # Build provenance dict
        provenance = None
        if data.provenance:
            provenance = {
                "tool": data.provenance.tool,
                "sourceData": data.provenance.source_data,
            }
        
        # Create asset
        asset = Asset(
            id=str(uuid4()),
            name=data.name,
            description=data.description,
            format=data.format,
            tri_count=data.tri_count,
            version=1,
            file_path=file_path,
            file_size=file_size,
            checksum=checksum,
            uploader=user_id,
            provenance=provenance,
            use_case=data.use_case,
            access_level=data.access_level,
            owner_id=user_id,
            owner_institution=user_institution,
            authorized_users=data.authorized_users,
            authorized_institutions=data.authorized_institutions,
            embargo_until=data.embargo_until,
            license=data.license,
            attribution_required=data.attribution_required,
            lineage_id=getattr(data, "lineage_id", None),
            derived_from_asset=getattr(data, "derived_from_asset", None),
            lod_levels=data.lod_levels,
            material_properties=data.material_properties,
            bounding_box=data.bounding_box,
            quality_metrics=data.quality_metrics,
            scientific_domain=data.scientific_domain,
            source_data_format=data.source_data_format,
            processing_parameters=data.processing_parameters,
            project_phase=getattr(data, "project_phase", None),
            theme=getattr(data, "theme", None),
            access_scope=getattr(data, "access_scope", None),
            geo_restrictions=getattr(data, "geo_restrictions", None),
            usage_constraints=getattr(data, "usage_constraints", None),
            visualization_capabilities=getattr(data, "visualization_capabilities", None),
            usage_guidelines=getattr(data, "usage_guidelines", None),
            deployment_notes=getattr(data, "deployment_notes", None),
            tags=tags,
        )
        
        # Create initial version record
        version = AssetVersion(
            id=str(uuid4()),
            asset_id=asset.id,
            version_number=1,
            file_path=file_path,
            file_size=file_size,
            checksum=checksum,
            changes="Initial version",
            created_by=user_id,
        )
        
        self.db.add(asset)
        self.db.add(version)
        
        # Update tag usage counts
        for tag in tags:
            tag.usage_count += 1
        
        await self.db.flush()
        await self.db.refresh(asset)
        
        return asset
    
    async def update_metadata(
        self,
        asset_id: str,
        data: AssetUpdate,
        user_id: str,
    ) -> Asset:
        """
        Update asset metadata.
        
        Args:
            asset_id: Asset UUID
            data: Update data
            user_id: User performing the update
            
        Returns:
            Updated Asset model
        """
        asset = await self.get_by_id(asset_id)
        
        # Check ownership (will be enforced by permission system)
        if asset.owner_id != user_id:
            raise ValidationException("Only asset owner can update metadata")
        
        # Update allowed fields
        if data.name is not None:
            asset.name = data.name
        if data.description is not None:
            asset.description = data.description
        
        asset.updated_at = datetime.utcnow()
        
        await self.db.flush()
        await self.db.refresh(asset)
        
        return asset
    
    async def update_tags(
        self,
        asset_id: str,
        tags: list[str],
        user_id: str,
    ) -> Asset:
        """
        Replace asset tags.
        
        Args:
            asset_id: Asset UUID
            tags: New tag list
            user_id: User performing the update
            
        Returns:
            Updated Asset model
        """
        asset = await self.get_by_id(asset_id)
        
        # Check ownership
        if asset.owner_id != user_id:
            raise ValidationException("Only asset owner can update tags")
        
        # Decrement old tag counts
        for tag in asset.tags:
            tag.usage_count = max(0, tag.usage_count - 1)
        
        # Get or create new tags
        new_tags = await self._get_or_create_tags(tags)
        
        # Update asset tags
        asset.tags = new_tags
        asset.updated_at = datetime.utcnow()
        
        # Increment new tag counts
        for tag in new_tags:
            tag.usage_count += 1
        
        await self.db.flush()
        await self.db.refresh(asset)
        
        return asset
    
    async def upload_new_version(
        self,
        asset_id: str,
        file_path: str,
        file_size: int,
        checksum: str,
        user_id: str,
        changes: str | None = None,
    ) -> Asset:
        """
        Upload a new version of an asset.
        
        Args:
            asset_id: Asset UUID
            file_path: Storage path for the new version
            file_size: Size of the file in bytes
            checksum: SHA-256 checksum
            user_id: User uploading the version
            changes: Description of changes
            
        Returns:
            Updated Asset model
        """
        asset = await self.get_by_id(asset_id)
        
        # Check ownership
        if asset.owner_id != user_id:
            raise ValidationException("Only asset owner can upload new versions")
        
        # Increment version
        new_version_number = asset.version + 1
        
        # Create version record
        version = AssetVersion(
            id=str(uuid4()),
            asset_id=asset.id,
            version_number=new_version_number,
            file_path=file_path,
            file_size=file_size,
            checksum=checksum,
            changes=changes or f"Version {new_version_number}",
            created_by=user_id,
        )
        
        # Update asset
        asset.version = new_version_number
        asset.file_path = file_path
        asset.file_size = file_size
        asset.checksum = checksum
        asset.updated_at = datetime.utcnow()
        
        self.db.add(version)
        
        await self.db.flush()
        await self.db.refresh(asset)
        
        return asset
    
    async def delete(self, asset_id: str, user_id: str) -> bool:
        """
        Delete an asset.
        
        Args:
            asset_id: Asset UUID
            user_id: User performing the deletion
            
        Returns:
            True if deleted
        """
        asset = await self.get_by_id(asset_id)
        
        # Check ownership
        if asset.owner_id != user_id:
            raise ValidationException("Only asset owner can delete assets")
        
        # Decrement tag counts
        for tag in asset.tags:
            tag.usage_count = max(0, tag.usage_count - 1)
        
        await self.db.delete(asset)
        await self.db.flush()
        
        return True
    
    async def _get_or_create_tags(self, tag_names: list[str]) -> list[Tag]:
        """Get existing tags or create new ones."""
        if not tag_names:
            return []
        
        tags = []
        for name in tag_names:
            # Try to find existing tag
            query = select(Tag).where(Tag.name == name)
            result = await self.db.execute(query)
            tag = result.scalar_one_or_none()
            
            if not tag:
                # Determine category based on name patterns
                category = self._determine_tag_category(name)
                tag = Tag(
                    id=str(uuid4()),
                    name=name,
                    category=category,
                    usage_count=0,
                )
                self.db.add(tag)
            
            tags.append(tag)
        
        return tags
    
    def _determine_tag_category(self, name: str) -> TagCategory:
        """Determine tag category based on name patterns."""
        name_lower = name.lower()
        
        # Use case patterns
        if name_lower.startswith("uc") and name_lower[2:].isdigit():
            return TagCategory.USE_CASE
        
        # Domain patterns
        domain_keywords = ["molecule", "admet", "aq", "cancer", "dopamine", "cell", "protein"]
        if any(kw in name_lower for kw in domain_keywords):
            return TagCategory.DOMAIN
        
        # Technical patterns
        tech_keywords = ["lowpoly", "lod", "mobile", "xr", "vr", "ar", "optimized"]
        if any(kw in name_lower for kw in tech_keywords):
            return TagCategory.TECHNICAL
        
        # Geographic patterns (common city/country names)
        geo_keywords = ["helsinki", "brno", "barcelona", "munich", "finland", "germany"]
        if any(kw in name_lower for kw in geo_keywords):
            return TagCategory.GEOGRAPHIC
        
        # Temporal patterns
        if any(c.isdigit() for c in name) and any(kw in name_lower for kw in ["q1", "q2", "q3", "q4", "latest"]):
            return TagCategory.TEMPORAL
        
        return TagCategory.GENERAL


def compute_checksum(data: bytes) -> str:
    """Compute SHA-256 checksum of data."""
    return hashlib.sha256(data).hexdigest()
