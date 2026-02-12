"""
METRO 3D Asset Registry API - Main Application Entry Point.

This is the FastAPI application for the DTRIP4H 3D Asset Registry,
implementing the D9.1 Architecture Design Document specifications.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.exceptions import MetroAPIException
from app.api.v1.router import api_router
from app.services.metrics import MetricsMiddleware

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME}")
    logger.info(f"Storage backend: {settings.STORAGE_BACKEND}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Dev mode (bypass auth): {settings.DEV_MODE}")
    
    # Import session helpers
    from app.db.session import engine, is_using_sqlite_fallback, get_active_database_url
    
    # Show database status
    if is_using_sqlite_fallback():
        logger.warning("[DEV MODE] Using SQLite fallback database")
    else:
        logger.info(f"Database: PostgreSQL")
    
    # Auto-create tables for SQLite (dev mode)
    if is_using_sqlite_fallback():
        logger.info("Creating SQLite development tables...")
        from app.db.base import Base
        # Import all models to register them
        from app.models import Asset, AssetVersion, Tag, asset_tags  # noqa: F401
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Development database ready")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
## METRO 3D Asset Registry API

RESTful API for managing 3D assets within the DTRIP4H project ecosystem.

### Features
- **Asset Management**: Upload, search, download, and manage 3D assets
- **Version Control**: Immutable versioning with rollback capabilities
- **Tag System**: Flexible tagging for asset discovery
- **JSON-LD Support**: Semantic metadata with content negotiation
- **Federated Authentication**: DDTE JWT token integration

### Supported Formats
- glTF 2.0 (.gltf, .glb)
- USDZ (.usdz)
- Blender (.blend)
- FBX (.fbx)

### Documentation
- [D9.1 Architecture Design Document](https://dtrip4h.eu/docs/d9.1)
- [RDF Metadata Framework](https://dtrip4h.eu/docs/rdf)
    """,
    version="1.0.0",
    openapi_tags=[
        {"name": "assets", "description": "3D Asset management operations"},
        {"name": "tags", "description": "Tag management operations"},
        {"name": "health", "description": "Service health checks"},
    ],
    lifespan=lifespan,
)

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics middleware for request tracking (D9.1 Section 8.3.4)
app.add_middleware(MetricsMiddleware)


@app.exception_handler(MetroAPIException)
async def metro_exception_handler(request: Request, exc: MetroAPIException) -> JSONResponse:
    """
    Global exception handler for METRO API exceptions.
    Returns standardized error responses per D9.1 Section 3.1.3.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all exception handler for unexpected errors.
    Logs the full error but returns a sanitized response.
    """
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred",
        },
    )


# Include API routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirects to API documentation."""
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "api": settings.API_V1_PREFIX,
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
