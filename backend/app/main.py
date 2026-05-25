from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import logging
import os
import uuid as _uuid

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

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    # Only add HSTS on production (where HTTPS is guaranteed)
}

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        for key, value in _SECURITY_HEADERS.items():
            response.headers[key] = value
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Propagate or generate X-Request-ID for distributed tracing (L-01)."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(_uuid.uuid4())
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# Middleware — order matters: outermost runs last on responses
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
)

# Exception handlers — H-01: never leak internal error details to clients

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Intercept all HTTPExceptions: log 5xx details internally, return generic message."""
    if exc.status_code >= 500:
        logger.error(
            "HTTP %d at %s: %s",
            exc.status_code,
            request.url.path,
            exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": "Internal server error"},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# M-01 (CSRF): This API uses JWT Bearer token auth — credentials are sent in
# Authorization headers, not cookies. Browsers never auto-attach Bearer tokens
# cross-origin, so CSRF is not applicable. The CORS origin whitelist provides
# additional defence-in-depth. No CSRF tokens needed.

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception at %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
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

from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import FileResponse

# ── WEB APP (Expo export, served at /app) ───────────────────
web_dist_path = os.path.join(os.path.dirname(__file__), "../frontend/dist")
if os.path.exists(web_dist_path):
    # Mount static files for assets, but handle SPA routing manually
    app.mount("/app/assets", StaticFiles(directory=os.path.join(web_dist_path, "assets")), name="assets")
    app.mount("/app/_expo", StaticFiles(directory=os.path.join(web_dist_path, "_expo")), name="expo")
    
    @app.get("/app", response_class=FileResponse)
    async def serve_app_root():
        return FileResponse(os.path.join(web_dist_path, "index.html"))
    
    @app.get("/app/{full_path:path}", response_class=FileResponse)
    async def serve_app_spa(full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/"):
            raise StarletteHTTPException(status_code=404)
        # Serve index.html for all client-side routes
        return FileResponse(os.path.join(web_dist_path, "index.html"))

# ── LANDING PAGE (served at root /) ──────────────────────────
landing_dist_path = os.path.join(os.path.dirname(__file__), "../landing/dist")
if os.path.exists(landing_dist_path):
    # Serve static assets for landing page
    app.mount("/assets", StaticFiles(directory=os.path.join(landing_dist_path, "assets")), name="landing_assets")
    
    @app.get("/", response_class=FileResponse)
    async def serve_landing_root():
        return FileResponse(os.path.join(landing_dist_path, "index.html"))
    
    @app.get("/{path:path}", response_class=FileResponse)
    async def serve_landing_spa(path: str):
        # Don't intercept API, app, or legal routes
        if path.startswith("api/") or path.startswith("app/") or path in ("privacy", "terms", "dmca"):
            raise StarletteHTTPException(status_code=404)
        # Check if file exists (for assets), otherwise serve index.html
        file_path = os.path.join(landing_dist_path, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(landing_dist_path, "index.html"))
