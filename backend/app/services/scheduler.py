import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from app.core.config import settings
from app.services.database import SupabaseService
from app.services.social_posting import SocialPostingService
from app.services.zernio_service import ZernioService
from app.services.queue import QueueService

from app.services.earnings_service import EarningsService, PLATFORM_RPMS

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
            pipeline = await self.db.get_pipeline(pipeline_id)
            if not pipeline:
                logger.warning(f"[Scheduler] Pipeline {pipeline_id} not found for clip {clip_id}")
                return
            
            target_platforms = pipeline.get("target_platforms", [])
            autonomy_mode = pipeline.get("autonomy_mode", "suggestOnly")
            
            if autonomy_mode == "suggestOnly":
                logger.info(f"[Scheduler] Clip {clip_id} is suggestOnly - not auto-posting")
                return
            
            if autonomy_mode == "approveEach":
                logger.info(f"[Scheduler] Clip {clip_id} needs manual approval")
                return
            
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
            
            all_success = all(r.get("success") for r in results)
            
            if all_success:
                await self.db.update_clip(clip_id, {
                    "status": "posted",
                    "posted_at": datetime.now(timezone.utc).isoformat(),
                    "post_results": results
                })
                logger.info(f"[Scheduler] Clip {clip_id} posted successfully")
            else:
                await self.db.update_clip(clip_id, {
                    "status": "ready_for_review",
                    "post_results": results,
                    "post_error": "Some platforms failed"
                })
                logger.warning(f"[Scheduler] Clip {clip_id} partial post failure")
            
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
    """Periodically sync metrics from social platforms via Zernio."""
    
    def __init__(self):
        self.db = SupabaseService()
        self.zernio = ZernioService()
        self.earnings = EarningsService()
    
    async def sync_all_metrics(self):
        """Sync metrics for all posted clips from the last 30 days."""
        try:
            from datetime import timedelta
            since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            
            # Get all posted clips from last 30 days
            clips = await self.db.list_clips(
                user_id=None,
                status="posted",
                limit=500
            )
            
            # Filter to recent clips
            recent_clips = [
                c for c in clips
                if c.get("posted_at") and c["posted_at"] >= since
            ]
            
            logger.info(f"[Metrics] Syncing {len(recent_clips)} clips since {since[:10]}")
            
            for clip in recent_clips:
                await self._sync_clip_metrics(clip)
                # Sync earnings after metrics update
                earnings_result = await self.earnings.sync_earnings_from_clip(clip["id"])
                if earnings_result.get("records_created"):
                    logger.info(f"[Earnings] Created {earnings_result['records_created']} earning records for clip {clip['id']}")
                
        except Exception as e:
            logger.error(f"[Metrics] Sync failed: {e}")
    
    async def _sync_clip_metrics(self, clip: Dict[str, Any]):
        """Sync metrics for a single clip from Zernio."""
        clip_id = clip["id"]
        user_id = clip.get("user_id")
        post_results = clip.get("post_results", [])
        
        if not post_results or not user_id:
            return
        
        try:
            # Get user's connected social accounts
            accounts = await self.db.list_social_accounts(user_id)
            account_map = {a.get("platform", "").lower(): a for a in accounts}
            
            total_views = 0
            total_likes = 0
            total_shares = 0
            total_comments = 0
            platform_metrics = {}
            
            for result in post_results:
                platform = result.get("platform", "").lower()
                post_id = result.get("post_id") or result.get("id")
                zernio_account_id = result.get("account_id")
                
                if not post_id:
                    continue
                
                # Find the Zernio account ID for this platform
                if not zernio_account_id:
                    account = account_map.get(platform)
                    if account:
                        zernio_account_id = account.get("account_id") or account.get("id")
                
                if not zernio_account_id:
                    logger.warning(f"[Metrics] No Zernio account for {platform}, clip {clip_id}")
                    continue
                
                try:
                    metrics_response = await self.zernio.get_metrics(
                        account_id=zernio_account_id,
                        post_ids=[post_id]
                    )
                    
                    metrics = metrics_response.get("metrics", [])
                    if metrics:
                        m = metrics[0]
                        views = m.get("views", 0)
                        likes = m.get("likes", 0)
                        shares = m.get("shares", 0) or m.get("retweets", 0) or m.get(" reposts", 0)
                        comments = m.get("comments", 0)
                        
                        total_views += views
                        total_likes += likes
                        total_shares += shares
                        total_comments += comments
                        
                        platform_metrics[platform] = {
                            "views": views,
                            "likes": likes,
                            "shares": shares,
                            "comments": comments,
                            "post_id": post_id
                        }
                        
                except Exception as e:
                    logger.warning(f"[Metrics] Failed to fetch metrics for {platform} post {post_id}: {e}")
            
            # Estimate watch time and retention from platform data
            estimated_watch_time = None
            estimated_retention = None
            if total_views > 0:
                # Estimate retention based on content type and platform
                base_retention = 0.45  # 45% baseline for short-form
                if any(p in platform_metrics for p in ["youtube"]):
                    base_retention = 0.62  # YouTube tends to have higher retention
                elif any(p in platform_metrics for p in ["tiktok"]):
                    base_retention = 0.38  # TikTok lower retention but higher volume
                
                # Adjust by engagement rate (likes per view)
                engagement_rate = total_likes / total_views if total_views > 0 else 0
                retention_adjustment = min(0.15, engagement_rate * 2)  # Up to +15% for high engagement
                estimated_retention = min(0.95, base_retention + retention_adjustment)
                
                # Estimate watch time from retention * average duration (assume 30s for short-form)
                avg_duration = clip.get("video_duration") or clip.get("duration") or 30
                estimated_watch_time = total_views * avg_duration * estimated_retention
            
            # Compute earnings from views
            total_earnings = 0
            for platform, m in platform_metrics.items():
                views = m.get("views", 0)
                rpm = PLATFORM_RPMS.get(platform, 0.5)
                total_earnings += (views / 1000) * rpm
            
            total_earnings_cents = int(total_earnings * 100)
            
            # Update clip with aggregated metrics
            await self.db.update_clip(clip_id, {
                "views": total_views,
                "likes": total_likes,
                "shares": total_shares,
                "comments": total_comments,
                "watch_time_seconds": estimated_watch_time,
                "retention_pct": estimated_retention,
                "earnings_cents": total_earnings_cents,
                "platform_metrics": platform_metrics,
                "metrics_synced_at": datetime.now(timezone.utc).isoformat()
            })
            
            # Update pipeline totals
            pipeline_id = clip.get("pipeline_id")
            if pipeline_id:
                pipeline = await self.db.get_pipeline(pipeline_id)
                if pipeline:
                    current_views = pipeline.get("total_views", 0)
                    current_likes = pipeline.get("total_likes", 0)
                    
                    await self.db.update_pipeline(pipeline_id, {
                        "total_views": current_views + total_views,
                        "total_likes": current_likes + total_likes
                    })
            
            logger.info(f"[Metrics] Synced clip {clip_id}: {total_views} views, {total_likes} likes")
            
        except Exception as e:
            logger.error(f"[Metrics] Failed to sync clip {clip_id}: {e}")

class ContentDiscoveryScheduler:
    """Periodically run ContentAgent discovery for all active pipelines."""
    
    def __init__(self):
        self.db = SupabaseService()
        self.queue = QueueService()
    
    async def run_discovery_cycle(self):
        """Run content discovery for all active pipelines."""
        try:
            # Get all active pipelines
            result = supabase.table("pipelines")\
                .select("id, user_id, autonomy_mode, target_platforms, last_discovery_run")\
                .eq("status", "active")\
                .execute()
            
            pipelines = result.data or []
            logger.info(f"[Discovery] Running discovery for {len(pipelines)} active pipelines")
            
            for pipeline in pipelines:
                pipeline_id = pipeline["id"]
                user_id = pipeline.get("user_id", "")
                autonomy = pipeline.get("autonomy_mode", "suggestOnly")
                
                # Check if discovery is due (every 4 hours for active pipelines)
                last_run = pipeline.get("last_discovery_run")
                if last_run:
                    try:
                        last_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                        hours_since = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
                        if hours_since < 4:
                            continue  # Not due yet
                    except:
                        pass
                
                # Queue discovery job
                job_id = f"discovery-{pipeline_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
                await self.queue.enqueue("content_discovery", {
                    "job_id": job_id,
                    "job_type": "content_discovery",
                    "pipeline_id": pipeline_id,
                    "user_id": user_id,
                    "autonomy_mode": autonomy,
                    "max_proposals": 5 if autonomy == "suggestOnly" else 10
                }, priority=5)
                
                # Update last discovery run
                supabase.table("pipelines")\
                    .update({"last_discovery_run": datetime.now(timezone.utc).isoformat()})\
                    .eq("id", pipeline_id)\
                    .execute()
                
                logger.info(f"[Discovery] Queued discovery for pipeline {pipeline_id}")
                
        except Exception as e:
            logger.error(f"[Discovery] Cycle failed: {e}")


class SourceHealthScheduler:
    """Periodically run source health checks."""
    
    def __init__(self):
        self.db = SupabaseService()
    
    async def run_health_cycle(self):
        """Run health checks on all sources."""
        try:
            from app.agents.source_agent import source_agent
            result = await source_agent.run_health_check_batch(auto_disable=True)
            
            if result.get("success"):
                logger.info(
                    f"[SourceHealth] Checked {result['total_sources']} sources: "
                    f"{result['healthy']} healthy, {result['degraded']} degraded, "
                    f"{result['failing']} failing, {result['stale']} stale, "
                    f"{result.get('auto_disabled', 0)} auto-disabled"
                )
            else:
                logger.warning(f"[SourceHealth] Failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"[SourceHealth] Cycle failed: {e}")


async def run_schedulers():
    """Run all schedulers in a background loop."""
    post_scheduler = PostScheduler()
    metrics_scheduler = MetricsSyncScheduler()
    discovery_scheduler = ContentDiscoveryScheduler()
    health_scheduler = SourceHealthScheduler()
    
    cycle_count = 0
    while True:
        try:
            cycle_count += 1
            
            # Run every minute
            await post_scheduler.run_scheduler_cycle()
            await metrics_scheduler.sync_all_metrics()
            
            # Run discovery every 15 minutes (cycle_count % 15)
            if cycle_count % 15 == 0:
                await discovery_scheduler.run_discovery_cycle()
            
            # Run source health check every 60 minutes (cycle_count % 60)
            if cycle_count % 60 == 0:
                await health_scheduler.run_health_cycle()
                cycle_count = 0  # Reset to avoid overflow
                
        except Exception as e:
            logger.error(f"[Scheduler loop] Error: {e}")
        
        await asyncio.sleep(60)  # 1 minute base interval


if __name__ == "__main__":
    asyncio.run(run_schedulers())
