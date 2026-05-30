"""
Phase 5 Comprehensive Test Suite
Tests: Parallel Pipeline, Auto-Scaler, Load Testing
Run: pytest app/tests/test_phase5_parallel_autoscale_load.py -v
"""
import sys, os, asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.parallel_pipeline import (
    ParallelPipelineExecutor, ParallelPipelineResult, StageResult,
    PipelineStage, STAGE_DEPENDENCIES, PARALLEL_GROUPS,
    get_parallel_executor
)
from app.services.autoscaler import (
    QueueDepthAutoscaler, WorkerPoolConfig, ScalingAction, ScalingDecision,
    get_autoscaler
)
from app.services.load_testing import (
    LoadTestRunner, LoadTestResult, get_load_tester
)


# ============================================================================
# Parallel Pipeline Tests
# ============================================================================

class TestPipelineStageEnum:
    def test_all_stages_present(self):
        stages = list(PipelineStage)
        assert len(stages) == 9
        assert PipelineStage.DOWNLOAD in stages
        assert PipelineStage.EXTRACT_AUDIO in stages
        assert PipelineStage.TRANSCRIBE in stages
        assert PipelineStage.DETECT_SEGMENTS in stages
        assert PipelineStage.SAFETY_CHECK in stages
        assert PipelineStage.GENERATE_CLIPS in stages
        assert PipelineStage.CREATE_THUMBNAILS in stages
        assert PipelineStage.ENRICH_CONTENT in stages
        assert PipelineStage.UPLOAD_ASSETS in stages


class TestStageDependencies:
    def test_download_has_no_deps(self):
        assert STAGE_DEPENDENCIES[PipelineStage.DOWNLOAD] == set()

    def test_extract_audio_has_no_deps(self):
        assert STAGE_DEPENDENCIES[PipelineStage.EXTRACT_AUDIO] == set()

    def test_transcribe_depends_on_download_and_audio(self):
        deps = STAGE_DEPENDENCIES[PipelineStage.TRANSCRIBE]
        assert PipelineStage.DOWNLOAD in deps
        assert PipelineStage.EXTRACT_AUDIO in deps

    def test_detect_segments_depends_on_transcribe(self):
        deps = STAGE_DEPENDENCIES[PipelineStage.DETECT_SEGMENTS]
        assert PipelineStage.TRANSCRIBE in deps

    def test_safety_check_depends_on_transcribe(self):
        deps = STAGE_DEPENDENCIES[PipelineStage.SAFETY_CHECK]
        assert PipelineStage.TRANSCRIBE in deps

    def test_generate_clips_depends_on_detect_segments(self):
        deps = STAGE_DEPENDENCIES[PipelineStage.GENERATE_CLIPS]
        assert PipelineStage.DETECT_SEGMENTS in deps

    def test_upload_depends_on_generate_thumbnails_enrich(self):
        deps = STAGE_DEPENDENCIES[PipelineStage.UPLOAD_ASSETS]
        assert PipelineStage.GENERATE_CLIPS in deps
        assert PipelineStage.CREATE_THUMBNAILS in deps
        assert PipelineStage.ENRICH_CONTENT in deps

    def test_no_circular_dependencies(self):
        """Verify the dependency graph has no cycles."""
        visited = set()
        recursion_stack = set()

        def has_cycle(stage, visited, stack):
            visited.add(stage)
            stack.add(stage)
            for dep in STAGE_DEPENDENCIES.get(stage, set()):
                if dep not in visited:
                    if has_cycle(dep, visited, stack):
                        return True
                elif dep in stack:
                    return True
            stack.remove(stage)
            return False

        for stage in PipelineStage:
            if stage not in visited:
                assert not has_cycle(stage, visited, recursion_stack), \
                    f"Cycle detected involving {stage.value}"

    def test_all_stages_have_deps_defined(self):
        for stage in PipelineStage:
            assert stage in STAGE_DEPENDENCIES, f"{stage.value} missing from STAGE_DEPENDENCIES"


class TestStageResult:
    def test_creation(self):
        r = StageResult(stage="download", status="completed", duration_ms=1000, cost_usd=0.01)
        assert r.stage == "download"
        assert r.is_success is True

    def test_failed_not_success(self):
        r = StageResult(stage="download", status="failed")
        assert r.is_success is False

    def test_pending_not_success(self):
        r = StageResult(stage="download", status="pending")
        assert r.is_success is False


class TestParallelPipelineExecutor:
    def test_singleton(self):
        e1 = get_parallel_executor()
        e2 = get_parallel_executor()
        assert e1 is e2

    def test_has_all_handlers(self):
        e = ParallelPipelineExecutor()
        assert len(e._stage_handlers) == 9
        for stage in PipelineStage:
            assert stage in e._stage_handlers

    def test_execution_waves(self):
        e = ParallelPipelineExecutor()
        waves = e._build_execution_waves()
        assert len(waves) >= 4  # Should have multiple waves

        # First wave should be stages with no dependencies
        first_wave = set(waves[0])
        assert PipelineStage.DOWNLOAD in first_wave
        assert PipelineStage.EXTRACT_AUDIO in first_wave

        # All stages should appear in exactly one wave
        all_stages_in_waves = set()
        for wave in waves:
            for stage in wave:
                assert stage not in all_stages_in_waves, f"{stage.value} appears in multiple waves"
                all_stages_in_waves.add(stage)

        assert len(all_stages_in_waves) == len(PipelineStage)

    def test_prerequisites_met_for_root_stages(self):
        e = ParallelPipelineExecutor()
        completed = set()
        results = {}
        assert e._prerequisites_met(PipelineStage.DOWNLOAD, completed, True, results) is True
        assert e._prerequisites_met(PipelineStage.EXTRACT_AUDIO, completed, True, results) is True

    def test_prerequisites_met_after_completion(self):
        e = ParallelPipelineExecutor()
        completed = {PipelineStage.DOWNLOAD, PipelineStage.EXTRACT_AUDIO}
        results = {s.value: StageResult(stage=s.value, status="completed") for s in completed}
        assert e._prerequisites_met(PipelineStage.TRANSCRIBE, completed, True, results) is True

    def test_prerequisites_not_met_when_failed(self):
        e = ParallelPipelineExecutor()
        completed = set()
        results = {
            PipelineStage.DOWNLOAD.value: StageResult(stage=PipelineStage.DOWNLOAD.value, status="failed"),
        }
        assert e._prerequisites_met(PipelineStage.TRANSCRIBE, completed, True, results) is False

    def test_baseline_times_positive(self):
        for stage, ms in ParallelPipelineExecutor.STAGE_BASELINE_MS.items():
            assert ms > 0, f"{stage.value} has invalid baseline {ms}"

    def test_parallelization_report(self):
        e = ParallelPipelineExecutor()
        report = e.get_parallelization_report()
        assert "total_stages" in report
        assert report["total_stages"] == 9
        assert "execution_waves" in report
        assert "theoretical_speedup" in report
        assert report["theoretical_speedup"] > 1.0

    def test_speedup_is_reasonable(self):
        e = ParallelPipelineExecutor()
        report = e.get_parallelization_report()
        # Speedup should be between 1.2x and 5x (depends on wave structure)
        assert 1.2 <= report["theoretical_speedup"] <= 5.0, \
            f"Speedup {report['theoretical_speedup']}x seems unreasonable"


# ============================================================================
# Auto-Scaler Tests
# ============================================================================

class TestWorkerPoolConfig:
    def test_defaults(self):
        p = WorkerPoolConfig(pool_name="test", queue_names=["q1"])
        assert p.min_workers == 1
        assert p.max_workers == 20
        assert p.scale_up_threshold > p.scale_down_threshold

    def test_ai_pool_config(self):
        scaler = QueueDepthAutoscaler()
        ai = scaler.pools["ai"]
        assert ai.min_workers == 2
        assert ai.max_workers == 20
        assert len(ai.queue_names) >= 3


class TestScalingDecision:
    def test_creation(self):
        d = ScalingDecision(
            pool_name="ai", action=ScalingAction.SCALE_UP,
            current_workers=2, target_workers=4,
            reason="queue_depth=60 > threshold=50",
        )
        assert d.pool_name == "ai"
        assert d.action == ScalingAction.SCALE_UP
        assert d.to_dict()["worker_delta"] == 2

    def test_scale_down(self):
        d = ScalingDecision(
            pool_name="ffmpeg", action=ScalingAction.SCALE_DOWN,
            current_workers=4, target_workers=3,
            reason="low utilization",
        )
        assert d.to_dict()["worker_delta"] == -1

    def test_hold(self):
        d = ScalingDecision(
            pool_name="io", action=ScalingAction.HOLD,
            current_workers=2, target_workers=2,
            reason="stable",
        )
        assert d.to_dict()["worker_delta"] == 0


class TestQueueDepthAutoscalerInterface:
    def test_singleton(self):
        a1 = get_autoscaler()
        a2 = get_autoscaler()
        assert a1 is a2

    def test_has_default_pools(self):
        a = QueueDepthAutoscaler()
        assert "ai" in a.pools
        assert "ffmpeg" in a.pools
        assert "io" in a.pools

    def test_default_ai_pool(self):
        a = QueueDepthAutoscaler()
        ai = a.pools["ai"]
        assert ai.scale_up_threshold == 50
        assert ai.scale_down_threshold == 10
        assert ai.scale_up_increment == 2
        assert ai.scale_down_decrement == 1

    def test_default_ffmpeg_pool(self):
        a = QueueDepthAutoscaler()
        ff = a.pools["ffmpeg"]
        assert ff.latency_baseline_ms == 120_000
        assert ff.max_workers == 10

    def test_pool_status(self):
        a = QueueDepthAutoscaler()
        status = a.get_pool_status()
        assert "ai" in status
        assert "ffmpeg" in status
        assert "current_workers" in status["ai"]

    def test_recent_decisions_empty(self):
        a = QueueDepthAutoscaler()
        assert a.get_recent_decisions() == []


class TestScalingEvaluation:
    def test_scale_up_on_high_queue_depth(self):
        a = QueueDepthAutoscaler()
        pool = a.pools["ai"]
        pool.current_workers = 2

        metrics = {"queue_depth": 100, "avg_latency_ms": 30_000, "utilization_pct": 90.0}

        # Trigger scale-up twice (required by hysteresis)
        d1 = a._evaluate_pool(pool, metrics)
        d2 = a._evaluate_pool(pool, metrics)

        assert d2.action == ScalingAction.SCALE_UP
        assert d2.target_workers == 4  # 2 + scale_up_increment

    def test_hold_after_single_trigger(self):
        a = QueueDepthAutoscaler()
        pool = a.pools["ai"]

        metrics = {"queue_depth": 100, "avg_latency_ms": 30_000, "utilization_pct": 90.0}
        d = a._evaluate_pool(pool, metrics)

        # First trigger should be HOLD (need 2 consecutive)
        assert d.action == ScalingAction.HOLD

    def test_scale_down_on_low_load(self):
        a = QueueDepthAutoscaler()
        pool = a.pools["ai"]
        pool.current_workers = 6

        metrics = {"queue_depth": 2, "avg_latency_ms": 10_000, "utilization_pct": 10.0}

        # Trigger 5 times (required by hysteresis)
        for _ in range(5):
            d = a._evaluate_pool(pool, metrics)

        assert d.action == ScalingAction.SCALE_DOWN
        assert d.target_workers == 5  # 6 - 1

    def test_never_below_min(self):
        a = QueueDepthAutoscaler()
        pool = a.pools["ai"]
        pool.current_workers = pool.min_workers

        metrics = {"queue_depth": 0, "avg_latency_ms": 10_000, "utilization_pct": 0.0}

        for _ in range(10):
            d = a._evaluate_pool(pool, metrics)

        assert d.target_workers >= pool.min_workers

    def test_never_above_max(self):
        a = QueueDepthAutoscaler()
        pool = a.pools["ai"]
        pool.current_workers = pool.max_workers

        metrics = {"queue_depth": 1000, "avg_latency_ms": 300_000, "utilization_pct": 100.0}

        for _ in range(5):
            d = a._evaluate_pool(pool, metrics)

        assert d.target_workers <= pool.max_workers

    def test_hard_budget_enforced(self):
        a = QueueDepthAutoscaler()
        pool = a.pools["ai"]
        pool.max_workers = 100  # Very high
        pool.current_workers = 48
        pool.hard_budget_max = 50

        metrics = {"queue_depth": 1000, "avg_latency_ms": 100_000, "utilization_pct": 95.0}

        for _ in range(3):
            d = a._evaluate_pool(pool, metrics)

        assert d.target_workers <= 50

    def test_high_latency_triggers_scale_up(self):
        a = QueueDepthAutoscaler()
        pool = a.pools["ai"]
        pool.current_workers = 2

        # 4x baseline latency should trigger (3x = 90K threshold)
        metrics = {"queue_depth": 10, "avg_latency_ms": 120_000, "utilization_pct": 50.0}

        # Need 2 consecutive triggers; capture the decision that triggers
        decisions = []
        for _ in range(3):
            d = a._evaluate_pool(pool, metrics)
            decisions.append(d)

        # One of the first two should be SCALE_UP
        assert any(d.action == ScalingAction.SCALE_UP for d in decisions[:2]), \
            f"Expected SCALE_UP in first 2 decisions, got: {[d.action.value for d in decisions]}"


# ============================================================================
# Load Testing Tests
# ============================================================================

class TestLoadTestResult:
    def test_creation(self):
        r = LoadTestResult(
            test_id="t1", clip_count=100, concurrent_clips=10,
            total_duration_ms=60_000, successful_clips=95, failed_clips=5,
            avg_latency_ms=500, p50_latency_ms=450,
            p95_latency_ms=800, p99_latency_ms=1000,
            total_cost_usd=5.0, cost_per_clip_usd=0.05,
            clips_per_second=1.67,
        )
        assert r.test_id == "t1"
        assert r.successful_clips == 95

    def test_sla_meets_all(self):
        r = LoadTestResult(
            test_id="t1", clip_count=1000, concurrent_clips=50,
            total_duration_ms=120_000, successful_clips=990, failed_clips=10,
            avg_latency_ms=80_000, p50_latency_ms=70_000,
            p95_latency_ms=100_000, p99_latency_ms=110_000,
            total_cost_usd=10.0, cost_per_clip_usd=0.01,
            clips_per_second=8.33,  # ~720K/day
        )
        sla = r.meets_sla()
        assert sla["meets_all_sla"] is True
        assert sla["daily_capacity"] > 10_000
        assert sla["latency_sla_met"] is True
        assert sla["cost_sla_met"] is True

    def test_sla_fails_latency(self):
        r = LoadTestResult(
            test_id="t1", clip_count=100, concurrent_clips=10,
            total_duration_ms=300_000, successful_clips=100, failed_clips=0,
            avg_latency_ms=200_000, p50_latency_ms=180_000,
            p95_latency_ms=300_000, p99_latency_ms=350_000,
            total_cost_usd=1.0, cost_per_clip_usd=0.01,
            clips_per_second=0.02,  # Very low capacity: ~1,728/day
        )
        sla = r.meets_sla()
        assert sla["meets_all_sla"] is False
        assert sla["latency_sla_met"] is False
        assert sla["capacity_sla_met"] is False  # 1,728/day < 10,000 target

    def test_sla_fails_cost(self):
        r = LoadTestResult(
            test_id="t1", clip_count=100, concurrent_clips=10,
            total_duration_ms=60_000, successful_clips=100, failed_clips=0,
            avg_latency_ms=50_000, p50_latency_ms=40_000,
            p95_latency_ms=80_000, p99_latency_ms=90_000,
            total_cost_usd=50.0, cost_per_clip_usd=0.50,
            clips_per_second=1.67,
        )
        sla = r.meets_sla()
        assert sla["meets_all_sla"] is False
        assert sla["cost_sla_met"] is False

    def test_recommendations_when_failing(self):
        r = LoadTestResult(
            test_id="t1", clip_count=100, concurrent_clips=10,
            total_duration_ms=300_000, successful_clips=100, failed_clips=0,
            avg_latency_ms=200_000, p50_latency_ms=180_000,
            p95_latency_ms=300_000, p99_latency_ms=350_000,
            total_cost_usd=50.0, cost_per_clip_usd=0.50,
            clips_per_second=0.33,
        )
        sla = r.meets_sla()
        recs = sla["recommendations"]
        assert len(recs) >= 2

    def test_success_recommendation(self):
        r = LoadTestResult(
            test_id="t1", clip_count=1000, concurrent_clips=50,
            total_duration_ms=100_000, successful_clips=1000, failed_clips=0,
            avg_latency_ms=50_000, p50_latency_ms=40_000,
            p95_latency_ms=90_000, p99_latency_ms=100_000,
            total_cost_usd=5.0, cost_per_clip_usd=0.005,
            clips_per_second=10.0,
        )
        sla = r.meets_sla()
        assert "ready for production" in sla["recommendations"][0].lower()


class TestLoadTestRunnerInterface:
    def test_singleton(self):
        r1 = get_load_tester()
        r2 = get_load_tester()
        assert r1 is r2

    def test_has_profiles(self):
        runner = LoadTestRunner()
        profiles = runner.list_profiles()
        assert "smoke" in profiles
        assert "capacity_1k" in profiles
        assert "capacity_5k" in profiles
        assert "capacity_10k" in profiles
        assert "stress" in profiles

    def test_smoke_profile(self):
        runner = LoadTestRunner()
        p = runner.PROFILES["smoke"]
        assert p["clips"] < 50
        assert p["concurrent"] < 5

    def test_10k_profile(self):
        runner = LoadTestRunner()
        p = runner.PROFILES["capacity_10k"]
        assert p["clips"] == 1000
        assert p["concurrent"] == 50

    def test_stress_profile(self):
        runner = LoadTestRunner()
        p = runner.PROFILES["stress"]
        assert p["clips"] == 2000
        assert p["concurrent"] == 100


# ============================================================================
# Cross-Phase Integration Tests
# ============================================================================

class TestPhase5Integration:
    def test_parallel_groups_are_independent(self):
        """Stages in parallel groups must not depend on each other."""
        for group in PARALLEL_GROUPS:
            stages = list(group)
            for i, s1 in enumerate(stages):
                for s2 in stages[i+1:]:
                    assert s2 not in STAGE_DEPENDENCIES.get(s1, set()), \
                        f"{s1.value} depends on {s2.value} but they're in same parallel group"
                    assert s1 not in STAGE_DEPENDENCIES.get(s2, set()), \
                        f"{s2.value} depends on {s1.value} but they're in same parallel group"

    def test_autoscaler_pools_match_queues(self):
        """Auto-scaler pool queues must exist in Celery config."""
        from app.core.celery_config import PIPELINE_QUEUES
        configured_queues = {q.name for q in PIPELINE_QUEUES}
        scaler = QueueDepthAutoscaler()
        for pool_name, pool in scaler.pools.items():
            for q in pool.queue_names:
                assert q in configured_queues, f"Pool '{pool_name}' references unknown queue '{q}'"

    def test_autoscaler_min_leq_max(self):
        for pool in QueueDepthAutoscaler().pools.values():
            assert pool.min_workers <= pool.max_workers, \
                f"Pool {pool.pool_name}: min {pool.min_workers} > max {pool.max_workers}"

    def test_all_services_have_singletons(self):
        from app.services.parallel_pipeline import get_parallel_executor
        from app.services.autoscaler import get_autoscaler
        from app.services.load_testing import get_load_tester

        assert get_parallel_executor() is get_parallel_executor()
        assert get_autoscaler() is get_autoscaler()
        assert get_load_tester() is get_load_tester()

    def test_parallel_speedup_greater_than_1(self):
        e = ParallelPipelineExecutor()
        report = e.get_parallelization_report()
        assert report["theoretical_speedup"] > 1.0, "Parallel must be faster than sequential"

    def test_load_test_meets_sla_at_10k(self):
        """Simulated 10K capacity test should pass SLA when system is properly tuned."""
        r = LoadTestResult(
            test_id="sim_10k", clip_count=1000, concurrent_clips=50,
            total_duration_ms=86_400_000 // 10,  # 10K/day = ~8.6s per batch
            successful_clips=995, failed_clips=5,
            avg_latency_ms=90_000, p50_latency_ms=80_000,
            p95_latency_ms=110_000, p99_latency_ms=115_000,
            total_cost_usd=8.0, cost_per_clip_usd=0.008,
            clips_per_second=10_000 / 86400.0,
        )
        sla = r.meets_sla(target_clips_per_day=10_000)
        assert sla["meets_all_sla"] is True, \
            f"10K SLA not met: {sla['recommendations']}"
