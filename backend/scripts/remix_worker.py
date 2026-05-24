#!/usr/bin/env python3
"""
Clip Remix Worker

Processes clip_remix queue jobs using AI-powered scene detection,
hook optimization, and FFmpeg rendering.

Run: python scripts/remix_worker.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.queue import QueueService
from app.services.remix_service import remix_service
from app.services.database import SupabaseService
from app.core.config import settings

queue = QueueService()
db = SupabaseService()

async def process_remix_job(job_data: dict):
    """Process a single clip remix job."""
    job_id = job_data.get("job_id", "unknown")
    clip_id = job_data.get("clip_id")
    user_id = job_data.get("user_id")
    num_variants = job_data.get("num_variants", 3)
    target_duration = job_data.get("target_duration", 20)
    preferred_hook = job_data.get("preferred_hook_archetype")
    
    print(f"[Remix Worker] Processing remix job {job_id} for clip {clip_id}")
    
    try:
        # Update status to processing
        await db.update_clip(clip_id, {"remix_status": "processing"})
        await queue.mark_job_complete(job_id, {"status": "processing"})
        
        # Run AI remix
        result = await remix_service.create_remix(
            clip_id=clip_id,
            user_id=user_id,
            num_variants=num_variants,
            target_duration=(target_duration * 0.75, target_duration)
        )
        
        if result.get("success"):
            await db.update_clip(clip_id, {
                "remix_status": "completed",
                "remix_variants": result.get("variants", [])
            })
            
            await queue.mark_job_complete(job_id, {
                "status": "completed",
                "variants": result.get("variants", []),
                "total_variants": result.get("total_variants", 0)
            })
            
            print(f"[Remix Worker] Completed {result.get('total_variants', 0)} variants")
        else:
            await db.update_clip(clip_id, {"remix_status": "failed"})
            await queue.mark_job_failed(job_id, result.get("error", "Unknown error"))
            print(f"[Remix Worker] Failed: {result.get('error')}")
            
    except Exception as e:
        await db.update_clip(clip_id, {"remix_status": "failed"})
        await queue.mark_job_failed(job_id, str(e))
        print(f"[Remix Worker] Exception: {e}")

async def run_worker():
    """Main worker loop."""
    print("[Remix Worker] Starting clip remix worker...")
    
    while True:
        try:
            job = await queue.dequeue("clip_remix")
            
            if job:
                await process_remix_job(job)
            else:
                await asyncio.sleep(5)
                
        except KeyboardInterrupt:
            print("[Remix Worker] Shutting down...")
            break
        except Exception as e:
            print(f"[Remix Worker] Error in loop: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(run_worker())
