from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from app.services.auth import get_current_user
from app.services.database import SupabaseService, supabase
from app.agents.content_agent import content_agent
from app.agents.source_agent import source_agent

router = APIRouter(prefix="/agents", tags=["agents"])
db = SupabaseService()

# ═══════════════════════════════════════════════════════════
#  Content Discovery
# ═══════════════════════════════════════════════════════════

class DiscoveryRequest(BaseModel):
    pipeline_id: str
    max_proposals: Optional[int] = 5

@router.post("/discover")
async def run_discovery(
    req: DiscoveryRequest,
    user = Depends(get_current_user)
):
    """Trigger content discovery for a pipeline."""
    pipeline = await db.get_pipeline(req.pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    if pipeline.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your pipeline")
    
    result = await content_agent.run_content_discovery(
        pipeline_id=req.pipeline_id,
        user_id=user["id"],
        max_proposals=req.max_proposals
    )
    
    return result

@router.get("/discover/{pipeline_id}/status")
async def get_discovery_status(
    pipeline_id: str,
    user = Depends(get_current_user)
):
    """Get latest discovery results for a pipeline."""
    pipeline = await db.get_pipeline(pipeline_id)
    if not pipeline or pipeline.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not found")
    
    # Get pending review clips (proposals)
    result = supabase.table("clips")\
        .select("*")\
        .eq("pipeline_id", pipeline_id)\
        .eq("status", "pending_review")\
        .order("confidence_score", desc=True)\
        .execute()
    
    return {
        "pipeline_id": pipeline_id,
        "pending_proposals": len(result.data or []),
        "proposals": result.data or [],
        "last_discovery_run": pipeline.get("last_discovery_run")
    }

# ═══════════════════════════════════════════════════════════
#  Source Management
# ═══════════════════════════════════════════════════════════

class CreateSourceRequest(BaseModel):
    pipeline_id: str
    source_type: str  # youtube, rss, upload, url
    url: Optional[str] = None
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

@router.post("/sources")
async def create_source(
    req: CreateSourceRequest,
    user = Depends(get_current_user)
):
    """Create a new content source."""
    pipeline = await db.get_pipeline(req.pipeline_id)
    if not pipeline or pipeline.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not your pipeline")
    
    result = await source_agent.create_source(
        user_id=user["id"],
        pipeline_id=req.pipeline_id,
        source_type=req.source_type,
        url=req.url or "",
        name=req.name,
        config=req.config
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result

@router.get("/sources/{pipeline_id}")
async def list_sources(
    pipeline_id: str,
    user = Depends(get_current_user)
):
    """List all sources for a pipeline with health info."""
    pipeline = await db.get_pipeline(pipeline_id)
    if not pipeline or pipeline.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not found")
    
    sources = await source_agent.list_pipeline_sources(pipeline_id)
    return {
        "pipeline_id": pipeline_id,
        "sources": sources,
        "total": len(sources)
    }

@router.post("/sources/{source_id}/refresh")
async def refresh_source(
    source_id: str,
    user = Depends(get_current_user)
):
    """Refresh a source (reset failures, re-check health)."""
    result = await source_agent.update_source(source_id, {
        "status": "active",
        "consecutive_failures": 0,
        "updated_at": "now()"
    })
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail="Source not found")
    
    return {"success": True, "source": result.get("source")}

@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: str,
    user = Depends(get_current_user)
):
    """Remove a source."""
    result = await source_agent.delete_source(source_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    
    return result

@router.get("/sources/{pipeline_id}/health")
async def check_sources_health(
    pipeline_id: str,
    user = Depends(get_current_user)
):
    """Run health check on all pipeline sources."""
    pipeline = await db.get_pipeline(pipeline_id)
    if not pipeline or pipeline.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not found")
    
    result = await source_agent.run_health_check_batch(pipeline_id=pipeline_id)
    return result

# ═══════════════════════════════════════════════════════════
#  Source Discovery
# ═══════════════════════════════════════════════════════════

@router.get("/sources/discover/{topic}")
async def discover_new_sources(
    topic: str,
    platform: str = "youtube",
    max_results: int = 5,
    user = Depends(get_current_user)
):
    """Discover new sources for a topic."""
    sources = await source_agent.discover_sources(topic, platform, max_results)
    return {
        "topic": topic,
        "platform": platform,
        "sources": sources,
        "total": len(sources)
    }

# ═══════════════════════════════════════════════════════════
#  Proposal Management
# ═══════════════════════════════════════════════════════════

class ProposalActionRequest(BaseModel):
    clip_id: str
    action: str  # approve, reject, edit
    edits: Optional[Dict[str, Any]] = None

@router.post("/proposals/action")
async def proposal_action(
    req: ProposalActionRequest,
    user = Depends(get_current_user)
):
    """Approve, reject, or edit a proposal."""
    clip = await db.get_clip(req.clip_id)
    if not clip or clip.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not found")
    
    if clip.get("status") != "pending_review":
        raise HTTPException(status_code=400, detail="Clip is not in pending review status")
    
    if req.action == "approve":
        await db.update_clip(req.clip_id, {
            "status": "approved",
            "approved_at": "now()",
            "updated_at": "now()"
        })
        return {"success": True, "action": "approved", "clip_id": req.clip_id}
    
    elif req.action == "reject":
        await db.update_clip(req.clip_id, {
            "status": "rejected",
            "rejected_at": "now()",
            "updated_at": "now()"
        })
        return {"success": True, "action": "rejected", "clip_id": req.clip_id}
    
    elif req.action == "edit":
        if not req.edits:
            raise HTTPException(status_code=400, detail="No edits provided")
        
        await db.update_clip(req.clip_id, {
            **req.edits,
            "status": "pending_review",
            "updated_at": "now()"
        })
        return {"success": True, "action": "edited", "clip_id": req.clip_id}
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

# ═══════════════════════════════════════════════════════════
#  Agent Status
# ═══════════════════════════════════════════════════════════

@router.get("/status")
async def get_agent_status(user = Depends(get_current_user)):
    """Get overall agent system status."""
    # Count active pipelines
    pipeline_result = supabase.table("pipelines")\
        .select("id, status, last_discovery_run")\
        .eq("user_id", user["id"])\
        .execute()
    
    pipelines = pipeline_result.data or []
    active_pipelines = [p for p in pipelines if p.get("status") == "active"]
    
    # Count pending proposals
    proposals_result = supabase.table("clips")\
        .select("id", count="exact")\
        .eq("user_id", user["id"])\
        .eq("status", "pending_review")\
        .execute()
    
    # Count sources
    sources_result = supabase.table("sources")\
        .select("id, status")\
        .eq("user_id", user["id"])\
        .execute()
    
    sources = sources_result.data or []
    healthy_sources = sum(1 for s in sources if s.get("health_status") == "healthy")
    
    return {
        "pipelines": {
            "total": len(pipelines),
            "active": len(active_pipelines)
        },
        "proposals_pending": proposals_result.count or 0,
        "sources": {
            "total": len(sources),
            "healthy": healthy_sources
        },
        "last_discovery_run": max(
            (p.get("last_discovery_run") for p in active_pipelines if p.get("last_discovery_run")),
            default=None
        )
    }
