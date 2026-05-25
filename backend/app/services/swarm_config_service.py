"""Swarm configuration service with customizable agent allocation.

Manages user swarm configs, enforces tier limits, supports custom
agent allocation across pool types, and tracks costs per pool type.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from app.models import SwarmConfig, SwarmTier, SwarmJob, SwarmAgentResult
from app.services.database import supabase

logger = logging.getLogger(__name__)


class SwarmConfigService:
    """Manage swarm configurations with customizable agent allocation."""

    # Tier → total max agents across all pools
    TIER_LIMITS = {
        SwarmTier.free: 1,
        SwarmTier.basic: 2,
        SwarmTier.pro: 5,
        SwarmTier.enterprise: 10,
    }

    # Default costs per agent execution (cents)
    DEFAULT_COSTS = {
        "hook": 5,           # ~$0.05 per Claude call
        "remix": 20,         # ~$0.20 per variant (FFmpeg + storage)
        "post": 1,           # ~$0.01 per API call
        "ab_test": 3,        # ~$0.03 per variant comparison
        "music_match": 2,    # ~$0.02 per track match
        "thumbnail": 1,      # ~$0.01 per thumbnail generation
        "safety": 1,         # ~$0.01 per safety check
        "hooks_analysis": 8, # ~$0.08 per analysis batch
        "segment_analyze": 5, # ~$0.05 per segment strategy
        "edit": 15,          # ~$0.15 per edit recipe
    }

    @staticmethod
    async def get_config(user_id: str) -> Optional[SwarmConfig]:
        """Get swarm config for a user. Creates default if none exists."""
        try:
            result = supabase.table("swarm_configs").select("*").eq("user_id", user_id).single().execute()
            if result.data:
                return SwarmConfig(**result.data)
        except Exception as e:
            logger.debug(f"[SwarmConfig] No config found for {user_id}: {e}")

        # Create default config
        return await SwarmConfigService.create_default_config(user_id)

    @staticmethod
    async def create_default_config(user_id: str, tier: SwarmTier = SwarmTier.free) -> SwarmConfig:
        """Create a default swarm config for a user.
        
        Uses auto-balance mode by default, distributing agents evenly
        across all enabled pools.
        """
        total_agents = SwarmConfigService.TIER_LIMITS.get(tier, 1)

        config = SwarmConfig(
            user_id=user_id,
            tier=tier,
            total_max_agents=total_agents,
            auto_balance=True,
            enabled_pools=[
                "hook", "remix", "post", "ab_test", "music_match",
                "thumbnail", "safety", "hooks_analysis", "segment_analyze", "edit"
            ],
            daily_budget_cents=0,
        )
        
        # Auto-balance the allocation
        config.auto_balance_allocation()

        try:
            supabase.table("swarm_configs").upsert(config.model_dump(mode="json")).execute()
        except Exception as e:
            logger.warning(f"[SwarmConfig] Failed to persist config: {e}")

        return config

    @staticmethod
    async def update_config(user_id: str, updates: Dict[str, Any]) -> SwarmConfig:
        """Update swarm config (enforces tier limits on allocation).
        
        Supported updates:
        - enabled_pools: List[str]
        - daily_budget_cents: int
        - tier: SwarmTier
        - auto_balance: bool
        - agent_behavior: Dict[str, Any]
        """
        config = await SwarmConfigService.get_config(user_id)
        if not config:
            config = await SwarmConfigService.create_default_config(user_id)

        # Apply allowed updates
        if "enabled_pools" in updates:
            config.enabled_pools = updates["enabled_pools"]
        if "daily_budget_cents" in updates:
            config.daily_budget_cents = max(0, int(updates["daily_budget_cents"]))
        if "tier" in updates:
            new_tier = SwarmTier(updates["tier"])
            config.tier = new_tier
            config.total_max_agents = SwarmConfigService.TIER_LIMITS.get(new_tier, 1)
            # Re-balance when tier changes
            if config.auto_balance:
                config.auto_balance_allocation()
        if "auto_balance" in updates:
            config.auto_balance = bool(updates["auto_balance"])
            if config.auto_balance:
                config.auto_balance_allocation()
        if "agent_behavior" in updates:
            config.agent_behavior.update(updates["agent_behavior"])

        # Handle custom allocation updates
        if "agent_allocation" in updates:
            new_allocation = dict(updates["agent_allocation"])
            # Validate and sanitize
            for pool in list(new_allocation.keys()):
                if pool not in config.enabled_pools:
                    del new_allocation[pool]
            
            config.agent_allocation = new_allocation
            config.auto_balance = False  # Custom allocation disables auto-balance

        # Validate the final config
        is_valid, error = config.validate_allocation()
        if not is_valid:
            # Reset to auto-balanced if invalid
            config.auto_balance = True
            config.auto_balance_allocation()
            logger.warning(f"[SwarmConfig] Invalid allocation, reset to auto: {error}")

        config.updated_at = datetime.now(timezone.utc)

        try:
            supabase.table("swarm_configs").upsert(config.model_dump(mode="json")).execute()
        except Exception as e:
            logger.warning(f"[SwarmConfig] Failed to update config: {e}")

        return config

    @staticmethod
    async def update_allocation(user_id: str, allocation: Dict[str, int]) -> tuple[SwarmConfig, str]:
        """Update custom agent allocation for a user.
        
        Args:
            user_id: User ID
            allocation: Dict mapping pool type to agent count
            
        Returns:
            (updated_config, message)
        """
        config = await SwarmConfigService.get_config(user_id)
        if not config:
            config = await SwarmConfigService.create_default_config(user_id)

        # Sanitize allocation
        sanitized = {}
        for pool, count in allocation.items():
            if pool not in config.enabled_pools:
                continue
            sanitized[pool] = max(0, int(count))

        # Check total
        total = sum(sanitized.values())
        if total > config.total_max_agents:
            return config, f"Total allocation ({total}) exceeds tier limit ({config.total_max_agents})"
        
        if total == 0:
            return config, "Must allocate at least 1 agent"

        config.agent_allocation = sanitized
        config.auto_balance = False
        config.updated_at = datetime.now(timezone.utc)

        try:
            supabase.table("swarm_configs").upsert(config.model_dump(mode="json")).execute()
        except Exception as e:
            logger.warning(f"[SwarmConfig] Failed to update allocation: {e}")

        return config, "Allocation updated"

    @staticmethod
    def enforce_tier_limits(config: SwarmConfig) -> SwarmConfig:
        """Ensure total allocation does not exceed tier limit."""
        limit = SwarmConfigService.TIER_LIMITS.get(config.tier, 1)
        config.total_max_agents = limit
        
        # If over limit, auto-balance
        if config.allocated_total > limit:
            config.auto_balance = True
            config.auto_balance_allocation()
        
        return config

    @staticmethod
    def get_max_agents_for_tier(tier: SwarmTier) -> int:
        """Get total max agents allowed for a tier."""
        return SwarmConfigService.TIER_LIMITS.get(tier, 1)

    @staticmethod
    def get_pool_costs(config: SwarmConfig) -> Dict[str, int]:
        """Get estimated costs per pool type based on current allocation."""
        costs = {}
        for pool, count in config.agent_allocation.items():
            per_agent = SwarmConfigService.DEFAULT_COSTS.get(pool, 5)
            costs[pool] = per_agent * count
        return costs

    @staticmethod
    async def check_budget(user_id: str, pool_type: str, agent_count: int) -> bool:
        """Check if user has sufficient daily budget for a pool execution."""
        config = await SwarmConfigService.get_config(user_id)
        if not config or config.daily_budget_cents == 0:
            return True  # Unlimited budget

        estimated_cost = SwarmConfigService.DEFAULT_COSTS.get(pool_type, 5) * agent_count

        # Get today's spend
        try:
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            result = supabase.table("swarm_jobs").select("cost_cents") \
                .eq("user_id", user_id) \
                .gte("created_at", today_start) \
                .execute()

            spent = sum(j.get("cost_cents", 0) for j in (result.data or []))
            return (spent + estimated_cost) <= config.daily_budget_cents
        except Exception as e:
            logger.warning(f"[SwarmConfig] Budget check failed: {e}")
            return True  # Fail open

    @staticmethod
    def estimate_cost(pool_type: str, agent_count: int) -> int:
        """Estimate cost in cents for a swarm execution."""
        per_agent = SwarmConfigService.DEFAULT_COSTS.get(pool_type, 5)
        return per_agent * agent_count

    @staticmethod
    async def audit_budget_post_execution(user_id: str, actual_cost_cents: int) -> None:
        """Re-verify budget after execution and warn when the daily cap is breached (M-07).

        The pre-execution check uses estimated cost; concurrent jobs can slip past
        the guard together.  This post-execution audit detects the overrun and logs
        a warning so ops can investigate and adjust tier limits.
        """
        try:
            config = await SwarmConfigService.get_config(user_id)
            if not config or config.daily_budget_cents == 0:
                return  # Unlimited budget — nothing to audit

            today_start = (
                datetime.now(timezone.utc)
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .isoformat()
            )
            result = (
                supabase.table("swarm_jobs")
                .select("cost_cents")
                .eq("user_id", user_id)
                .gte("created_at", today_start)
                .execute()
            )
            total_spent = sum(j.get("cost_cents", 0) for j in (result.data or []))

            if total_spent > config.daily_budget_cents:
                overage = total_spent - config.daily_budget_cents
                logger.warning(
                    "[SwarmConfig] Daily budget breached for user %s: "
                    "spent=%d limit=%d overage=%d (cents)",
                    user_id,
                    total_spent,
                    config.daily_budget_cents,
                    overage,
                )
        except Exception as exc:
            logger.debug("[SwarmConfig] Post-execution budget audit failed: %s", exc)


class SwarmJobService:
    """Persist and retrieve swarm jobs and agent results."""

    @staticmethod
    async def create_job(job: SwarmJob) -> SwarmJob:
        """Persist a swarm job."""
        try:
            supabase.table("swarm_jobs").insert(job.model_dump(mode="json")).execute()
        except Exception as e:
            logger.warning(f"[SwarmJob] Failed to create job: {e}")
        return job

    @staticmethod
    async def update_job(job: SwarmJob) -> SwarmJob:
        """Update a swarm job."""
        try:
            supabase.table("swarm_jobs").update(job.model_dump(mode="json")).eq("job_id", job.job_id).execute()
        except Exception as e:
            logger.warning(f"[SwarmJob] Failed to update job: {e}")
        return job

    @staticmethod
    async def get_job(job_id: str) -> Optional[SwarmJob]:
        """Get a swarm job by ID."""
        try:
            result = supabase.table("swarm_jobs").select("*").eq("job_id", job_id).single().execute()
            if result.data:
                return SwarmJob(**result.data)
        except Exception as e:
            logger.debug(f"[SwarmJob] Job not found: {e}")
        return None

    @staticmethod
    async def list_jobs(user_id: str, limit: int = 50, offset: int = 0) -> List[SwarmJob]:
        """List swarm jobs for a user."""
        try:
            result = supabase.table("swarm_jobs").select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(limit).offset(offset).execute()
            return [SwarmJob(**j) for j in (result.data or [])]
        except Exception as e:
            logger.warning(f"[SwarmJob] Failed to list jobs: {e}")
            return []

    @staticmethod
    async def save_agent_result(result: SwarmAgentResult) -> SwarmAgentResult:
        """Persist an agent result."""
        try:
            supabase.table("swarm_agent_results").insert(result.model_dump(mode="json")).execute()
        except Exception as e:
            logger.warning(f"[SwarmJob] Failed to save agent result: {e}")
        return result

    @staticmethod
    async def get_agent_results(job_id: str) -> List[SwarmAgentResult]:
        """Get all agent results for a job."""
        try:
            result = supabase.table("swarm_agent_results").select("*") \
                .eq("job_id", job_id) \
                .order("agent_index", asc=True).execute()
            return [SwarmAgentResult(**r) for r in (result.data or [])]
        except Exception as e:
            logger.warning(f"[SwarmJob] Failed to get agent results: {e}")
            return []
