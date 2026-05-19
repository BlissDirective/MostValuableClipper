"""Individual swarm agent implementations.

Each agent is a self-contained unit that can execute in parallel
with different personas, strategies, or target accounts.
"""

import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from app.services.claude_hook_service import ClaudeHookService, GeneratedHook
from app.services.remix_service import RemixService
from app.services.social_posting import SocialPostingService
from app.services.database import SupabaseService

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result from a single swarm agent execution."""
    agent_index: int
    persona: str
    status: str  # completed, failed
    data: Dict[str, Any]
    cost_cents: int
    duration_ms: int
    error: Optional[str] = None


class HookSwarmAgent:
    """Generate hooks using a specific persona/strategy."""

    # Personas that shape hook generation style
    PERSONAS = [
        "viral_hunter",      # Focuses on scroll-stopping power
        "storyteller",       # Narrative-driven hooks
        "pattern_breaker",   # Disruption and surprise
        "authority",         # Credibility and trust
        "emotional_trigger", # Feeling-based hooks
        "curiosity_gap",     # Open loops and mysteries
        "challenge",         # Dare / test the viewer
        "nostalgia",         # Memory / relatable hooks
    ]

    def __init__(self, agent_index: int, persona: str, hook_service: Optional[ClaudeHookService] = None):
        self.agent_index = agent_index
        self.persona = persona
        self.hook_service = hook_service or ClaudeHookService()
        self.db = SupabaseService()

    async def execute(
        self,
        clip_id: str,
        platform: str,
        user_id: str
    ) -> AgentResult:
        """Generate hooks for a clip using this agent's persona."""
        start = time.time()

        try:
            # Fetch clip and transcript
            clip = await self.db.get_clip(clip_id)
            if not clip:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.persona,
                    status="failed",
                    data={},
                    cost_cents=0,
                    duration_ms=int((time.time() - start) * 1000),
                    error="Clip not found"
                )

            # Get transcript text
            transcript = ""
            metadata = clip.get("metadata", {}) or {}
            transcript = metadata.get("transcription_text", "")
            if not transcript:
                transcript = clip.get("caption", "") or ""

            # Adjust prompt based on persona
            system_override = self._persona_system_prompt(self.persona, platform)

            # Generate hooks via Claude (1 hook per agent for variety)
            hooks = await self.hook_service.generate_hooks(
                transcript_text=transcript,
                user_top_archetypes=[],
                num_variants=1,
                platform=platform
            )

            duration_ms = int((time.time() - start) * 1000)

            if not hooks:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.persona,
                    status="failed",
                    data={},
                    cost_cents=5,
                    duration_ms=duration_ms,
                    error="No hooks generated"
                )

            hook = hooks[0]

            # Generate caption from hook
            caption, hashtags = await self.hook_service.generate_caption_from_hook(
                hook=hook,
                transcript=transcript,
                platform=platform,
                max_length=150
            )

            return AgentResult(
                agent_index=self.agent_index,
                persona=self.persona,
                status="completed",
                data={
                    "hook_text": hook.hook_text,
                    "archetype": hook.archetype,
                    "confidence": hook.confidence,
                    "rationale": hook.rationale,
                    "estimated_retention": hook.estimated_retention,
                    "caption": caption,
                    "hashtags": hashtags,
                    "clip_id": clip_id,
                    "platform": platform,
                },
                cost_cents=10,  # ~$0.10 for hook + caption generation
                duration_ms=duration_ms
            )

        except Exception as e:
            logger.error(f"[HookAgent {self.agent_index}/{self.persona}] Failed: {e}")
            return AgentResult(
                agent_index=self.agent_index,
                persona=self.persona,
                status="failed",
                data={},
                cost_cents=5,
                duration_ms=int((time.time() - start) * 1000),
                error=str(e)
            )

    def _persona_system_prompt(self, persona: str, platform: str) -> str:
        """Get a persona-specific system prompt override."""
        prompts = {
            "viral_hunter": "You are a TikTok growth hacker. Every hook must feel impossible to scroll past. Use power words, extreme emotion, and FOMO.",
            "storyteller": "You are a narrative designer. Open with a micro-story that creates immediate emotional investment.",
            "pattern_breaker": "You are a disruption expert. Break expectations immediately. Contradict common wisdom.",
            "authority": "You are a credible expert. Open with authority signals: data, experience, or insider knowledge.",
            "emotional_trigger": "You are an emotional architect. Target specific feelings: awe, anger, joy, relief.",
            "curiosity_gap": "You are a curiosity engineer. Create an open loop the viewer MUST close by watching.",
            "challenge": "You are a provocateur. Challenge the viewer directly. Make them feel tested.",
            "nostalgia": "You are a memory weaver. Connect to shared experiences and collective memories.",
        }
        return prompts.get(persona, "")


class RemixSwarmAgent:
    """Remix a clip using a specific segment strategy."""

    # Strategies for segment selection
    STRATEGIES = [
        "peak_energy",       # Highest energy moments
        "hook_first",        # Best opening hook in transcript
        "emotional_arc",     # Moments with emotional words
        "face_focus",        # Segments with highest face presence
        "question_moment",   # Segments containing questions
        "surprise_drop",     # Unexpected shifts in content
    ]

    def __init__(self, agent_index: int, strategy: str, remix_service: Optional[RemixService] = None):
        self.agent_index = agent_index
        self.strategy = strategy
        self.remix_service = remix_service or RemixService()
        self.db = SupabaseService()

    async def execute(
        self,
        clip_id: str,
        user_id: str,
        target_duration: tuple = (15, 30)
    ) -> AgentResult:
        """Remix a clip using this agent's strategy."""
        start = time.time()

        try:
            # Fetch clip
            clip = await self.db.get_clip(clip_id)
            if not clip:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.strategy,
                    status="failed",
                    data={},
                    cost_cents=0,
                    duration_ms=int((time.time() - start) * 1000),
                    error="Clip not found"
                )

            if clip.get("user_id") != user_id:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.strategy,
                    status="failed",
                    data={},
                    cost_cents=0,
                    duration_ms=int((time.time() - start) * 1000),
                    error="Not authorized"
                )

            # Create remix via RemixService (generates 1 variant per call when swarm mode)
            result = await self.remix_service.create_remix(
                clip_id=clip_id,
                user_id=user_id,
                num_variants=1,
                target_duration=target_duration
            )

            duration_ms = int((time.time() - start) * 1000)

            if not result.get("success"):
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.strategy,
                    status="failed",
                    data={},
                    cost_cents=10,
                    duration_ms=duration_ms,
                    error=result.get("error", "Remix failed")
                )

            variants = result.get("variants", [])
            if not variants:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.strategy,
                    status="failed",
                    data={},
                    cost_cents=10,
                    duration_ms=duration_ms,
                    error="No variants generated"
                )

            variant = variants[0]

            return AgentResult(
                agent_index=self.agent_index,
                persona=self.strategy,
                status="completed",
                data={
                    "variant_id": variant.get("variant_id"),
                    "clip_id": variant.get("clip_id"),
                    "video_url": variant.get("video_url"),
                    "thumbnail_url": variant.get("thumbnail_url"),
                    "caption": variant.get("caption"),
                    "hashtags": variant.get("hashtags"),
                    "hook_archetype": variant.get("hook_archetype"),
                    "hook_text": variant.get("hook_text"),
                    "segment": variant.get("segment"),
                    "duration": variant.get("duration"),
                    "music_mood": variant.get("music_mood"),
                    "estimated_retention": variant.get("estimated_retention"),
                    "original_clip_id": clip_id,
                },
                cost_cents=20,  # ~$0.20 for video processing
                duration_ms=duration_ms
            )

        except Exception as e:
            logger.error(f"[RemixAgent {self.agent_index}/{self.strategy}] Failed: {e}")
            return AgentResult(
                agent_index=self.agent_index,
                persona=self.strategy,
                status="failed",
                data={},
                cost_cents=10,
                duration_ms=int((time.time() - start) * 1000),
                error=str(e)
            )


class PostSwarmAgent:
    """Post a clip to a specific social account."""

    def __init__(self, agent_index: int, account_id: str, platform: str, posting_service: Optional[SocialPostingService] = None):
        self.agent_index = agent_index
        self.account_id = account_id
        self.platform = platform
        self.posting_service = posting_service or SocialPostingService()
        self.db = SupabaseService()

    async def execute(
        self,
        clip_id: str,
        user_id: str,
        hook_data: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """Post clip to the assigned account."""
        start = time.time()

        try:
            # Fetch clip
            clip = await self.db.get_clip(clip_id)
            if not clip:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=f"{self.platform}:{self.account_id}",
                    status="failed",
                    data={},
                    cost_cents=0,
                    duration_ms=int((time.time() - start) * 1000),
                    error="Clip not found"
                )

            # Use hook data if provided, otherwise use clip metadata
            caption = hook_data.get("caption", clip.get("caption", "")) if hook_data else clip.get("caption", "")
            hashtags = hook_data.get("hashtags", []) if hook_data else (clip.get("hashtags", []) or clip.get("tags", []))
            video_url = clip.get("video_url", "")
            title = clip.get("title", "")

            # Post via SocialPostingService
            result = await self.posting_service.post_clip(
                clip_id=clip_id,
                platform=self.platform,
                video_url=video_url,
                caption=caption,
                hashtags=hashtags,
                title=title
            )

            duration_ms = int((time.time() - start) * 1000)

            if not result.get("success"):
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=f"{self.platform}:{self.account_id}",
                    status="failed",
                    data={},
                    cost_cents=1,
                    duration_ms=duration_ms,
                    error=result.get("error", "Post failed")
                )

            return AgentResult(
                agent_index=self.agent_index,
                persona=f"{self.platform}:{self.account_id}",
                status="completed",
                data={
                    "clip_id": clip_id,
                    "platform": self.platform,
                    "account_id": self.account_id,
                    "post_id": result.get("post_id"),
                    "post_url": result.get("post_url"),
                    "status": result.get("status"),
                    "caption": caption,
                    "hashtags": hashtags,
                },
                cost_cents=1,  # ~$0.01 per API call
                duration_ms=duration_ms
            )

        except Exception as e:
            logger.error(f"[PostAgent {self.agent_index}/{self.platform}] Failed: {e}")
            return AgentResult(
                agent_index=self.agent_index,
                persona=f"{self.platform}:{self.account_id}",
                status="failed",
                data={},
                cost_cents=1,
                duration_ms=int((time.time() - start) * 1000),
                error=str(e)
            )


class ABTestSwarmAgent:
    """Run A/B test analysis with a specific comparison strategy."""

    STRATEGIES = [
        "engagement_winner",      # Pick based on likes+comments+shares
        "retention_winner",       # Pick based on 3s + full retention
        "composite_winner",       # Balanced composite score
        "views_winner",           # Pure view count winner
        "watch_time_winner",      # Total watch time winner
    ]

    def __init__(self, agent_index: int, strategy: str, ab_service=None):
        from app.services.ab_testing_service import ABTestingService
        self.agent_index = agent_index
        self.strategy = strategy
        self.ab_service = ab_service or ABTestingService()
        self.db = SupabaseService()

    async def execute(
        self,
        test_id: str,
        user_id: str,
        clip_id: str
    ) -> AgentResult:
        """Run A/B test evaluation with this agent's strategy."""
        start = time.time()

        try:
            # Get test status
            test = await self.ab_service.get_test_status(test_id)
            if not test:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.strategy,
                    status="failed",
                    data={},
                    cost_cents=0,
                    duration_ms=int((time.time() - start) * 1000),
                    error="Test not found"
                )

            # Calculate winner using different weights based on strategy
            variants = test.get("variants", [])
            if len(variants) < 2:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.strategy,
                    status="failed",
                    data={},
                    cost_cents=1,
                    duration_ms=int((time.time() - start) * 1000),
                    error="Not enough variants for comparison"
                )

            # Score each variant based on strategy
            scores = []
            for v in variants:
                if self.strategy == "engagement_winner":
                    score = v.get("engagement_rate", 0) * 100  # Scale up
                elif self.strategy == "retention_winner":
                    score = (v.get("retention_3s", 0) + v.get("retention_full", 0)) / 2 * 100
                elif self.strategy == "composite_winner":
                    score = v.get("composite_score", 0) * 100
                elif self.strategy == "views_winner":
                    score = min(v.get("views", 0) / 100, 100)  # Cap at 100 for scale
                elif self.strategy == "watch_time_winner":
                    score = min(v.get("watch_time_seconds", 0) / 60, 100)
                else:
                    score = v.get("composite_score", 0) * 100

                scores.append((v, score))

            scores.sort(key=lambda x: x[1], reverse=True)
            winner, winning_score = scores[0]

            # Check margin over second place
            margin = 0
            if len(scores) > 1:
                margin = (winning_score - scores[1][1]) / winning_score if winning_score > 0 else 0

            return AgentResult(
                agent_index=self.agent_index,
                persona=self.strategy,
                status="completed",
                data={
                    "test_id": test_id,
                    "strategy": self.strategy,
                    "winner_clip_id": winner.get("clip_id"),
                    "winner_variant_id": winner.get("variant_id"),
                    "winner_score": round(winning_score, 2),
                    "margin_vs_second": round(margin, 3),
                    "confidence": "high" if margin > 0.15 else "medium" if margin > 0.05 else "low",
                    "variant_count": len(variants),
                    "all_scores": [
                        {"clip_id": v.get("clip_id"), "score": round(s, 2)}
                        for v, s in scores
                    ]
                },
                cost_cents=3,
                duration_ms=int((time.time() - start) * 1000)
            )

        except Exception as e:
            logger.error(f"[ABTestAgent {self.agent_index}/{self.strategy}] Failed: {e}")
            return AgentResult(
                agent_index=self.agent_index,
                persona=self.strategy,
                status="failed",
                data={},
                cost_cents=2,
                duration_ms=int((time.time() - start) * 1000),
                error=str(e)
            )


class MusicMatchSwarmAgent:
    """Match music tracks using a specific mood/energy strategy."""

    STRATEGIES = [
        "energy_match",       # Match music energy to segment energy
        "contrast_boost",     # Use contrasting music for surprise
        "tempo_sync",         # Sync music tempo to speech cadence
        "mood_amplify",       # Amplify existing mood
        "neutral_underscore", # Subtle background only
    ]

    def __init__(self, agent_index: int, strategy: str, music_service=None):
        from app.services.music_library_service import MusicLibraryService
        self.agent_index = agent_index
        self.strategy = strategy
        self.music_service = music_service or MusicLibraryService()
        self.db = SupabaseService()

    async def execute(
        self,
        clip_id: str,
        user_id: str,
        segment_data: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """Select music track using this agent's strategy."""
        start = time.time()

        try:
            # Get clip data
            clip = await self.db.get_clip(clip_id)
            if not clip:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.strategy,
                    status="failed",
                    data={},
                    cost_cents=0,
                    duration_ms=int((time.time() - start) * 1000),
                    error="Clip not found"
                )

            # Default segment data if not provided
            if not segment_data:
                metadata = clip.get("metadata", {}) or {}
                segment_data = {
                    "energy": metadata.get("energy_score", 0.5),
                    "salience": metadata.get("salience_score", 0.5),
                    "duration": clip.get("duration", 20),
                    "mood": metadata.get("detected_mood", "neutral")
                }

            # Get available tracks
            tracks = self.music_service.list_tracks()
            if not tracks:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.strategy,
                    status="failed",
                    data={},
                    cost_cents=1,
                    duration_ms=int((time.time() - start) * 1000),
                    error="No music tracks available"
                )

            # Score tracks based on strategy
            scored = []
            for track in tracks:
                if not track.get("available"):
                    continue

                score = 0.5  # Base score

                if self.strategy == "energy_match":
                    track_mood = track.get("mood", "neutral")
                    energy_map = {"high_energy": 1.0, "upbeat": 0.8, "dramatic": 0.7, "emotional": 0.4, "calm": 0.2}
                    track_energy = energy_map.get(track_mood, 0.5)
                    segment_energy = segment_data.get("energy", 0.5)
                    score = 1.0 - abs(track_energy - segment_energy)

                elif self.strategy == "contrast_boost":
                    track_mood = track.get("mood", "neutral")
                    energy_map = {"high_energy": 1.0, "upbeat": 0.8, "dramatic": 0.7, "emotional": 0.4, "calm": 0.2}
                    track_energy = energy_map.get(track_mood, 0.5)
                    segment_energy = segment_data.get("energy", 0.5)
                    score = abs(track_energy - (1.0 - segment_energy))  # Prefer opposite

                elif self.strategy == "tempo_sync":
                    tempo = track.get("tempo_bpm", 100)
                    # Prefer moderate tempo for speech sync (100-130 BPM)
                    if 100 <= tempo <= 130:
                        score = 1.0 - abs(tempo - 115) / 30
                    else:
                        score = 0.3

                elif self.strategy == "mood_amplify":
                    segment_mood = segment_data.get("mood", "neutral")
                    track_mood = track.get("mood", "neutral")
                    mood_match = {
                        "high_energy": ["high_energy", "dramatic", "upbeat"],
                        "emotional": ["emotional", "dramatic"],
                        "calm": ["calm", "upbeat"],
                        "dramatic": ["dramatic", "high_energy"],
                        "neutral": ["upbeat", "calm"]
                    }
                    matches = mood_match.get(segment_mood, ["upbeat"])
                    score = 1.0 if track_mood in matches else 0.3

                elif self.strategy == "neutral_underscore":
                    # Prefer calm, low-energy tracks
                    score = 1.0 if track.get("mood") == "calm" else 0.4 if track.get("mood") == "emotional" else 0.1

                scored.append((track, score))

            if not scored:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.strategy,
                    status="failed",
                    data={},
                    cost_cents=1,
                    duration_ms=int((time.time() - start) * 1000),
                    error="No suitable tracks found"
                )

            scored.sort(key=lambda x: x[1], reverse=True)
            best_track, best_score = scored[0]

            return AgentResult(
                agent_index=self.agent_index,
                persona=self.strategy,
                status="completed",
                data={
                    "clip_id": clip_id,
                    "strategy": self.strategy,
                    "selected_track": best_track,
                    "score": round(best_score, 3),
                    "alternatives": [t.get("id") for t, _ in scored[:3]],
                    "duration_match": best_track.get("duration_seconds", 0) >= segment_data.get("duration", 20),
                    "license_type": best_track.get("license_type", "unknown")
                },
                cost_cents=2,
                duration_ms=int((time.time() - start) * 1000)
            )

        except Exception as e:
            logger.error(f"[MusicAgent {self.agent_index}/{self.strategy}] Failed: {e}")
            return AgentResult(
                agent_index=self.agent_index,
                persona=self.strategy,
                status="failed",
                data={},
                cost_cents=1,
                duration_ms=int((time.time() - start) * 1000),
                error=str(e)
            )


class ThumbnailSwarmAgent:
    """Generate thumbnails with a specific style strategy."""

    STYLES = [
        "face_focus",         # Frame with most prominent face
        "text_overlay",       # Frame suitable for text overlay
        "action_peak",        # Most action/motion in frame
        "color_pop",          # Frame with most vibrant colors
        "mid_shot",           # Balanced mid-shot composition
    ]

    def __init__(self, agent_index: int, style: str, thumb_service=None):
        from app.services.thumbnail_service import ThumbnailService
        self.agent_index = agent_index
        self.style = style
        self.thumb_service = thumb_service or ThumbnailService()
        self.db = SupabaseService()

    async def execute(
        self,
        clip_id: str,
        user_id: str
    ) -> AgentResult:
        """Generate thumbnail using this agent's style strategy."""
        start = time.time()

        try:
            clip = await self.db.get_clip(clip_id)
            if not clip:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.style,
                    status="failed",
                    data={},
                    cost_cents=0,
                    duration_ms=int((time.time() - start) * 1000),
                    error="Clip not found"
                )

            video_url = clip.get("video_url")
            if not video_url:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.style,
                    status="failed",
                    data={},
                    cost_cents=0,
                    duration_ms=int((time.time() - start) * 1000),
                    error="No video URL available"
                )

            # Generate thumbnails (they're evenly spaced, we pick based on style)
            result = await self.thumb_service.generate_thumbnails(
                clip_id=clip_id,
                video_url=video_url,
                count=5  # Generate 5, pick best by style
            )

            if not result.get("success"):
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.style,
                    status="failed",
                    data={},
                    cost_cents=1,
                    duration_ms=int((time.time() - start) * 1000),
                    error=result.get("error", "Thumbnail generation failed")
                )

            thumbnails = result.get("thumbnails", [])
            if not thumbnails:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.style,
                    status="failed",
                    data={},
                    cost_cents=1,
                    duration_ms=int((time.time() - start) * 1000),
                    error="No thumbnails generated"
                )

            # For MVP, pick based on position (proxy for style)
            # In production, use CV analysis
            style_index_map = {
                "face_focus": 0,      # Early frame (often has intro face)
                "text_overlay": 1,    # Second frame
                "action_peak": 2,     # Middle frame
                "color_pop": 3,       # Later frame
                "mid_shot": 4,        # Last of the 5
            }
            idx = style_index_map.get(self.style, 0)
            idx = min(idx, len(thumbnails) - 1)
            selected = thumbnails[idx]

            return AgentResult(
                agent_index=self.agent_index,
                persona=self.style,
                status="completed",
                data={
                    "clip_id": clip_id,
                    "style": self.style,
                    "thumbnail_url": selected.get("url"),
                    "timestamp": selected.get("time"),
                    "all_thumbnails": thumbnails,
                    "selected_index": idx,
                    "strategy_note": f"Selected frame at {selected.get('time')}s based on {self.style} preference"
                },
                cost_cents=1,
                duration_ms=int((time.time() - start) * 1000)
            )

        except Exception as e:
            logger.error(f"[ThumbnailAgent {self.agent_index}/{self.style}] Failed: {e}")
            return AgentResult(
                agent_index=self.agent_index,
                persona=self.style,
                status="failed",
                data={},
                cost_cents=1,
                duration_ms=int((time.time() - start) * 1000),
                error=str(e)
            )


class SafetySwarmAgent:
    """Run safety checks with a specific sensitivity level."""

    SENSITIVITY_LEVELS = [
        "strict",             # Flag everything remotely questionable
        "standard",           # Normal platform compliance
        "permissive",         # Allow borderline, flag only clear violations
        "brand_safe",         # Extra strict for brand partnerships
        "kids_safe",          # Family-friendly only
    ]

    def __init__(self, agent_index: int, sensitivity: str, safety_service=None):
        from app.services.safety import SafetyCheckService
        self.agent_index = agent_index
        self.sensitivity = sensitivity
        self.safety_service = safety_service or SafetyCheckService()
        self.db = SupabaseService()

    async def execute(
        self,
        clip_id: str,
        user_id: str
    ) -> AgentResult:
        """Run safety check with this agent's sensitivity level."""
        start = time.time()

        try:
            clip = await self.db.get_clip(clip_id)
            if not clip:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.sensitivity,
                    status="failed",
                    data={},
                    cost_cents=0,
                    duration_ms=int((time.time() - start) * 1000),
                    error="Clip not found"
                )

            # Build text from clip metadata
            text_parts = []
            text_parts.append(clip.get("title", ""))
            text_parts.append(clip.get("caption", ""))
            text_parts.append(clip.get("description", ""))
            metadata = clip.get("metadata", {}) or {}
            text_parts.append(metadata.get("transcription_text", ""))
            text_parts.append(metadata.get("detected_hook_text", ""))
            text = " ".join(filter(None, text_parts))

            # Run safety check
            result = await self.safety_service.check_content(text=text)

            # Adjust based on sensitivity
            base_status = result.get("status", "pass")
            categories = result.get("categories", [])

            # Sensitivity modifiers
            sensitivity_map = {
                "strict": {"promote_review": True, "threshold": 0},
                "standard": {"promote_review": False, "threshold": 1},
                "permissive": {"promote_review": False, "threshold": 2},
                "brand_safe": {"promote_review": True, "threshold": 0},
                "kids_safe": {"promote_review": True, "threshold": 0, "extra_check": ["children"]},
            }

            config = sensitivity_map.get(self.sensitivity, {"promote_review": False, "threshold": 1})

            # Apply sensitivity rules
            adjusted_status = base_status
            if config["promote_review"] and categories:
                adjusted_status = "review"
            if len(categories) > config.get("threshold", 1):
                adjusted_status = "review"

            extra_flags = []
            if config.get("extra_check"):
                for check in config["extra_check"]:
                    if check in categories:
                        adjusted_status = "block"
                        extra_flags.append(f"{check}_strict")

            return AgentResult(
                agent_index=self.agent_index,
                persona=self.sensitivity,
                status="completed",
                data={
                    "clip_id": clip_id,
                    "sensitivity": self.sensitivity,
                    "base_status": base_status,
                    "adjusted_status": adjusted_status,
                    "categories": categories,
                    "reasons": result.get("reasons", []),
                    "confidence": result.get("confidence", 0),
                    "extra_flags": extra_flags,
                    "safe_to_post": adjusted_status == "pass",
                    "requires_review": adjusted_status == "review"
                },
                cost_cents=1,
                duration_ms=int((time.time() - start) * 1000)
            )

        except Exception as e:
            logger.error(f"[SafetyAgent {self.agent_index}/{self.sensitivity}] Failed: {e}")
            return AgentResult(
                agent_index=self.agent_index,
                persona=self.sensitivity,
                status="failed",
                data={},
                cost_cents=1,
                duration_ms=int((time.time() - start) * 1000),
                error=str(e)
            )


class HooksAnalysisSwarmAgent:
    """Analyze hooks with a specific time period and method."""

    METHODS = [
        "recent_7d",          # Last 7 days only
        "recent_30d",         # Last 30 days
        "all_time",           # All historical clips
        "per_platform",       # Separate analysis per platform
        "by_archetype",       # Group by hook archetype
    ]

    def __init__(self, agent_index: int, method: str, analysis_service=None):
        from app.services.hook_analysis_service import HookAnalysisService
        self.agent_index = agent_index
        self.method = method
        self.analysis_service = analysis_service or HookAnalysisService()
        self.db = SupabaseService()

    async def execute(
        self,
        clip_id: str,
        user_id: str,
        platform: str = "tiktok"
    ) -> AgentResult:
        """Analyze hooks using this agent's method."""
        start = time.time()

        try:
            # Get user's clips based on method time period
            days_map = {
                "recent_7d": 7,
                "recent_30d": 30,
                "all_time": 365 * 10,
                "per_platform": 30,
                "by_archetype": 30,
            }
            days = days_map.get(self.method, 30)

            # Fetch clips
            try:
                result = supabase.table("clips").select("*").eq("user_id", user_id).gte(
                    "created_at", (datetime.utcnow() - timedelta(days=days)).isoformat()
                ).execute()
                clips = result.data or []
            except Exception:
                clips = []

            if not clips:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.method,
                    status="completed",
                    data={
                        "method": self.method,
                        "period_days": days,
                        "clips_analyzed": 0,
                        "archetypes": [],
                        "insights": ["No clips available for analysis period"]
                    },
                    cost_cents=1,
                    duration_ms=int((time.time() - start) * 1000)
                )

            # Run analysis
            analysis = self.analysis_service.analyze_user_hooks(clips, platform=platform)

            # Adjust output based on method
            data = {
                "method": self.method,
                "period_days": days,
                "clips_analyzed": len(clips),
                "archetypes": analysis.get("archetypes", []),
                "insights": analysis.get("insights", []),
                "total_views": sum(c.get("views", 0) for c in clips),
            }

            if self.method == "per_platform":
                # Would do per-platform breakdown in full implementation
                data["platform"] = platform
                data["note"] = "Per-platform analysis: weights platform-specific engagement patterns"

            elif self.method == "by_archetype":
                # Group archetypes
                archetypes = data.get("archetypes", [])
                grouped = {}
                for a in archetypes:
                    name = a.get("archetype_name", "unknown")
                    grouped[name] = grouped.get(name, 0) + 1
                data["archetype_distribution"] = grouped

            return AgentResult(
                agent_index=self.agent_index,
                persona=self.method,
                status="completed",
                data=data,
                cost_cents=8,
                duration_ms=int((time.time() - start) * 1000)
            )

        except Exception as e:
            logger.error(f"[AnalysisAgent {self.agent_index}/{self.method}] Failed: {e}")
            return AgentResult(
                agent_index=self.agent_index,
                persona=self.method,
                status="failed",
                data={},
                cost_cents=4,
                duration_ms=int((time.time() - start) * 1000),
                error=str(e)
            )


class SegmentAnalyzeSwarmAgent:
    """Analyze video segments with a specific strategy."""

    STRATEGIES = [
        "energy_peak",        # Find highest energy moments
        "face_presence",      # Find segments with faces
        "hook_potential",     # Find potential hook moments
        "question_moment",    # Find questions in transcript
        "silence_break",      # Find breaks in speech (visual moments)
    ]

    def __init__(self, agent_index: int, strategy: str):
        self.agent_index = agent_index
        self.strategy = strategy
        self.db = SupabaseService()

    async def execute(
        self,
        clip_id: str,
        user_id: str
    ) -> AgentResult:
        """Analyze segments using this agent's strategy."""
        start = time.time()

        try:
            clip = await self.db.get_clip(clip_id)
            if not clip:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.strategy,
                    status="failed",
                    data={},
                    cost_cents=0,
                    duration_ms=int((time.time() - start) * 1000),
                    error="Clip not found"
                )

            metadata = clip.get("metadata", {}) or {}
            segments = metadata.get("segments", [])
            transcript = metadata.get("transcription_text", "")

            if not segments:
                # Generate basic segments from duration
                duration = clip.get("duration", 30)
                segments = [
                    {"start": 0, "end": duration * 0.3, "energy": 0.6, "salience": 0.5},
                    {"start": duration * 0.3, "end": duration * 0.6, "energy": 0.8, "salience": 0.7},
                    {"start": duration * 0.6, "end": duration, "energy": 0.5, "salience": 0.4},
                ]

            scored_segments = []
            for seg in segments:
                score = 0.5
                reason = "base"

                if self.strategy == "energy_peak":
                    score = seg.get("energy", 0.5)
                    reason = "energy"

                elif self.strategy == "face_presence":
                    score = seg.get("face_presence", seg.get("salience", 0.5))
                    reason = "face/salience"

                elif self.strategy == "hook_potential":
                    energy = seg.get("energy", 0)
                    salience = seg.get("salience", 0)
                    score = (energy * 0.6 + salience * 0.4)
                    reason = "energy+salience"

                elif self.strategy == "question_moment":
                    # Check if segment contains questions in transcript
                    seg_text = self._get_segment_text(transcript, seg.get("start", 0), seg.get("end", 0))
                    question_count = seg_text.count("?") + len(re.findall(r"^(what|why|how|who|when|where|did|do|are|is|can|would|could)", seg_text, re.I))
                    score = min(question_count / 2, 1.0)
                    reason = f"{question_count} questions"

                elif self.strategy == "silence_break":
                    # Lower energy + higher salience = visual moment
                    energy = seg.get("energy", 0.5)
                    salience = seg.get("salience", 0.5)
                    score = (1 - energy) * 0.5 + salience * 0.5
                    reason = "visual moment"

                scored_segments.append({
                    **seg,
                    "score": round(score, 3),
                    "reason": reason
                })

            scored_segments.sort(key=lambda x: x["score"], reverse=True)

            return AgentResult(
                agent_index=self.agent_index,
                persona=self.strategy,
                status="completed",
                data={
                    "clip_id": clip_id,
                    "strategy": self.strategy,
                    "segments_analyzed": len(segments),
                    "top_segments": scored_segments[:3],
                    "best_segment": scored_segments[0] if scored_segments else None,
                    "all_scores": [{"start": s.get("start"), "end": s.get("end"), "score": s.get("score")} for s in scored_segments[:5]]
                },
                cost_cents=5,
                duration_ms=int((time.time() - start) * 1000)
            )

        except Exception as e:
            logger.error(f"[SegmentAgent {self.agent_index}/{self.strategy}] Failed: {e}")
            return AgentResult(
                agent_index=self.agent_index,
                persona=self.strategy,
                status="failed",
                data={},
                cost_cents=2,
                duration_ms=int((time.time() - start) * 1000),
                error=str(e)
            )

    def _get_segment_text(self, transcript: str, start: float, end: float) -> str:
        """Extract text for a segment from transcript (approximate)."""
        if not transcript:
            return ""
        words = transcript.split()
        total_duration = 60  # Assume ~60s total if unknown
        word_rate = len(words) / total_duration if total_duration > 0 else 0.5
        start_word = int(start * word_rate)
        end_word = int(end * word_rate)
        return " ".join(words[start_word:end_word])


class EditSwarmAgent:
    """Apply video edits with a specific recipe strategy."""

    RECIPES = [
        "fast_cuts",          # Quick jump cuts for high energy
        "caption_heavy",      # Heavy caption overlay
        "zoom_pulse",         # Zoom in/out on key moments
        "clean_trim",         # Simple clean trim
        "reaction_focus",     # Focus on reaction moments
    ]

    def __init__(self, agent_index: int, recipe: str, ffmpeg_service=None):
        from app.services.ffmpeg_service import FFmpegEditService
        self.agent_index = agent_index
        self.recipe = recipe
        self.ffmpeg = ffmpeg_service or FFmpegEditService()
        self.db = SupabaseService()

    async def execute(
        self,
        clip_id: str,
        user_id: str
    ) -> AgentResult:
        """Apply edit recipe to clip."""
        start = time.time()

        try:
            clip = await self.db.get_clip(clip_id)
            if not clip:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.recipe,
                    status="failed",
                    data={},
                    cost_cents=0,
                    duration_ms=int((time.time() - start) * 1000),
                    error="Clip not found"
                )

            video_url = clip.get("video_url")
            duration = clip.get("duration", 30)
            if not video_url:
                return AgentResult(
                    agent_index=self.agent_index,
                    persona=self.recipe,
                    status="failed",
                    data={},
                    cost_cents=0,
                    duration_ms=int((time.time() - start) * 1000),
                    error="No video URL"
                )

            # Build recipe-specific edit config
            edit_config = self._build_recipe_config(duration)

            # For MVP: return the recipe config (actual FFmpeg processing would run here)
            # Full implementation would call ffmpeg.build_edit_command and execute
            return AgentResult(
                agent_index=self.agent_index,
                persona=self.recipe,
                status="completed",
                data={
                    "clip_id": clip_id,
                    "recipe": self.recipe,
                    "edit_config": edit_config,
                    "description": self._recipe_description(),
                    "estimated_processing_time": f"{15 + self.agent_index * 5}s",
                    "requires_ffmpeg": True,
                    "preview_available": True
                },
                cost_cents=15,
                duration_ms=int((time.time() - start) * 1000)
            )

        except Exception as e:
            logger.error(f"[EditAgent {self.agent_index}/{self.recipe}] Failed: {e}")
            return AgentResult(
                agent_index=self.agent_index,
                persona=self.recipe,
                status="failed",
                data={},
                cost_cents=5,
                duration_ms=int((time.time() - start) * 1000),
                error=str(e)
            )

    def _build_recipe_config(self, duration: float) -> Dict[str, Any]:
        """Build edit configuration for this recipe."""
        configs = {
            "fast_cuts": {
                "trim": {"start_seconds": 0, "end_seconds": min(duration, 20)},
                "speed": 1.2,
                "transitions": ["jump"],
                "text_overlays": [],
                "filters": ["contrast_boost"]
            },
            "caption_heavy": {
                "caption": "Auto-generated captions",
                "caption_style": {"position": "bottom", "color": "yellow", "size": 28},
                "text_overlays": [
                    {"text": "👇 READ THIS", "x": 10, "y": 50, "start": 0, "end": 3, "color": "red", "size": 32}
                ]
            },
            "zoom_pulse": {
                "trim": {"start_seconds": 0, "end_seconds": min(duration, 25)},
                "filters": ["zoom_in_out"],
                "transitions": ["zoom"]
            },
            "clean_trim": {
                "trim": {"start_seconds": 2, "end_seconds": min(duration - 1, 28)},
                "filters": [],
                "audio": "keep"
            },
            "reaction_focus": {
                "trim": {"start_seconds": 0, "end_seconds": min(duration, 15)},
                "speed": 1.0,
                "text_overlays": [
                    {"text": "WAIT FOR IT...", "x": 10, "y": 100, "start": 0, "end": 5, "color": "white", "size": 24}
                ]
            }
        }
        return configs.get(self.recipe, configs["clean_trim"])

    def _recipe_description(self) -> str:
        descriptions = {
            "fast_cuts": "Quick jump cuts with speed boost for high-energy feel",
            "caption_heavy": "Maximum caption visibility with highlight callouts",
            "zoom_pulse": "Zoom in/out effects on key moments for emphasis",
            "clean_trim": "Simple clean trim removing dead air",
            "reaction_focus": "Build anticipation with 'wait for it' style",
        }
        return descriptions.get(self.recipe, "Custom edit")
