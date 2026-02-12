"""
Health and metrics endpoints.
No authentication required as per D9.1 Section 3.1.2 / 8.3.4.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, is_using_sqlite_fallback
from app.models.asset import Asset
from app.services.metrics import get_metrics_collector

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Service health check endpoint.
    
    Returns:
        {"status": "ok"} when service is healthy
        {"status": "degraded", "issues": [...]} when there are issues
    """
    issues = []
    warnings = []
    
    # Check if using SQLite fallback
    if is_using_sqlite_fallback():
        warnings.append("Using SQLite dev fallback - PostgreSQL not available")
    
    # Check database connectivity
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        issues.append(f"Database: {str(e)}")
    
    if issues:
        return {
            "status": "degraded",
            "issues": issues,
        }
    
    response = {
        "status": "ok",
        "database": "sqlite (dev fallback)" if is_using_sqlite_fallback() else "postgresql",
    }
    
    if warnings:
        response["warnings"] = warnings
    
    return response


@router.get("/metrics")
async def metrics(db: AsyncSession = Depends(get_db)):
    """
    Prometheus-compatible metrics endpoint.
    Per D9.1 Section 8.3.4: request counts, response times,
    error rates, and storage utilization.
    
    Returns Prometheus text exposition format when Accept header
    includes text/plain, otherwise returns JSON.
    """
    collector = get_metrics_collector()
    
    # Get storage utilization from DB
    try:
        result = await db.execute(select(func.count(Asset.id)))
        asset_count = result.scalar() or 0
        
        size_result = await db.execute(select(func.sum(Asset.file_size)))
        total_storage_bytes = size_result.scalar() or 0
    except Exception:
        asset_count = -1
        total_storage_bytes = -1
    
    metrics_data = collector.get_metrics()
    metrics_data["storage"] = {
        "total_assets": asset_count,
        "total_storage_bytes": total_storage_bytes,
    }
    
    return metrics_data


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
async def metrics_prometheus(db: AsyncSession = Depends(get_db)):
    """
    Prometheus text exposition format endpoint.
    Compatible with Prometheus scraping.
    """
    collector = get_metrics_collector()
    
    text_output = collector.to_prometheus()
    
    # Append storage metrics
    try:
        result = await db.execute(select(func.count(Asset.id)))
        asset_count = result.scalar() or 0
        
        size_result = await db.execute(select(func.sum(Asset.file_size)))
        total_storage_bytes = size_result.scalar() or 0
        
        text_output += "# HELP metro_assets_total Total number of assets\n"
        text_output += "# TYPE metro_assets_total gauge\n"
        text_output += f"metro_assets_total {asset_count}\n\n"
        text_output += "# HELP metro_storage_bytes_total Total storage used in bytes\n"
        text_output += "# TYPE metro_storage_bytes_total gauge\n"
        text_output += f"metro_storage_bytes_total {total_storage_bytes}\n"
    except Exception:
        pass
    
    return PlainTextResponse(
        content=text_output,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
