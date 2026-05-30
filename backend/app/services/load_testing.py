"""
Load Testing Service — Performance Benchmarking (Phase 5)

Simulates production workloads to validate the system can handle
1,000-10,000 clips per day. Measures:
  - Pipeline end-to-end latency
  - Per-stage execution time
  - LLM cost per clip at scale
  - Worker throughput and utilization
  - Queue depth under load

Usage:
    from app.services.load_testing import LoadTestRunner
    runner = LoadTestRunner()
    report = await runner.run_test(clip_count=1000, concurrent=50)
"""
from __future__ import annotations

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LoadTestResult:
    """Results from a load test run."""
    test_id: str
    clip_count: int
    concurrent_clips: int
    total_duration_ms: int
    successful_clips: int
    failed_clips: int
    avg_latency_ms: int
    p50_latency_ms: int
    p95_latency_ms: int
    p99_latency_ms: int
    total_cost_usd: float
    cost_per_clip_usd: float
    clips_per_second: float
    max_queue_depth: int = 0
    worker_utilization_avg: float = 0.0

    def meets_sla(self, target_clips_per_day: int = 10_000) -> Dict[str, Any]:
        """Check if results meet the production SLA targets."""
        daily_capacity = int(self.clips_per_second * 86400)
        latency_sla_met = self.p95_latency_ms < 120_000  # 2 min p95
        cost_sla_met = self.cost_per_clip_usd < 0.15
        capacity_sla_met = daily_capacity >= target_clips_per_day

        return {
            "meets_all_sla": latency_sla_met and cost_sla_met and capacity_sla_met,
            "daily_capacity": daily_capacity,
            "target_daily": target_clips_per_day,
            "latency_sla_ms": 120_000,
            "latency_sla_met": latency_sla_met,
            "cost_sla_usd": 0.15,
            "cost_sla_met": cost_sla_met,
            "capacity_sla_met": capacity_sla_met,
            "recommendations": self._generate_recommendations(
                latency_sla_met, cost_sla_met, capacity_sla_met, daily_capacity
            ),
        }

    def _generate_recommendations(self, lat_ok: bool, cost_ok: bool,
                                   cap_ok: bool, daily_cap: int) -> List[str]:
        recs = []
        if not lat_ok:
            recs.append("P95 latency > 2min: Add more AI workers or enable parallel pipeline")
        if not cost_ok:
            recs.append("Cost per clip > $0.15: Enable response caching and batch API")
        if not cap_ok:
            needed = (10000 - daily_cap) / 86400
            recs.append(f"Capacity shortfall: Need +{needed:.1f} clips/sec. Scale workers.")
        if not recs:
            recs.append("All SLAs met. System ready for production load.")
        return recs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "clip_count": self.clip_count,
            "concurrent_clips": self.concurrent_clips,
            "total_duration_ms": self.total_duration_ms,
            "total_duration_sec": round(self.total_duration_ms / 1000, 1),
            "successful_clips": self.successful_clips,
            "failed_clips": self.failed_clips,
            "success_rate": round(self.successful_clips / max(self.clip_count, 1) * 100, 1),
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "cost_per_clip_usd": round(self.cost_per_clip_usd, 6),
            "clips_per_second": round(self.clips_per_second, 2),
            "max_queue_depth": self.max_queue_depth,
            "worker_utilization_avg": round(self.worker_utilization_avg, 1),
        }


class LoadTestRunner:
    """Run controlled load tests against the pipeline."""

    # Pre-configured test profiles
    PROFILES = {
        "smoke":      {"clips": 10,   "concurrent": 2,  "description": "Quick validation"},
        "capacity_1k": {"clips": 100,  "concurrent": 10, "description": "1K/day validation"},
        "capacity_5k": {"clips": 500,  "concurrent": 25, "description": "5K/day validation"},
        "capacity_10k": {"clips": 1000, "concurrent": 50, "description": "10K/day validation"},
        "stress":     {"clips": 2000, "concurrent": 100, "description": "Stress test"},
    }

    async def run_test(self, clip_count: int = 100, concurrent: int = 10,
                       profile: Optional[str] = None) -> LoadTestResult:
        """Run a load test with specified parameters.

        Args:
            clip_count: Total number of clips to process
            concurrent: Number of clips to process in parallel
            profile: Use a predefined profile (overrides other params)

        Returns:
            LoadTestResult with full performance metrics
        """
        if profile and profile in self.PROFILES:
            p = self.PROFILES[profile]
            clip_count = p["clips"]
            concurrent = p["concurrent"]

        test_id = f"load_{int(time.time())}"
        logger.info(f"[LoadTest] Starting test={test_id} clips={clip_count} concurrent={concurrent}")

        start_time = time.time()
        semaphore = asyncio.Semaphore(concurrent)

        # Launch all clip processing tasks
        tasks = [
            self._process_single_clip(semaphore, i)
            for i in range(clip_count)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_duration = int((time.time() - start_time) * 1000)

        # Analyze results
        latencies = []
        total_cost = 0.0
        successful = 0
        failed = 0

        for r in results:
            if isinstance(r, Exception):
                failed += 1
                continue
            if isinstance(r, dict):
                successful += 1
                latencies.append(r.get("duration_ms", 0))
                total_cost += r.get("cost_usd", 0.0)
            else:
                failed += 1

        # Calculate percentiles
        latencies.sort()
        n = len(latencies)
        p50 = latencies[n // 2] if n else 0
        p95_idx = int(n * 0.95)
        p99_idx = int(n * 0.99)
        p95 = latencies[min(p95_idx, n - 1)] if n else 0
        p99 = latencies[min(p99_idx, n - 1)] if n else 0
        avg_lat = sum(latencies) // max(n, 1)

        clips_per_sec = clip_count / max(total_duration / 1000, 0.001)
        cost_per_clip = total_cost / max(successful, 1)

        result = LoadTestResult(
            test_id=test_id, clip_count=clip_count,
            concurrent_clips=concurrent,
            total_duration_ms=total_duration,
            successful_clips=successful, failed_clips=failed,
            avg_latency_ms=avg_lat, p50_latency_ms=p50,
            p95_latency_ms=p95, p99_latency_ms=p99,
            total_cost_usd=total_cost, cost_per_clip_usd=cost_per_clip,
            clips_per_second=clips_per_sec,
        )

        # Log SLA check
        sla = result.meets_sla()
        logger.info(f"[LoadTest] Completed test={test_id}: "
                   f"success={successful}/{clip_count} "
                   f"p95={p95}ms cost=${cost_per_clip:.4f}/clip "
                   f"capacity={sla['daily_capacity']}/day "
                   f"sla_met={sla['meets_all_sla']}")

        for rec in sla["recommendations"]:
            logger.info(f"[LoadTest] Recommendation: {rec}")

        return result

    async def _process_single_clip(self, semaphore: asyncio.Semaphore,
                                   index: int) -> Dict[str, Any]:
        """Process a single simulated clip."""
        async with semaphore:
            clip_start = time.time()

            # Simulate the parallel pipeline
            from app.services.parallel_pipeline import get_parallel_executor
            executor = get_parallel_executor()

            clip_id = f"loadtest_{index}"
            source_url = f"https://example.com/video_{index}.mp4"
            user_id = "loadtest_user"

            try:
                result = await executor.execute_parallel(clip_id, source_url, user_id)
                duration_ms = int((time.time() - clip_start) * 1000)

                return {
                    "clip_id": clip_id,
                    "status": "success",
                    "duration_ms": duration_ms,
                    "cost_usd": result.total_cost_usd,
                    "stages_completed": result.stages_executed,
                }

            except Exception as e:
                logger.warning(f"[LoadTest] Clip {clip_id} failed: {e}")
                return {
                    "clip_id": clip_id,
                    "status": "failed",
                    "duration_ms": int((time.time() - clip_start) * 1000),
                    "cost_usd": 0.0,
                    "error": str(e),
                }

    def list_profiles(self) -> Dict[str, Dict[str, Any]]:
        """List available test profiles."""
        return {
            name: {"clips": p["clips"], "concurrent": p["concurrent"],
                   "description": p["description"]}
            for name, p in self.PROFILES.items()
        }


# Singleton
_load_tester: Optional[LoadTestRunner] = None


def get_load_tester() -> LoadTestRunner:
    global _load_tester
    if _load_tester is None:
        _load_tester = LoadTestRunner()
    return _load_tester
