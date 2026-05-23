from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from app.services.database import SupabaseService

# Platform-specific estimated RPMs (revenue per 1,000 views) in USD
# These are conservative averages for the creator economy
PLATFORM_RPMS = {
    "tiktok": 0.50,      # TikTok Creativity Program
    "instagram": 0.30,   # Instagram Reels Play
    "youtube": 2.50,       # YouTube Partner Program
    "facebook": 0.20,    # Facebook Reels
    "twitter": 0.10,     # Twitter/X ad share
    "linkedin": 1.00,    # LinkedIn thought leader ads
}

class EarningsService:
    """Compute and manage earnings from clip performance metrics."""
    
    def __init__(self):
        self.db = SupabaseService()
    
    def estimate_revenue(self, views: int, platform: str) -> float:
        """Estimate revenue for a given view count and platform."""
        rpm = PLATFORM_RPMS.get(platform.lower(), 0.10)
        return (views / 1000.0) * rpm
    
    async def sync_earnings_from_clip(self, clip_id: str) -> Dict[str, Any]:
        """Create or update earnings records based on a clip's current metrics."""
        clip = await self.db.get_clip(clip_id)
        if not clip:
            return {"success": False, "error": "Clip not found"}
        
        user_id = clip.get("user_id")
        views = clip.get("views", 0) or 0
        platform_metrics = clip.get("platform_metrics", {})
        
        if views == 0:
            return {"success": True, "message": "No views to monetize"}
        
        total_revenue = 0.0
        records_created = 0
        
        # Create/update earnings record per platform
        for platform, metrics in (platform_metrics or {}).items():
            platform_views = metrics.get("views", 0)
            if platform_views == 0:
                continue
            
            revenue = self.estimate_revenue(platform_views, platform)
            total_revenue += revenue
            
            # Upsert earnings record for this clip + platform + month
            month_key = datetime.now(timezone.utc).strftime("%Y-%m")
            
            # Check if record exists
            existing = await self._get_earning_record(user_id, clip_id, platform, month_key)
            
            if existing:
                # Update existing
                await self.db.update_earning(existing["id"], {
                    "views": platform_views,
                    "amount": revenue,
                    "updated_at": "now()"
                })
            else:
                # Create new
                await self.db.create_earning({
                    "user_id": user_id,
                    "clip_id": clip_id,
                    "platform": platform,
                    "period": month_key,
                    "views": platform_views,
                    "amount": revenue,
                    "currency": "USD",
                    "source": "estimated",
                    "created_at": "now()",
                    "updated_at": "now()"
                })
                records_created += 1
        
        return {
            "success": True,
            "clip_id": clip_id,
            "total_revenue_usd": round(total_revenue, 4),
            "records_created": records_created,
            "records_updated": len(platform_metrics) - records_created if platform_metrics else 0
        }
    
    async def _get_earning_record(self, user_id: str, clip_id: str, platform: str, period: str) -> Optional[Dict[str, Any]]:
        """Find an existing earnings record for a clip + platform + period."""
        from app.services.database import supabase
        result = supabase.table("earnings")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("clip_id", clip_id)\
            .eq("platform", platform)\
            .eq("period", period)\
            .single()\
            .execute()
        return result.data if result.data else None
    
    async def get_computed_earnings(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        platform: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get earnings combining stored records + computed estimates from clips."""
        # Get stored earnings records
        stored = await self.db.get_earnings(user_id, start_date, end_date, platform)
        
        # Get clips with views in the date range (last 30 days if no range)
        clips = await self.db.list_clips(user_id=user_id, status="posted", limit=500)
        
        # Compute earnings from clips that don't have stored records
        computed_platform_totals = {}
        computed_total = 0.0
        computed_views = 0
        
        for clip in clips:
            clip_views = clip.get("views", 0) or 0
            if clip_views == 0:
                continue
            
            pm = clip.get("platform_metrics", {})
            # If no platform breakdown, attribute all views to "unknown"
            if not pm:
                revenue = self.estimate_revenue(clip_views, "unknown")
                computed_total += revenue
                computed_views += clip_views
                computed_platform_totals["unknown"] = computed_platform_totals.get("unknown", 0) + revenue
            else:
                for p, m in pm.items():
                    pv = m.get("views", 0)
                    revenue = self.estimate_revenue(pv, p)
                    computed_total += revenue
                    computed_views += pv
                    computed_platform_totals[p] = computed_platform_totals.get(p, 0) + revenue
        
        # Merge stored + computed
        stored_total = sum(e.get("amount", 0) for e in stored)
        stored_views = sum(e.get("views", 0) for e in stored)
        
        by_platform = {}
        for e in stored:
            p = e.get("platform", "unknown")
            by_platform[p] = by_platform.get(p, 0) + e.get("amount", 0)
        
        for p, amt in computed_platform_totals.items():
            by_platform[p] = by_platform.get(p, 0) + amt
        
        return {
            "items": stored,
            "summary": {
                "stored_revenue_usd": round(stored_total, 2),
                "computed_revenue_usd": round(computed_total, 2),
                "total_revenue_usd": round(stored_total + computed_total, 2),
                "total_views": stored_views + computed_views,
                "by_platform": {k: round(v, 2) for k, v in by_platform.items()},
                "rpm_ranges": PLATFORM_RPMS
            }
        }


# Global instance
earnings_service = EarningsService()
