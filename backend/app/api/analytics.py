from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.services.auth import get_current_user
from app.services.database import SupabaseService
from app.services.hook_analysis_service import hook_analysis_service

router = APIRouter(prefix="/analytics", tags=["analytics"])
db = SupabaseService()

class EventPayload(BaseModel):
    event_type: str
    event_data: Optional[dict] = None

@router.post("/events")
async def track_event(
    event: EventPayload,
    user = Depends(get_current_user)
):
    """Track an analytics event."""
    try:
        await db.store_analytics_event({
            "user_id": user.id,
            "event_type": event.event_type,
            "event_data": event.event_data,
            "created_at": datetime.now().isoformat()
        })
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track event: {str(e)}")

@router.get("/dashboard")
async def get_analytics_dashboard(user = Depends(get_current_user)):
    """Get full analytics dashboard."""
    try:
        # Get user's clips for stats
        from app.services.database import SupabaseService
        _db = SupabaseService()
        clips = await _db.list_clips(user_id=user.id, limit=1000)
        
        total_clips = len(clips)
        total_views = sum(c.get("views", 0) for c in clips)
        total_revenue = sum(c.get("revenue", 0) for c in clips)
        
        platform_breakdown = {}
        for clip in clips:
            posts = clip.get("platform_posts", [])
            for post in posts:
                platform = post.get("platform", "unknown")
                platform_breakdown[platform] = platform_breakdown.get(platform, 0) + 1
        
        # Daily stats for the last 30 days
        daily_stats = []
        from collections import defaultdict
        by_day = defaultdict(lambda: {"clips": 0, "views": 0})
        for clip in clips:
            day = clip.get("created_at", "")[:10] if clip.get("created_at") else ""
            if day:
                by_day[day]["clips"] += 1
                by_day[day]["views"] += clip.get("views", 0)
        
        for day, stats in sorted(by_day.items())[-30:]:
            daily_stats.append({
                "date": day,
                "clips_generated": stats["clips"],
                "views": stats["views"]
            })
        
        return {
            "total_clips": total_clips,
            "total_views": total_views,
            "total_revenue": total_revenue,
            "platform_breakdown": platform_breakdown,
            "daily_stats": daily_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")

@router.get("/pipeline/{pipeline_id}")
async def get_pipeline_analytics(
    pipeline_id: str,
    days: int = 30,
    user = Depends(get_current_user)
):
    """Get analytics for a specific pipeline."""
    try:
        from app.services.database import SupabaseService
        _db = SupabaseService()
        
        # Verify ownership
        pipeline = await _db.get_pipeline(pipeline_id)
        if not pipeline or pipeline.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        clips = await _db.list_clips(user_id=user.id, pipeline_id=pipeline_id, limit=1000)
        
        total_views = sum(c.get("views", 0) for c in clips)
        engagement = sum(c.get("likes", 0) + c.get("comments", 0) + c.get("shares", 0) for c in clips)
        engagement_rate = (engagement / total_views * 100) if total_views > 0 else 0
        
        return {
            "pipeline_id": pipeline_id,
            "period_days": days,
            "clips_generated": len(clips),
            "clips_posted": len([c for c in clips if c.get("status") == "posted"]),
            "total_views": total_views,
            "engagement_rate": round(engagement_rate, 2)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pipeline analytics: {str(e)}")

@router.get("/hooks")
async def get_hook_analysis(
    days: int = 30,
    user = Depends(get_current_user)
):
    """Get AI-powered hook archetype analysis for the user's clips.

    Analyzes clip openings, classifies hook patterns dynamically,
    correlates with performance metrics, and returns ranked archetypes
    with retention deltas and generated insights.
    """
    try:
        result = await hook_analysis_service.analyze_hooks(
            user_id=user.id,
            days=days
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze hooks: {str(e)}")
