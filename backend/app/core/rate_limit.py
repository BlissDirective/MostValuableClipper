"""Rate limiting middleware — L-03: in-app DDoS mitigation (tuned).

Two-layer sliding-window approach per client key:
  1. Per-minute window  — sustained throughput cap (existing behaviour).
  2. Per-10-second burst window — absorbs legitimate spikes but blocks floods.

Client key = IP : token-hash (when Bearer token is present) so authenticated
users are tracked separately from anonymous traffic, and a single compromised
IP with many accounts cannot pool quota.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, List, Optional, Tuple
import time
import hashlib
import json


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Tiered rate limiting with burst protection.

    Limits (per minute / per 10-second burst):
    - Auth endpoints  : 10 / min, burst 4 / 10 s  (brute-force + stuffing)
    - Expensive ops   : 30 / min, burst 10 / 10 s  (swarm, clips, worker)
    - Webhooks        : 60 / min, burst 20 / 10 s
    - Public/health   : 600 / min, burst 100 / 10 s
    - Default         : 120 / min, burst 30 / 10 s
    """

    # (per-minute limit, per-10-second burst limit)
    DEFAULT_LIMIT:   Tuple[int, int] = (120, 30)
    AUTH_LIMIT:      Tuple[int, int] = (10,   4)
    EXPENSIVE_LIMIT: Tuple[int, int] = (30,  10)
    WEBHOOK_LIMIT:   Tuple[int, int] = (60,  20)
    PUBLIC_LIMIT:    Tuple[int, int] = (600, 100)

    WINDOW_SECONDS = 60
    BURST_SECONDS  = 10

    # Auth endpoints that support per-email limiting (M-02)
    _AUTH_BODY_PATHS = {"/api/v1/auth/login", "/api/v1/auth/register"}

    AUTH_PATTERNS     = ["/api/v1/auth/", "/api/v1/users/me/subscription"]
    EXPENSIVE_PATTERNS = ["/api/v1/swarm/", "/api/v1/clips/", "/api/v1/worker/"]
    WEBHOOK_PATTERNS   = ["/api/v1/webhooks/"]
    PUBLIC_PATTERNS    = ["/api/v1/health", "/", "/privacy", "/terms", "/dmca"]

    def __init__(self, app):
        super().__init__(app)
        # key -> list[timestamp]  (shared for both window checks)
        self._requests: Dict[str, List[float]] = {}
        self._cleanup_last = time.time()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        ip = forwarded.split(",")[0].strip() if forwarded else (
            request.client.host if request.client else "unknown"
        )
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            token_hash = hashlib.sha256(auth[7:].encode()).hexdigest()[:16]
            return f"{ip}:{token_hash}"
        return ip

    def _get_limits(self, path: str) -> Tuple[int, int]:
        for p in self.PUBLIC_PATTERNS:
            if path == p or path.startswith(p):
                return self.PUBLIC_LIMIT
        for p in self.AUTH_PATTERNS:
            if path.startswith(p):
                return self.AUTH_LIMIT
        for p in self.EXPENSIVE_PATTERNS:
            if path.startswith(p):
                return self.EXPENSIVE_LIMIT
        for p in self.WEBHOOK_PATTERNS:
            if path.startswith(p):
                return self.WEBHOOK_LIMIT
        return self.DEFAULT_LIMIT

    def _is_exempt(self, path: str) -> bool:
        return path.startswith("/api/v1/webhooks/stripe") or path in (
            "/api/v1/health", "/health"
        )

    def _cleanup_old_entries(self):
        now = time.time()
        if now - self._cleanup_last < 30:
            return
        cutoff = now - self.WINDOW_SECONDS * 2
        to_remove = [k for k, ts in self._requests.items()
                     if not [t for t in ts if t > cutoff]]
        for key in to_remove:
            del self._requests[key]
        for key in self._requests:
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        self._cleanup_last = now

    def _rate_limited(
        self, key: str, minute_limit: int, burst_limit: int
    ) -> Optional[Response]:
        """Check both windows. Returns a 429 Response if either is exceeded."""
        now = time.time()
        history = self._requests.setdefault(key, [])
        in_minute = [t for t in history if t > now - self.WINDOW_SECONDS]
        in_burst   = [t for t in in_minute if t > now - self.BURST_SECONDS]

        if len(in_minute) >= minute_limit:
            retry_after = max(1, int(self.WINDOW_SECONDS - (now - in_minute[0])))
            return self._429(minute_limit, retry_after)

        if len(in_burst) >= burst_limit:
            retry_after = max(1, int(self.BURST_SECONDS - (now - in_burst[0])))
            return self._429(burst_limit, retry_after)

        history.append(now)
        return None

    @staticmethod
    def _429(limit: int, retry_after: int) -> Response:
        return Response(
            content='{"detail":"Rate limit exceeded. Please slow down."}',
            status_code=429,
            headers={
                "Content-Type": "application/json",
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(retry_after),
            },
        )

    async def _check_email_limit(self, request: Request, path: str) -> Optional[Response]:
        """Per-email rate limit for login/register (M-02)."""
        if path not in self._AUTH_BODY_PATHS:
            return None
        try:
            body_json = json.loads(await request.body())
            email = str(body_json.get("email", "")).lower().strip()
            if not email:
                return None
        except Exception:
            return None

        key = "email:" + hashlib.sha256(email.encode()).hexdigest()[:24]
        minute_limit, burst_limit = self.AUTH_LIMIT
        return self._rate_limited(key, minute_limit, burst_limit)

    # ------------------------------------------------------------------
    # Main dispatch
    # ------------------------------------------------------------------

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if self._is_exempt(path):
            return await call_next(request)

        self._cleanup_old_entries()

        email_resp = await self._check_email_limit(request, path)
        if email_resp:
            return email_resp

        client_key = self._get_client_key(request)
        minute_limit, burst_limit = self._get_limits(path)

        blocked = self._rate_limited(client_key, minute_limit, burst_limit)
        if blocked:
            return blocked

        response = await call_next(request)

        history = self._requests.get(client_key, [])
        now = time.time()
        in_minute = [t for t in history if t > now - self.WINDOW_SECONDS]
        remaining = max(0, minute_limit - len(in_minute))
        response.headers["X-RateLimit-Limit"] = str(minute_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
