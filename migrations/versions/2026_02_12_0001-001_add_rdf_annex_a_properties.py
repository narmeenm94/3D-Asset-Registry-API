"""Add RDF Annex A properties and expand asset format enum

Adds:
- lineage_id, derived_from_asset (lineage & derivation)
- project_phase, theme, access_scope, geo_restrictions,
  usage_constraints, visualization_capabilities,
  usage_guidelines, deployment_notes (Annex A RDF properties)
- Expands asset format enum with obj, stl, ply

Revision ID: 001
Revises: None
Create Date: 2026-02-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Lineage & Derivation ---
    op.add_column(
        "assets",
        sa.Column("lineage_id", sa.String(36), nullable=True, comment="Stable UUID grouping all versions of the same logical asset across nodes/URLs"),
    )
    op.create_index("ix_assets_lineage_id", "assets", ["lineage_id"])
    
    op.add_column(
        "assets",
        sa.Column("derived_from_asset", sa.JSON(), nullable=True, comment="URI(s) of parent asset/version when this is a fork/derivative"),
    )
    
    # --- Additional RDF Annex A Properties ---
    op.add_column(
        "assets",
        sa.Column("project_phase", sa.String(50), nullable=True, comment="Project phase (e.g., prototype, production, archived)"),
    )
    op.add_column(
        "assets",
        sa.Column("theme", sa.JSON(), nullable=True, comment="DCAT theme classification"),
    )
    op.add_column(
        "assets",
        sa.Column("access_scope", sa.JSON(), nullable=True, comment="Array of OAuth scopes required for access"),
    )
    op.add_column(
        "assets",
        sa.Column("geo_restrictions", sa.JSON(), nullable=True, comment="Array of geographic restriction codes (ISO 3166)"),
    )
    op.add_column(
        "assets",
        sa.Column("usage_constraints", sa.Text(), nullable=True, comment="Usage constraints/limitations description"),
    )
    op.add_column(
        "assets",
        sa.Column("visualization_capabilities", sa.JSON(), nullable=True, comment="Visualization capabilities info"),
    )
    op.add_column(
        "assets",
        sa.Column("usage_guidelines", sa.JSON(), nullable=True, comment="Usage instructions and guidelines"),
    )
    op.add_column(
        "assets",
        sa.Column("deployment_notes", sa.Text(), nullable=True, comment="Deployment or integration notes"),
    )
    
    # --- Expand AssetFormat enum ---
    # For PostgreSQL, we need to add new values to the enum type.
    # This uses ALTER TYPE which is PostgreSQL-specific.
    # SQLite does not have enums, so this is a no-op there.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE assetformat ADD VALUE IF NOT EXISTS 'obj'")
        op.execute("ALTER TYPE assetformat ADD VALUE IF NOT EXISTS 'stl'")
        op.execute("ALTER TYPE assetformat ADD VALUE IF NOT EXISTS 'ply'")


def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_column("assets", "deployment_notes")
    op.drop_column("assets", "usage_guidelines")
    op.drop_column("assets", "visualization_capabilities")
    op.drop_column("assets", "usage_constraints")
    op.drop_column("assets", "geo_restrictions")
    op.drop_column("assets", "access_scope")
    op.drop_column("assets", "theme")
    op.drop_column("assets", "project_phase")
    op.drop_column("assets", "derived_from_asset")
    op.drop_index("ix_assets_lineage_id", "assets")
    op.drop_column("assets", "lineage_id")
    
    # Note: PostgreSQL enum values cannot be removed without recreating the type.
    # The extra enum values (obj, stl, ply) will remain after downgrade.
