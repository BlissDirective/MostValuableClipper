from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

from app.models import Source, SourceCreate
from app.services.auth import get_current_user
from app.services.database import SupabaseService
from app.services.queue import QueueService

router = APIRouter(prefix="/sources", tags=["sources"])

db = SupabaseService()
queue = QueueService()

@router.get("")
async def list_sources(
    pipeline_id: Optional[str] = None,
    user = Depends(get_current_user)
):
    """List all video sources for the current user."""
    try:
        sources = await db.list_sources(user.id)
        
        if pipeline_id:
            sources = [s for s in sources if s.get("pipeline_id") == pipeline_id]
        
        return {"items": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sources: {str(e)}")

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_source(
    source: SourceCreate,
    user = Depends(get_current_user)
):
    """Add a new video source."""
    try:
        source_data = source.model_dump()
        source_data["user_id"] = user.id
        source_data["videos_found_count"] = 0
        source_data["is_active"] = True
        
        created = await db.create_source(source_data)
        return created
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create source: {str(e)}")

@router.get("/{source_id}")
async def get_source(
    source_id: str,
    user = Depends(get_current_user)
):
    """Get a specific source."""
    try:
        source = await db.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        if source.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return source
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get source: {str(e)}")

@router.delete("/{source_id}")
async def delete_source(
    source_id: str,
    user = Depends(get_current_user)
):
    """Delete a source."""
    try:
        source = await db.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        if source.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        success = await db.delete_source(source_id)
        return {"success": success, "source_id": source_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete source: {str(e)}")

@router.post("/{source_id}/refresh")
async def refresh_source(
    source_id: str,
    user = Depends(get_current_user)
):
    """Manually trigger a source refresh."""
    try:
        source = await db.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        if source.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        await queue.enqueue("source_refresh", {
            "source_id": source_id,
            "user_id": user.id,
            "source_type": source.get("type"),
            "url": source.get("url")
        })
        
        return {
            "success": True,
            "source_id": source_id,
            "message": "Refresh queued"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh source: {str(e)}")
