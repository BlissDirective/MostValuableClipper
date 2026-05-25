"""Swarm orchestrator — coordinates parallel agent execution.

The orchestrator:
1. Validates swarm configs and tier limits
2. Spawns N agents in parallel via asyncio.gather
3. Tracks per-agent costs and results
4. Publishes job status to the queue
5. Returns a consolidated result with best-pick logic
"""

import logging
import asyncio
import uuid
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from app.models import (
    SwarmJob, SwarmJobType, SwarmJobStatus,
    SwarmAgentResult, SwarmTier
)
from app.services.swarm_config_service import SwarmConfigService, SwarmJobService
from app.services.swarm_agents import (
    HookSwarmAgent, RemixSwarmAgent, PostSwarmAgent,
    ABTestSwarmAgent, MusicMatchSwarmAgent, ThumbnailSwarmAgent,
    SafetySwarmAgent, HooksAnalysisSwarmAgent, SegmentAnalyzeSwarmAgent,
    EditSwarmAgent, AgentResult
)
from app.services.queue import QueueService
from app.services.database import SupabaseService

logger = logging.getLogger(__name__)


class SwarmOrchestrator:
    """Execute swarm jobs with parallel agents, cost tracking, and tier enforcement."""

    def __init__(self):
        self.config_service = SwarmConfigService()
        self.job_service = SwarmJobService()
        self.queue = QueueService()
        self.db = SupabaseService()

    # ─────────────────────────────────────────────────────────────
    # Hook Swarm
    # ─────────────────────────────────────────────────────────────

    async def execute_hook_swarm(
        self,
        clip_id: str,
        user_id: str,
        platform: str,
        agent_count: Optional[int] = None,
        persona_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate hooks in parallel with multiple personas.

        Uses user's custom allocation unless agent_count is explicitly provided.

        Returns:
            {
                "job_id": str,
                "agents": int,
                "results": List[dict],
                "best_hook": dict,
                "total_cost_cents": int,
                "duration_ms": int,
            }
        """
        config = await self.config_service.get_config(user_id)
        # Use custom allocation or explicit override
        allocated = config.get_pool_agents("hook")
        requested = agent_count if agent_count is not None else allocated
        max_agents = min(requested, allocated)

        # Enforce tier limit
        if max_agents <= 0:
            return {"error": "Hook swarm disabled or limit reached", "job_id": None}

        # Check budget with pool-specific cost
        if not await self.config_service.check_budget(user_id, "hook", max_agents):
            return {"error": "Daily budget exceeded", "job_id": None}

        if "hook" not in config.enabled_pools:
            return {"error": "Hook swarm pool disabled", "job_id": None}

        # Create job record
        job_id = str(uuid.uuid4())
        job = SwarmJob(
            job_id=job_id,
            user_id=user_id,
            job_type=SwarmJobType.hook,
            status=SwarmJobStatus.running,
            total_agents=max_agents,
        )
        await self.job_service.create_job(job)
        await self.queue.enqueue("swarm_jobs", job.model_dump(mode="json"))

        # Select personas
        available_personas = HookSwarmAgent.PERSONAS
        if persona_filter:
            personas = [p for p in persona_filter if p in available_personas]
            if not personas:
                personas = available_personas[:max_agents]
        else:
            personas = available_personas[:max_agents]

        # Ensure we don't exceed agent count
        personas = personas[:max_agents]

        # Spawn agents
        agents = [
            HookSwarmAgent(agent_index=i, persona=personas[i])
            for i in range(len(personas))
        ]

        start_time = time.time()
        results = await self._run_agents(agents, job_id, clip_id, platform, user_id)
        duration_ms = int((time.time() - start_time) * 1000)

        # Pick best hook (highest estimated retention)
        completed = [r for r in results if r.status == "completed" and r.data]
        best_hook = None
        if completed:
            best = max(completed, key=lambda r: r.data.get("estimated_retention", 0))
            best_hook = best.data

        total_cost = sum(r.cost_cents for r in results)

        # Update job
        job.status = SwarmJobStatus.completed if completed else SwarmJobStatus.failed
        job.completed_agents = len(completed)
        job.failed_agents = len(results) - len(completed)
        job.cost_cents = total_cost
        job.completed_at = datetime.now(timezone.utc)
        job.results_summary = {
            "clip_id": clip_id,
            "platform": platform,
            "personas_used": personas[:len(agents)],
            "best_persona": best.persona if best else None,
            "total_agents": len(agents),
            "completed": len(completed),
            "failed": len(results) - len(completed),
        }
        await self.job_service.update_job(job)
        await self.queue.mark_job_complete(job_id, job.model_dump(mode="json"))

        return {
            "job_id": job_id,
            "agents": len(agents),
            "results": [self._serialize_result(r) for r in results],
            "best_hook": best_hook,
            "total_cost_cents": total_cost,
            "duration_ms": duration_ms,
        }

    # ─────────────────────────────────────────────────────────────
    # Remix Swarm
    # ─────────────────────────────────────────────────────────────

    async def execute_remix_swarm(
        self,
        clip_id: str,
        user_id: str,
        agent_count: Optional[int] = None,
        strategy_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Remix a clip in parallel with different strategies.

        Uses user's custom allocation unless agent_count is explicitly provided.

        Returns:
            {
                "job_id": str,
                "agents": int,
                "variants": List[dict],
                "best_variant": dict,
                "total_cost_cents": int,
                "duration_ms": int,
            }
        """
        config = await self.config_service.get_config(user_id)
        # Use custom allocation or explicit override
        allocated = config.get_pool_agents("remix")
        requested = agent_count if agent_count is not None else allocated
        max_agents = min(requested, allocated)

        if max_agents <= 0:
            return {"error": "Remix swarm disabled or limit reached", "job_id": None}

        # Check budget with pool-specific cost
        if not await self.config_service.check_budget(user_id, "remix", max_agents):
            return {"error": "Daily budget exceeded", "job_id": None}

        if "remix" not in config.enabled_pools:
            return {"error": "Remix swarm pool disabled", "job_id": None}

        job_id = str(uuid.uuid4())
        job = SwarmJob(
            job_id=job_id,
            user_id=user_id,
            job_type=SwarmJobType.remix,
            status=SwarmJobStatus.running,
            total_agents=max_agents,
        )
        await self.job_service.create_job(job)
        await self.queue.enqueue("swarm_jobs", job.model_dump(mode="json"))

        available_strategies = RemixSwarmAgent.STRATEGIES
        if strategy_filter:
            strategies = [s for s in strategy_filter if s in available_strategies]
            if not strategies:
                strategies = available_strategies[:max_agents]
        else:
            strategies = available_strategies[:max_agents]
        strategies = strategies[:max_agents]

        agents = [
            RemixSwarmAgent(agent_index=i, strategy=strategies[i])
            for i in range(len(strategies))
        ]

        start_time = time.time()
        results = await self._run_agents(agents, job_id, clip_id, "", user_id)
        duration_ms = int((time.time() - start_time) * 1000)

        completed = [r for r in results if r.status == "completed" and r.data]
        best_variant = None
        best_strategy = None
        best = None
        if completed:
            best = max(completed, key=lambda r: r.data.get("estimated_retention", 0))
            best_variant = best.data
            best_strategy = best.persona

        total_cost = sum(r.cost_cents for r in results)

        job.status = SwarmJobStatus.completed if completed else SwarmJobStatus.failed
        job.completed_agents = len(completed)
        job.failed_agents = len(results) - len(completed)
        job.cost_cents = total_cost
        job.completed_at = datetime.now(timezone.utc)
        job.results_summary = {
            "clip_id": clip_id,
            "strategies_used": strategies[:len(agents)],
            "best_strategy": best_strategy,
            "total_agents": len(agents),
            "completed": len(completed),
            "failed": len(results) - len(completed),
        }
        await self.job_service.update_job(job)
        await self.queue.mark_job_complete(job_id, job.model_dump(mode="json"))

        return {
            "job_id": job_id,
            "agents": len(agents),
            "variants": [self._serialize_result(r) for r in results],
            "best_variant": best_variant,
            "total_cost_cents": total_cost,
            "duration_ms": duration_ms,
        }

    # ─────────────────────────────────────────────────────────────
    # Post Swarm
    # ─────────────────────────────────────────────────────────────

    async def execute_post_swarm(
        self,
        clip_id: str,
        user_id: str,
        accounts: List[Dict[str, str]],
        hooks: Optional[List[Dict[str, Any]]] = None,
        agent_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """Post a clip to multiple accounts in parallel.

        Uses user's custom allocation unless agent_count is explicitly provided.

        Args:
            accounts: [{"account_id": str, "platform": str}, ...]
            hooks: Optional list of hook data to use per post

        Returns:
            {
                "job_id": str,
                "agents": int,
                "posts": List[dict],
                "summary": dict,
                "total_cost_cents": int,
                "duration_ms": int,
            }
        """
        config = await self.config_service.get_config(user_id)
        # Use custom allocation or explicit override
        allocated = config.get_pool_agents("post")
        requested = agent_count if agent_count is not None else allocated
        max_agents = min(requested, allocated)

        if max_agents <= 0:
            return {"error": "Post swarm disabled or limit reached", "job_id": None}

        # Check budget with pool-specific cost
        if not await self.config_service.check_budget(user_id, "post", max_agents):
            return {"error": "Daily budget exceeded", "job_id": None}

        if "post" not in config.enabled_pools:
            return {"error": "Post swarm pool disabled", "job_id": None}

        # Limit accounts to max agents
        accounts = accounts[:max_agents]

        job_id = str(uuid.uuid4())
        job = SwarmJob(
            job_id=job_id,
            user_id=user_id,
            job_type=SwarmJobType.post,
            status=SwarmJobStatus.running,
            total_agents=len(accounts),
        )
        await self.job_service.create_job(job)
        await self.queue.enqueue("swarm_jobs", job.model_dump(mode="json"))

        agents = []
        for i, account in enumerate(accounts):
            hook_data = hooks[i] if hooks and i < len(hooks) else None
            agents.append(PostSwarmAgent(
                agent_index=i,
                account_id=account["account_id"],
                platform=account["platform"]
            ))

        start_time = time.time()
        results = await self._run_post_agents(agents, job_id, clip_id, user_id, hooks)
        duration_ms = int((time.time() - start_time) * 1000)

        completed = [r for r in results if r.status == "completed"]
        failed = [r for r in results if r.status == "failed"]

        total_cost = sum(r.cost_cents for r in results)

        job.status = SwarmJobStatus.partial if (completed and failed) else (
            SwarmJobStatus.completed if completed else SwarmJobStatus.failed
        )
        job.completed_agents = len(completed)
        job.failed_agents = len(failed)
        job.cost_cents = total_cost
        job.completed_at = datetime.now(timezone.utc)
        job.results_summary = {
            "clip_id": clip_id,
            "platforms": [a["platform"] for a in accounts],
            "total_agents": len(agents),
            "completed": len(completed),
            "failed": len(failed),
        }
        await self.job_service.update_job(job)
        await self.queue.mark_job_complete(job_id, job.model_dump(mode="json"))

        return {
            "job_id": job_id,
            "agents": len(agents),
            "posts": [self._serialize_result(r) for r in results],
            "summary": {
                "total": len(agents),
                "success": len(completed),
                "failed": len(failed),
                "platforms": list(set(a["platform"] for a in accounts)),
            },
            "total_cost_cents": total_cost,
            "duration_ms": duration_ms,
        }

    # ─────────────────────────────────────────────────────────────
    # AB Test Swarm
    # ─────────────────────────────────────────────────────────────

    async def execute_ab_test_swarm(
        self,
        test_id: str,
        user_id: str,
        clip_id: str,
        agent_count: Optional[int] = None,
        strategy_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run A/B test analysis in parallel with different strategies."""
        config = await self.config_service.get_config(user_id)
        allocated = config.get_pool_agents("ab_test")
        requested = agent_count if agent_count is not None else allocated
        max_agents = min(requested, allocated)

        if max_agents <= 0:
            return {"error": "A/B test swarm disabled or limit reached", "job_id": None}

        if not await self.config_service.check_budget(user_id, "ab_test", max_agents):
            return {"error": "Daily budget exceeded", "job_id": None}

        if "ab_test" not in config.enabled_pools:
            return {"error": "A/B test swarm pool disabled", "job_id": None}

        job_id = str(uuid.uuid4())
        job = SwarmJob(
            job_id=job_id,
            user_id=user_id,
            job_type=SwarmJobType.ab_test,
            status=SwarmJobStatus.running,
            total_agents=max_agents,
        )
        await self.job_service.create_job(job)
        await self.queue.enqueue("swarm_jobs", job.model_dump(mode="json"))

        available_strategies = ABTestSwarmAgent.STRATEGIES
        if strategy_filter:
            strategies = [s for s in strategy_filter if s in available_strategies]
            if not strategies:
                strategies = available_strategies[:max_agents]
        else:
            strategies = available_strategies[:max_agents]
        strategies = strategies[:max_agents]

        agents = [
            ABTestSwarmAgent(agent_index=i, strategy=strategies[i])
            for i in range(len(strategies))
        ]

        start_time = time.time()
        results = await self._run_agents(agents, job_id, clip_id, "", user_id)
        duration_ms = int((time.time() - start_time) * 1000)

        completed = [r for r in results if r.status == "completed"]
        best_result = None
        if completed:
            # Pick winner with highest margin
            best_result = max(completed, key=lambda r: r.data.get("margin_vs_second", 0))

        total_cost = sum(r.cost_cents for r in results)

        job.status = SwarmJobStatus.completed if completed else SwarmJobStatus.failed
        job.completed_agents = len(completed)
        job.failed_agents = len(results) - len(completed)
        job.cost_cents = total_cost
        job.completed_at = datetime.now(timezone.utc)
        job.results_summary = {
            "test_id": test_id,
            "strategies_used": strategies,
            "best_strategy": best_result.persona if best_result else None,
            "total_agents": len(agents),
            "completed": len(completed),
            "failed": len(results) - len(completed),
        }
        await self.job_service.update_job(job)
        await self.queue.mark_job_complete(job_id, job.model_dump(mode="json"))

        return {
            "job_id": job_id,
            "agents": len(agents),
            "results": [self._serialize_result(r) for r in results],
            "best_result": self._serialize_result(best_result) if best_result else None,
            "total_cost_cents": total_cost,
            "duration_ms": duration_ms,
        }

    # ─────────────────────────────────────────────────────────────
    # Music Match Swarm
    # ─────────────────────────────────────────────────────────────

    async def execute_music_match_swarm(
        self,
        clip_id: str,
        user_id: str,
        agent_count: Optional[int] = None,
        strategy_filter: Optional[List[str]] = None,
        segment_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Match music tracks in parallel with different strategies."""
        config = await self.config_service.get_config(user_id)
        allocated = config.get_pool_agents("music_match")
        requested = agent_count if agent_count is not None else allocated
        max_agents = min(requested, allocated)

        if max_agents <= 0:
            return {"error": "Music match swarm disabled or limit reached", "job_id": None}

        if not await self.config_service.check_budget(user_id, "music_match", max_agents):
            return {"error": "Daily budget exceeded", "job_id": None}

        if "music_match" not in config.enabled_pools:
            return {"error": "Music match swarm pool disabled", "job_id": None}

        job_id = str(uuid.uuid4())
        job = SwarmJob(
            job_id=job_id,
            user_id=user_id,
            job_type=SwarmJobType.music_match,
            status=SwarmJobStatus.running,
            total_agents=max_agents,
        )
        await self.job_service.create_job(job)
        await self.queue.enqueue("swarm_jobs", job.model_dump(mode="json"))

        available_strategies = MusicMatchSwarmAgent.STRATEGIES
        if strategy_filter:
            strategies = [s for s in strategy_filter if s in available_strategies]
            if not strategies:
                strategies = available_strategies[:max_agents]
        else:
            strategies = available_strategies[:max_agents]
        strategies = strategies[:max_agents]

        agents = [
            MusicMatchSwarmAgent(agent_index=i, strategy=strategies[i])
            for i in range(len(strategies))
        ]

        start_time = time.time()
        # Custom runner for music agents with segment_data
        results = await self._run_music_agents(agents, job_id, clip_id, user_id, segment_data)
        duration_ms = int((time.time() - start_time) * 1000)

        completed = [r for r in results if r.status == "completed"]
        best_result = None
        if completed:
            best_result = max(completed, key=lambda r: r.data.get("score", 0))

        total_cost = sum(r.cost_cents for r in results)

        job.status = SwarmJobStatus.completed if completed else SwarmJobStatus.failed
        job.completed_agents = len(completed)
        job.failed_agents = len(results) - len(completed)
        job.cost_cents = total_cost
        job.completed_at = datetime.now(timezone.utc)
        job.results_summary = {
            "clip_id": clip_id,
            "strategies_used": strategies,
            "best_strategy": best_result.persona if best_result else None,
            "total_agents": len(agents),
            "completed": len(completed),
            "failed": len(results) - len(completed),
        }
        await self.job_service.update_job(job)
        await self.queue.mark_job_complete(job_id, job.model_dump(mode="json"))

        return {
            "job_id": job_id,
            "agents": len(agents),
            "results": [self._serialize_result(r) for r in results],
            "best_result": self._serialize_result(best_result) if best_result else None,
            "total_cost_cents": total_cost,
            "duration_ms": duration_ms,
        }

    # ─────────────────────────────────────────────────────────────
    # Thumbnail Swarm
    # ─────────────────────────────────────────────────────────────

    async def execute_thumbnail_swarm(
        self,
        clip_id: str,
        user_id: str,
        agent_count: Optional[int] = None,
        style_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate thumbnails in parallel with different styles."""
        config = await self.config_service.get_config(user_id)
        allocated = config.get_pool_agents("thumbnail")
        requested = agent_count if agent_count is not None else allocated
        max_agents = min(requested, allocated)

        if max_agents <= 0:
            return {"error": "Thumbnail swarm disabled or limit reached", "job_id": None}

        if not await self.config_service.check_budget(user_id, "thumbnail", max_agents):
            return {"error": "Daily budget exceeded", "job_id": None}

        if "thumbnail" not in config.enabled_pools:
            return {"error": "Thumbnail swarm pool disabled", "job_id": None}

        job_id = str(uuid.uuid4())
        job = SwarmJob(
            job_id=job_id,
            user_id=user_id,
            job_type=SwarmJobType.thumbnail,
            status=SwarmJobStatus.running,
            total_agents=max_agents,
        )
        await self.job_service.create_job(job)
        await self.queue.enqueue("swarm_jobs", job.model_dump(mode="json"))

        available_styles = ThumbnailSwarmAgent.STYLES
        if style_filter:
            styles = [s for s in style_filter if s in available_styles]
            if not styles:
                styles = available_styles[:max_agents]
        else:
            styles = available_styles[:max_agents]
        styles = styles[:max_agents]

        agents = [
            ThumbnailSwarmAgent(agent_index=i, style=styles[i])
            for i in range(len(styles))
        ]

        start_time = time.time()
        results = await self._run_agents(agents, job_id, clip_id, "", user_id)
        duration_ms = int((time.time() - start_time) * 1000)

        completed = [r for r in results if r.status == "completed"]

        total_cost = sum(r.cost_cents for r in results)

        job.status = SwarmJobStatus.completed if completed else SwarmJobStatus.failed
        job.completed_agents = len(completed)
        job.failed_agents = len(results) - len(completed)
        job.cost_cents = total_cost
        job.completed_at = datetime.now(timezone.utc)
        job.results_summary = {
            "clip_id": clip_id,
            "styles_used": styles,
            "thumbnails_generated": len(completed),
            "total_agents": len(agents),
            "completed": len(completed),
            "failed": len(results) - len(completed),
        }
        await self.job_service.update_job(job)
        await self.queue.mark_job_complete(job_id, job.model_dump(mode="json"))

        return {
            "job_id": job_id,
            "agents": len(agents),
            "results": [self._serialize_result(r) for r in results],
            "total_cost_cents": total_cost,
            "duration_ms": duration_ms,
        }

    # ─────────────────────────────────────────────────────────────
    # Safety Swarm
    # ─────────────────────────────────────────────────────────────

    async def execute_safety_swarm(
        self,
        clip_id: str,
        user_id: str,
        agent_count: Optional[int] = None,
        sensitivity_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run safety checks in parallel with different sensitivity levels."""
        config = await self.config_service.get_config(user_id)
        allocated = config.get_pool_agents("safety")
        requested = agent_count if agent_count is not None else allocated
        max_agents = min(requested, allocated)

        if max_agents <= 0:
            return {"error": "Safety swarm disabled or limit reached", "job_id": None}

        if not await self.config_service.check_budget(user_id, "safety", max_agents):
            return {"error": "Daily budget exceeded", "job_id": None}

        if "safety" not in config.enabled_pools:
            return {"error": "Safety swarm pool disabled", "job_id": None}

        job_id = str(uuid.uuid4())
        job = SwarmJob(
            job_id=job_id,
            user_id=user_id,
            job_type=SwarmJobType.safety,
            status=SwarmJobStatus.running,
            total_agents=max_agents,
        )
        await self.job_service.create_job(job)
        await self.queue.enqueue("swarm_jobs", job.model_dump(mode="json"))

        available_levels = SafetySwarmAgent.SENSITIVITY_LEVELS
        if sensitivity_filter:
            levels = [s for s in sensitivity_filter if s in available_levels]
            if not levels:
                levels = available_levels[:max_agents]
        else:
            levels = available_levels[:max_agents]
        levels = levels[:max_agents]

        agents = [
            SafetySwarmAgent(agent_index=i, sensitivity=levels[i])
            for i in range(len(levels))
        ]

        start_time = time.time()
        results = await self._run_agents(agents, job_id, clip_id, "", user_id)
        duration_ms = int((time.time() - start_time) * 1000)

        completed = [r for r in results if r.status == "completed"]
        # Consensus: most restrictive wins
        all_safe = all(r.data.get("safe_to_post", False) for r in completed) if completed else False
        needs_review = any(r.data.get("requires_review", False) for r in completed) if completed else False

        total_cost = sum(r.cost_cents for r in results)

        job.status = SwarmJobStatus.completed if completed else SwarmJobStatus.failed
        job.completed_agents = len(completed)
        job.failed_agents = len(results) - len(completed)
        job.cost_cents = total_cost
        job.completed_at = datetime.now(timezone.utc)
        job.results_summary = {
            "clip_id": clip_id,
            "levels_used": levels,
            "consensus_safe": all_safe,
            "needs_review": needs_review,
            "total_agents": len(agents),
            "completed": len(completed),
            "failed": len(results) - len(completed),
        }
        await self.job_service.update_job(job)
        await self.queue.mark_job_complete(job_id, job.model_dump(mode="json"))

        return {
            "job_id": job_id,
            "agents": len(agents),
            "results": [self._serialize_result(r) for r in results],
            "consensus": {
                "safe_to_post": all_safe,
                "needs_review": needs_review,
                "restrictive_level": next((r.persona for r in completed if r.data.get("requires_review")), "standard")
            },
            "total_cost_cents": total_cost,
            "duration_ms": duration_ms,
        }

    # ─────────────────────────────────────────────────────────────
    # Hooks Analysis Swarm
    # ─────────────────────────────────────────────────────────────

    async def execute_hooks_analysis_swarm(
        self,
        clip_id: str,
        user_id: str,
        platform: str = "tiktok",
        agent_count: Optional[int] = None,
        method_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze hooks in parallel with different methods/time periods."""
        config = await self.config_service.get_config(user_id)
        allocated = config.get_pool_agents("hooks_analysis")
        requested = agent_count if agent_count is not None else allocated
        max_agents = min(requested, allocated)

        if max_agents <= 0:
            return {"error": "Hooks analysis swarm disabled or limit reached", "job_id": None}

        if not await self.config_service.check_budget(user_id, "hooks_analysis", max_agents):
            return {"error": "Daily budget exceeded", "job_id": None}

        if "hooks_analysis" not in config.enabled_pools:
            return {"error": "Hooks analysis swarm pool disabled", "job_id": None}

        job_id = str(uuid.uuid4())
        job = SwarmJob(
            job_id=job_id,
            user_id=user_id,
            job_type=SwarmJobType.hooks_analysis,
            status=SwarmJobStatus.running,
            total_agents=max_agents,
        )
        await self.job_service.create_job(job)
        await self.queue.enqueue("swarm_jobs", job.model_dump(mode="json"))

        available_methods = HooksAnalysisSwarmAgent.METHODS
        if method_filter:
            methods = [m for m in method_filter if m in available_methods]
            if not methods:
                methods = available_methods[:max_agents]
        else:
            methods = available_methods[:max_agents]
        methods = methods[:max_agents]

        agents = [
            HooksAnalysisSwarmAgent(agent_index=i, method=methods[i])
            for i in range(len(methods))
        ]

        start_time = time.time()
        results = await self._run_agents(agents, job_id, clip_id, platform, user_id)
        duration_ms = int((time.time() - start_time) * 1000)

        completed = [r for r in results if r.status == "completed"]

        total_cost = sum(r.cost_cents for r in results)

        job.status = SwarmJobStatus.completed if completed else SwarmJobStatus.failed
        job.completed_agents = len(completed)
        job.failed_agents = len(results) - len(completed)
        job.cost_cents = total_cost
        job.completed_at = datetime.now(timezone.utc)
        job.results_summary = {
            "clip_id": clip_id,
            "methods_used": methods,
            "total_agents": len(agents),
            "completed": len(completed),
            "failed": len(results) - len(completed),
        }
        await self.job_service.update_job(job)
        await self.queue.mark_job_complete(job_id, job.model_dump(mode="json"))

        return {
            "job_id": job_id,
            "agents": len(agents),
            "results": [self._serialize_result(r) for r in results],
            "total_cost_cents": total_cost,
            "duration_ms": duration_ms,
        }

    # ─────────────────────────────────────────────────────────────
    # Segment Analysis Swarm
    # ─────────────────────────────────────────────────────────────

    async def execute_segment_analyze_swarm(
        self,
        clip_id: str,
        user_id: str,
        agent_count: Optional[int] = None,
        strategy_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze video segments in parallel with different strategies."""
        config = await self.config_service.get_config(user_id)
        allocated = config.get_pool_agents("segment_analyze")
        requested = agent_count if agent_count is not None else allocated
        max_agents = min(requested, allocated)

        if max_agents <= 0:
            return {"error": "Segment analyze swarm disabled or limit reached", "job_id": None}

        if not await self.config_service.check_budget(user_id, "segment_analyze", max_agents):
            return {"error": "Daily budget exceeded", "job_id": None}

        if "segment_analyze" not in config.enabled_pools:
            return {"error": "Segment analyze swarm pool disabled", "job_id": None}

        job_id = str(uuid.uuid4())
        job = SwarmJob(
            job_id=job_id,
            user_id=user_id,
            job_type=SwarmJobType.segment_analyze,
            status=SwarmJobStatus.running,
            total_agents=max_agents,
        )
        await self.job_service.create_job(job)
        await self.queue.enqueue("swarm_jobs", job.model_dump(mode="json"))

        available_strategies = SegmentAnalyzeSwarmAgent.STRATEGIES
        if strategy_filter:
            strategies = [s for s in strategy_filter if s in available_strategies]
            if not strategies:
                strategies = available_strategies[:max_agents]
        else:
            strategies = available_strategies[:max_agents]
        strategies = strategies[:max_agents]

        agents = [
            SegmentAnalyzeSwarmAgent(agent_index=i, strategy=strategies[i])
            for i in range(len(strategies))
        ]

        start_time = time.time()
        results = await self._run_agents(agents, job_id, clip_id, "", user_id)
        duration_ms = int((time.time() - start_time) * 1000)

        completed = [r for r in results if r.status == "completed"]
        best_result = None
        if completed:
            best_result = max(completed, key=lambda r: r.data.get("best_segment", {}).get("score", 0) if r.data.get("best_segment") else 0)

        total_cost = sum(r.cost_cents for r in results)

        job.status = SwarmJobStatus.completed if completed else SwarmJobStatus.failed
        job.completed_agents = len(completed)
        job.failed_agents = len(results) - len(completed)
        job.cost_cents = total_cost
        job.completed_at = datetime.now(timezone.utc)
        job.results_summary = {
            "clip_id": clip_id,
            "strategies_used": strategies,
            "best_strategy": best_result.persona if best_result else None,
            "total_agents": len(agents),
            "completed": len(completed),
            "failed": len(results) - len(completed),
        }
        await self.job_service.update_job(job)
        await self.queue.mark_job_complete(job_id, job.model_dump(mode="json"))

        return {
            "job_id": job_id,
            "agents": len(agents),
            "results": [self._serialize_result(r) for r in results],
            "best_result": self._serialize_result(best_result) if best_result else None,
            "total_cost_cents": total_cost,
            "duration_ms": duration_ms,
        }

    # ─────────────────────────────────────────────────────────────
    # Edit Swarm
    # ─────────────────────────────────────────────────────────────

    async def execute_edit_swarm(
        self,
        clip_id: str,
        user_id: str,
        agent_count: Optional[int] = None,
        recipe_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Apply video edits in parallel with different recipes."""
        config = await self.config_service.get_config(user_id)
        allocated = config.get_pool_agents("edit")
        requested = agent_count if agent_count is not None else allocated
        max_agents = min(requested, allocated)

        if max_agents <= 0:
            return {"error": "Edit swarm disabled or limit reached", "job_id": None}

        if not await self.config_service.check_budget(user_id, "edit", max_agents):
            return {"error": "Daily budget exceeded", "job_id": None}

        if "edit" not in config.enabled_pools:
            return {"error": "Edit swarm pool disabled", "job_id": None}

        job_id = str(uuid.uuid4())
        job = SwarmJob(
            job_id=job_id,
            user_id=user_id,
            job_type=SwarmJobType.edit,
            status=SwarmJobStatus.running,
            total_agents=max_agents,
        )
        await self.job_service.create_job(job)
        await self.queue.enqueue("swarm_jobs", job.model_dump(mode="json"))

        available_recipes = EditSwarmAgent.RECIPES
        if recipe_filter:
            recipes = [r for r in recipe_filter if r in available_recipes]
            if not recipes:
                recipes = available_recipes[:max_agents]
        else:
            recipes = available_recipes[:max_agents]
        recipes = recipes[:max_agents]

        agents = [
            EditSwarmAgent(agent_index=i, recipe=recipes[i])
            for i in range(len(recipes))
        ]

        start_time = time.time()
        results = await self._run_agents(agents, job_id, clip_id, "", user_id)
        duration_ms = int((time.time() - start_time) * 1000)

        completed = [r for r in results if r.status == "completed"]

        total_cost = sum(r.cost_cents for r in results)

        job.status = SwarmJobStatus.completed if completed else SwarmJobStatus.failed
        job.completed_agents = len(completed)
        job.failed_agents = len(results) - len(completed)
        job.cost_cents = total_cost
        job.completed_at = datetime.now(timezone.utc)
        job.results_summary = {
            "clip_id": clip_id,
            "recipes_used": recipes,
            "total_agents": len(agents),
            "completed": len(completed),
            "failed": len(results) - len(completed),
        }
        await self.job_service.update_job(job)
        await self.queue.mark_job_complete(job_id, job.model_dump(mode="json"))

        return {
            "job_id": job_id,
            "agents": len(agents),
            "results": [self._serialize_result(r) for r in results],
            "total_cost_cents": total_cost,
            "duration_ms": duration_ms,
        }

    # ─────────────────────────────────────────────────────────────
    # Internal: parallel agent execution (updated for all types)
    # ─────────────────────────────────────────────────────────────

    async def _run_agents(
        self,
        agents: List[Any],
        job_id: str,
        clip_id: str,
        platform: str,
        user_id: str
    ) -> List[AgentResult]:
        """Execute agents in parallel with error isolation."""
        async def run_with_tracking(agent):
            try:
                if isinstance(agent, HookSwarmAgent):
                    result = await agent.execute(clip_id, platform, user_id)
                elif isinstance(agent, RemixSwarmAgent):
                    result = await agent.execute(clip_id, user_id)
                elif isinstance(agent, ABTestSwarmAgent):
                    result = await agent.execute(clip_id, user_id, clip_id)
                elif isinstance(agent, ThumbnailSwarmAgent):
                    result = await agent.execute(clip_id, user_id)
                elif isinstance(agent, SafetySwarmAgent):
                    result = await agent.execute(clip_id, user_id)
                elif isinstance(agent, HooksAnalysisSwarmAgent):
                    result = await agent.execute(clip_id, user_id, platform)
                elif isinstance(agent, SegmentAnalyzeSwarmAgent):
                    result = await agent.execute(clip_id, user_id)
                elif isinstance(agent, EditSwarmAgent):
                    result = await agent.execute(clip_id, user_id)
                else:
                    result = AgentResult(
                        agent_index=agent.agent_index,
                        persona="unknown",
                        status="failed",
                        data={},
                        cost_cents=0,
                        duration_ms=0,
                        error="Unknown agent type"
                    )

                # Persist result
                await self.job_service.save_agent_result(SwarmAgentResult(
                    result_id=str(uuid.uuid4()),
                    job_id=job_id,
                    agent_index=result.agent_index,
                    agent_persona=result.persona,
                    status=result.status,
                    result_data=result.data,
                    cost_cents=result.cost_cents,
                    duration_ms=result.duration_ms,
                    error_message=result.error,
                ))
                return result
            except Exception as e:
                logger.error(f"[SwarmOrchestrator] Agent {agent.agent_index} crashed: {e}")
                persona = getattr(agent, "persona", getattr(agent, "strategy", getattr(agent, "style", getattr(agent, "sensitivity", getattr(agent, "method", getattr(agent, "recipe", "unknown"))))))
                result = AgentResult(
                    agent_index=agent.agent_index,
                    persona=persona,
                    status="failed",
                    data={},
                    cost_cents=0,
                    duration_ms=0,
                    error=str(e)
                )
                await self.job_service.save_agent_result(SwarmAgentResult(
                    result_id=str(uuid.uuid4()),
                    job_id=job_id,
                    agent_index=result.agent_index,
                    agent_persona=result.persona,
                    status="failed",
                    result_data={},
                    cost_cents=0,
                    duration_ms=0,
                    error_message=str(e),
                ))
                return result

        # Run all agents concurrently
        tasks = [run_with_tracking(agent) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Log any unexpected exceptions that weren't caught by run_with_tracking
        import logging
        _log = logging.getLogger(__name__)
        for r in results:
            if isinstance(r, BaseException):
                _log.error(f"[SwarmOrchestrator] Unhandled agent exception: {r}", exc_info=r)
        return [r for r in results if not isinstance(r, BaseException)]

    async def _run_post_agents(
        self,
        agents: List[PostSwarmAgent],
        job_id: str,
        clip_id: str,
        user_id: str,
        hooks: Optional[List[Dict[str, Any]]] = None
    ) -> List[AgentResult]:
        """Execute post agents in parallel with error isolation."""
        async def run_with_tracking(agent, hook_data):
            try:
                result = await agent.execute(clip_id, user_id, hook_data)

                await self.job_service.save_agent_result(SwarmAgentResult(
                    result_id=str(uuid.uuid4()),
                    job_id=job_id,
                    agent_index=result.agent_index,
                    agent_persona=result.persona,
                    status=result.status,
                    result_data=result.data,
                    cost_cents=result.cost_cents,
                    duration_ms=result.duration_ms,
                    error_message=result.error,
                ))
                return result
            except Exception as e:
                logger.error(f"[SwarmOrchestrator] Post agent {agent.agent_index} crashed: {e}")
                result = AgentResult(
                    agent_index=agent.agent_index,
                    persona=f"{agent.platform}:{agent.account_id}",
                    status="failed",
                    data={},
                    cost_cents=0,
                    duration_ms=0,
                    error=str(e)
                )
                await self.job_service.save_agent_result(SwarmAgentResult(
                    result_id=str(uuid.uuid4()),
                    job_id=job_id,
                    agent_index=result.agent_index,
                    agent_persona=result.persona,
                    status="failed",
                    result_data={},
                    cost_cents=0,
                    duration_ms=0,
                    error_message=str(e),
                ))
                return result

        tasks = []
        for i, agent in enumerate(agents):
            hook_data = hooks[i] if hooks and i < len(hooks) else None
            tasks.append(run_with_tracking(agent, hook_data))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Log any unexpected exceptions that weren't caught by run_with_tracking
        import logging
        _log = logging.getLogger(__name__)
        for r in results:
            if isinstance(r, BaseException):
                _log.error(f"[SwarmOrchestrator] Unhandled agent exception: {r}", exc_info=r)
        return [r for r in results if not isinstance(r, BaseException)]

    async def _run_music_agents(
        self,
        agents: List[MusicMatchSwarmAgent],
        job_id: str,
        clip_id: str,
        user_id: str,
        segment_data: Optional[Dict[str, Any]] = None
    ) -> List[AgentResult]:
        """Execute music match agents in parallel with error isolation."""
        async def run_with_tracking(agent):
            try:
                result = await agent.execute(clip_id, user_id, segment_data)

                await self.job_service.save_agent_result(SwarmAgentResult(
                    result_id=str(uuid.uuid4()),
                    job_id=job_id,
                    agent_index=result.agent_index,
                    agent_persona=result.persona,
                    status=result.status,
                    result_data=result.data,
                    cost_cents=result.cost_cents,
                    duration_ms=result.duration_ms,
                    error_message=result.error,
                ))
                return result
            except Exception as e:
                logger.error(f"[SwarmOrchestrator] Music agent {agent.agent_index} crashed: {e}")
                result = AgentResult(
                    agent_index=agent.agent_index,
                    persona=agent.strategy,
                    status="failed",
                    data={},
                    cost_cents=0,
                    duration_ms=0,
                    error=str(e)
                )
                await self.job_service.save_agent_result(SwarmAgentResult(
                    result_id=str(uuid.uuid4()),
                    job_id=job_id,
                    agent_index=result.agent_index,
                    agent_persona=result.persona,
                    status="failed",
                    result_data={},
                    cost_cents=0,
                    duration_ms=0,
                    error_message=str(e),
                ))
                return result

        tasks = [run_with_tracking(agent) for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Log any unexpected exceptions that weren't caught by run_with_tracking
        import logging
        _log = logging.getLogger(__name__)
        for r in results:
            if isinstance(r, BaseException):
                _log.error(f"[SwarmOrchestrator] Unhandled agent exception: {r}", exc_info=r)
        return [r for r in results if not isinstance(r, BaseException)]

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _serialize_result(result: AgentResult) -> Dict[str, Any]:
        """Convert AgentResult to a serializable dict."""
        return {
            "agent_index": result.agent_index,
            "persona": result.persona,
            "status": result.status,
            "data": result.data,
            "cost_cents": result.cost_cents,
            "duration_ms": result.duration_ms,
            "error": result.error,
        }


# Singleton
swarm_orchestrator = SwarmOrchestrator()
