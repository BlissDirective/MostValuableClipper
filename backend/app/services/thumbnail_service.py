import subprocess
import os
import tempfile
from typing import List, Dict, Any, Tuple
from pathlib import Path
from app.services.r2_service import R2Service

class ThumbnailService:
    """Generate thumbnail frames from video clips for timeline scrubber."""
    
    def __init__(self):
        self.r2 = R2Service()
    
    def _run_ffmpeg(self, cmd: List[str], timeout: int = 60) -> Tuple[bool, str]:
        """Run FFmpeg command."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, f"FFmpeg error: {e.stderr}"
        except subprocess.TimeoutExpired:
            return False, "FFmpeg timeout"
    
    async def generate_thumbnails(
        self,
        clip_id: str,
        video_url: str,
        count: int = 20,
        width: int = 120,
        height: int = 68
    ) -> Dict[str, Any]:
        """Generate evenly spaced thumbnail frames from a video.
        
        Args:
            clip_id: Clip identifier
            video_url: Source video URL
            count: Number of thumbnails to generate (default 20)
            width: Thumbnail width in pixels
            height: Thumbnail height in pixels
            
        Returns:
            {"success": True, "thumbnails": [{"time": 0.5, "url": "..."}, ...]}
        """
        temp_dir = tempfile.mkdtemp(prefix=f"thumbs_{clip_id}_")
        
        try:
            # Download video
            local_path = os.path.join(temp_dir, "source.mp4")
            
            if "r2.cloudflarestorage.com" in video_url or "r2.dev" in video_url:
                key = video_url.split("/")[-1].split("?")[0]
                if not key.startswith("clips/"):
                    key = f"clips/{key}"
                await self.r2.download_file(key, local_path)
            else:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(video_url, timeout=120)
                    with open(local_path, "wb") as f:
                        f.write(response.content)
            
            # Get video duration using ffprobe
            duration_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                local_path
            ]
            result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=30)
            duration_data = __import__('json').loads(result.stdout)
            duration = float(duration_data.get("format", {}).get("duration", 0))
            
            if duration == 0:
                return {"success": False, "error": "Could not determine video duration"}
            
            # Generate thumbnails at evenly spaced intervals
            thumbnails = []
            interval = duration / (count + 1)  # +1 to avoid first/last frame edge cases
            
            for i in range(count):
                timestamp = interval * (i + 1)
                thumb_filename = f"thumb_{i:03d}.jpg"
                thumb_path = os.path.join(temp_dir, thumb_filename)
                
                # Extract frame at timestamp
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(timestamp),
                    "-i", local_path,
                    "-vframes", "1",
                    "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
                    "-q:v", "2",
                    thumb_path
                ]
                
                success, error = self._run_ffmpeg(cmd, timeout=30)
                if not success:
                    continue
                
                # Upload thumbnail to R2
                r2_key = f"thumbnails/{clip_id}/{thumb_filename}"
                await self.r2.upload_file(thumb_path, r2_key)
                thumb_url = await self.r2.get_presigned_url(r2_key, expires_in=604800)
                
                thumbnails.append({
                    "time": round(timestamp, 2),
                    "url": thumb_url
                })
            
            return {
                "success": True,
                "thumbnails": thumbnails,
                "duration": round(duration, 2),
                "count": len(thumbnails)
            }
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def get_or_create_thumbnails(
        self,
        clip_id: str,
        video_url: str,
        count: int = 20
    ) -> Dict[str, Any]:
        """Get thumbnails from cache or generate new ones."""
        # Check if thumbnails already exist in R2
        r2_key = f"thumbnails/{clip_id}/thumb_000.jpg"
        try:
            # Try to get existing thumbnails
            thumbs = []
            for i in range(count):
                key = f"thumbnails/{clip_id}/thumb_{i:03d}.jpg"
                url = await self.r2.get_presigned_url(key, expires_in=604800)
                if url:
                    thumbs.append({"time": i, "url": url})
            
            if len(thumbs) >= count // 2:  # If we have most thumbnails, use cached
                return {"success": True, "thumbnails": thumbs, "cached": True}
        except Exception:
            pass
        
        # Generate new thumbnails
        return await self.generate_thumbnails(clip_id, video_url, count)
