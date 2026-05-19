from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ClipStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    rendered = "rendered"
    approved = "approved"
    scheduled = "scheduled"
    posted = "posted"
    failed = "failed"
    flagged = "flagged"

class Platform(str, Enum):
    tiktok = "tiktok"
    instagram = "instagram"
    youtube = "youtube"
    facebook = "facebook"
    twitter = "twitter"

class PlatformPost(BaseModel):
    platform: Platform
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = []
    scheduled_time: Optional[datetime] = None
    clip_id: str

class Clip(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    pipeline_id: str
    user_id: str
    status: ClipStatus
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    platform_posts: Optional[List[PlatformPost]] = []
    created_at: datetime
    updated_at: datetime

class ClipCreate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    pipeline_id: str
    source_video_url: Optional[str] = None

class ClipUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ClipStatus] = None
    platform_posts: Optional[List[PlatformPost]] = []

class PipelineStatus(str, Enum):
    active = "active"
    paused = "paused"
    draft = "draft"
    archived = "archived"

class Pipeline(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    user_id: str
    status: PipelineStatus
    source_ids: Optional[List[str]] = []
    settings: Optional[Dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime

class PipelineCreate(BaseModel):
    name: str
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = {}

class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[PipelineStatus] = None
    settings: Optional[Dict[str, Any]] = None

class SourceType(str, Enum):
    upload = "upload"
    url = "url"
    youtube = "youtube"
    tiktok = "tiktok"
    instagram = "instagram"

class Source(BaseModel):
    id: str
    name: str
    url: Optional[str] = None
    type: SourceType
    pipeline_id: str
    user_id: str
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime

class SourceCreate(BaseModel):
    name: str
    url: Optional[str] = None
    type: SourceType
    pipeline_id: str
    metadata: Optional[Dict[str, Any]] = {}

class Earnings(BaseModel):
    id: str
    user_id: str
    clip_id: str
    platform: Platform
    amount: float
    currency: str = "USD"
    status: str = "pending"
    transaction_id: Optional[str] = None
    created_at: datetime

class SwarmTier(str, Enum):
    free = "free"
    basic = "basic"
    pro = "pro"
    enterprise = "enterprise"

class SwarmConfig(BaseModel):
    """User's swarm configuration with customizable agent allocation."""
    user_id: str
    tier: SwarmTier = SwarmTier.free
    
    # Custom agent allocation across swarm types
    # Keys: "hook", "remix", "post"
    # Values: number of agents allocated to each type
    agent_allocation: Dict[str, int] = Field(
        default_factory=lambda: {"hook": 1, "remix": 1, "post": 1},
        description="Custom agent allocation per swarm type"
    )
    
    # Auto-balance mode: when true, automatically distributes agents evenly
    # When false, uses custom agent_allocation
    auto_balance: bool = Field(default=True, description="Auto-distribute agents evenly")
    
    # Maximum total agents allowed (derived from tier, but can be overridden in enterprise)
    total_max_agents: int = Field(1, ge=1, le=50, description="Total agent limit")
    
    # Which swarm pools are enabled for this user
    enabled_pools: List[str] = Field(default_factory=lambda: ["hook", "remix", "post"])
    
    # Daily budget for swarm operations (cents)
    daily_budget_cents: int = Field(0, ge=0, description="Daily budget in cents. 0 = unlimited")
    
    # Agent behavior preferences
    agent_behavior: Dict[str, Any] = Field(
        default_factory=lambda: {
            "hook": {"personas": ["punchy", "aspirational", "controversial"]},
            "remix": {"strategies": ["energy_max", "face_presence", "hook_quality"]},
            "post": {"parallel_accounts": True, "stagger_posts": False}
        },
        description="Agent behavior configuration per pool type"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def allocated_total(self) -> int:
        """Total agents currently allocated."""
        return sum(self.agent_allocation.values())
    
    @property
    def available_agents(self) -> int:
        """Remaining agents available for allocation."""
        return self.total_max_agents - self.allocated_total
    
    def get_pool_agents(self, pool_type: str) -> int:
        """Get number of agents allocated to a specific pool."""
        if pool_type not in self.enabled_pools:
            return 0
        return self.agent_allocation.get(pool_type, 0)
    
    def validate_allocation(self) -> tuple[bool, str]:
        """Validate that current allocation is valid.
        
        Returns:
            (is_valid, error_message)
        """
        total = self.allocated_total
        
        if total > self.total_max_agents:
            return False, f"Total allocation ({total}) exceeds tier limit ({self.total_max_agents})"
        
        if total == 0:
            return False, "Must allocate at least 1 agent"
        
        for pool, count in self.agent_allocation.items():
            if count < 0:
                return False, f"Agent count for {pool} cannot be negative"
            if pool not in self.enabled_pools and count > 0:
                return False, f"Cannot allocate agents to disabled pool: {pool}"
        
        return True, "Valid"
    
    def auto_balance_allocation(self) -> None:
        """Automatically balance agent allocation across enabled pools."""
        enabled = [p for p in self.enabled_pools if p in [
            "hook", "remix", "post", "ab_test", "music_match",
            "thumbnail", "safety", "hooks_analysis", "segment_analyze", "edit"
        ]]
        n_pools = len(enabled)
        
        if n_pools == 0:
            self.agent_allocation = {}
            return
        
        base = self.total_max_agents // n_pools
        remainder = self.total_max_agents % n_pools
        
        allocation = {}
        for i, pool in enumerate(enabled):
            allocation[pool] = base + (1 if i < remainder else 0)
        
        self.agent_allocation = allocation

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
    partial = "partial"

class SwarmJob(BaseModel):
    """A swarm execution job tracking parallel agent execution."""
    job_id: str
    user_id: str
    job_type: SwarmJobType
    status: SwarmJobStatus = SwarmJobStatus.queued
    total_agents: int = 0
    completed_agents: int = 0
    failed_agents: int = 0
    results_summary: Optional[Dict[str, Any]] = None
    cost_cents: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class SwarmAgentResult(BaseModel):
    """Result from one agent in a swarm execution."""
    result_id: str
    job_id: str
    agent_index: int
    agent_persona: str
    status: str = "pending"  # pending, completed, failed
    result_data: Optional[Dict[str, Any]] = None
    cost_cents: int = 0
    duration_ms: int = 0
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)



class EarningsSummary(BaseModel):
    total_earnings: float = 0
    pending_earnings: float = 0
    paid_earnings: float = 0
    total_clips_monetized: int = 0
    by_platform: Dict[str, float] = {}



# ============================================
# CLIP REMIX MODELS
# ============================================
class RemixRequest(BaseModel):
    """Request to AI-remix an existing clip."""
    num_variants: Optional[int] = Field(3, ge=1, le=5, description="Number of remix variants to generate")
    target_duration: Optional[int] = Field(20, ge=10, le=60, description="Target duration in seconds")
    preferred_hook_archetype: Optional[str] = None  # "question", "promise", "pattern_break", etc.
    include_music: Optional[bool] = True
    include_captions: Optional[bool] = True
    output_format: Optional[str] = "9:16"  # "9:16", "1:1", "16:9"

class RemixVariantResponse(BaseModel):
    """A single remix variant result."""
    variant_id: str
    clip_id: str
    video_url: str
    thumbnail_url: Optional[str] = None
    caption: str
    hashtags: List[str]
    hook_archetype: str
    hook_text: str
    segment: Dict[str, Any]  # {"start": 0, "end": 25, "duration": 25, "score": 0.85}
    duration: float
    music_mood: str
    estimated_retention: float

class RemixResponse(BaseModel):
    """Response from AI remix generation."""
    success: bool
    original_clip_id: str
    variants: List[RemixVariantResponse]
    total_variants: int
    error: Optional[str] = None

class RemixJob(BaseModel):
    """Queued remix job status."""
    job_id: str
    clip_id: str
    user_id: str
    status: str  # "queued", "processing", "completed", "failed"
    num_variants: int
    result: Optional[RemixResponse] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None

class ClipRevision(BaseModel):
    """Revision history entry for a clip (edit or remix)."""
    id: str
    clip_id: str
    user_id: str
    revision_type: str  # "edit", "remix", "manual"
    previous_state: Dict[str, Any]
    new_state: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = {}
    created_at: str

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
