#!/usr/bin/env python3
"""
Background worker for processing clip generation jobs and scheduled posts.
Run with: python -m app.workers.clip_worker
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.core.logging import setup_logging
from app.services.queue import QueueService
from app.services.langgraph_service import ClipProcessingPipeline
from app.services.social_posting import SocialPostingService
from app.services.database import SupabaseService

setup_logging()
logger = logging.getLogger(__name__)

async def process_clip_job(job_data: dict) -> dict:
    """Process a single clip generation job."""
    clip_id = job_data.get("clip_id")
    source_id = job_data.get("source_id")
    pipeline_id = job_data.get("pipeline_id")
    user_id = job_data.get("user_id")
    
    logger.info(f"[Worker] Processing clip job: {clip_id}")
    
    try:
        # Initialize pipeline
        pipeline = ClipProcessingPipeline()
        
        # Execute full workflow
        result = await pipeline.process(
            clip_id=clip_id,
            source_id=source_id,
            pipeline_id=pipeline_id,
            user_id=user_id
        )
        
        logger.info(f"[Worker] Clip {clip_id} processed: {result['status']}")
        return result
        
    except Exception as e:
        logger.error(f"[Worker] Failed to process clip {clip_id}: {e}")
        raise

async def process_scheduled_posts():
    """Check for and post scheduled clips."""
    try:
        db = SupabaseService()
        posting_service = SocialPostingService()
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Get clips scheduled for now or earlier that haven't been posted
        # This is a simplified version - real implementation would query Supabase
        logger.info("[Worker] Checking scheduled posts...")
        
    except Exception as e:
        logger.error(f"[Worker] Scheduled post processing failed: {e}")

async def worker_loop():
    """Main worker loop."""
    queue = QueueService()
    logger.info("🎬 MVC Worker started")
    logger.info("   Listening for: clip_generation, scheduled_posts")
    
    while True:
        try:
            # Process clip generation jobs
            job = await queue.dequeue("clip_generation")
            
            if job:
                logger.info(f"[Worker] Got clip job: {job.get('job_id')}")
                
                try:
                    result = await process_clip_job(job)
                    await queue.mark_job_complete(
                        job.get("job_id"),
                        result
                    )
                except Exception as e:
                    await queue.mark_job_failed(
                        job.get("job_id"),
                        str(e)
                    )
            
            # Check scheduled posts
            await process_scheduled_posts()
            
            # Sleep if no jobs
            if not job:
                await asyncio.sleep(5)
                
        except Exception as e:
            logger.error(f"[Worker] Loop error: {e}")
            await asyncio.sleep(10)

def main():
    """Entry point."""
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logger.info("👋 Worker shutting down gracefully")

if __name__ == "__main__":
    main()
