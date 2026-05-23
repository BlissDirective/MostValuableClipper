from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.events import startup_event, shutdown_event
from app.core.rate_limit import RateLimitMiddleware
from app.api import (
    health, users, clips, pipelines, sources, earnings,
    webhooks, social, analytics, legal, auth, subscriptions, swarm, worker, agents
)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    await startup_event()
    yield
    await shutdown_event()

app = FastAPI(
    title="MVC API",
    description="Monetized Video Content - Backend API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/api/redoc" if settings.APP_ENV != "production" else None,
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(clips.router, prefix="/api/v1", tags=["clips"])
app.include_router(pipelines.router, prefix="/api/v1", tags=["pipelines"])
app.include_router(sources.router, prefix="/api/v1", tags=["sources"])
app.include_router(earnings.router, prefix="/api/v1", tags=["earnings"])
app.include_router(subscriptions.router, prefix="/api/v1", tags=["subscriptions"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["webhooks"])
app.include_router(social.router, prefix="/api/v1", tags=["social"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(swarm.router, prefix="/api/v1", tags=["swarm"])
app.include_router(worker.router, prefix="/api/v1", tags=["worker"])
app.include_router(agents.router, prefix="/api/v1", tags=["agents"])

# Legal pages (no API prefix - public pages for social platform requirements)
app.include_router(legal.router, tags=["legal"])

@app.get("/")
async def root():
    return {
        "message": "MVC API", 
        "version": "0.1.0", 
        "docs": "/api/docs",
        "legal": {
            "privacy": "/privacy",
            "terms": "/terms",
            "dmca": "/dmca"
        }
    }
