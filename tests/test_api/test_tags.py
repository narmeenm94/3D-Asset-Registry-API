"""
Tests for tag endpoints.
"""

import io
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_tags_empty(client: AsyncClient):
    """Test listing tags when database is empty."""
    response = await client.get("/api/v1/tags")
    
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_tags_created_with_assets(
    client: AsyncClient,
    sample_asset_data: dict,
    sample_file_content: bytes,
):
    """Test that tags are created when assets are created."""
    # Create asset with tags
    files = {
        "file": ("test.gltf", io.BytesIO(sample_file_content), "model/gltf+json"),
    }
    await client.post(
        "/api/v1/assets",
        data=sample_asset_data,
        files=files,
    )
    
    # Check tags exist
    response = await client.get("/api/v1/tags")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    tag_names = [tag["name"] for tag in data["items"]]
    assert "UC2" in tag_names
    assert "molecule" in tag_names


@pytest.mark.asyncio
async def test_tag_usage_count(
    client: AsyncClient,
    sample_asset_data: dict,
    sample_file_content: bytes,
):
    """Test that tag usage counts are tracked."""
    # Create first asset
    files = {
        "file": ("test1.gltf", io.BytesIO(sample_file_content), "model/gltf+json"),
    }
    await client.post(
        "/api/v1/assets",
        data=sample_asset_data,
        files=files,
    )
    
    # Create second asset with same tags
    data2 = sample_asset_data.copy()
    data2["name"] = "test_asset_2"
    files2 = {
        "file": ("test2.gltf", io.BytesIO(sample_file_content), "model/gltf+json"),
    }
    await client.post(
        "/api/v1/assets",
        data=data2,
        files=files2,
    )
    
    # Check tag counts
    response = await client.get("/api/v1/tags")
    data = response.json()
    
    # Find UC2 tag
    uc2_tag = next((t for t in data["items"] if t["name"] == "UC2"), None)
    assert uc2_tag is not None
    assert uc2_tag["usageCount"] == 2


@pytest.mark.asyncio
async def test_popular_tags(
    client: AsyncClient,
    sample_asset_data: dict,
    sample_file_content: bytes,
):
    """Test getting popular tags."""
    # Create assets
    files = {
        "file": ("test.gltf", io.BytesIO(sample_file_content), "model/gltf+json"),
    }
    await client.post(
        "/api/v1/assets",
        data=sample_asset_data,
        files=files,
    )
    
    # Get popular tags
    response = await client.get("/api/v1/tags/popular")
    
    assert response.status_code == 200
    data = response.json()
    assert "tags" in data


@pytest.mark.asyncio
async def test_tag_categories(client: AsyncClient):
    """Test listing tag categories."""
    response = await client.get("/api/v1/tags/categories")
    
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    
    category_ids = [c["id"] for c in data["categories"]]
    assert "use_case" in category_ids
    assert "domain" in category_ids
    assert "technical" in category_ids
