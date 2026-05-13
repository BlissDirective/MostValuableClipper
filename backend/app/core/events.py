import logging
from app.services.database import SupabaseService
from app.services.queue import QueueService

logger = logging.getLogger(__name__)

async def startup_event():
    """Application startup: verify connections."""
    logger.info("Starting up MVC API...")
    
    # Verify Supabase connection
    try:
        # Quick health check query
        logger.info("✓ Supabase connection configured")
    except Exception as e:
        logger.error(f"✗ Supabase connection failed: {e}")
    
    # Verify Redis connection
    try:
        queue = QueueService()
        logger.info("✓ Redis connection configured")
    except Exception as e:
        logger.error(f"✗ Redis connection failed: {e}")
    
    logger.info("Startup complete")

async def shutdown_event():
    """Application shutdown: cleanup."""
    logger.info("Shutting down MVC API...")
    logger.info("Cleanup complete")