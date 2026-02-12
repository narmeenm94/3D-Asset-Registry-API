"""
Association tables for many-to-many relationships.
"""

from sqlalchemy import Column, ForeignKey, String, Table

from app.db.base import Base

# Asset-Tag many-to-many association table
asset_tags = Table(
    "asset_tags",
    Base.metadata,
    Column(
        "asset_id",
        String(36),
        ForeignKey("assets.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        String(36),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
