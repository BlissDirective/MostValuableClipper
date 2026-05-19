from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict

router = APIRouter()

class HealthCheck(BaseModel):
    status: str
    version: str
    environment: str
    services: Dict[str, str]

@router.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    return HealthCheck(
        status="healthy",
        version="0.1.0",
        environment="development",
        services={
            "database": "connected",
            "redis": "connected",
            "storage": "connected"
        }
    )

@router.get("/health/ready")
async def readiness_check():
    """Readiness probe for orchestration."""
    return {"ready": True}

@router.get("/health/live")
async def liveness_check():
    """Liveness probe for orchestration."""
    return {"alive": True}
