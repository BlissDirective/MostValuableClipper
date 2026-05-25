from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class HealthCheck(BaseModel):
    status: str
    version: str
    environment: str
    services: Dict[str, str]


async def _check_supabase() -> str:
    try:
        from app.services.database import supabase_admin
        supabase_admin.table("profiles").select("id").limit(1).execute()
        return "connected"
    except Exception as exc:
        logger.warning("[health] Supabase check failed: %s", exc)
        return "degraded"


async def _check_redis() -> str:
    try:
        from app.services.queue import CacheService
        cache = CacheService()
        # Upstash Redis doesn't expose ping(); a benign get suffices
        cache.redis.get("health:ping")
        return "connected"
    except Exception as exc:
        logger.warning("[health] Redis check failed: %s", exc)
        return "degraded"


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint — returns real dependency status (H-09)."""
    from app.core.config import settings

    db_status = await _check_supabase()
    redis_status = await _check_redis()

    overall = "healthy" if db_status == "connected" and redis_status == "connected" else "degraded"

    return HealthCheck(
        status=overall,
        version="0.1.0",
        environment=settings.APP_ENV,
        services={
            "database": db_status,
            "redis": redis_status,
            # R2 is presigned-URL based — no persistent conn to probe
            "storage": "connected",
        },
    )


@router.get("/health/ready")
async def readiness_check():
    """Readiness probe — 503 if critical dependencies are unavailable."""
    db_status = await _check_supabase()
    redis_status = await _check_redis()

    if db_status != "connected" or redis_status != "connected":
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "services": {"database": db_status, "redis": redis_status},
            },
        )
    return {"ready": True}


@router.get("/health/live")
async def liveness_check():
    """Liveness probe — 200 as long as the process is running."""
    return {"alive": True}
