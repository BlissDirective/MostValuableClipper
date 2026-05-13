from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# ============================================
# ENUMS
# ============================================
class AutonomyMode(str, Enum):
    FULL_AUTO = "fullAuto"
    APPROVE_EACH = "approveEach"
    SUGGEST_ONLY = "suggestOnly"

class PipelineStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    ERRORED = "errored"
    SETUP_INCOMPLETE = "setup-incomplete"

class ClipStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    GENERATING = "generating"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    POSTED = "posted"
    REJECTED = "rejected"
    FAILED = "failed"

class Platform(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    FACEBOOK = "facebook"

class SubscriptionTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class RetentionPolicy(str, Enum):
    AGGRESSIVE = "aggressive"
    MODERATE = "moderate"
    INDEFINITE = "indefinite"

# ============================================
# BASE MODELS
# ============================================
class TimestampModel(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    autonomy_mode: AutonomyMode = AutonomyMode.APPROVE_EACH
    cohort_opt_in: bool = False
    onboarding_completed: bool = False

class UserCreate(UserBase):
    pass

class User(UserBase, TimestampModel):
    id: str
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None

    class Config:
        from_attributes = True

# ============================================
# CLIP MODELS
# ============================================
class ClipBase(BaseModel):
    caption: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = []
    status: ClipStatus = ClipStatus.PENDING

class ClipCreate(ClipBase):
    pipeline_id: Optional[str] = None
    source_id: Optional[str] = None

class ClipUpdate(BaseModel):
    caption: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[ClipStatus] = None

class PlatformPost(BaseModel):
    platform: Platform
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    status: str = "pending"
    metrics: Dict[str, Any] = {}

class Clip(ClipBase, TimestampModel):
    id: str
    user_id: str
    pipeline_id: Optional[str] = None
    source_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    video_duration: Optional[int] = None
    platform_posts: Dict[str, PlatformPost] = {}
    safety_flags: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {}
    posted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ============================================
# PIPELINE MODELS
# ============================================
class PostSchedule(BaseModel):
    weekdays: List[int] = [1, 2, 3, 4, 5]
    times: List[str] = ["09:00", "15:00", "19:00"]

class PipelineBase(BaseModel):
    name: str
    theme: str
    niche: Optional[str] = None
    status: PipelineStatus = PipelineStatus.SETUP_INCOMPLETE
    retention_policy: RetentionPolicy = RetentionPolicy.MODERATE
    min_clip_length_seconds: int = 15
    max_clip_length_seconds: int = 90
    post_schedule: PostSchedule = PostSchedule()
    target_platforms: List[Platform] = []

class PipelineCreate(PipelineBase):
    pass

class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    theme: Optional[str] = None
    niche: Optional[str] = None
    status: Optional[PipelineStatus] = None
    retention_policy: Optional[RetentionPolicy] = None
    min_clip_length_seconds: Optional[int] = None
    max_clip_length_seconds: Optional[int] = None
    post_schedule: Optional[PostSchedule] = None
    target_platforms: Optional[List[Platform]] = None

class Pipeline(PipelineBase, TimestampModel):
    id: str
    user_id: str
    clips_count: Optional[int] = None
    views_delta: Optional[str] = None

    class Config:
        from_attributes = True

# ============================================
# SOURCE MODELS
# ============================================
class SourceBase(BaseModel):
    title: str
    description: Optional[str] = None
    original_url: Optional[str] = None
    duration: Optional[int] = None

class SourceCreate(SourceBase):
    pipeline_id: Optional[str] = None

class Source(SourceBase, TimestampModel):
    id: str
    user_id: str
    pipeline_id: Optional[str] = None
    storage_path: Optional[str] = None
    status: str = "processing"
    metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True

# ============================================
# EARNINGS MODELS
# ============================================
class EarningsBase(BaseModel):
    platform: Platform
    period_start: str  # ISO date
    period_end: str
    revenue_cents: int = 0
    currency: str = "USD"
    views: int = 0
    breakdown: Dict[str, Any] = {}

class EarningsCreate(EarningsBase):
    pass

class Earnings(EarningsBase, TimestampModel):
    id: str
    user_id: str

    class Config:
        from_attributes = True

class EarningsSummary(BaseModel):
    total_revenue_cents: int
    total_views: int
    by_platform: Dict[str, Dict[str, Any]]
    period_start: str
    period_end: str

# ============================================
# ONBOARDING MODELS
# ============================================
class OnboardingStep(BaseModel):
    step: str
    completed: bool
    data: Optional[Dict[str, Any]] = None

class OnboardingState(BaseModel):
    current_step: str
    steps: List[OnboardingStep]
    completed: bool

# ============================================
# ANALYTICS MODELS
# ============================================
class AnalyticsEvent(BaseModel):
    event_type: str
    event_data: Dict[str, Any] = {}
    created_at: Optional[datetime] = None

# ============================================
# WEBHOOK MODELS
# ============================================
class StripeWebhookPayload(BaseModel):
    id: str
    object: str
    type: str
    data: Dict[str, Any]
