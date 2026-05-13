from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel

from app.services.database import SupabaseService
from app.services.queue import QueueService

router = APIRouter(prefix="/clips", tags=["clips"])

class ClipListResponse(BaseModel):
    items: List[Clip]
    total: int
    page: int
    page_size: int

class ClipActionRequest(BaseModel):
    action: str  # "approve", "reject", "retry", "delete"
    reason: Optional[str] = None

db = SupabaseService()
queue = QueueService()

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
        
        # Get total count (simplified - in production would query count)
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
        # Create clip in database
        clip_data = clip.model_dump()
        clip_data["user_id"] = user.id
        clip_data["status"] = "queued"
        
        created = await db.create_clip(clip_data)
        
        # Queue for processing
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
        # Query Supabase for clip
        # For now, return a placeholder
        raise HTTPException(status_code=404, detail="Clip not found")
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
            # Re-queue for processing
            clip = await db.get_clip(clip_id)  # This method needs to be added
            if clip:
                await queue.enqueue("clip_generation", {
                    "job_id": clip_id,
                    "clip_id": clip_id,
                    "source_id": clip["source_id"],
                    "pipeline_id": clip["pipeline_id"],
                    "user_id": user.id
                })
        elif action.action == "delete":
            # TODO: Implement delete in database service
            pass
        
        return {"success": True, "clip_id": clip_id, "action": action.action}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Action failed: {str(e)}")

@router.post("/{clip_id}/post")
async def post_clip(
    clip_id: str,
    platforms: List[Platform],
    user = Depends(get_current_user)
):
    """Post an approved clip to selected platforms."""
    try:
        # TODO: Get clip details and post to each platform
        # This requires social platform OAuth tokens
        return {
            "success": True,
            "clip_id": clip_id,
            "platforms": platforms,
            "note": "Social posting requires platform OAuth setup"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Post failed: {str(e)}")
