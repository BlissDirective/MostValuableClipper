"""
Comprehensive test suite for LLM Router and TASK_MODEL_MAP.
Tests routing logic, model selection, caching, fallback, and cost tracking.
Run with: pytest backend/app/tests/test_llm_router.py -v
"""
import pytest
import os
import sys
import asyncio

# Ensure app is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.services.llm_router import (
    LLMRouter, ModelTier, SemanticCache, MODEL_REGISTRY, TASK_MODEL_MAP,
    get_router
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def router():
    """Fresh router instance with no cache."""
    return LLMRouter(redis_client=None, cache_ttl=60)


@pytest.fixture
def router_with_keys(monkeypatch):
    """Router with all provider API keys set."""
    keys = {
        "ANTHROPIC_API_KEY": "sk-ant-test",
        "OPENAI_API_KEY": "sk-test",
        "GROQ_API_KEY": "gsk-test",
        "DEEPSEEK_API_KEY": "sk-ds-test",
        "GEMINI_API_KEY": "gem-test",
    }
    for k, v in keys.items():
        monkeypatch.setenv(k, v)
    return LLMRouter(redis_client=None, cache_ttl=60)


# ============================================================================
# Model Registry Tests
# ============================================================================

class TestModelRegistry:
    def test_all_models_have_required_fields(self):
        required = ["provider", "model_id", "litellm_name", "input_cost_per_1m",
                    "output_cost_per_1m", "env_key"]
        for name, cfg in MODEL_REGISTRY.items():
            for field in required:
                assert getattr(cfg, field, None) is not None, f"{name} missing {field}"

    def test_no_duplicate_model_ids(self):
        ids = [cfg.model_id for cfg in MODEL_REGISTRY.values()]
        assert len(ids) == len(set(ids)), "Duplicate model_ids found"

    def test_costs_are_positive(self):
        for name, cfg in MODEL_REGISTRY.items():
            assert cfg.input_cost_per_1m > 0, f"{name} has invalid input cost"
            assert cfg.output_cost_per_1m > 0, f"{name} has invalid output cost"

    def test_provider_is_valid(self):
        valid = {"anthropic", "openai", "google", "groq", "deepseek"}
        for name, cfg in MODEL_REGISTRY.items():
            assert cfg.provider in valid, f"{name} has invalid provider: {cfg.provider}"

    def test_context_window_is_reasonable(self):
        for name, cfg in MODEL_REGISTRY.items():
            assert 1000 <= cfg.context_window <= 2_000_000, f"{name} context window suspicious: {cfg.context_window}"

    def test_quality_scores_in_range(self):
        for name, cfg in MODEL_REGISTRY.items():
            assert 0.0 <= cfg.quality_score <= 1.0, f"{name} quality score out of range: {cfg.quality_score}"


# ============================================================================
# TASK_MODEL_MAP Tests
# ============================================================================

class TestTaskModelMap:
    def test_all_tasks_have_required_keys(self):
        required = ["tier", "models", "rationale", "cost_reduction_vs_baseline"]
        for task_name, config in TASK_MODEL_MAP.items():
            for key in required:
                assert key in config, f"Task '{task_name}' missing key '{key}'"

    def test_all_tiers_are_valid(self):
        valid_tiers = {ModelTier.PREMIUM, ModelTier.STANDARD, ModelTier.ECONOMY}
        for task_name, config in TASK_MODEL_MAP.items():
            assert config["tier"] in valid_tiers, f"Task '{task_name}' has invalid tier: {config['tier']}"

    def test_all_models_exist_in_registry(self):
        for task_name, config in TASK_MODEL_MAP.items():
            for model_id in config["models"]:
                assert model_id in MODEL_REGISTRY, f"Task '{task_name}' references unknown model '{model_id}'"

    def test_cost_reduction_in_valid_range(self):
        for task_name, config in TASK_MODEL_MAP.items():
            reduction = config["cost_reduction_vs_baseline"]
            assert 0.0 <= reduction <= 1.0, f"Task '{task_name}' has invalid reduction: {reduction}"

    def test_premium_tasks_have_zero_reduction(self):
        for task_name, config in TASK_MODEL_MAP.items():
            if config["tier"] == ModelTier.PREMIUM:
                assert config["cost_reduction_vs_baseline"] == 0, \
                    f"PREMIUM task '{task_name}' should have 0% reduction"

    def test_each_task_has_fallback_models(self):
        for task_name, config in TASK_MODEL_MAP.items():
            assert len(config["models"]) >= 2, f"Task '{task_name}' should have at least 2 fallback models"

    def test_rationale_is_non_empty(self):
        for task_name, config in TASK_MODEL_MAP.items():
            assert len(config["rationale"]) > 10, f"Task '{task_name}' has empty rationale"


# ============================================================================
# Model Selection (Routing Logic) Tests
# ============================================================================

class TestModelSelection:
    def test_unknown_task_falls_back(self, router):
        """Unknown task types fall back to the default model."""
        model = router.select_model("totally_unknown_task")
        assert model.model_id == MODEL_REGISTRY[router.fallback].model_id

    def test_force_model_override(self, router_with_keys):
        """force_model bypasses tier mapping."""
        model = router_with_keys.select_model("hook_generate", force_model="gpt-4.1-nano")
        assert model.model_id == "gpt-4.1-nano"

    def test_force_tier_override(self, router_with_keys):
        """force_tier changes the selection tier."""
        model = router_with_keys.select_model("safety_check", force_tier=ModelTier.PREMIUM)
        # All PREMIUM models: claude-sonnet-4.6, claude-opus-4.7, gpt-5.4, gemini-3.1-pro
        premium_ids = {m.model_id for m in MODEL_REGISTRY.values() if m.quality_score >= 0.90}
        assert model.model_id in premium_ids

    def test_prefer_speed_sorts_by_tps(self, router_with_keys):
        """prefer_speed=True sorts by tokens per second."""
        model = router_with_keys.select_model("hook_generate", prefer_speed=True)
        # Among premium models, GPT-5.4 is fastest at 80 TPS
        assert model.speed_tps >= 80

    def test_premium_tasks_select_premium_models(self, router_with_keys):
        """Hook generation should select a PREMIUM tier model."""
        model = router_with_keys.select_model("hook_generate")
        assert model.model_id in TASK_MODEL_MAP["hook_generate"]["models"]
        assert TASK_MODEL_MAP["hook_generate"]["tier"] == ModelTier.PREMIUM

    def test_economy_tasks_select_cheapest(self, router_with_keys):
        """Safety check should select the cheapest economy model."""
        model = router_with_keys.select_model("safety_check")
        # Verify the model_id exists in registry values and is economy-class
        all_model_ids = {cfg.model_id for cfg in MODEL_REGISTRY.values()}
        assert model.model_id in all_model_ids
        assert model.quality_score < 0.75, f"Expected economy quality (<0.75), got {model.quality_score}"
        assert TASK_MODEL_MAP["safety_check"]["tier"] == ModelTier.ECONOMY

    def test_standard_tasks_select_standard(self, router_with_keys):
        """Caption generation should select a STANDARD model."""
        model = router_with_keys.select_model("caption_generate")
        assert model.model_id in TASK_MODEL_MAP["caption_generate"]["models"]
        assert TASK_MODEL_MAP["caption_generate"]["tier"] == ModelTier.STANDARD

    def test_no_api_key_filters_out_model(self, router, monkeypatch):
        """Models without API keys configured should be skipped."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
        model = router.select_model("hook_generate")
        # Only Anthropic models should be available
        assert model.provider == "anthropic"

    def test_all_keys_unavailable_falls_back(self, router):
        """When no keys are set at all, should fall back."""
        model = router.select_model("safety_check")
        assert model.model_id == MODEL_REGISTRY[router.fallback].model_id


# ============================================================================
# Semantic Cache Tests
# ============================================================================

class TestSemanticCache:
    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        cache = SemanticCache(redis_client=None, ttl_seconds=60)
        result = await cache.get("test_task", "test prompt", "gpt-4.1-nano")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit_returns_value(self):
        cache = SemanticCache(redis_client=None, ttl_seconds=60)
        await cache.set("test_task", "test prompt", "gpt-4.1-nano", "cached response")
        result = await cache.get("test_task", "test prompt", "gpt-4.1-nano")
        assert result == "cached response"

    @pytest.mark.asyncio
    async def test_different_tasks_dont_share_cache(self):
        cache = SemanticCache(redis_client=None, ttl_seconds=60)
        await cache.set("task_a", "same prompt", "gpt-4.1-nano", "response A")
        result = await cache.get("task_b", "same prompt", "gpt-4.1-nano")
        assert result is None

    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self):
        cache = SemanticCache(redis_client=None, ttl_seconds=60)
        await cache.set("task", "prompt1", "model", "response1")
        await cache.get("task", "prompt1", "model")  # hit
        await cache.get("task", "prompt2", "model")  # miss
        assert cache.hit_rate == 0.5


# ============================================================================
# Cost Estimation Tests
# ============================================================================

class TestCostEstimation:
    def test_claude_sonnet_cost_estimate(self):
        cfg = MODEL_REGISTRY["claude-sonnet-4.6"]
        cost = cfg.estimate_cost_usd(input_tokens=2000, output_tokens=400)
        expected = (2000 / 1e6 * 3.00) + (400 / 1e6 * 15.00)
        assert abs(cost - expected) < 0.0001

    def test_gpt_4_1_nano_cost_estimate(self):
        cfg = MODEL_REGISTRY["gpt-4.1-nano"]
        cost = cfg.estimate_cost_usd(input_tokens=500, output_tokens=200)
        expected = (500 / 1e6 * 0.10) + (200 / 1e6 * 0.40)
        assert abs(cost - expected) < 0.0001

    def test_cost_reduction_calculation(self):
        """Verify that economy tier savings are calculated correctly."""
        baseline_input_1m = 3.00  # Claude Sonnet 4.6
        nano_input_1m = 0.10      # GPT-4.1 Nano
        reduction = 1 - (nano_input_1m / baseline_input_1m)
        assert abs(reduction - 0.9667) < 0.01

    def test_economy_vs_premium_cost_ratio(self):
        """Economy model should be ~60x cheaper than premium on input."""
        premium = MODEL_REGISTRY["claude-opus-4.7"]
        economy = MODEL_REGISTRY["groq-llama-8b"]
        ratio = premium.input_cost_per_1m / economy.input_cost_per_1m
        assert ratio >= 50, f"Expected economy to be ~100x cheaper, got {ratio}x"


# ============================================================================
# Router Integration Tests
# ============================================================================

class TestRouterIntegration:
    def test_get_router_singleton(self):
        r1 = get_router()
        r2 = get_router()
        assert r1 is r2

    def test_stats_initially_empty(self, router):
        stats = router.get_stats()
        assert stats["total_cost"] == 0.0
        assert stats["cache_stats"]["hits"] == 0

    def test_recommendations_has_all_tasks(self, router):
        recs = router.get_model_recommendations()
        task_names = [r["task"] for r in recs]
        assert len(task_names) == len(TASK_MODEL_MAP)
        for task in TASK_MODEL_MAP:
            assert task in task_names, f"Missing recommendation for task: {task}"

    def test_recommendations_cost_reduction_format(self, router):
        recs = router.get_model_recommendations()
        for r in recs:
            assert "%" in r["cost_reduction_vs_claude_sonnet"]
            assert r["est_cost_per_call_usd"] > 0

    def test_print_routing_table_runs(self, router, capsys):
        router.print_routing_table()
        captured = capsys.readouterr()
        assert "MVC Agent Task" in captured.out
        assert "Tier" in captured.out


# ============================================================================
# Tier Classification Tests
# ============================================================================

class TestTierClassification:
    def test_exactly_two_premium_tasks(self):
        premium = [t for t, c in TASK_MODEL_MAP.items() if c["tier"] == ModelTier.PREMIUM]
        assert len(premium) == 2, f"Expected 2 PREMIUM tasks, got {len(premium)}: {premium}"

    def test_premium_tasks_are_hooks_and_edit(self):
        premium = {t for t, c in TASK_MODEL_MAP.items() if c["tier"] == ModelTier.PREMIUM}
        assert premium == {"hook_generate", "edit_instructions"}, f"Unexpected PREMIUM tasks: {premium}"

    def test_economy_tasks_count(self):
        economy = [t for t, c in TASK_MODEL_MAP.items() if c["tier"] == ModelTier.ECONOMY]
        assert len(economy) >= 5, f"Expected at least 5 ECONOMY tasks, got {len(economy)}"

    def test_all_tasks_covered(self):
        """Every task must have a tier and at least one model."""
        for task, config in TASK_MODEL_MAP.items():
            assert config["tier"] in [ModelTier.PREMIUM, ModelTier.STANDARD, ModelTier.ECONOMY]
            assert len(config["models"]) >= 1


# ============================================================================
# Run all tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
