

# ============================================
# CLIP EDITING MODELS
# ============================================
class ClipEditRequest(BaseModel):
    """Edit recipe for clip modification via FFmpeg."""
    trim: Optional[dict] = None  # {"start_seconds": 2.5, "end_seconds": 28.0}
    segments: Optional[List[dict]] = None  # [{"start": 2.5, "end": 15.0}]
    caption: Optional[str] = None
    caption_style: Optional[dict] = None  # {"position": "bottom", "color": "white", "size": 24}
    audio: Optional[str] = "keep"  # "keep", "mute", "replace:<url>"
    speed: Optional[float] = 1.0  # 0.5 to 4.0
    filters: Optional[List[str]] = None  # ["grayscale", "sepia", "vintage", "blur", "sharpen"]
    text_overlays: Optional[List[dict]] = None
    transitions: Optional[List[str]] = None  # ["fade", "dissolve"]
    stickers: Optional[List[dict]] = None

class ClipEditJob(BaseModel):
    """Queued clip edit job status."""
    job_id: str
    clip_id: str
    user_id: str
    status: str  # "queued", "processing", "completed", "failed"
    recipe: ClipEditRequest
    result_url: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
