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
from datetime import datetime

from app.models import (
    SwarmJob, SwarmJobType, SwarmJobStatus,
    SwarmAgentResult, SwarmTier
)
from app.services.swarm_config_service import SwarmConfigService, SwarmJobService
from app.services.swarm_agents import HookSwarmAgent, RemixSwarmAgent, PostSwarmAgent, AgentResult
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
        job.completed_at = datetime.utcnow()
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
        job.completed_at = datetime.utcnow()
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
        job.completed_at = datetime.utcnow()
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
    # Internal: parallel agent execution
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
                result = AgentResult(
                    agent_index=agent.agent_index,
                    persona=getattr(agent, "persona", getattr(agent, "strategy", "unknown")),
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
        return await asyncio.gather(*tasks)

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

        return await asyncio.gather(*tasks)

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
