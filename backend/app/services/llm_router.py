"""
LLM Router Service - Tiered Model Routing for MVC Agentic Pipeline

Replaces the single-provider Claude-only approach with intelligent multi-model routing.
Uses a three-tier strategy to minimize costs while maintaining output quality:

  - TIER_PREMIUM:  Claude Sonnet 4.6, GPT-5.4 - creative, high-stakes tasks
  - TIER_STANDARD: Claude Haiku 4.5, GPT-5.4 Mini, Gemini 2.5 Flash - general tasks
  - TIER_ECONOMY:  Groq Llama 3.1 8B, DeepSeek V4 Flash, GPT-4.1 Nano - classification,
                   formatting, high-volume batch tasks

Integration:
  1. Install: pip install litellm
  2. Set provider API keys as env vars
  3. Replace direct Anthropic client calls with LLMRouter.route()

Cost reduction target: 60-85% on tiered tasks vs. Claude Sonnet 4.6 baseline.
"""
from __future__ import annotations

import os
import logging
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import json
import time
import hashlib

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model Tier Definitions - sourced from market research (May 2026)
# ---------------------------------------------------------------------------

class ModelTier(str, Enum):
    PREMIUM = "premium"    # Highest quality, highest cost
    STANDARD = "standard"  # Good quality, moderate cost
    ECONOMY = "economy"    # Acceptable quality, lowest cost


@dataclass(frozen=True)
class ModelConfig:
    """Immutable configuration for a single model endpoint."""
    provider: str
    model_id: str
    litellm_name: str
    input_cost_per_1m: float
    output_cost_per_1m: float
    avg_output_tokens: int = 500
    context_window: int = 128_000
    max_output_tokens: int = 4096
    supports_caching: bool = False
    supports_batch: bool = False
    speed_tps: float = 50.0
    quality_score: float = 0.85
    env_key: str = ""

    def estimate_cost_usd(self, input_tokens: int, output_tokens: Optional[int] = None) -> float:
        out = output_tokens or self.avg_output_tokens
        return (input_tokens / 1_000_000) * self.input_cost_per_1m + (out / 1_000_000) * self.output_cost_per_1m


# ---------------------------------------------------------------------------
# Model Registry - all models available for routing
# ---------------------------------------------------------------------------
MODEL_REGISTRY: Dict[str, ModelConfig] = {
    # ========================= PREMIUM TIER =========================
    "claude-sonnet-4.6": ModelConfig(
        provider="anthropic",
        model_id="claude-sonnet-4-6-20250514",
        litellm_name="anthropic/claude-sonnet-4-6-20250514",
        input_cost_per_1m=3.00,
        output_cost_per_1m=15.00,
        avg_output_tokens=400,
        context_window=1_000_000,
        max_output_tokens=4096,
        supports_caching=True,
        supports_batch=True,
        speed_tps=80,
        quality_score=0.95,
        env_key="ANTHROPIC_API_KEY",
    ),
    "claude-opus-4.7": ModelConfig(
        provider="anthropic",
        model_id="claude-opus-4-7-20250616",
        litellm_name="anthropic/claude-opus-4-7-20250616",
        input_cost_per_1m=5.00,
        output_cost_per_1m=25.00,
        avg_output_tokens=400,
        context_window=1_000_000,
        max_output_tokens=4096,
        supports_caching=True,
        supports_batch=True,
        speed_tps=40,
        quality_score=0.98,
        env_key="ANTHROPIC_API_KEY",
    ),
    "gpt-5.4": ModelConfig(
        provider="openai",
        model_id="gpt-5.4",
        litellm_name="openai/gpt-5.4",
        input_cost_per_1m=2.50,
        output_cost_per_1m=15.00,
        avg_output_tokens=400,
        context_window=1_000_000,
        max_output_tokens=4096,
        supports_caching=True,
        supports_batch=True,
        speed_tps=80,
        quality_score=0.94,
        env_key="OPENAI_API_KEY",
    ),
    "gemini-3.1-pro": ModelConfig(
        provider="google",
        model_id="gemini-3.1-pro",
        litellm_name="gemini/gemini-3.1-pro",
        input_cost_per_1m=2.00,
        output_cost_per_1m=12.00,
        avg_output_tokens=400,
        context_window=1_000_000,
        max_output_tokens=8192,
        supports_caching=True,
        supports_batch=True,
        speed_tps=100,
        quality_score=0.93,
        env_key="GEMINI_API_KEY",
    ),
    # ========================= STANDARD TIER =========================
    "claude-haiku-4.5": ModelConfig(
        provider="anthropic",
        model_id="claude-haiku-4-5-20251001",
        litellm_name="anthropic/claude-haiku-4-5-20251001",
        input_cost_per_1m=1.00,
        output_cost_per_1m=5.00,
        avg_output_tokens=300,
        context_window=200_000,
        max_output_tokens=4096,
        supports_caching=True,
        supports_batch=True,
        speed_tps=200,
        quality_score=0.82,
        env_key="ANTHROPIC_API_KEY",
    ),
    "gpt-5.4-mini": ModelConfig(
        provider="openai",
        model_id="gpt-5.4-mini",
        litellm_name="openai/gpt-5.4-mini",
        input_cost_per_1m=0.75,
        output_cost_per_1m=4.50,
        avg_output_tokens=300,
        context_window=400_000,
        max_output_tokens=4096,
        supports_caching=True,
        supports_batch=True,
        speed_tps=150,
        quality_score=0.83,
        env_key="OPENAI_API_KEY",
    ),
    "gemini-2.5-flash": ModelConfig(
        provider="google",
        model_id="gemini-2.5-flash",
        litellm_name="gemini/gemini-2.5-flash",
        input_cost_per_1m=0.30,
        output_cost_per_1m=2.50,
        avg_output_tokens=300,
        context_window=1_000_000,
        max_output_tokens=8192,
        supports_caching=True,
        supports_batch=True,
        speed_tps=250,
        quality_score=0.80,
        env_key="GEMINI_API_KEY",
    ),
    "groq-llama-70b": ModelConfig(
        provider="groq",
        model_id="llama-3.3-70b-versatile",
        litellm_name="groq/llama-3.3-70b-versatile",
        input_cost_per_1m=0.59,
        output_cost_per_1m=0.79,
        avg_output_tokens=300,
        context_window=128_000,
        max_output_tokens=4096,
        supports_caching=False,
        supports_batch=False,
        speed_tps=394,
        quality_score=0.81,
        env_key="GROQ_API_KEY",
    ),
    # ========================= ECONOMY TIER =========================
    "groq-llama-8b": ModelConfig(
        provider="groq",
        model_id="llama-3.1-8b-instant",
        litellm_name="groq/llama-3.1-8b-instant",
        input_cost_per_1m=0.05,
        output_cost_per_1m=0.08,
        avg_output_tokens=200,
        context_window=128_000,
        max_output_tokens=4096,
        supports_caching=False,
        supports_batch=False,
        speed_tps=840,
        quality_score=0.65,
        env_key="GROQ_API_KEY",
    ),
    "deepseek-v4-flash": ModelConfig(
        provider="deepseek",
        model_id="deepseek-v4-flash",
        litellm_name="deepseek/deepseek-v4-flash",
        input_cost_per_1m=0.14,
        output_cost_per_1m=0.28,
        avg_output_tokens=200,
        context_window=1_000_000,
        max_output_tokens=384_000,
        supports_caching=True,
        supports_batch=True,
        speed_tps=120,
        quality_score=0.77,
        env_key="DEEPSEEK_API_KEY",
    ),
    "gpt-4.1-nano": ModelConfig(
        provider="openai",
        model_id="gpt-4.1-nano",
        litellm_name="openai/gpt-4.1-nano",
        input_cost_per_1m=0.10,
        output_cost_per_1m=0.40,
        avg_output_tokens=200,
        context_window=1_000_000,
        max_output_tokens=4096,
        supports_caching=True,
        supports_batch=True,
        speed_tps=300,
        quality_score=0.70,
        env_key="OPENAI_API_KEY",
    ),
    "gemini-2.5-flash-lite": ModelConfig(
        provider="google",
        model_id="gemini-2.5-flash-lite",
        litellm_name="gemini/gemini-2.5-flash-lite",
        input_cost_per_1m=0.10,
        output_cost_per_1m=0.40,
        avg_output_tokens=200,
        context_window=1_000_000,
        max_output_tokens=8192,
        supports_caching=True,
        supports_batch=True,
        speed_tps=350,
        quality_score=0.68,
        env_key="GEMINI_API_KEY",
    ),
    "deepseek-v4-pro": ModelConfig(
        provider="deepseek",
        model_id="deepseek-v4-pro",
        litellm_name="deepseek/deepseek-v4-pro",
        input_cost_per_1m=0.435,
        output_cost_per_1m=0.87,
        avg_output_tokens=300,
        context_window=1_000_000,
        max_output_tokens=384_000,
        supports_caching=True,
        supports_batch=True,
        speed_tps=80,
        quality_score=0.86,
        env_key="DEEPSEEK_API_KEY",
    ),
}

# ---------------------------------------------------------------------------
# Task-to-Tier Mapping - the heart of the routing strategy
# ---------------------------------------------------------------------------
TASK_MODEL_MAP: Dict[str, Dict[str, Any]] = {
    # Hook generation - PREMIUM: creative quality is critical
    "hook_generate": {
        "tier": ModelTier.PREMIUM,
        "models": ["claude-sonnet-4.6", "gpt-5.4", "deepseek-v4-pro"],
        "rationale": "Hook quality directly impacts clip virality. Premium models only.",
        "cost_reduction_vs_baseline": 0,
    },
    # Edit instructions - PREMIUM: requires nuanced understanding
    "edit_instructions": {
        "tier": ModelTier.PREMIUM,
        "models": ["claude-sonnet-4.6", "gpt-5.4"],
        "rationale": "Edit instructions need precise video understanding. Premium models.",
        "cost_reduction_vs_baseline": 0,
    },
    # Segment analysis - STANDARD: structured output, less creative
    "segment_analyze": {
        "tier": ModelTier.STANDARD,
        "models": ["gpt-5.4-mini", "groq-llama-70b", "claude-haiku-4.5"],
        "rationale": "Segment scoring is structured analysis. Standard tier is sufficient.",
        "cost_reduction_vs_baseline": 0.75,
    },
    # Safety classification - ECONOMY: pattern matching task
    "safety_check": {
        "tier": ModelTier.ECONOMY,
        "models": ["gpt-4.1-nano", "groq-llama-8b", "deepseek-v4-flash", "gemini-2.5-flash-lite"],
        "rationale": "Safety is primarily classification. Economy models excel here.",
        "cost_reduction_vs_baseline": 0.95,
    },
    # Caption generation - STANDARD: creative but structured
    "caption_generate": {
        "tier": ModelTier.STANDARD,
        "models": ["gpt-5.4-mini", "gemini-2.5-flash", "deepseek-v4-flash"],
        "rationale": "Captions need platform-aware formatting. Standard tier handles well.",
        "cost_reduction_vs_baseline": 0.80,
    },
    # Hashtag optimization - ECONOMY: pattern-based
    "hashtag_optimize": {
        "tier": ModelTier.ECONOMY,
        "models": ["gpt-4.1-nano", "gemini-2.5-flash-lite", "deepseek-v4-flash"],
        "rationale": "Hashtag generation is highly pattern-based. Economy tier optimal.",
        "cost_reduction_vs_baseline": 0.93,
    },
    # Post text generation - STANDARD: needs platform awareness
    "post_text_generate": {
        "tier": ModelTier.STANDARD,
        "models": ["claude-haiku-4.5", "gpt-5.4-mini", "gemini-2.5-flash"],
        "rationale": "Post text needs platform-specific formatting but isn't high-creative.",
        "cost_reduction_vs_baseline": 0.78,
    },
    # Music mood matching - ECONOMY: classification task
    "music_match": {
        "tier": ModelTier.ECONOMY,
        "models": ["gpt-4.1-nano", "groq-llama-8b", "deepseek-v4-flash"],
        "rationale": "Music matching is mood classification from transcript. Economy tier.",
        "cost_reduction_vs_baseline": 0.95,
    },
    # A/B test variant gen - STANDARD: creative variations
    "ab_test_variants": {
        "tier": ModelTier.STANDARD,
        "models": ["gpt-5.4-mini", "deepseek-v4-flash", "gemini-2.5-flash"],
        "rationale": "Variant generation is templated creativity. Standard tier is sufficient.",
        "cost_reduction_vs_baseline": 0.80,
    },
    # Thumbnail text - ECONOMY: short-form text
    "thumbnail_text": {
        "tier": ModelTier.ECONOMY,
        "models": ["gpt-4.1-nano", "gemini-2.5-flash-lite", "groq-llama-8b"],
        "rationale": "Thumbnail text is very short. Economy tier is perfect.",
        "cost_reduction_vs_baseline": 0.93,
    },
    # Transcription routing - ECONOMY: simple routing decision
    "transcription_route": {
        "tier": ModelTier.ECONOMY,
        "models": ["gpt-4.1-nano", "groq-llama-8b"],
        "rationale": "Routing decisions are trivial classification. Economy only.",
        "cost_reduction_vs_baseline": 0.97,
    },
    # Content enrichment (metadata) - ECONOMY: extraction
    "content_enrich": {
        "tier": ModelTier.ECONOMY,
        "models": ["deepseek-v4-flash", "gpt-4.1-nano", "gemini-2.5-flash-lite"],
        "rationale": "Metadata extraction is structured. Economy tier handles well.",
        "cost_reduction_vs_baseline": 0.92,
    },
    # Remix variant generation - STANDARD: creative adaptation
    "remix_generate": {
        "tier": ModelTier.STANDARD,
        "models": ["gpt-5.4-mini", "claude-haiku-4.5", "deepseek-v4-flash"],
        "rationale": "Remixing needs understanding of format differences. Standard tier.",
        "cost_reduction_vs_baseline": 0.78,
    },
    # Hooks analysis - STANDARD: analytical with creative elements
    "hooks_analysis": {
        "tier": ModelTier.STANDARD,
        "models": ["gpt-5.4-mini", "groq-llama-70b", "deepseek-v4-flash"],
        "rationale": "Hook analysis combines metrics + creativity assessment. Standard.",
        "cost_reduction_vs_baseline": 0.75,
    },
    # Title generation - STANDARD: needs click-worthy creativity
    "title_generate": {
        "tier": ModelTier.STANDARD,
        "models": ["gpt-5.4-mini", "claude-haiku-4.5", "deepseek-v4-flash"],
        "rationale": "Titles need click-worthy creativity but are short. Standard tier optimal.",
        "cost_reduction_vs_baseline": 0.78,
    },
    # Content moderation classification - ECONOMY: binary classification
    "moderation_classify": {
        "tier": ModelTier.ECONOMY,
        "models": ["gpt-4.1-nano", "groq-llama-8b"],
        "rationale": "Moderation is binary/multiclass classification. Economy tier sufficient.",
        "cost_reduction_vs_baseline": 0.95,
    },
}


# ---------------------------------------------------------------------------
# Semantic Cache - Redis-backed response caching
# ---------------------------------------------------------------------------

class SemanticCache:
    """Simple embedding-based cache for AI responses."""

    def __init__(self, redis_client=None, ttl_seconds: int = 3600):
        self.redis = redis_client
        self.ttl = ttl_seconds
        self._local_cache: Dict[str, Any] = {}
        self._hit_count = 0
        self._miss_count = 0

    def _make_key(self, task_type: str, prompt_hash: str, model_tier: str) -> str:
        return f"llm_cache:{task_type}:{model_tier}:{prompt_hash}"

    def _hash_prompt(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    async def get(self, task_type: str, prompt: str, model_tier: str) -> Optional[str]:
        key = self._make_key(task_type, self._hash_prompt(prompt), model_tier)
        if self.redis:
            try:
                cached = await self.redis.get(key)
                if cached:
                    self._hit_count += 1
                    return cached.decode() if isinstance(cached, bytes) else cached
            except Exception:
                pass
        else:
            cached = self._local_cache.get(key)
            if cached:
                self._hit_count += 1
                return cached
        self._miss_count += 1
        return None

    async def set(self, task_type: str, prompt: str, model_tier: str, response: str) -> None:
        key = self._make_key(task_type, self._hash_prompt(prompt), model_tier)
        if self.redis:
            try:
                await self.redis.setex(key, self.ttl, response)
            except Exception:
                pass
        else:
            self._local_cache[key] = response

    @property
    def hit_rate(self) -> float:
        total = self._hit_count + self._miss_count
        return self._hit_count / total if total > 0 else 0.0

    def stats(self) -> Dict[str, Any]:
        return {"hits": self._hit_count, "misses": self._miss_count, "hit_rate": self.hit_rate}


# ---------------------------------------------------------------------------
# LLM Router - the main service
# ---------------------------------------------------------------------------

class LLMRouter:
    """Intelligent multi-model router for MVC agent tasks."""

    def __init__(self, redis_client=None, cache_ttl: int = 3600, default_fallback: str = "claude-sonnet-4.6"):
        self.models = MODEL_REGISTRY
        self.tasks = TASK_MODEL_MAP
        self.cache = SemanticCache(redis_client, cache_ttl)
        self.fallback = default_fallback
        self._usage_stats: Dict[str, Dict[str, Any]] = {}
        self._cost_stats: Dict[str, float] = {}

    def select_model(self, task_type: str, force_tier: Optional[ModelTier] = None,
                     force_model: Optional[str] = None, prefer_speed: bool = False) -> ModelConfig:
        """Select the best model for a given task.

        Priority:
          1. Explicitly forced model (if valid)
          2. Explicitly forced tier (pick cheapest in tier across ALL models)
          3. Task's default model list (sorted by cost)
          4. Fallback to default fallback model
        """
        if force_model and force_model in self.models:
            return self.models[force_model]

        task_config = self.tasks.get(task_type)
        if not task_config:
            logger.warning(f"Unknown task type '{task_type}', falling back to {self.fallback}")
            return self.models[self.fallback]

        if force_tier:
            # When tier is forced, consider ALL models in that tier, not just task defaults
            tier_models = [m for m in self.models.values() if self._get_model_tier(m.model_id) == force_tier]
            available = [m for m in tier_models if self._has_api_key(m)]
        else:
            candidate_ids = task_config["models"]
            available = [
                self.models[mid] for mid in candidate_ids
                if mid in self.models and self._has_api_key(self.models[mid])
            ]

        if not available:
            logger.warning(f"No available models for task '{task_type}', using fallback")
            return self.models[self.fallback]

        if prefer_speed:
            available.sort(key=lambda m: m.speed_tps, reverse=True)
        else:
            available.sort(key=lambda m: m.input_cost_per_1m)

        return available[0]

    def _get_model_tier(self, model_id: str) -> Optional[ModelTier]:
        """Determine which tier a model belongs to based on its quality score."""
        model = self.models.get(model_id)
        if not model:
            return None
        # Quality score thresholds: >=0.90 = PREMIUM, >=0.75 = STANDARD, else ECONOMY
        if model.quality_score >= 0.90:
            return ModelTier.PREMIUM
        elif model.quality_score >= 0.75:
            return ModelTier.STANDARD
        else:
            return ModelTier.ECONOMY

    def _has_api_key(self, model: ModelConfig) -> bool:
        if not model.env_key:
            return True
        return bool(os.environ.get(model.env_key))

    async def call(self, task_type: str, prompt: str, system_prompt: Optional[str] = None,
                   temperature: float = 0.7, max_tokens: Optional[int] = None,
                   force_model: Optional[str] = None, use_cache: bool = True, **kwargs) -> Dict[str, Any]:
        """Execute an LLM call with automatic routing, caching, and cost tracking."""
        model_cfg = self.select_model(task_type, force_model=force_model)
        cache_key_tier = model_cfg.model_id

        # Check cache
        if use_cache:
            cached = await self.cache.get(task_type, prompt, cache_key_tier)
            if cached is not None:
                return {
                    "content": cached, "model_used": model_cfg.model_id,
                    "cost_usd": 0.0, "tokens_in": 0, "tokens_out": 0,
                    "duration_ms": 0, "cached": True,
                }

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start_time = time.time()
        try:
            response = await self._execute_litellm(
                model_cfg=model_cfg, messages=messages,
                temperature=temperature,
                max_tokens=max_tokens or model_cfg.max_output_tokens, **kwargs
            )
        except Exception as e:
            logger.error(f"LLM call failed for {task_type} with {model_cfg.model_id}: {e}")
            if model_cfg.model_id != self.fallback:
                logger.info(f"Retrying with fallback model {self.fallback}")
                model_cfg = self.models[self.fallback]
                response = await self._execute_litellm(
                    model_cfg=model_cfg, messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens or model_cfg.max_output_tokens, **kwargs
                )
            else:
                raise

        duration_ms = int((time.time() - start_time) * 1000)
        content = response["choices"][0]["message"]["content"]
        usage = response.get("usage", {})
        tokens_in = usage.get("prompt_tokens", len(prompt) // 4)
        tokens_out = usage.get("completion_tokens", len(content) // 4)
        cost_usd = model_cfg.estimate_cost_usd(tokens_in, tokens_out)

        self._update_stats(task_type, model_cfg.model_id, cost_usd, tokens_in, tokens_out)

        if use_cache:
            await self.cache.set(task_type, prompt, cache_key_tier, content)

        return {
            "content": content, "model_used": model_cfg.model_id,
            "cost_usd": cost_usd, "tokens_in": tokens_in,
            "tokens_out": tokens_out, "duration_ms": duration_ms, "cached": False,
        }

    async def _execute_litellm(self, model_cfg: ModelConfig, messages: List[Dict[str, str]],
                               temperature: float, max_tokens: int, **kwargs) -> Dict[str, Any]:
        try:
            import litellm
            litellm.set_verbose = False
            litellm.drop_params = True
            response = await litellm.acompletion(
                model=model_cfg.litellm_name, messages=messages,
                temperature=temperature, max_tokens=max_tokens,
                api_key=os.environ.get(model_cfg.env_key) if model_cfg.env_key else None, **kwargs
            )
            return response
        except ImportError:
            return await self._direct_http_call(model_cfg, messages, temperature, max_tokens)

    async def _direct_http_call(self, model_cfg: ModelConfig, messages: List[Dict[str, str]],
                                temperature: float, max_tokens: int) -> Dict[str, Any]:
        import httpx
        api_key = os.environ.get(model_cfg.env_key) if model_cfg.env_key else ""
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        provider_urls = {
            "anthropic": "https://api.anthropic.com/v1/messages",
            "openai": "https://api.openai.com/v1/chat/completions",
            "groq": "https://api.groq.com/openai/v1/chat/completions",
            "deepseek": "https://api.deepseek.com/v1/chat/completions",
            "google": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
        }
        url = provider_urls.get(model_cfg.provider, provider_urls["openai"])
        payload = {"model": model_cfg.model_id, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens}
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()

    async def call_batch(self, task_type: str, prompts: List[str],
                         system_prompt: Optional[str] = None, temperature: float = 0.7) -> List[Any]:
        tasks = [self.call(task_type, p, system_prompt, temperature, use_cache=True) for p in prompts]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def _update_stats(self, task: str, model: str, cost: float, tin: int, tout: int) -> None:
        key = f"{task}:{model}"
        if key not in self._usage_stats:
            self._usage_stats[key] = {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost": 0.0}
        self._usage_stats[key]["calls"] += 1
        self._usage_stats[key]["tokens_in"] += tin
        self._usage_stats[key]["tokens_out"] += tout
        self._usage_stats[key]["cost"] += cost
        self._cost_stats[task] = self._cost_stats.get(task, 0.0) + cost

    def get_stats(self) -> Dict[str, Any]:
        return {
            "usage_by_task_model": self._usage_stats,
            "cost_by_task": self._cost_stats,
            "cache_stats": self.cache.stats(),
            "total_cost": sum(self._cost_stats.values()),
        }

    def get_model_recommendations(self) -> List[Dict[str, Any]]:
        recommendations = []
        for task_name, config in self.tasks.items():
            tier = config["tier"]
            primary_model_id = config["models"][0]
            primary_model = self.models.get(primary_model_id)
            if not primary_model:
                continue
            cost_reduction = config["cost_reduction_vs_baseline"]
            est_input = 2000
            est_output = primary_model.avg_output_tokens
            est_cost = primary_model.estimate_cost_usd(est_input, est_output)
            recommendations.append({
                "task": task_name, "tier": tier.value,
                "recommended_model": primary_model_id, "provider": primary_model.provider,
                "est_cost_per_call_usd": round(est_cost, 5),
                "cost_reduction_vs_claude_sonnet": f"{int(cost_reduction * 100)}%",
                "speed_tps": primary_model.speed_tps,
                "quality_score": primary_model.quality_score,
                "rationale": config["rationale"],
                "fallback_models": config["models"][1:3],
            })
        return recommendations

    def print_routing_table(self) -> None:
        print("=" * 110)
        print(f"{'MVC Agent Task':<25} {'Tier':<10} {'Primary Model':<22} {'Cost/Call':<12} {'Savings':<10} {'Speed':<10}")
        print("=" * 110)
        for rec in self.get_model_recommendations():
            print(f"{rec['task']:<25} {rec['tier']:<10} {rec['recommended_model']:<22} "
                  f"${rec['est_cost_per_call_usd']:<11} {rec['cost_reduction_vs_claude_sonnet']:<10} "
                  f"{rec['speed_tps']} tps")
        print("=" * 110)


# Singleton router instance
_router: Optional[LLMRouter] = None


def get_router(redis_client=None) -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter(redis_client=redis_client)
    return _router
