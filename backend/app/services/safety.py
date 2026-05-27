"""
Content safety, moderation, and enrichment services — all routed through LLMRouter.

Replaces direct OpenAI API calls with tiered multi-model routing:
  - Content moderation → ECONOMY tier (GPT-4.1 Nano)
  - Caption generation → STANDARD tier (GPT-5.4 Mini)
  - Hashtag generation → ECONOMY tier (GPT-4.1 Nano)
  - Title generation → STANDARD tier (GPT-5.4 Mini)

All downstream consumers (LangGraph pipeline, swarm agents) get routing transparently.
"""
import logging
import os
from typing import Dict, Any, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_router():
    """Lazy import to avoid circular dependencies."""
    from app.services.llm_router import get_router
    return get_router()


class SafetyCheckService:
    """Content safety and moderation checks for generated clips."""

    SENSITIVE_CATEGORIES = [
        "news_political", "health", "finance", "children",
        "identifiable_individual", "violent_graphic"
    ]

    FLAG_KEYWORDS = {
        "news_political": [
            "election", "vote", "politician", "president", "congress",
            "senate", "legislation", "policy", "campaign", "party"
        ],
        "health": [
            "medical advice", "treatment", "diagnosis", "prescription",
            "medication", "cure", "disease", "condition"
        ],
        "finance": [
            "investment advice", "stock tip", "guaranteed return",
            "financial advice", "buy this", "sell now", "crypto"
        ],
        "children": [
            "child", "minor", "underage", "kid", "teenager"
        ],
        "violent_graphic": [
            "blood", "gore", "death", "killed", "murder", "attack",
            "violence", "weapon", "gun", "shooting"
        ]
    }

    async def check_content(self, text: str, video_path: Optional[str] = None) -> Dict[str, Any]:
        """Run content safety checks on clip text and video."""
        result = {
            "status": "pass",
            "categories": [],
            "confidence": 0.0,
            "reasons": []
        }

        # Keyword-based checks
        text_lower = text.lower()
        for category, keywords in self.FLAG_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    if category not in result["categories"]:
                        result["categories"].append(category)
                        result["reasons"].append(f"Keyword '{keyword}' flagged for {category}")

        # AI-based moderation via LLMRouter (ECONOMY tier)
        if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
            try:
                ai_result = await self._ai_moderation(text)
                if ai_result["flagged"]:
                    result["categories"].extend(ai_result["categories"])
                    result["reasons"].extend(ai_result["reasons"])
            except Exception as e:
                logger.warning(f"[Safety] AI moderation failed: {e}")

        if result["categories"]:
            sensitive_found = any(cat in self.SENSITIVE_CATEGORIES for cat in result["categories"])
            result["status"] = "review" if sensitive_found else "pass"

        result["confidence"] = min(len(result["categories"]) * 0.3, 1.0)
        return result

    async def _ai_moderation(self, text: str) -> Dict[str, Any]:
        """AI moderation via LLMRouter (ECONOMY tier classification)."""
        router = _get_router()
        result = await router.call(
            task_type="moderation_classify",
            prompt=f"Analyze this content for safety issues. Return JSON with 'flagged' (bool), 'categories' (list of strings), and 'reasons' (list of strings):\n\n{text[:1000]}",
            system_prompt="You are a content moderation classifier. Identify: hate, harassment, violence, sexual content, self-harm, illegal acts. Return JSON only.",
            temperature=0.1,
            max_tokens=200,
        )

        try:
            import json
            data = json.loads(result["content"])
            flagged = data.get("flagged", False)
            categories = data.get("categories", [])
            reasons = data.get("reasons", [])

            # If the model returned string categories instead of list
            if isinstance(categories, str):
                categories = [categories] if categories else []
            if isinstance(reasons, str):
                reasons = [reasons] if reasons else []

            logger.info(f"[Safety] Moderation via {result['model_used']} "
                        f"flagged={flagged} cost=${result['cost_usd']:.5f}")

            return {"flagged": flagged, "categories": categories, "reasons": reasons}
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"[Safety] Failed to parse moderation response: {e}")
            return {"flagged": False, "categories": [], "reasons": []}

    def check_copyright(self, text: str) -> Dict[str, Any]:
        """Basic copyright checks."""
        result = {"likely_infringing": False, "reasons": []}
        phrases = ["copyright", "all rights reserved", "do not copy", "not for redistribution", "proprietary"]
        text_lower = text.lower()
        for phrase in phrases:
            if phrase in text_lower:
                result["reasons"].append(f"Found copyright phrase: '{phrase}'")
        result["likely_infringing"] = len(result["reasons"]) > 0
        return result

    def generate_safety_report(self, clip_id: str, checks: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a human-readable safety report."""
        return {
            "clip_id": clip_id,
            "overall_status": checks["status"],
            "requires_human_review": checks["status"] == "review",
            "categories": checks["categories"],
            "explanation": "; ".join(checks["reasons"]) if checks["reasons"] else "No issues detected",
            "confidence": checks["confidence"],
            "recommended_action": (
                "Block" if checks["status"] == "block"
                else "Review" if checks["status"] == "review"
                else "Approve"
            )
        }


class ContentEnrichmentService:
    """Generate captions, hashtags, and titles via LLMRouter tiered routing.

    Same public interface as before — all downstream consumers (LangGraph pipeline,
    swarm agents) get automatic cost optimization transparently.
    """

    def __init__(self):
        self._last_model_used: str = ""
        self._last_cost_usd: float = 0.0

    @property
    def last_model_used(self) -> str:
        return self._last_model_used

    @property
    def last_cost_usd(self) -> float:
        return self._last_cost_usd

    async def generate_caption(self, transcript: str, niche: str, platform: str, max_length: int = 150) -> str:
        """Generate caption via LLMRouter (STANDARD tier: GPT-5.4 Mini / Claude Haiku)."""
        if not _has_any_api_key():
            return transcript[:max_length] if transcript else "Check out this clip!"

        router = _get_router()
        try:
            result = await router.call(
                task_type="caption_generate",
                prompt=f"Write a catchy caption (max {max_length} chars) for this {platform} video:\n\n{transcript[:500]}",
                system_prompt=f"You are a social media expert for {niche} content. Write engaging {platform} captions. Return ONLY the caption text, no quotes.",
                temperature=0.7,
                max_tokens=100,
            )
            self._last_model_used = result["model_used"]
            self._last_cost_usd = result["cost_usd"]
            caption = result["content"].strip().strip('"').strip("'")[:max_length]
            logger.info(f"[Enrichment] Caption via {result['model_used']} cost=${result['cost_usd']:.5f}")
            return caption
        except Exception as e:
            logger.error(f"[Enrichment] Caption generation failed: {e}")
            return transcript[:max_length]

    async def generate_hashtags(self, transcript: str, niche: str, platform: str, count: int = 5) -> List[str]:
        """Generate hashtags via LLMRouter (ECONOMY tier: GPT-4.1 Nano)."""
        if not _has_any_api_key():
            return [f"#{niche.replace(' ', '')}", f"#{platform}content", "#viral", "#trending", "#fyp"]

        router = _get_router()
        try:
            result = await router.call(
                task_type="hashtag_optimize",
                prompt=f"Generate {count} relevant hashtags for this {platform} {niche} content:\n\n{transcript[:300]}",
                system_prompt=f"Generate {count} relevant hashtags for {platform} {niche} content. Return ONLY comma-separated hashtags, no explanation.",
                temperature=0.5,
                max_tokens=50,
            )
            self._last_model_used = result["model_used"]
            self._last_cost_usd += result["cost_usd"]
            hashtags_text = result["content"].strip()

            # Parse hashtags
            hashtags = [tag.strip() for tag in hashtags_text.replace("\n", ",").split(",") if tag.strip()]
            hashtags = [tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]
            hashtags = [h for h in hashtags if len(h) > 1][:count]

            logger.info(f"[Enrichment] Hashtags via {result['model_used']} cost=${result['cost_usd']:.5f}")
            return hashtags if hashtags else [f"#{niche.replace(' ', '')}", "#viral"]
        except Exception as e:
            logger.error(f"[Enrichment] Hashtag generation failed: {e}")
            return [f"#{niche.replace(' ', '')}", "#content", "#viral"]

    async def generate_title(self, transcript: str, niche: str) -> str:
        """Generate title via LLMRouter (STANDARD tier: GPT-5.4 Mini)."""
        if not _has_any_api_key():
            sentences = transcript.split(".")
            return sentences[0][:80] if sentences else "Untitled Clip"

        router = _get_router()
        try:
            result = await router.call(
                task_type="title_generate",
                prompt=f"Write a click-worthy title (max 60 chars) for this {niche} clip:\n\n{transcript[:300]}",
                system_prompt=f"You write click-worthy, concise titles for {niche} short-form video clips. Max 60 characters. Return ONLY the title, no quotes.",
                temperature=0.8,
                max_tokens=50,
            )
            self._last_model_used = result["model_used"]
            self._last_cost_usd += result["cost_usd"]
            title = result["content"].strip().strip('"').strip("'")[:60]
            logger.info(f"[Enrichment] Title via {result['model_used']} cost=${result['cost_usd']:.5f}")
            return title
        except Exception as e:
            logger.error(f"[Enrichment] Title generation failed: {e}")
            return transcript[:60]


def _has_any_api_key() -> bool:
    """Check if any LLM provider API key is configured."""
    return bool(
        settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY or
        settings.GROQ_API_KEY or settings.DEEPSEEK_API_KEY or settings.GEMINI_API_KEY
    )
