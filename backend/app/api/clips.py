from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel

from app.models import (
    Clip, ClipCreate, ClipUpdate, ClipStatus,
    Platform, PlatformPost
)
from app.services.auth import get_current_user
from app.services.database import SupabaseService
from app.services.queue import QueueService
from app.services.scheduler import PostScheduler
from app.services.r2_service import R2Service
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
    """Post an approved clip to selected platforms immediately."""
    try:
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        # TODO: Get social platform access tokens and post
        return {
            "success": True,
            "clip_id": clip_id,
            "platforms": request.platforms,
            "note": "Social posting requires platform OAuth setup"
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
