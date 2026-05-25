import os
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.models import (
    Clip, ClipCreate, ClipUpdate, ClipStatus,
    Platform, ClipEditRequest,
    RemixRequest, RemixResponse
)
from app.services.auth import get_current_user, get_user_db
from app.services.database import SupabaseService
from app.services.queue import QueueService
from app.services.scheduler import PostScheduler
from app.services.r2_service import R2Service
from app.services.zernio_service import ZernioService
from app.services.ffmpeg_service import FFmpegEditService
from app.services.music_library_service import music_library_service as music_library
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/clips", tags=["clips"])

class ClipListResponse(BaseModel):
    items: List[Clip]
    total: int
    page: int
    page_size: int

class ClipActionRequest(BaseModel):
    action: str  # "approve", "reject", "retry", "delete"
    reason: Optional[str] = None

class ScheduleRequest(BaseModel):
    post_time: str  # ISO 8601

class PostRequest(BaseModel):
    platforms: List[Platform]

queue = QueueService()
scheduler = PostScheduler()
r2 = R2Service()

# Initialize Zernio service if key is configured
zernio: Optional[ZernioService] = None
try:
    zernio = ZernioService()
except ValueError:
    zernio = None

@router.get("", response_model=ClipListResponse)
async def list_clips(
    status: Optional[ClipStatus] = None,
    pipeline_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """List clips with optional filtering."""
    try:
        clips = await db.list_clips(
            user_id=user.id,
            status=status,
            pipeline_id=pipeline_id,
            limit=page_size,
            offset=(page - 1) * page_size
        )
        
        total = len(clips)  # Placeholder
        
        return ClipListResponse(
            items=clips,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list clips: {str(e)}")

@router.get("/feed")
async def get_clip_feed(
    limit: int = Query(10, ge=1, le=50),
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Get clips ready for approval (swipe deck feed)."""
    try:
        clips = await db.list_clips(
            user_id=user.id,
            status="ready_for_review",
            limit=limit
        )
        return {"items": clips}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get feed: {str(e)}")

@router.post("", response_model=Clip, status_code=status.HTTP_201_CREATED)
async def create_clip(
    clip: ClipCreate,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Create a new clip and queue it for processing."""
    try:
        clip_data = clip.model_dump()
        clip_data["user_id"] = user.id
        clip_data["status"] = "queued"
        
        created = await db.create_clip(clip_data)
        
        await queue.enqueue("clip_generation", {
            "job_id": created["id"],
            "clip_id": created["id"],
            "source_id": clip.source_id,
            "pipeline_id": clip.pipeline_id,
            "user_id": user.id
        })
        
        return created
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create clip: {str(e)}")

@router.get("/{clip_id}", response_model=Clip)
async def get_clip(
    clip_id: str,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Get a specific clip by ID."""
    try:
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return clip
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get clip: {str(e)}")

@router.patch("/{clip_id}", response_model=Clip)
async def update_clip(
    clip_id: str,
    update: ClipUpdate,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Update a clip."""
    try:
        updated = await db.update_clip(clip_id, update.model_dump(exclude_unset=True))
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update clip: {str(e)}")

@router.post("/{clip_id}/approve")
async def approve_clip(
    clip_id: str,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Approve a clip for posting."""
    try:
        await db.update_clip(clip_id, {"status": "approved"})
        return {"success": True, "clip_id": clip_id, "status": "approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Approve failed: {str(e)}")

@router.post("/{clip_id}/reject")
async def reject_clip(
    clip_id: str,
    reason: Optional[str] = None,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Reject a clip."""
    try:
        await db.update_clip(clip_id, {
            "status": "rejected",
            "rejection_reason": reason
        })
        return {"success": True, "clip_id": clip_id, "status": "rejected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reject failed: {str(e)}")

@router.post("/{clip_id}/action")
async def clip_action(
    clip_id: str,
    action: ClipActionRequest,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Perform an action on a clip (approve, reject, retry, delete)."""
    try:
        if action.action == "approve":
            await db.update_clip(clip_id, {"status": "approved"})
        elif action.action == "reject":
            await db.update_clip(clip_id, {
                "status": "rejected",
                "rejection_reason": action.reason
            })
        elif action.action == "retry":
            await db.update_clip(clip_id, {"status": "queued"})
            clip = await db.get_clip(clip_id)
            if clip:
                await queue.enqueue("clip_generation", {
                    "job_id": clip_id,
                    "clip_id": clip_id,
                    "source_id": clip["source_id"],
                    "pipeline_id": clip["pipeline_id"],
                    "user_id": user.id
                })
        elif action.action == "delete":
            await db.delete_clip(clip_id)
        
        return {"success": True, "clip_id": clip_id, "action": action.action}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Action failed: {str(e)}")

@router.patch("/{clip_id}/schedule")
async def schedule_clip(
    clip_id: str,
    request: ScheduleRequest,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Schedule a clip for posting at a specific time."""
    try:
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        result = await scheduler.schedule_clip(
            clip_id=clip_id,
            pipeline_id=clip["pipeline_id"],
            post_time=request.post_time
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schedule failed: {str(e)}")

@router.post("/{clip_id}/post")
async def post_clip(
    clip_id: str,
    request: PostRequest,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Post an approved clip to selected platforms immediately via Zernio.
    
    If Zernio is configured, posts immediately with rate limit handling.
    Otherwise, falls back to queueing for background worker.
    """
    try:
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        video_url = clip.get("video_url")
        if not video_url:
            raise HTTPException(status_code=400, detail="Clip has no video URL")
        
        # Map platforms to Zernio format
        zernio_platforms = [ZernioService.map_platform_to_zernio(p.value) for p in request.platforms]
        
        if zernio:
            # Post via Zernio immediately
            result = await zernio.post_clip(
                video_url=video_url,
                caption=clip.get("caption", ""),
                platforms=zernio_platforms,
                hashtags=clip.get("tags", [])
            )
            
            # Update clip with post IDs
            platform_posts = {}
            for platform_result in result.get("platforms", []):
                platform_name = ZernioService.map_zernio_to_platform(platform_result.get("platform", ""))
                platform_posts[platform_name] = {
                    "platform": platform_name,
                    "post_id": platform_result.get("post_id"),
                    "post_url": platform_result.get("post_url"),
                    "status": "posted" if platform_result.get("success") else "failed",
                    "metrics": {}
                }
            
            await db.update_clip(clip_id, {
                "platform_posts": platform_posts,
                "status": "posted",
                "posted_at": "now()"
            })
            
            return {
                "success": True,
                "clip_id": clip_id,
                "platforms": platform_posts,
                "zernio_post_id": result.get("post_id"),
                "posted_via": "zernio"
            }
        else:
            # Fallback: queue for background worker
            results = []
            for platform in request.platforms:
                await queue.enqueue("social_post", {
                    "clip_id": clip_id,
                    "platform": platform.value,
                    "user_id": user.id,
                    "scheduled": False
                })
                results.append({"platform": platform.value, "status": "queued"})
            
            await db.update_clip(clip_id, {"status": "scheduled"})
            
            return {
                "success": True,
                "clip_id": clip_id,
                "results": results,
                "posted_via": "queue"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Post failed: {str(e)}")

@router.post("/{clip_id}/download-url")
async def get_download_url(
    clip_id: str,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Generate a presigned R2 URL for downloading a clip.
    
    The URL expires in 5 minutes and forces Content-Disposition: attachment
    so the device treats it as a download, not inline playback.
    """
    try:
        # Verify ownership
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to download this clip")
        
        if clip.get("status") not in ("rendered", "approved", "posted"):
            raise HTTPException(status_code=400, detail="Clip is not ready for download")
        
        # Build R2 key — follows storage convention: /clips/{clip_id}.mp4
        key = f"clips/{clip_id}.mp4"
        
        # Generate presigned URL with attachment disposition
        url = await r2.get_presigned_download_url(
            key=key,
            expires_in=300,  # 5 minutes
            filename=f"blissclip_{clip_id}.mp4"
        )
        
        return {
            "url": url,
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat(),
            "filename": f"blissclip_{clip_id}.mp4",
            "content_type": "video/mp4",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {str(e)}")


@router.post("/{clip_id}/edit")
async def edit_clip(
    clip_id: str,
    request: ClipEditRequest,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Edit a clip with advanced FFmpeg processing.
    
    Supports: trim, segments, caption, text overlays, filters,
    speed adjustment, audio mute, transitions.
    
    Processing is async via queue. Returns job_id for polling.
    """
    try:
        # Verify ownership
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Validate recipe
        ffmpeg = FFmpegEditService()
        is_valid, error = ffmpeg.validate_recipe(request.model_dump(exclude_unset=True))
        if not is_valid:
            raise HTTPException(status_code=400, detail=error)
        
        # Queue the edit job
        recipe_data = request.model_dump(exclude_unset=True)
        job_data = {
            "job_type": "clip_edit",
            "clip_id": clip_id,
            "user_id": user.id,
            "source_url": clip.get("video_url"),
            "recipe": recipe_data,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        job_id = await queue.enqueue("clip_edit", job_data)
        
        # Update clip status to indicate editing in progress
        await db.update_clip(clip_id, {
            "status": "editing",
            "edit_job_id": job_id,
            "edit_recipe": recipe_data
        })
        
        return {
            "success": True,
            "clip_id": clip_id,
            "job_id": job_id,
            "status": "queued",
            "message": "Edit job queued. Poll /clips/{id} for status updates."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Edit failed: {str(e)}")


@router.get("/{clip_id}/edit-status")
async def get_edit_status(
    clip_id: str,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Get the status of a clip edit job."""
    try:
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        job_id = clip.get("edit_job_id")
        if not job_id:
            return {"status": "no_edit", "clip_id": clip_id}
        
        # Check queue status
        job_status = await queue.get_job_status(job_id)
        
        return {
            "clip_id": clip_id,
            "job_id": job_id,
            "status": job_status or clip.get("status", "unknown"),
            "video_url": clip.get("video_url") if clip.get("status") == "rendered" else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get edit status: {str(e)}")


@router.post("/{clip_id}/remix", response_model=RemixResponse)
async def remix_clip(
    clip_id: str,
    request: RemixRequest,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """AI-powered remix of an existing clip.
    
    Extracts optimal segments using transcript analysis + audio energy scoring,
    applies hook archetype optimization from the user's top-performing patterns,
    generates 2-3 vertical 9:16 variants with new captions and thumbnails.
    
    Processing is async via queue. Returns immediately with job_id for polling.
    """
    try:
        # Verify ownership
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Queue the remix job (async processing)
        job_data = {
            "job_type": "clip_remix",
            "clip_id": clip_id,
            "user_id": user.id,
            "num_variants": request.num_variants,
            "target_duration": request.target_duration,
            "preferred_hook_archetype": request.preferred_hook_archetype,
            "include_music": request.include_music,
            "include_captions": request.include_captions,
            "output_format": request.output_format,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        job_id = await queue.enqueue("clip_remix", job_data)
        
        # Update original clip to track remix
        await db.update_clip(clip_id, {
            "remix_job_id": job_id,
            "remix_status": "queued"
        })
        
        return {
            "success": True,
            "original_clip_id": clip_id,
            "job_id": job_id,
            "status": "queued",
            "message": "Remix job queued. Poll /clips/{id}/remix-status for progress.",
            "variants": [],
            "total_variants": 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Remix failed: {str(e)}")


@router.get("/{clip_id}/remix-status")
async def get_remix_status(
    clip_id: str,
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Get the status of a clip remix job and any completed variants."""
    try:
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        job_id = clip.get("remix_job_id")
        if not job_id:
            return {
                "clip_id": clip_id,
                "status": "no_remix",
                "variants": []
            }
        
        # Check queue status
        job_status = await queue.get_job_status(job_id)
        
        # Fetch any completed remix variants
        variants = await db.list_clips(
            user_id=user.id,
            status="rendered",
            limit=10
        )
        # Filter to children of this clip
        remix_variants = [
            v for v in variants
            if v.get("parent_clip_id") == clip_id
        ]
        
        return {
            "clip_id": clip_id,
            "job_id": job_id,
            "status": job_status or clip.get("remix_status", "unknown"),
            "variants": remix_variants
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get remix status: {str(e)}")


@router.post("/{clip_id}/thumbnails")
async def get_thumbnails(
    clip_id: str,
    count: int = Query(20, ge=1, le=50),
    user = Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Generate thumbnail frames for timeline scrubber.
    
    Returns evenly spaced thumbnail images from the clip video.
    """
    try:
        from app.services.thumbnail_service import ThumbnailService
        
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        video_url = clip.get("video_url")
        if not video_url:
            raise HTTPException(status_code=400, detail="Clip has no video URL")
        
        thumbnail_service = ThumbnailService()
        result = await thumbnail_service.get_or_create_thumbnails(
            clip_id=clip_id,
            video_url=video_url,
            count=count
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Thumbnail generation failed"))
        
        return {
            "success": True,
            "clip_id": clip_id,
            "thumbnails": result["thumbnails"],
            "duration": result.get("duration"),
            "count": result["count"],
            "cached": result.get("cached", False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate thumbnails: {str(e)}")


# ─────────────────────────────────────────────────────────────
# A/B Testing Endpoints
# ─────────────────────────────────────────────────────────────

@router.post("/{clip_id}/ab-test")
async def create_ab_test(
    clip_id: str,
    variant_ids: List[str],
    user=Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db),
    platform: str = "tiktok",
    confidence_level: float = 0.95
):
    """Create an A/B test comparing original vs remix variants."""
    try:
        # Verify original clip exists and belongs to user
        original = await db.get_clip(clip_id)
        if not original:
            raise HTTPException(status_code=404, detail="Original clip not found")
        if original.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Verify all variants exist and belong to user
        for vid in variant_ids:
            variant = await db.get_clip(vid)
            if not variant:
                raise HTTPException(status_code=404, detail=f"Variant {vid} not found")
            if variant.get("user_id") != user.id:
                raise HTTPException(status_code=403, detail=f"Not authorized for variant {vid}")
        
        test = await ab_testing_service.create_test(
            original_clip_id=clip_id,
            user_id=user.id,
            variant_clip_ids=variant_ids,
            pipeline_id=original.get("pipeline_id"),
            platform=platform,
            confidence_level=confidence_level
        )
        
        return {
            "success": True,
            "test_id": test.test_id,
            "status": test.status.value,
            "variant_count": len(test.variants),
            "message": "A/B test created. Post variants to start collecting data."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create A/B test: {str(e)}")


@router.get("/{clip_id}/ab-test-status")
async def get_ab_test_status(
    clip_id: str,
    user=Depends(get_current_user)
):
    """Get A/B test status for a clip."""
    try:
        # Find test by original_clip_id
        tests = await ab_testing_service.list_user_tests(user.id, limit=50)
        
        test = next(
            (t for t in tests if t["original_clip_id"] == clip_id),
            None
        )
        
        if not test:
            raise HTTPException(status_code=404, detail="No A/B test found for this clip")
        
        return await ab_testing_service.get_test_status(test["test_id"])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get test status: {str(e)}")


@router.get("/ab-tests")
async def list_ab_tests(
    user=Depends(get_current_user),
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """List all A/B tests for the current user."""
    try:
        from app.services.ab_testing_service import TestStatus
        
        test_status = TestStatus(status) if status else None
        
        tests = await ab_testing_service.list_user_tests(
            user_id=user.id,
            status=test_status,
            limit=limit
        )
        
        return {
            "tests": tests,
            "total": len(tests)
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tests: {str(e)}")


# ─────────────────────────────────────────────────────────────
# Music Library Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/music/tracks")
async def list_music_tracks(
    mood: Optional[str] = None,
    genre: Optional[str] = None,
    vibe: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    user=Depends(get_current_user)
):
    """List available background music tracks with multi-dimensional filtering."""
    try:
        tracks = music_library.list_tracks(
            mood=mood,
            genre=genre,
            vibe=vibe,
            source=source,
            search=search,
        )
        distinct = music_library.get_distinct_values()
        return {
            "tracks": tracks,
            "total": len(tracks),
            "filters": {
                "genres": distinct["genres"],
                "vibes": distinct["vibes"],
                "moods": distinct["moods"],
                "sources": distinct["sources"],
            },
            "sources": {
                "bundled": "Pre-bundled royalty-free tracks",
                "pixabay": "Pixabay Music (CC0)",
                "fma": "Free Music Archive (CC)",
                "incompetech": "Incompetech / Kevin MacLeod (CC BY)",
                "user_upload": "User-uploaded tracks",
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tracks: {str(e)}")


@router.post("/music/upload")
async def upload_music_track(
    file: UploadFile,
    title: str,
    artist: Optional[str] = "Unknown",
    genre: Optional[str] = "misc",
    vibe: Optional[str] = "neutral",
    license_type: Optional[str] = "user_owned",
    user=Depends(get_current_user)
):
    """Upload a custom music track to the library.
    
    The track will be stored in user_uploads/ and made available
    for mixing in clips.
    """
    try:
        # Validate file
        if not file.filename or not file.filename.endswith(".mp3"):
            raise HTTPException(status_code=400, detail="Only MP3 files are supported")
        
        # Save to temp
        temp_path = f"/tmp/upload_{user.id}_{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            # Add to library
            track = music_library.add_user_upload(
                file_path=temp_path,
                user_id=user.id,
                title=title,
                artist=artist,
                genre=genre,
                vibe=vibe,
                license_type=license_type,
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        return {
            "success": True,
            "track": music_library.get_track_info(track.id),
            "message": f"Track '{title}' uploaded successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/music/reload-catalog")
async def reload_music_catalog(user=Depends(get_current_user)):
    """Reload the music catalog (for admin use after bulk downloads)."""
    try:
        music_library.reload()
        distinct = music_library.get_distinct_values()
        return {
            "success": True,
            "total_tracks": len(music_library.tracks),
            "filters": {
                "genres": distinct["genres"],
                "vibes": distinct["vibes"],
                "moods": distinct["moods"],
                "sources": distinct["sources"],
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reload failed: {str(e)}")


@router.post("/{clip_id}/preview-music")
async def preview_music_mix(
    clip_id: str,
    track_id: str,
    profile: str = "background",
    preview_duration: Optional[float] = None,
    custom_duck_factor: Optional[float] = None,
    user=Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Generate a music-mixed preview of a clip.

    Renders a preview video with background music mixed in using FFmpeg.
    The preview is stored in R2 and returned as a presigned URL.

    Args:
        track_id: Music track ID from /music/tracks
        profile: Mix profile — prominent, background, intro_only, outro_only, build
        preview_duration: Optional — render only first N seconds for quick preview
        custom_duck_factor: Optional — override profile ducking (0.0-1.0)
    """
    try:
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        video_url = clip.get("video_url")
        if not video_url:
            raise HTTPException(status_code=400, detail="Clip has no video URL")
        
        from app.services.music_mix_service import music_mix_service
        
        result = await music_mix_service.generate_preview(
            clip_id=clip_id,
            video_url=video_url,
            track_id=track_id,
            profile=profile,
            preview_duration=preview_duration,
            custom_duck_factor=custom_duck_factor,
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Preview generation failed"))
        
        return {
            "success": True,
            "clip_id": clip_id,
            "track_id": track_id,
            "job_id": result["job_id"],
            "preview_url": result["preview_url"],
            "profile": result["profile"],
            "duck_factor": result["duck_factor"],
            "duration": result["duration"],
            "expires_at": result["expires_at"],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview music: {str(e)}")


@router.get("/music/profiles")
async def list_mix_profiles(user=Depends(get_current_user)):
    """List available music mix profiles."""
    from app.services.music_mix_service import music_mix_service
    return {
        "profiles": music_mix_service.get_profiles()
    }


# ─────────────────────────────────────────────────────────────
# Edit Swarm Agent Endpoints
# ─────────────────────────────────────────────────────────────

from app.services.edit_agent_service import EditSwarm

class EditAgentsRequest(BaseModel):
    agents: List[str]  # e.g., ["sticker", "music", "color"]
    clip_data: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None

class EditAgentsResponse(BaseModel):
    recipe: Dict[str, Any]
    agents_run: List[Dict[str, Any]]
    total_cost_estimate: float
    clip_id: Optional[str] = None

@router.post("/{clip_id}/edit-agents")
async def run_edit_agents(
    clip_id: str,
    request: EditAgentsRequest,
    user=Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Run selected Edit Swarm agents and return a merged edit recipe.

    Agents analyze the clip and generate an edit recipe that can be
    applied via the standard /edit endpoint.

    Available agents: sticker, transition, music, color, caption, pacing, thumbnail
    """
    try:
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Build clip_data for agents
        clip_data = request.clip_data or {}
        clip_data.setdefault("id", clip_id)
        clip_data.setdefault("caption", clip.get("caption", ""))
        clip_data.setdefault("duration", clip.get("duration", 30))
        clip_data.setdefault("platform", clip.get("platform", "tiktok"))
        clip_data.setdefault("tags", clip.get("tags", []))
        
        swarm = EditSwarm()
        result = await swarm.run(
            clip_data=clip_data,
            agents=request.agents,
            settings=request.settings or {}
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent swarm failed: {str(e)}")


@router.post("/{clip_id}/edit-analyze")
async def analyze_clip_for_editing(
    clip_id: str,
    user=Depends(get_current_user),
    db: SupabaseService = Depends(get_user_db)
):
    """Analyze a clip with all agents and return enhancement suggestions.

    Returns per-agent analysis, cost estimates, and quality scores.
    Use this to decide which agents to run.
    """
    try:
        clip = await db.get_clip(clip_id)
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        if clip.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        clip_data = {
            "id": clip_id,
            "caption": clip.get("caption", ""),
            "duration": clip.get("duration", 30),
            "platform": clip.get("platform", "tiktok"),
            "tags": clip.get("tags", []),
        }
        
        swarm = EditSwarm()
        suggestions = await swarm.analyze_clip(clip_data)
        
        return {
            "clip_id": clip_id,
            "suggestions": suggestions,
            "total_agents": len(suggestions),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/assets/stickers")
async def list_sticker_assets(user=Depends(get_current_user)):
    """List all available sticker assets."""
    from app.services.edit_agent_service import StickerAgent
    agent = StickerAgent()
    return {
        "stickers": agent.STICKER_LIBRARY,
        "positions": list(agent.POSITION_PRESETS.keys())
    }


@router.get("/assets/transitions")
async def list_transition_assets(user=Depends(get_current_user)):
    """List all available transition types."""
    from app.services.edit_agent_service import TransitionAgent
    agent = TransitionAgent()
    return {
        "transitions": agent.TRANSITION_LIBRARY
    }


@router.get("/assets/music")
async def list_music_assets(user=Depends(get_current_user)):
    """List all available music tracks."""
    from app.services.edit_agent_service import MusicAgent
    agent = MusicAgent()
    return {
        "tracks": agent.MUSIC_LIBRARY
    }

@router.post("/generate-hooks")
async def generate_hooks_llm(
    transcript: str,
    user=Depends(get_current_user),
    num_variants: int = 3,
    platform: str = "tiktok"
):
    """
    Generate viral hooks using Claude LLM.
    
    This endpoint is useful for testing the LLM hook generation
    without going through the full remix pipeline.
    """
    try:
        # Get user's top archetypes
        from app.services.hook_analysis_service import hook_analysis_service
        
        user_top_archetypes = []
        try:
            hook_analysis = await hook_analysis_service.analyze_hooks(user.id, days=30)
            if hook_analysis.get("archetypes"):
                user_top_archetypes = hook_analysis["archetypes"]
        except Exception:
            pass
        
        # Generate hooks
        hooks = await claude_hook_service.generate_hooks(
            transcript_text=transcript,
            user_top_archetypes=user_top_archetypes,
            num_variants=num_variants,
            platform=platform
        )
        
        return {
            "success": True,
            "hooks": [
                {
                    "hook_text": h.hook_text,
                    "archetype": h.archetype,
                    "confidence": h.confidence,
                    "rationale": h.rationale,
                    "estimated_retention": h.estimated_retention,
                    "variant_index": h.variant_index
                }
                for h in hooks
            ],
            "user_top_archetypes": user_top_archetypes,
            "model_used": "claude-sonnet-4-20250514" if claude_hook_service.api_key else "fallback"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hook generation failed: {str(e)}")
