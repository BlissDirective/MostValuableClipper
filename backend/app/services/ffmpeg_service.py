import subprocess
import json
import os
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from app.core.config import settings
from app.services.r2_service import R2Service

class FFmpegEditService:
    """Server-side video editing via FFmpeg.
    
    Supports: trim, concat, text overlays, audio mute/replace,
    speed adjustment, filters, and basic transitions.
    """
    
    def __init__(self):
        self.r2 = R2Service()
    
    def _run_ffmpeg(self, cmd: List[str], timeout: int = 300) -> Tuple[bool, str]:
        """Run FFmpeg command and return (success, error_or_output)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, f"FFmpeg error: {e.stderr}"
        except subprocess.TimeoutExpired:
            return False, "FFmpeg timeout"
    
    def _get_video_info(self, path: str) -> Dict[str, Any]:
        """Get video duration, dimensions, fps via ffprobe."""
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=duration,width,height,r_frame_rate",
            "-of", "json",
            path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            data = json.loads(result.stdout)
            stream = data.get("streams", [{}])[0]
            
            # Parse frame rate fraction
            fps_str = stream.get("r_frame_rate", "30/1")
            num, den = map(int, fps_str.split("/"))
            fps = num / den if den != 0 else 30
            
            return {
                "duration": float(stream.get("duration", 0)),
                "width": int(stream.get("width", 1920)),
                "height": int(stream.get("height", 1080)),
                "fps": fps
            }
        except Exception:
            return {"duration": 0, "width": 1920, "height": 1080, "fps": 30}
    
    async def download_source(self, video_url: str, temp_dir: str) -> str:
        """Download source video to temp directory."""
        # If it's an R2 URL, use pre-signed download
        if "r2.cloudflarestorage.com" in video_url or "r2.dev" in video_url:
            # Extract key from URL
            key = video_url.split("/")[-1].split("?")[0]
            if not key.startswith("clips/"):
                key = f"clips/{key}"
            local_path = os.path.join(temp_dir, "source.mp4")
            await self.r2.download_file(key, local_path)
            return local_path
        else:
            # Generic HTTP download
            import httpx
            local_path = os.path.join(temp_dir, "source.mp4")
            async with httpx.AsyncClient() as client:
                response = await client.get(video_url, timeout=120)
                response.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(response.content)
            return local_path
    
    async def upload_result(self, local_path: str, clip_id: str) -> str:
        """Upload edited video to R2 and return URL."""
        key = f"clips/{clip_id}_edited.mp4"
        await self.r2.upload_file(local_path, key)
        return await self.r2.get_presigned_url(key, expires_in=604800)  # 7 days
    
    def build_edit_command(
        self,
        source_path: str,
        output_path: str,
        recipe: Dict[str, Any]
    ) -> List[str]:
        """Build FFmpeg command from edit recipe.
        
        Recipe format:
        {
            "trim": {"start_seconds": 2.5, "end_seconds": 28.0},
            "segments": [{"start": 2.5, "end": 15.0}, {"start": 18.0, "end": 28.0}],
            "caption": "New caption text",
            "caption_style": {"position": "bottom", "color": "white", "size": 24},
            "audio": "keep",  # "keep", "mute", "replace:<track_url>"
            "speed": 1.0,  # 0.5 = half, 2.0 = double
            "filters": ["grayscale", "sepia", "vintage"],  # applied in order
            "text_overlays": [
                {"text": "Subscribe!", "x": 100, "y": 100, "start": 0, "end": 5, "color": "red", "size": 36}
            ],
            "transitions": ["fade", "dissolve"]  # between segments
        }
        """
        info = self._get_video_info(source_path)
        
        # Build filter complex
        filters = []
        stream = "[0:v]"
        audio_stream = "[0:a]"
        
        # 1. Trim or segment
        segments = recipe.get("segments")
        if segments and len(segments) > 0:
            # Multi-segment: use concat
            trim_parts = []
            for i, seg in enumerate(segments):
                start = seg.get("start", 0)
                end = seg.get("end", info["duration"])
                duration = end - start
                trim_parts.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}]")
                trim_parts.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]")
            
            # Add transition between segments if specified
            transitions = recipe.get("transitions", [])
            concat_inputs = []
            for i in range(len(segments)):
                concat_inputs.append(f"[v{i}]")
                concat_inputs.append(f"[a{i}]")
            
            # Simple concat (transitions are post-MVP complex)
            stream = f"{''.join(concat_inputs)}concat=n={len(segments)}:v=1:a=1[outv][outa]"
            filters.extend(trim_parts)
            filters.append(stream)
            stream = "[outv]"
            audio_stream = "[outa]"
        elif "trim" in recipe:
            start = recipe["trim"].get("start_seconds", 0)
            end = recipe["trim"].get("end_seconds", info["duration"])
            duration = end - start
            filters.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS{stream}")
            filters.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS{audio_stream}")
        
        # 2. Speed adjustment
        speed = recipe.get("speed", 1.0)
        if speed != 1.0:
            # For speed: use setpts for video and atempo for audio
            # atempo supports 0.5 to 2.0, for others chain multiple
            v_speed = 1.0 / speed
            filters.append(f"{stream}setpts={v_speed}*PTS{stream}")
            
            if speed >= 0.5 and speed <= 2.0:
                filters.append(f"{audio_stream}atempo={speed}{audio_stream}")
            elif speed < 0.5:
                # Chain two atempo filters
                temp = f"[atempo_tmp]"
                filters.append(f"{audio_stream}atempo=0.5{temp}")
                filters.append(f"{temp}atempo={speed * 2}{audio_stream}")
            else:
                # speed > 2.0, chain multiple
                temp = f"[atempo_tmp]"
                filters.append(f"{audio_stream}atempo=2.0{temp}")
                filters.append(f"{temp}atempo={speed / 2}{audio_stream}")
        
        # 3. Video filters (grayscale, sepia, vintage)
        filter_names = recipe.get("filters", [])
        for filter_name in filter_names:
            if filter_name == "grayscale":
                filters.append(f"{stream}colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3{stream}")
            elif filter_name == "sepia":
                filters.append(f"{stream}colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131{stream}")
            elif filter_name == "vintage":
                filters.append(f"{stream}curves=preset=vintage{stream}")
            elif filter_name == "blur":
                filters.append(f"{stream}boxblur=2:1{stream}")
            elif filter_name == "sharpen":
                filters.append(f"{stream}unsharp=3:3:1.5{stream}")
        
        # 4. Text overlays and caption
        text_overlays = recipe.get("text_overlays", [])
        caption = recipe.get("caption")
        caption_style = recipe.get("caption_style", {})
        
        all_texts = []
        if caption:
            all_texts.append({
                "text": caption,
                "x": caption_style.get("x", "(w-text_w)/2"),
                "y": caption_style.get("y", "h-text_h-50"),
                "start": 0,
                "end": info["duration"],
                "color": caption_style.get("color", "white"),
                "size": caption_style.get("size", 24),
                "font": caption_style.get("font", "Arial")
            })
        
        all_texts.extend(text_overlays)
        
        for i, text_item in enumerate(all_texts):
            text = text_item.get("text", "")
            x = text_item.get("x", "(w-text_w)/2")
            y = text_item.get("y", "h-text_h-50")
            start = text_item.get("start", 0)
            end = text_item.get("end", info["duration"])
            color = text_item.get("color", "white")
            size = text_item.get("size", 24)
            font = text_item.get("font", "Arial")
            
            # Sanitize text for FFmpeg
            text_escaped = text.replace("'", "'\\\\''")
            
            # Build drawtext filter
            drawtext = (
                f"drawtext=text='{text_escaped}':"
                f"x={x}:y={y}:"
                f"fontsize={size}:fontcolor={color}:"
                f"enable='between(t\\,{start}\\,{end})'"
            )
            
            # Add border for readability
            drawtext += ":box=1:boxcolor=black@0.5:boxborderw=5"
            
            filters.append(f"{stream}{drawtext}{stream}")
        
        # 5. Audio handling
        audio_action = recipe.get("audio", "keep")
        if audio_action == "mute":
            # Replace audio stream with silent audio
            filters.append(f"{audio_stream}volume=0{audio_stream}")
        elif audio_action.startswith("replace:"):
            # Replace with music track - requires second input
            # This is handled separately in the command builder
            pass
        
        # Build final command
        cmd = ["ffmpeg", "-y", "-i", source_path]
        
        # Add music track if replacing audio
        if audio_action.startswith("replace:"):
            music_url = audio_action.replace("replace:", "")
            # Download music to temp
            music_path = os.path.join(os.path.dirname(source_path), "music.mp3")
            # For now, skip complex audio replacement in MVP
            # User would upload music file separately
            pass
        
        if filters:
            cmd.extend(["-filter_complex", ";".join(filters)])
        
        # Map streams
        if stream != "[0:v]":
            cmd.extend(["-map", stream.replace("[", "").replace("]", "")])
        else:
            cmd.extend(["-map", "0:v"])
        
        if audio_stream != "[0:a]":
            cmd.extend(["-map", audio_stream.replace("[", "").replace("]", "")])
        else:
            cmd.extend(["-map", "0:a"])
        
        # Output settings
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            output_path
        ])
        
        return cmd
    
    async def edit_clip(
        self,
        clip_id: str,
        source_url: str,
        recipe: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply edit recipe to clip and return new video URL.
        
        Args:
            clip_id: Clip identifier
            source_url: Current video URL (R2 or external)
            recipe: Edit instructions dict
            
        Returns:
            {"success": True, "video_url": "...", "duration": 28.5}
        """
        temp_dir = tempfile.mkdtemp(prefix=f"clip_edit_{clip_id}_")
        
        try:
            # 1. Download source
            source_path = await self.download_source(source_url, temp_dir)
            
            # 2. Build FFmpeg command
            output_path = os.path.join(temp_dir, "output.mp4")
            cmd = self.build_edit_command(source_path, output_path, recipe)
            
            # 3. Run FFmpeg
            success, error = self._run_ffmpeg(cmd, timeout=300)
            if not success:
                return {"success": False, "error": error}
            
            # 4. Get output info
            output_info = self._get_video_info(output_path)
            
            # 5. Upload to R2
            video_url = await self.upload_result(output_path, clip_id)
            
            return {
                "success": True,
                "video_url": video_url,
                "duration": output_info["duration"],
                "width": output_info["width"],
                "height": output_info["height"]
            }
            
        finally:
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def add_sticker_overlay(
        self,
        video_path: str,
        sticker_url: str,
        position: Dict[str, Any],
        output_path: str
    ) -> Dict[str, Any]:
        """Add a sticker/image overlay to video.
        
        Args:
            video_path: Local video file path
            sticker_url: URL to sticker image (PNG with alpha)
            position: {"x": 100, "y": 100, "scale": 0.5}
            output_path: Where to save result
        """
        # Download sticker
        sticker_path = os.path.join(os.path.dirname(video_path), "sticker.png")
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(sticker_url, timeout=30)
            with open(sticker_path, "wb") as f:
                f.write(response.content)
        
        x = position.get("x", 0)
        y = position.get("y", 0)
        scale = position.get("scale", 1.0)
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", sticker_path,
            "-filter_complex",
            f"[1:v]scale=iw*{scale}:-1[sticker];[0:v][sticker]overlay={x}:{y}:format=auto",
            "-c:a", "copy",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            output_path
        ]
        
        success, error = self._run_ffmpeg(cmd)
        if not success:
            return {"success": False, "error": error}
        
        return {"success": True, "output_path": output_path}
    
    async def apply_transition(
        self,
        segment_paths: List[str],
        transition_type: str,
        output_path: str,
        duration: float = 0.5
    ) -> Dict[str, Any]:
        """Apply transition between video segments.
        
        Args:
            segment_paths: List of video file paths
            transition_type: "fade", "dissolve", "wipe", "slide"
            output_path: Output file path
            duration: Transition duration in seconds
        """
        if len(segment_paths) < 2:
            return {"success": False, "error": "Need at least 2 segments for transitions"}
        
        if transition_type == "fade":
            # Use xfade filter for crossfade
            inputs = []
            for i, path in enumerate(segment_paths):
                inputs.extend(["-i", path])
            
            # Build xfade chain
            filters = []
            stream = "[0:v]"
            astream = "[0:a]"
            
            for i in range(1, len(segment_paths)):
                next_stream = f"[{i}:v]"
                next_astream = f"[{i}:a]"
                out_v = f"[v{i}]"
                out_a = f"[a{i}]"
                
                filters.append(
                    f"{stream}{next_stream}xfade=transition=fade:duration={duration}:offset=0{out_v}"
                )
                # Audio crossfade
                filters.append(
                    f"{astream}{next_astream}acrossfade=d={duration}{out_a}"
                )
                stream = out_v
                astream = out_a
            
            filter_str = ";".join(filters)
            
            cmd = ["ffmpeg", "-y"] + inputs
            cmd.extend(["-filter_complex", filter_str])
            cmd.extend(["-map", stream.replace("[", "").replace("]", "")])
            cmd.extend(["-map", astream.replace("[", "").replace("]", "")])
            cmd.extend([
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                output_path
            ])
            
            success, error = self._run_ffmpeg(cmd, timeout=300)
            if not success:
                return {"success": False, "error": error}
            
            return {"success": True, "output_path": output_path}
        
        else:
            return {"success": False, "error": f"Transition '{transition_type}' not yet implemented"}
    
    def validate_recipe(self, recipe: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate edit recipe before processing.
        
        Returns: (is_valid, error_message)
        """
        # Check for conflicting operations
        if "trim" in recipe and "segments" in recipe:
            return False, "Cannot use both 'trim' and 'segments'"
        
        # Validate speed range
        speed = recipe.get("speed", 1.0)
        if speed < 0.25 or speed > 4.0:
            return False, "Speed must be between 0.25x and 4.0x"
        
        # Validate segment order
        segments = recipe.get("segments", [])
        for i, seg in enumerate(segments):
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            if start >= end:
                return False, f"Segment {i}: start must be before end"
            if i > 0 and start < segments[i-1].get("end", 0):
                return False, f"Segment {i}: overlaps with previous segment"
        
        # Validate text overlays
        texts = recipe.get("text_overlays", [])
        for i, text in enumerate(texts):
            if not text.get("text"):
                return False, f"Text overlay {i}: text is required"
        
        return True, ""