from supabase import create_client, Client
from typing import Optional, Dict, Any, List
from app.core.config import settings

# Initialize Supabase client with service role for admin operations
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

class SupabaseService:
    """Wrapper for Supabase database operations."""
    
    @staticmethod
    async def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by ID."""
        result = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        return result.data if result.data else None
    
    @staticmethod
    async def create_clip(clip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new clip."""
        result = supabase.table("clips").insert(clip_data).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def update_clip(clip_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a clip."""
        result = supabase.table("clips").update(update_data).eq("id", clip_id).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def list_clips(
        user_id: str,
        status: Optional[str] = None,
        pipeline_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List clips with filters."""
        query = supabase.table("clips").select("*").eq("user_id", user_id)
        
        if status:
            query = query.eq("status", status)
        if pipeline_id:
            query = query.eq("pipeline_id", pipeline_id)
        
        result = query.order("created_at", desc=True).limit(limit).offset(offset).execute()
        return result.data if result.data else []
    
    @staticmethod
    async def create_pipeline(pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new pipeline."""
        result = supabase.table("pipelines").insert(pipeline_data).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def list_pipelines(user_id: str) -> List[Dict[str, Any]]:
        """List all pipelines for a user."""
        result = supabase.table("pipelines").select("*").eq("user_id", user_id).execute()
        return result.data if result.data else []
    
    @staticmethod
    async def create_source(source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new video source."""
        result = supabase.table("sources").insert(source_data).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def list_sources(user_id: str) -> List[Dict[str, Any]]:
        """List all sources for a user."""
        result = supabase.table("sources").select("*").eq("user_id", user_id).execute()
        return result.data if result.data else []
    
    @staticmethod
    async def get_source(source_id: str) -> Optional[Dict[str, Any]]:
        """Get a source by ID."""
        result = supabase.table("sources").select("*").eq("id", source_id).single().execute()
        return result.data if result.data else None
    
    @staticmethod
    async def get_pipeline(pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get a pipeline by ID."""
        result = supabase.table("pipelines").select("*").eq("id", pipeline_id).single().execute()
        return result.data if result.data else None
    
    @staticmethod
    async def update_pipeline(pipeline_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a pipeline."""
        result = supabase.table("pipelines").update(update_data).eq("id", pipeline_id).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def delete_pipeline(pipeline_id: str) -> bool:
        """Delete a pipeline."""
        result = supabase.table("pipelines").delete().eq("id", pipeline_id).execute()
        return len(result.data) > 0 if result.data else False
    
    @staticmethod
    async def get_clip(clip_id: str) -> Optional[Dict[str, Any]]:
        """Get a clip by ID."""
        result = supabase.table("clips").select("*").eq("id", clip_id).single().execute()
        return result.data if result.data else None
    
    @staticmethod
    async def get_clip_revisions(clip_id: str) -> List[Dict[str, Any]]:
        """Get revision history for a clip."""
        result = supabase.table("clip_revisions").select("*").eq("clip_id", clip_id).order("created_at", desc=True).execute()
        return result.data if result.data else []
    
    @staticmethod
    async def create_clip_revision(revision_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a revision history entry."""
        result = supabase.table("clip_revisions").insert(revision_data).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def get_remix_variants(parent_clip_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get all remix variants of a parent clip."""
        result = supabase.table("clips").select("*").eq("parent_clip_id", parent_clip_id).eq("user_id", user_id).order("created_at", desc=True).execute()
        return result.data if result.data else []
    
    @staticmethod
    async def delete_clip(clip_id: str) -> bool:
        """Delete a clip."""
        result = supabase.table("clips").delete().eq("id", clip_id).execute()
        return len(result.data) > 0 if result.data else False
    
    @staticmethod
    async def get_clips_for_posting(
        status: str = "approved",
        scheduled_before: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get clips ready for posting."""
        query = supabase.table("clips").select("*").eq("status", status)
        
        if scheduled_before:
            query = query.lte("scheduled_post_time", scheduled_before)
        
        result = query.execute()
        return result.data if result.data else []
    
    @staticmethod
    async def delete_source(source_id: str) -> bool:
        """Delete a source."""
        result = supabase.table("sources").delete().eq("id", source_id).execute()
        return len(result.data) > 0 if result.data else False
    
    @staticmethod
    async def update_source(source_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a source."""
        result = supabase.table("sources").update(update_data).eq("id", source_id).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def create_profile(profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a user profile."""
        result = supabase.table("profiles").upsert(profile_data).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def update_profile(user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a user profile."""
        result = supabase.table("profiles").update(update_data).eq("id", user_id).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def delete_profile(user_id: str) -> bool:
        """Soft-delete a user profile."""
        result = supabase.table("profiles").update({"deleted_at": "now()"}).eq("id", user_id).execute()
        return len(result.data) > 0 if result.data else False
    
    @staticmethod
    async def get_earnings(
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        platform: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get earnings records for a user."""
        query = supabase.table("earnings").select("*").eq("user_id", user_id)
        
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", end_date)
        if platform:
            query = query.eq("platform", platform)
        
        result = query.order("created_at", desc=True).execute()
        return result.data if result.data else []
    
    @staticmethod
    async def get_earnings_summary(user_id: str, period_start: str, period_end: str) -> Dict[str, Any]:
        """Get earnings summary for a period."""
        earnings = await SupabaseService.get_earnings(user_id, period_start, period_end)
        
        total = sum(e.get("amount", 0) for e in earnings)
        by_platform = {}
        for e in earnings:
            platform = e.get("platform", "unknown")
            by_platform[platform] = by_platform.get(platform, 0) + e.get("amount", 0)
        
        return {
            "total_revenue_cents": int(total * 100),
            "total_views": sum(e.get("views", 0) for e in earnings),
            "by_platform": by_platform,
            "period_start": period_start,
            "period_end": period_end
        }
    
    @staticmethod
    async def store_analytics_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store an analytics event."""
        result = supabase.table("analytics_events").insert(event_data).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def get_analytics_events(user_id: str, event_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get analytics events for a user."""
        query = supabase.table("analytics_events").select("*").eq("user_id", user_id)
        if event_type:
            query = query.eq("event_type", event_type)
        result = query.order("created_at", desc=True).limit(limit).execute()
        return result.data if result.data else []
    
    @staticmethod
    async def count_clips_this_month(user_id: str) -> int:
        """Count clips created by user in current calendar month."""
        from datetime import datetime
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        result = supabase.table("clips")\
            .select("id", count="exact")\
            .eq("user_id", user_id)\
            .gte("created_at", start_of_month)\
            .execute()
        
        return result.count if hasattr(result, 'count') else 0

    @staticmethod
    async def create_earning(earning_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an earnings record."""
        result = supabase.table("earnings").insert(earning_data).execute()
        return result.data[0] if result.data else {}

    @staticmethod
    async def update_earning(earning_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an earnings record."""
        result = supabase.table("earnings").update(update_data).eq("id", earning_id).execute()
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_user_clip_stats(user_id: str) -> Dict[str, Any]:
        """Get aggregated clip stats for a user via true database aggregation."""
        try:
            # Use raw SQL via RPC for true aggregation (SUM, COUNT, GROUP BY)
            # This is O(1) regardless of clip count vs O(n) for Python-side aggregation
            from app.services.database import supabase
            
            # Aggregate totals via raw SQL
            agg_res = supabase.rpc("get_user_stats", {"p_user_id": user_id}).execute()
            if agg_res.data:
                agg = agg_res.data[0] if isinstance(agg_res.data, list) else agg_res.data
                total_clips = agg.get("total_clips", 0)
                total_views = agg.get("total_views", 0)
                total_revenue = agg.get("total_revenue", 0)
            else:
                # Fallback: use count + limited slice (old behavior)
                count_res = supabase.table("clips").select("id", count="exact").eq("user_id", user_id).execute()
                total_clips = count_res.count if hasattr(count_res, 'count') else 0
                total_views = 0
                total_revenue = 0.0
            
            # Platform breakdown via raw SQL
            platform_res = supabase.rpc("get_user_platform_breakdown", {"p_user_id": user_id}).execute()
            platform_breakdown = {}
            if platform_res.data and isinstance(platform_res.data, list):
                for row in platform_res.data:
                    platform_breakdown[row.get("platform", "unknown")] = row.get("count", 0)
            
            # Daily stats (last 30 days) via raw SQL
            daily_res = supabase.rpc("get_user_daily_stats", {"p_user_id": user_id, "p_days": 30}).execute()
            daily_stats = []
            if daily_res.data and isinstance(daily_res.data, list):
                daily_stats = [
                    {
                        "date": row.get("date"),
                        "clips_generated": row.get("clips", 0),
                        "views": row.get("views", 0)
                    }
                    for row in daily_res.data
                ]
            
            return {
                "total_clips": total_clips,
                "total_views": total_views,
                "total_revenue": total_revenue,
                "platform_breakdown": platform_breakdown,
                "daily_stats": daily_stats,
                "_aggregation_method": "db_rpc" if agg_res.data else "db_count_fallback"
            }
            
        except Exception:
            # Ultimate fallback: old method
            return await SupabaseService._get_user_clip_stats_fallback(user_id)
    
    @staticmethod
    async def _get_user_clip_stats_fallback(user_id: str) -> Dict[str, Any]:
        """Fallback Python-side aggregation (for when RPC functions don't exist)."""
        count_res = supabase.table("clips").select("id", count="exact").eq("user_id", user_id).execute()
        total_clips = count_res.count if hasattr(count_res, 'count') else 0
        
        stats_res = supabase.table("clips")\
            .select("views, revenue, platform_posts, created_at")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(500)\
            .execute()
        
        rows = stats_res.data if stats_res.data else []
        total_views = sum(r.get("views", 0) or 0 for r in rows)
        total_revenue = sum(r.get("revenue", 0) or 0 for r in rows)
        
        platform_breakdown = {}
        by_day = {}
        for r in rows:
            posts = r.get("platform_posts", [])
            for post in posts or []:
                platform = post.get("platform", "unknown")
                platform_breakdown[platform] = platform_breakdown.get(platform, 0) + 1
            
            day = r.get("created_at", "")[:10] if r.get("created_at") else ""
            if day:
                if day not in by_day:
                    by_day[day] = {"clips": 0, "views": 0}
                by_day[day]["clips"] += 1
                by_day[day]["views"] += r.get("views", 0) or 0
        
        daily_stats = [
            {"date": day, "clips_generated": s["clips"], "views": s["views"]}
            for day, s in sorted(by_day.items())[-30:]
        ]
        
        return {
            "total_clips": total_clips,
            "total_views": total_views,
            "total_revenue": total_revenue,
            "platform_breakdown": platform_breakdown,
            "daily_stats": daily_stats,
            "_aggregation_method": "python_fallback",
            "_aggregation_sample_size": len(rows)
        }

    @staticmethod
    async def get_pipeline_stats(pipeline_id: str, user_id: str) -> Dict[str, Any]:
        """Get aggregated stats for a specific pipeline via true DB aggregation."""
        try:
            from app.services.database import supabase
            
            # Use RPC for true aggregation
            agg_res = supabase.rpc("get_pipeline_stats", {
                "p_pipeline_id": pipeline_id,
                "p_user_id": user_id
            }).execute()
            
            if agg_res.data and isinstance(agg_res.data, list) and len(agg_res.data) > 0:
                agg = agg_res.data[0]
                return {
                    "clips_generated": agg.get("total_clips", 0),
                    "clips_posted": agg.get("posted_clips", 0),
                    "total_views": agg.get("total_views", 0),
                    "engagement_rate": round(agg.get("engagement_rate", 0), 2),
                    "_aggregation_method": "db_rpc"
                }
        except Exception:
            pass
        
        # Fallback: count + limited slice
        total_res = supabase.table("clips").select("id", count="exact").eq("pipeline_id", pipeline_id).eq("user_id", user_id).execute()
        total_clips = total_res.count if hasattr(total_res, 'count') else 0
        
        posted_res = supabase.table("clips").select("id", count="exact").eq("pipeline_id", pipeline_id).eq("user_id", user_id).eq("status", "posted").execute()
        posted_clips = posted_res.count if hasattr(posted_res, 'count') else 0
        
        stats_res = supabase.table("clips")\
            .select("views, likes, comments, shares")\
            .eq("pipeline_id", pipeline_id)\
            .eq("user_id", user_id)\
            .limit(500)\
            .execute()
        
        rows = stats_res.data if stats_res.data else []
        total_views = sum(r.get("views", 0) or 0 for r in rows)
        engagement = sum(
            (r.get("likes", 0) or 0) + (r.get("comments", 0) or 0) + (r.get("shares", 0) or 0)
            for r in rows
        )
        engagement_rate = (engagement / total_views * 100) if total_views > 0 else 0
        
        return {
            "clips_generated": total_clips,
            "clips_posted": posted_clips,
            "total_views": total_views,
            "engagement_rate": round(engagement_rate, 2),
            "_aggregation_method": "python_fallback",
            "_aggregation_sample_size": len(rows)
        }

    @staticmethod
    async def get_subscription(user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user's subscription."""
        result = supabase.table("subscriptions").select("*").eq("user_id", user_id).single().execute()
        return result.data if result.data else None
    
    @staticmethod
    async def update_subscription(user_id: str, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update or create a user's subscription."""
        result = supabase.table("subscriptions").upsert({"user_id": user_id, **subscription_data}).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def create_social_account(account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a connected social account."""
        result = supabase.table("social_accounts").insert(account_data).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def list_social_accounts(user_id: str) -> List[Dict[str, Any]]:
        """List connected social accounts for a user."""
        result = supabase.table("social_accounts").select("*").eq("user_id", user_id).execute()
        return result.data if result.data else []
    
    @staticmethod
    async def get_social_account(account_id: str) -> Optional[Dict[str, Any]]:
        """Get a social account by ID."""
        result = supabase.table("social_accounts").select("*").eq("id", account_id).single().execute()
        return result.data if result.data else None
    
    @staticmethod
    async def update_social_account(account_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a social account."""
        result = supabase.table("social_accounts").update(update_data).eq("id", account_id).execute()
        return result.data[0] if result.data else {}

    @staticmethod
    async def delete_social_account(account_id: str) -> bool:
        """Delete a social account."""
        result = supabase.table("social_accounts").delete().eq("id", account_id).execute()
        return len(result.data) > 0 if result.data else False
