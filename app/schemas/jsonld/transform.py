"""
JSON-LD transformation utilities.
Transforms standard JSON responses to JSON-LD format with semantic context.
"""

from typing import Any

from fastapi import Request

from app.config import get_settings
from app.schemas.jsonld.context import (
    METRO_JSONLD_CONTEXT,
    FORMAT_TO_MIME,
    CONFORMANCE_STANDARDS,
)

settings = get_settings()


def transform_to_jsonld(asset_data: dict[str, Any], request: Request) -> dict[str, Any]:
    """
    Transform asset JSON response to JSON-LD format.
    
    Adds semantic context and restructures data to follow
    the RDF metadata framework specification.
    
    Args:
        asset_data: Standard JSON asset response
        request: FastAPI request (for building URLs)
        
    Returns:
        JSON-LD formatted response
    """
    # Build base URL
    base_url = str(request.base_url).rstrip("/")
    asset_id = asset_data.get("id", "")
    
    # Get format-specific information
    format_value = asset_data.get("format", "gltf")
    mime_type = FORMAT_TO_MIME.get(format_value, "application/octet-stream")
    
    # Build JSON-LD document
    jsonld = {
        "@context": METRO_JSONLD_CONTEXT,
        "@type": ["dcat:Dataset", "schema:3DModel"],
        "@id": f"{base_url}/api/v1/assets/{asset_id}",
        
        # Identification & Discovery
        "dct:title": asset_data.get("name"),
        "dct:description": asset_data.get("description", ""),
        "dct:identifier": asset_id,
        "dcat:keyword": asset_data.get("tags", []),
        
        # Technical Specifications
        "schema:encodingFormat": mime_type,
        "metro:triangleCount": asset_data.get("triCount", 0),
        "dcat:byteSize": asset_data.get("fileSize", 0),
        
        # Provenance
        "dct:creator": {
            "@type": "schema:Person",
            "schema:identifier": asset_data.get("uploader"),
        },
        "dct:created": asset_data.get("createdAt"),
        "dct:modified": asset_data.get("updatedAt"),
        "schema:version": str(asset_data.get("version", 1)),
        
        # Domain Classification
        "metro:useCase": asset_data.get("useCase"),
        "metro:scientificDomain": asset_data.get("scientificDomain"),
        
        # Access Control
        "metro:accessLevel": asset_data.get("accessLevel"),
        "metro:ownerId": asset_data.get("ownerId"),
        "metro:ownerInstitution": asset_data.get("ownerInstitution"),
        "metro:requiresAuthentication": True,
        "metro:attributionRequired": asset_data.get("attributionRequired", False),
        
        # Distribution
        "dcat:distribution": [
            {
                "@type": "dcat:Distribution",
                "dct:title": f"{format_value.upper()} Distribution",
                "dcat:accessURL": f"{base_url}/api/v1/assets/{asset_id}/file",
                "dct:format": mime_type,
                "dcat:byteSize": asset_data.get("fileSize", 0),
            }
        ],
        
        # Standards Compliance
        "dct:conformsTo": [
            CONFORMANCE_STANDARDS.get(format_value, CONFORMANCE_STANDARDS["metro"]),
            CONFORMANCE_STANDARDS["metro"],
        ],
        "metro:dataClassification": "generic-public",
        
        # Service Information
        "metro:serviceEndpoint": f"{base_url}/api/v1",
        "metro:deploymentPhase": "development" if settings.DEV_MODE else "production",
        
        # Contact Point
        "dcat:contactPoint": {
            "@type": "vcard:Organization",
            "vcard:fn": "METRO WP9 Team",
            "vcard:hasEmail": "wp9@metropolia.fi",
        },
    }
    
    # Hosting node from config
    jsonld["metro:hostingNode"] = settings.HOSTING_NODE
    
    # Version history (from _versions embedded by endpoint when JSON-LD requested)
    versions = asset_data.get("_versions")
    if versions:
        # Build version history list (sorted by version number ascending)
        sorted_versions = sorted(versions, key=lambda v: v["versionNumber"])
        jsonld["metro:versionHistory"] = [
            {
                "@type": "metro:AssetVersion",
                "schema:version": str(v["versionNumber"]),
                "dct:created": v["createdAt"],
                "dct:creator": v["createdBy"],
                "schema:description": v.get("changes"),
            }
            for v in sorted_versions
        ]
        # Derive previousVersion from version history
        current_version = asset_data.get("version", 1)
        if current_version and current_version > 1:
            jsonld["metro:previousVersion"] = (
                f"{base_url}/api/v1/assets/{asset_id}/versions/{current_version - 1}"
            )
    
    # Add lineage & derivation if present
    if asset_data.get("lineageId"):
        jsonld["metro:lineageId"] = asset_data["lineageId"]
    
    if asset_data.get("derivedFromAsset"):
        derived = asset_data["derivedFromAsset"]
        # Normalize to list
        if isinstance(derived, str):
            derived = [derived]
        jsonld["metro:derivedFromAsset"] = derived
    
    # Add optional properties if present
    if asset_data.get("lodLevels"):
        jsonld["metro:lodLevels"] = asset_data["lodLevels"]
    
    if asset_data.get("materialProperties"):
        jsonld["metro:materialProperties"] = asset_data["materialProperties"]
    
    if asset_data.get("boundingBox"):
        jsonld["metro:boundingBox"] = asset_data["boundingBox"]
    
    if asset_data.get("qualityMetrics"):
        jsonld["metro:qualityMetrics"] = asset_data["qualityMetrics"]
    
    if asset_data.get("sourceDataFormat"):
        jsonld["metro:sourceDataFormat"] = asset_data["sourceDataFormat"]
    
    if asset_data.get("processingParameters"):
        jsonld["metro:processingParameters"] = asset_data["processingParameters"]
    
    if asset_data.get("provenance"):
        provenance = asset_data["provenance"]
        jsonld["metro:generatedWith"] = {
            "@type": "schema:SoftwareApplication",
            "schema:name": provenance.get("tool", "Unknown"),
        }
        if provenance.get("sourceData"):
            jsonld["dct:source"] = {
                "@type": "schema:Dataset",
                "schema:name": ", ".join(provenance["sourceData"]),
            }
    
    if asset_data.get("license"):
        jsonld["dct:license"] = {
            "@type": "schema:CreativeWork",
            "@id": asset_data["license"],
        }
    
    # Add remaining RDF Annex A properties if present
    if asset_data.get("projectPhase"):
        jsonld["metro:projectPhase"] = asset_data["projectPhase"]
    
    if asset_data.get("theme"):
        jsonld["dcat:theme"] = asset_data["theme"]
    
    if asset_data.get("accessScope"):
        jsonld["metro:accessScope"] = asset_data["accessScope"]
    
    if asset_data.get("geoRestrictions"):
        jsonld["metro:geoRestrictions"] = asset_data["geoRestrictions"]
    
    if asset_data.get("usageConstraints"):
        jsonld["metro:usageConstraints"] = asset_data["usageConstraints"]
    
    if asset_data.get("visualizationCapabilities"):
        jsonld["metro:visualizationCapabilities"] = asset_data["visualizationCapabilities"]
    
    if asset_data.get("usageGuidelines"):
        jsonld["metro:usageGuidelines"] = asset_data["usageGuidelines"]
    
    if asset_data.get("deploymentNotes"):
        jsonld["metro:deploymentNotes"] = asset_data["deploymentNotes"]
    
    # Clean up None values
    jsonld = {k: v for k, v in jsonld.items() if v is not None}
    
    return jsonld


def transform_list_to_jsonld(
    assets_data: list[dict[str, Any]],
    request: Request,
    total: int,
    page: int,
    size: int,
) -> dict[str, Any]:
    """
    Transform asset list response to JSON-LD format.
    
    Creates a DCAT Catalog containing the assets as datasets.
    
    Args:
        assets_data: List of asset JSON responses
        request: FastAPI request
        total: Total number of assets
        page: Current page number
        size: Page size
        
    Returns:
        JSON-LD formatted catalog response
    """
    base_url = str(request.base_url).rstrip("/")
    
    # Transform each asset
    datasets = [transform_to_jsonld(asset, request) for asset in assets_data]
    
    catalog = {
        "@context": METRO_JSONLD_CONTEXT,
        "@type": "dcat:Catalog",
        "@id": f"{base_url}/api/v1/assets",
        "dct:title": "METRO 3D Asset Catalog",
        "dct:description": "Catalog of 3D visualization assets for DTRIP4H project",
        "dct:publisher": {
            "@type": "schema:Organization",
            "schema:name": "METRO (Metropolia Ammattikorkeakoulu OY)",
        },
        "dcat:dataset": datasets,
        "metro:totalResults": total,
        "metro:currentPage": page,
        "metro:pageSize": size,
        "metro:totalPages": (total + size - 1) // size if total > 0 else 1,
    }
    
    return catalog


def create_minimal_context() -> dict[str, str]:
    """
    Create a minimal JSON-LD context for simple responses.
    
    Returns:
        Minimal context with essential prefixes
    """
    return {
        "@vocab": "http://dtrip4h.eu/metro/vocab#",
        "dcat": "http://www.w3.org/ns/dcat#",
        "dct": "http://purl.org/dc/terms/",
        "schema": "http://schema.org/",
        "metro": "http://dtrip4h.eu/metro/vocab#",
    }
