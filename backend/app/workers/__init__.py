#!/usr/bin/env python3
"""
Background worker for processing clip generation jobs.
Run with: python -m app.workers.clip_worker
"""
import asyncio
import logging
import json
from typing import Optional

from app.core.config import settings
from app.core.logging import setup_logging
from app.services.queue import QueueService
from app.services.langgraph_service import LangGraphService

setup_logging()
logger = logging.getLogger(__name__)

async def process_clip_job(job_data: dict):
    """Process a single clip generation job."""
    clip_id = job_data.get("clip_id")
    source_id = job_data.get("source_id")
    
    logger.info(f"Processing clip job: {clip_id}")
    
    try:
        # Initialize LangGraph workflow
        service = LangGraphService()
        result = await service.process_clip(clip_id, source_id)
        
        logger.info(f"Clip {clip_id} processed: {result['status']}")
        return result
    except Exception as e:
        logger.error(f"Failed to process clip {clip_id}: {e}")
        raise

async def worker_loop():
    """Main worker loop."""
    queue = QueueService()
    logger.info("🎬 Clip worker started")
    
    while True:
        try:
            # Get next job from queue
            job = await queue.dequeue("clip_generation")
            
            if job:
                logger.info(f"Got job: {job.get('job_id')}")
                
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
            else:
                # No jobs, wait before checking again
                await asyncio.sleep(5)
                
        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(10)

def main():
    """Entry point."""
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logger.info("👋 Worker shutting down")

if __name__ == "__main__":
    main()
