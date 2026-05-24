#!/usr/bin/env python3
"""
Clip Edit Worker

Processes clip_edit queue jobs using FFmpeg.
Run: python scripts/edit_worker.py

This worker should be run as a background process or scheduled job.
For production, use a proper worker system like Celery or RQ.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.queue import QueueService
from app.services.ffmpeg_service import FFmpegEditService
from app.services.database import SupabaseService
from app.core.config import settings

queue = QueueService()
ffmpeg = FFmpegEditService()
db = SupabaseService()

async def process_edit_job(job_data: dict):
    """Process a single clip edit job."""
    job_id = job_data.get("job_id", "unknown")
    clip_id = job_data.get("clip_id")
    user_id = job_data.get("user_id")
    source_url = job_data.get("source_url")
    recipe = job_data.get("recipe", {})
    
    print(f"[Worker] Processing edit job {job_id} for clip {clip_id}")
    
    try:
        # Update status to processing
        await db.update_clip(clip_id, {"status": "generating"})
        await queue.mark_job_complete(job_id, {"status": "processing"})
        
        # Run FFmpeg edit
        result = await ffmpeg.edit_clip(clip_id, source_url, recipe)
        
        if result.get("success"):
            # Update clip with new video URL
            await db.update_clip(clip_id, {
                "video_url": result["video_url"],
                "status": "rendered",
                "duration": result.get("duration"),
                "width": result.get("width"),
                "height": result.get("height"),
                "edit_job_id": None,
                "edit_recipe": None
            })
            
            await queue.mark_job_complete(job_id, {
                "status": "completed",
                "video_url": result["video_url"],
                "duration": result.get("duration")
            })
            
            print(f"[Worker] Edit completed: {result['video_url']}")
        else:
            # Mark as failed
            await db.update_clip(clip_id, {"status": "failed"})
            await queue.mark_job_failed(job_id, result.get("error", "Unknown error"))
            
            print(f"[Worker] Edit failed: {result.get('error')}")
            
    except Exception as e:
        await db.update_clip(clip_id, {"status": "failed"})
        await queue.mark_job_failed(job_id, str(e))
        print(f"[Worker] Edit exception: {e}")

async def run_worker():
    """Main worker loop."""
    print("[Worker] Starting clip edit worker...")
    
    while True:
        try:
            # Poll for jobs
            job = await queue.dequeue("clip_edit")
            
            if job:
                await process_edit_job(job)
            else:
                # No jobs, sleep before polling again
                await asyncio.sleep(5)
                
        except KeyboardInterrupt:
            print("[Worker] Shutting down...")
            break
        except Exception as e:
            print(f"[Worker] Error in loop: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(run_worker())
