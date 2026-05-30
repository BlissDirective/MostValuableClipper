"""
Auto-Scaler Service — Queue-Depth-Based Worker Scaling (Phase 5)

Monitors Celery queue depths and scales worker pools up/down based on:
  - Queue depth (number of pending tasks)
  - Processing latency (average task completion time)
  - Worker utilization (active / total workers)
  - Cost budget (hard cap on concurrent workers)

Scale-up triggers:
  - Queue depth > 50 for 2 consecutive checks
  - Average latency > 3x baseline for 2 consecutive checks
  - Worker utilization > 80% for 3 consecutive checks

Scale-down triggers:
  - Queue depth < 10 for 5 consecutive checks
  - Worker utilization < 30% for 5 consecutive checks

Usage:
    from app.services.autoscaler import QueueDepthAutoscaler
    scaler = QueueDepthAutoscaler()
    await scaler.check_and_scale()  # Run every 60 seconds
"""
from __future__ import annotations

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ScalingAction(str, Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    HOLD = "hold"


@dataclass
class WorkerPoolConfig:
    """Configuration for a scalable worker pool."""
    pool_name: str
    queue_names: List[str]
    min_workers: int = 1
    max_workers: int = 20
    current_workers: int = 2
    target_workers: int = 2
    scale_up_threshold: int = 50        # Queue depth
    scale_down_threshold: int = 10      # Queue depth
    scale_up_increment: int = 2
    scale_down_decrement: int = 1
    latency_baseline_ms: int = 30_000   # 30 seconds
    hard_budget_max: int = 50           # Absolute max regardless of load


@dataclass
class ScalingDecision:
    """A decision to scale a worker pool."""
    pool_name: str
    action: ScalingAction
    current_workers: int
    target_workers: int
    reason: str
    queue_depth: int = 0
    avg_latency_ms: int = 0
    utilization_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pool_name": self.pool_name,
            "action": self.action.value,
            "current_workers": self.current_workers,
            "target_workers": self.target_workers,
            "worker_delta": self.target_workers - self.current_workers,
            "reason": self.reason,
            "queue_depth": self.queue_depth,
            "avg_latency_ms": self.avg_latency_ms,
            "utilization_pct": round(self.utilization_pct, 1),
        }


class QueueDepthAutoscaler:
    """Automatically scale worker pools based on queue metrics.

    Uses a hysteresis approach to prevent flapping:
      - Scale-up requires 2 consecutive triggers
      - Scale-down requires 5 consecutive triggers
      - Never scales below min_workers or above max_workers
    """

    DEFAULT_POOLS: Dict[str, WorkerPoolConfig] = {
        "ai": WorkerPoolConfig(
            pool_name="ai",
            queue_names=["pipeline.transcribe", "pipeline.safety", "pipeline.enrich",
                        "swarm.hooks", "swarm.post", "swarm.ab_test"],
            min_workers=2, max_workers=20,
            current_workers=4, target_workers=4,
            scale_up_threshold=50, scale_down_threshold=10,
            scale_up_increment=2, scale_down_decrement=1,
            latency_baseline_ms=30_000,
        ),
        "ffmpeg": WorkerPoolConfig(
            pool_name="ffmpeg",
            queue_names=["pipeline.generate", "pipeline.thumbnail"],
            min_workers=1, max_workers=10,
            current_workers=2, target_workers=2,
            scale_up_threshold=20, scale_down_threshold=5,
            scale_up_increment=1, scale_down_decrement=1,
            latency_baseline_ms=120_000,
        ),
        "io": WorkerPoolConfig(
            pool_name="io",
            queue_names=["pipeline.download", "pipeline.upload"],
            min_workers=1, max_workers=15,
            current_workers=2, target_workers=2,
            scale_up_threshold=30, scale_down_threshold=5,
            scale_up_increment=2, scale_down_decrement=1,
            latency_baseline_ms=15_000,
        ),
    }

    def __init__(self, pools: Optional[Dict[str, WorkerPoolConfig]] = None):
        self.pools = pools or dict(self.DEFAULT_POOLS)
        self._trigger_counts: Dict[str, Dict[str, int]] = {
            name: {"scale_up": 0, "scale_down": 0}
            for name in self.pools
        }
        self._scale_up_required = 2   # Consecutive triggers needed
        self._scale_down_required = 5
        self._decisions: List[ScalingDecision] = []

    async def check_and_scale(self) -> List[ScalingDecision]:
        """Check all pools and make scaling decisions.

        Returns list of decisions taken. Call every 60 seconds.
        """
        decisions: List[ScalingDecision] = []

        for pool_name, pool in self.pools.items():
            metrics = await self._get_queue_metrics(pool)
            decision = self._evaluate_pool(pool, metrics)

            if decision.action != ScalingAction.HOLD:
                decisions.append(decision)
                self._apply_decision(pool, decision)

        self._decisions.extend(decisions)
        return decisions

    async def _get_queue_metrics(self, pool: WorkerPoolConfig) -> Dict[str, Any]:
        """Get metrics for a worker pool's queues.

        In production, queries Redis/RMQ for queue depth and
        Celery inspect for worker stats.
        """
        try:
            from app.core.celery_config import celery_app
            inspect = celery_app.control.inspect(timeout=5)

            # Get queue depths
            active_queues = inspect.active_queues() or {}
            scheduled = inspect.scheduled() or {}
            reserved = inspect.reserved() or {}

            total_depth = 0
            worker_count = 0
            active_tasks = 0

            for worker_name, queues in active_queues.items():
                queue_names = [q["name"] for q in queues]
                if any(pq in queue_names for pq in pool.queue_names):
                    worker_count += 1
                    active_tasks += len(scheduled.get(worker_name, []))
                    active_tasks += len(reserved.get(worker_name, []))

            # Estimate queue depth from scheduled + reserved
            total_depth = active_tasks

            # Estimate latency (use baseline if no data)
            avg_latency = pool.latency_baseline_ms

            # Calculate utilization
            utilization = (active_tasks / max(worker_count * pool.current_workers, 1)) * 100

            return {
                "queue_depth": total_depth,
                "avg_latency_ms": avg_latency,
                "utilization_pct": min(utilization, 100.0),
                "worker_count": worker_count,
            }

        except Exception as e:
            logger.warning(f"[AutoScaler] Metrics fetch failed for {pool.pool_name}: {e}")
            return {
                "queue_depth": 0, "avg_latency_ms": pool.latency_baseline_ms,
                "utilization_pct": 0.0, "worker_count": pool.current_workers,
            }

    def _evaluate_pool(self, pool: WorkerPoolConfig,
                       metrics: Dict[str, Any]) -> ScalingDecision:
        """Evaluate whether to scale a pool up, down, or hold."""
        depth = metrics["queue_depth"]
        latency = metrics["avg_latency_ms"]
        utilization = metrics["utilization_pct"]
        triggers = self._trigger_counts[pool.pool_name]

        # Check scale-up conditions
        scale_up_triggered = (
            depth > pool.scale_up_threshold or
            latency > pool.latency_baseline_ms * 3 or
            utilization > 80.0
        )

        # Check scale-down conditions
        scale_down_triggered = (
            depth < pool.scale_down_threshold and
            utilization < 30.0
        )

        if scale_up_triggered:
            triggers["scale_up"] += 1
            triggers["scale_down"] = 0
        elif scale_down_triggered:
            triggers["scale_down"] += 1
            triggers["scale_up"] = 0
        else:
            triggers["scale_up"] = max(0, triggers["scale_up"] - 1)
            triggers["scale_down"] = max(0, triggers["scale_down"] - 1)

        # Make decision based on trigger history
        if triggers["scale_up"] >= self._scale_up_required:
            new_target = min(
                pool.current_workers + pool.scale_up_increment,
                pool.max_workers,
                pool.hard_budget_max,
            )
            if new_target > pool.current_workers:
                triggers["scale_up"] = 0
                return ScalingDecision(
                    pool_name=pool.pool_name,
                    action=ScalingAction.SCALE_UP,
                    current_workers=pool.current_workers,
                    target_workers=new_target,
                    reason=f"queue_depth={depth} > threshold={pool.scale_up_threshold}, "
                           f"utilization={utilization:.0f}%",
                    queue_depth=depth,
                    avg_latency_ms=latency,
                    utilization_pct=utilization,
                )

        if triggers["scale_down"] >= self._scale_down_required:
            new_target = max(
                pool.current_workers - pool.scale_down_decrement,
                pool.min_workers,
            )
            if new_target < pool.current_workers:
                triggers["scale_down"] = 0
                return ScalingDecision(
                    pool_name=pool.pool_name,
                    action=ScalingAction.SCALE_DOWN,
                    current_workers=pool.current_workers,
                    target_workers=new_target,
                    reason=f"queue_depth={depth} < threshold={pool.scale_down_threshold}, "
                           f"utilization={utilization:.0f}%",
                    queue_depth=depth,
                    avg_latency_ms=latency,
                    utilization_pct=utilization,
                )

        return ScalingDecision(
            pool_name=pool.pool_name,
            action=ScalingAction.HOLD,
            current_workers=pool.current_workers,
            target_workers=pool.current_workers,
            reason=f"queue_depth={depth}, utilization={utilization:.0f}%, stable",
            queue_depth=depth,
            avg_latency_ms=latency,
            utilization_pct=utilization,
        )

    def _apply_decision(self, pool: WorkerPoolConfig, decision: ScalingDecision) -> None:
        """Apply a scaling decision to a pool."""
        if decision.action == ScalingAction.SCALE_UP:
            pool.current_workers = decision.target_workers
            pool.target_workers = decision.target_workers
            logger.info(f"[AutoScaler] SCALE UP {pool.pool_name}: "
                       f"{decision.current_workers} -> {decision.target_workers} workers. "
                       f"Reason: {decision.reason}")
        elif decision.action == ScalingAction.SCALE_DOWN:
            pool.current_workers = decision.target_workers
            pool.target_workers = decision.target_workers
            logger.info(f"[AutoScaler] SCALE DOWN {pool.pool_name}: "
                       f"{decision.current_workers} -> {decision.target_workers} workers. "
                       f"Reason: {decision.reason}")

    def get_pool_status(self) -> Dict[str, Any]:
        """Get current status of all pools."""
        return {
            name: {
                "current_workers": pool.current_workers,
                "target_workers": pool.target_workers,
                "min_workers": pool.min_workers,
                "max_workers": pool.max_workers,
                "queue_names": pool.queue_names,
            }
            for name, pool in self.pools.items()
        }

    def get_recent_decisions(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent scaling decisions."""
        return [d.to_dict() for d in self._decisions[-count:]]


# Singleton
_autoscaler: Optional[QueueDepthAutoscaler] = None


def get_autoscaler() -> QueueDepthAutoscaler:
    global _autoscaler
    if _autoscaler is None:
        _autoscaler = QueueDepthAutoscaler()
    return _autoscaler
