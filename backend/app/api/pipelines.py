from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

from app.models import (
    Pipeline, PipelineCreate, PipelineUpdate, PipelineStatus
)
from app.services.auth import get_current_user, get_user_db
from app.services.database import SupabaseService

router = APIRouter(prefix="/pipelines", tags=["pipelines"])

@router.get("")
async def list_pipelines(
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """List all pipelines for the current user."""
    try:
        pipelines = await db.list_pipelines(user.id)
        return {"items": pipelines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list pipelines: {str(e)}")

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    pipeline: PipelineCreate,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Create a new content pipeline."""
    try:
        pipeline_data = pipeline.model_dump()
        pipeline_data["user_id"] = user.id
        pipeline_data["status"] = "setup-incomplete"
        pipeline_data["total_clips_generated"] = 0
        pipeline_data["total_views"] = 0
        pipeline_data["total_revenue"] = 0
        pipeline_data["error_count"] = 0
        
        created = await db.create_pipeline(pipeline_data)
        return created
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create pipeline: {str(e)}")

@router.get("/{pipeline_id}")
async def get_pipeline(
    pipeline_id: str,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Get pipeline details."""
    try:
        pipeline = await db.get_pipeline(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        # Verify ownership
        if pipeline.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return pipeline
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pipeline: {str(e)}")

@router.patch("/{pipeline_id}")
async def update_pipeline(
    pipeline_id: str,
    update: PipelineUpdate,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Update pipeline settings."""
    try:
        # Verify ownership
        pipeline = await db.get_pipeline(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        if pipeline.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        updated = await db.update_pipeline(pipeline_id, update.model_dump(exclude_unset=True))
        return updated
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update pipeline: {str(e)}")

@router.post("/{pipeline_id}/toggle")
async def toggle_pipeline(
    pipeline_id: str,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Toggle pipeline between running and paused."""
    try:
        pipeline = await db.get_pipeline(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        if pipeline.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        current_status = pipeline.get("status", "paused")
        new_status = "active" if current_status != "active" else "paused"
        
        updated = await db.update_pipeline(pipeline_id, {"status": new_status})
        return {"success": True, "pipeline_id": pipeline_id, "status": new_status, "data": updated}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle pipeline: {str(e)}")

@router.delete("/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: str,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Delete a pipeline."""
    try:
        pipeline = await db.get_pipeline(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        if pipeline.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        success = await db.delete_pipeline(pipeline_id)
        return {"success": success, "pipeline_id": pipeline_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete pipeline: {str(e)}")

@router.get("/{pipeline_id}/metrics")
async def get_pipeline_metrics(
    pipeline_id: str,
    days: int = 7,
    user = Depends(get_current_user)
):
    """Get pipeline performance metrics."""
    try:
        return {
            "pipeline_id": pipeline_id,
            "clips_generated": 0,
            "clips_posted": 0,
            "total_views": 0,
            "period_days": days
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")
