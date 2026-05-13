import os
import subprocess
import tempfile
from typing import Dict, Any, List, Optional
from pathlib import Path

class ClipGenerationService:
    """Generate short-form video clips from long-form content using ffmpeg."""
    
    async def generate_clip(
        self,
        source_video: str,
        output_path: str,
        start_time: float,
        end_time: float,
        target_aspect_ratio: str = "9:16",  # Default: vertical (TikTok/Reels)
        target_resolution: str = "1080x1920",
        add_captions: bool = True,
        caption_text: str = ""
    ) -> str:
        """Generate a clip from a video segment."""
        duration = end_time - start_time
        
        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-i", source_video,
            "-ss", str(start_time),
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-y"
        ]
        
        # Apply aspect ratio crop/pad
        if target_aspect_ratio == "9:16":
            # Vertical: crop sides or pad top/bottom
            cmd.extend([
                "-vf", f"crop='ih*9/16:ih',scale={target_resolution}:force_original_aspect_ratio=decrease,pad={target_resolution}:(ow-iw)/2:(oh-ih)/2:black"
            ])
        elif target_aspect_ratio == "1:1":
            # Square
            cmd.extend([
                "-vf", f"crop='min(iw,ih):min(iw,ih)',scale={target_resolution}:force_original_aspect_ratio=decrease,pad={target_resolution}:(ow-iw)/2:(oh-ih)/2:black"
            ])
        elif target_aspect_ratio == "16:9":
            # Horizontal
            cmd.extend([
                "-vf", f"crop='iw:iw*9/16',scale={target_resolution}:force_original_aspect_ratio=decrease,pad={target_resolution}:(ow-iw)/2:(oh-ih)/2:black"
            ])
        
        cmd.append(output_path)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise Exception(f"ffmpeg clip generation failed: {result.stderr}")
        
        return output_path
    
    async def add_subtitles(
        self,
        video_path: str,
        output_path: str,
        segments: List[Dict[str, Any]]
    ) -> str:
        """Add burned-in subtitles to video."""
        # Generate SRT file
        srt_path = video_path.replace(".mp4", ".srt")
        
        with open(srt_path, "w") as f:
            for i, seg in enumerate(segments):
                start = self._format_time(seg["start"])
                end = self._format_time(seg["end"])
                text = seg.get("text", "").strip()
                
                f.write(f"{i+1}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")
        
        # Burn subtitles into video
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"subtitles={srt_path}:force_style='FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2'",
            "-c:a", "copy",
            "-y",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        # Clean up SRT
        os.remove(srt_path)
        
        if result.returncode != 0:
            raise Exception(f"ffmpeg subtitle burn failed: {result.stderr}")
        
        return output_path
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds to SRT time format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    async def add_background_music(
        self,
        video_path: str,
        output_path: str,
        music_path: Optional[str] = None,
        volume: float = 0.15
    ) -> str:
        """Add background music to video."""
        if not music_path or not os.path.exists(music_path):
            # No music provided, return original
            return video_path
        
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex",
            f"[0:a]volume=1.0[a0];[1:a]volume={volume}[a1];[a0][a1]amix=inputs=2:duration=first[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-y",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            raise Exception(f"ffmpeg music add failed: {result.stderr}")
        
        return output_path

class ThumbnailService:
    """Generate thumbnails for video clips."""
    
    async def generate_thumbnail(
        self,
        video_path: str,
        output_path: str,
        timestamp: Optional[float] = None
    ) -> str:
        """Generate a thumbnail from a video frame."""
        # Use middle of video if no timestamp specified
        if timestamp is None:
            # Get duration
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                capture_output=True, text=True, timeout=30
            )
            duration = float(result.stdout.strip())
            timestamp = duration / 2
        
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-ss", str(timestamp),
            "-vframes", "1",
            "-q:v", "2",
            "-y",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            raise Exception(f"ffmpeg thumbnail failed: {result.stderr}")
        
        return output_path
    
    async def generate_thumbnail_with_text(
        self,
        video_path: str,
        output_path: str,
        title: str,
        timestamp: Optional[float] = None
    ) -> str:
        """Generate a thumbnail with overlaid title text."""
        # First generate base thumbnail
        base_path = output_path.replace(".jpg", "_base.jpg")
        await self.generate_thumbnail(video_path, base_path, timestamp)
        
        # Add text overlay using ImageMagick or ffmpeg drawtext
        cmd = [
            "ffmpeg",
            "-i", base_path,
            "-vf",
            f"drawtext=text='{title}':fontcolor=white:fontsize=48:box=1:boxcolor=black@0.5:boxborderw=10:x=(w-text_w)/2:y=(h-text_h)/2",
            "-y",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Clean up base
        os.remove(base_path)
        
        if result.returncode != 0:
            raise Exception(f"ffmpeg text overlay failed: {result.stderr}")
        
        return output_path
