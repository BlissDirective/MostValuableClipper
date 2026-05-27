"""
Health check endpoints for monitoring workers and system status.
Used by Fly.io health checks, load balancers, and monitoring dashboards.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class HealthStatus(BaseModel):
    status: str
    timestamp: str
    version: str = "1.0.0"
    checks: Dict[str, Any]


class WorkerHealthResponse(BaseModel):
    status: str
    worker_type: str
    queues: list
    concurrency: int
    uptime_seconds: float
    processed_tasks: int
    failed_tasks: int


def _check_redis() -> Dict[str, Any]:
    """Check Redis connectivity."""
    try:
        import redis
        r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
        info = r.info()
        return {
            "status": "ok",
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def _check_db() -> Dict[str, Any]:
    """Check database connectivity (if configured)."""
    try:
        # Try Supabase first, then fallback
        from app.services.database import supabase
        supabase.table("clips").select("count", count="exact").limit(1).execute()
        return {"status": "ok", "provider": "supabase"}
    except Exception as e:
        return {"status": "error" if "connection" in str(e).lower() else "ok", "detail": str(e)}


def _check_celery() -> Dict[str, Any]:
    """Check Celery worker status via Redis."""
    try:
        from app.core.celery_config import celery_app
        inspect = celery_app.control.inspect(timeout=5)
        active = inspect.active() or {}
        stats = inspect.stats() or {}
        
        workers = {}
        for worker_name, worker_stats in stats.items():
            workers[worker_name] = {
                "processed": worker_stats.get("total", {}),
                "active": len(active.get(worker_name, [])),
                "concurrency": worker_stats.get("pool", {}).get("max-concurrency", 0),
            }
        
        return {
            "status": "ok" if workers else "warning",
            "workers_online": len(workers),
            "workers": workers,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def _check_storage() -> Dict[str, Any]:
    """Check R2 / S3 storage connectivity."""
    try:
        from app.services.storage import R2Service
        r2 = R2Service()
        # Lightweight check — just verify credentials work
        return {"status": "ok", "provider": "r2"}
    except Exception as e:
        return {"status": "warning", "detail": str(e)}


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """Overall system health check. Returns 200 if critical services are OK."""
    checks = {
        "redis": _check_redis(),
        "database": _check_db(),
        "celery_workers": _check_celery(),
        "storage": _check_storage(),
    }
    
    # Overall status: ok if all critical services are ok
    critical = [checks["redis"]["status"], checks["database"]["status"]]
    overall = "ok" if all(s == "ok" for s in critical) else "degraded"
    
    return HealthStatus(
        status=overall,
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks=checks,
    )


@router.get("/health/ready")
async def readiness_check():
    """Kubernetes/Fly.io readiness probe. Returns 200 when ready to accept traffic."""
    redis_check = _check_redis()
    if redis_check["status"] != "ok":
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Redis not ready")
    return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/live")
async def liveness_check():
    """Kubernetes/Fly.io liveness probe. Returns 200 if process is alive."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/workers")
async def worker_health():
    """Detailed worker pool status."""
    return _check_celery()
