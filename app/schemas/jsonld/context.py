"""
JSON-LD context definitions for METRO API.
Implements the vocabulary defined in the RDF Document Section 4.

The namespace URI http://dtrip4h.eu/metro/vocab# is a unique identifier
for our custom vocabulary. It does not need to resolve to a live URL.
The vocabulary definitions are embedded directly in this context.
"""

# METRO JSON-LD Context
# This combines standard vocabularies (DCAT, Dublin Core, Schema.org)
# with custom METRO vocabulary for 3D-specific properties.
METRO_JSONLD_CONTEXT = {
    # Namespace definitions
    "@vocab": "http://dtrip4h.eu/metro/vocab#",
    "dcat": "http://www.w3.org/ns/dcat#",
    "dct": "http://purl.org/dc/terms/",
    "schema": "http://schema.org/",
    "metro": "http://dtrip4h.eu/metro/vocab#",
    "vcard": "http://www.w3.org/2006/vcard/ns#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    
    # === Identification & Discovery ===
    "title": "dct:title",
    "description": "dct:description",
    "identifier": "dct:identifier",
    "keywords": {
        "@id": "dcat:keyword",
        "@container": "@set"
    },
    
    # === Technical Specifications ===
    "encodingFormat": "schema:encodingFormat",
    "triangleCount": {
        "@id": "metro:triangleCount",
        "@type": "xsd:integer"
    },
    "lodLevels": {
        "@id": "metro:lodLevels",
        "@type": "xsd:integer"
    },
    "materialProperties": "metro:materialProperties",
    "boundingBox": "metro:boundingBox",
    "byteSize": {
        "@id": "dcat:byteSize",
        "@type": "xsd:integer"
    },
    "qualityMetrics": "metro:qualityMetrics",
    
    # === Provenance & Generation ===
    "creator": "dct:creator",
    "generatedWith": "metro:generatedWith",
    "source": "dct:source",
    "sourceDataFormat": "metro:sourceDataFormat",
    "processingParameters": "metro:processingParameters",
    
    # === Domain Classification ===
    "useCase": "metro:useCase",
    "scientificDomain": "metro:scientificDomain",
    "projectPhase": "metro:projectPhase",
    "theme": "dcat:theme",
    
    # === Lineage & Derivation ===
    "lineageId": "metro:lineageId",
    "derivedFromAsset": {
        "@id": "metro:derivedFromAsset",
        "@type": "@id",
        "@container": "@set"
    },
    
    # === Version & Lifecycle ===
    "version": "schema:version",
    "created": {
        "@id": "dct:created",
        "@type": "xsd:dateTime"
    },
    "modified": {
        "@id": "dct:modified",
        "@type": "xsd:dateTime"
    },
    "versionHistory": {
        "@id": "metro:versionHistory",
        "@container": "@list"
    },
    "previousVersion": {
        "@id": "metro:previousVersion",
        "@type": "@id"
    },
    
    # === Access Control & Distribution ===
    "distribution": {
        "@id": "dcat:distribution",
        "@container": "@set"
    },
    "accessURL": {
        "@id": "dcat:accessURL",
        "@type": "@id"
    },
    "requiresAuthentication": {
        "@id": "metro:requiresAuthentication",
        "@type": "xsd:boolean"
    },
    "license": "dct:license",
    "accessScope": {
        "@id": "metro:accessScope",
        "@container": "@set"
    },
    
    # === Permission Management ===
    "accessLevel": "metro:accessLevel",
    "ownerId": "metro:ownerId",
    "ownerInstitution": "metro:ownerInstitution",
    "authorizedUsers": {
        "@id": "metro:authorizedUsers",
        "@container": "@set"
    },
    "authorizedInstitutions": {
        "@id": "metro:authorizedInstitutions",
        "@container": "@set"
    },
    "embargoUntil": {
        "@id": "metro:embargoUntil",
        "@type": "xsd:dateTime"
    },
    "approvalWorkflow": "metro:approvalWorkflow",
    "geoRestrictions": {
        "@id": "metro:geoRestrictions",
        "@container": "@set"
    },
    "usageConstraints": "metro:usageConstraints",
    "attributionRequired": {
        "@id": "metro:attributionRequired",
        "@type": "xsd:boolean"
    },
    
    # === Federated Infrastructure ===
    "hostingNode": "metro:hostingNode",
    "serviceEndpoint": {
        "@id": "metro:serviceEndpoint",
        "@type": "@id"
    },
    "replicationStatus": "metro:replicationStatus",
    "federatedCatalog": {
        "@id": "metro:federatedCatalog",
        "@type": "@id"
    },
    "deploymentPhase": "metro:deploymentPhase",
    
    # === Standards Compliance ===
    "conformsTo": {
        "@id": "dct:conformsTo",
        "@container": "@set"
    },
    "dataClassification": "metro:dataClassification",
    "contactPoint": "dcat:contactPoint",
    
    # === Optional Descriptive Metadata ===
    "visualizationCapabilities": "metro:visualizationCapabilities",
    "usageGuidelines": "metro:usageGuidelines",
    "deploymentNotes": "metro:deploymentNotes",
}


def get_full_context() -> dict:
    """
    Get the full JSON-LD context for API responses.
    
    Returns:
        Complete context dictionary
    """
    return METRO_JSONLD_CONTEXT.copy()


# MIME type mapping for 3D formats per D9.1 Section 4.2.1
FORMAT_TO_MIME = {
    "gltf": "model/gltf+json",
    "glb": "model/gltf-binary",
    "usdz": "model/vnd.usdz+zip",
    "blend": "application/x-blender",
    "fbx": "application/octet-stream",
    "obj": "model/obj",
    "stl": "model/stl",
    "ply": "application/x-ply",
}


# Standards conformance URIs
CONFORMANCE_STANDARDS = {
    "gltf": "https://www.khronos.org/gltf/",
    "usdz": "https://openusd.org/",
    "metro": "http://dtrip4h.eu/specifications/3d-assets/v1.0",
}
