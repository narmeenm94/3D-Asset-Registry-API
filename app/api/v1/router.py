"""
API v1 Router - Aggregates all v1 endpoints.
Base Path: /api/v1
"""

from fastapi import APIRouter

from app.api.v1 import assets, tags, health

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
