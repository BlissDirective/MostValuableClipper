import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from app.core.config import settings
from app.services.database import SupabaseService
from app.services.social_posting import SocialPostingService
from app.services.queue import QueueService

logger = logging.getLogger(__name__)

class PostScheduler:
    """Schedule and execute automatic clip posting based on pipeline configuration."""
    
    def __init__(self):
        self.db = SupabaseService()
        self.posting_service = SocialPostingService()
        self.queue = QueueService()
    
    async def run_scheduler_cycle(self):
        """Check for clips that should be posted now."""
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        
        logger.info(f"[Scheduler] Checking for clips to post at {now_iso}")
        
        try:
            # Get approved clips with scheduled_post_time <= now
            clips = await self.db.get_clips_for_posting(
                status="approved",
                scheduled_before=now_iso
            )
            
            logger.info(f"[Scheduler] Found {len(clips)} clips ready to post")
            
            for clip in clips:
                await self._process_scheduled_clip(clip)
                
        except Exception as e:
            logger.error(f"[Scheduler] Cycle failed: {e}")
    
    async def _process_scheduled_clip(self, clip: Dict[str, Any]):
        """Process a single scheduled clip."""
        clip_id = clip["id"]
        pipeline_id = clip.get("pipeline_id")
        user_id = clip.get("user_id")
        
        logger.info(f"[Scheduler] Processing clip {clip_id}")
        
        try:
            # Get pipeline for posting config
            pipeline = await self.db.get_pipeline(pipeline_id)
            if not pipeline:
                logger.warning(f"[Scheduler] Pipeline {pipeline_id} not found for clip {clip_id}")
                return
            
            target_platforms = pipeline.get("target_platforms", [])
            autonomy_mode = pipeline.get("autonomy_mode", "suggestOnly")
            
            # Only post if autonomy allows
            if autonomy_mode == "suggestOnly":
                logger.info(f"[Scheduler] Clip {clip_id} is suggestOnly - not auto-posting")
                return
            
            # For approveEach, we'd need to check if explicitly approved
            # For now, only fullAuto posts automatically
            if autonomy_mode == "approveEach":
                logger.info(f"[Scheduler] Clip {clip_id} needs manual approval")
                return
            
            # Post to each target platform
            results = []
            for platform in target_platforms:
                result = await self.posting_service.post_clip(
                    clip_id=clip_id,
                    platform=platform,
                    video_url=clip.get("video_url", ""),
                    caption=clip.get("caption", ""),
                    hashtags=clip.get("hashtags", []),
                    title=clip.get("title", "")
                )
                results.append(result)
            
            # Check if all posts succeeded
            all_success = all(r.get("success") for r in results)
            
            if all_success:
                await self.db.update_clip(clip_id, {
                    "status": "posted",
                    "posted_at": datetime.now(timezone.utc).isoformat(),
                    "post_results": results
                })
                logger.info(f"[Scheduler] Clip {clip_id} posted successfully")
            else:
                # Some posts failed - mark for review
                await self.db.update_clip(clip_id, {
                    "status": "ready_for_review",
                    "post_results": results,
                    "post_error": "Some platforms failed"
                })
                logger.warning(f"[Scheduler] Clip {clip_id} partial post failure")
            
            # Update pipeline stats
            await self.db.update_pipeline(pipeline_id, {
                "total_clips_generated": pipeline.get("total_clips_generated", 0) + 1
            })
            
        except Exception as e:
            logger.error(f"[Scheduler] Failed to post clip {clip_id}: {e}")
            await self.db.update_clip(clip_id, {
                "status": "failed",
                "post_error": str(e)
            })
    
    async def schedule_clip(
        self,
        clip_id: str,
        pipeline_id: str,
        post_time: str
    ) -> Dict[str, Any]:
        """Manually schedule a clip for posting."""
        try:
            await self.db.update_clip(clip_id, {
                "status": "approved",
                "scheduled_post_time": post_time
            })
            
            logger.info(f"[Scheduler] Clip {clip_id} scheduled for {post_time}")
            
            return {
                "success": True,
                "clip_id": clip_id,
                "scheduled_time": post_time
            }
        except Exception as e:
            logger.error(f"[Scheduler] Failed to schedule clip {clip_id}: {e}")
            return {
                "success": False,
                "clip_id": clip_id,
                "error": str(e)
            }
    
    async def get_posting_schedule(self, pipeline_id: str) -> List[Dict[str, Any]]:
        """Get upcoming scheduled posts for a pipeline."""
        try:
            pipeline = await self.db.get_pipeline(pipeline_id)
            if not pipeline:
                return []
            
            post_schedule = pipeline.get("post_schedule", {})
            weekdays = post_schedule.get("weekdays", [1, 2, 3, 4, 5])
            times = post_schedule.get("times", ["09:00", "15:00", "19:00"])
            timezone_str = post_schedule.get("timezone", "UTC")
            
            # Get scheduled clips
            clips = await self.db.list_clips(
                user_id=pipeline.get("user_id"),
                status="approved"
            )
            
            upcoming = [
                {
                    "clip_id": c["id"],
                    "title": c.get("title", ""),
                    "scheduled_time": c.get("scheduled_post_time"),
                    "platforms": pipeline.get("target_platforms", [])
                }
                for c in clips
                if c.get("scheduled_post_time")
            ]
            
            return upcoming
            
        except Exception as e:
            logger.error(f"[Scheduler] Failed to get schedule: {e}")
            return []

class MetricsSyncScheduler:
    """Periodically sync metrics from social platforms."""
    
    def __init__(self):
        self.db = SupabaseService()
        self.posting_service = SocialPostingService()
    
    async def sync_all_metrics(self):
        """Sync metrics for all posted clips."""
        try:
            # Get all posted clips
            clips = await self.db.list_clips(
                user_id=None,  # All users
                status="posted",
                limit=100
            )
            
            logger.info(f"[Metrics] Syncing {len(clips)} clips")
            
            for clip in clips:
                await self._sync_clip_metrics(clip)
                
        except Exception as e:
            logger.error(f"[Metrics] Sync failed: {e}")
    
    async def _sync_clip_metrics(self, clip: Dict[str, Any]):
        """Sync metrics for a single clip."""
        clip_id = clip["id"]
        post_results = clip.get("post_results", [])
        
        total_views = 0
        total_likes = 0
        
        for result in post_results:
            platform = result.get("platform")
            # Platform metrics sync requires OAuth tokens (stored in social_accounts table)
            # This will be implemented when platform OAuth flows are complete
            pass
        
        # Update clip with new metrics
        await self.db.update_clip(clip_id, {
            "views": total_views,
            "likes": total_likes
        })
        
        # Update pipeline totals
        pipeline_id = clip.get("pipeline_id")
        if pipeline_id:
            pipeline = await self.db.get_pipeline(pipeline_id)
            if pipeline:
                await self.db.update_pipeline(pipeline_id, {
                    "total_views": pipeline.get("total_views", 0) + total_views
                })
