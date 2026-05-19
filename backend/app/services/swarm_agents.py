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
