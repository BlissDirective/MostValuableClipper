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
    SwarmTier, SwarmJobStatus,
    SwarmBatchJob, SwarmBatchJobStatus, SwarmBatchClipResult
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

# ─────────────────────────────────────────────────────────────
# Batch Request / Response Models
# ─────────────────────────────────────────────────────────────

class SwarmBatchRequest(BaseModel):
    """Request to execute a swarm on multiple clips in batch.
    
    Batch processing shares source analysis context across clips
    to minimize redundant API calls and reduce costs.
    """
    clip_ids: List[str] = Field(..., min_length=1, max_length=100, description="Clips to process (max 100)")
    pool_type: str = Field(..., description="Swarm pool type: hook, remix, post, ab_test, music_match, thumbnail, safety, hooks_analysis, segment_analyze, edit")
    agent_count: Optional[int] = Field(None, ge=1, le=50, description="Agents per clip. Uses user's allocation if not provided.")
    strategy_filter: Optional[List[str]] = None
    priority: str = Field("balanced", description="Processing priority: cost | balanced | speed")
    top_k: Optional[int] = Field(None, ge=1, le=100, description="Only process top N clips (smart selection)")
    shared_context: bool = True
    custom_options: Optional[Dict[str, Any]] = None

class SwarmBatchClipResultResponse(BaseModel):
    """Result for a single clip in a batch."""
    clip_id: str
    status: str
    result_data: Optional[Dict[str, Any]] = None
    cost_cents: int = 0
    duration_ms: int = 0
    error_message: Optional[str] = None

class SwarmBatchResponse(BaseModel):
    """Response from a batch swarm execution."""
    batch_id: str
    pool_type: str
    total_clips: int
    processed_clips: int
    failed_clips: int
    status: str
    results: List[SwarmBatchClipResultResponse]
    cost_cents: int
    estimated_cost_usd: float
    savings_percent: float
    duration_ms: int
    created_at: str
    completed_at: Optional[str] = None

class SwarmBatchJobListResponse(BaseModel):
    """List of batch jobs for a user."""
    jobs: List[Dict[str, Any]]
    total: int

class SwarmBatchJobDetailResponse(BaseModel):
    """Detailed view of a batch job with per-clip results."""
    job: Dict[str, Any]
    clip_results: List[Dict[str, Any]]


# ─────────────────────────────────────────────────────────────
# Config Update / Allocation Models
# ─────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────
# Batch Execution Endpoints
# ─────────────────────────────────────────────────────────────

@router.post("/batch", response_model=SwarmBatchResponse)
async def execute_batch_swarm(
    request: SwarmBatchRequest,
    user=Depends(get_current_user)
):
    """Queue a swarm batch job for async background processing.
    
    Creates a batch job and enqueues it to the Redis queue.
    Returns immediately with a batch_id for polling progress.
    
    The batch will be processed by a background worker with:
    - Shared source analysis across clips (cost savings)
    - Real-time progress updates via Supabase realtime
    - Partial results streaming as clips complete
    
    Priority modes:
    - **cost**: Sequential processing, shared context, minimal agents
    - **balanced**: Smart selection — analyze all, deep-dive on top performers
    - **speed**: Max parallel, process all simultaneously
    """
    # Validate clip_ids exist and belong to user
    if len(request.clip_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 clips per batch"
        )
    
    # Determine processing strategy based on priority
    priority = request.priority.lower()
    if priority not in ("cost", "balanced", "speed"):
        priority = "balanced"
    
    # Enqueue batch for async processing
    from app.services.swarm_batch_service import SwarmBatchService
    
    batch_service = SwarmBatchService(swarm_orchestrator)
    
    result = await batch_service.enqueue_batch(
        clip_ids=request.clip_ids,
        pool_type=request.pool_type,
        user_id=user.id,
        agent_count=request.agent_count,
        strategy_filter=request.strategy_filter,
        priority=priority,
        top_k=request.top_k,
        shared_context=request.shared_context,
        custom_options=request.custom_options or {},
    )
    
    if "error" in result and not result.get("batch_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return SwarmBatchResponse(**result)


@router.get("/batch", response_model=SwarmBatchJobListResponse)
async def list_batch_jobs(
    limit: int = 50,
    offset: int = 0,
    user=Depends(get_current_user)
):
    """List batch swarm jobs for the current user."""
    from app.services.swarm_batch_service import SwarmBatchService
    
    batch_service = SwarmBatchService(swarm_orchestrator)
    jobs = await batch_service.list_batch_jobs(user.id, limit=limit, offset=offset)
    
    return SwarmBatchJobListResponse(
        jobs=jobs,
        total=len(jobs)
    )


@router.get("/batch/{batch_id}", response_model=SwarmBatchJobDetailResponse)
async def get_batch_job(
    batch_id: str,
    user=Depends(get_current_user)
):
    """Get details of a specific batch job including per-clip results."""
    from app.services.swarm_batch_service import SwarmBatchService
    
    batch_service = SwarmBatchService(swarm_orchestrator)
    job = await batch_service.get_batch_job(batch_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch job not found"
        )
    
    if job["user_id"] != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this batch job"
        )
    
    clip_results = await batch_service.get_batch_clip_results(batch_id)
    
    return SwarmBatchJobDetailResponse(
        job=job,
        clip_results=clip_results
    )


@router.delete("/batch/{batch_id}")
async def cancel_batch_job(
    batch_id: str,
    user=Depends(get_current_user)
):
    """Cancel a running batch job."""
    from app.services.swarm_batch_service import SwarmBatchService
    
    batch_service = SwarmBatchService(swarm_orchestrator)
    job = await batch_service.get_batch_job(batch_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch job not found"
        )
    
    if job["user_id"] != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this batch job"
        )
    
    success = await batch_service.cancel_batch_job(batch_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not cancel batch job — it may already be completed or failed"
        )
    
    return {"success": True, "batch_id": batch_id, "status": "cancelled"}


@router.post("/batch/{batch_id}/estimate-cost")
async def estimate_batch_cost(
    batch_id: str,
    user=Depends(get_current_user)
):
    """Get cost estimate for a batch before execution.
    
    Returns per-clip and total cost breakdown with savings vs individual execution.
    """
    from app.services.swarm_batch_service import SwarmBatchService
    
    batch_service = SwarmBatchService(swarm_orchestrator)
    job = await batch_service.get_batch_job(batch_id)
    
    if not job or job["user_id"] != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch job not found"
        )
    
    return await batch_service.estimate_batch_cost(batch_id)


# ─────────────────────────────────────────────────────────────
# Batch Templates
# ─────────────────────────────────────────────────────────────

class TemplateCreateRequest(BaseModel):
    name: str
    pool_type: str
    agent_count: Optional[int] = None
    strategy_filter: Optional[List[str]] = None
    priority: str = "balanced"
    shared_context: bool = True
    custom_options: Optional[Dict[str, Any]] = None
    is_default: bool = False

@router.post("/batch/templates")
async def create_batch_template(
    request: TemplateCreateRequest,
    user=Depends(get_current_user)
):
    """Create a saved batch configuration template."""
    from app.services.swarm_batch_service import SwarmBatchService
    
    service = SwarmBatchService()
    result = await service.create_template(
        user_id=str(user.id),
        name=request.name,
        pool_type=request.pool_type,
        agent_count=request.agent_count,
        strategy_filter=request.strategy_filter,
        priority=request.priority,
        shared_context=request.shared_context,
        custom_options=request.custom_options,
        is_default=request.is_default,
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/batch/templates")
async def list_batch_templates(
    user=Depends(get_current_user)
):
    """List all batch templates for the current user."""
    from app.services.swarm_batch_service import SwarmBatchService
    
    service = SwarmBatchService()
    return await service.list_templates(str(user.id))

@router.delete("/batch/templates/{template_id}")
async def delete_batch_template(
    template_id: str,
    user=Depends(get_current_user)
):
    """Delete a batch template."""
    from app.services.swarm_batch_service import SwarmBatchService
    
    service = SwarmBatchService()
    success = await service.delete_template(template_id, str(user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"success": True}


# ─────────────────────────────────────────────────────────────
# Batch Queue Depth & ETA
# ─────────────────────────────────────────────────────────────

@router.get("/batch/queue-depth")
async def get_batch_queue_depth(
    user=Depends(get_current_user)
):
    """Get current batch queue depth and estimated wait time."""
    from app.services.queue import QueueService
    
    queue = QueueService()
    depth = await queue.get_queue_length("swarm_batch")
    
    # Estimate: ~30s per clip with 5 concurrent
    est_seconds = depth * 6  # rough estimate
    
    return {
        "queue_depth": depth,
        "estimated_wait_seconds": est_seconds,
        "estimated_wait_formatted": f"{est_seconds // 60}m {est_seconds % 60}s" if est_seconds > 60 else f"{est_seconds}s",
    }

@router.get("/batch/{batch_id}/eta")
async def get_batch_eta(
    batch_id: str,
    user=Depends(get_current_user)
):
    """Get estimated completion time for a batch job."""
    from app.services.swarm_batch_service import SwarmBatchService
    
    service = SwarmBatchService()
    job = await service.get_batch_job(batch_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found")
    
    if job.get("user_id") != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this batch job")
    
    if job.get("status") in ("completed", "failed", "cancelled"):
        return {"eta_seconds": 0, "eta_formatted": "Done", "status": job["status"]}
    
    total = job.get("total_clips", 0)
    processed = job.get("processed_clips", 0)
    remaining = total - processed
    
    # Estimate ~15s per clip for balanced, 8s for speed, 25s for cost
    priority = job.get("results_summary", {}).get("priority", "balanced")
    seconds_per_clip = {"speed": 8, "balanced": 15, "cost": 25}.get(priority, 15)
    
    # Adjust for wave overhead
    waves = job.get("results_summary", {}).get("waves", 1)
    eta_seconds = remaining * seconds_per_clip + (waves * 5)
    
    return {
        "eta_seconds": eta_seconds,
        "eta_formatted": f"{eta_seconds // 60}m {eta_seconds % 60}s" if eta_seconds > 60 else f"{eta_seconds}s",
        "remaining_clips": remaining,
        "status": job["status"],
        "current_wave": job.get("results_summary", {}).get("wave", 1),
        "total_waves": waves,
    }
