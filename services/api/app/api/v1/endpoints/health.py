"""Health check endpoint — no authentication required."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return service health status."""
    return {
        "status": "ok",
        "service": "aftermind-api",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
    }
