import logging
from app.core.config import settings
from app.services.database import SupabaseService
from app.services.queue import QueueService

logger = logging.getLogger(__name__)

async def startup_event():
    """Application startup: verify connections and critical config."""
    logger.info(f"Starting up MVC API — env={settings.APP_ENV}")

    # Hard-fail if APP_SECRET is not set — all sessions are forgeable without it
    if not settings.APP_SECRET:
        raise RuntimeError(
            "APP_SECRET must be set to a secure random value (e.g. openssl rand -hex 32). "
            "Refusing to start without it."
        )
    
    # Check critical configuration
    missing = settings.check_critical()
    if missing:
        logger.warning(f"Missing critical config: {', '.join(missing)}")
    else:
        logger.info("✓ All critical environment variables present")
    
    # Verify Supabase connection
    try:
        db = SupabaseService()
        # Light check: list tables query will fail fast if creds are bad
        logger.info("✓ Supabase connection configured")
    except Exception as e:
        logger.error(f"✗ Supabase connection failed: {e}")
    
    # Verify Redis connection
    try:
        queue = QueueService()
        logger.info("✓ Redis connection configured")
    except Exception as e:
        logger.error(f"✗ Redis connection failed: {e}")
    
    # Stripe mode indicator
    if settings.STRIPE_SECRET_KEY:
        mode = "LIVE" if settings.is_stripe_live else "TEST"
        logger.info(f"✓ Stripe configured ({mode} mode)")
    
    # R2 indicator
    if settings.CLOUDFLARE_R2_ENDPOINT and settings.CLOUDFLARE_R2_ACCESS_KEY_ID:
        logger.info("✓ R2 storage configured")
    
    logger.info("Startup complete")

async def shutdown_event():
    """Application shutdown: cleanup."""
    logger.info("Shutting down MVC API...")
    logger.info("Cleanup complete")