from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.models import Source, SourceCreate
from app.services.auth import get_current_user

router = APIRouter(prefix="/sources", tags=["sources"])

@router.get("")
async def list_sources(
    user = Depends(get_current_user)
):
    """List all video sources."""
    # TODO: Implement
    return {"items": []}

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_source(
    source: SourceCreate,
    user = Depends(get_current_user)
):
    """Register a new video source."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{source_id}")
async def get_source(
    source_id: str,
    user = Depends(get_current_user)
):
    """Get source details."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")

@router.delete("/{source_id}")
async def delete_source(
    source_id: str,
    user = Depends(get_current_user)
):
    """Delete a source."""
    # TODO: Implement
    return {"success": True}

@router.post("/{source_id}/process")
async def process_source(
    source_id: str,
    user = Depends(get_current_user)
):
    """Trigger processing of a source video."""
    # TODO: Implement - queue for processing
    return {"success": True, "source_id": source_id, "status": "queued"}
