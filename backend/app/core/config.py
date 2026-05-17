from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    All values are read from .env file or actual environment.
    Critical keys are validated at startup.
    """
    
    # ============================================
    # Application
    # ============================================
    APP_ENV: str = "development"
    APP_SECRET: str = "change-me-in-production"
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS — comma-separated string for env compatibility
    CORS_ORIGINS_STR: str = "http://localhost:3000,http://localhost:8081,https://*.fly.dev"
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS_STR.split(",") if o.strip()]
    
    # ============================================
    # Supabase (Database + Auth)
    # ============================================
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    
    # ============================================
    # Upstash Redis (Queue + Cache)
    # ============================================
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""
    
    # ============================================
    # Cloudflare R2 (Object Storage)
    # ============================================
    CLOUDFLARE_ACCOUNT_ID: str = ""
    CLOUDFLARE_R2_ACCESS_KEY_ID: str = ""
    CLOUDFLARE_R2_SECRET_ACCESS_KEY: str = ""
    CLOUDFLARE_R2_API_TOKEN: Optional[str] = None
    CLOUDFLARE_R2_BUCKET: str = "mvc-clips"
    CLOUDFLARE_R2_ENDPOINT: str = ""
    CLOUDFLARE_R2_PUBLIC_URL: Optional[str] = None  # e.g. https://pub-xxx.r2.dev
    
    # ============================================
    # Stripe (Payments)
    # ============================================
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_BASIC: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_ENTERPRISE: str = ""
    
    # ============================================
    # AI / LLM (Optional — will warn if missing)
    # ============================================
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # ============================================
    # Zernio (Unified Social API)
    # ============================================
    ZERNIO_API_KEY: Optional[str] = None

    # ============================================
    # Social Platform OAuth (Phase 2 — optional)
    # ============================================
    TIKTOK_CLIENT_ID: Optional[str] = None
    TIKTOK_CLIENT_SECRET: Optional[str] = None
    INSTAGRAM_CLIENT_ID: Optional[str] = None
    INSTAGRAM_CLIENT_SECRET: Optional[str] = None
    YOUTUBE_CLIENT_ID: Optional[str] = None
    YOUTUBE_CLIENT_SECRET: Optional[str] = None
    
    # ============================================
    # Error Tracking (Optional)
    # ============================================
    SENTRY_DSN_BACKEND: Optional[str] = None
    SENTRY_DSN_FRONTEND: Optional[str] = None
    
    # ============================================
    # GitHub (Repo Access + Actions)
    # ============================================
    GH_TOKEN: Optional[str] = None
    
    # ============================================
    # Fly.io
    # ============================================
    FLY_APP_NAME: Optional[str] = None
    FLY_REGION: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # ignore unknown env vars

    # ============================================
    # Validation helpers
    # ============================================
    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in ("production", "prod")
    
    @property
    def is_stripe_live(self) -> bool:
        """True if using live Stripe keys (starts with sk_live_ or pk_live_)."""
        return "live" in self.STRIPE_SECRET_KEY or "live" in self.STRIPE_PUBLISHABLE_KEY
    
    def check_critical(self) -> List[str]:
        """Return list of missing critical configuration keys."""
        missing = []
        critical = [
            ("SUPABASE_URL", "Supabase URL"),
            ("SUPABASE_SERVICE_ROLE_KEY", "Supabase Service Role Key"),
            ("UPSTASH_REDIS_REST_URL", "Upstash Redis URL"),
            ("UPSTASH_REDIS_REST_TOKEN", "Upstash Redis Token"),
            ("CLOUDFLARE_R2_ENDPOINT", "R2 Endpoint"),
            ("CLOUDFLARE_R2_ACCESS_KEY_ID", "R2 Access Key"),
            ("CLOUDFLARE_R2_SECRET_ACCESS_KEY", "R2 Secret Key"),
            ("STRIPE_SECRET_KEY", "Stripe Secret Key"),
        ]
        for attr, label in critical:
            if not getattr(self, attr):
                missing.append(label)
        return missing

@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — use this in FastAPI dependencies."""
    return Settings()

# Backward-compatible global
settings = get_settings()

