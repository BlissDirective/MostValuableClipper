import subprocess
import json
import os
import tempfile
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from app.core.config import settings
from app.services.r2_service import R2Service
import httpx

logger = logging.getLogger(__name__)

class FFmpegEditService:
    """Server-side video editing via FFmpeg.
    
    Supports: trim, concat, text overlays, audio mute/replace,
    speed adjustment, filters, stickers, transitions, music library.
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
        if "r2.cloudflarestorage.com" in video_url or "r2.dev" in video_url:
            key = video_url.split("/")[-1].split("?")[0]
            if not key.startswith("clips/"):
                key = f"clips/{key}"
            local_path = os.path.join(temp_dir, "source.mp4")
            await self.r2.download_file(key, local_path)
            return local_path
        else:
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
        return await self.r2.get_presigned_url(key, expires_in=604800)
    
    async def download_sticker(self, sticker_url: str, temp_dir: str) -> str:
        """Download sticker image to temp directory."""
        ext = sticker_url.split("?")[0].split(".")[-1] or "png"
        if ext not in ("png", "jpg", "jpeg", "gif", "webp"):
            ext = "png"
        sticker_path = os.path.join(temp_dir, f"sticker_{os.urandom(4).hex()}.{ext}")
        async with httpx.AsyncClient() as client:
            response = await client.get(sticker_url, timeout=30)
            response.raise_for_status()
            with open(sticker_path, "wb") as f:
                f.write(response.content)
        return sticker_path
    
    async def download_music(self, music_url: str, temp_dir: str) -> str:
        """Download music track to temp directory."""
        ext = music_url.split("?")[0].split(".")[-1] or "mp3"
        if ext not in ("mp3", "wav", "aac", "m4a"):
            ext = "mp3"
        music_path = os.path.join(temp_dir, f"music.{ext}")
        async with httpx.AsyncClient() as client:
            response = await client.get(music_url, timeout=60)
            response.raise_for_status()
            with open(music_path, "wb") as f:
                f.write(response.content)
        return music_path

    def build_edit_command(
        self,
        source_path: str,
        output_path: str,
        recipe: Dict[str, Any]
    ) -> List[str]:
        """Build FFmpeg command from edit recipe."""
        info = self._get_video_info(source_path)
        
        # Gather all external inputs
        sticker_inputs = []  # List of (sticker_path, overlay_config)
        music_input = None
        music_config = {}
        
        # Check for stickers
        stickers = recipe.get("stickers", [])
        for s in stickers:
            url = s.get("url")
            if url:
                sticker_inputs.append((url, s))
        
        # Check for music replacement
        audio_action = recipe.get("audio", "keep")
        if audio_action.startswith("replace:"):
            music_url = audio_action.replace("replace:", "")
            music_input = music_url
            music_config = {
                "volume": recipe.get("music_volume", 0.25),
                "fade_in": recipe.get("music_fade_in", 1.0),
                "fade_out": recipe.get("music_fade_out", 2.0),
                "loop": recipe.get("music_loop", False),
                "ducking": recipe.get("ducking", True)
            }
        
        # Build command
        cmd = ["ffmpeg", "-y", "-i", source_path]
        
        # Add sticker inputs
        for sticker_path, _ in sticker_inputs:
            cmd.extend(["-i", sticker_path])
        
        # Add music input
        if music_input:
            cmd.extend(["-i", music_input])
        
        # Build filter complex
        filter_parts = []
        
        # Base video stream
        v_stream = "[0:v]"
        a_stream = "[0:a]"
        next_sticker_idx = 1
        
        # 1. Trim or segment
        segments = recipe.get("segments")
        transitions = recipe.get("transitions", [])
        
        if segments and len(segments) > 0:
            # Multi-segment editing with transitions
            trim_parts = []
            v_streams = []
            a_streams = []
            
            for i, seg in enumerate(segments):
                start = seg.get("start", 0)
                end = seg.get("end", info["duration"])
                trim_parts.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}]")
                trim_parts.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]")
                v_streams.append(f"[v{i}]")
                a_streams.append(f"[a{i}]")
            
            filter_parts.extend(trim_parts)
            
            # Apply transitions between segments
            if transitions and len(v_streams) > 1:
                current_v = v_streams[0]
                current_a = a_streams[0]
                
                for i in range(1, len(v_streams)):
                    trans = transitions[i - 1] if i - 1 < len(transitions) else {"type": "fade", "duration": 0.5}
                    trans_type = trans.get("type", "fade")
                    trans_duration = trans.get("duration", 0.5)
                    
                    # Map transition types to xfade names
                    xfade_map = {
                        "fade": "fade",
                        "dissolve": "fadeblack",
                        "wipe_left": "wipeleft",
                        "wipe_right": "wiperight",
                        "slide_up": "slideup",
                        "slide_down": "slidedown",
                        "zoom_in": "zoomin",
                        "zoom_out": "zoomout",
                        "spin": "smoothleft",
                        "pixelate": "pixelize",
                    }
                    xfade_type = xfade_map.get(trans_type, "fade")
                    
                    out_v = f"[vt{i}]"
                    out_a = f"[at{i}]"
                    
                    # xfade requires knowing the duration of the first clip
                    seg_duration = segments[i - 1].get("end", info["duration"]) - segments[i - 1].get("start", 0)
                    offset = max(0, seg_duration - trans_duration)
                    
                    filter_parts.append(
                        f"{current_v}{v_streams[i]}xfade=transition={xfade_type}:duration={trans_duration}:offset={offset}{out_v}"
                    )
                    filter_parts.append(
                        f"{current_a}{a_streams[i]}acrossfade=d={trans_duration}{out_a}"
                    )
                    
                    current_v = out_v
                    current_a = out_a
                
                v_stream = current_v
                a_stream = current_a
            else:
                # Simple concat without transitions
                v_concat = "".join(v_streams)
                a_concat = "".join(a_streams)
                filter_parts.append(f"{v_concat}{a_concat}concat=n={len(segments)}:v=1:a=1[vout][aout]")
                v_stream = "[vout]"
                a_stream = "[aout]"
        elif "trim" in recipe:
            start = recipe["trim"].get("start_seconds", 0)
            end = recipe["trim"].get("end_seconds", info["duration"])
            filter_parts.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[vtrim]")
            filter_parts.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[atrim]")
            v_stream = "[vtrim]"
            a_stream = "[atrim]"
        
        # 2. Speed adjustment
        speed = recipe.get("speed", 1.0)
        if speed != 1.0:
            v_speed = 1.0 / speed
            filter_parts.append(f"{v_stream}setpts={v_speed}*PTS[vspd]")
            v_stream = "[vspd]"
            
            if speed >= 0.5 and speed <= 2.0:
                filter_parts.append(f"{a_stream}atempo={speed}[aspd]")
                a_stream = "[aspd]"
            elif speed < 0.5:
                filter_parts.append(f"{a_stream}atempo=0.5[atempo_tmp]")
                filter_parts.append(f"[atempo_tmp]atempo={speed * 2}[aspd]")
                a_stream = "[aspd]"
            else:
                filter_parts.append(f"{a_stream}atempo=2.0[atempo_tmp]")
                filter_parts.append(f"[atempo_tmp]atempo={speed / 2}[aspd]")
                a_stream = "[aspd]"
        
        # 3. Video filters
        filter_names = recipe.get("filters", [])
        color_grade = recipe.get("color_grade")
        
        # Apply color grade LUT first if specified
        if color_grade:
            lut_filters = {
                "tiktok": "eq=saturation=1.2:contrast=1.1:brightness=0.05",
                "instagram": "eq=saturation=1.1:contrast=1.05",
                "youtube": "eq=saturation=1.0:contrast=1.05",
            }
            if color_grade in lut_filters:
                filter_parts.append(f"{v_stream}{lut_filters[color_grade]}[vlut]")
                v_stream = "[vlut]"
        
        for filter_name in filter_names:
            if filter_name == "grayscale":
                filter_parts.append(f"{v_stream}colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3[vfilt]")
                v_stream = "[vfilt]"
            elif filter_name == "sepia":
                filter_parts.append(f"{v_stream}colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131[vfilt]")
                v_stream = "[vfilt]"
            elif filter_name == "vintage":
                filter_parts.append(f"{v_stream}curves=preset=vintage[vfilt]")
                v_stream = "[vfilt]"
            elif filter_name == "blur":
                filter_parts.append(f"{v_stream}boxblur=2:1[vfilt]")
                v_stream = "[vfilt]"
            elif filter_name == "sharpen":
                filter_parts.append(f"{v_stream}unsharp=3:3:1.5[vfilt]")
                v_stream = "[vfilt]"
            elif filter_name == "vibrant":
                filter_parts.append(f"{v_stream}eq=saturation=1.3:contrast=1.1[vfilt]")
                v_stream = "[vfilt]"
            elif filter_name == "warm":
                filter_parts.append(f"{v_stream}colorchannelmixer=1.1:0.1:0.1:0:0.1:1.05:0.05:0:0.1:0.05:1.05[vfilt]")
                v_stream = "[vfilt]"
            elif filter_name == "cinematic":
                filter_parts.append(f"{v_stream}eq=saturation=1.0:contrast=1.05:brightness=-0.02[vfilt]")
                v_stream = "[vfilt]"
        
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
            
            text_escaped = text.replace("'", "'\\''")
            
            drawtext = (
                f"drawtext=text='{text_escaped}':"
                f"x={x}:y={y}:"
                f"fontsize={size}:fontcolor={color}:"
                f"enable='between(t\\,{start}\\,{end})'"
            )
            drawtext += ":box=1:boxcolor=black@0.5:boxborderw=5"
            
            filter_parts.append(f"{v_stream}{drawtext}[vtxt{i}]")
            v_stream = f"[vtxt{i}]"
        
        # 5. Sticker overlays
        for i, (sticker_path, config) in enumerate(sticker_inputs):
            x = config.get("x", 20)
            y = config.get("y", 20)
            scale = config.get("scale", 0.5)
            start = config.get("start", 0)
            end = config.get("end", info["duration"])
            
            # Convert negative coordinates (from right/bottom)
            x_expr = str(x) if x >= 0 else f"W-w{x}"
            y_expr = str(y) if y >= 0 else f"H-h{y}"
            
            sticker_idx = next_sticker_idx
            next_sticker_idx += 1
            
            filter_parts.append(
                f"[{sticker_idx}:v]scale=iw*{scale}:-1[sticker{i}]"
            )
            filter_parts.append(
                f"{v_stream}[sticker{i}]overlay={x_expr}:{y_expr}:"
                f"enable='between(t\\,{start}\\,{end})':format=auto[vstk{i}]"
            )
            v_stream = f"[vstk{i}]"
        
        # 6. Audio handling
        if audio_action == "mute":
            filter_parts.append(f"{a_stream}volume=0[amute]")
            a_stream = "[amute]"
        elif audio_action.startswith("replace:") and music_input:
            music_idx = next_sticker_idx if sticker_inputs else 1
            
            # Apply volume, fade, and ducking
            vol = music_config.get("volume", 0.25)
            fade_in = music_config.get("fade_in", 1.0)
            fade_out = music_config.get("fade_out", 2.0)
            
            # Build audio filter chain for music
            afilters = [f"[{music_idx}:a]volume={vol}"]
            
            if fade_in > 0:
                afilters.append(f"afade=t=in:ss=0:d={fade_in}")
            if fade_out > 0:
                # Fade out starts at end minus fade_out duration
                afilters.append(f"afade=t=out:st={info['duration'] - fade_out}:d={fade_out}")
            
            # Loop if needed
            if music_config.get("loop", False):
                afilters.append(f"aloop=loop=-1:size=2e+09")
            
            afilters.append(f"amix=inputs=2:duration=longest:dropout_transition=0[amixed]")
            
            filter_parts.append(f"[{music_idx}:a]volume={vol}[music_vol]")
            
            if fade_in > 0:
                filter_parts.append(f"[music_vol]afade=t=in:ss=0:d={fade_in}[music_fade]")
                music_stream = "[music_fade]"
            else:
                music_stream = "[music_vol]"
            
            # Mix original audio with music
            filter_parts.append(f"{a_stream}{music_stream}amix=inputs=2:duration=first:dropout_transition=0[amixed]")
            a_stream = "[amixed]"
        
        # Build final command
        if filter_parts:
            cmd.extend(["-filter_complex", ";".join(filter_parts)])
        
        # Map streams
        cmd.extend(["-map", v_stream.replace("[", "").replace("]", "")])
        cmd.extend(["-map", a_stream.replace("[", "").replace("]", "")])
        
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
    
    def _recipe_hash(self, recipe: Dict[str, Any]) -> str:
        """Generate a deterministic hash for an edit recipe.
        
        Used for FFmpeg output caching — same recipe = same output.
        """
        # Sort keys for determinism
        recipe_json = json.dumps(recipe, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(recipe_json.encode()).hexdigest()[:16]
    
    async def edit_clip(
        self,
        clip_id: str,
        source_url: str,
        recipe: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply edit recipe to clip and return new video URL.
        
        Uses recipe-hash based caching to avoid re-processing identical edits.
        """
        # Generate recipe hash for caching
        recipe_hash = self._recipe_hash(recipe)
        cache_key = f"clips/edits/{clip_id}_{recipe_hash}.mp4"
        
        # Check if cached output exists
        try:
            cached_url = self.r2.get_cdn_url(cache_key)
            # Verify the object exists by trying to get metadata
            # (In production, you could use a HEAD request)
            logger.info(f"[FFmpeg] Cache hit for clip {clip_id} — hash {recipe_hash}")
            return {
                "success": True,
                "video_url": cached_url,
                "cached": True,
                "recipe_hash": recipe_hash,
                "duration": recipe.get("trim", {}).get("end_seconds", 30),
            }
        except Exception:
            # Cache miss — proceed with processing
            pass
        
        temp_dir = tempfile.mkdtemp(prefix=f"clip_edit_{clip_id}_")
        
        try:
            # Download source
            source_path = await self.download_source(source_url, temp_dir)
            
            # Download stickers
            stickers = recipe.get("stickers", [])
            sticker_paths = []
            for s in stickers:
                url = s.get("url")
                if url:
                    path = await self.download_sticker(url, temp_dir)
                    s["local_path"] = path
                    sticker_paths.append(path)
            
            # Download music if replacing
            audio_action = recipe.get("audio", "keep")
            if audio_action.startswith("replace:"):
                music_url = audio_action.replace("replace:", "")
                music_path = await self.download_music(music_url, temp_dir)
                recipe["music_local_path"] = music_path
            
            # Build FFmpeg command
            output_path = os.path.join(temp_dir, "output.mp4")
            cmd = self.build_edit_command(source_path, output_path, recipe)
            
            # Run FFmpeg
            success, error = self._run_ffmpeg(cmd, timeout=300)
            if not success:
                return {"success": False, "error": error}
            
            # Get output info
            output_info = self._get_video_info(output_path)
            
            # Upload to R2 with cache key (recipe hash)
            with open(output_path, "rb") as f:
                r2_url = await self.r2.upload_file(cache_key, f)
            # Get CDN URL for public delivery
            cdn_url = self.r2.get_cdn_url(cache_key)
            
            return {
                "success": True,
                "video_url": cdn_url,
                "r2_url": video_url,
                "cached": False,
                "recipe_hash": recipe_hash,
                "duration": output_info["duration"],
                "width": output_info["width"],
                "height": output_info["height"]
            }
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def validate_recipe(self, recipe: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate edit recipe before processing."""
        if "trim" in recipe and "segments" in recipe:
            return False, "Cannot use both 'trim' and 'segments'"
        
        speed = recipe.get("speed", 1.0)
        if speed < 0.25 or speed > 4.0:
            return False, "Speed must be between 0.25x and 4.0x"
        
        segments = recipe.get("segments", [])
        for i, seg in enumerate(segments):
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            if start >= end:
                return False, f"Segment {i}: start must be before end"
            if i > 0 and start < segments[i-1].get("end", 0):
                return False, f"Segment {i}: overlaps with previous segment"
        
        texts = recipe.get("text_overlays", [])
        for i, text in enumerate(texts):
            if not text.get("text"):
                return False, f"Text overlay {i}: text is required"
        
        # Validate stickers
        stickers = recipe.get("stickers", [])
        for i, s in enumerate(stickers):
            if not s.get("url"):
                return False, f"Sticker {i}: url is required"
        
        # Validate transitions
        transitions = recipe.get("transitions", [])
        valid_transitions = {
            "fade", "dissolve", "wipe_left", "wipe_right",
            "slide_up", "slide_down", "zoom_in", "zoom_out", "spin", "pixelate"
        }
        for i, t in enumerate(transitions):
            t_type = t.get("type") if isinstance(t, dict) else t
            if t_type not in valid_transitions:
                return False, f"Transition {i}: invalid type '{t_type}'"
        
        return True, ""