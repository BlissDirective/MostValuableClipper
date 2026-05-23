from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Optional
import time
import hashlib

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Custom rate limiting middleware with tiered limits per endpoint category.
    
    Tracks requests by client IP (with fallback to API key hash for server-to-server).
    Uses in-memory sliding window with automatic cleanup.
    
    Limits:
    - Default: 120 requests/minute
    - Auth (login/register): 10/minute (prevent brute force)
    - Swarm/Remix/Post: 30/minute (expensive operations)
    - Webhooks: 60/minute (external services)
    - Health/Legal: 600/minute (public pages)
    """
    
    DEFAULT_LIMIT = 120  # requests per window
    AUTH_LIMIT = 10
    EXPENSIVE_LIMIT = 30
    WEBHOOK_LIMIT = 60
    PUBLIC_LIMIT = 600
    WINDOW_SECONDS = 60
    
    # Endpoint category patterns
    AUTH_PATTERNS = ["/api/v1/auth/", "/api/v1/users/me/subscription"]
    EXPENSIVE_PATTERNS = ["/api/v1/swarm/", "/api/v1/clips/", "/api/v1/worker/"]
    WEBHOOK_PATTERNS = ["/api/v1/webhooks/"]
    PUBLIC_PATTERNS = ["/api/v1/health", "/", "/privacy", "/terms", "/dmca"]
    
    def __init__(self, app):
        super().__init__(app)
        self._requests: Dict[str, list] = {}  # key -> list of timestamps
        self._cleanup_last = time.time()
    
    def _get_client_key(self, request: Request) -> str:
        """Get a unique key for the client."""
        # Prefer forwarded IP (for proxy/load balancer setups)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        # Include API key hash if present (for server-to-server identification)
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            # Hash token to avoid storing raw credentials
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
            return f"{ip}:{token_hash}"
        
        return ip
    
    def _get_limit(self, path: str) -> int:
        """Determine rate limit based on endpoint path."""
        for pattern in self.PUBLIC_PATTERNS:
            if path.startswith(pattern) or path == pattern:
                return self.PUBLIC_LIMIT
        
        for pattern in self.AUTH_PATTERNS:
            if path.startswith(pattern):
                return self.AUTH_LIMIT
        
        for pattern in self.EXPENSIVE_PATTERNS:
            if path.startswith(pattern):
                return self.EXPENSIVE_LIMIT
        
        for pattern in self.WEBHOOK_PATTERNS:
            if path.startswith(pattern):
                return self.WEBHOOK_LIMIT
        
        return self.DEFAULT_LIMIT
    
    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting."""
        # Stripe webhooks need high throughput
        if path.startswith("/api/v1/webhooks/stripe"):
            return True
        # Health checks
        if path == "/api/v1/health" or path == "/health":
            return True
        return False
    
    def _cleanup_old_entries(self):
        """Remove entries older than the window to prevent memory growth."""
        now = time.time()
        if now - self._cleanup_last < 30:  # Cleanup every 30 seconds
            return
        
        cutoff = now - self.WINDOW_SECONDS * 2
        to_remove = []
        for key, timestamps in self._requests.items():
            self._requests[key] = [t for t in timestamps if t > cutoff]
            if not self._requests[key]:
                to_remove.append(key)
        
        for key in to_remove:
            del self._requests[key]
        
        self._cleanup_last = now
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Skip rate limiting for exempt paths
        if self._is_exempt(path):
            return await call_next(request)
        
        # Periodic cleanup
        self._cleanup_old_entries()
        
        client_key = self._get_client_key(request)
        limit = self._get_limit(path)
        
        now = time.time()
        window_start = now - self.WINDOW_SECONDS
        
        # Get or create request history for this client
        if client_key not in self._requests:
            self._requests[client_key] = []
        
        # Count requests in current window
        recent_requests = [t for t in self._requests[client_key] if t > window_start]
        
        if len(recent_requests) >= limit:
            retry_after = int(self.WINDOW_SECONDS - (now - recent_requests[0]))
            return Response(
                content='{"detail":"Rate limit exceeded. Please slow down."}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(max(1, retry_after))
                }
            )
        
        # Record this request
        self._requests[client_key].append(now)
        
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, limit - len(recent_requests) - 1)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
