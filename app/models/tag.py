"""
Tag SQLAlchemy model.
Aligned with D9.1 Section 5.2.1 Tagging Strategy.
"""

import enum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.asset import Asset


class TagCategory(str, enum.Enum):
    """
    Tag categories per D9.1 Section 5.2.1 Tagging Strategy.
    """
    USE_CASE = "use_case"       # UC2, UC3, UC4, UC5
    DOMAIN = "domain"           # molecule, admet, aq, cancer, dopamine
    TECHNICAL = "technical"     # lowpoly, lod, mobile, xr
    GEOGRAPHIC = "geographic"   # brno, helsinki, barcelona
    TEMPORAL = "temporal"       # 2025q1, march2025, latest
    GENERAL = "general"         # Uncategorized tags


class Tag(Base):
    """
    Tag entity model for asset classification and discovery.
    
    Tags support the discovery workflow defined in D9.1 Section 6.1
    and follow the tagging strategy in Section 5.2.1.
    """
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        comment="Tag unique identifier",
    )
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Tag name (1-50 chars, unique)",
    )
    category: Mapped[TagCategory] = mapped_column(
        Enum(TagCategory),
        nullable=False,
        default=TagCategory.GENERAL,
        index=True,
        comment="Tag category for organization",
    )
    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of assets using this tag (denormalized)",
    )

    # Relationship to assets
    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        secondary="asset_tags",
        back_populates="tags",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Tag(name={self.name}, category={self.category})>"
