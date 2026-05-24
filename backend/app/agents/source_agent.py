"""SourceAgent — manages content source catalog, health checking,
freshness tracking, and failure handling.

Responsibilities:
  1. Source CRUD — Add, update, remove pipeline sources
  2. Health Checking — Validate source URLs, check availability
  3. Freshness Scoring — Track how fresh/stale each source is
  4. Failure Handling — Track consecutive failures, auto-disable broken sources
  5. Discovery — Find new relevant sources based on pipeline topic/niche
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict

from app.services.database import SupabaseService, supabase
from app.services.video_download import VideoDownloadService

logger = logging.getLogger(__name__)


@dataclass
class SourceHealth:
    """Health assessment for a single source."""
    source_id: str
    status: str  # healthy, degraded, failing, disabled
    last_scanned_at: Optional[str]
    consecutive_failures: int
    last_error: Optional[str]
    avg_items_per_scan: float
    freshness_score: float  # 0.0-1.0 (1.0 = very fresh)
    response_time_ms: int
    recommended_action: str  # none, retry, investigate, disable


class SourceAgent:
    """Manages content source lifecycle and health."""
    
    # Failure thresholds
    FAILURE_THRESHOLD_DISABLE = 5   # Auto-disable after 5 consecutive failures
    FAILURE_THRESHOLD_ALERT = 3     # Alert after 3 consecutive failures
    
    # Freshness thresholds
    FRESHNESS_STALE_HOURS = 48     # Consider stale after 48h
    FRESHNESS_WARNING_HOURS = 24  # Warning after 24h
    
    def __init__(self):
        self.db = SupabaseService()
        self.downloader = VideoDownloadService()
    
    # ═══════════════════════════════════════════════════════════
    #  1. SOURCE CRUD
    # ═══════════════════════════════════════════════════════════
    
    async def create_source(
        self,
        user_id: str,
        pipeline_id: str,
        source_type: str,
        url: str,
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new source after validation."""
        
        # Validate URL format and reachability
        valid, error = await self._validate_source_url(source_type, url)
        if not valid:
            return {"success": False, "error": error}
        
        # Auto-generate name if not provided
        if not name:
            name = self._auto_name_from_url(url, source_type)
        
        source_data = {
            "user_id": user_id,
            "pipeline_id": pipeline_id,
            "type": source_type,
            "url": url,
            "name": name,
            "config": config or {},
            "status": "active",
            "consecutive_failures": 0,
            "total_items_found": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            result = supabase.table("sources").insert(source_data).execute()
            if result.data and len(result.data) > 0:
                created = result.data[0]
                logger.info(f"[SourceAgent] Created source {created['id']} for pipeline {pipeline_id}")
                return {"success": True, "source": created}
            else:
                return {"success": False, "error": "Failed to create source"}
        except Exception as e:
            logger.error(f"[SourceAgent] Failed to create source: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_source(
        self,
        source_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update source configuration."""
        try:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            result = supabase.table("sources")\
                .update(updates)\
                .eq("id", source_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return {"success": True, "source": result.data[0]}
            return {"success": False, "error": "Source not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def delete_source(self, source_id: str) -> Dict[str, Any]:
        """Remove a source and all its references."""
        try:
            # First check if source has pending clips
            pending_result = supabase.table("clips")\
                .select("id")\
                .eq("source_id", source_id)\
                .in_("status", ["pending", "processing", "pending_review"])\
                .execute()
            
            pending_count = len(pending_result.data or [])
            
            # Soft delete: mark as inactive
            result = supabase.table("sources")\
                .update({
                    "status": "deleted",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })\
                .eq("id", source_id)\
                .execute()
            
            if result.data:
                return {
                    "success": True,
                    "message": f"Source marked as deleted. {pending_count} pending clips affected."
                }
            return {"success": False, "error": "Source not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def list_pipeline_sources(self, pipeline_id: str) -> List[Dict[str, Any]]:
        """List all sources for a pipeline with health metadata."""
        try:
            result = supabase.table("sources")\
                .select("*")\
                .eq("pipeline_id", pipeline_id)\
                .neq("status", "deleted")\
                .execute()
            
            sources = result.data or []
            
            # Enrich with health info
            enriched = []
            for source in sources:
                health = await self.check_source_health(source)
                source["health"] = asdict(health)
                enriched.append(source)
            
            return enriched
        except Exception as e:
            logger.error(f"[SourceAgent] Failed to list sources: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════
    #  2. HEALTH CHECKING
    # ═══════════════════════════════════════════════════════════
    
    async def check_source_health(self, source: Dict[str, Any]) -> SourceHealth:
        """Check health of a single source."""
        source_id = source.get("id", "")
        url = source.get("url", "")
        source_type = source.get("type", "")
        failures = source.get("consecutive_failures", 0)
        last_scanned = source.get("last_scanned_at")
        total_items = source.get("total_items_found", 0)
        scan_count = source.get("scan_count", 1)  # Avoid div by zero
        
        start_time = time.time()
        
        # Test URL reachability
        reachable, error = await self._validate_source_url(source_type, url)
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Calculate freshness score
        freshness = self._calculate_freshness(last_scanned)
        
        # Calculate average items per scan
        avg_items = total_items / max(1, scan_count)
        
        # Determine status and recommended action
        if not reachable:
            if failures >= self.FAILURE_THRESHOLD_DISABLE:
                status = "disabled"
                action = "disable"
            elif failures >= self.FAILURE_THRESHOLD_ALERT:
                status = "failing"
                action = "investigate"
            else:
                status = "degraded"
                action = "retry"
        elif failures > 0:
            status = "degraded"
            action = "monitor"
        elif freshness < 0.3:
            status = "stale"
            action = "investigate"
        else:
            status = "healthy"
            action = "none"
        
        return SourceHealth(
            source_id=source_id,
            status=status,
            last_scanned_at=last_scanned,
            consecutive_failures=failures,
            last_error=error if not reachable else None,
            avg_items_per_scan=round(avg_items, 1),
            freshness_score=round(freshness, 2),
            response_time_ms=response_time_ms,
            recommended_action=action
        )
    
    async def run_health_check_batch(
        self,
        pipeline_id: Optional[str] = None,
        auto_disable: bool = True
    ) -> Dict[str, Any]:
        """Run health checks on all sources, optionally auto-disable failing ones."""
        
        try:
            query = supabase.table("sources").select("*").neq("status", "deleted")
            if pipeline_id:
                query = query.eq("pipeline_id", pipeline_id)
            
            result = query.execute()
            sources = result.data or []
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        health_results = []
        disabled_count = 0
        
        for source in sources:
            health = await self.check_source_health(source)
            health_results.append(asdict(health))
            
            # Auto-disable if recommended
            if auto_disable and health.recommended_action == "disable":
                await self.update_source(source["id"], {
                    "status": "disabled",
                    "disabled_at": datetime.now(timezone.utc).isoformat(),
                    "disable_reason": f"Auto-disabled after {health.consecutive_failures} failures"
                })
                disabled_count += 1
            
            # Update source with latest health info
            await self.update_source(source["id"], {
                "last_health_check": datetime.now(timezone.utc).isoformat(),
                "health_status": health.status
            })
        
        # Summary
        healthy = sum(1 for h in health_results if h["status"] == "healthy")
        degraded = sum(1 for h in health_results if h["status"] == "degraded")
        failing = sum(1 for h in health_results if h["status"] in ["failing", "disabled"])
        stale = sum(1 for h in health_results if h["status"] == "stale")
        
        return {
            "success": True,
            "total_sources": len(sources),
            "healthy": healthy,
            "degraded": degraded,
            "failing": failing,
            "stale": stale,
            "auto_disabled": disabled_count,
            "details": health_results
        }
    
    # ═══════════════════════════════════════════════════════════
    #  3. FRESHNESS SCORING
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_freshness(self, last_scanned_at: Optional[str]) -> float:
        """Calculate freshness score (0.0-1.0) based on last scan time."""
        if not last_scanned_at:
            return 0.0  # Never scanned = completely stale
        
        try:
            last_scan = datetime.fromisoformat(last_scanned_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            hours_since_scan = (now - last_scan).total_seconds() / 3600
        except:
            return 0.5
        
        if hours_since_scan <= self.FRESHNESS_WARNING_HOURS:
            return 1.0  # Very fresh
        elif hours_since_scan <= self.FRESHNESS_STALE_HOURS:
            # Linear decay from 1.0 to 0.3
            decay = (hours_since_scan - self.FRESHNESS_WARNING_HOURS) / \
                    (self.FRESHNESS_STALE_HOURS - self.FRESHNESS_WARNING_HOURS)
            return max(0.3, 1.0 - (decay * 0.7))
        else:
            # Beyond stale threshold, decay to 0
            extra_hours = hours_since_scan - self.FRESHNESS_STALE_HOURS
            return max(0.0, 0.3 - (extra_hours * 0.01))  # 0.01 per hour decay
    
    # ═══════════════════════════════════════════════════════════
    #  4. VALIDATION
    # ═══════════════════════════════════════════════════════════
    
    async def _validate_source_url(self, source_type: str, url: str) -> Tuple[bool, Optional[str]]:
        """Validate that a source URL is reachable and valid."""
        if not url or not url.startswith(("http://", "https://")):
            return False, "URL must start with http:// or https://"
        
        try:
            if source_type in ["youtube", "url"]:
                # Test with yt-dlp extract_info (lightweight)
                info = await self.downloader.extract_info(url, extract_flat=True)
                if info:
                    return True, None
                else:
                    return False, "Could not extract video info from URL"
                    
            elif source_type == "rss":
                import feedparser
                feed = feedparser.parse(url)
                if feed.get("entries"):
                    return True, None
                elif feed.get("bozo"):
                    return False, f"RSS parse error: {feed.get('bozo_exception', 'Unknown')}"
                else:
                    return False, "No entries found in RSS feed"
                    
            elif source_type == "upload":
                # Upload sources don't have URLs to validate
                return True, None
            else:
                return False, f"Unknown source type: {source_type}"
                
        except Exception as e:
            return False, f"Validation error: {str(e)[:200]}"
    
    def _auto_name_from_url(self, url: str, source_type: str) -> str:
        """Generate a display name from URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        if source_type == "youtube":
            # Extract channel name from URL or use domain
            path = parsed.path.strip("/")
            if path.startswith("@"):
                return f"YouTube: {path[1:]}"
            elif "/channel/" in path or "/c/" in path:
                parts = path.split("/")
                return f"YouTube: {parts[-1]}"
            else:
                return f"YouTube Source"
        elif source_type == "rss":
            return f"RSS: {parsed.netloc}"
        else:
            return f"{source_type.capitalize()}: {parsed.netloc}"
    
    # ═══════════════════════════════════════════════════════════
    #  5. SOURCE DISCOVERY (find new sources)
    # ═══════════════════════════════════════════════════════════
    
    async def discover_sources(
        self,
        topic: str,
        platform: str = "youtube",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Discover new sources for a given topic/niche.
        
        Uses search to find popular channels/feeds related to the topic.
        """
        discovered = []
        
        try:
            if platform == "youtube":
                # Use yt-dlp search to find top channels for topic
                search_query = f"ytsearch{max_results}:{topic} channel"
                search_result = await self.downloader.extract_info(search_query, extract_flat=True)
                
                if search_result and search_result.get("entries"):
                    for entry in search_result["entries"][:max_results]:
                        channel_url = entry.get("channel_url") or \
                                      f"https://youtube.com/channel/{entry.get('channel_id', '')}"
                        
                        discovered.append({
                            "platform": "youtube",
                            "url": channel_url,
                            "name": entry.get("channel", topic),
                            "type": "youtube",
                            "estimated_subscribers": entry.get("channel_follower_count", 0),
                            "sample_video_count": entry.get("playlist_count", 0),
                            "relevance_score": 0.8,  # From search ranking
                        })
            
            elif platform == "rss":
                # Use a curated list of popular RSS feeds by topic
                # (In production, this would query a feed directory API)
                topic_feeds = self._get_topic_rss_feeds(topic)
                discovered.extend(topic_feeds[:max_results])
            
        except Exception as e:
            logger.error(f"[SourceAgent] Discovery failed for topic '{topic}': {e}")
        
        return discovered
    
    def _get_topic_rss_feeds(self, topic: str) -> List[Dict[str, Any]]:
        """Get known RSS feeds for common topics. (Stub for production RSS directory.)"""
        # Production would integrate with feedly, rsslookup, etc.
        known_feeds = {
            "tech": [
                {"url": "https://techcrunch.com/feed/", "name": "TechCrunch", "relevance_score": 0.95},
                {"url": "https://www.theverge.com/rss/index.xml", "name": "The Verge", "relevance_score": 0.9},
            ],
            "business": [
                {"url": "https://feeds.bbci.co.uk/news/business/rss.xml", "name": "BBC Business", "relevance_score": 0.9},
            ],
            "entertainment": [
                {"url": "https://variety.com/feed/", "name": "Variety", "relevance_score": 0.85},
            ],
        }
        
        feeds = known_feeds.get(topic.lower(), [])
        for feed in feeds:
            feed["platform"] = "rss"
            feed["type"] = "rss"
        
        return feeds
    
    # ═══════════════════════════════════════════════════════════
    #  6. BULK OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    async def refresh_all_pipeline_sources(self, pipeline_id: str) -> Dict[str, Any]:
        """Force-refresh all sources in a pipeline."""
        sources = await self.list_pipeline_sources(pipeline_id)
        
        refreshed = 0
        failed = 0
        
        for source in sources:
            try:
                # Reset failure count for retry
                if source.get("status") == "disabled":
                    await self.update_source(source["id"], {
                        "status": "active",
                        "consecutive_failures": 0,
                        "disabled_at": None,
                        "disable_reason": None
                    })
                
                # Trigger a health check
                health = await self.check_source_health(source)
                refreshed += 1
                
            except Exception as e:
                logger.error(f"[SourceAgent] Refresh failed for {source.get('id')}: {e}")
                failed += 1
        
        return {
            "success": True,
            "pipeline_id": pipeline_id,
            "sources_refreshed": refreshed,
            "sources_failed": failed,
            "total_sources": len(sources)
        }


# Global instance
source_agent = SourceAgent()
