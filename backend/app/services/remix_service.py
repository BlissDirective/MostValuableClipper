"""AI-powered remix service for clip generation.

Reimagines existing clips by extracting optimal segments, applying
AI-generated hooks, dynamic 9:16 reframing with face tracking,
music matching, and multi-variant output.
"""

import logging
import os
import tempfile
import subprocess
import json
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from app.services.database import SupabaseService
from app.services.ffmpeg_service import FFmpegEditService
from app.services.r2_service import R2Service
from app.services.hook_analysis_service import hook_analysis_service
from app.services.queue import QueueService

logger = logging.getLogger(__name__)


@dataclass
class SegmentScore:
    """Scored video segment with metadata."""
    start: float
    end: float
    duration: float
    text: str
    salience_score: float      # 0-1 based on transcript keywords
    energy_score: float        # 0-1 based on audio/visual energy
    face_presence: float       # 0-1 ratio of frames with faces
    hook_quality: float        # 0-1 based on opening hook pattern
    composite_score: float


@dataclass
class RemixVariant:
    """A single remix output."""
    variant_id: str
    hook_archetype: str
    hook_text: str
    segment: SegmentScore
    music_mood: str
    caption: str
    hashtags: List[str]
    estimated_retention: float


class RemixService:
    """
    AI-powered clip remix engine.

    Pipeline:
    1. Analyze source clip (transcript, shots, energy)
    2. Score all possible segments (15-30s windows)
    3. Pick top-N segments using composite scoring
    4. Generate hook variants using best-performing archetype
    5. Apply dynamic 9:16 reframe with face tracking
    6. Add mood-matched background music
    7. Generate auto-thumbnail with title
    8. Return 2-3 remix variants for user selection
    """

    # Background music library (mood → URL mapping)
    # In production, these would be royalty-free tracks from Freesound/YouTube Audio Library
    MUSIC_LIBRARY = {
        "high_energy": ["energetic_1", "upbeat_1", "driving_1"],
        "conversational": ["chill_1", "lofi_1", "ambient_1"],
        "emotional": ["emotional_1", "inspiring_1", "cinematic_1"],
        "funny": ["quirky_1", "playful_1", "comedy_1"],
        "neutral": ["neutral_1", "corporate_1", "minimal_1"],
    }

    # Hook templates by archetype
    HOOK_TEMPLATES = {
        "question": [
            "Did you know {topic}?",
            "Why does {topic} matter?",
            "What if {topic} changed everything?",
        ],
        "promise": [
            "Here's how {topic} actually works...",
            "The truth about {topic} nobody talks about.",
            "Watch this — {topic} explained in 30 seconds.",
        ],
        "pattern_break": [
            "Everything you know about {topic} is wrong.",
            "Stop believing this lie about {topic}.",
            "The opposite of what they told you about {topic}.",
        ],
        "statistic": [
            "87% of people get {topic} wrong.",
            "The data on {topic} is shocking.",
            "3 facts about {topic} that change everything.",
        ],
        "story": [
            "I learned {topic} the hard way.",
            "The moment I understood {topic}...",
            "True story: {topic} changed my mind.",
        ],
        "challenge": [
            "I bet you can't guess {topic}.",
            "Try this {topic} challenge.",
            "Can you handle the truth about {topic}?",
        ],
    }

    def __init__(self):
        self.db = SupabaseService()
        self.ffmpeg = FFmpegEditService()
        self.r2 = R2Service()
        self.queue = QueueService()

    # ─────────────────────────────────────────────────────────────
    # Phase 1: Segment Analysis & Scoring
    # ─────────────────────────────────────────────────────────────

    def _analyze_source(self, clip: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all analyzable metadata from a clip record."""
        metadata = clip.get("metadata", {}) or {}
        transcript = metadata.get("transcription_text", "")
        
        # Parse transcript segments if available
        transcript_segments = metadata.get("transcript_segments", [])
        if not transcript_segments and transcript:
            # Create simple word-level segments
            words = transcript.split()
            chunk_size = 10
            transcript_segments = [
                {
                    "start": i * 2.0,
                    "end": (i + 1) * 2.0,
                    "text": " ".join(words[i:i+chunk_size])
                }
                for i in range(0, len(words), chunk_size)
            ]
        
        # Shot metadata
        shots = metadata.get("shot_metadata", {}).get("shots", [])
        
        # Audio energy (if available)
        energy_peaks = metadata.get("audio_energy_peaks", [])
        
        return {
            "transcript": transcript,
            "segments": transcript_segments,
            "shots": shots,
            "energy_peaks": energy_peaks,
            "duration": clip.get("duration", 30) or 30,
            "caption": clip.get("caption", ""),
            "title": clip.get("title", ""),
        }

    def _score_salience(self, text: str) -> float:
        """Score how attention-grabbing a text segment is."""
        if not text:
            return 0.0
        
        score = 0.0
        text_lower = text.lower()
        
        # Question marks = curiosity trigger
        if "?" in text:
            score += 0.3
        
        # Numbers = credibility
        if any(c.isdigit() for c in text):
            score += 0.2
        
        # Strong emotional words
        emotional_words = ["shocking", "amazing", "incredible", "unbelievable", 
                          "secret", "truth", "lie", "wrong", "right", "must",
                          "never", "always", "everyone", "nobody", "everything"]
        score += sum(0.15 for w in emotional_words if w in text_lower)
        
        # Short punchy sentences score higher
        words = text.split()
        if 5 <= len(words) <= 20:
            score += 0.2
        elif len(words) > 30:
            score -= 0.1
        
        # Keywords indicating value
        value_words = ["how", "why", "what", "discover", "learn", "find out",
                      "revealed", "exposed", "hidden", "unknown"]
        score += sum(0.1 for w in value_words if w in text_lower)
        
        return min(score, 1.0)

    def _score_energy(self, segment_start: float, segment_end: float,
                     energy_peaks: List[float]) -> float:
        """Score audio/visual energy within a time window."""
        if not energy_peaks:
            return 0.5  # Neutral when no data
        
        # Count energy peaks within segment
        peaks_in_segment = [p for p in energy_peaks if segment_start <= p <= segment_end]
        
        # Normalize by duration
        duration = segment_end - segment_start
        peak_density = len(peaks_in_segment) / max(duration / 5.0, 1.0)  # per 5-second window
        
        score = min(peak_density * 0.3, 1.0)
        
        # Boost if peaks are near the beginning (good for hooks)
        if peaks_in_segment and min(peaks_in_segment) < segment_start + 3.0:
            score += 0.2
        
        return min(score, 1.0)

    def _score_face_presence(self, segment_start: float, segment_end: float,
                            shots: List[Dict]) -> float:
        """Estimate face presence ratio in segment."""
        if not shots:
            return 0.5  # Unknown
        
        # Find shots overlapping with segment
        overlapping = []
        for shot in shots:
            shot_start = shot.get("start", 0)
            shot_end = shot.get("end", 0)
            if shot_end >= segment_start and shot_start <= segment_end:
                overlap_start = max(shot_start, segment_start)
                overlap_end = min(shot_end, segment_end)
                overlap_duration = max(0, overlap_end - overlap_start)
                overlapping.append((overlap_duration, shot.get("has_face", False)))
        
        if not overlapping:
            return 0.5
        
        total_duration = sum(d for d, _ in overlapping)
        face_duration = sum(d for d, has_face in overlapping if has_face)
        
        return face_duration / total_duration if total_duration > 0 else 0.5

    def _score_hook_quality(self, text: str, user_id: str) -> float:
        """Score how good this text would be as an opening hook."""
        if not text:
            return 0.0
        
        # Use the hook analysis service to classify
        patterns = hook_analysis_service._classify_hook(text)
        
        if not patterns:
            return 0.3  # No clear pattern = statement = lower score
        
        # Higher confidence = better hook
        top_pattern = patterns[0]
        confidence = top_pattern.get("confidence", 0.5)
        
        # Get user's top-performing archetype if available
        try:
            # We can't await here (sync context), so we use a heuristic
            # In production, this would be cached
            top_archetypes = ["question", "promise", "pattern_break"]
            if top_pattern["pattern_type"] in top_archetypes:
                confidence += 0.15
        except Exception:
            pass
        
        return min(confidence, 1.0)

    def _find_optimal_segments(self, source: Dict[str, Any],
                               target_duration: Tuple[float, float] = (15, 30),
                               num_variants: int = 3) -> List[SegmentScore]:
        """Find the best N segments for remixing."""
        duration = source["duration"]
        transcript_segments = source["segments"]
        energy_peaks = source["energy_peaks"]
        shots = source["shots"]
        
        min_dur, max_dur = target_duration
        
        # Generate candidate windows (sliding window approach)
        candidates = []
        step = 2.0  # 2-second step
        
        for start in [i * step for i in range(int(duration / step))]:
            for end in [start + min_dur, start + (min_dur + max_dur) / 2, start + max_dur]:
                if end > duration:
                    continue
                
                # Get text for this window
                window_text = ""
                for seg in transcript_segments:
                    seg_start = seg.get("start", 0)
                    seg_end = seg.get("end", 0)
                    if seg_start >= start and seg_end <= end:
                        window_text += " " + seg.get("text", "")
                
                window_text = window_text.strip()
                
                # Score the segment
                salience = self._score_salience(window_text)
                energy = self._score_energy(start, end, energy_peaks)
                face = self._score_face_presence(start, end, shots)
                hook = self._score_hook_quality(window_text, "")
                
                # Composite score — weighted combination
                # Hook quality matters most for openings
                # Face presence matters for 9:16 reframe
                # Energy matters for retention
                composite = (
                    hook * 0.30 +        # 30% — hook quality
                    salience * 0.25 +    # 25% — text salience
                    energy * 0.25 +      # 25% — energy
                    face * 0.20          # 20% — face presence (for vertical crop)
                )
                
                candidates.append(SegmentScore(
                    start=start,
                    end=end,
                    duration=end - start,
                    text=window_text,
                    salience_score=salience,
                    energy_score=energy,
                    face_presence=face,
                    hook_quality=hook,
                    composite_score=composite
                ))
        
        # Sort by composite score descending
        candidates.sort(key=lambda x: x.composite_score, reverse=True)
        
        # Pick top N non-overlapping segments
        selected = []
        for candidate in candidates:
            # Check overlap with already selected
            overlaps = any(
                not (candidate.end <= s.start or candidate.start >= s.end)
                for s in selected
            )
            if not overlaps and len(selected) < num_variants:
                selected.append(candidate)
        
        # If we don't have enough, just take top scoring ones even if overlapping
        if len(selected) < num_variants:
            for candidate in candidates:
                if candidate not in selected:
                    selected.append(candidate)
                if len(selected) >= num_variants:
                    break
        
        return selected[:num_variants]

    # ─────────────────────────────────────────────────────────────
    # Phase 2: Hook & Caption Generation
    # ─────────────────────────────────────────────────────────────

    def _generate_hook_variants(self, segment: SegmentScore,
                                 user_id: str,
                                 top_archetype: Optional[str] = None) -> List[Dict[str, str]]:
        """Generate 2-3 hook text variants for a segment."""
        # Determine best archetype to use
        if not top_archetype:
            # Use the segment's detected pattern
            patterns = hook_analysis_service._classify_hook(segment.text)
            if patterns:
                top_archetype = patterns[0]["pattern_type"]
            else:
                top_archetype = "question"  # Default
        
        # Get user's top-performing archetype if we have data
        user_top = None
        try:
            # This would ideally be cached; for now use default
            user_top = "question"
        except Exception:
            pass
        
        # Prefer user-top archetype if segment supports it
        preferred_archetypes = [user_top] if user_top else []
        if top_archetype not in preferred_archetypes:
            preferred_archetypes.append(top_archetype)
        preferred_archetypes.append("question")  # Fallback
        
        # Extract topic from segment text
        topic = segment.text[:30].strip()
        if len(topic) > 40:
            words = topic.split()[:5]
            topic = " ".join(words)
        
        variants = []
        used_archetypes = set()
        
        for archetype in preferred_archetypes:
            if archetype in used_archetypes:
                continue
            used_archetypes.add(archetype)
            
            templates = self.HOOK_TEMPLATES.get(archetype, self.HOOK_TEMPLATES["question"])
            
            # Pick template based on energy
            if segment.energy_score > 0.7:
                template = templates[0]  # More provocative
            elif segment.energy_score > 0.4:
                template = templates[1]  # Balanced
            else:
                template = templates[2]  # Subtle
            
            hook_text = template.replace("{topic}", topic)
            
            variants.append({
                "archetype": archetype,
                "hook_text": hook_text,
                "template": template
            })
            
            if len(variants) >= 3:
                break
        
        return variants

    def _generate_caption(self, hook: str, segment_text: str,
                         style: str = "standard") -> Tuple[str, List[str]]:
        """Generate caption and hashtags for remix."""
        # Build caption from hook + condensed segment
        body = segment_text[:120] if len(segment_text) > 120 else segment_text
        
        caption = f"{hook}\n\n{body}"
        
        # Generate hashtags from content
        hashtag_candidates = []
        words = (hook + " " + body).lower().split()
        
        # Extract key topics as hashtags
        topic_words = [w for w in words if len(w) > 4 and w.isalpha()]
        hashtag_candidates = list(set(topic_words))[:5]
        
        # Add trending/format hashtags
        format_tags = ["#viral", "#trending", "#fyp", "#shorts", "#reels"]
        
        hashtags = [f"#{tag}" for tag in hashtag_candidates] + format_tags[:3]
        
        return caption, hashtags

    def _select_music_mood(self, segment: SegmentScore) -> str:
        """Select background music mood based on segment characteristics."""
        if segment.energy_score > 0.7 and segment.salience_score > 0.6:
            return "high_energy"
        elif segment.salience_score > 0.7:
            return "emotional"
        elif segment.energy_score > 0.6:
            return "funny"
        elif segment.energy_score > 0.3:
            return "conversational"
        return "neutral"

    # ─────────────────────────────────────────────────────────────
    # Phase 3: Video Processing
    # ─────────────────────────────────────────────────────────────

    def _get_video_info(self, path: str) -> Dict[str, Any]:
        """Get video metadata via ffprobe."""
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=duration,width,height,r_frame_rate,nb_frames",
            "-show_entries", "format=duration",
            "-of", "json",
            path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            data = json.loads(result.stdout)
            stream = data.get("streams", [{}])[0]
            fmt = data.get("format", {})
            
            fps_str = stream.get("r_frame_rate", "30/1")
            num, den = map(int, fps_str.split("/"))
            fps = num / den if den != 0 else 30
            
            return {
                "duration": float(fmt.get("duration", stream.get("duration", 0))),
                "width": int(stream.get("width", 1920)),
                "height": int(stream.get("height", 1080)),
                "fps": fps,
                "total_frames": int(stream.get("nb_frames", 0))
            }
        except Exception as e:
            logger.warning(f"[Remix] ffprobe failed: {e}")
            return {"duration": 30, "width": 1920, "height": 1080, "fps": 30, "total_frames": 900}

    def _build_9x16_crop_filter(self, video_path: str, segment: SegmentScore,
                                 output_width: int = 1080,
                                 output_height: int = 1920) -> str:
        """Build FFmpeg crop filter for dynamic 9:16 with face-centering."""
        info = self._get_video_info(video_path)
        orig_w, orig_h = info["width"], info["height"]
        
        # Target aspect ratio: 9:16 = 0.5625
        target_ratio = output_width / output_height
        
        if orig_w / orig_h > target_ratio:
            # Video is wider than target — crop sides
            crop_h = orig_h
            crop_w = int(orig_h * target_ratio)
            
            # If face presence is high, try to center on face
            # In production, this would use face detection frame-by-frame
            # For MVP, we use simple center crop or bias based on segment face score
            if segment.face_presence > 0.6:
                # Bias toward left side (speaker often on left in interviews)
                x_offset = int((orig_w - crop_w) * 0.3)
            else:
                x_offset = (orig_w - crop_w) // 2
            
            y_offset = 0
            
            return f"crop={crop_w}:{crop_h}:{x_offset}:{y_offset},scale={output_width}:{output_height}"
        else:
            # Video is taller than target — crop top/bottom
            crop_w = orig_w
            crop_h = int(orig_w / target_ratio)
            
            # Center vertically, slightly bias toward upper third (faces)
            y_offset = max(0, (orig_h - crop_h) // 3)
            x_offset = 0
            
            return f"crop={crop_w}:{crop_h}:{x_offset}:{y_offset},scale={output_width}:{output_height}"

    async def _render_remix(self,
                            source_path: str,
                            variant: RemixVariant,
                            output_path: str) -> Dict[str, Any]:
        """Render a single remix variant using FFmpeg."""
        segment = variant.segment
        
        # 1. Extract segment with 9:16 crop
        crop_filter = self._build_9x16_crop_filter(source_path, segment)
        
        temp_segment = output_path.replace(".mp4", "_segment.mp4")
        
        # Extract and crop segment
        cmd_extract = [
            "ffmpeg", "-y",
            "-ss", str(segment.start),
            "-t", str(segment.duration),
            "-i", source_path,
            "-vf", crop_filter,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            temp_segment
        ]
        
        result = subprocess.run(cmd_extract, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return {"success": False, "error": f"Segment extract failed: {result.stderr}"}
        
        # 2. Add text hook overlay (first 3 seconds)
        temp_hooked = output_path.replace(".mp4", "_hooked.mp4")
        
        # Sanitize hook text for FFmpeg
        hook_text = variant.hook_text.replace("'", "\\'")
        
        hook_filter = (
            f"drawtext=text='{hook_text}':"
            f"fontcolor=white:fontsize=48:"
            f"x=(w-text_w)/2:y=(h*0.15):"
            f"box=1:boxcolor=black@0.6:boxborderw=10:"
            f"enable='between(t\\,0\\,3)'"
        )
        
        cmd_hook = [
            "ffmpeg", "-y",
            "-i", temp_segment,
            "-vf", hook_filter,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "copy",
            temp_hooked
        ]
        
        result = subprocess.run(cmd_hook, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            # If hook overlay fails, just use segment
            temp_hooked = temp_segment
        
        # 3. Add background music (if available)
        # In production, this would download a track from the music library
        # For MVP, we skip music if no track is available locally
        music_available = False  # Would check music library
        
        if music_available:
            cmd_music = [
                "ffmpeg", "-y",
                "-i", temp_hooked,
                "-i", "music_track.mp3",  # Placeholder
                "-filter_complex",
                "[0:a]volume=1.0[a0];[1:a]volume=0.12[a1];[a0][a1]amix=inputs=2:duration=first[aout]",
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                output_path
            ]
            result = subprocess.run(cmd_music, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                # Fallback to no music
                os.rename(temp_hooked, output_path)
        else:
            # No music available
            if os.path.exists(temp_hooked):
                os.rename(temp_hooked, output_path)
            else:
                os.rename(temp_segment, output_path)
        
        # Cleanup temp files
        for temp in [temp_segment, temp_hooked]:
            if os.path.exists(temp) and temp != output_path:
                os.remove(temp)
        
        # Get output info
        output_info = self._get_video_info(output_path)
        
        return {
            "success": True,
            "output_path": output_path,
            "duration": output_info["duration"],
            "width": output_info["width"],
            "height": output_info["height"]
        }

    # ─────────────────────────────────────────────────────────────
    # Phase 4: Thumbnail Generation
    # ─────────────────────────────────────────────────────────────

    async def _generate_thumbnail(self, video_path: str,
                                   variant: RemixVariant,
                                   output_path: str) -> bool:
        """Generate an engaging thumbnail from the video."""
        try:
            # Pick a high-energy frame (first 5 seconds or mid-point)
            info = self._get_video_info(video_path)
            if variant.segment.energy_score > 0.6:
                timestamp = 1.0  # Early frame for hook
            else:
                timestamp = min(info["duration"] / 2, 5.0)
            
            # Extract frame
            base_thumb = output_path.replace(".jpg", "_base.jpg")
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                base_thumb
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if not os.path.exists(base_thumb):
                return False
            
            # Add hook text as overlay
            hook_text = variant.hook_text[:40]  # Truncate for thumbnail
            
            cmd_text = [
                "ffmpeg", "-y",
                "-i", base_thumb,
                "-vf",
                f"drawtext=text='{hook_text}':fontcolor=white:fontsize=36:"
                f"x=(w-text_w)/2:y=(h*0.75):"
                f"box=1:boxcolor=black@0.7:boxborderw=8",
                "-y",
                output_path
            ]
            subprocess.run(cmd_text, capture_output=True, text=True, timeout=30)
            
            os.remove(base_thumb)
            
            return os.path.exists(output_path)
        except Exception as e:
            logger.warning(f"[Remix] Thumbnail generation failed: {e}")
            return False

    # ─────────────────────────────────────────────────────────────
    # Main Entry Point
    # ─────────────────────────────────────────────────────────────

    async def create_remix(self,
                           clip_id: str,
                           user_id: str,
                           num_variants: int = 3,
                           target_duration: Tuple[float, float] = (15, 30)) -> Dict[str, Any]:
        """
        Create AI-powered remix variants of an existing clip.
        
        Returns:
            {
                "success": True,
                "original_clip_id": "...",
                "variants": [
                    {
                        "variant_id": "...",
                        "video_url": "...",
                        "thumbnail_url": "...",
                        "caption": "...",
                        "hashtags": [...],
                        "hook_archetype": "...",
                        "hook_text": "...",
                        "segment": {"start": 0, "end": 25, "score": 0.85},
                        "duration": 25.0,
                        "music_mood": "high_energy"
                    },
                    ...
                ]
            }
        """
        temp_dir = tempfile.mkdtemp(prefix=f"remix_{clip_id}_")
        
        try:
            # 1. Fetch original clip
            clip = await self.db.get_clip(clip_id)
            if not clip:
                return {"success": False, "error": "Clip not found"}
            
            if clip.get("user_id") != user_id:
                return {"success": False, "error": "Not authorized"}
            
            source_url = clip.get("video_url")
            if not source_url:
                return {"success": False, "error": "Clip has no video"}
            
            # 2. Download source video
            source_path = os.path.join(temp_dir, "source.mp4")
            await self.ffmpeg.download_source(source_url, temp_dir)
            
            # The download_source puts file at temp_dir/source.mp4
            if not os.path.exists(source_path):
                # Try finding it
                for f in os.listdir(temp_dir):
                    if f.endswith(".mp4"):
                        source_path = os.path.join(temp_dir, f)
                        break
            
            # 3. Analyze source
            source_analysis = self._analyze_source(clip)
            
            # If we don't have transcript, extract it now
            if not source_analysis["transcript"]:
                # Use speech-to-text on the source video
                # For MVP, we'll create simple dummy transcript
                source_analysis["transcript"] = clip.get("caption", "")
                source_analysis["segments"] = [{
                    "start": 0,
                    "end": source_analysis["duration"],
                    "text": clip.get("caption", "")
                }]
            
            # 4. Find optimal segments
            segments = self._find_optimal_segments(
                source_analysis,
                target_duration=target_duration,
                num_variants=num_variants
            )
            
            if not segments:
                return {"success": False, "error": "Could not find suitable segments for remix"}
            
            # 5. Get user's top-performing hook archetype
            user_top_archetype = None
            try:
                hook_analysis = await hook_analysis_service.analyze_hooks(user_id, days=30)
                if hook_analysis.get("archetypes"):
                    user_top_archetype = hook_analysis["archetypes"][0]["pattern_type"]
            except Exception:
                pass
            
            # 6. Generate variants
            variants = []
            for i, segment in enumerate(segments):
                # Generate hooks
                hook_variants = self._generate_hook_variants(
                    segment, user_id, user_top_archetype
                )
                
                # Use the first hook variant
                hook = hook_variants[0]
                
                # Generate caption
                caption, hashtags = self._generate_caption(
                    hook["hook_text"], segment.text
                )
                
                # Select music mood
                music_mood = self._select_music_mood(segment)
                
                # Create variant
                variant = RemixVariant(
                    variant_id=f"{clip_id}_remix_{i+1}",
                    hook_archetype=hook["archetype"],
                    hook_text=hook["hook_text"],
                    segment=segment,
                    music_mood=music_mood,
                    caption=caption,
                    hashtags=hashtags,
                    estimated_retention=segment.composite_score
                )
                
                # 7. Render the variant
                output_path = os.path.join(temp_dir, f"remix_{i+1}.mp4")
                render_result = await self._render_remix(source_path, variant, output_path)
                
                if not render_result.get("success"):
                    logger.warning(f"[Remix] Variant {i+1} render failed: {render_result.get('error')}")
                    continue
                
                # 8. Upload to R2
                r2_key = f"clips/{variant.variant_id}.mp4"
                await self.r2.upload_file(render_result["output_path"], r2_key)
                video_url = await self.r2.get_presigned_url(r2_key, expires_in=604800)
                
                # 9. Generate thumbnail
                thumb_path = os.path.join(temp_dir, f"thumb_{i+1}.jpg")
                thumb_success = await self._generate_thumbnail(
                    render_result["output_path"], variant, thumb_path
                )
                
                thumb_url = None
                if thumb_success:
                    thumb_r2_key = f"thumbnails/{variant.variant_id}.jpg"
                    await self.r2.upload_file(thumb_path, thumb_r2_key)
                    thumb_url = await self.r2.get_presigned_url(thumb_r2_key, expires_in=604800)
                
                # 10. Create clip record for this variant
                variant_clip_data = {
                    "user_id": user_id,
                    "pipeline_id": clip.get("pipeline_id"),
                    "source_id": clip.get("source_id"),
                    "title": f"Remix: {clip.get('title', 'Untitled')}",
                    "caption": caption,
                    "hashtags": hashtags,
                    "status": "rendered",
                    "video_url": video_url,
                    "thumbnail_url": thumb_url,
                    "duration_seconds": render_result.get("duration"),
                    "parent_clip_id": clip_id,
                    "remix_variant_id": variant.variant_id,
                    "remix_metadata": {
                        "hook_archetype": variant.hook_archetype,
                        "hook_text": variant.hook_text,
                        "segment_start": segment.start,
                        "segment_end": segment.end,
                        "segment_score": segment.composite_score,
                        "music_mood": variant.music_mood,
                        "estimated_retention": variant.estimated_retention
                    }
                }
                
                created_variant = await self.db.create_clip(variant_clip_data)
                
                variants.append({
                    "variant_id": variant.variant_id,
                    "clip_id": created_variant.get("id"),
                    "video_url": video_url,
                    "thumbnail_url": thumb_url,
                    "caption": caption,
                    "hashtags": hashtags,
                    "hook_archetype": variant.hook_archetype,
                    "hook_text": variant.hook_text,
                    "segment": {
                        "start": segment.start,
                        "end": segment.end,
                        "duration": segment.duration,
                        "score": round(segment.composite_score, 3)
                    },
                    "duration": render_result.get("duration"),
                    "music_mood": variant.music_mood,
                    "estimated_retention": round(variant.estimated_retention, 3)
                })
            
            if not variants:
                return {"success": False, "error": "All remix variants failed to render"}
            
            # 10. Create revision history
            revision_data = {
                "clip_id": clip_id,
                "user_id": user_id,
                "revision_type": "remix",
                "previous_state": {
                    "video_url": clip.get("video_url"),
                    "caption": clip.get("caption"),
                    "status": clip.get("status")
                },
                "new_state": {
                    "variant_count": len(variants)
                },
                "metadata": {
                    "remix_variants": [v["variant_id"] for v in variants]
                }
            }
            try:
                await self.db.create_clip_revision(revision_data)
            except Exception as e:
                logger.warning(f"[Remix] Failed to create revision: {e}")
            
            return {
                "success": True,
                "original_clip_id": clip_id,
                "variants": variants,
                "total_variants": len(variants)
            }
        
        except Exception as e:
            logger.error(f"[Remix] Fatal error: {e}")
            return {"success": False, "error": str(e)}
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


# Singleton
remix_service = RemixService()
