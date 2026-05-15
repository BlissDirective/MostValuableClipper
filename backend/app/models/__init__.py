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

class EarningsSummary(BaseModel):
    total_earnings: float = 0
    pending_earnings: float = 0
    paid_earnings: float = 0
    total_clips_monetized: int = 0
    by_platform: Dict[str, float] = {}
