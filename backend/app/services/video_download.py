import os
import subprocess
import tempfile
from typing import Optional, Dict, Any, List
import httpx
from pathlib import Path

class VideoDownloadService:
    """Download videos from various sources (YouTube, RSS, Twitch, direct URLs)."""
    
    async def download_from_youtube(self, video_url: str, output_path: str) -> str:
        """Download a YouTube video using yt-dlp."""
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "-f", "best[height<=720]",  # 720p max for processing speed
                    "--no-playlist",
                    "-o", output_path,
                    video_url
                ],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise Exception(f"yt-dlp failed: {result.stderr}")
            
            return output_path
        except FileNotFoundError:
            raise Exception("yt-dlp not installed. Install with: pip install yt-dlp")
    
    async def download_from_url(self, video_url: str, output_path: str) -> str:
        """Download a video from a direct URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(video_url, follow_redirects=True, timeout=120)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            return output_path
    
    async def extract_audio(self, video_path: str, output_path: str) -> str:
        """Extract audio track from video using ffmpeg."""
        result = subprocess.run(
            [
                "ffmpeg",
                "-i", video_path,
                "-vn",  # No video
                "-acodec", "pcm_s16le",  # PCM 16-bit little-endian
                "-ar", "16000",  # 16kHz (Whisper optimal)
                "-ac", "1",  # Mono
                "-y",  # Overwrite output
                output_path
            ],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            raise Exception(f"ffmpeg audio extraction failed: {result.stderr}")
        
        return output_path
    
    def get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds using ffprobe."""
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                video_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise Exception(f"ffprobe failed: {result.stderr}")
        
        import json
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
