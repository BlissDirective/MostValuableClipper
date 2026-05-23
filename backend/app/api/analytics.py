from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.services.auth import get_current_user
from app.services.database import SupabaseService, supabase
from app.services.hook_analysis_service import hook_analysis_service
from app.services.queue import CacheService

router = APIRouter(prefix="/analytics", tags=["analytics"])
db = SupabaseService()
cache = CacheService()

ANALYTICS_CACHE_TTL = 300  # 5 minutes

class EventPayload(BaseModel):
    event_type: str
    event_data: Optional[dict] = None

class CaptionStyleResult(BaseModel):
    name: str
    body: str
    delta_pct: float
    variant: str  # positive, negative, neutral
    sample_size: int

class CaptionStylesResponse(BaseModel):
    styles: List[CaptionStyleResult]
    baseline_views: float
    total_clips_analyzed: int
    generated_at: str

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
    """Get full analytics dashboard using database aggregation with Redis caching."""
    cache_key = f"analytics:dashboard:{user.id}"
    
    try:
        # Try cache first
        cached = await cache.get(cache_key)
        if cached:
            cached["_cached"] = True
            cached["_cached_at"] = datetime.now().isoformat()
            return cached
        
        stats = await db.get_user_clip_stats(user.id)
        stats["_cached"] = False
        stats["_cached_at"] = datetime.now().isoformat()
        
        # Cache for 5 minutes
        await cache.set(cache_key, stats, ttl_seconds=ANALYTICS_CACHE_TTL)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")

@router.get("/pipeline/{pipeline_id}")
async def get_pipeline_analytics(
    pipeline_id: str,
    days: int = 30,
    user = Depends(get_current_user)
):
    """Get analytics for a specific pipeline using database aggregation with caching."""
    try:
        # Verify ownership
        pipeline = await db.get_pipeline(pipeline_id)
        if not pipeline or pipeline.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        cache_key = f"analytics:pipeline:{pipeline_id}:{days}"
        
        cached = await cache.get(cache_key)
        if cached:
            cached["_cached"] = True
            cached["_cached_at"] = datetime.now().isoformat()
            return cached
        
        stats = await db.get_pipeline_stats(pipeline_id, user.id)
        stats["pipeline_id"] = pipeline_id
        stats["period_days"] = days
        stats["_cached"] = False
        stats["_cached_at"] = datetime.now().isoformat()
        
        await cache.set(cache_key, stats, ttl_seconds=ANALYTICS_CACHE_TTL)
        return stats
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


# ── Caption Style Analysis ──

def _classify_caption(caption: str, hashtags: List[str]) -> List[str]:
    """Return list of style tags for a caption."""
    styles = []
    text = (caption or "").strip()
    h_count = len(hashtags) if hashtags else 0
    
    # Length-based
    if len(text) < 90:
        styles.append("short")
    elif len(text) <= 200:
        styles.append("medium")
    else:
        styles.append("long")
    
    # Hashtag density
    if h_count == 0:
        styles.append("no_hashtags")
    elif h_count <= 2:
        styles.append("light_hashtags")
    else:
        styles.append("hashtag_heavy")
    
    # Structural patterns
    if text and text[0].isdigit():
        styles.append("numbered_list")
    if text.endswith("?"):
        styles.append("question")
    if any(w in text.lower() for w in ["link", "follow", "click", "swipe up", "bio"]):
        styles.append("call_to_action")
    if "\"" in text or "'" in text:
        styles.append("quote")
    
    return styles


@router.get("/caption-styles", response_model=CaptionStylesResponse)
async def get_caption_style_analysis(
    days: int = 30,
    user = Depends(get_current_user)
):
    """Analyze caption performance by style category.
    
    Categorizes posted clip captions by length, hashtag density, and
    structural patterns, then computes average views per category.
    Returns ranked styles with performance deltas vs baseline.
    """
    try:
        # Fetch clips posted in the period
        since = datetime.now() - timedelta(days=days)
        clips_res = supabase.table("clips")\
            .select("id, views, platform_posts, created_at")\
            .eq("user_id", user.id)\
            .eq("status", "posted")\
            .gte("created_at", since.isoformat())\
            .order("created_at", desc=True)\
            .limit(500)\
            .execute()
        
        clips = clips_res.data or []
        if not clips:
            return CaptionStylesResponse(
                styles=[],
                baseline_views=0,
                total_clips_analyzed=0,
                generated_at=datetime.now().isoformat()
            )
        
        # Aggregate views by style
        style_stats: dict = {}  # style -> {"views": [], "clips": 0}
        all_views = []
        
        for clip in clips:
            views = clip.get("views", 0) or 0
            all_views.append(views)
            posts = clip.get("platform_posts", []) or []
            
            for post in posts:
                caption = post.get("caption", "")
                hashtags = post.get("hashtags", []) or []
                styles = _classify_caption(caption, hashtags)
                
                for s in styles:
                    if s not in style_stats:
                        style_stats[s] = {"views": [], "clips": 0}
                    style_stats[s]["views"].append(views)
                    style_stats[s]["clips"] += 1
        
        baseline = sum(all_views) / max(1, len(all_views))
        
        # Build ranked results
        results = []
        style_labels = {
            "short": "Short · under 90 chars",
            "medium": "Medium · 90–200 chars",
            "long": "Long · over 200 chars",
            "no_hashtags": "No hashtags",
            "light_hashtags": "Light hashtags · 1–2 tags",
            "hashtag_heavy": "Hashtag-heavy · 3+ tags",
            "numbered_list": "Numbered list",
            "question": "Question hook",
            "call_to_action": "Call to action",
            "quote": "Quote format",
        }
        style_descriptions = {
            "short": "Concise captions that get straight to the point.",
            "medium": "Balanced detail without overwhelming the viewer.",
            "long": "Storytelling or detailed explanation captions.",
            "no_hashtags": "Captions relying purely on content, no tags.",
            "light_hashtags": "Minimal hashtag strategy for discoverability.",
            "hashtag_heavy": "Maximum hashtag coverage for reach.",
            "numbered_list": "Structured list format for easy scanning.",
            "question": "Engagement-driven question openings.",
            "call_to_action": "Direct prompts to drive action.",
            "quote": "Inspirational or provocative quote format.",
        }
        
        for style, stats in style_stats.items():
            if stats["clips"] < 2:  # Need at least 2 clips for meaningful data
                continue
            avg_views = sum(stats["views"]) / len(stats["views"])
            delta = ((avg_views - baseline) / baseline * 100) if baseline > 0 else 0
            
            if delta > 5:
                variant = "positive"
            elif delta < -5:
                variant = "negative"
            else:
                variant = "neutral"
            
            results.append(CaptionStyleResult(
                name=style_labels.get(style, style),
                body=style_descriptions.get(style, f"{stats['clips']} clips with this style."),
                delta_pct=round(delta, 1),
                variant=variant,
                sample_size=stats["clips"]
            ))
        
        # Sort by absolute delta (most impactful first)
        results.sort(key=lambda r: abs(r.delta_pct), reverse=True)
        
        return CaptionStylesResponse(
            styles=results[:6],  # Top 6 styles
            baseline_views=round(baseline, 1),
            total_clips_analyzed=len(clips),
            generated_at=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze caption styles: {str(e)}")


@router.post("/cache/clear")
async def clear_analytics_cache(user = Depends(get_current_user)):
    """Clear analytics cache for the current user."""
    try:
        await cache.delete(f"analytics:dashboard:{user.id}")
        return {"success": True, "message": "Analytics cache cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

