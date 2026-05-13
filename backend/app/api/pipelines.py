from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

from app.models import (
    Pipeline, PipelineCreate, PipelineUpdate, PipelineStatus
)
from app.services.auth import get_current_user
from app.services.database import SupabaseService

router = APIRouter(prefix="/pipelines", tags=["pipelines"])

db = SupabaseService()

@router.get("")
async def list_pipelines(
    user = Depends(get_current_user)
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
    user = Depends(get_current_user)
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
    user = Depends(get_current_user)
):
    """Get pipeline details."""
    try:
        # TODO: Add get_pipeline to database service
        raise HTTPException(status_code=404, detail="Pipeline not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pipeline: {str(e)}")

@router.patch("/{pipeline_id}")
async def update_pipeline(
    pipeline_id: str,
    update: PipelineUpdate,
    user = Depends(get_current_user)
):
    """Update pipeline settings."""
    try:
        # TODO: Add update_pipeline to database service
        return {"id": pipeline_id, **update.model_dump(exclude_unset=True)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update pipeline: {str(e)}")

@router.post("/{pipeline_id}/toggle")
async def toggle_pipeline(
    pipeline_id: str,
    user = Depends(get_current_user)
):
    """Toggle pipeline between running and paused."""
    try:
        # TODO: Get current status and toggle
        return {"success": True, "pipeline_id": pipeline_id, "status": "running"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle pipeline: {str(e)}")

@router.delete("/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: str,
    user = Depends(get_current_user)
):
    """Delete a pipeline."""
    try:
        # TODO: Implement delete in database service
        return {"success": True, "pipeline_id": pipeline_id}
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
