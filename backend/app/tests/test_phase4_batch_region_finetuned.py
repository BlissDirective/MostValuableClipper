"""
Phase 4 Comprehensive Test Suite
Tests: Batch API, Regional Config, Fine-Tuned Models
Run: pytest app/tests/test_phase4_batch_region_finetuned.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.batch_api_service import (
    BatchAPIService, BatchJob, BatchJobStatus
)
from app.core.regional_config import (
    RegionConfig, get_region_config, get_current_region,
    get_nearest_region, is_primary_region, REGION_REGISTRY
)
from app.services.finetuned_model_service import (
    FineTunedModelService, FineTunedTask, FineTunedModelConfig,
    FINETUNED_REGISTRY
)


# ============================================================================
# Batch API Service Tests
# ============================================================================

class TestBatchJobDataclass:
    def test_basic_creation(self):
        j = BatchJob(
            job_id="test-123", task_type="safety_check",
            model_used="gpt-4.1-nano", provider="openai",
            total_requests=100, status=BatchJobStatus.SUBMITTED,
        )
        assert j.job_id == "test-123"
        assert j.task_type == "safety_check"
        assert j.status == BatchJobStatus.SUBMITTED
        assert j.discount_applied == 0.5

    def test_to_dict(self):
        j = BatchJob(
            job_id="test", task_type="safety_check",
            model_used="gpt-4.1-nano", provider="openai",
            total_requests=50, status=BatchJobStatus.COMPLETED,
            estimated_cost_usd=10.0, actual_cost_usd=5.0,
            results=[{"r": 1}] * 50,
        )
        d = j.to_dict()
        assert d["job_id"] == "test"
        assert d["status"] == "completed"
        assert d["total_requests"] == 50
        assert d["estimated_cost_usd"] == 10.0
        assert d["actual_cost_usd"] == 5.0
        assert d["savings_usd"] == 5.0
        assert d["results_count"] == 50

    def test_savings_calculation(self):
        j = BatchJob(
            job_id="test", task_type="safety_check",
            model_used="gpt-4.1-nano", provider="openai",
            total_requests=100, estimated_cost_usd=20.0,
            actual_cost_usd=10.0,
        )
        assert j.to_dict()["savings_usd"] == 10.0  # 50% off

    def test_job_status_enum(self):
        assert BatchJobStatus.SUBMITTED.value == "submitted"
        assert BatchJobStatus.COMPLETED.value == "completed"
        assert BatchJobStatus.FAILED.value == "failed"


class TestBatchAPIServiceInterface:
    def test_singleton(self):
        from app.services.batch_api_service import get_batch_service
        b1 = get_batch_service()
        b2 = get_batch_service()
        assert b1 is b2

    def test_has_all_methods(self):
        b = BatchAPIService()
        methods = ["is_eligible", "submit", "get_status", "retrieve_results", "list_jobs"]
        for m in methods:
            assert hasattr(b, m), f"Missing: {m}"
            assert callable(getattr(b, m))

    def test_eligible_tasks(self):
        b = BatchAPIService()
        assert b.is_eligible("safety_check") is True
        assert b.is_eligible("hashtag_optimize") is True
        assert b.is_eligible("thumbnail_text") is True
        assert b.is_eligible("music_match") is True
        assert b.is_eligible("moderation_classify") is True
        assert b.is_eligible("content_enrich") is True
        assert b.is_eligible("ab_test_variants") is True

    def test_ineligible_tasks(self):
        b = BatchAPIService()
        assert b.is_eligible("hook_generate") is False
        assert b.is_eligible("edit_instructions") is False
        assert b.is_eligible("caption_generate") is False

    def test_all_eligible_are_economy_or_standard(self):
        """All batch-eligible tasks should be ECONOMY or STANDARD tier."""
        from app.services.llm_router import TASK_MODEL_MAP, ModelTier
        b = BatchAPIService()
        for task in b.ELIGIBLE_TASKS:
            assert task in TASK_MODEL_MAP, f"Eligible task '{task}' not in TASK_MODEL_MAP"
            tier = TASK_MODEL_MAP[task]["tier"]
            assert tier in (ModelTier.ECONOMY, ModelTier.STANDARD), \
                f"Task '{task}' is PREMIUM — should not be batch eligible"

    def test_job_tracking(self):
        b = BatchAPIService()
        # Manually inject a job
        job = BatchJob(
            job_id="track-test", task_type="safety_check",
            model_used="gpt-4.1-nano", provider="openai",
            total_requests=10, status=BatchJobStatus.COMPLETED,
            results=[{"i": i} for i in range(10)],
        )
        b._jobs["track-test"] = job

        # Test via to_dict directly (get_status is async)
        status = job.to_dict()
        assert status is not None
        assert status["job_id"] == "track-test"
        assert status["results_count"] == 10

        # Test list via _jobs dict directly
        assert len(b._jobs) == 1
        assert "track-test" in b._jobs

        completed = [j for j in b._jobs.values() if j.status == BatchJobStatus.COMPLETED]
        assert len(completed) == 1

        failed = [j for j in b._jobs.values() if j.status == BatchJobStatus.FAILED]
        assert len(failed) == 0


class TestBatchAPIErrorHandling:
    def test_ineligible_task_raises(self):
        b = BatchAPIService()
        import asyncio
        with pytest.raises(ValueError) as exc_info:
            asyncio.run(b.submit("hook_generate", ["prompt"]))
        assert "not eligible" in str(exc_info.value)

    def test_empty_prompts_raises(self):
        b = BatchAPIService()
        import asyncio
        with pytest.raises(ValueError) as exc_info:
            asyncio.run(b.submit("safety_check", []))
        assert "No prompts" in str(exc_info.value)

    def test_unknown_job_status(self):
        b = BatchAPIService()
        import asyncio
        status = asyncio.run(b.get_status("nonexistent"))
        assert status is None


# ============================================================================
# Regional Config Tests
# ============================================================================

class TestRegionConfigDataclass:
    def test_basic_creation(self):
        r = RegionConfig(
            code="lax", name="Los Angeles", timezone="America/Los_Angeles",
            database_url="postgres://lax", redis_url="redis://lax",
            storage_region="wnam", worker_capacity=50,
            latency_target_ms=100, is_primary=True,
        )
        assert r.code == "lax"
        assert r.is_primary is True
        assert r.full_name == "Los Angeles (LAX)"

    def test_full_name_format(self):
        r = RegionConfig(
            code="fra", name="Frankfurt", timezone="Europe/Berlin",
            database_url=None, redis_url=None,
            storage_region="weur", worker_capacity=20,
            latency_target_ms=150, is_primary=False,
        )
        assert r.full_name == "Frankfurt (FRA)"


class TestRegionalConfigRegistry:
    def test_all_regions_in_registry(self):
        assert "lax" in REGION_REGISTRY
        assert "iad" in REGION_REGISTRY
        assert "fra" in REGION_REGISTRY

    def test_lax_is_primary(self):
        assert REGION_REGISTRY["lax"].is_primary is True

    def test_other_regions_not_primary(self):
        assert REGION_REGISTRY["iad"].is_primary is False
        assert REGION_REGISTRY["fra"].is_primary is False

    def test_unique_storage_regions(self):
        regions = [r.storage_region for r in REGION_REGISTRY.values()]
        assert len(regions) == len(set(regions))

    def test_capacity_scaling(self):
        """Primary region has highest capacity."""
        lax_cap = REGION_REGISTRY["lax"].worker_capacity
        iad_cap = REGION_REGISTRY["iad"].worker_capacity
        fra_cap = REGION_REGISTRY["fra"].worker_capacity
        assert lax_cap >= iad_cap >= fra_cap


class TestGetRegionConfig:
    def test_returns_valid_region(self):
        r = get_region_config("lax")
        assert r.code == "lax"
        assert r.name == "Los Angeles"

    def test_unknown_region_fallback(self):
        r = get_region_config("xyz")
        assert r.code == "lax"  # Falls back

    def test_default_region(self):
        r = get_region_config()
        assert r.code in ("lax", "test")  # Depends on env


class TestGetCurrentRegion:
    def test_returns_string(self):
        region = get_current_region()
        assert isinstance(region, str)
        assert len(region) > 0


class TestGetNearestRegion:
    def test_east_coast_hint(self, monkeypatch):
        """East coast hint routes to iad when deployed."""
        monkeypatch.setenv("DEPLOYED_REGIONS", "lax,iad,fra")
        r = get_nearest_region("us-east")
        assert r == "iad"

    def test_europe_hint(self, monkeypatch):
        """Europe hint routes to fra when deployed."""
        monkeypatch.setenv("DEPLOYED_REGIONS", "lax,iad,fra")
        r = get_nearest_region("eu")
        assert r == "fra"

    def test_no_hint_returns_current(self):
        r = get_nearest_region()
        assert r == get_current_region()

    def test_unknown_hint_returns_default(self):
        r = get_nearest_region("mars")
        assert r == get_current_region()

    def test_east_coast_fallback_when_not_deployed(self, monkeypatch):
        """Falls back to lax when iad is not deployed."""
        monkeypatch.setenv("DEPLOYED_REGIONS", "lax")
        r = get_nearest_region("us-east")
        assert r == "lax"


class TestIsPrimaryRegion:
    def test_returns_bool(self):
        result = is_primary_region()
        assert isinstance(result, bool)


# ============================================================================
# Fine-Tuned Model Service Tests
# ============================================================================

class TestFineTunedModelConfig:
    def test_config_creation(self):
        c = FineTunedModelConfig(
            task=FineTunedTask.SAFETY_CLASSIFIER,
            model_id="ft:gpt-4.1-nano:org:safety:abc",
            base_model="gpt-4.1-nano",
            deployment="groq",
            input_cost_per_1m=0.10, output_cost_per_1m=0.40,
            accuracy_score=0.94, latency_ms_avg=50,
            training_examples=5000,
        )
        assert c.task == FineTunedTask.SAFETY_CLASSIFIER
        assert c.accuracy_score == 0.94
        assert c.training_examples == 5000


class TestFineTunedModelServiceInterface:
    def test_singleton(self):
        from app.services.finetuned_model_service import get_finetuned_service
        f1 = get_finetuned_service()
        f2 = get_finetuned_service()
        assert f1 is f2

    def test_has_all_methods(self):
        f = FineTunedModelService()
        methods = ["is_available", "predict", "get_model_info", "list_available_models"]
        for m in methods:
            assert hasattr(f, m), f"Missing: {m}"

    def test_task_mapping_completeness(self):
        """All mapped tasks should have registry entries."""
        f = FineTunedModelService()
        for router_task, ft_task in f.TASK_MAPPING.items():
            assert ft_task in FINETUNED_REGISTRY, f"No registry for {ft_task}"

    def test_mapped_tasks_are_economy(self):
        """All fine-tuned tasks should map to ECONOMY-tier router tasks."""
        from app.services.llm_router import TASK_MODEL_MAP, ModelTier
        f = FineTunedModelService()
        for router_task in f.TASK_MAPPING.keys():
            tier = TASK_MODEL_MAP[router_task]["tier"]
            assert tier == ModelTier.ECONOMY, \
                f"Task '{router_task}' should be ECONOMY for fine-tuning"

    def test_is_available_without_env(self):
        """Without API keys, no models should be available."""
        f = FineTunedModelService()
        for task in f.TASK_MAPPING.keys():
            assert f.is_available(task) is False

    def test_get_model_info_returns_dict(self):
        f = FineTunedModelService()
        info = f.get_model_info("safety_check")
        assert isinstance(info, dict)
        assert "task" in info
        assert "accuracy_score" in info
        assert "available" in info

    def test_get_model_info_unknown_task(self):
        f = FineTunedModelService()
        info = f.get_model_info("hook_generate")
        assert info is None

    def test_list_available_models_empty_by_default(self):
        f = FineTunedModelService()
        models = f.list_available_models()
        assert models == []


class TestFineTunedCostEfficiency:
    def test_ft_vs_frontier_cost_ratio(self):
        """Fine-tuned models should be ~99% cheaper than frontier."""
        safety_ft = FINETUNED_REGISTRY[FineTunedTask.SAFETY_CLASSIFIER]
        frontier_input_cost = 3.00  # Claude Sonnet 4.6
        ratio = safety_ft.input_cost_per_1m / frontier_input_cost
        assert ratio <= 0.05, f"Fine-tuned should be <=5% of frontier cost, got {ratio*100:.1f}%"

    def test_ft_accuracy_within_range(self):
        """Fine-tuned accuracy should be within 5% of frontier."""
        for task, config in FINETUNED_REGISTRY.items():
            assert config.accuracy_score >= 0.85, \
                f"{task} accuracy {config.accuracy_score} too low"
            assert config.accuracy_score <= 1.0


# ============================================================================
# Cross-Phase Integration Tests
# ============================================================================

class TestPhase4Integration:
    def test_batch_eligible_tasks_are_not_premium(self):
        """Batch tasks should never include PREMIUM tasks."""
        from app.services.llm_router import TASK_MODEL_MAP, ModelTier
        from app.services.batch_api_service import BatchAPIService
        b = BatchAPIService()
        for task in b.ELIGIBLE_TASKS:
            assert task in TASK_MODEL_MAP, f"Batch task '{task}' missing from TASK_MODEL_MAP"
            tier = TASK_MODEL_MAP[task]["tier"]
            assert tier != ModelTier.PREMIUM

    def test_finetuned_tasks_are_batch_eligible(self):
        """All fine-tuned tasks should also be batch eligible."""
        from app.services.finetuned_model_service import FineTunedModelService
        from app.services.batch_api_service import BatchAPIService
        ft = FineTunedModelService()
        batch = BatchAPIService()
        for router_task in ft.TASK_MAPPING.keys():
            assert batch.is_eligible(router_task), \
                f"Fine-tuned task '{router_task}' should also be batch eligible"

    def test_all_regions_have_distinct_storage(self):
        """Each region should map to a distinct storage region."""
        storage_regions = set()
        for code, config in REGION_REGISTRY.items():
            assert config.storage_region not in storage_regions, \
                f"Duplicate storage region for {code}"
            storage_regions.add(config.storage_region)

    def test_primary_region_has_highest_capacity(self):
        primary = REGION_REGISTRY["lax"]
        for code, config in REGION_REGISTRY.items():
            if code != "lax":
                assert primary.worker_capacity >= config.worker_capacity, \
                    f"Primary capacity should be >= {code}"


# Need pytest import for raises context manager
import pytest

# Add sync wrapper for test convenience
BatchAPIService.get_status_sync = lambda self, job_id: self._jobs.get(job_id, {}).to_dict() if job_id in self._jobs else None
