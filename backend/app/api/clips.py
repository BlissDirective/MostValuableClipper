from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel

from app.models import (
    Clip, ClipCreate, ClipUpdate, ClipStatus,
    Platform, PlatformPost, ClipEditRequest
)
from app.services.auth import get_current_user
from app.services.database import SupabaseService
from app.services.queue import QueueService
from app.services.scheduler import PostScheduler
from app.services.r2_service import R2Service
from app.services.zernio_service import ZernioService
from app.services.ffmpeg_service import FFmpegEditService
from datetime import datetime, timedelta

router = APIRouter(prefix="/clips", tags=["clips"])

class ClipListResponse(BaseModel):
    items: List[Clip]
    total: int
    page: int
    page_size: int

class ClipActionRequest(BaseModel):
    action: str  # "approve", "reject", "retry", "delete"
    reason: Optional[str] = None

class ScheduleRequest(BaseModel):
    post_time: str  # ISO 8601

class PostRequest(BaseModel):
    platforms: List[Platform]

db = SupabaseService()
queue = QueueService()
scheduler = PostScheduler()
r2 = R2Service()

# Initialize Zernio service if key is configured
zernio: Optional[ZernioService] = None
try:
    zernio = ZernioService()
except ValueError:
    zernio = None

@router.get("", response_model=ClipListResponse)
async def list_clips(
    status: Optional[ClipStatus] = None,
    pipeline_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    user = Depends(get_current_user)
):
    """List clips with optional filtering."""
    try:
        clips = await db.list_clips(
            user_id=user.id,
            status=status,
            pipeline_id=pipeline_id,
            limit=page_size,
            offset=(page - 1) * page_size
        )
        
        total = len(clips)  # Placeholder
        
        return ClipListResponse(
            items=clips,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list clips: {str(e)}")

@router.get("/feed")
async def get_clip_feed(
    limit: int = 10,
    user = Depends(get_current_user)
):
    """Get clips ready for approval (swipe deck feed)."""
    try:
        clips = await db.list_clips(
            user_id=user.id,
            status="ready_for_review",
            limit=limit
        )
        return {"items": clips}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get feed: {str(e)}")

@router.post("", response_model=Clip, status_code=status.HTTP_201_CREATED)
async def create_clip(
    clip: ClipCreate,
    user = Depends(get_current_user)
):
    """Create a new clip and queue it for processing."""
    try:
        clip_data = clip.model_dump()
        clip_data["user_id"] = user.id
        clip_data["status"] = "queued"
        
        created = await db.create_clip(clip_data)
        
        await queue.enqueue("clip_generation", {
            "job_id": created["id"],
            "clip_id": created["id"],
            "source_id": clip.source_id,
            "pipeline_id": clip.pipeline_id,
            "user_id": user.id
        })
        
        return created
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create clip: {str(e)}")

@router.get("/{clip_id}", response_model=Clip)
async def get_clip(
    clip_id: str,
    user = Depends(get_current_user)
):
    """Get a specific clip by ID."""
    try:
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        return clip
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get clip: {str(e)}")

@router.patch("/{clip_id}", response_model=Clip)
async def update_clip(
    clip_id: str,
    update: ClipUpdate,
    user = Depends(get_current_user)
):
    """Update a clip."""
    try:
        updated = await db.update_clip(clip_id, update.model_dump(exclude_unset=True))
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update clip: {str(e)}")

@router.post("/{clip_id}/approve")
async def approve_clip(
    clip_id: str,
    user = Depends(get_current_user)
):
    """Approve a clip for posting."""
    try:
        await db.update_clip(clip_id, {"status": "approved"})
        return {"success": True, "clip_id": clip_id, "status": "approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Approve failed: {str(e)}")

@router.post("/{clip_id}/reject")
async def reject_clip(
    clip_id: str,
    reason: Optional[str] = None,
    user = Depends(get_current_user)
):
    """Reject a clip."""
    try:
        await db.update_clip(clip_id, {
            "status": "rejected",
            "rejection_reason": reason
        })
        return {"success": True, "clip_id": clip_id, "status": "rejected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reject failed: {str(e)}")

@router.post("/{clip_id}/action")
async def clip_action(
    clip_id: str,
    action: ClipActionRequest,
    user = Depends(get_current_user)
):
    """Perform an action on a clip (approve, reject, retry, delete)."""
    try:
        if action.action == "approve":
            await db.update_clip(clip_id, {"status": "approved"})
        elif action.action == "reject":
            await db.update_clip(clip_id, {
                "status": "rejected",
                "rejection_reason": action.reason
            })
        elif action.action == "retry":
            await db.update_clip(clip_id, {"status": "queued"})
            clip = await db.get_clip(clip_id)
            if clip:
                await queue.enqueue("clip_generation", {
                    "job_id": clip_id,
                    "clip_id": clip_id,
                    "source_id": clip["source_id"],
                    "pipeline_id": clip["pipeline_id"],
                    "user_id": user.id
                })
        elif action.action == "delete":
            await db.delete_clip(clip_id)
        
        return {"success": True, "clip_id": clip_id, "action": action.action}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Action failed: {str(e)}")

@router.patch("/{clip_id}/schedule")
async def schedule_clip(
    clip_id: str,
    request: ScheduleRequest,
    user = Depends(get_current_user)
):
    """Schedule a clip for posting at a specific time."""
    try:
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        result = await scheduler.schedule_clip(
            clip_id=clip_id,
            pipeline_id=clip["pipeline_id"],
            post_time=request.post_time
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schedule failed: {str(e)}")

@router.post("/{clip_id}/post")
async def post_clip(
    clip_id: str,
    request: PostRequest,
    user = Depends(get_current_user)
):
    """Post an approved clip to selected platforms immediately via Zernio.
    
    If Zernio is configured, posts immediately with rate limit handling.
    Otherwise, falls back to queueing for background worker.
    """
    try:
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        video_url = clip.get("video_url")
        if not video_url:
            raise HTTPException(status_code=400, detail="Clip has no video URL")
        
        # Map platforms to Zernio format
        zernio_platforms = [ZernioService.map_platform_to_zernio(p.value) for p in request.platforms]
        
        if zernio:
            # Post via Zernio immediately
            result = await zernio.post_clip(
                video_url=video_url,
                caption=clip.get("caption", ""),
                platforms=zernio_platforms,
                hashtags=clip.get("tags", [])
            )
            
            # Update clip with post IDs
            platform_posts = {}
            for platform_result in result.get("platforms", []):
                platform_name = ZernioService.map_zernio_to_platform(platform_result.get("platform", ""))
                platform_posts[platform_name] = {
                    "platform": platform_name,
                    "post_id": platform_result.get("post_id"),
                    "post_url": platform_result.get("post_url"),
                    "status": "posted" if platform_result.get("success") else "failed",
                    "metrics": {}
                }
            
            await db.update_clip(clip_id, {
                "platform_posts": platform_posts,
                "status": "posted",
                "posted_at": "now()"
            })
            
            return {
                "success": True,
                "clip_id": clip_id,
                "platforms": platform_posts,
                "zernio_post_id": result.get("post_id"),
                "posted_via": "zernio"
            }
        else:
            # Fallback: queue for background worker
            results = []
            for platform in request.platforms:
                await queue.enqueue("social_post", {
                    "clip_id": clip_id,
                    "platform": platform.value,
                    "user_id": user.id,
                    "scheduled": False
                })
                results.append({"platform": platform.value, "status": "queued"})
            
            await db.update_clip(clip_id, {"status": "scheduled"})
            
            return {
                "success": True,
                "clip_id": clip_id,
                "results": results,
                "posted_via": "queue"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Post failed: {str(e)}")

@router.post("/{clip_id}/download-url")
async def get_download_url(
    clip_id: str,
    user = Depends(get_current_user)
):
    """Generate a presigned R2 URL for downloading a clip.
    
    The URL expires in 5 minutes and forces Content-Disposition: attachment
    so the device treats it as a download, not inline playback.
    """
    try:
        # Verify ownership
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to download this clip")
        
        if clip.get("status") not in ("rendered", "approved", "posted"):
            raise HTTPException(status_code=400, detail="Clip is not ready for download")
        
        # Build R2 key — follows storage convention: /clips/{clip_id}.mp4
        key = f"clips/{clip_id}.mp4"
        
        # Generate presigned URL with attachment disposition
        url = await r2.get_presigned_download_url(
            key=key,
            expires_in=300,  # 5 minutes
            filename=f"blissclip_{clip_id}.mp4"
        )
        
        return {
            "url": url,
            "expires_at": (datetime.utcnow() + timedelta(seconds=300)).isoformat(),
            "filename": f"blissclip_{clip_id}.mp4",
            "content_type": "video/mp4",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {str(e)}")


@router.post("/{clip_id}/edit")
async def edit_clip(
    clip_id: str,
    request: ClipEditRequest,
    user = Depends(get_current_user)
):
    """Edit a clip with advanced FFmpeg processing.
    
    Supports: trim, segments, caption, text overlays, filters,
    speed adjustment, audio mute, transitions.
    
    Processing is async via queue. Returns job_id for polling.
    """
    try:
        # Verify ownership
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Validate recipe
        ffmpeg = FFmpegEditService()
        is_valid, error = ffmpeg.validate_recipe(request.model_dump(exclude_unset=True))
        if not is_valid:
            raise HTTPException(status_code=400, detail=error)
        
        # Queue the edit job
        recipe_data = request.model_dump(exclude_unset=True)
        job_data = {
            "job_type": "clip_edit",
            "clip_id": clip_id,
            "user_id": user.id,
            "source_url": clip.get("video_url"),
            "recipe": recipe_data,
            "status": "queued",
            "created_at": datetime.utcnow().isoformat()
        }
        
        job_id = await queue.enqueue("clip_edit", job_data)
        
        # Update clip status to indicate editing in progress
        await db.update_clip(clip_id, {
            "status": "editing",
            "edit_job_id": job_id,
            "edit_recipe": recipe_data
        })
        
        return {
            "success": True,
            "clip_id": clip_id,
            "job_id": job_id,
            "status": "queued",
            "message": "Edit job queued. Poll /clips/{id} for status updates."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Edit failed: {str(e)}")


@router.get("/{clip_id}/edit-status")
async def get_edit_status(
    clip_id: str,
    user = Depends(get_current_user)
):
    """Get the status of a clip edit job."""
    try:
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        job_id = clip.get("edit_job_id")
        if not job_id:
            return {"status": "no_edit", "clip_id": clip_id}
        
        # Check queue status
        job_status = await queue.get_job_status(job_id)
        
        return {
            "clip_id": clip_id,
            "job_id": job_id,
            "status": job_status or clip.get("status", "unknown"),
            "video_url": clip.get("video_url") if clip.get("status") == "rendered" else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get edit status: {str(e)}")
