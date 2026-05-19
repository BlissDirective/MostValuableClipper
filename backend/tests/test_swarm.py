import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app
from app.models import SwarmConfig, SwarmTier, SwarmJob, SwarmJobType, SwarmJobStatus, SwarmAgentResult

client = TestClient(app)


class TestSwarmUnauthorized:
    """Test swarm endpoints reject unauthenticated requests."""

    def test_swarm_hooks_unauthorized(self):
        response = client.post("/api/v1/swarm/hooks", json={
            "clip_id": "test-clip",
            "platform": "tiktok"
        })
        assert response.status_code == 401

    def test_swarm_remix_unauthorized(self):
        response = client.post("/api/v1/swarm/remix", json={
            "clip_id": "test-clip"
        })
        assert response.status_code == 401

    def test_swarm_post_unauthorized(self):
        response = client.post("/api/v1/swarm/post", json={
            "clip_id": "test-clip",
            "accounts": [{"account_id": "acc1", "platform": "tiktok"}]
        })
        assert response.status_code == 401

    def test_swarm_config_get_unauthorized(self):
        response = client.get("/api/v1/swarm/config")
        assert response.status_code == 401

    def test_swarm_config_patch_unauthorized(self):
        response = client.patch("/api/v1/swarm/config", json={
            "daily_budget_cents": 100
        })
        assert response.status_code == 401

    def test_swarm_jobs_list_unauthorized(self):
        response = client.get("/api/v1/swarm/jobs")
        assert response.status_code == 401

    def test_swarm_job_detail_unauthorized(self):
        response = client.get("/api/v1/swarm/jobs/test-job-id")
        assert response.status_code == 401


class TestSwarmConfigService:
    """Test SwarmConfigService tier limits and defaults."""

    def test_tier_limits_constants(self):
        from app.services.swarm_config_service import SwarmConfigService
        assert SwarmConfigService.TIER_LIMITS[SwarmTier.free] == 1
        assert SwarmConfigService.TIER_LIMITS[SwarmTier.basic] == 2
        assert SwarmConfigService.TIER_LIMITS[SwarmTier.pro] == 5
        assert SwarmConfigService.TIER_LIMITS[SwarmTier.enterprise] == 10

    def test_enforce_tier_limits_free(self):
        from app.services.swarm_config_service import SwarmConfigService
        config = SwarmConfig(
            user_id="u1",
            tier=SwarmTier.free,
            max_hook_agents=5,
            max_remix_agents=5,
            max_post_agents=5
        )
        config = SwarmConfigService.enforce_tier_limits(config)
        assert config.max_hook_agents == 1
        assert config.max_remix_agents == 1
        assert config.max_post_agents == 1

    def test_enforce_tier_limits_pro(self):
        from app.services.swarm_config_service import SwarmConfigService
        config = SwarmConfig(
            user_id="u1",
            tier=SwarmTier.pro,
            max_hook_agents=20,
            max_remix_agents=20,
            max_post_agents=20
        )
        config = SwarmConfigService.enforce_tier_limits(config)
        assert config.max_hook_agents == 5
        assert config.max_remix_agents == 5
        assert config.max_post_agents == 5

    def test_get_max_agents_for_tier(self):
        from app.services.swarm_config_service import SwarmConfigService
        assert SwarmConfigService.get_max_agents_for_tier(SwarmTier.free, "hook") == 1
        assert SwarmConfigService.get_max_agents_for_tier(SwarmTier.basic, "remix") == 2
        assert SwarmConfigService.get_max_agents_for_tier(SwarmTier.pro, "post") == 5
        assert SwarmConfigService.get_max_agents_for_tier(SwarmTier.enterprise, "hook") == 10

    def test_estimate_cost(self):
        from app.services.swarm_config_service import SwarmConfigService
        assert SwarmConfigService.estimate_cost("hook", 3) == 15
        assert SwarmConfigService.estimate_cost("remix", 2) == 40
        assert SwarmConfigService.estimate_cost("post", 5) == 5


class TestSwarmAgents:
    """Test individual swarm agents."""

    def test_hook_agent_personas(self):
        from app.services.swarm_agents import HookSwarmAgent
        assert len(HookSwarmAgent.PERSONAS) >= 8
        assert "viral_hunter" in HookSwarmAgent.PERSONAS
        assert "storyteller" in HookSwarmAgent.PERSONAS

    def test_remix_agent_strategies(self):
        from app.services.swarm_agents import RemixSwarmAgent
        assert len(RemixSwarmAgent.STRATEGIES) >= 6
        assert "peak_energy" in RemixSwarmAgent.STRATEGIES
        assert "hook_first" in RemixSwarmAgent.STRATEGIES

    def test_hook_agent_init(self):
        from app.services.swarm_agents import HookSwarmAgent
        agent = HookSwarmAgent(agent_index=0, persona="viral_hunter")
        assert agent.agent_index == 0
        assert agent.persona == "viral_hunter"

    def test_remix_agent_init(self):
        from app.services.swarm_agents import RemixSwarmAgent
        agent = RemixSwarmAgent(agent_index=1, strategy="peak_energy")
        assert agent.agent_index == 1
        assert agent.strategy == "peak_energy"

    def test_post_agent_init(self):
        from app.services.swarm_agents import PostSwarmAgent
        agent = PostSwarmAgent(agent_index=2, account_id="acc1", platform="tiktok")
        assert agent.agent_index == 2
        assert agent.account_id == "acc1"
        assert agent.platform == "tiktok"


class TestSwarmOrchestrator:
    """Test SwarmOrchestrator with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_execute_hook_swarm_budget_exceeded(self):
        from app.services.swarm_orchestrator import SwarmOrchestrator
        orch = SwarmOrchestrator()

        with patch.object(orch.config_service, "get_config", new_callable=AsyncMock) as mock_get, \
             patch.object(orch.config_service, "check_budget", new_callable=AsyncMock) as mock_budget:

            mock_get.return_value = SwarmConfig(
                user_id="u1", tier=SwarmTier.free,
                max_hook_agents=1, enabled_pools=["hook"]
            )
            mock_budget.return_value = False

            result = await orch.execute_hook_swarm("clip1", "u1", "tiktok")
            assert "error" in result
            assert "budget" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_hook_swarm_pool_disabled(self):
        from app.services.swarm_orchestrator import SwarmOrchestrator
        orch = SwarmOrchestrator()

        with patch.object(orch.config_service, "get_config", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SwarmConfig(
                user_id="u1", tier=SwarmTier.free,
                max_hook_agents=1, enabled_pools=["remix", "post"]
            )

            result = await orch.execute_hook_swarm("clip1", "u1", "tiktok")
            assert "error" in result
            assert "disabled" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_remix_swarm_limit_reached(self):
        from app.services.swarm_orchestrator import SwarmOrchestrator
        orch = SwarmOrchestrator()

        with patch.object(orch.config_service, "get_config", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = SwarmConfig(
                user_id="u1", tier=SwarmTier.free,
                max_remix_agents=1, enabled_pools=["remix"]
            )

            result = await orch.execute_remix_swarm("clip1", "u1", agent_count=0)
            assert "error" in result
            assert "limit" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_post_swarm_empty_accounts(self):
        from app.services.swarm_orchestrator import SwarmOrchestrator
        orch = SwarmOrchestrator()

        result = await orch.execute_post_swarm("clip1", "u1", [])
        assert "error" in result

    @pytest.mark.asyncio
    async def test_serialize_result(self):
        from app.services.swarm_orchestrator import SwarmOrchestrator
        from app.services.swarm_agents import AgentResult

        result = AgentResult(
            agent_index=0, persona="test", status="completed",
            data={"key": "val"}, cost_cents=5, duration_ms=100
        )
        serialized = SwarmOrchestrator._serialize_result(result)
        assert serialized["agent_index"] == 0
        assert serialized["persona"] == "test"
        assert serialized["cost_cents"] == 5


class TestSwarmModels:
    """Test Pydantic models for swarm."""

    def test_swarm_config_defaults(self):
        config = SwarmConfig(user_id="u1")
        assert config.tier == SwarmTier.free
        assert config.max_hook_agents == 1
        assert config.enabled_pools == ["hook", "remix", "post"]
        assert config.daily_budget_cents == 0

    def test_swarm_job_defaults(self):
        job = SwarmJob(job_id="j1", user_id="u1", job_type=SwarmJobType.hook)
        assert job.status == SwarmJobStatus.queued
        assert job.total_agents == 0
        assert job.cost_cents == 0

    def test_swarm_agent_result_defaults(self):
        result = SwarmAgentResult(
            result_id="r1", job_id="j1", agent_index=0, agent_persona="test"
        )
        assert result.status == "pending"
        assert result.cost_cents == 0
        assert result.duration_ms == 0

    def test_swarm_tier_enum_values(self):
        assert SwarmTier.free.value == "free"
        assert SwarmTier.basic.value == "basic"
        assert SwarmTier.pro.value == "pro"
        assert SwarmTier.enterprise.value == "enterprise"


class TestSwarmRequestValidation:
    """Test request model validation."""

    def test_hook_request_agent_count_bounds(self):
        from app.api.swarm import SwarmHookRequest
        # Valid
        req = SwarmHookRequest(clip_id="c1", agent_count=5)
        assert req.agent_count == 5
        # agent_count=None is valid
        req = SwarmHookRequest(clip_id="c1")
        assert req.agent_count is None

    def test_remix_request_agent_count_bounds(self):
        from app.api.swarm import SwarmRemixRequest
        req = SwarmRemixRequest(clip_id="c1", agent_count=3)
        assert req.agent_count == 3

    def test_post_request_accounts_required(self):
        from app.api.swarm import SwarmPostRequest
        req = SwarmPostRequest(clip_id="c1", accounts=[
            {"account_id": "a1", "platform": "tiktok"}
        ])
        assert len(req.accounts) == 1
        assert req.accounts[0].account_id == "a1"
        assert req.accounts[0].platform == "tiktok"

    def test_config_update_budget_nonnegative(self):
        from app.api.swarm import SwarmConfigUpdateRequest
        req = SwarmConfigUpdateRequest(daily_budget_cents=0)
        assert req.daily_budget_cents == 0
        req = SwarmConfigUpdateRequest(daily_budget_cents=500)
        assert req.daily_budget_cents == 500


class TestSwarmAPIResponseShapes:
    """Test response model shapes match expected structures."""

    def test_swarm_hook_response_shape(self):
        from app.api.swarm import SwarmHookResponse
        resp = SwarmHookResponse(
            job_id="j1", agents=3, results=[],
            best_hook={"hook_text": "test"},
            total_cost_cents=15, duration_ms=1000
        )
        assert resp.job_id == "j1"
        assert resp.best_hook["hook_text"] == "test"

    def test_swarm_remix_response_shape(self):
        from app.api.swarm import SwarmRemixResponse
        resp = SwarmRemixResponse(
            job_id="j1", agents=2, variants=[],
            best_variant={"video_url": "http://x"},
            total_cost_cents=40, duration_ms=2000
        )
        assert resp.best_variant["video_url"] == "http://x"

    def test_swarm_post_response_shape(self):
        from app.api.swarm import SwarmPostResponse
        resp = SwarmPostResponse(
            job_id="j1", agents=1, posts=[],
            summary={"total": 1, "success": 1, "failed": 0, "platforms": ["tiktok"]},
            total_cost_cents=1, duration_ms=500
        )
        assert resp.summary["success"] == 1

    def test_swarm_config_response_shape(self):
        from app.api.swarm import SwarmConfigResponse
        resp = SwarmConfigResponse(
            user_id="u1", tier="pro",
            max_hook_agents=5, max_remix_agents=5, max_post_agents=5,
            enabled_pools=["hook", "remix"], daily_budget_cents=1000
        )
        assert resp.tier == "pro"
        assert resp.max_hook_agents == 5

    def test_swarm_job_list_response_shape(self):
        from app.api.swarm import SwarmJobListResponse
        resp = SwarmJobListResponse(jobs=[], total=0)
        assert resp.total == 0

    def test_swarm_job_detail_response_shape(self):
        from app.api.swarm import SwarmJobDetailResponse
        job = SwarmJob(job_id="j1", user_id="u1", job_type=SwarmJobType.hook)
        resp = SwarmJobDetailResponse(job=job, agent_results=[])
        assert resp.job.job_id == "j1"


class TestSwarmIntegration:
    """Integration tests for swarm with mocked services."""

    @pytest.mark.asyncio
    async def test_hook_swarm_end_to_end_mocked(self):
        from app.services.swarm_orchestrator import SwarmOrchestrator
        from app.services.swarm_agents import AgentResult

        orch = SwarmOrchestrator()

        mock_result = AgentResult(
            agent_index=0, persona="viral_hunter", status="completed",
            data={
                "hook_text": "This is wild",
                "estimated_retention": 0.92,
                "clip_id": "clip1",
                "platform": "tiktok"
            },
            cost_cents=10, duration_ms=500
        )

        with patch.object(orch.config_service, "get_config", new_callable=AsyncMock) as mock_get, \
             patch.object(orch.config_service, "check_budget", new_callable=AsyncMock) as mock_budget, \
             patch.object(orch, "_run_agents", new_callable=AsyncMock) as mock_run, \
             patch.object(orch.job_service, "create_job", new_callable=AsyncMock), \
             patch.object(orch.job_service, "update_job", new_callable=AsyncMock), \
             patch.object(orch.job_service, "save_agent_result", new_callable=AsyncMock), \
             patch.object(orch.queue, "enqueue", new_callable=AsyncMock), \
             patch.object(orch.queue, "mark_job_complete", new_callable=AsyncMock):

            mock_get.return_value = SwarmConfig(
                user_id="u1", tier=SwarmTier.pro,
                max_hook_agents=5, enabled_pools=["hook"]
            )
            mock_budget.return_value = True
            mock_run.return_value = [mock_result]

            result = await orch.execute_hook_swarm("clip1", "u1", "tiktok", agent_count=1)

            assert result["job_id"] is not None
            assert result["agents"] == 1
            assert result["best_hook"]["hook_text"] == "This is wild"
            assert result["total_cost_cents"] == 10

    @pytest.mark.asyncio
    async def test_post_swarm_partial_failure(self):
        from app.services.swarm_orchestrator import SwarmOrchestrator
        from app.services.swarm_agents import AgentResult

        orch = SwarmOrchestrator()

        results = [
            AgentResult(
                agent_index=0, persona="tiktok:acc1", status="completed",
                data={"post_id": "p1"}, cost_cents=1, duration_ms=300
            ),
            AgentResult(
                agent_index=1, persona="instagram:acc2", status="failed",
                data={}, cost_cents=1, duration_ms=100, error="Rate limited"
            ),
        ]

        with patch.object(orch.config_service, "get_config", new_callable=AsyncMock) as mock_get, \
             patch.object(orch.config_service, "check_budget", new_callable=AsyncMock) as mock_budget, \
             patch.object(orch, "_run_post_agents", new_callable=AsyncMock) as mock_run, \
             patch.object(orch.job_service, "create_job", new_callable=AsyncMock), \
             patch.object(orch.job_service, "update_job", new_callable=AsyncMock), \
             patch.object(orch.job_service, "save_agent_result", new_callable=AsyncMock), \
             patch.object(orch.queue, "enqueue", new_callable=AsyncMock), \
             patch.object(orch.queue, "mark_job_complete", new_callable=AsyncMock):

            mock_get.return_value = SwarmConfig(
                user_id="u1", tier=SwarmTier.pro,
                max_post_agents=5, enabled_pools=["post"]
            )
            mock_budget.return_value = True
            mock_run.return_value = results

            result = await orch.execute_post_swarm(
                "clip1", "u1",
                [{"account_id": "acc1", "platform": "tiktok"},
                 {"account_id": "acc2", "platform": "instagram"}]
            )

            assert result["job_id"] is not None
            assert result["summary"]["success"] == 1
            assert result["summary"]["failed"] == 1
            assert len(result["posts"]) == 2

    @pytest.mark.asyncio
    async def test_remix_swarm_best_variant_selection(self):
        from app.services.swarm_orchestrator import SwarmOrchestrator
        from app.services.swarm_agents import AgentResult

        orch = SwarmOrchestrator()

        results = [
            AgentResult(
                agent_index=0, persona="peak_energy", status="completed",
                data={"estimated_retention": 0.75, "variant_id": "v1"},
                cost_cents=20, duration_ms=2000
            ),
            AgentResult(
                agent_index=1, persona="hook_first", status="completed",
                data={"estimated_retention": 0.91, "variant_id": "v2"},
                cost_cents=20, duration_ms=1800
            ),
        ]

        with patch.object(orch.config_service, "get_config", new_callable=AsyncMock) as mock_get, \
             patch.object(orch.config_service, "check_budget", new_callable=AsyncMock) as mock_budget, \
             patch.object(orch, "_run_agents", new_callable=AsyncMock) as mock_run, \
             patch.object(orch.job_service, "create_job", new_callable=AsyncMock), \
             patch.object(orch.job_service, "update_job", new_callable=AsyncMock), \
             patch.object(orch.job_service, "save_agent_result", new_callable=AsyncMock), \
             patch.object(orch.queue, "enqueue", new_callable=AsyncMock), \
             patch.object(orch.queue, "mark_job_complete", new_callable=AsyncMock):

            mock_get.return_value = SwarmConfig(
                user_id="u1", tier=SwarmTier.pro,
                max_remix_agents=5, enabled_pools=["remix"]
            )
            mock_budget.return_value = True
            mock_run.return_value = results

            result = await orch.execute_remix_swarm("clip1", "u1", agent_count=2)

            assert result["best_variant"]["variant_id"] == "v2"
            assert result["best_variant"]["estimated_retention"] == 0.91

    @pytest.mark.asyncio
    async def test_remix_swarm_all_failed(self):
        from app.services.swarm_orchestrator import SwarmOrchestrator
        from app.services.swarm_agents import AgentResult

        orch = SwarmOrchestrator()

        results = [
            AgentResult(
                agent_index=0, persona="peak_energy", status="failed",
                data={}, cost_cents=10, duration_ms=500, error="FFmpeg error"
            ),
        ]

        with patch.object(orch.config_service, "get_config", new_callable=AsyncMock) as mock_get, \
             patch.object(orch.config_service, "check_budget", new_callable=AsyncMock) as mock_budget, \
             patch.object(orch, "_run_agents", new_callable=AsyncMock) as mock_run, \
             patch.object(orch.job_service, "create_job", new_callable=AsyncMock), \
             patch.object(orch.job_service, "update_job", new_callable=AsyncMock), \
             patch.object(orch.job_service, "save_agent_result", new_callable=AsyncMock), \
             patch.object(orch.queue, "enqueue", new_callable=AsyncMock), \
             patch.object(orch.queue, "mark_job_complete", new_callable=AsyncMock):

            mock_get.return_value = SwarmConfig(
                user_id="u1", tier=SwarmTier.basic,
                max_remix_agents=2, enabled_pools=["remix"]
            )
            mock_budget.return_value = True
            mock_run.return_value = results

            result = await orch.execute_remix_swarm("clip1", "u1", agent_count=1)

            assert result["job_id"] is not None
            assert result["best_variant"] is None
            assert result["variants"][0]["status"] == "failed"


class TestSwarmEndpointValidation:
    """Test endpoint-level input validation."""

    def test_swarm_hooks_invalid_platform(self):
        from app.api.swarm import SwarmHookRequest
        # Platform is a plain string in the model — no enum restriction
        req = SwarmHookRequest(clip_id="c1", platform="notaplatform")
        assert req.platform == "notaplatform"

    def test_swarm_post_missing_account_id(self):
        from pydantic import ValidationError
        from app.api.swarm import SwarmPostAccount
        with pytest.raises(ValidationError):
            SwarmPostAccount(platform="tiktok")

    def test_swarm_post_missing_platform(self):
        from pydantic import ValidationError
        from app.api.swarm import SwarmPostAccount
        with pytest.raises(ValidationError):
            SwarmPostAccount(account_id="a1")
