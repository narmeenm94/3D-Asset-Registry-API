"""
Pydantic schemas for Tag request/response validation.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.models.tag import TagCategory


class TagResponse(BaseModel):
    """Response schema for a single tag."""
    
    id: str
    name: str
    category: TagCategory
    usage_count: int = Field(alias="usageCount")
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class TagListResponse(BaseModel):
    """Response schema for tag listing."""
    
    items: list[TagResponse]
    total: int
