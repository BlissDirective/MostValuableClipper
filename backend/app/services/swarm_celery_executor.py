"""
CelerySwarmExecutor — Distributed Agent Execution Engine (Phase 3)

Replaces asyncio.gather-based agent execution with true distributed execution
via Celery. Each agent runs as an independent Celery task, enabling:
  - Horizontal scaling across worker pools
  - Per-agent retry logic with individual failure isolation
  - Real-time progress tracking
  - Cost tracking aggregation across distributed tasks

Architecture:
  SwarmOrchestrator.spawn_agents() → Celery group → individual worker tasks
                                          ↓
                                   Celery chord → result aggregator

Usage:
    from app.services.swarm_celery_executor import CelerySwarmExecutor
    executor = CelerySwarmExecutor()
    result = await executor.execute_hook_swarm(clip_id="abc", user_id="xyz")
"""
from __future__ import annotations

import logging
import asyncio
import uuid
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field

from app.core.celery_config import celery_app
from app.workers.swarm_tasks import (
    hook_agent_task, remix_agent_task, post_agent_task,
    ab_test_agent_task, music_match_agent_task, thumbnail_agent_task,
    safety_agent_task, segment_agent_task, edit_agent_task,
    aggregate_swarm_results,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Execution Result
# ---------------------------------------------------------------------------

@dataclass
class DistributedSwarmResult:
    """Aggregated result from a distributed swarm execution."""
    job_id: str
    pool_type: str
    total_agents: int
    completed: int
    failed: int
    results: List[Dict[str, Any]]
    best_result: Optional[Dict[str, Any]]
    total_cost_usd: float
    duration_ms: int
    cached_hits: int = 0
    model_breakdown: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        success_rate = round(self.completed / max(self.total_agents, 1) * 100, 1)
        return {
            "job_id": self.job_id,
            "pool_type": self.pool_type,
            "total_agents": self.total_agents,
            "completed": self.completed,
            "failed": self.failed,
            "success_rate": success_rate,
            "results": self.results,
            "best_result": self.best_result,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "duration_ms": self.duration_ms,
            "cached_hits": self.cached_hits,
            "model_breakdown": self.model_breakdown,
        }


# ---------------------------------------------------------------------------
# Celery Swarm Executor
# ---------------------------------------------------------------------------

class CelerySwarmExecutor:
    """Execute swarm agents via distributed Celery tasks.

    Wraps the existing SwarmOrchestrator logic but distributes agent
    execution across the Celery worker pool instead of running them
    inline with asyncio.gather.

    Key advantages over inline execution:
      1. Agents run on dedicated worker machines (not the API server)
      2. Failed agents retry independently without affecting others
      3. Worker pools scale independently per agent type
      4. No GIL contention — true parallelism for CPU-bound agents
    """

    # Mapping from pool type to agent task function and queue
    AGENT_TASK_MAP = {
        "hook":         (hook_agent_task,        "swarm.hooks"),
        "remix":        (remix_agent_task,       "swarm.remix"),
        "post":         (post_agent_task,        "swarm.post"),
        "ab_test":      (ab_test_agent_task,     "swarm.ab_test"),
        "music_match":  (music_match_agent_task, "swarm.music"),
        "thumbnail":    (thumbnail_agent_task,   "swarm.thumbnail"),
        "safety":       (safety_agent_task,      "swarm.safety"),
        "segment":      (segment_agent_task,     "swarm.segment"),
        "edit":         (edit_agent_task,        "swarm.edit"),
    }

    # Best-result selection strategy per pool type
    BEST_RESULT_SELECTOR = {
        "hook":         lambda results: max((r for r in results if r.get("status") == "completed"),
                                            key=lambda x: x.get("data", {}).get("estimated_retention", 0), default=None),
        "remix":        lambda results: max((r for r in results if r.get("status") == "completed"),
                                            key=lambda x: x.get("data", {}).get("estimated_retention", 0), default=None),
        "music_match":  lambda results: max((r for r in results if r.get("status") == "completed"),
                                            key=lambda x: x.get("data", {}).get("score", 0), default=None),
        "segment":      lambda results: max((r for r in results if r.get("status") == "completed"),
                                            key=lambda x: x.get("data", {}).get("best_segment", {}).get("score", 0) if x.get("data", {}).get("best_segment") else 0, default=None),
        "safety":       lambda results: next((r for r in results if r.get("status") == "completed" and
                                              r.get("data", {}).get("requires_review", False)), None),
    }

    def __init__(self, use_cache: bool = True, max_concurrent_per_swarm: int = 10):
        self.use_cache = use_cache
        self.max_concurrent = max_concurrent_per_swarm
        self._stats: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Public API — mirrors SwarmOrchestrator's interface
    # ------------------------------------------------------------------

    async def execute_hook_swarm(
        self, clip_id: str, user_id: str, platform: str = "tiktok",
        personas: Optional[List[str]] = None, agent_count: int = 3
    ) -> DistributedSwarmResult:
        """Execute hook generation agents across the worker pool."""
        agents = personas or ["hype_beast", "storyteller", "educator"]
        agents = agents[:agent_count]

        tasks = [
            hook_agent_task.s(clip_id, "", persona, platform)
            for persona in agents
        ]
        return await self._execute_group("hook", clip_id, tasks)

    async def execute_remix_swarm(
        self, clip_id: str, user_id: str,
        strategies: Optional[List[str]] = None, agent_count: int = 3
    ) -> DistributedSwarmResult:
        """Execute remix agents across the worker pool."""
        agents = strategies or ["reformat", "platform_adapt", "speed_change"]
        agents = agents[:agent_count]

        tasks = [
            remix_agent_task.s(clip_id, "original hook", strategy)
            for strategy in agents
        ]
        return await self._execute_group("remix", clip_id, tasks)

    async def execute_post_swarm(
        self, clip_id: str, user_id: str,
        platforms: Optional[List[str]] = None
    ) -> DistributedSwarmResult:
        """Execute post optimization agents across the worker pool."""
        targets = platforms or ["tiktok", "instagram", "youtube"]

        tasks = [
            post_agent_task.s(clip_id, "", platform)
            for platform in targets
        ]
        return await self._execute_group("post", clip_id, tasks)

    async def execute_ab_test_swarm(
        self, clip_id: str, user_id: str,
        strategies: Optional[List[str]] = None, agent_count: int = 3
    ) -> DistributedSwarmResult:
        """Execute A/B test variant agents across the worker pool."""
        agents = strategies or ["curiosity_gap", "social_proof", "urgency"]
        agents = agents[:agent_count]

        tasks = [
            ab_test_agent_task.s(clip_id, "", strategy)
            for strategy in agents
        ]
        return await self._execute_group("ab_test", clip_id, tasks)

    async def execute_music_match_swarm(
        self, clip_id: str, user_id: str,
        strategies: Optional[List[str]] = None, agent_count: int = 3
    ) -> DistributedSwarmResult:
        """Execute music match agents across the worker pool."""
        agents = strategies or ["mood_match", "energy_sync", "genre_fit"]
        agents = agents[:agent_count]

        tasks = [
            music_match_agent_task.s(clip_id, f"{strategy} mood")
            for strategy in agents
        ]
        return await self._execute_group("music_match", clip_id, tasks)

    async def execute_thumbnail_swarm(
        self, clip_id: str, user_id: str,
        styles: Optional[List[str]] = None, agent_count: int = 3
    ) -> DistributedSwarmResult:
        """Execute thumbnail generation agents across the worker pool."""
        agents = styles or ["text_overlay", "face_focus", "action_shot"]
        agents = agents[:agent_count]

        tasks = [
            thumbnail_agent_task.s(clip_id, f"{style} thumbnail")
            for style in agents
        ]
        return await self._execute_group("thumbnail", clip_id, tasks)

    async def execute_safety_swarm(
        self, clip_id: str, user_id: str,
        levels: Optional[List[str]] = None, agent_count: int = 3
    ) -> DistributedSwarmResult:
        """Execute safety check agents across the worker pool."""
        agents = levels or ["low", "medium", "high"]
        agents = agents[:agent_count]

        tasks = [
            safety_agent_task.s(clip_id, f"content for {level} check")
            for level in agents
        ]
        return await self._execute_group("safety", clip_id, tasks)

    async def execute_segment_analyze_swarm(
        self, clip_id: str, user_id: str,
        strategies: Optional[List[str]] = None, agent_count: int = 5
    ) -> DistributedSwarmResult:
        """Execute segment analysis agents across the worker pool."""
        agents = strategies or ["energy_peak", "face_presence", "hook_potential", "question_moment", "silence_break"]
        agents = agents[:agent_count]

        tasks = [
            segment_agent_task.s(clip_id, "", strategy)
            for strategy in agents
        ]
        return await self._execute_group("segment", clip_id, tasks)

    async def execute_edit_swarm(
        self, clip_id: str, user_id: str,
        recipes: Optional[List[str]] = None, agent_count: int = 3
    ) -> DistributedSwarmResult:
        """Execute video edit agents across the worker pool."""
        agents = recipes or ["fast_cuts", "zoom_pulse", "clean_trim"]
        agents = agents[:agent_count]

        tasks = [
            edit_agent_task.s(clip_id, f"{recipe} edit", {"duration": 30})
            for recipe in agents
        ]
        return await self._execute_group("edit", clip_id, tasks)

    # ------------------------------------------------------------------
    # Generic distributed execution — the core engine
    # ------------------------------------------------------------------

    async def _execute_group(
        self, pool_type: str, clip_id: str,
        celery_tasks: List, timeout_seconds: int = 300
    ) -> DistributedSwarmResult:
        """Execute a group of Celery tasks and aggregate results.

        This is the core engine: it submits a Celery group, waits for
        all tasks to complete, then aggregates results with the
        pool-type-specific best-result selector.
        """
        job_id = str(uuid.uuid4())
        start_time = time.time()
        total_agents = len(celery_tasks)

        logger.info(f"[CelerySwarm] Starting {pool_type} swarm: "
                    f"job={job_id} agents={total_agents} clip={clip_id}")

        if total_agents == 0:
            return DistributedSwarmResult(
                job_id=job_id, pool_type=pool_type, total_agents=0,
                completed=0, failed=0, results=[], best_result=None,
                total_cost_usd=0.0, duration_ms=0,
            )

        try:
            # Apply the Celery group asynchronously
            job = celery_app.backend

            # Submit tasks individually and collect AsyncResults
            async_results = []
            for task in celery_tasks:
                result = task.apply_async()
                async_results.append(result)

            # Wait for all tasks with timeout
            raw_results = await self._wait_for_results(
                async_results, timeout=timeout_seconds
            )

            # Normalize results
            normalized = self._normalize_results(raw_results, total_agents)

            # Count stats
            completed = sum(1 for r in normalized if r.get("status") == "completed")
            failed = total_agents - completed
            total_cost = sum(r.get("cost_usd", 0) for r in normalized)
            cache_hits = sum(r.get("cached", False) for r in normalized)

            # Build model breakdown
            model_breakdown: Dict[str, int] = {}
            for r in normalized:
                model = r.get("model_used", "unknown")
                model_breakdown[model] = model_breakdown.get(model, 0) + 1

            # Select best result
            selector = self.BEST_RESULT_SELECTOR.get(pool_type)
            best = selector(normalized) if selector else None

            duration_ms = int((time.time() - start_time) * 1000)

            # Update stats
            self._update_stats(pool_type, total_agents, completed, failed, total_cost, duration_ms)

            logger.info(f"[CelerySwarm] {pool_type} complete: "
                        f"completed={completed}/{total_agents} "
                        f"cost=${total_cost:.4f} duration={duration_ms}ms "
                        f"cached={cache_hits}")

            return DistributedSwarmResult(
                job_id=job_id, pool_type=pool_type, total_agents=total_agents,
                completed=completed, failed=failed, results=normalized,
                best_result=best, total_cost_usd=total_cost,
                duration_ms=duration_ms, cached_hits=cache_hits,
                model_breakdown=model_breakdown,
            )

        except Exception as e:
            logger.error(f"[CelerySwarm] {pool_type} swarm failed: {e}")
            return DistributedSwarmResult(
                job_id=job_id, pool_type=pool_type, total_agents=total_agents,
                completed=0, failed=total_agents, results=[],
                best_result=None, total_cost_usd=0.0,
                duration_ms=int((time.time() - start_time) * 1000),
            )

    async def _wait_for_results(
        self, async_results: List, timeout: int = 300
    ) -> List[Any]:
        """Wait for all Celery async results with timeout.

        Uses asyncio to avoid blocking the event loop while
        polling Celery results.
        """
        results = []
        pending = list(enumerate(async_results))
        start = time.time()

        while pending and (time.time() - start) < timeout:
            still_pending = []
            for idx, async_result in pending:
                if async_result.ready():
                    try:
                        if async_result.successful():
                            results.append((idx, async_result.get()))
                        else:
                            results.append((idx, {"status": "failed", "error": str(async_result.result)}))
                    except Exception as e:
                        results.append((idx, {"status": "failed", "error": str(e)}))
                else:
                    still_pending.append((idx, async_result))
            pending = still_pending
            if pending:
                await asyncio.sleep(0.5)

        # Mark timed-out tasks as failed
        for idx, _ in pending:
            results.append((idx, {"status": "failed", "error": "timeout"}))

        # Sort by original index to maintain order
        results.sort(key=lambda x: x[0])
        return [r for _, r in results]

    def _normalize_results(self, raw_results: List[Any], expected_count: int) -> List[Dict[str, Any]]:
        """Normalize raw Celery results into a consistent format."""
        normalized = []
        for i, result in enumerate(raw_results):
            if isinstance(result, dict):
                normalized.append(result)
            elif isinstance(result, Exception):
                normalized.append({
                    "agent_index": i, "status": "failed",
                    "error": str(result), "cost_usd": 0,
                })
            else:
                # Try to convert to dict
                try:
                    normalized.append(dict(result))
                except (TypeError, ValueError):
                    normalized.append({
                        "agent_index": i, "status": "completed",
                        "data": {"raw_result": str(result)},
                        "cost_usd": 0,
                    })

        # Pad if we got fewer results than expected
        while len(normalized) < expected_count:
            normalized.append({
                "agent_index": len(normalized), "status": "failed",
                "error": "missing result", "cost_usd": 0,
            })

        return normalized

    def _update_stats(self, pool_type: str, total: int, completed: int,
                      failed: int, cost: float, duration_ms: int) -> None:
        if pool_type not in self._stats:
            self._stats[pool_type] = {
                "runs": 0, "total_agents": 0, "completed": 0,
                "failed": 0, "total_cost": 0.0, "total_duration_ms": 0,
            }
        s = self._stats[pool_type]
        s["runs"] += 1
        s["total_agents"] += total
        s["completed"] += completed
        s["failed"] += failed
        s["total_cost"] += cost
        s["total_duration_ms"] += duration_ms

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics for all pool types."""
        stats = {}
        for pool, s in self._stats.items():
            runs = s["runs"]
            stats[pool] = {
                "runs": runs,
                "avg_agents_per_run": round(s["total_agents"] / runs, 1) if runs else 0,
                "success_rate": round(s["completed"] / max(s["total_agents"], 1) * 100, 1),
                "total_cost_usd": round(s["total_cost"], 4),
                "avg_duration_ms": round(s["total_duration_ms"] / runs, 0) if runs else 0,
            }
        return stats


# Singleton
_swarm_executor: Optional[CelerySwarmExecutor] = None


def get_swarm_executor(use_cache: bool = True) -> CelerySwarmExecutor:
    global _swarm_executor
    if _swarm_executor is None:
        _swarm_executor = CelerySwarmExecutor(use_cache=use_cache)
    return _swarm_executor
