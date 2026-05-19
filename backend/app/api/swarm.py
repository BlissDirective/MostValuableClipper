"""Swarm API endpoints for customizable parallel agent execution.

Provides endpoints for hook generation, remix, and posting swarms
with customizable agent allocation per pool type.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.services.auth import get_current_user
from app.services.swarm_orchestrator import SwarmOrchestrator, swarm_orchestrator
from app.services.swarm_config_service import SwarmConfigService, SwarmJobService
from app.models import (
    SwarmConfig, SwarmJob, SwarmAgentResult,
    SwarmTier, SwarmJobStatus
)

router = APIRouter(prefix="/swarm", tags=["swarm"])


# ─────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────

class SwarmHookRequest(BaseModel):
    clip_id: str
    platform: str = "tiktok"
    # Optional override; if not provided, uses user's custom allocation
    agent_count: Optional[int] = Field(None, ge=1, le=50)
    persona_filter: Optional[List[str]] = None

class SwarmRemixRequest(BaseModel):
    clip_id: str
    # Optional override; if not provided, uses user's custom allocation
    agent_count: Optional[int] = Field(None, ge=1, le=50)
    strategy_filter: Optional[List[str]] = None

class SwarmPostAccount(BaseModel):
    account_id: str
    platform: str

class SwarmPostRequest(BaseModel):
    clip_id: str
    accounts: List[SwarmPostAccount]
    hooks: Optional[List[Dict[str, Any]]] = None
    # Optional override; if not provided, uses user's custom allocation
    agent_count: Optional[int] = Field(None, ge=1, le=50)

class SwarmABTestRequest(BaseModel):
    test_id: str
    clip_id: str
    agent_count: Optional[int] = Field(None, ge=1, le=50)
    strategy_filter: Optional[List[str]] = None

class SwarmMusicMatchRequest(BaseModel):
    clip_id: str
    agent_count: Optional[int] = Field(None, ge=1, le=50)
    strategy_filter: Optional[List[str]] = None
    segment_data: Optional[Dict[str, Any]] = None

class SwarmThumbnailRequest(BaseModel):
    clip_id: str
    agent_count: Optional[int] = Field(None, ge=1, le=50)
    style_filter: Optional[List[str]] = None

class SwarmSafetyRequest(BaseModel):
    clip_id: str
    agent_count: Optional[int] = Field(None, ge=1, le=50)
    sensitivity_filter: Optional[List[str]] = None

class SwarmHooksAnalysisRequest(BaseModel):
    clip_id: str
    platform: str = "tiktok"
    agent_count: Optional[int] = Field(None, ge=1, le=50)
    method_filter: Optional[List[str]] = None

class SwarmSegmentAnalyzeRequest(BaseModel):
    clip_id: str
    agent_count: Optional[int] = Field(None, ge=1, le=50)
    strategy_filter: Optional[List[str]] = None

class SwarmEditRequest(BaseModel):
    clip_id: str
    agent_count: Optional[int] = Field(None, ge=1, le=50)
    recipe_filter: Optional[List[str]] = None

class SwarmConfigUpdateRequest(BaseModel):
    enabled_pools: Optional[List[str]] = None
    daily_budget_cents: Optional[int] = Field(None, ge=0)
    auto_balance: Optional[bool] = None
    agent_behavior: Optional[Dict[str, Any]] = None

class SwarmAllocationRequest(BaseModel):
    """Request to set custom agent allocation.
    
    Example: {"hook": 2, "remix": 3, "post": 0}
    Total must not exceed tier limit.
    """
    allocation: Dict[str, int] = Field(
        ..., description="Agent count per pool type"
    )

class SwarmAllocationResponse(BaseModel):
    """Current agent allocation with validation info."""
    user_id: str
    tier: str
    total_max_agents: int
    auto_balance: bool
    allocation: Dict[str, int]
    allocated_total: int
    available_agents: int
    enabled_pools: List[str]
    is_valid: bool
    message: str

class SwarmHookResponse(BaseModel):
    job_id: str
    agents: int
    results: List[Dict[str, Any]]
    best_hook: Optional[Dict[str, Any]] = None
    total_cost_cents: int
    duration_ms: int

class SwarmRemixResponse(BaseModel):
    job_id: str
    agents: int
    variants: List[Dict[str, Any]]
    best_variant: Optional[Dict[str, Any]] = None
    total_cost_cents: int
    duration_ms: int

class SwarmPostResponse(BaseModel):
    job_id: str
    agents: int
    posts: List[Dict[str, Any]]
    summary: Dict[str, Any]
    total_cost_cents: int
    duration_ms: int

class SwarmABTestResponse(BaseModel):
    job_id: str
    agents: int
    results: List[Dict[str, Any]]
    best_result: Optional[Dict[str, Any]] = None
    total_cost_cents: int
    duration_ms: int

class SwarmMusicMatchResponse(BaseModel):
    job_id: str
    agents: int
    results: List[Dict[str, Any]]
    best_result: Optional[Dict[str, Any]] = None
    total_cost_cents: int
    duration_ms: int

class SwarmThumbnailResponse(BaseModel):
    job_id: str
    agents: int
    results: List[Dict[str, Any]]
    total_cost_cents: int
    duration_ms: int

class SwarmSafetyResponse(BaseModel):
    job_id: str
    agents: int
    results: List[Dict[str, Any]]
    consensus: Dict[str, Any]
    total_cost_cents: int
    duration_ms: int

class SwarmHooksAnalysisResponse(BaseModel):
    job_id: str
    agents: int
    results: List[Dict[str, Any]]
    total_cost_cents: int
    duration_ms: int

class SwarmSegmentAnalyzeResponse(BaseModel):
    job_id: str
    agents: int
    results: List[Dict[str, Any]]
    best_result: Optional[Dict[str, Any]] = None
    total_cost_cents: int
    duration_ms: int

class SwarmEditResponse(BaseModel):
    job_id: str
    agents: int
    results: List[Dict[str, Any]]
    total_cost_cents: int
    duration_ms: int

class SwarmConfigResponse(BaseModel):
    user_id: str
    tier: str
    total_max_agents: int
    auto_balance: bool
    allocation: Dict[str, int]
    allocated_total: int
    available_agents: int
    enabled_pools: List[str]
    daily_budget_cents: int
    agent_behavior: Dict[str, Any]

class SwarmJobListResponse(BaseModel):
    jobs: List[SwarmJob]
    total: int

class SwarmJobDetailResponse(BaseModel):
    job: SwarmJob
    agent_results: List[SwarmAgentResult]


# ─────────────────────────────────────────────────────────────
# Allocation Endpoints
# ─────────────────────────────────────────────────────────────

@router.post("/allocation", response_model=SwarmAllocationResponse)
async def set_agent_allocation(
    request: SwarmAllocationRequest,
    user=Depends(get_current_user)
):
    """Set custom agent allocation across swarm types.
    
    The total must not exceed the user's tier limit:
    - Free: 1 total agent
    - Basic: 2 total agents
    - Pro: 5 total agents
    - Enterprise: 10 total agents
    
    Setting custom allocation disables auto-balance mode.
    """
    config, message = await SwarmConfigService.update_allocation(
        user_id=user.id,
        allocation=request.allocation
    )
    
    is_valid = message == "Allocation updated"
    
    return SwarmAllocationResponse(
        user_id=config.user_id,
        tier=config.tier.value,
        total_max_agents=config.total_max_agents,
        auto_balance=config.auto_balance,
        allocation=config.agent_allocation,
        allocated_total=config.allocated_total,
        available_agents=config.available_agents,
        enabled_pools=config.enabled_pools,
        is_valid=is_valid,
        message=message,
    )


@router.get("/allocation", response_model=SwarmAllocationResponse)
async def get_agent_allocation(
    user=Depends(get_current_user)
):
    """Get current agent allocation and available agents."""
    config = await SwarmConfigService.get_config(user.id)
    if not config:
        config = await SwarmConfigService.create_default_config(user.id)
    
    is_valid, error = config.validate_allocation()
    
    return SwarmAllocationResponse(
        user_id=config.user_id,
        tier=config.tier.value,
        total_max_agents=config.total_max_agents,
        auto_balance=config.auto_balance,
        allocation=config.agent_allocation,
        allocated_total=config.allocated_total,
        available_agents=config.available_agents,
        enabled_pools=config.enabled_pools,
        is_valid=is_valid,
        message=error if not is_valid else "Valid allocation",
    )


@router.post("/allocation/auto-balance", response_model=SwarmAllocationResponse)
async def auto_balance_allocation(
    user=Depends(get_current_user)
):
    """Enable auto-balance mode, which evenly distributes agents across enabled pools."""
    config = await SwarmConfigService.get_config(user.id)
    if not config:
        config = await SwarmConfigService.create_default_config(user.id)
    
    config.auto_balance = True
    config.auto_balance_allocation()
    config.updated_at = __import__("datetime").datetime.utcnow()
    
    try:
        supabase = __import__("app.services.database", fromlist=["supabase"]).supabase
        supabase.table("swarm_configs").upsert(config.model_dump(mode="json")).execute()
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.warning(f"[SwarmConfig] Failed to auto-balance: {e}")
    
    return SwarmAllocationResponse(
        user_id=config.user_id,
        tier=config.tier.value,
        total_max_agents=config.total_max_agents,
        auto_balance=config.auto_balance,
        allocation=config.agent_allocation,
        allocated_total=config.allocated_total,
        available_agents=config.available_agents,
        enabled_pools=config.enabled_pools,
        is_valid=True,
        message="Auto-balance enabled",
    )


# ─────────────────────────────────────────────────────────────
# Swarm Execution Endpoints
# ─────────────────────────────────────────────────────────────

@router.post("/hooks", response_model=SwarmHookResponse)
async def generate_hooks_swarm(
    request: SwarmHookRequest,
    user=Depends(get_current_user)
):
    """Generate hooks in parallel using multiple personas.
    
    Uses the user's custom allocation for hook agents unless overridden.
    """
    result = await swarm_orchestrator.execute_hook_swarm(
        clip_id=request.clip_id,
        user_id=user.id,
        platform=request.platform,
        agent_count=request.agent_count,  # None = use custom allocation
        persona_filter=request.persona_filter
    )

    if "error" in result and not result.get("job_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return SwarmHookResponse(**result)


@router.post("/remix", response_model=SwarmRemixResponse)
async def remix_clip_swarm(
    request: SwarmRemixRequest,
    user=Depends(get_current_user)
):
    """Remix a clip in parallel using different strategies.
    
    Uses the user's custom allocation for remix agents unless overridden.
    """
    result = await swarm_orchestrator.execute_remix_swarm(
        clip_id=request.clip_id,
        user_id=user.id,
        agent_count=request.agent_count,  # None = use custom allocation
        strategy_filter=request.strategy_filter
    )

    if "error" in result and not result.get("job_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return SwarmRemixResponse(**result)


@router.post("/post", response_model=SwarmPostResponse)
async def post_clip_swarm(
    request: SwarmPostRequest,
    user=Depends(get_current_user)
):
    """Post a clip to multiple accounts in parallel.
    
    Uses the user's custom allocation for post agents unless overridden.
    """
    accounts = [{"account_id": a.account_id, "platform": a.platform} for a in request.accounts]

    result = await swarm_orchestrator.execute_post_swarm(
        clip_id=request.clip_id,
        user_id=user.id,
        accounts=accounts,
        hooks=request.hooks,
        agent_count=request.agent_count  # None = use custom allocation
    )

    if "error" in result and not result.get("job_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return SwarmPostResponse(**result)


# ─────────────────────────────────────────────────────────────
# Expanded Swarm Execution Endpoints
# ─────────────────────────────────────────────────────────────

@router.post("/ab-test", response_model=SwarmABTestResponse)
async def ab_test_swarm(
    request: SwarmABTestRequest,
    user=Depends(get_current_user)
):
    """Run A/B test analysis in parallel with different comparison strategies.
    
    Strategies: engagement_winner, retention_winner, composite_winner, views_winner, watch_time_winner
    """
    result = await swarm_orchestrator.execute_ab_test_swarm(
        test_id=request.test_id,
        user_id=user.id,
        clip_id=request.clip_id,
        agent_count=request.agent_count,
        strategy_filter=request.strategy_filter
    )

    if "error" in result and not result.get("job_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return SwarmABTestResponse(**result)


@router.post("/music-match", response_model=SwarmMusicMatchResponse)
async def music_match_swarm(
    request: SwarmMusicMatchRequest,
    user=Depends(get_current_user)
):
    """Match music tracks in parallel with different selection strategies.
    
    Strategies: energy_match, contrast_boost, tempo_sync, mood_amplify, neutral_underscore
    """
    result = await swarm_orchestrator.execute_music_match_swarm(
        clip_id=request.clip_id,
        user_id=user.id,
        agent_count=request.agent_count,
        strategy_filter=request.strategy_filter,
        segment_data=request.segment_data
    )

    if "error" in result and not result.get("job_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return SwarmMusicMatchResponse(**result)


@router.post("/thumbnail", response_model=SwarmThumbnailResponse)
async def thumbnail_swarm(
    request: SwarmThumbnailRequest,
    user=Depends(get_current_user)
):
    """Generate thumbnails in parallel with different style strategies.
    
    Styles: face_focus, text_overlay, action_peak, color_pop, mid_shot
    """
    result = await swarm_orchestrator.execute_thumbnail_swarm(
        clip_id=request.clip_id,
        user_id=user.id,
        agent_count=request.agent_count,
        style_filter=request.style_filter
    )

    if "error" in result and not result.get("job_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return SwarmThumbnailResponse(**result)


@router.post("/safety", response_model=SwarmSafetyResponse)
async def safety_swarm(
    request: SwarmSafetyRequest,
    user=Depends(get_current_user)
):
    """Run safety checks in parallel with different sensitivity levels.
    
    Levels: strict, standard, permissive, brand_safe, kids_safe
    """
    result = await swarm_orchestrator.execute_safety_swarm(
        clip_id=request.clip_id,
        user_id=user.id,
        agent_count=request.agent_count,
        sensitivity_filter=request.sensitivity_filter
    )

    if "error" in result and not result.get("job_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return SwarmSafetyResponse(**result)


@router.post("/hooks-analysis", response_model=SwarmHooksAnalysisResponse)
async def hooks_analysis_swarm(
    request: SwarmHooksAnalysisRequest,
    user=Depends(get_current_user)
):
    """Analyze hooks in parallel with different time periods and methods.
    
    Methods: recent_7d, recent_30d, all_time, per_platform, by_archetype
    """
    result = await swarm_orchestrator.execute_hooks_analysis_swarm(
        clip_id=request.clip_id,
        user_id=user.id,
        platform=request.platform,
        agent_count=request.agent_count,
        method_filter=request.method_filter
    )

    if "error" in result and not result.get("job_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return SwarmHooksAnalysisResponse(**result)


@router.post("/segment-analyze", response_model=SwarmSegmentAnalyzeResponse)
async def segment_analyze_swarm(
    request: SwarmSegmentAnalyzeRequest,
    user=Depends(get_current_user)
):
    """Analyze video segments in parallel with different strategies.
    
    Strategies: energy_peak, face_presence, hook_potential, question_moment, silence_break
    """
    result = await swarm_orchestrator.execute_segment_analyze_swarm(
        clip_id=request.clip_id,
        user_id=user.id,
        agent_count=request.agent_count,
        strategy_filter=request.strategy_filter
    )

    if "error" in result and not result.get("job_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return SwarmSegmentAnalyzeResponse(**result)


@router.post("/edit", response_model=SwarmEditResponse)
async def edit_swarm(
    request: SwarmEditRequest,
    user=Depends(get_current_user)
):
    """Apply video edits in parallel with different recipe strategies.
    
    Recipes: fast_cuts, caption_heavy, zoom_pulse, clean_trim, reaction_focus
    """
    result = await swarm_orchestrator.execute_edit_swarm(
        clip_id=request.clip_id,
        user_id=user.id,
        agent_count=request.agent_count,
        recipe_filter=request.recipe_filter
    )

    if "error" in result and not result.get("job_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    return SwarmEditResponse(**result)


# ─────────────────────────────────────────────────────────────
# Config Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/config", response_model=SwarmConfigResponse)
async def get_swarm_config(
    user=Depends(get_current_user)
):
    """Get the current user's swarm configuration with allocation."""
    config = await SwarmConfigService.get_config(user.id)
    if not config:
        config = await SwarmConfigService.create_default_config(user.id)

    return SwarmConfigResponse(
        user_id=config.user_id,
        tier=config.tier.value,
        total_max_agents=config.total_max_agents,
        auto_balance=config.auto_balance,
        allocation=config.agent_allocation,
        allocated_total=config.allocated_total,
        available_agents=config.available_agents,
        enabled_pools=config.enabled_pools,
        daily_budget_cents=config.daily_budget_cents,
        agent_behavior=config.agent_behavior,
    )


@router.patch("/config", response_model=SwarmConfigResponse)
async def update_swarm_config(
    request: SwarmConfigUpdateRequest,
    user=Depends(get_current_user)
):
    """Update swarm configuration (within tier limits).
    
    Use POST /swarm/allocation to set custom agent allocation.
    """
    updates = {}
    if request.enabled_pools is not None:
        updates["enabled_pools"] = request.enabled_pools
    if request.daily_budget_cents is not None:
        updates["daily_budget_cents"] = request.daily_budget_cents
    if request.auto_balance is not None:
        updates["auto_balance"] = request.auto_balance
    if request.agent_behavior is not None:
        updates["agent_behavior"] = request.agent_behavior

    config = await SwarmConfigService.update_config(user.id, updates)

    return SwarmConfigResponse(
        user_id=config.user_id,
        tier=config.tier.value,
        total_max_agents=config.total_max_agents,
        auto_balance=config.auto_balance,
        allocation=config.agent_allocation,
        allocated_total=config.allocated_total,
        available_agents=config.available_agents,
        enabled_pools=config.enabled_pools,
        daily_budget_cents=config.daily_budget_cents,
        agent_behavior=config.agent_behavior,
    )


# ─────────────────────────────────────────────────────────────
# Job History Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/jobs", response_model=SwarmJobListResponse)
async def list_swarm_jobs(
    limit: int = 50,
    offset: int = 0,
    user=Depends(get_current_user)
):
    """List swarm jobs for the current user."""
    jobs = await SwarmJobService.list_jobs(user.id, limit=limit, offset=offset)
    return SwarmJobListResponse(
        jobs=jobs,
        total=len(jobs)  # Simplified — could query count separately
    )


@router.get("/jobs/{job_id}", response_model=SwarmJobDetailResponse)
async def get_swarm_job(
    job_id: str,
    user=Depends(get_current_user)
):
    """Get details of a specific swarm job including agent results."""
    job = await SwarmJobService.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if job.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this job"
        )

    agent_results = await SwarmJobService.get_agent_results(job_id)

    return SwarmJobDetailResponse(
        job=job,
        agent_results=agent_results
    )


# ─────────────────────────────────────────────────────────────
# Cost Estimation Endpoint
# ─────────────────────────────────────────────────────────────

@router.post("/estimate-cost", response_model=Dict[str, Any])
async def estimate_swarm_cost(
    pool_type: str,
    agent_count: Optional[int] = None,
    user=Depends(get_current_user)
):
    """Estimate cost for a swarm execution.
    
    If agent_count is not provided, uses the user's current allocation.
    """
    config = await SwarmConfigService.get_config(user.id)
    if not config:
        config = await SwarmConfigService.create_default_config(user.id)
    
    count = agent_count or config.get_pool_agents(pool_type)
    cost = SwarmConfigService.estimate_cost(pool_type, count)
    
    return {
        "pool_type": pool_type,
        "agent_count": count,
        "estimated_cost_cents": cost,
        "estimated_cost_usd": round(cost / 100, 2),
        "daily_budget_cents": config.daily_budget_cents,
        "within_budget": await SwarmConfigService.check_budget(user.id, pool_type, count),
    }
