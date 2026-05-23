from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# ============================================
# CLIP EDITING MODELS
# ============================================
class ClipEditRequest(BaseModel):
    """Edit recipe for clip modification via FFmpeg."""
    trim: Optional[dict] = None
    segments: Optional[List[dict]] = None
    caption: Optional[str] = None
    caption_style: Optional[dict] = None
    audio: Optional[str] = "keep"
    speed: Optional[float] = 1.0
    filters: Optional[List[str]] = None
    text_overlays: Optional[List[dict]] = None
    transitions: Optional[List[str]] = None
    stickers: Optional[List[dict]] = None

class ClipEditJob(BaseModel):
    """Queued clip edit job status."""
    job_id: str
    clip_id: str
    user_id: str
    status: str
    recipe: ClipEditRequest
    result_url: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None

# ============================================
# SWARM MODELS
# ============================================
class SwarmTier(str, Enum):
    free = "free"
    basic = "basic"
    pro = "pro"
    enterprise = "enterprise"

class SwarmJobType(str, Enum):
    hook = "hook"
    remix = "remix"
    post = "post"
    ab_test = "ab_test"
    music_match = "music_match"
    thumbnail = "thumbnail"
    safety = "safety"
    hooks_analysis = "hooks_analysis"
    segment_analyze = "segment_analyze"
    edit = "edit"

class SwarmJobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"

class SwarmConfig(BaseModel):
    """User swarm configuration with customizable agent allocation."""
    user_id: str
    tier: SwarmTier = SwarmTier.free
    total_max_agents: int = 1
    auto_balance: bool = True
    enabled_pools: List[str] = [
        "hook", "remix", "post", "ab_test", "music_match",
        "thumbnail", "safety", "hooks_analysis", "segment_analyze", "edit"
    ]
    agent_allocation: Dict[str, int] = {}
    daily_budget_cents: int = 0
    agent_behavior: Dict[str, Any] = {}
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def allocated_total(self) -> int:
        return sum(self.agent_allocation.values())

    def validate_allocation(self) -> tuple[bool, str]:
        total = self.allocated_total()
        if total > self.total_max_agents:
            return False, f"Total {total} exceeds limit {self.total_max_agents}"
        return True, ""

    def auto_balance_allocation(self):
        """Distribute agents evenly across enabled pools."""
        pools = self.enabled_pools or []
        if not pools:
            self.agent_allocation = {}
            return
        count = len(pools)
        base = self.total_max_agents // count
        remainder = self.total_max_agents % count
        allocation = {}
        for i, pool in enumerate(pools):
            allocation[pool] = base + (1 if i < remainder else 0)
        self.agent_allocation = allocation

class SwarmJob(BaseModel):
    """A single swarm job execution record."""
    job_id: str
    user_id: str
    job_type: SwarmJobType
    status: SwarmJobStatus = SwarmJobStatus.queued
    clip_id: Optional[str] = None
    pipeline_id: Optional[str] = None
    config: Dict[str, Any] = {}
    result: Optional[Dict[str, Any]] = None
    cost_cents: int = 0
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None

class SwarmAgentResult(BaseModel):
    """Result from a single agent in a swarm execution."""
    result_id: str
    job_id: str
    agent_index: int
    pool_type: str
    status: str = "success"
    output: Optional[Dict[str, Any]] = None
    cost_cents: int = 0
    latency_ms: int = 0
    error: Optional[str] = None
    created_at: Optional[str] = None

class SwarmBatchJobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class SwarmBatchClipResult(BaseModel):
    """Result for a single clip within a batch job."""
    clip_id: str
    status: str = "pending"
    hooks: Optional[List[Dict[str, Any]]] = None
    remix_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    post_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    cost_cents: int = 0

class SwarmBatchJob(BaseModel):
    """A batch swarm job that processes multiple clips."""
    batch_id: str
    user_id: str
    status: SwarmBatchJobStatus = SwarmBatchJobStatus.queued
    clip_ids: List[str] = []
    pools: List[str] = []
    config: Dict[str, Any] = {}
    results: List[SwarmBatchClipResult] = []
    total_cost_cents: int = 0
    total_clips: int = 0
    completed_clips: int = 0
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None

# ============================================
# SOURCE MODELS
# ============================================
class SourceCreate(BaseModel):
    """Request model for creating a new source."""
    name: str
    type: str = "url"
    url: str
    description: Optional[str] = None
    pipeline_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = {}

class Source(BaseModel):
    """A content source (YouTube channel, RSS feed, etc.)."""
    id: str
    user_id: str
    name: str
    type: str
    url: str
    description: Optional[str] = None
    config: Dict[str, Any] = {}
    health_status: str = "unknown"
    last_checked_at: Optional[str] = None
    last_fetched_at: Optional[str] = None
    fetch_count: int = 0
    error_count: int = 0
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ClipProposal(BaseModel):
    """A proposed clip from content discovery."""
    proposal_id: str
    user_id: str
    source_id: str
    source_type: str
    title: str
    description: Optional[str] = None
    original_url: str
    predicted_reach: int = 0
    predicted_retention: float = 0.0
    confidence_score: float = 0.0
    duration_seconds: Optional[float] = None
    transcript_preview: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: str = "pending"
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
