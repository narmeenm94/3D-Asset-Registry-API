"""
Asset endpoints - Full implementation.
Implements D9.1 Section 3.1.2 API Endpoint Specification.
"""

from typing import Any

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.core.exceptions import (
    AssetNotFoundException,
    PayloadTooLargeException,
    ValidationException,
)
from app.dependencies import DbSession, ResponseFormat, Storage
from app.models.asset import AccessLevel, AssetFormat
from app.schemas.asset import (
    AssetCreate,
    AssetListResponse,
    AssetResponse,
    AssetSearchParams,
    AssetTagsUpdate,
    AssetUpdate,
    AssetVersionResponse,
)
from app.services.asset_service import AssetService, compute_checksum
from app.services.metadata_extractor import get_metadata_extractor
from app.storage.base import get_mime_type
from app.auth.dependencies import OptionalUser, RequireRead, RequireWrite
from app.auth.permissions import check_asset_access

router = APIRouter()
settings = get_settings()


def _asset_to_response(asset, include_tags: bool = True, include_versions: bool = False) -> dict[str, Any]:
    """Convert Asset model to response dict."""
    response = {
        "id": asset.id,
        "name": asset.name,
        "description": asset.description,
        "format": asset.format.value,
        "triCount": asset.tri_count,
        "tags": [tag.name for tag in asset.tags] if include_tags else [],
        "version": asset.version,
        "uploader": asset.uploader,
        "createdAt": asset.created_at.isoformat(),
        "updatedAt": asset.updated_at.isoformat(),
        "provenance": asset.provenance,
        "useCase": asset.use_case,
        "fileSize": asset.file_size,
        "accessLevel": asset.access_level.value,
        "ownerId": asset.owner_id,
        "ownerInstitution": asset.owner_institution,
        "license": asset.license,
        "attributionRequired": asset.attribution_required,
        "lineageId": asset.lineage_id,
        "derivedFromAsset": asset.derived_from_asset,
        "lodLevels": asset.lod_levels,
        "materialProperties": asset.material_properties,
        "boundingBox": asset.bounding_box,
        "qualityMetrics": asset.quality_metrics,
        "scientificDomain": asset.scientific_domain,
        "sourceDataFormat": asset.source_data_format,
        "processingParameters": asset.processing_parameters,
        "projectPhase": asset.project_phase,
        "theme": asset.theme,
        "accessScope": asset.access_scope,
        "geoRestrictions": asset.geo_restrictions,
        "usageConstraints": asset.usage_constraints,
        "visualizationCapabilities": asset.visualization_capabilities,
        "usageGuidelines": asset.usage_guidelines,
        "deploymentNotes": asset.deployment_notes,
    }
    
    # Include version history for JSON-LD transform
    if include_versions and hasattr(asset, "versions") and asset.versions:
        response["_versions"] = [
            {
                "versionNumber": v.version_number,
                "createdAt": v.created_at.isoformat(),
                "createdBy": v.created_by,
                "changes": v.changes,
                "checksum": v.checksum,
            }
            for v in asset.versions
        ]
    
    return response


@router.get("", response_model=AssetListResponse)
async def list_assets(
    db: DbSession,
    user: OptionalUser,
    q: str | None = Query(default=None, description="Full-text search query"),
    tags: str | None = Query(default=None, description="Comma-separated tag filter"),
    format: AssetFormat | None = Query(default=None, description="File format filter"),
    minTris: int | None = Query(default=None, ge=0, description="Minimum triangle count"),
    maxTris: int | None = Query(default=None, le=10_000_000, description="Maximum triangle count"),
    useCase: str | None = Query(default=None, description="Use case filter (UC2-UC5)"),
    accessLevel: AccessLevel | None = Query(default=None, description="Access level filter"),
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=20, ge=1, le=100, description="Page size"),
):
    """
    Search and list assets with pagination.
    
    Supports filtering by:
    - Full-text search (q)
    - Tags (comma-separated)
    - File format
    - Triangle count range
    - Use case
    - Access level
    
    Uses OptionalUser: unauthenticated users see only public assets;
    authenticated users see assets according to their access level.
    """
    params = AssetSearchParams(
        q=q,
        tags=tags,
        format=format,
        min_tris=minTris,
        max_tris=maxTris,
        use_case=useCase,
        access_level=accessLevel,
        page=page,
        size=size,
    )
    
    service = AssetService(db)
    assets, total = await service.search(
        params,
        user_id=user.get("user_id") if user else None,
        user_institution=user.get("institution") if user else None,
        is_consortium_member=user.get("is_consortium_member", False) if user else False,
    )
    
    items = [_asset_to_response(asset) for asset in assets]
    pages = (total + size - 1) // size if total > 0 else 1
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.get("/{asset_id}")
async def get_asset(
    asset_id: str,
    request: Request,
    db: DbSession,
    user: RequireRead,
    response_format: ResponseFormat,
):
    """
    Get specific asset metadata.
    Requires assets:read scope.
    
    Supports content negotiation:
    - Accept: application/json - Standard JSON response
    - Accept: application/ld+json - JSON-LD with semantic context
    """
    service = AssetService(db)
    asset = await service.get_by_id(asset_id)
    
    # Enforce per-asset permission check
    check_asset_access(asset, user, action="read")
    
    # Include version history when JSON-LD is requested (for metro:versionHistory)
    response = _asset_to_response(asset, include_versions=(response_format == "jsonld"))
    
    # JSON-LD transformation handled by jsonld module
    if response_format == "jsonld":
        from app.schemas.jsonld import transform_to_jsonld
        return transform_to_jsonld(response, request)
    
    return response


@router.get("/{asset_id}/file")
async def download_asset_file(
    asset_id: str,
    db: DbSession,
    user: RequireRead,
    storage: Storage,
):
    """
    Download asset binary file.
    Requires assets:read scope.
    
    Returns the file as a streaming response with appropriate MIME type.
    """
    service = AssetService(db)
    asset = await service.get_by_id(asset_id)
    
    # Enforce per-asset permission check
    check_asset_access(asset, user, action="read")
    
    # Get MIME type for the format
    mime_type = get_mime_type(asset.format.value)
    
    # Stream the file
    async def file_iterator():
        async for chunk in storage.download(asset.file_path):
            yield chunk
    
    # Build filename
    filename = f"{asset.name}.{asset.format.value}"
    
    return StreamingResponse(
        file_iterator(),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(asset.file_size),
        },
    )


@router.post("", status_code=201)
async def create_asset(
    request: Request,
    db: DbSession,
    storage: Storage,
    user: RequireWrite,
    file: UploadFile = File(..., description="3D asset file"),
    name: str = Form(..., min_length=1, max_length=100),
    description: str = Form(default="", max_length=500),
    format: AssetFormat = Form(...),
    triCount: int | None = Form(default=None, ge=0, le=10_000_000, description="Auto-extracted if not provided"),
    tags: str = Form(default="", description="Comma-separated tags"),
    useCase: str | None = Form(default=None),
    accessLevel: AccessLevel = Form(default=AccessLevel.PRIVATE),
    license: str | None = Form(default=None),
    attributionRequired: bool = Form(default=False),
    scientificDomain: str | None = Form(default=None),
    sourceDataFormat: str | None = Form(default=None),
    lineageId: str | None = Form(default=None, description="Stable UUID grouping all versions of the same logical asset"),
    derivedFromAsset: str | None = Form(default=None, description="Comma-separated URI(s) of parent asset when this is a fork/derivative"),
    projectPhase: str | None = Form(default=None, description="Project phase (prototype, production, archived)"),
    usageConstraints: str | None = Form(default=None, description="Usage constraints/limitations"),
    deploymentNotes: str | None = Form(default=None, description="Deployment/integration notes"),
    autoExtract: bool = Form(default=True, description="Auto-extract metadata from 3D file"),
):
    """
    Create a new asset.
    Requires assets:write scope.
    
    Accepts multipart/form-data with:
    - file: The 3D asset binary file
    - Metadata fields as form fields
    
    When autoExtract=True (default), the API will automatically parse the 3D file
    and extract: triCount, vertexCount, boundingBox, materials, animations, etc.
    User-provided values override auto-extracted values.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Validate file size
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise PayloadTooLargeException(settings.MAX_UPLOAD_SIZE)
    
    # Compute checksum
    checksum = compute_checksum(file_content)
    
    # Auto-extract metadata from 3D file
    extracted_metadata = {}
    if autoExtract:
        try:
            extractor = get_metadata_extractor()
            extracted_metadata = await extractor.extract(
                file_content=file_content,
                filename=file.filename or f"{name}.{format.value}",
                file_format=format.value,
            )
            logger.info(f"Auto-extracted metadata: {list(extracted_metadata.keys())}")
        except Exception as e:
            logger.warning(f"Metadata extraction failed (continuing without): {e}")
    
    # Use extracted values as defaults, user-provided values override
    final_tri_count = triCount if triCount is not None else extracted_metadata.get("tri_count", 0)
    
    # Build extended metadata from extraction
    extracted_bounding_box = extracted_metadata.get("bounding_box")
    extracted_materials = {}
    if extracted_metadata.get("has_materials"):
        extracted_materials = {
            "count": extracted_metadata.get("material_count", 0),
            "names": extracted_metadata.get("material_names", []),
        }
    
    # Build quality metrics from extraction
    quality_metrics = {}
    if extracted_metadata.get("vertex_count"):
        quality_metrics["vertexCount"] = extracted_metadata["vertex_count"]
    if extracted_metadata.get("is_watertight") is not None:
        quality_metrics["isWatertight"] = extracted_metadata["is_watertight"]
    if extracted_metadata.get("dimensions"):
        quality_metrics["dimensions"] = extracted_metadata["dimensions"]
    if extracted_metadata.get("has_animations"):
        quality_metrics["hasAnimations"] = True
        quality_metrics["animationCount"] = extracted_metadata.get("animation_count", 0)
    if extracted_metadata.get("has_textures"):
        quality_metrics["hasTextures"] = True
        quality_metrics["textureCount"] = extracted_metadata.get("texture_count", 0)
    if extracted_metadata.get("mesh_count"):
        quality_metrics["meshCount"] = extracted_metadata["mesh_count"]
    if extracted_metadata.get("generator"):
        quality_metrics["generator"] = extracted_metadata["generator"]
    
    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    
    # Validate tag count
    if len(tag_list) > 20:
        raise ValidationException("Maximum 20 tags allowed")
    
    # Build storage path
    from uuid import uuid4
    asset_id = str(uuid4())
    file_path = f"assets/{asset_id}/v1/{name}.{format.value}"
    
    # Upload file to storage
    await storage.upload_bytes(
        file_content,
        file_path,
        get_mime_type(format.value),
    )
    
    # Parse derivedFromAsset (comma-separated URIs)
    derived_list = None
    if derivedFromAsset:
        derived_list = [u.strip() for u in derivedFromAsset.split(",") if u.strip()]
    
    # Create asset data with extracted metadata
    create_data = AssetCreate(
        name=name,
        description=description,
        format=format,
        tri_count=final_tri_count,
        tags=tag_list,
        use_case=useCase,
        access_level=accessLevel,
        license=license,
        attribution_required=attributionRequired,
        scientific_domain=scientificDomain,
        source_data_format=sourceDataFormat,
        lineage_id=lineageId,
        derived_from_asset=derived_list,
        project_phase=projectPhase,
        usage_constraints=usageConstraints,
        deployment_notes=deploymentNotes,
        # Add extracted data
        bounding_box=extracted_bounding_box,
        material_properties=extracted_materials if extracted_materials else None,
        quality_metrics=quality_metrics if quality_metrics else None,
    )
    
    # Create in database
    service = AssetService(db)
    
    # Reset file position for potential re-read
    await file.seek(0)
    
    asset = await service.create(
        data=create_data,
        file=file,
        file_path=file_path,
        file_size=file_size,
        checksum=checksum,
        user_id=user["user_id"],
        user_institution=user["institution"],
    )
    
    # Add extraction info to response
    response = _asset_to_response(asset)
    if extracted_metadata and extracted_metadata.get("extracted"):
        response["_extraction"] = {
            "autoExtracted": True,
            "fieldsExtracted": [k for k in extracted_metadata.keys() if k not in ("extracted", "format_detected", "file_size_bytes")],
        }
    
    return response


@router.put("/{asset_id}/file")
async def upload_new_version(
    asset_id: str,
    db: DbSession,
    storage: Storage,
    user: RequireWrite,
    file: UploadFile = File(..., description="New version file"),
    changes: str | None = Form(default=None, description="Description of changes"),
):
    """
    Upload a new version of an asset.
    Requires assets:write scope and asset ownership.
    
    Creates a new version record and updates the asset's current version.
    Previous versions are preserved for rollback.
    """
    service = AssetService(db)
    
    # Get existing asset to verify it exists and get metadata
    asset = await service.get_by_id(asset_id)
    
    # Enforce per-asset permission check (write requires ownership)
    check_asset_access(asset, user, action="write")
    
    # Validate file size
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise PayloadTooLargeException(settings.MAX_UPLOAD_SIZE)
    
    # Compute checksum
    checksum = compute_checksum(file_content)
    
    # Build storage path for new version
    new_version = asset.version + 1
    file_path = f"assets/{asset_id}/v{new_version}/{asset.name}.{asset.format.value}"
    
    # Upload file to storage
    await storage.upload_bytes(
        file_content,
        file_path,
        get_mime_type(asset.format.value),
    )
    
    # Update asset with new version
    updated_asset = await service.upload_new_version(
        asset_id=asset_id,
        file_path=file_path,
        file_size=file_size,
        checksum=checksum,
        user_id=user["user_id"],
        changes=changes,
    )
    
    return _asset_to_response(updated_asset)


@router.patch("/{asset_id}")
async def update_asset_metadata(
    asset_id: str,
    db: DbSession,
    user: RequireWrite,
    data: AssetUpdate,
):
    """
    Update asset metadata fields.
    Requires assets:write scope and asset ownership.
    
    Only name and description can be updated via this endpoint.
    Use PUT /assets/{id}/tags for tag updates.
    """
    service = AssetService(db)
    
    # Fetch asset and enforce ownership
    asset = await service.get_by_id(asset_id)
    check_asset_access(asset, user, action="write")
    
    asset = await service.update_metadata(
        asset_id=asset_id,
        data=data,
        user_id=user["user_id"],
    )
    
    return _asset_to_response(asset)


@router.put("/{asset_id}/tags")
async def replace_asset_tags(
    asset_id: str,
    db: DbSession,
    user: RequireWrite,
    data: AssetTagsUpdate,
):
    """
    Replace asset tag set.
    Requires assets:write scope and asset ownership.
    
    Replaces all existing tags with the provided list.
    """
    service = AssetService(db)
    
    # Fetch asset and enforce ownership
    asset = await service.get_by_id(asset_id)
    check_asset_access(asset, user, action="write")
    
    asset = await service.update_tags(
        asset_id=asset_id,
        tags=data.tags,
        user_id=user["user_id"],
    )
    
    return _asset_to_response(asset)


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: str,
    db: DbSession,
    user: RequireWrite,
    storage: Storage,
):
    """
    Delete an asset.
    Requires assets:write scope and asset ownership.
    
    Removes the asset and all its versions from storage.
    This operation cannot be undone.
    """
    service = AssetService(db)
    
    # Get asset to retrieve file paths
    asset = await service.get_by_id(asset_id)
    
    # Enforce per-asset permission check (delete requires ownership)
    check_asset_access(asset, user, action="delete")
    
    # Delete all version files from storage
    for version in asset.versions:
        try:
            await storage.delete(version.file_path)
        except Exception:
            pass  # Continue even if file deletion fails
    
    # Delete from database
    await service.delete(
        asset_id=asset_id,
        user_id=user["user_id"],
    )
    
    return None


@router.get("/{asset_id}/versions")
async def list_asset_versions(
    asset_id: str,
    db: DbSession,
    user: RequireRead,
):
    """
    List all versions of an asset.
    Requires assets:read scope.
    
    Returns version history with change descriptions and timestamps.
    """
    service = AssetService(db)
    asset = await service.get_by_id(asset_id)
    
    # Enforce per-asset permission check
    check_asset_access(asset, user, action="read")
    
    versions = [
        {
            "id": v.id,
            "versionNumber": v.version_number,
            "fileSize": v.file_size,
            "checksum": v.checksum,
            "changes": v.changes,
            "createdAt": v.created_at.isoformat(),
            "createdBy": v.created_by,
        }
        for v in asset.versions
    ]
    
    return {"versions": versions, "total": len(versions)}
