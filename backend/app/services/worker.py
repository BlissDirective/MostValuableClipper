import asyncio
import json
import os
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.services.queue import QueueService, CacheService
from app.services.ffmpeg_service import FFmpegEditService
from app.services.remix_service import RemixService
from app.services.thumbnail_service import ThumbnailService
from app.services.zernio_service import ZernioService
from app.services.database import SupabaseService
from app.core.config import settings

class VideoProcessingWorker:
    """Background worker that consumes the Redis queue and processes video jobs.

    Listens on multiple queues:
    - video_processing: Edit, remix, thumbnail, post, segment analyze, transcribe jobs
    - swarm_batch: Batch swarm execution jobs

    Circuit-breaker (H-05): after CIRCUIT_OPEN_THRESHOLD consecutive cycle-level
    exceptions the worker pauses for CIRCUIT_COOLDOWN seconds before retrying.
    This prevents a broken dependency (e.g. Redis unreachable) from spin-looping
    and flooding logs.
    """

    QUEUES = ["video_processing", "swarm_batch"]

    # Circuit-breaker thresholds
    CIRCUIT_OPEN_THRESHOLD = 5   # consecutive failures before opening
    CIRCUIT_COOLDOWN = 60        # seconds to stay open before half-open retry

    def __init__(self):
        self.queue = QueueService()
        self.cache = CacheService()
        self.ffmpeg = FFmpegEditService()
        self.remix = RemixService()
        self.thumbnail = ThumbnailService()
        self.zernio = ZernioService()
        self.db = SupabaseService()
        self.running = False
        self.current_job: Optional[str] = None
        # Circuit-breaker state
        self._consecutive_failures: int = 0
        self._circuit_open: bool = False
        self._circuit_reopen_at: float = 0.0
    
    async def process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single job based on its type."""
        job_type = job.get("job_type")
        job_id = job.get("job_id", "unknown")
        
        print(f"[{datetime.now().isoformat()}] Processing job {job_id} ({job_type})")
        
        try:
            if job_type == "edit_clip":
                return await self._process_edit(job)
            elif job_type == "remix_clip":
                return await self._process_remix(job)
            elif job_type == "generate_thumbnail":
                return await self._process_thumbnail(job)
            elif job_type == "post_clip":
                return await self._process_post(job)
            elif job_type == "segment_analyze":
                return await self._process_segment_analyze(job)
            elif job_type == "transcribe":
                return await self._process_transcribe(job)
            elif job_type == "batch_swarm":
                return await self._process_batch_swarm(job)
            elif job_type == "content_discovery":
                return await self._process_content_discovery(job)
            else:
                return {"success": False, "error": f"Unknown job type: {job_type}"}
                
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Job {job_id} failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _process_edit(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process an edit clip job."""
        clip_id = job["clip_id"]
        source_url = job["source_url"]
        recipe = job["recipe"]
        
        valid, error = self.ffmpeg.validate_recipe(recipe)
        if not valid:
            return {"success": False, "error": error}
        
        result = await self.ffmpeg.edit_clip(clip_id, source_url, recipe)
        
        if result["success"]:
            await self.db.update_clip(clip_id, {
                "video_url": result["video_url"],
                "duration_seconds": result["duration"],
                "status": "ready_for_review",
                "updated_at": "now()"
            })
            await self.cache.set(f"clip:{clip_id}:edit", result, ttl_seconds=3600)
        
        return result
    
    async def _process_remix(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a remix clip job."""
        clip_id = job["clip_id"]
        source_url = job["source_url"]
        params = job.get("params", {})
        
        result = await self.remix.generate_remix(
            clip_id=clip_id,
            source_url=source_url,
            num_variants=params.get("num_variants", 3),
            target_duration=params.get("target_duration", 20),
            include_music=params.get("include_music", True),
            include_captions=params.get("include_captions", True),
            output_format=params.get("output_format", "9:16")
        )
        
        if result.get("success"):
            for variant in result.get("variants", []):
                await self.db.create_clip({
                    "parent_id": clip_id,
                    "title": variant.get("title", "Remix"),
                    "video_url": variant["video_url"],
                    "caption": variant.get("caption", ""),
                    "status": "ready_for_review",
                    "created_at": "now()"
                })
        
        return result
    
    async def _process_thumbnail(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a thumbnail generation job."""
        clip_id = job["clip_id"]
        source_url = job["source_url"]
        
        result = await self.thumbnail.generate_thumbnail(
            clip_id=clip_id,
            video_url=source_url,
            strategy="best_frame"
        )
        
        if result.get("success"):
            await self.db.update_clip(clip_id, {
                "thumbnail_url": result["thumbnail_url"],
                "updated_at": "now()"
            })
        
        return result
    
    async def _process_post(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a social media post job."""
        clip_id = job["clip_id"]
        video_url = job["video_url"]
        caption = job.get("caption", "")
        platforms = job.get("platforms", [])
        account_ids = job.get("account_ids")
        schedule_time = job.get("schedule_time")
        
        zernio_platforms = [self.zernio.map_platform_to_zernio(p) for p in platforms]
        
        result = await self.zernio.post_clip(
            video_url=video_url,
            caption=caption,
            platforms=zernio_platforms,
            account_ids=account_ids,
            schedule_time=schedule_time
        )
        
        if result.get("success"):
            await self.db.update_clip(clip_id, {
                "status": "posted",
                "posted_at": "now()",
                "post_ids": result.get("post_ids", []),
                "updated_at": "now()"
            })
        
        return result
    
    async def _process_segment_analyze(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a segment analysis job."""
        clip_id = job["clip_id"]
        source_url = job["source_url"]
        
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix=f"segment_{clip_id}_")
        
        try:
            source_path = await self.ffmpeg.download_source(source_url, temp_dir)
            info = self.ffmpeg._get_video_info(source_path)
            
            duration = info["duration"]
            segments = []
            
            if duration > 60:
                num_segments = max(3, int(duration / 20))
                segment_duration = duration / num_segments
                for i in range(num_segments):
                    start = i * segment_duration
                    end = min((i + 1) * segment_duration, duration)
                    segments.append({
                        "start": start,
                        "end": end,
                        "label": f"Segment {i+1}"
                    })
            else:
                segments.append({
                    "start": 0,
                    "end": duration,
                    "label": "Full clip"
                })
            
            result = {
                "success": True,
                "segments": segments,
                "duration": duration,
                "resolution": f"{info['width']}x{info['height']}"
            }
            
            await self.db.update_clip(clip_id, {
                "metadata": {"segments": segments, "video_info": info},
                "updated_at": "now()"
            })
            
            return result
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def _process_transcribe(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a transcription job."""
        clip_id = job["clip_id"]
        source_url = job["source_url"]
        
        try:
            from app.services.transcription import TranscriptionService
            transcriber = TranscriptionService()
            result = await transcriber.transcribe(source_url)
            
            if result.get("success"):
                await self.db.update_clip(clip_id, {
                    "caption": result.get("text", ""),
                    "transcript": result.get("segments", []),
                    "updated_at": "now()"
                })
            
            return result
        except Exception as e:
            return {"success": False, "error": f"Transcription failed: {str(e)}"}
    
    async def _process_batch_swarm(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a batch swarm job by delegating to the swarm batch service."""
        batch_id = job.get("batch_id")
        
        try:
            from app.services.swarm_batch_service import SwarmBatchService
            from app.services.swarm_orchestrator import swarm_orchestrator
            
            service = SwarmBatchService(swarm_orchestrator)
            result = await service.process_batch_job(batch_id)
            
            return result or {"success": True, "batch_id": batch_id}
        except Exception as e:
            return {"success": False, "error": f"Batch processing failed: {str(e)}"}
    
    async def _process_content_discovery(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a content discovery job."""
        pipeline_id = job.get("pipeline_id")
        user_id = job.get("user_id")
        max_proposals = job.get("max_proposals", 5)
        
        try:
            from app.agents.content_agent import content_agent
            result = await content_agent.run_content_discovery(
                pipeline_id=pipeline_id,
                user_id=user_id,
                max_proposals=max_proposals
            )
            return result
        except Exception as e:
            return {"success": False, "error": f"Content discovery failed: {str(e)}"}
    
    async def run_single_cycle(self) -> bool:
        """Run a single poll-process cycle across all queues."""
        for queue_name in self.QUEUES:
            # Try priority queue first
            job = await self.queue.dequeue_with_priority(queue_name)
            
            if not job:
                # Fallback to regular queue
                job = await self.queue.dequeue(queue_name)
            
            if job:
                job_id = job.get("job_id", "unknown")
                self.current_job = job_id
                
                try:
                    result = await self.process_job(job)
                    
                    if result.get("success"):
                        await self.queue.mark_job_complete(job_id, result)
                    else:
                        await self.queue.mark_job_failed(job_id, result.get("error", "Unknown error"))
                        
                except Exception as e:
                    await self.queue.mark_job_failed(job_id, str(e))
                finally:
                    self.current_job = None
                
                return True
        
        return False
    
    async def run(self, poll_interval: float = 2.0):
        """Main worker loop with circuit-breaker protection (H-05)."""
        self.running = True
        print(f"[{datetime.now().isoformat()}] Worker started. Listening on queues: {', '.join(self.QUEUES)}")

        while self.running:
            # Circuit-breaker: check if open
            if self._circuit_open:
                now = asyncio.get_event_loop().time()
                if now < self._circuit_reopen_at:
                    await asyncio.sleep(poll_interval)
                    continue
                # Half-open: allow one attempt
                print(f"[{datetime.now().isoformat()}] Circuit half-open — attempting recovery")
                self._circuit_open = False

            try:
                processed = await self.run_single_cycle()
                # Success: reset failure counter
                if self._consecutive_failures > 0:
                    print(f"[{datetime.now().isoformat()}] Circuit closed after recovery")
                self._consecutive_failures = 0

                if not processed:
                    await asyncio.sleep(poll_interval)

            except Exception as e:
                self._consecutive_failures += 1
                print(
                    f"[{datetime.now().isoformat()}] Worker cycle error "
                    f"(failure {self._consecutive_failures}/{self.CIRCUIT_OPEN_THRESHOLD}): {e}"
                )
                if self._consecutive_failures >= self.CIRCUIT_OPEN_THRESHOLD:
                    self._circuit_open = True
                    self._circuit_reopen_at = asyncio.get_event_loop().time() + self.CIRCUIT_COOLDOWN
                    print(
                        f"[{datetime.now().isoformat()}] Circuit OPEN — "
                        f"pausing {self.CIRCUIT_COOLDOWN}s after {self._consecutive_failures} failures"
                    )
                await asyncio.sleep(poll_interval)

        print(f"[{datetime.now().isoformat()}] Worker stopped.")
    
    def stop(self):
        """Signal the worker to stop."""
        self.running = False
        print(f"[{datetime.now().isoformat()}] Stop signal received.")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        total_queue_length = 0
        for queue_name in self.QUEUES:
            total_queue_length += await self.queue.get_queue_length(queue_name)
        
        return {
            "running": self.running,
            "current_job": self.current_job,
            "queue_length": total_queue_length,
            "worker_id": os.getpid(),
            "circuit_breaker": {
                "open": self._circuit_open,
                "consecutive_failures": self._consecutive_failures,
            },
        }


def run_worker():
    """Run the worker as a standalone process."""
    worker = VideoProcessingWorker()
    
    def handle_signal(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        worker.stop()
    
    import signal
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        worker.stop()
        print("Worker stopped by user.")


if __name__ == "__main__":
    run_worker()
