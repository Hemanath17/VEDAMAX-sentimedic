"""Health check routes."""

from fastapi import APIRouter
from src.config.settings import settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health():
    """Basic health check."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
    }


@router.get("/ready")
async def readiness():
    """Readiness check - verifies dependencies."""
    # TODO: Add checks for Qdrant, LLM, etc.
    return {
        "status": "ready",
        "dependencies": {
            "qdrant": "connected",  # TODO: Implement actual check
            "llm": "available",  # TODO: Implement actual check
        },
    }


@router.get("/live")
async def liveness():
    """Liveness check."""
    return {"status": "alive"}

