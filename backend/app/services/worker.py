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

    # Phase 2: "clip_generation" is the queue the API writes to on clip create —
    # previously unlistened, so queued clips never processed. Now consumed here.
    QUEUES = ["clip_generation", "video_processing", "swarm_batch"]

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
            # Phase 2: clip_generation jobs (from the clips API) carry no job_type;
            # route them through the full ingest pipeline.
            if job_type in ("ingest_source", "ingest") or (job_type is None and job.get("clip_id")):
                return await self._process_ingest(job)
            elif job_type == "edit_clip":
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
    
    async def _process_ingest(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2 end-to-end ingest for a user's OWN uploaded source video.

        upload → download → extract audio → transcribe → pick interesting
        segments → render each as a standalone clip → upload → create clip
        records (status ready_for_review). No auto-posting; user reviews/exports.
        """
        import tempfile, shutil, os
        clip_id = job.get("clip_id")
        user_id = job.get("user_id")
        if not clip_id:
            return {"success": False, "error": "ingest job missing clip_id"}

        parent = await self.db.get_clip(clip_id)
        if not parent:
            return {"success": False, "error": "source clip not found"}

        # Resolve the uploaded source URL (clip record, else its source row).
        source_url = parent.get("video_url") or parent.get("source_url")
        if not source_url and job.get("source_id"):
            try:
                src = await self.db.get_source(job["source_id"])
                source_url = (src or {}).get("url") or (src or {}).get("video_url")
            except Exception:
                source_url = None
        if not source_url:
            await self.db.update_clip(clip_id, {"status": "failed", "updated_at": "now()"})
            return {"success": False, "error": "no source video to ingest"}

        await self.db.update_clip(clip_id, {"status": "processing", "updated_at": "now()"})

        temp_dir = tempfile.mkdtemp(prefix=f"ingest_{clip_id}_")
        try:
            # 1. Download source once.
            source_path = await self.ffmpeg.download_source(source_url, temp_dir)

            # 2. Extract audio + 3. transcribe.
            audio_path = os.path.join(temp_dir, "audio.wav")
            ok, info = self.ffmpeg.extract_audio(source_path, audio_path)
            from app.services.transcription import TranscriptionService
            transcriber = TranscriptionService()
            transcription = await transcriber.transcribe(audio_path) if ok else {"segments": [], "duration": 0}

            # 4. Pick interesting segments (falls back to whole-video if none).
            video_info = self.ffmpeg._get_video_info(source_path)
            total_duration = transcription.get("duration") or video_info.get("duration") or 0
            segments = transcriber.find_interesting_segments(
                transcription, min_duration=15, max_duration=90, num_clips=8
            )
            if not segments and total_duration:
                segments = [{"start": 0, "end": min(total_duration, 60), "text": transcription.get("text", "")}]

            # 5-6. Render + upload + create a clip record per segment.
            created = []
            for i, seg in enumerate(segments):
                start, end = float(seg.get("start", 0)), float(seg.get("end", 0))
                if end <= start:
                    continue
                out_path = os.path.join(temp_dir, f"clip_{i}.mp4")
                ok, rendered = self.ffmpeg.render_segment(source_path, start, end, out_path)
                if not ok:
                    continue
                variant_id = f"{clip_id}_seg{i}"
                video_url = await self.ffmpeg.upload_result(rendered, variant_id)
                rec = await self.db.create_clip({
                    "user_id": user_id,
                    "parent_clip_id": clip_id,
                    "pipeline_id": parent.get("pipeline_id"),
                    "source_id": parent.get("source_id"),
                    "title": f"Clip {i+1}: {parent.get('title', 'Untitled')}",
                    "caption": (seg.get("text") or "").strip()[:300],
                    "status": "ready_for_review",
                    "video_url": video_url,
                    "duration_seconds": round(end - start, 2),
                    "metadata": {
                        "segment": {"start": start, "end": end},
                        "transcript_text": (seg.get("text") or "").strip(),
                        "ingest_score": seg.get("score"),
                    },
                    "created_at": "now()",
                    "updated_at": "now()",
                })
                created.append(rec.get("id") if isinstance(rec, dict) else None)

            # 7. Mark the source done. Transcription cost ≈ $0.006/min (Whisper).
            cost_usd = round((total_duration / 60.0) * 0.006, 6) if total_duration else 0.0
            await self.db.update_clip(clip_id, {
                "status": "processed" if created else "failed",
                "metadata": {
                    "transcript_text": transcription.get("text", ""),
                    "child_clip_ids": created,
                    "ingest_cost_usd": cost_usd,
                },
                "updated_at": "now()",
            })
            return {
                "success": bool(created),
                "clip_id": clip_id,
                "clips_created": len(created),
                "child_clip_ids": created,
                "cost_usd": cost_usd,
            }
        except Exception as e:
            await self.db.update_clip(clip_id, {"status": "failed", "updated_at": "now()"})
            return {"success": False, "error": f"Ingest failed: {str(e)}"}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

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
        """Process a transcription job.

        Fix (Phase 2): TranscriptionService.transcribe expects a local AUDIO file,
        not a video URL. Download the source, extract audio, then transcribe. The
        Whisper response has no "success" key, so derive it from the result.
        """
        import tempfile, shutil, os
        clip_id = job["clip_id"]
        source_url = job["source_url"]

        temp_dir = tempfile.mkdtemp(prefix=f"transcribe_{clip_id}_")
        try:
            from app.services.transcription import TranscriptionService
            transcriber = TranscriptionService()

            source_path = await self.ffmpeg.download_source(source_url, temp_dir)
            audio_path = os.path.join(temp_dir, "audio.wav")
            ok, info = self.ffmpeg.extract_audio(source_path, audio_path)
            if not ok:
                return {"success": False, "error": f"Audio extraction failed: {info}"}

            result = await transcriber.transcribe(audio_path)
            text = result.get("text", "")

            await self.db.update_clip(clip_id, {
                "caption": text,
                "transcript": result.get("segments", []),
                "updated_at": "now()",
            })
            return {"success": bool(text or result.get("segments")), **result}
        except Exception as e:
            return {"success": False, "error": f"Transcription failed: {str(e)}"}
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
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
