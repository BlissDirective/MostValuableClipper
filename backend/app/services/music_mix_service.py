"""
Music Mix Service for generating audio-mixed clip previews.

Provides FFmpeg-based mixing with:
- Volume ducking during speech
- Music looping/trimming to fit clip duration
- Fade in/out curves
- Multiple mix profiles (prominent, background, intro-only, outro-only)
- Preview generation (full clip or first N seconds)
- R2 storage for rendered previews
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from app.services.r2_service import R2Service
from app.services.music_library_service import MusicLibraryService, MusicTrack

logger = logging.getLogger(__name__)


class MixProfile:
    """Named mix configuration."""
    name: str
    duck_factor: float
    fade_in: float
    fade_out: float
    music_start_offset: float  # seconds into clip to start music
    music_end_before_clip_end: float  # seconds before clip end to stop music
    loop: bool


MIX_PROFILES = {
    "prominent": MixProfile(),  # Music prominent, light ducking
    "background": MixProfile(),  # Music in background, heavy ducking
    "intro_only": MixProfile(),  # Music only at start
    "outro_only": MixProfile(),  # Music only at end
    "build": MixProfile(),  # Music builds to climax
}

# Configure profiles
MIX_PROFILES["prominent"].__dict__.update({
    "name": "prominent", "duck_factor": 0.25, "fade_in": 2.0, "fade_out": 3.0,
    "music_start_offset": 0.0, "music_end_before_clip_end": 2.0, "loop": True
})
MIX_PROFILES["background"].__dict__.update({
    "name": "background", "duck_factor": 0.08, "fade_in": 3.0, "fade_out": 4.0,
    "music_start_offset": 1.0, "music_end_before_clip_end": 3.0, "loop": True
})
MIX_PROFILES["intro_only"].__dict__.update({
    "name": "intro_only", "duck_factor": 0.20, "fade_in": 1.0, "fade_out": 2.0,
    "music_start_offset": 0.0, "music_end_before_clip_end": 999.0, "loop": False
})
MIX_PROFILES["outro_only"].__dict__.update({
    "name": "outro_only", "duck_factor": 0.20, "fade_in": 2.0, "fade_out": 1.0,
    "music_start_offset": -999.0, "music_end_before_clip_end": 0.0, "loop": False
})
MIX_PROFILES["build"].__dict__.update({
    "name": "build", "duck_factor": 0.15, "fade_in": 1.0, "fade_out": 5.0,
    "music_start_offset": 0.0, "music_end_before_clip_end": 0.0, "loop": True
})


class MusicMixService:
    """
    Generate mixed audio previews for clips.
    
    Mixes background music with clip audio using FFmpeg,
    with configurable ducking, fading, and timing.
    """
    
    def __init__(self):
        self.r2 = R2Service()
        self.music_lib = MusicLibraryService()
    
    def _run_ffmpeg(self, cmd: List[str], timeout: int = 180) -> Tuple[bool, str]:
        """Run FFmpeg command and return (success, error_or_output)."""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, f"FFmpeg error: {e.stderr}"
        except subprocess.TimeoutExpired:
            return False, "FFmpeg timeout"
    
    def _get_audio_info(self, path: str) -> Dict[str, Any]:
        """Get audio duration via ffprobe."""
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=duration",
            "-of", "json", path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            data = json.loads(result.stdout)
            stream = data.get("streams", [{}])[0]
            return {"duration": float(stream.get("duration", 0))}
        except Exception:
            return {"duration": 0}
    
    async def generate_preview(
        self,
        clip_id: str,
        video_url: str,
        track_id: str,
        profile: str = "background",
        preview_duration: Optional[float] = None,
        custom_duck_factor: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generate a music-mixed preview of a clip.
        
        Args:
            clip_id: Clip ID for R2 key naming
            video_url: Source video URL
            track_id: Music track ID from library
            profile: Mix profile name (prominent, background, intro_only, outro_only, build)
            preview_duration: If set, only render first N seconds (for quick preview)
            custom_duck_factor: Override profile duck factor (0.0-1.0)
        
        Returns:
            Dict with preview_url, job_id, duration, profile_used
        """
        track = self.music_lib.get_track_info(track_id)
        if not track:
            return {"success": False, "error": f"Track {track_id} not found"}
        
        if not track.get("available"):
            return {"success": False, "error": f"Track {track_id} not available on disk"}
        
        mix_profile = MIX_PROFILES.get(profile, MIX_PROFILES["background"])
        duck_factor = custom_duck_factor if custom_duck_factor is not None else mix_profile.duck_factor
        
        job_id = f"mix_{clip_id}_{track_id}_{profile}_{int(datetime.now(timezone.utc).timestamp())}"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download source video
            source_path = os.path.join(temp_dir, "source.mp4")
            if video_url.startswith("http"):
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(video_url, timeout=120)
                    response.raise_for_status()
                    with open(source_path, "wb") as f:
                        f.write(response.content)
            else:
                # Local path
                source_path = video_url
            
            # Get video info
            video_info = self._get_audio_info(source_path)
            video_duration = video_info.get("duration", 30)
            
            # Determine preview duration
            render_duration = preview_duration or video_duration
            render_duration = min(render_duration, video_duration)
            
            # Get track file path
            track_file = None
            for t in self.music_lib.tracks:
                if t.id == track_id:
                    track_file = t.file_path
                    break
            
            if not track_file or not os.path.exists(track_file):
                return {"success": False, "error": f"Track file not found: {track_file}"}
            
            # Get track duration
            track_info = self._get_audio_info(track_file)
            track_duration = track_info.get("duration", 120)
            
            # Build FFmpeg command
            output_path = os.path.join(temp_dir, "preview.mp4")
            
            # Calculate music timing
            music_start = max(0, mix_profile.music_start_offset)
            if mix_profile.music_start_offset < 0:
                # Negative offset = start before end
                music_start = max(0, render_duration + mix_profile.music_start_offset)
            
            music_end = render_duration - mix_profile.music_end_before_clip_end
            if mix_profile.music_end_before_clip_end > 900:
                # Large value = use only beginning portion (intro_only)
                music_end = min(render_duration * 0.4, track_duration)
            music_end = min(music_end, render_duration)
            music_duration = max(0, music_end - music_start)
            
            if music_duration < 1.0:
                return {"success": False, "error": "Music duration too short after profile constraints"}
            
            # Build filter complex
            filter_parts = []
            
            # Music input processing
            music_filters = []
            
            # Loop if needed
            if mix_profile.loop and track_duration < music_duration:
                loop_count = int(music_duration / track_duration) + 1
                music_filters.append(f"aloop=loop={loop_count}:size=2e+09")
            
            # Trim to needed duration
            music_filters.append(f"atrim=start={music_start}:end={music_end}")
            
            # Fade in
            if mix_profile.fade_in > 0:
                music_filters.append(f"afade=t=in:ss=0:d={mix_profile.fade_in}")
            
            # Fade out
            if mix_profile.fade_out > 0:
                fade_start = max(0, music_duration - mix_profile.fade_out)
                music_filters.append(f"afade=t=out:st={fade_start}:d={mix_profile.fade_out}")
            
            # Volume / ducking
            music_filters.append(f"volume={duck_factor}")
            
            # Build full filter
            music_filter_str = ",".join(music_filters)
            
            filter_complex = (
                f"[1:a]{music_filter_str}[music];"
                f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )
            
            # Build command
            cmd = [
                "ffmpeg", "-y",
                "-i", source_path,
                "-i", track_file,
                "-filter_complex", filter_complex,
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "28",
                "-c:a", "aac", "-b:a", "192k",
                "-t", str(render_duration),
                "-movflags", "+faststart",
                output_path
            ]
            
            # For preview mode, trim video too
            if preview_duration:
                cmd = [
                    "ffmpeg", "-y",
                    "-i", source_path,
                    "-i", track_file,
                    "-filter_complex", filter_complex,
                    "-map", "0:v",
                    "-map", "[aout]",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "28",
                    "-c:a", "aac", "-b:a", "192k",
                    "-t", str(preview_duration),
                    "-movflags", "+faststart",
                    output_path
                ]
            
            logger.info(f"[MusicMix] Rendering preview: {job_id}")
            logger.info(f"[MusicMix] Profile={profile}, duck={duck_factor}, duration={render_duration}s")
            
            success, error = self._run_ffmpeg(cmd, timeout=180)
            
            if not success:
                logger.error(f"[MusicMix] Failed: {error}")
                return {"success": False, "error": error, "job_id": job_id}
            
            # Upload to R2
            r2_key = f"previews/{job_id}.mp4"
            await self.r2.upload_file(output_path, r2_key)
            preview_url = await self.r2.get_presigned_url(r2_key, expires_in=3600)
            
            logger.info(f"[MusicMix] Preview ready: {preview_url[:80]}...")
            
            return {
                "success": True,
                "job_id": job_id,
                "preview_url": preview_url,
                "clip_id": clip_id,
                "track_id": track_id,
                "profile": profile,
                "duck_factor": duck_factor,
                "duration": render_duration,
                "expires_at": (datetime.now(timezone.utc).timestamp() + 3600)
            }
    
    async def mix_for_edit(
        self,
        source_path: str,
        track: MusicTrack,
        output_path: str,
        video_duration: float,
        duck_factor: Optional[float] = None,
        fade_in: float = 1.0,
        fade_out: float = 2.0,
    ) -> Tuple[bool, str]:
        """
        Mix music into a clip for the edit pipeline.
        
        Simpler interface for the edit agent service.
        """
        if not track.file_path or not os.path.exists(track.file_path):
            return False, f"Track file not found: {track.file_path}"
        
        duck = duck_factor if duck_factor is not None else track.volume_duck_factor
        
        # Music should end ~2 seconds before video for clean outro
        music_duration = min(video_duration - 2.0, track.duration_seconds)
        music_duration = max(music_duration, 3.0)
        
        filter_complex = (
            f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{music_duration},"
            f"afade=t=in:ss=0:d={fade_in},afade=t=out:st={music_duration-fade_out}:d={fade_out},"
            f"volume={duck}[music];"
            f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        
        cmd = [
            "ffmpeg", "-y",
            "-i", source_path,
            "-i", track.file_path,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path
        ]
        
        return self._run_ffmpeg(cmd, timeout=300)
    
    def get_profiles(self) -> List[Dict[str, Any]]:
        """List available mix profiles with descriptions."""
        return [
            {
                "id": p.name,
                "name": p.name.replace("_", " ").title(),
                "duck_factor": p.duck_factor,
                "fade_in": p.fade_in,
                "fade_out": p.fade_out,
                "description": self._profile_description(p.name)
            }
            for p in MIX_PROFILES.values()
        ]
    
    def _profile_description(self, profile_id: str) -> str:
        descriptions = {
            "prominent": "Music leads, light ducking. Best for montages and high-energy clips.",
            "background": "Music stays subtle behind speech. Best for talking-head and tutorial clips.",
            "intro_only": "Music plays at the start then fades out. Great for branded intros.",
            "outro_only": "Music fades in for the ending. Perfect for call-to-action closings.",
            "build": "Music builds throughout, peaking at the climax. Ideal for storytelling arcs."
        }
        return descriptions.get(profile_id, "Custom mix profile.")


# Singleton
music_mix_service = MusicMixService()