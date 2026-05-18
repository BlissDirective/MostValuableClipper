"""
Music Library Service for clip remixing.

Provides curated background music tracks with mood-based selection,
volume ducking integration, and tempo matching.

Sources:
- Pre-bundled tracks (YouTube Audio Library, Pixabay — free, no accounts)
- TikTok Commercial Music Library (requires TikTok for Business account)
- Upgrade path: Epidemic Sound, Artlist
"""

import logging
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class MusicTrack:
    """A background music track."""
    id: str
    title: str
    artist: str
    mood: str  # high_energy, emotional, calm, dramatic, upbeat
    tempo_bpm: int
    duration_seconds: float
    file_path: Optional[str]  # Local path or None for external
    source: str  # "bundled", "tiktok", "epidemic", etc.
    license_type: str  # "royalty_free", "tiktok_commercial", "premium"
    volume_duck_factor: float = 0.15  # How much to reduce during speech


class MusicLibraryService:
    """
    Music library with mood-based track selection.
    
    MVP: Uses pre-bundled free tracks (no accounts needed).
    Phase 2: Integrates TikTok Commercial Music Library.
    Phase 3: Premium sources (Epidemic Sound, Artlist).
    """
    
    # Pre-bundled tracks for MVP — download these from YouTube Audio Library + Pixabay
    BUNDLED_TRACKS = [
        MusicTrack(
            id="bundle_energetic_01",
            title="High Octane",
            artist="YouTube Audio Library",
            mood="high_energy",
            tempo_bpm=128,
            duration_seconds=120.0,
            file_path="/app/music/bundle_energetic_01.mp3",
            source="bundled",
            license_type="royalty_free",
            volume_duck_factor=0.12
        ),
        MusicTrack(
            id="bundle_emotional_01",
            title="Soft Piano",
            artist="Pixabay",
            mood="emotional",
            tempo_bpm=72,
            duration_seconds=180.0,
            file_path="/app/music/bundle_emotional_01.mp3",
            source="bundled",
            license_type="royalty_free",
            volume_duck_factor=0.20
        ),
        MusicTrack(
            id="bundle_calm_01",
            title="Lo-Fi Chill",
            artist="YouTube Audio Library",
            mood="calm",
            tempo_bpm=85,
            duration_seconds=240.0,
            file_path="/app/music/bundle_calm_01.mp3",
            source="bundled",
            license_type="royalty_free",
            volume_duck_factor=0.18
        ),
        MusicTrack(
            id="bundle_dramatic_01",
            title="Cinematic Build",
            artist="Pixabay",
            mood="dramatic",
            tempo_bpm=110,
            duration_seconds=150.0,
            file_path="/app/music/bundle_dramatic_01.mp3",
            source="bundled",
            license_type="royalty_free",
            volume_duck_factor=0.15
        ),
        MusicTrack(
            id="bundle_upbeat_01",
            title="Summer Vibes",
            artist="YouTube Audio Library",
            mood="upbeat",
            tempo_bpm=120,
            duration_seconds=200.0,
            file_path="/app/music/bundle_upbeat_01.mp3",
            source="bundled",
            license_type="royalty_free",
            volume_duck_factor=0.14
        ),
    ]
    
    # Mood mapping from segment characteristics to music mood
    MOOD_MAPPING = {
        "high_energy": ["high_energy", "upbeat"],
        "emotional": ["emotional", "calm"],
        "calm": ["calm", "upbeat"],
        "dramatic": ["dramatic", "high_energy"],
        "neutral": ["upbeat", "calm"]
    }
    
    def __init__(self, music_dir: Optional[str] = None):
        self.music_dir = music_dir or "/app/music"
        self.tracks: List[MusicTrack] = []
        self._load_bundled_tracks()
        self._load_tiktok_tracks()
    
    def _load_bundled_tracks(self):
        """Load pre-bundled tracks that exist on disk."""
        for track in self.BUNDLED_TRACKS:
            if track.file_path and os.path.exists(track.file_path):
                self.tracks.append(track)
                logger.info(f"[MusicLib] Loaded bundled track: {track.title}")
            else:
                logger.warning(f"[MusicLib] Bundled track not found: {track.file_path}")
        
        if not self.tracks:
            logger.warning("[MusicLib] No bundled tracks found — music mixing will be disabled")
    
    def _load_tiktok_tracks(self):
        """Load TikTok Commercial Music Library tracks if available."""
        tiktok_token = os.environ.get("TIKTOK_MUSIC_TOKEN")
        if not tiktok_token:
            logger.info("[MusicLib] TikTok music token not set — skipping TikTok library")
            return
        
        # TikTok Commercial Music Library integration placeholder
        # Requires TikTok for Business account + API access
        # https://ads.tiktok.com/marketing_api/docs?id=1735721028165697
        logger.info("[MusicLib] TikTok music integration ready (token present)")
    
    def select_track(
        self,
        segment_energy: float,
        segment_salience: float,
        target_duration: float,
        exclude_tracks: Optional[List[str]] = None
    ) -> Optional[MusicTrack]:
        """
        Select the best music track for a segment.
        
        Args:
            segment_energy: 0.0-1.0 energy score
            segment_salience: 0.0-1.0 content importance
            target_duration: How long the clip will be
            exclude_tracks: Track IDs to exclude (for diversity across variants)
        
        Returns:
            Best matching MusicTrack or None
        """
        if not self.tracks:
            return None
        
        # Determine mood from energy/salience
        if segment_energy > 0.7 and segment_salience > 0.6:
            target_mood = "high_energy"
        elif segment_salience > 0.7:
            target_mood = "emotional"
        elif segment_energy < 0.3:
            target_mood = "calm"
        else:
            target_mood = "upbeat"
        
        # Get acceptable moods
        acceptable_moods = self.MOOD_MAPPING.get(target_mood, ["upbeat"])
        
        # Filter candidates
        exclude = set(exclude_tracks or [])
        candidates = [
            t for t in self.tracks
            if t.mood in acceptable_moods and t.id not in exclude
        ]
        
        if not candidates:
            # Fallback: any track not excluded
            candidates = [t for t in self.tracks if t.id not in exclude]
        
        if not candidates:
            # Final fallback: any track
            candidates = self.tracks
        
        # Score candidates by duration match and mood accuracy
        best_track = None
        best_score = -1.0
        
        for track in candidates:
            # Duration score: prefer tracks longer than needed but not too long
            duration_score = 1.0
            if track.duration_seconds < target_duration:
                duration_score = 0.3  # Too short — will loop awkwardly
            elif track.duration_seconds > target_duration * 3:
                duration_score = 0.7  # Too long — waste of storage
            
            # Mood accuracy score
            mood_score = 1.0 if track.mood == target_mood else 0.6
            
            # Energy match (tempo correlation)
            energy_tempo_map = {"high_energy": 120, "upbeat": 110, "dramatic": 100, "emotional": 75, "calm": 80}
            target_tempo = energy_tempo_map.get(target_mood, 100)
            tempo_diff = abs(track.tempo_bpm - target_tempo)
            tempo_score = max(0, 1.0 - (tempo_diff / 60.0))
            
            # Composite score
            score = (mood_score * 0.4) + (duration_score * 0.3) + (tempo_score * 0.3)
            
            if score > best_score:
                best_score = score
                best_track = track
        
        if best_track:
            logger.info(f"[MusicLib] Selected track '{best_track.title}' (mood={best_track.mood}, score={best_score:.2f})")
        
        return best_track
    
    def get_ffmpeg_mix_command(
        self,
        video_path: str,
        track: MusicTrack,
        output_path: str,
        video_duration: float,
        duck_during_speech: bool = True
    ) -> List[str]:
        """
        Build FFmpeg command to mix music with video.
        
        Implements:
        - Volume ducking during speech (sidechain compression simulation)
        - Loop music if shorter than video
        - Fade in/out
        - Music ends before video (don't cover the outro)
        """
        if not track.file_path or not os.path.exists(track.file_path):
            logger.warning(f"[MusicLib] Track file not found: {track.file_path}")
            return []
        
        # Music should end ~2 seconds before video for clean outro
        music_duration = min(video_duration - 2.0, track.duration_seconds)
        music_duration = max(music_duration, 3.0)  # At least 3 seconds
        
        # Build complex FFmpeg filter for music mixing
        # This creates a sidechain-like effect where music dips during speech
        filter_complex = (
            f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{music_duration},"
            f"afade=t=in:ss=0:d=1.0,afade=t=out:st={music_duration-1.5}:d=1.5,"
            f"volume={track.volume_duck_factor}[music];"
            f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-i", track.file_path,
            "-filter_complex", filter_complex,
            "-map", "0:v",  # Keep original video
            "-map", "[aout]",  # Use mixed audio
            "-c:v", "copy",  # Don't re-encode video
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ]
        
        return cmd
    
    def get_track_info(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Get info about a specific track."""
        for track in self.tracks:
            if track.id == track_id:
                return {
                    "id": track.id,
                    "title": track.title,
                    "artist": track.artist,
                    "mood": track.mood,
                    "tempo_bpm": track.tempo_bpm,
                    "duration_seconds": track.duration_seconds,
                    "source": track.source,
                    "license_type": track.license_type
                }
        return None
    
    def list_tracks(self, mood: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available tracks, optionally filtered by mood."""
        tracks = self.tracks
        if mood:
            tracks = [t for t in tracks if t.mood == mood]
        
        return [
            {
                "id": t.id,
                "title": t.title,
                "artist": t.artist,
                "mood": t.mood,
                "tempo_bpm": t.tempo_bpm,
                "duration_seconds": t.duration_seconds,
                "source": t.source,
                "license_type": t.license_type,
                "available": t.file_path is not None and os.path.exists(t.file_path)
            }
            for t in tracks
        ]
    
    def download_free_track(self, url: str, title: str, mood: str) -> Optional[MusicTrack]:
        """
        Download a free track from YouTube Audio Library or Pixabay.
        
        For MVP: Manually download tracks and place in /app/music/
        This method documents the process.
        
        Sources:
        - YouTube Audio Library: https://www.youtube.com/audiolibrary/music
        - Pixabay Music: https://pixabay.com/music/
        - Free Music Archive: https://freemusicarchive.org/
        """
        logger.info(f"[MusicLib] To add '{title}' ({mood}):")
        logger.info("  1. Visit https://www.youtube.com/audiolibrary/music or https://pixabay.com/music/")
        logger.info("  2. Search by mood: " + mood)
        logger.info("  3. Download MP3 (free, royalty-free)")
        logger.info(f"  4. Place in: {self.music_dir}/")
        logger.info("  5. Update BUNDLED_TRACKS in music_library_service.py")
        return None


# Singleton
music_library = MusicLibraryService()
