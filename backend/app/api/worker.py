import asyncio
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional

from app.services.auth import get_current_user
from app.services.worker import VideoProcessingWorker

router = APIRouter(prefix="/worker", tags=["worker"])

# Global worker instance (managed by FastAPI lifespan)
worker_instance: Optional[VideoProcessingWorker] = None

@router.get("/status")
async def get_worker_status(user = Depends(get_current_user)):
    """Get video processing worker status."""
    try:
        if worker_instance:
            stats = await worker_instance.get_stats()
            return {"success": True, "worker": stats}
        return {"success": True, "worker": {"running": False, "current_job": None, "queue_length": 0}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get worker status: {str(e)}")

@router.post("/start")
async def start_worker(user = Depends(get_current_user)):
    """Start the video processing worker."""
    global worker_instance
    try:
        if worker_instance and worker_instance.running:
            return {"success": True, "message": "Worker already running."}
        
        worker_instance = VideoProcessingWorker()
        asyncio.create_task(worker_instance.run())
        return {"success": True, "message": "Worker started."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start worker: {str(e)}")

@router.post("/stop")
async def stop_worker(user = Depends(get_current_user)):
    """Stop the video processing worker."""
    global worker_instance
    try:
        if worker_instance:
            worker_instance.stop()
            return {"success": True, "message": "Worker stop signal sent."}
        return {"success": True, "message": "Worker not running."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop worker: {str(e)}")
