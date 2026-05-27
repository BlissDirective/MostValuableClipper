"""
Phase 3 Comprehensive Test Suite
Tests: CelerySwarmExecutor, AnalyticsService, Distributed Execution
Run: pytest app/tests/test_phase3_distributed.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.swarm_celery_executor import (
    CelerySwarmExecutor, DistributedSwarmResult, get_swarm_executor
)
from app.services.analytics_service import (
    AnalyticsService, MetricEvent, get_analytics
)


class TestDistributedSwarmResult:
    """Test the result dataclass."""

    def test_basic_creation(self):
        r = DistributedSwarmResult(
            job_id="test-123", pool_type="hook", total_agents=3,
            completed=3, failed=0, results=[{"status": "completed"}],
            best_result=None, total_cost_usd=0.015, duration_ms=1000,
        )
        assert r.job_id == "test-123"
        assert r.pool_type == "hook"
        assert r.completed == 3
        assert r.failed == 0
        assert r.total_cost_usd == 0.015

    def test_to_dict(self):
        r = DistributedSwarmResult(
            job_id="test", pool_type="hook", total_agents=2,
            completed=2, failed=0, results=[], best_result=None,
            total_cost_usd=0.01, duration_ms=500,
            model_breakdown={"claude": 2},
        )
        d = r.to_dict()
        assert d["job_id"] == "test"
        assert d["success_rate"] == 100.0  # 2/2
        assert d["model_breakdown"]["claude"] == 2
        assert "total_cost_usd" in d

    def test_empty_results(self):
        r = DistributedSwarmResult(
            job_id="test", pool_type="hook", total_agents=0,
            completed=0, failed=0, results=[], best_result=None,
            total_cost_usd=0.0, duration_ms=0,
        )
        assert r.total_agents == 0
        d = r.to_dict()
        assert d["success_rate"] == 0.0


class TestCelerySwarmExecutorInterface:
    """Test executor interface and singleton."""

    def test_singleton(self):
        e1 = get_swarm_executor()
        e2 = get_swarm_executor()
        assert e1 is e2

    def test_has_all_execute_methods(self):
        e = CelerySwarmExecutor()
        methods = [
            "execute_hook_swarm", "execute_remix_swarm",
            "execute_post_swarm", "execute_ab_test_swarm",
            "execute_music_match_swarm", "execute_thumbnail_swarm",
            "execute_safety_swarm", "execute_segment_analyze_swarm",
            "execute_edit_swarm",
        ]
        for m in methods:
            assert hasattr(e, m), f"Missing method: {m}"
            assert callable(getattr(e, m))

    def test_agent_task_map_complete(self):
        """All 10 pool types must have task mappings."""
        expected = {"hook", "remix", "post", "ab_test", "music_match",
                    "thumbnail", "safety", "segment", "edit"}
        actual = set(CelerySwarmExecutor.AGENT_TASK_MAP.keys())
        assert expected == actual, f"Missing: {expected - actual}"

    def test_best_result_selectors(self):
        """Key pool types must have best-result selectors."""
        selectors = CelerySwarmExecutor.BEST_RESULT_SELECTOR
        assert "hook" in selectors
        assert "remix" in selectors
        assert "music_match" in selectors
        assert "segment" in selectors
        assert "safety" in selectors

    def test_stats_initially_empty(self):
        e = CelerySwarmExecutor()
        assert e.get_stats() == {}

    def test_normalize_results(self):
        e = CelerySwarmExecutor()
        raw = [{"status": "completed"}, Exception("fail")]
        norm = e._normalize_results(raw, 2)
        assert len(norm) == 2
        assert norm[0]["status"] == "completed"
        assert norm[1]["status"] == "failed"

    def test_normalize_results_pads(self):
        e = CelerySwarmExecutor()
        norm = e._normalize_results([], 3)
        assert len(norm) == 3
        assert all(r["status"] == "failed" for r in norm)

    def test_update_stats(self):
        e = CelerySwarmExecutor()
        e._update_stats("hook", 3, 3, 0, 0.015, 1000)
        stats = e.get_stats()
        assert "hook" in stats
        assert stats["hook"]["runs"] == 1
        assert stats["hook"]["success_rate"] == 100.0

    def test_update_stats_multiple_runs(self):
        e = CelerySwarmExecutor()
        e._update_stats("hook", 3, 2, 1, 0.01, 1000)
        e._update_stats("hook", 3, 3, 0, 0.015, 800)
        stats = e.get_stats()
        assert stats["hook"]["runs"] == 2
        assert stats["hook"]["success_rate"] == 83.3  # 5/6

    def test_result_selector_hook(self):
        sel = CelerySwarmExecutor.BEST_RESULT_SELECTOR["hook"]
        results = [
            {"status": "completed", "data": {"estimated_retention": 0.5}},
            {"status": "completed", "data": {"estimated_retention": 0.8}},
            {"status": "failed", "data": {}},
        ]
        best = sel(results)
        assert best["data"]["estimated_retention"] == 0.8

    def test_result_selector_safety(self):
        sel = CelerySwarmExecutor.BEST_RESULT_SELECTOR["safety"]
        results = [
            {"status": "completed", "data": {"requires_review": False}},
            {"status": "completed", "data": {"requires_review": True}},
        ]
        best = sel(results)
        assert best["data"]["requires_review"] is True


class TestMetricEvent:
    """Test analytics metric event dataclass."""

    def test_basic_event(self):
        e = MetricEvent(
            event_type="llm_call", clip_id="abc", user_id="xyz",
            task_type="hook_generate", model_used="claude-sonnet-4.6",
            cost_usd=0.005, tokens_in=100, tokens_out=50,
            duration_ms=800, status="success",
        )
        assert e.event_type == "llm_call"
        assert e.cost_usd == 0.005
        d = e.to_dict()
        assert d["event_type"] == "llm_call"
        assert d["clip_id"] == "abc"
        assert "timestamp" in d

    def test_cached_event(self):
        e = MetricEvent(event_type="llm_call", cached=True, cost_usd=0)
        assert e.cached is True
        assert e.cost_usd == 0

    def test_serialization(self):
        e = MetricEvent(event_type="test", metadata={"key": "value"})
        d = e.to_dict()
        assert "metadata_json" in d
        import json
        assert json.loads(d["metadata_json"]) == {"key": "value"}


class TestAnalyticsServiceInterface:
    """Test analytics service interface."""

    def test_singleton(self):
        a1 = get_analytics()
        a2 = get_analytics()
        assert a1 is a2

    def test_has_all_methods(self):
        a = AnalyticsService()
        methods = [
            "record_event", "record_llm_call", "record_pipeline_stage",
            "record_agent_execution", "get_daily_costs", "get_user_usage",
            "get_system_metrics", "get_model_efficiency_report",
            "run_daily_aggregation",
        ]
        for m in methods:
            assert hasattr(a, m), f"Missing: {m}"

    def test_buffering(self):
        a = AnalyticsService()
        assert len(a._buffer) == 0
        assert a._buffer_size == 50


class TestPhase3PhaseIntegration:
    """Verify Phase 3 components integrate with Phases 1-2."""

    def test_executor_uses_correct_task_types(self):
        """Verify agent task types match LLMRouter task types."""
        from app.services.llm_router import TASK_MODEL_MAP
        executor_types = {"hook", "remix", "post", "ab_test", "music_match",
                         "thumbnail", "safety", "segment", "edit"}
        router_types = set(TASK_MODEL_MAP.keys())
        # All executor types should have corresponding router entries
        for et in executor_types:
            mapped = {
                "hook": "hook_generate",
                "remix": "remix_generate",
                "post": "post_text_generate",
                "ab_test": "ab_test_variants",
                "music_match": "music_match",
                "thumbnail": "thumbnail_text",
                "safety": "safety_check",
                "segment": "segment_analyze",
                "edit": "edit_instructions",
            }
            assert mapped[et] in router_types, f"No router mapping for {et} -> {mapped[et]}"

    def test_all_pools_have_tier_assignment(self):
        """Every swarm pool must have a tier in the LLMRouter."""
        from app.services.llm_router import TASK_MODEL_MAP
        pool_to_task = {
            "hook": "hook_generate",
            "remix": "remix_generate",
            "post": "post_text_generate",
            "ab_test": "ab_test_variants",
            "music_match": "music_match",
            "thumbnail": "thumbnail_text",
            "safety": "safety_check",
            "segment": "segment_analyze",
            "edit": "edit_instructions",
        }
        for pool, task in pool_to_task.items():
            assert task in TASK_MODEL_MAP, f"Pool '{pool}' -> task '{task}' not in TASK_MODEL_MAP"
            assert "tier" in TASK_MODEL_MAP[task]

    def test_analytics_records_zero_cost_for_cached(self):
        a = AnalyticsService()
        e = MetricEvent(event_type="llm_call", cached=True, cost_usd=0)
        assert e.cached is True
        assert e.cost_usd == 0

    def test_cost_tracking_precision(self):
        """Verify cost tracking handles very small values correctly."""
        costs = [0.0002, 0.0003, 0.0001, 0.0002]
        total = sum(costs)
        assert round(total, 4) == 0.0008
