from supabase import create_client, Client
from typing import Optional, Dict, Any, List
from app.core.config import settings

# Admin client: uses service-role key. Only for system/webhook operations that
# have no user context (e.g. Stripe webhooks, background workers). User-facing
# API endpoints MUST use get_user_client() so that RLS is enforced.
supabase_admin: Client = create_client(
    settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
)

# Backward-compat alias — existing service files that imported `supabase` directly
# continue to work; they are system-level operations and admin access is correct.
supabase = supabase_admin


def get_user_client(access_token: str) -> Client:
    """Return a Supabase client authenticated as the requesting user.

    Queries executed through this client are subject to Row Level Security
    policies keyed on auth.uid(), preventing cross-user data access.
    """
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    # Set the user JWT so PostgREST evaluates auth.uid() correctly
    client.postgrest.auth(access_token)
    return client


class SupabaseService:
    """Wrapper for Supabase database operations.

    Pass a user-scoped client (from get_user_client) for user-facing endpoints
    so that RLS policies apply. Leave client=None only for system operations.
    """

    def __init__(self, client: Optional[Client] = None):
        self._db = client or supabase_admin

    # ─── Profiles ─────────────────────────────────────────────────────────────

    async def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        result = self._db.table("profiles").select("*").eq("id", user_id).single().execute()
        return result.data if result.data else None

    async def create_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self._db.table("profiles").upsert(profile_data).execute()
        return result.data[0] if result.data else {}

    async def update_profile(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self._db.table("profiles").update(update_data).eq("id", user_id).execute()
        return result.data[0] if result.data else {}

    async def delete_profile(self, user_id: str) -> bool:
        result = self._db.table("profiles").update({"deleted_at": "now()"}).eq("id", user_id).execute()
        return len(result.data) > 0 if result.data else False

    # ─── Clips ────────────────────────────────────────────────────────────────

    async def create_clip(self, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self._db.table("clips").insert(clip_data).execute()
        return result.data[0] if result.data else {}

    async def update_clip(self, clip_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self._db.table("clips").update(update_data).eq("id", clip_id).execute()
        return result.data[0] if result.data else {}

    async def list_clips(
        self,
        user_id: str,
        status: Optional[str] = None,
        pipeline_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query = self._db.table("clips").select("*").eq("user_id", user_id)
        if status:
            query = query.eq("status", status)
        if pipeline_id:
            query = query.eq("pipeline_id", pipeline_id)
        result = query.order("created_at", desc=True).limit(limit).offset(offset).execute()
        return result.data if result.data else []

    async def get_clip(self, clip_id: str) -> Optional[Dict[str, Any]]:
        result = self._db.table("clips").select("*").eq("id", clip_id).single().execute()
        return result.data if result.data else None

    async def delete_clip(self, clip_id: str) -> bool:
        result = self._db.table("clips").delete().eq("id", clip_id).execute()
        return len(result.data) > 0 if result.data else False

    async def get_clips_for_posting(
        self, status: str = "approved", scheduled_before: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = self._db.table("clips").select("*").eq("status", status)
        if scheduled_before:
            query = query.lte("scheduled_post_time", scheduled_before)
        result = query.execute()
        return result.data if result.data else []

    async def get_clip_revisions(self, clip_id: str) -> List[Dict[str, Any]]:
        result = (
            self._db.table("clip_revisions")
            .select("*")
            .eq("clip_id", clip_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data if result.data else []

    async def create_clip_revision(self, revision_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self._db.table("clip_revisions").insert(revision_data).execute()
        return result.data[0] if result.data else {}

    async def get_remix_variants(
        self, parent_clip_id: str, user_id: str
    ) -> List[Dict[str, Any]]:
        result = (
            self._db.table("clips")
            .select("*")
            .eq("parent_clip_id", parent_clip_id)
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data if result.data else []

    async def count_clips_this_month(self, user_id: str) -> int:
        from datetime import datetime
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        result = (
            self._db.table("clips")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", start_of_month)
            .execute()
        )
        return result.count if hasattr(result, "count") else 0

    # ─── Pipelines ────────────────────────────────────────────────────────────

    async def create_pipeline(self, pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self._db.table("pipelines").insert(pipeline_data).execute()
        return result.data[0] if result.data else {}

    async def list_pipelines(self, user_id: str) -> List[Dict[str, Any]]:
        result = self._db.table("pipelines").select("*").eq("user_id", user_id).execute()
        return result.data if result.data else []

    async def get_pipeline(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        result = self._db.table("pipelines").select("*").eq("id", pipeline_id).single().execute()
        return result.data if result.data else None

    async def update_pipeline(self, pipeline_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self._db.table("pipelines").update(update_data).eq("id", pipeline_id).execute()
        return result.data[0] if result.data else {}

    async def delete_pipeline(self, pipeline_id: str) -> bool:
        result = self._db.table("pipelines").delete().eq("id", pipeline_id).execute()
        return len(result.data) > 0 if result.data else False

    # ─── Sources ──────────────────────────────────────────────────────────────

    async def create_source(self, source_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self._db.table("sources").insert(source_data).execute()
        return result.data[0] if result.data else {}

    async def list_sources(self, user_id: str) -> List[Dict[str, Any]]:
        result = self._db.table("sources").select("*").eq("user_id", user_id).execute()
        return result.data if result.data else []

    async def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        result = self._db.table("sources").select("*").eq("id", source_id).single().execute()
        return result.data if result.data else None

    async def update_source(self, source_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self._db.table("sources").update(update_data).eq("id", source_id).execute()
        return result.data[0] if result.data else {}

    async def delete_source(self, source_id: str) -> bool:
        result = self._db.table("sources").delete().eq("id", source_id).execute()
        return len(result.data) > 0 if result.data else False

    # ─── Earnings ─────────────────────────────────────────────────────────────

    async def get_earnings(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = self._db.table("earnings").select("*").eq("user_id", user_id)
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", end_date)
        if platform:
            query = query.eq("platform", platform)
        result = query.order("created_at", desc=True).execute()
        return result.data if result.data else []

    async def get_earnings_summary(
        self, user_id: str, period_start: str, period_end: str
    ) -> Dict[str, Any]:
        earnings = await self.get_earnings(user_id, period_start, period_end)
        total = sum(e.get("amount", 0) for e in earnings)
        by_platform: Dict[str, float] = {}
        for e in earnings:
            p = e.get("platform", "unknown")
            by_platform[p] = by_platform.get(p, 0) + e.get("amount", 0)
        return {
            "total_revenue_cents": int(total * 100),
            "total_views": sum(e.get("views", 0) for e in earnings),
            "by_platform": by_platform,
            "period_start": period_start,
            "period_end": period_end,
        }

    async def create_earning(self, earning_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self._db.table("earnings").insert(earning_data).execute()
        return result.data[0] if result.data else {}

    async def update_earning(self, earning_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self._db.table("earnings").update(update_data).eq("id", earning_id).execute()
        return result.data[0] if result.data else {}

    # ─── Analytics ────────────────────────────────────────────────────────────

    async def store_analytics_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self._db.table("analytics_events").insert(event_data).execute()
        return result.data[0] if result.data else {}

    async def get_analytics_events(
        self, user_id: str, event_type: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        query = self._db.table("analytics_events").select("*").eq("user_id", user_id)
        if event_type:
            query = query.eq("event_type", event_type)
        result = query.order("created_at", desc=True).limit(limit).execute()
        return result.data if result.data else []

    async def get_user_clip_stats(self, user_id: str) -> Dict[str, Any]:
        """Aggregated clip stats via DB RPC (falls back to Python-side)."""
        try:
            agg_res = self._db.rpc("get_user_stats", {"p_user_id": user_id}).execute()
            if agg_res.data:
                agg = agg_res.data[0] if isinstance(agg_res.data, list) else agg_res.data
                total_clips = agg.get("total_clips", 0)
                total_views = agg.get("total_views", 0)
                total_revenue = agg.get("total_revenue", 0)
            else:
                count_res = (
                    self._db.table("clips")
                    .select("id", count="exact")
                    .eq("user_id", user_id)
                    .execute()
                )
                total_clips = count_res.count if hasattr(count_res, "count") else 0
                total_views = 0
                total_revenue = 0.0

            platform_res = self._db.rpc(
                "get_user_platform_breakdown", {"p_user_id": user_id}
            ).execute()
            platform_breakdown: Dict[str, int] = {}
            if platform_res.data and isinstance(platform_res.data, list):
                for row in platform_res.data:
                    platform_breakdown[row.get("platform", "unknown")] = row.get("count", 0)

            daily_res = self._db.rpc(
                "get_user_daily_stats", {"p_user_id": user_id, "p_days": 30}
            ).execute()
            daily_stats = []
            if daily_res.data and isinstance(daily_res.data, list):
                daily_stats = [
                    {
                        "date": row.get("date"),
                        "clips_generated": row.get("clips", 0),
                        "views": row.get("views", 0),
                    }
                    for row in daily_res.data
                ]

            return {
                "total_clips": total_clips,
                "total_views": total_views,
                "total_revenue": total_revenue,
                "platform_breakdown": platform_breakdown,
                "daily_stats": daily_stats,
                "_aggregation_method": "db_rpc" if agg_res.data else "db_count_fallback",
            }
        except Exception:
            return await self._get_user_clip_stats_fallback(user_id)

    async def _get_user_clip_stats_fallback(self, user_id: str) -> Dict[str, Any]:
        count_res = (
            self._db.table("clips")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        total_clips = count_res.count if hasattr(count_res, "count") else 0

        stats_res = (
            self._db.table("clips")
            .select("views, revenue, platform_posts, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(500)
            .execute()
        )
        rows = stats_res.data if stats_res.data else []
        total_views = sum(r.get("views", 0) or 0 for r in rows)
        total_revenue = sum(r.get("revenue", 0) or 0 for r in rows)

        platform_breakdown: Dict[str, int] = {}
        by_day: Dict[str, Dict[str, int]] = {}
        for r in rows:
            for post in r.get("platform_posts") or []:
                p = post.get("platform", "unknown")
                platform_breakdown[p] = platform_breakdown.get(p, 0) + 1
            day = (r.get("created_at") or "")[:10]
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
            "_aggregation_sample_size": len(rows),
        }

    async def get_pipeline_stats(self, pipeline_id: str, user_id: str) -> Dict[str, Any]:
        try:
            agg_res = self._db.rpc(
                "get_pipeline_stats", {"p_pipeline_id": pipeline_id, "p_user_id": user_id}
            ).execute()
            if agg_res.data and isinstance(agg_res.data, list) and len(agg_res.data) > 0:
                agg = agg_res.data[0]
                return {
                    "clips_generated": agg.get("total_clips", 0),
                    "clips_posted": agg.get("posted_clips", 0),
                    "total_views": agg.get("total_views", 0),
                    "engagement_rate": round(agg.get("engagement_rate", 0), 2),
                    "_aggregation_method": "db_rpc",
                }
        except Exception:
            pass

        total_res = (
            self._db.table("clips")
            .select("id", count="exact")
            .eq("pipeline_id", pipeline_id)
            .eq("user_id", user_id)
            .execute()
        )
        total_clips = total_res.count if hasattr(total_res, "count") else 0

        posted_res = (
            self._db.table("clips")
            .select("id", count="exact")
            .eq("pipeline_id", pipeline_id)
            .eq("user_id", user_id)
            .eq("status", "posted")
            .execute()
        )
        posted_clips = posted_res.count if hasattr(posted_res, "count") else 0

        stats_res = (
            self._db.table("clips")
            .select("views, likes, comments, shares")
            .eq("pipeline_id", pipeline_id)
            .eq("user_id", user_id)
            .limit(500)
            .execute()
        )
        rows = stats_res.data if stats_res.data else []
        total_views = sum(r.get("views", 0) or 0 for r in rows)
        engagement = sum(
            (r.get("likes", 0) or 0)
            + (r.get("comments", 0) or 0)
            + (r.get("shares", 0) or 0)
            for r in rows
        )
        engagement_rate = (engagement / total_views * 100) if total_views > 0 else 0

        return {
            "clips_generated": total_clips,
            "clips_posted": posted_clips,
            "total_views": total_views,
            "engagement_rate": round(engagement_rate, 2),
            "_aggregation_method": "python_fallback",
            "_aggregation_sample_size": len(rows),
        }

    # ─── Subscriptions ────────────────────────────────────────────────────────

    async def get_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        result = self._db.table("subscriptions").select("*").eq("user_id", user_id).single().execute()
        return result.data if result.data else None

    async def update_subscription(
        self, user_id: str, subscription_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        result = (
            self._db.table("subscriptions")
            .upsert({"user_id": user_id, **subscription_data})
            .execute()
        )
        return result.data[0] if result.data else {}

    # ─── Social accounts ──────────────────────────────────────────────────────

    async def create_social_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        result = self._db.table("social_accounts").insert(account_data).execute()
        return result.data[0] if result.data else {}

    async def list_social_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        result = self._db.table("social_accounts").select("*").eq("user_id", user_id).execute()
        return result.data if result.data else []

    async def get_social_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        result = self._db.table("social_accounts").select("*").eq("id", account_id).single().execute()
        return result.data if result.data else None

    async def update_social_account(
        self, account_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        result = (
            self._db.table("social_accounts").update(update_data).eq("id", account_id).execute()
        )
        return result.data[0] if result.data else {}

    async def delete_social_account(self, account_id: str) -> bool:
        result = self._db.table("social_accounts").delete().eq("id", account_id).execute()
        return len(result.data) > 0 if result.data else False
