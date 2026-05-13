from langgraph.graph import StateGraph, END
from typing import Dict, Any, TypedDict, Optional
import logging
import tempfile
import os

from app.core.config import settings
from app.services.video_download import VideoDownloadService
from app.services.transcription import TranscriptionService
from app.services.clip_generation import ClipGenerationService, ThumbnailService
from app.services.safety import SafetyCheckService, ContentEnrichmentService
from app.services.database import SupabaseService
from app.services.r2_service import R2Service

logger = logging.getLogger(__name__)

class ClipProcessingState(TypedDict):
    """State for the clip processing pipeline."""
    clip_id: str
    source_id: str
    pipeline_id: str
    user_id: str
    video_path: Optional[str]
    audio_path: Optional[str]
    transcription: Optional[Dict[str, Any]]
    segments: Optional[list]
    generated_clips: Optional[list]
    safety_result: Optional[Dict[str, Any]]
    thumbnail_path: Optional[str]
    status: str
    error: str
    metadata: Dict[str, Any]

class ClipProcessingPipeline:
    """Complete AI pipeline for processing video into short-form clips."""
    
    def __init__(self):
        self.video_service = VideoDownloadService()
        self.transcription_service = TranscriptionService()
        self.clip_service = ClipGenerationService()
        self.thumbnail_service = ThumbnailService()
        self.safety_service = SafetyCheckService()
        self.enrichment_service = ContentEnrichmentService()
        self.db = SupabaseService()
        self.storage = R2Service()
        self.workflow = self._build_workflow()
    
    def _build_workflow(self):
        """Build the LangGraph workflow."""
        workflow = StateGraph(ClipProcessingState)
        
        # Define nodes
        workflow.add_node("download_source", self._download_source)
        workflow.add_node("extract_audio", self._extract_audio)
        workflow.add_node("transcribe", self._transcribe)
        workflow.add_node("detect_segments", self._detect_segments)
        workflow.add_node("generate_clips", self._generate_clips)
        workflow.add_node("safety_check", self._safety_check)
        workflow.add_node("enrich_content", self._enrich_content)
        workflow.add_node("create_thumbnails", self._create_thumbnails)
        workflow.add_node("upload_assets", self._upload_assets)
        workflow.add_node("finalize", self._finalize)
        
        # Define edges
        workflow.set_entry_point("download_source")
        workflow.add_edge("download_source", "extract_audio")
        workflow.add_edge("extract_audio", "transcribe")
        workflow.add_edge("transcribe", "detect_segments")
        workflow.add_edge("detect_segments", "generate_clips")
        workflow.add_edge("generate_clips", "safety_check")
        
        # Conditional edge after safety check
        workflow.add_conditional_edges(
            "safety_check",
            self._should_proceed,
            {
                "pass": "enrich_content",
                "block": "finalize",
                "review": "enrich_content"
            }
        )
        
        workflow.add_edge("enrich_content", "create_thumbnails")
        workflow.add_edge("create_thumbnails", "upload_assets")
        workflow.add_edge("upload_assets", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    async def _download_source(self, state: ClipProcessingState) -> ClipProcessingState:
        """Download source video."""
        logger.info(f"[Pipeline] Downloading source {state['source_id']}")
        state["status"] = "downloading"
        
        try:
            # Get source info from database
            # source = await self.db.get_source(state["source_id"])
            # For now, assume we have the video URL
            
            # Create temp directory for processing
            temp_dir = tempfile.mkdtemp(prefix=f"clip_{state['clip_id']}_")
            video_path = os.path.join(temp_dir, "source.mp4")
            
            # TODO: Get actual source URL from database
            # For demo, create a placeholder
            state["video_path"] = video_path
            state["metadata"]["temp_dir"] = temp_dir
            
            logger.info(f"[Pipeline] Video path: {video_path}")
        except Exception as e:
            logger.error(f"[Pipeline] Download failed: {e}")
            state["error"] = str(e)
            state["status"] = "failed"
        
        return state
    
    async def _extract_audio(self, state: ClipProcessingState) -> ClipProcessingState:
        """Extract audio from video."""
        if state.get("error"):
            return state
        
        logger.info(f"[Pipeline] Extracting audio for clip {state['clip_id']}")
        state["status"] = "extracting_audio"
        
        try:
            temp_dir = state["metadata"]["temp_dir"]
            audio_path = os.path.join(temp_dir, "audio.wav")
            
            await self.video_service.extract_audio(
                state["video_path"],
                audio_path
            )
            
            state["audio_path"] = audio_path
            logger.info(f"[Pipeline] Audio extracted: {audio_path}")
        except Exception as e:
            logger.error(f"[Pipeline] Audio extraction failed: {e}")
            state["error"] = str(e)
            state["status"] = "failed"
        
        return state
    
    async def _transcribe(self, state: ClipProcessingState) -> ClipProcessingState:
        """Transcribe audio to text."""
        if state.get("error"):
            return state
        
        logger.info(f"[Pipeline] Transcribing clip {state['clip_id']}")
        state["status"] = "transcribing"
        
        try:
            transcription = await self.transcription_service.transcribe(
                state["audio_path"]
            )
            
            state["transcription"] = transcription
            state["metadata"]["full_text"] = transcription.get("text", "")
            
            logger.info(f"[Pipeline] Transcription complete: {len(transcription.get('text', ''))} chars")
        except Exception as e:
            logger.error(f"[Pipeline] Transcription failed: {e}")
            state["error"] = str(e)
            state["status"] = "failed"
        
        return state
    
    async def _detect_segments(self, state: ClipProcessingState) -> ClipProcessingState:
        """Find interesting segments in the video."""
        if state.get("error"):
            return state
        
        logger.info(f"[Pipeline] Detecting segments for clip {state['clip_id']}")
        state["status"] = "detecting_segments"
        
        try:
            segments = self.transcription_service.find_interesting_segments(
                state["transcription"],
                min_duration=15,
                max_duration=90,
                num_clips=5
            )
            
            state["segments"] = segments
            state["metadata"]["num_segments_found"] = len(segments)
            
            logger.info(f"[Pipeline] Found {len(segments)} interesting segments")
        except Exception as e:
            logger.error(f"[Pipeline] Segment detection failed: {e}")
            state["error"] = str(e)
            state["status"] = "failed"
        
        return state
    
    async def _generate_clips(self, state: ClipProcessingState) -> ClipProcessingState:
        """Generate video clips from segments."""
        if state.get("error"):
            return state
        
        logger.info(f"[Pipeline] Generating clips for {state['clip_id']}")
        state["status"] = "generating_clips"
        
        try:
            temp_dir = state["metadata"]["temp_dir"]
            generated_clips = []
            
            for i, segment in enumerate(state["segments"]):
                clip_path = os.path.join(temp_dir, f"clip_{i}.mp4")
                
                await self.clip_service.generate_clip(
                    source_video=state["video_path"],
                    output_path=clip_path,
                    start_time=segment["start"],
                    end_time=segment["end"],
                    target_aspect_ratio="9:16",  # Vertical for TikTok/Reels
                    target_resolution="1080x1920"
                )
                
                generated_clips.append({
                    "path": clip_path,
                    "segment": segment,
                    "index": i
                })
            
            state["generated_clips"] = generated_clips
            state["metadata"]["clips_generated"] = len(generated_clips)
            
            logger.info(f"[Pipeline] Generated {len(generated_clips)} clips")
        except Exception as e:
            logger.error(f"[Pipeline] Clip generation failed: {e}")
            state["error"] = str(e)
            state["status"] = "failed"
        
        return state
    
    async def _safety_check(self, state: ClipProcessingState) -> ClipProcessingState:
        """Run safety checks on generated content."""
        if state.get("error"):
            return state
        
        logger.info(f"[Pipeline] Running safety checks for {state['clip_id']}")
        state["status"] = "checking_safety"
        
        try:
            text = state["transcription"].get("text", "")
            
            safety_result = await self.safety_service.check_content(
                text=text,
                video_path=state["video_path"]
            )
            
            state["safety_result"] = safety_result
            state["metadata"]["safety"] = safety_result["status"]
            
            # Generate safety report
            report = self.safety_service.generate_safety_report(
                state["clip_id"],
                safety_result
            )
            state["metadata"]["safety_report"] = report
            
            logger.info(f"[Pipeline] Safety check: {safety_result['status']}")
        except Exception as e:
            logger.error(f"[Pipeline] Safety check failed: {e}")
            # Don't fail the pipeline on safety check error - default to review
            state["safety_result"] = {"status": "review", "categories": [], "reasons": [f"Safety check error: {e}"]}
            state["metadata"]["safety"] = "review"
        
        return state
    
    async def _enrich_content(self, state: ClipProcessingState) -> ClipProcessingState:
        """Generate captions, hashtags, and titles."""
        if state.get("error"):
            return state
        
        logger.info(f"[Pipeline] Enriching content for {state['clip_id']}")
        state["status"] = "enriching"
        
        try:
            text = state["transcription"].get("text", "")
            
            # Generate title
            title = await self.enrichment_service.generate_title(
                transcript=text,
                niche="general"  # TODO: Get from pipeline config
            )
            
            # Generate caption
            caption = await self.enrichment_service.generate_caption(
                transcript=text,
                niche="general",
                platform="tiktok"
            )
            
            # Generate hashtags
            hashtags = await self.enrichment_service.generate_hashtags(
                transcript=text,
                niche="general",
                platform="tiktok",
                count=5
            )
            
            state["metadata"]["title"] = title
            state["metadata"]["caption"] = caption
            state["metadata"]["hashtags"] = hashtags
            
            logger.info(f"[Pipeline] Content enriched: title='{title[:50]}...'")
        except Exception as e:
            logger.error(f"[Pipeline] Content enrichment failed: {e}")
            # Don't fail pipeline - use fallbacks
            state["metadata"]["title"] = "Untitled Clip"
            state["metadata"]["caption"] = text[:150]
            state["metadata"]["hashtags"] = ["#content", "#viral"]
        
        return state
    
    async def _create_thumbnails(self, state: ClipProcessingState) -> ClipProcessingState:
        """Generate thumbnails for clips."""
        if state.get("error"):
            return state
        
        logger.info(f"[Pipeline] Creating thumbnails for {state['clip_id']}")
        state["status"] = "creating_thumbnails"
        
        try:
            temp_dir = state["metadata"]["temp_dir"]
            
            # Create thumbnail for first clip (main clip)
            if state["generated_clips"]:
                main_clip = state["generated_clips"][0]
                thumbnail_path = os.path.join(temp_dir, "thumbnail.jpg")
                
                await self.thumbnail_service.generate_thumbnail(
                    video_path=main_clip["path"],
                    output_path=thumbnail_path
                )
                
                state["thumbnail_path"] = thumbnail_path
                logger.info(f"[Pipeline] Thumbnail created: {thumbnail_path}")
        except Exception as e:
            logger.error(f"[Pipeline] Thumbnail creation failed: {e}")
            state["thumbnail_path"] = None
        
        return state
    
    async def _upload_assets(self, state: ClipProcessingState) -> ClipProcessingState:
        """Upload clips and thumbnails to storage."""
        if state.get("error"):
            return state
        
        logger.info(f"[Pipeline] Uploading assets for {state['clip_id']}")
        state["status"] = "uploading"
        
        try:
            user_id = state["user_id"]
            clip_id = state["clip_id"]
            
            # Upload main clip
            if state["generated_clips"]:
                main_clip = state["generated_clips"][0]
                video_key = f"users/{user_id}/clips/{clip_id}/video.mp4"
                
                with open(main_clip["path"], "rb") as f:
                    video_url = await self.storage.upload_file(
                        key=video_key,
                        file=f,
                        content_type="video/mp4"
                    )
                
                state["metadata"]["video_url"] = video_url
            
            # Upload thumbnail
            if state["thumbnail_path"]:
                thumb_key = f"users/{user_id}/clips/{clip_id}/thumbnail.jpg"
                
                with open(state["thumbnail_path"], "rb") as f:
                    thumb_url = await self.storage.upload_file(
                        key=thumb_key,
                        file=f,
                        content_type="image/jpeg"
                    )
                
                state["metadata"]["thumbnail_url"] = thumb_url
            
            logger.info(f"[Pipeline] Assets uploaded successfully")
        except Exception as e:
            logger.error(f"[Pipeline] Upload failed: {e}")
            state["error"] = str(e)
            state["status"] = "failed"
        
        return state
    
    async def _finalize(self, state: ClipProcessingState) -> ClipProcessingState:
        """Finalize clip and update database."""
        logger.info(f"[Pipeline] Finalizing clip {state['clip_id']}")
        
        if state.get("error"):
            state["status"] = "failed"
            
            # Update database with failure status
            try:
                await self.db.update_clip(state["clip_id"], {
                    "status": "failed",
                    "error_message": state["error"]
                })
            except Exception as db_error:
                logger.error(f"[Pipeline] Failed to update database: {db_error}")
        else:
            # Determine final status
            safety_status = state.get("safety_result", {}).get("status", "review")
            
            if safety_status == "block":
                final_status = "rejected"
            elif safety_status == "review":
                final_status = "ready_for_review"
            else:
                final_status = "approved"
            
            state["status"] = final_status
            
            # Update database with completed clip
            try:
                clip_data = {
                    "status": final_status,
                    "video_url": state["metadata"].get("video_url"),
                    "thumbnail_url": state["metadata"].get("thumbnail_url"),
                    "title": state["metadata"].get("title"),
                    "caption": state["metadata"].get("caption"),
                    "hashtags": state["metadata"].get("hashtags", []),
                    "duration_seconds": state["segments"][0]["duration"] if state["segments"] else None,
                    "safety_flags": state["safety_result"].get("categories", []),
                    "metadata": {
                        "transcription_text": state["metadata"].get("full_text", ""),
                        "num_segments": len(state["segments"]) if state["segments"] else 0,
                        "safety_report": state["metadata"].get("safety_report")
                    }
                }
                
                await self.db.update_clip(state["clip_id"], clip_data)
                logger.info(f"[Pipeline] Clip {state['clip_id']} finalized with status: {final_status}")
            except Exception as db_error:
                logger.error(f"[Pipeline] Failed to update database: {db_error}")
        
        # Cleanup temp files
        try:
            temp_dir = state["metadata"].get("temp_dir")
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"[Pipeline] Cleaned up temp directory: {temp_dir}")
        except Exception as cleanup_error:
            logger.warning(f"[Pipeline] Cleanup failed: {cleanup_error}")
        
        return state
    
    def _should_proceed(self, state: ClipProcessingState) -> str:
        """Determine next step after safety check."""
        if state.get("error"):
            return "block"
        
        safety = state.get("safety_result", {}).get("status", "review")
        return safety
    
    async def process(self, clip_id: str, source_id: str, pipeline_id: str, user_id: str) -> Dict[str, Any]:
        """Execute the full clip processing workflow."""
        initial_state = ClipProcessingState(
            clip_id=clip_id,
            source_id=source_id,
            pipeline_id=pipeline_id,
            user_id=user_id,
            video_path=None,
            audio_path=None,
            transcription=None,
            segments=None,
            generated_clips=None,
            safety_result=None,
            thumbnail_path=None,
            status="starting",
            error="",
            metadata={}
        )
        
        try:
            result = await self.workflow.ainvoke(initial_state)
            return {
                "clip_id": clip_id,
                "status": result["status"],
                "error": result.get("error"),
                "metadata": result["metadata"]
            }
        except Exception as e:
            logger.error(f"[Pipeline] Workflow failed: {e}")
            
            # Update database with failure
            try:
                await self.db.update_clip(clip_id, {
                    "status": "failed",
                    "error_message": str(e)
                })
            except Exception:
                pass
            
            return {
                "clip_id": clip_id,
                "status": "failed",
                "error": str(e),
                "metadata": {}
            }

# Backward compatibility
LangGraphService = ClipProcessingPipeline
