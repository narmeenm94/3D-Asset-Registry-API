"""
Tests for asset endpoints.
"""

import io
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_assets_empty(client: AsyncClient):
    """Test listing assets when database is empty."""
    response = await client.get("/api/v1/assets")
    
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_create_asset(
    client: AsyncClient,
    sample_asset_data: dict,
    sample_file_content: bytes,
):
    """Test creating a new asset."""
    # Prepare multipart form data
    files = {
        "file": ("test.gltf", io.BytesIO(sample_file_content), "model/gltf+json"),
    }
    data = sample_asset_data.copy()
    
    response = await client.post(
        "/api/v1/assets",
        data=data,
        files=files,
    )
    
    assert response.status_code == 201
    result = response.json()
    assert result["name"] == sample_asset_data["name"]
    assert result["format"] == sample_asset_data["format"]
    assert result["triCount"] == sample_asset_data["triCount"]
    assert "id" in result


@pytest.mark.asyncio
async def test_get_asset(
    client: AsyncClient,
    sample_asset_data: dict,
    sample_file_content: bytes,
):
    """Test getting a specific asset."""
    # First create an asset
    files = {
        "file": ("test.gltf", io.BytesIO(sample_file_content), "model/gltf+json"),
    }
    create_response = await client.post(
        "/api/v1/assets",
        data=sample_asset_data,
        files=files,
    )
    asset_id = create_response.json()["id"]
    
    # Then get it
    response = await client.get(f"/api/v1/assets/{asset_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == asset_id
    assert data["name"] == sample_asset_data["name"]


@pytest.mark.asyncio
async def test_get_asset_not_found(client: AsyncClient):
    """Test getting a non-existent asset returns 404."""
    response = await client.get("/api/v1/assets/non-existent-id")
    
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "not_found"


@pytest.mark.asyncio
async def test_update_asset_metadata(
    client: AsyncClient,
    sample_asset_data: dict,
    sample_file_content: bytes,
):
    """Test updating asset metadata."""
    # Create asset
    files = {
        "file": ("test.gltf", io.BytesIO(sample_file_content), "model/gltf+json"),
    }
    create_response = await client.post(
        "/api/v1/assets",
        data=sample_asset_data,
        files=files,
    )
    asset_id = create_response.json()["id"]
    
    # Update metadata
    update_data = {
        "name": "updated_molecule",
        "description": "Updated description",
    }
    response = await client.patch(
        f"/api/v1/assets/{asset_id}",
        json=update_data,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "updated_molecule"
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_update_asset_tags(
    client: AsyncClient,
    sample_asset_data: dict,
    sample_file_content: bytes,
):
    """Test replacing asset tags."""
    # Create asset
    files = {
        "file": ("test.gltf", io.BytesIO(sample_file_content), "model/gltf+json"),
    }
    create_response = await client.post(
        "/api/v1/assets",
        data=sample_asset_data,
        files=files,
    )
    asset_id = create_response.json()["id"]
    
    # Update tags
    response = await client.put(
        f"/api/v1/assets/{asset_id}/tags",
        json={"tags": ["newtag1", "newtag2", "UC3"]},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert set(data["tags"]) == {"newtag1", "newtag2", "UC3"}


@pytest.mark.asyncio
async def test_search_assets_by_query(
    client: AsyncClient,
    sample_asset_data: dict,
    sample_file_content: bytes,
):
    """Test searching assets by query string."""
    # Create asset
    files = {
        "file": ("test.gltf", io.BytesIO(sample_file_content), "model/gltf+json"),
    }
    await client.post(
        "/api/v1/assets",
        data=sample_asset_data,
        files=files,
    )
    
    # Search
    response = await client.get("/api/v1/assets", params={"q": "molecule"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any("molecule" in item["name"] for item in data["items"])


@pytest.mark.asyncio
async def test_search_assets_by_format(
    client: AsyncClient,
    sample_asset_data: dict,
    sample_file_content: bytes,
):
    """Test filtering assets by format."""
    # Create asset
    files = {
        "file": ("test.gltf", io.BytesIO(sample_file_content), "model/gltf+json"),
    }
    await client.post(
        "/api/v1/assets",
        data=sample_asset_data,
        files=files,
    )
    
    # Filter by format
    response = await client.get("/api/v1/assets", params={"format": "gltf"})
    
    assert response.status_code == 200
    data = response.json()
    assert all(item["format"] == "gltf" for item in data["items"])


@pytest.mark.asyncio
async def test_delete_asset(
    client: AsyncClient,
    sample_asset_data: dict,
    sample_file_content: bytes,
):
    """Test deleting an asset."""
    # Create asset
    files = {
        "file": ("test.gltf", io.BytesIO(sample_file_content), "model/gltf+json"),
    }
    create_response = await client.post(
        "/api/v1/assets",
        data=sample_asset_data,
        files=files,
    )
    asset_id = create_response.json()["id"]
    
    # Delete
    response = await client.delete(f"/api/v1/assets/{asset_id}")
    assert response.status_code == 204
    
    # Verify deleted
    get_response = await client.get(f"/api/v1/assets/{asset_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_pagination(
    client: AsyncClient,
    sample_asset_data: dict,
    sample_file_content: bytes,
):
    """Test asset list pagination."""
    # Create multiple assets
    for i in range(5):
        data = sample_asset_data.copy()
        data["name"] = f"test_asset_{i}"
        files = {
            "file": (f"test_{i}.gltf", io.BytesIO(sample_file_content), "model/gltf+json"),
        }
        await client.post("/api/v1/assets", data=data, files=files)
    
    # Test pagination
    response = await client.get("/api/v1/assets", params={"page": 1, "size": 2})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["pages"] == 3


@pytest.mark.asyncio
async def test_asset_validation_name_too_long(
    client: AsyncClient,
    sample_file_content: bytes,
):
    """Test that asset name validation works."""
    data = {
        "name": "a" * 101,  # Name too long
        "description": "Test",
        "format": "gltf",
        "triCount": 1000,
    }
    files = {
        "file": ("test.gltf", io.BytesIO(sample_file_content), "model/gltf+json"),
    }
    
    response = await client.post("/api/v1/assets", data=data, files=files)
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_jsonld_response(
    client: AsyncClient,
    sample_asset_data: dict,
    sample_file_content: bytes,
):
    """Test JSON-LD response format."""
    # Create asset
    files = {
        "file": ("test.gltf", io.BytesIO(sample_file_content), "model/gltf+json"),
    }
    create_response = await client.post(
        "/api/v1/assets",
        data=sample_asset_data,
        files=files,
    )
    asset_id = create_response.json()["id"]
    
    # Request JSON-LD format
    response = await client.get(
        f"/api/v1/assets/{asset_id}",
        headers={"Accept": "application/ld+json"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "@context" in data
    assert "@type" in data
    assert "@id" in data
