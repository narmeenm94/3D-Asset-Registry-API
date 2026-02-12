"""
Tag service - Business logic for tag operations.
"""

from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag, TagCategory


class TagService:
    """Service class for tag operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def list_all(self) -> tuple[Sequence[Tag], int]:
        """
        List all tags with usage counts.
        
        Returns:
            Tuple of (list of tags, total count)
        """
        # Get all tags ordered by usage count
        query = select(Tag).order_by(Tag.usage_count.desc(), Tag.name.asc())
        result = await self.db.execute(query)
        tags = result.scalars().all()
        
        return tags, len(tags)
    
    async def list_by_category(self, category: TagCategory) -> Sequence[Tag]:
        """
        List tags in a specific category.
        
        Args:
            category: Tag category to filter by
            
        Returns:
            List of tags in the category
        """
        query = (
            select(Tag)
            .where(Tag.category == category)
            .order_by(Tag.usage_count.desc(), Tag.name.asc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_popular(self, limit: int = 20) -> Sequence[Tag]:
        """
        Get most popular tags.
        
        Args:
            limit: Maximum number of tags to return
            
        Returns:
            List of most used tags
        """
        query = (
            select(Tag)
            .where(Tag.usage_count > 0)
            .order_by(Tag.usage_count.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def search(self, query_str: str) -> Sequence[Tag]:
        """
        Search tags by name.
        
        Args:
            query_str: Search query
            
        Returns:
            List of matching tags
        """
        query = (
            select(Tag)
            .where(Tag.name.ilike(f"%{query_str}%"))
            .order_by(Tag.usage_count.desc())
            .limit(50)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
