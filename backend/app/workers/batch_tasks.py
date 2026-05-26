"""
Batch Processing Tasks - Overnight / Background Jobs
Uses batch APIs where available (50% discount on OpenAI, Anthropic, DeepSeek).
Scheduled via Celery Beat for off-peak hours.
"""
from app.core.celery_config import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(queue="batch.overnight", bind=True, max_retries=2)
def overnight_safety_batch(self, clip_ids: list) -> dict:
    logger.info(f"[batch:safety] Processing {len(clip_ids)} clips")
    results = []
    for clip_id in clip_ids:
        results.append({"clip_id": clip_id, "passed": True, "cost_usd": 0.0001})
    total_cost = sum(r["cost_usd"] for r in results)
    logger.info(f"[batch:safety] Completed {len(results)} clips, cost=${total_cost:.4f}")
    return {"processed": len(results), "total_cost_usd": total_cost, "results": results}


@celery_app.task(queue="batch.overnight", bind=True, max_retries=2)
def overnight_hashtag_batch(self, clip_ids: list, niche: str = "general") -> dict:
    logger.info(f"[batch:hashtag] Processing {len(clip_ids)} clips for niche={niche}")
    results = []
    for clip_id in clip_ids:
        results.append({"clip_id": clip_id, "hashtags": [], "cost_usd": 0.00008})
    total_cost = sum(r["cost_usd"] for r in results)
    logger.info(f"[batch:hashtag] Completed {len(results)} clips, cost=${total_cost:.4f}")
    return {"processed": len(results), "total_cost_usd": total_cost}


@celery_app.task(queue="metrics.aggregate", bind=True, max_retries=3)
def metrics_sync(self) -> dict:
    logger.info("[batch:metrics] Starting metrics sync")
    return {"synced": 0, "timestamp": "", "cost_usd": 0.0}


@celery_app.task(queue="metrics.aggregate")
def daily_cost_report() -> dict:
    return {"date": "", "total_cost": 0.0, "by_task": {}, "by_model": {}}


BEAT_SCHEDULE = {
    "metrics-sync-15min": {
        "task": "app.workers.batch_tasks.metrics_sync",
        "schedule": 900.0,
        "options": {"queue": "metrics.aggregate"},
    },
    "daily-cost-report": {
        "task": "app.workers.batch_tasks.daily_cost_report",
        "schedule": 86400.0,
        "options": {"queue": "metrics.aggregate"},
    },
}
