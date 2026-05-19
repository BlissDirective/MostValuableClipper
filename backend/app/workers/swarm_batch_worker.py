"""Background worker for swarm batch jobs.

Consumes from the 'swarm_batch' Redis queue and processes
batch swarm jobs asynchronously with real-time progress tracking.

Run with: python -m app.workers.swarm_batch_worker
"""
import asyncio
import json
import logging
import signal
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.logging import setup_logging
from app.services.queue import QueueService, CacheService
from app.services.swarm_batch_service import SwarmBatchService
from app.services.swarm_orchestrator import swarm_orchestrator
from app.services.database import supabase

setup_logging()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Worker State
# ─────────────────────────────────────────────────────────────

shutdown_event = asyncio.Event()


def handle_signal(sig, frame):
    """Graceful shutdown on SIGINT/SIGTERM."""
    logger.info(f"[BatchWorker] Received signal {sig}, shutting down gracefully...")
    shutdown_event.set()


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


# ─────────────────────────────────────────────────────────────
# Progress Publishing
# ─────────────────────────────────────────────────────────────

class BatchProgressPublisher:
    """Publishes batch progress updates for real-time frontend tracking."""
    
    def __init__(self):
        self.cache = CacheService()
        self._batch_key = lambda batch_id: f"batch:{batch_id}:progress"
        self._batch_channel = lambda batch_id: f"batch:{batch_id}:updates"
    
    async def publish_progress(
        self,
        batch_id: str,
        processed: int,
        total: int,
        failed: int,
        current_clip: Optional[str] = None,
        current_status: str = "processing",
        detail: Optional[str] = None,
    ):
        """Publish progress update to cache and optionally Supabase realtime."""
        progress = {
            "batch_id": batch_id,
            "processed": processed,
            "total": total,
            "failed": failed,
            "percent": round((processed / max(total, 1)) * 100, 1),
            "current_clip": current_clip,
            "current_status": current_status,
            "detail": detail,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Cache progress for quick polling
        await self.cache.set(
            self._batch_key(batch_id),
            progress,
            ttl_seconds=86400,  # 24 hours
        )
        
        # Update Supabase for persistent tracking and realtime subscriptions
        try:
            supabase.table("swarm_batch_jobs").update({
                "processed_clips": processed,
                "failed_clips": failed,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "current_clip_id": current_clip,
            }).eq("batch_id", batch_id).execute()
        except Exception as e:
            logger.warning(f"[BatchWorker] Failed to update Supabase progress: {e}")
    
    async def publish_clip_result(
        self,
        batch_id: str,
        clip_id: str,
        result: Dict[str, Any],
    ):
        """Publish individual clip completion."""
        try:
            supabase.table("swarm_batch_clip_results").update({
                "status": result.get("status", "completed"),
                "result_data": result.get("result_data"),
                "cost_cents": result.get("cost_cents", 0),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("batch_id", batch_id).eq("clip_id", clip_id).execute()
        except Exception as e:
            logger.warning(f"[BatchWorker] Failed to update clip result: {e}")
    
    async def get_progress(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get cached progress for a batch."""
        return await self.cache.get(self._batch_key(batch_id))


# ─────────────────────────────────────────────────────────────
# Batch Job Processing
# ─────────────────────────────────────────────────────────────

async def process_batch_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single batch swarm job from the queue."""
    batch_id = job_data.get("batch_id")
    clip_ids = job_data.get("clip_ids", [])
    pool_type = job_data.get("pool_type")
    user_id = job_data.get("user_id")
    agent_count = job_data.get("agent_count")
    strategy_filter = job_data.get("strategy_filter")
    priority = job_data.get("priority", "balanced")
    shared_context = job_data.get("shared_context", True)
    custom_options = job_data.get("custom_options", {})
    
    logger.info(
        f"[BatchWorker] Starting batch {batch_id}: "
        f"{len(clip_ids)} clips, pool={pool_type}, priority={priority}"
    )
    
    publisher = BatchProgressPublisher()
    batch_service = SwarmBatchService(swarm_orchestrator)
    
    # Publish initial progress
    await publisher.publish_progress(
        batch_id=batch_id,
        processed=0,
        total=len(clip_ids),
        failed=0,
        current_status="running",
        detail="Initializing batch execution",
    )
    
    try:
        # Execute the batch with progress callbacks
        result = await batch_service.execute_batch(
            clip_ids=clip_ids,
            pool_type=pool_type,
            user_id=user_id,
            agent_count=agent_count,
            strategy_filter=strategy_filter,
            priority=priority,
            shared_context=shared_context,
            custom_options=custom_options,
            progress_callback=publisher.publish_progress,
            clip_result_callback=publisher.publish_clip_result,
        )
        
        logger.info(
            f"[BatchWorker] Batch {batch_id} completed: "
            f"{result.get('processed_clips')}/{result.get('total_clips')} clips, "
            f"status={result.get('status')}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"[BatchWorker] Batch {batch_id} failed: {e}")
        
        # Mark batch as failed
        try:
            supabase.table("swarm_batch_jobs").update({
                "status": "failed",
                "error": str(e),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("batch_id", batch_id).execute()
        except Exception as db_err:
            logger.warning(f"[BatchWorker] Failed to mark batch failed: {db_err}")
        
        raise


# ─────────────────────────────────────────────────────────────
# Main Worker Loop
# ─────────────────────────────────────────────────────────────

async def worker_loop():
    """Main worker loop consuming from the swarm_batch queue."""
    queue = QueueService()
    cache = CacheService()
    
    logger.info("🐝 Swarm Batch Worker started")
    logger.info(f"   Queue: swarm_batch")
    logger.info(f"   Poll interval: 2s")
    logger.info(f"   Redis: {settings.UPSTASH_REDIS_REST_URL[:30]}...")
    
    consecutive_errors = 0
    max_consecutive_errors = 10
    
    while not shutdown_event.is_set():
        try:
            # Check for shutdown
            if shutdown_event.is_set():
                break
            
            # Dequeue next batch job (priority queue first)
            job = await queue.dequeue_with_priority("swarm_batch")
            
            if job:
                consecutive_errors = 0
                job_id = job.get("job_id", "unknown")
                logger.info(f"[BatchWorker] Got job {job_id}")
                
                try:
                    result = await process_batch_job(job)
                    await queue.mark_job_complete(job_id, result)
                except Exception as e:
                    await queue.mark_job_failed(job_id, str(e))
                    logger.error(f"[BatchWorker] Job {job_id} failed: {e}")
            else:
                # No jobs available — sleep before polling again
                await asyncio.sleep(2)
                
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"[BatchWorker] Loop error ({consecutive_errors}/{max_consecutive_errors}): {e}")
            
            if consecutive_errors >= max_consecutive_errors:
                logger.critical("[BatchWorker] Too many consecutive errors, shutting down.")
                break
                
            await asyncio.sleep(min(2 ** consecutive_errors, 60))
    
    logger.info("👋 Batch worker shutting down gracefully")


def main():
    """Entry point."""
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logger.info("👋 Batch worker interrupted")
    except Exception as e:
        logger.critical(f"[BatchWorker] Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
