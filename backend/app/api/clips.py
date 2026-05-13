from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel

from app.models import (
    Clip, ClipCreate, ClipUpdate, ClipStatus,
    Platform, PlatformPost
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/clips", tags=["clips"])

class ClipListResponse(BaseModel):
    items: List[Clip]
    total: int
    page: int
    page_size: int

class ClipActionRequest(BaseModel):
    action: str  # "approve", "reject", "retry", "delete"
    reason: Optional[str] = None

@router.get("", response_model=ClipListResponse)
async def list_clips(
    status: Optional[ClipStatus] = None,
    pipeline_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    user = Depends(get_current_user)
):
    """List clips with optional filtering."""
    # TODO: Implement with Supabase
    return ClipListResponse(items=[], total=0, page=page, page_size=page_size)

@router.get("/feed")
async def get_clip_feed(
    limit: int = 10,
    user = Depends(get_current_user)
):
    """Get clips ready for approval (swipe deck feed)."""
    # TODO: Return clips in "ready_for_review" status
    return {"items": []}

@router.post("", response_model=Clip, status_code=status.HTTP_201_CREATED)
async def create_clip(
    clip: ClipCreate,
    user = Depends(get_current_user)
):
    """Create a new clip."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{clip_id}", response_model=Clip)
async def get_clip(
    clip_id: str,
    user = Depends(get_current_user)
):
    """Get a specific clip by ID."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")

@router.patch("/{clip_id}", response_model=Clip)
async def update_clip(
    clip_id: str,
    update: ClipUpdate,
    user = Depends(get_current_user)
):
    """Update a clip."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")

@router.post("/{clip_id}/action")
async def clip_action(
    clip_id: str,
    action: ClipActionRequest,
    user = Depends(get_current_user)
):
    """Perform an action on a clip (approve, reject, retry, delete)."""
    # TODO: Implement action handling
    return {"success": True, "clip_id": clip_id, "action": action.action}

@router.post("/{clip_id}/post")
async def post_clip(
    clip_id: str,
    platforms: List[Platform],
    user = Depends(get_current_user)
):
    """Post an approved clip to selected platforms."""
    # TODO: Implement posting logic
    return {"success": True, "clip_id": clip_id, "platforms": platforms}
