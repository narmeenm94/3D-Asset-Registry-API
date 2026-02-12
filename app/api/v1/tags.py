"""
Tag endpoints - Full implementation.
Implements D9.1 Section 3.1.2 API Endpoint Specification.
"""

from fastapi import APIRouter, Query

from app.dependencies import DbSession
from app.models.tag import TagCategory
from app.schemas.tag import TagListResponse, TagResponse
from app.services.tag_service import TagService

router = APIRouter()


@router.get("", response_model=TagListResponse)
async def list_tags(
    db: DbSession,
    category: TagCategory | None = Query(default=None, description="Filter by category"),
    q: str | None = Query(default=None, description="Search query"),
):
    """
    List all tags with usage counts.
    
    Optionally filter by category or search by name.
    Tags are ordered by usage count (most used first).
    """
    service = TagService(db)
    
    if q:
        tags = await service.search(q)
        total = len(tags)
    elif category:
        tags = await service.list_by_category(category)
        total = len(tags)
    else:
        tags, total = await service.list_all()
    
    items = [
        TagResponse(
            id=tag.id,
            name=tag.name,
            category=tag.category,
            usageCount=tag.usage_count,
        )
        for tag in tags
    ]
    
    return TagListResponse(items=items, total=total)


@router.get("/popular")
async def get_popular_tags(
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100, description="Number of tags to return"),
):
    """
    Get most popular tags.
    
    Returns tags with the highest usage counts.
    """
    service = TagService(db)
    tags = await service.get_popular(limit=limit)
    
    items = [
        {
            "name": tag.name,
            "category": tag.category.value,
            "usageCount": tag.usage_count,
        }
        for tag in tags
    ]
    
    return {"tags": items, "total": len(items)}


@router.get("/categories")
async def list_tag_categories():
    """
    List available tag categories.
    
    Returns the tag category taxonomy per D9.1 Section 5.2.1.
    """
    categories = [
        {
            "id": cat.value,
            "name": cat.name.replace("_", " ").title(),
            "description": _get_category_description(cat),
            "examples": _get_category_examples(cat),
        }
        for cat in TagCategory
    ]
    
    return {"categories": categories}


def _get_category_description(category: TagCategory) -> str:
    """Get description for a tag category."""
    descriptions = {
        TagCategory.USE_CASE: "Project use case classification (UC2-UC5)",
        TagCategory.DOMAIN: "Scientific field identification (molecule, admet, etc.)",
        TagCategory.TECHNICAL: "Technical characteristics (lowpoly, lod, mobile, xr)",
        TagCategory.GEOGRAPHIC: "Geographic data context (location-specific)",
        TagCategory.TEMPORAL: "Time-based context (quarters, dates)",
        TagCategory.GENERAL: "General purpose tags",
    }
    return descriptions.get(category, "")


def _get_category_examples(category: TagCategory) -> list[str]:
    """Get example tags for a category."""
    examples = {
        TagCategory.USE_CASE: ["UC2", "UC3", "UC4", "UC5"],
        TagCategory.DOMAIN: ["molecule", "admet", "cancer", "dopamine", "aq"],
        TagCategory.TECHNICAL: ["lowpoly", "lod", "mobile", "xr", "optimized"],
        TagCategory.GEOGRAPHIC: ["helsinki", "brno", "barcelona", "munich"],
        TagCategory.TEMPORAL: ["2025q1", "latest", "march2025"],
        TagCategory.GENERAL: ["template", "example", "reference"],
    }
    return examples.get(category, [])
