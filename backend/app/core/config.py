from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_ENV: str = "development"
    APP_SECRET: str = "change-me-in-production"
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8081", "https://*.fly.dev"]
    
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    
    # Upstash Redis
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""
    
    # Cloudflare R2
    CLOUDFLARE_ACCOUNT_ID: str = ""
    CLOUDFLARE_R2_ACCESS_KEY_ID: str = ""
    CLOUDFLARE_R2_SECRET_ACCESS_KEY: str = ""
    CLOUDFLARE_R2_BUCKET: str = "mvc-clips"
    CLOUDFLARE_R2_ENDPOINT: str = ""
    
    # Stripe
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""  # Live or test depending on env
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_BASIC: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_ENTERPRISE: str = ""
    
    # AI/ML (Optional)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Social Platform OAuth (Phase 2)
    TIKTOK_CLIENT_ID: Optional[str] = None
    TIKTOK_CLIENT_SECRET: Optional[str] = None
    INSTAGRAM_CLIENT_ID: Optional[str] = None
    INSTAGRAM_CLIENT_SECRET: Optional[str] = None
    YOUTUBE_CLIENT_ID: Optional[str] = None
    YOUTUBE_CLIENT_SECRET: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
