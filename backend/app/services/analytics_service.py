"""
Analytics Service — Pipeline Metrics, Cost Tracking & Usage Aggregation

Replaces in-memory analytics with persistent, aggregated metrics.
Tracks per-clip costs, per-model usage, pipeline stage latency,
and user-level usage for quota enforcement.

Designed for the scaling plan's Phase 3: Analytics Pipeline.
All data is stored in Supabase PostgreSQL for immediate use,
migratable to TimescaleDB for time-series optimization.
"""
from __future__ import annotations

import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Metric Event — emitted by pipeline stages and agents
# ---------------------------------------------------------------------------

@dataclass
class MetricEvent:
    """A single metric event to be recorded."""
    event_type: str                    # "pipeline_stage", "llm_call", "agent_exec"
    clip_id: Optional[str] = None
    user_id: Optional[str] = None
    pipeline_id: Optional[str] = None
    stage: Optional[str] = None        # PipelineStage value
    task_type: Optional[str] = None    # LLMRouter task_type
    model_used: Optional[str] = None
    cost_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: int = 0
    status: str = "success"            # success | failed | cached
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "event_type": self.event_type,
            "clip_id": self.clip_id,
            "user_id": self.user_id,
            "pipeline_id": self.pipeline_id,
            "stage": self.stage,
            "task_type": self.task_type,
            "model_used": self.model_used,
            "cost_usd": self.cost_usd,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "cached": self.cached,
            "metadata_json": json.dumps(self.metadata),
            "timestamp": self.timestamp.isoformat(),
        }
        return {k: v for k, v in data.items() if v is not None}


# ---------------------------------------------------------------------------
# Analytics Service
# ---------------------------------------------------------------------------

class AnalyticsService:
    """Collect, aggregate, and query pipeline analytics.

    Usage:
        svc = AnalyticsService()
        await svc.record_event(MetricEvent(
            event_type="llm_call",
            clip_id="abc", task_type="hook_generate",
            model_used="claude-sonnet-4.6", cost_usd=0.005
        ))
        daily = await svc.get_daily_costs(user_id="xyz")
    """

    TABLE_METRICS = "pipeline_metrics"
    TABLE_DAILY_AGG = "daily_usage_aggregates"

    def __init__(self, db_client=None):
        self._db = db_client
        self._buffer: List[MetricEvent] = []
        self._buffer_size = 50
        self._local_cache: Dict[str, Any] = {}

    def _get_db(self):
        """Lazy-load database client."""
        if self._db is None:
            try:
                from app.services.database import supabase
                self._db = supabase
            except Exception as e:
                logger.warning(f"[Analytics] DB unavailable: {e}")
        return self._db

    # ------------------------------------------------------------------
    # Event Recording
    # ------------------------------------------------------------------

    async def record_event(self, event: MetricEvent) -> None:
        """Record a single metric event. Batches writes for efficiency."""
        self._buffer.append(event)
        if len(self._buffer) >= self._buffer_size:
            await self._flush_buffer()

    async def record_llm_call(self, clip_id: str, user_id: str, task_type: str,
                              model_used: str, cost_usd: float, tokens_in: int,
                              tokens_out: int, duration_ms: int, cached: bool = False) -> None:
        """Convenience method for recording LLM call metrics."""
        await self.record_event(MetricEvent(
            event_type="llm_call", clip_id=clip_id, user_id=user_id,
            task_type=task_type, model_used=model_used, cost_usd=cost_usd,
            tokens_in=tokens_in, tokens_out=tokens_out,
            duration_ms=duration_ms, cached=cached,
        ))

    async def record_pipeline_stage(self, clip_id: str, user_id: str,
                                    pipeline_id: str, stage: str,
                                    duration_ms: int, cost_usd: float = 0.0,
                                    status: str = "success") -> None:
        """Convenience method for recording pipeline stage completion."""
        await self.record_event(MetricEvent(
            event_type="pipeline_stage", clip_id=clip_id, user_id=user_id,
            pipeline_id=pipeline_id, stage=stage, duration_ms=duration_ms,
            cost_usd=cost_usd, status=status,
        ))

    async def record_agent_execution(self, clip_id: str, user_id: str,
                                     task_type: str, model_used: str,
                                     cost_usd: float, duration_ms: int,
                                     status: str = "success") -> None:
        """Convenience method for recording swarm agent execution."""
        await self.record_event(MetricEvent(
            event_type="agent_exec", clip_id=clip_id, user_id=user_id,
            task_type=task_type, model_used=model_used,
            cost_usd=cost_usd, duration_ms=duration_ms, status=status,
        ))

    async def _flush_buffer(self) -> None:
        """Write buffered events to database."""
        if not self._buffer:
            return

        events = self._buffer[:]
        self._buffer = []

        db = self._get_db()
        if not db:
            logger.debug(f"[Analytics] Buffering {len(events)} events (no DB)")
            return

        try:
            rows = [e.to_dict() for e in events]
            db.table(self.TABLE_METRICS).insert(rows).execute()
            logger.debug(f"[Analytics] Flushed {len(events)} events")
        except Exception as e:
            logger.error(f"[Analytics] Failed to flush {len(events)} events: {e}")
            # Re-queue failed events
            self._buffer.extend(events[:self._buffer_size])

    # ------------------------------------------------------------------
    # Aggregation Queries
    # ------------------------------------------------------------------

    async def get_daily_costs(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily cost breakdown for a user."""
        db = self._get_db()
        if not db:
            return []

        start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        try:
            result = db.table(self.TABLE_METRICS) \
                .select("timestamp, cost_usd, task_type, model_used, cached") \
                .eq("user_id", user_id) \
                .gte("timestamp", start) \
                .execute()

            rows = result.data or []
            daily: Dict[str, Dict[str, Any]] = {}

            for row in rows:
                day = row["timestamp"][:10] if row.get("timestamp") else "unknown"
                if day not in daily:
                    daily[day] = {"date": day, "total_cost": 0.0, "calls": 0,
                                  "cached_calls": 0, "by_task": {}, "by_model": {}}
                d = daily[day]
                cost = row.get("cost_usd", 0) or 0
                d["total_cost"] += cost
                d["calls"] += 1
                if row.get("cached"):
                    d["cached_calls"] += 1

                task = row.get("task_type", "unknown")
                d["by_task"][task] = d["by_task"].get(task, 0) + cost

                model = row.get("model_used", "unknown")
                d["by_model"][model] = d["by_model"].get(model, 0) + cost

            return sorted(daily.values(), key=lambda x: x["date"])

        except Exception as e:
            logger.error(f"[Analytics] Daily costs query failed: {e}")
            return []

    async def get_user_usage(self, user_id: str, period_days: int = 30) -> Dict[str, Any]:
        """Get aggregated usage stats for a user."""
        db = self._get_db()
        if not db:
            return {"user_id": user_id, "total_cost": 0, "total_calls": 0}

        start = (datetime.now(timezone.utc) - timedelta(days=period_days)).isoformat()
        try:
            result = db.table(self.TABLE_METRICS) \
                .select("cost_usd, cached, task_type, status") \
                .eq("user_id", user_id) \
                .gte("timestamp", start) \
                .execute()

            rows = result.data or []
            total_cost = sum(r.get("cost_usd", 0) or 0 for r in rows)
            total_calls = len(rows)
            cached_calls = sum(1 for r in rows if r.get("cached"))
            failed_calls = sum(1 for r in rows if r.get("status") == "failed")

            by_task: Dict[str, Dict[str, Any]] = {}
            for r in rows:
                task = r.get("task_type", "unknown")
                if task not in by_task:
                    by_task[task] = {"calls": 0, "cost": 0.0}
                by_task[task]["calls"] += 1
                by_task[task]["cost"] += r.get("cost_usd", 0) or 0

            return {
                "user_id": user_id,
                "period_days": period_days,
                "total_cost_usd": round(total_cost, 4),
                "total_calls": total_calls,
                "cached_calls": cached_calls,
                "failed_calls": failed_calls,
                "cache_hit_rate": round(cached_calls / max(total_calls, 1) * 100, 1),
                "by_task": {k: {"calls": v["calls"], "cost_usd": round(v["cost"], 4)}
                            for k, v in sorted(by_task.items(), key=lambda x: -x[1]["cost"])},
            }

        except Exception as e:
            logger.error(f"[Analytics] User usage query failed: {e}")
            return {"user_id": user_id, "total_cost": 0, "total_calls": 0, "error": str(e)}

    async def get_system_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get system-wide metrics for the monitoring dashboard."""
        db = self._get_db()
        if not db:
            return {}

        start = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        try:
            result = db.table(self.TABLE_METRICS) \
                .select("event_type, cost_usd, duration_ms, status, cached, task_type") \
                .gte("timestamp", start) \
                .execute()

            rows = result.data or []
            total_cost = sum(r.get("cost_usd", 0) or 0 for r in rows)
            total_events = len(rows)

            by_type: Dict[str, int] = {}
            by_status: Dict[str, int] = {}
            for r in rows:
                et = r.get("event_type", "unknown")
                by_type[et] = by_type.get(et, 0) + 1
                st = r.get("status", "unknown")
                by_status[st] = by_status.get(st, 0) + 1

            durations = [r.get("duration_ms", 0) or 0 for r in rows if r.get("duration_ms")]
            avg_duration = sum(durations) / len(durations) if durations else 0

            return {
                "period_hours": hours,
                "total_cost_usd": round(total_cost, 4),
                "total_events": total_events,
                "avg_duration_ms": round(avg_duration, 0),
                "by_event_type": by_type,
                "by_status": by_status,
                "success_rate": round(by_status.get("success", 0) / max(total_events, 1) * 100, 1),
            }

        except Exception as e:
            logger.error(f"[Analytics] System metrics query failed: {e}")
            return {}

    async def get_model_efficiency_report(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get per-model cost-efficiency report."""
        db = self._get_db()
        if not db:
            return []

        start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        try:
            result = db.table(self.TABLE_METRICS) \
                .select("model_used, cost_usd, duration_ms, cached, task_type") \
                .gte("timestamp", start) \
                .execute()

            rows = result.data or []
            models: Dict[str, Dict[str, Any]] = {}

            for r in rows:
                model = r.get("model_used", "unknown")
                if model not in models:
                    models[model] = {"calls": 0, "cost": 0.0, "duration_ms": 0, "cached": 0}
                m = models[model]
                m["calls"] += 1
                m["cost"] += r.get("cost_usd", 0) or 0
                m["duration_ms"] += r.get("duration_ms", 0) or 0
                if r.get("cached"):
                    m["cached"] += 1

            report = []
            for model, stats in sorted(models.items(), key=lambda x: -x[1]["cost"]):
                report.append({
                    "model": model,
                    "calls": stats["calls"],
                    "total_cost_usd": round(stats["cost"], 4),
                    "avg_cost_per_call": round(stats["cost"] / stats["calls"], 6) if stats["calls"] else 0,
                    "avg_duration_ms": round(stats["duration_ms"] / stats["calls"], 0) if stats["calls"] else 0,
                    "cache_hits": stats["cached"],
                    "cache_hit_rate": round(stats["cached"] / stats["calls"] * 100, 1) if stats["calls"] else 0,
                })

            return report

        except Exception as e:
            logger.error(f"[Analytics] Model efficiency report failed: {e}")
            return []

    # ------------------------------------------------------------------
    # Periodic Aggregation
    # ------------------------------------------------------------------

    async def run_daily_aggregation(self) -> Dict[str, Any]:
        """Run daily aggregation — called by Celery Beat overnight.

        Aggregates raw metrics into daily summary tables for fast querying.
        """
        db = self._get_db()
        if not db:
            return {"status": "no_db"}

        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

        try:
            result = db.table(self.TABLE_METRICS) \
                .select("user_id, cost_usd, task_type, model_used, cached, status") \
                .like("timestamp", f"{yesterday}%") \
                .execute()

            rows = result.data or []
            by_user: Dict[str, Dict[str, Any]] = {}

            for r in rows:
                uid = r.get("user_id", "unknown")
                if uid not in by_user:
                    by_user[uid] = {
                        "date": yesterday, "user_id": uid,
                        "total_cost": 0.0, "calls": 0, "cached": 0,
                        "failed": 0, "by_model": {}, "by_task": {},
                    }
                u = by_user[uid]
                u["total_cost"] += r.get("cost_usd", 0) or 0
                u["calls"] += 1
                if r.get("cached"):
                    u["cached"] += 1
                if r.get("status") == "failed":
                    u["failed"] += 1

                model = r.get("model_used", "unknown")
                u["by_model"][model] = u["by_model"].get(model, 0) + (r.get("cost_usd", 0) or 0)
                task = r.get("task_type", "unknown")
                u["by_task"][task] = u["by_task"].get(task, 0) + (r.get("cost_usd", 0) or 0)

            # Write aggregates
            for uid, agg in by_user.items():
                agg["by_model_json"] = json.dumps(agg.pop("by_model"))
                agg["by_task_json"] = json.dumps(agg.pop("by_task"))
                try:
                    db.table(self.TABLE_DAILY_AGG).upsert(agg).execute()
                except Exception as e:
                    logger.warning(f"[Analytics] Daily agg upsert failed for {uid}: {e}")

            return {
                "status": "ok",
                "date": yesterday,
                "users_processed": len(by_user),
                "total_events": len(rows),
            }

        except Exception as e:
            logger.error(f"[Analytics] Daily aggregation failed: {e}")
            return {"status": "error", "detail": str(e)}


# Singleton
_analytics: Optional[AnalyticsService] = None


def get_analytics(db_client=None) -> AnalyticsService:
    global _analytics
    if _analytics is None:
        _analytics = AnalyticsService(db_client=db_client)
    return _analytics
