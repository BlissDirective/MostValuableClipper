#!/usr/bin/env python3
"""
Unified background worker for MVC.
Handles both clip generation and scheduled posting.

Run with: python -m app.workers.unified_worker
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.core.logging import setup_logging
from app.services.queue import QueueService
from app.services.langgraph_service import ClipProcessingPipeline
from app.services.scheduler import PostScheduler, MetricsSyncScheduler
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
        pipeline = ClipProcessingPipeline()
        
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

async def worker_loop():
    """Main unified worker loop."""
    queue = QueueService()
    scheduler = PostScheduler()
    metrics_sync = MetricsSyncScheduler()
    
    logger.info("🎬 MVC Unified Worker started")
    logger.info("   Clip generation queue: clip_generation")
    logger.info("   Post scheduler: every 60s")
    logger.info("   Metrics sync: every 300s")
    
    last_scheduler_run = 0
    last_metrics_sync = 0
    
    while True:
        try:
            now = datetime.now(timezone.utc).timestamp()
            
            # 1. Process clip generation jobs
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
            
            # 2. Run scheduler every 60 seconds
            if now - last_scheduler_run >= 60:
                await scheduler.run_scheduler_cycle()
                last_scheduler_run = now
            
            # 3. Sync metrics every 5 minutes
            if now - last_metrics_sync >= 300:
                await metrics_sync.sync_all_metrics()
                last_metrics_sync = now
            
            # Sleep if no jobs
            if not job:
                await asyncio.sleep(2)
                
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
