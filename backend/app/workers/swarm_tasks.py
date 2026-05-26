"""
Swarm Agent Tasks - Distributed via Celery Groups/Chords
Each swarm agent runs as a separate Celery task, enabling true parallelism
across the worker pool. Uses Celery's group primitive for parallel execution
and chord for result aggregation.
"""
from celery import group, chord
from app.core.celery_config import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(queue="swarm.hooks", bind=True, max_retries=2)
def hook_agent_task(self, clip_id: str, transcript: str, persona: str, platform: str) -> dict:
    try:
        logger.info(f"[swarm:hook] clip={clip_id} persona={persona}")
        return {"clip_id": clip_id, "agent": "HookSwarmAgent", "persona": persona,
                "hook": "", "cost_usd": 0.005, "model_used": "claude-sonnet-4.6"}
    except Exception as e:
        raise self.retry(exc=e)


@celery_app.task(queue="swarm.remix", bind=True, max_retries=2)
def remix_agent_task(self, clip_id: str, original_hook: str, target_platform: str) -> dict:
    try:
        logger.info(f"[swarm:remix] clip={clip_id} target={target_platform}")
        return {"clip_id": clip_id, "agent": "RemixSwarmAgent", "platform": target_platform,
                "remixed_hook": "", "cost_usd": 0.003, "model_used": "gpt-5.4-mini"}
    except Exception as e:
        raise self.retry(exc=e)


@celery_app.task(queue="swarm.post", bind=True, max_retries=2)
def post_agent_task(self, clip_id: str, hook: str, platform: str) -> dict:
    try:
        logger.info(f"[swarm:post] clip={clip_id} platform={platform}")
        return {"clip_id": clip_id, "agent": "PostSwarmAgent", "platform": platform,
                "post_text": "", "cost_usd": 0.002, "model_used": "claude-haiku-4.5"}
    except Exception as e:
        raise self.retry(exc=e)


@celery_app.task(queue="swarm.ab_test", bind=True, max_retries=2)
def ab_test_agent_task(self, clip_id: str, hook: str, variant_strategy: str) -> dict:
    try:
        logger.info(f"[swarm:ab_test] clip={clip_id} strategy={variant_strategy}")
        return {"clip_id": clip_id, "agent": "ABTestSwarmAgent", "variant": variant_strategy,
                "variant_hook": "", "cost_usd": 0.002, "model_used": "gpt-5.4-mini"}
    except Exception as e:
        raise self.retry(exc=e)


@celery_app.task(queue="swarm.music", bind=True, max_retries=2)
def music_match_agent_task(self, clip_id: str, mood_description: str) -> dict:
    try:
        logger.info(f"[swarm:music] clip={clip_id}")
        return {"clip_id": clip_id, "agent": "MusicMatchSwarmAgent",
                "recommended_tracks": [], "cost_usd": 0.0005, "model_used": "gpt-4.1-nano"}
    except Exception as e:
        raise self.retry(exc=e)


@celery_app.task(queue="swarm.thumbnail", bind=True, max_retries=2)
def thumbnail_agent_task(self, clip_id: str, transcript_summary: str) -> dict:
    try:
        logger.info(f"[swarm:thumbnail] clip={clip_id}")
        return {"clip_id": clip_id, "agent": "ThumbnailSwarmAgent",
                "thumbnail_text": "", "cost_usd": 0.0003, "model_used": "gpt-4.1-nano"}
    except Exception as e:
        raise self.retry(exc=e)


@celery_app.task(queue="swarm.safety", bind=True, max_retries=2)
def safety_agent_task(self, clip_id: str, clip_text: str) -> dict:
    try:
        logger.info(f"[swarm:safety] clip={clip_id}")
        return {"clip_id": clip_id, "agent": "SafetySwarmAgent",
                "safety_score": 1.0, "flags": [], "cost_usd": 0.0002, "model_used": "gpt-4.1-nano"}
    except Exception as e:
        raise self.retry(exc=e)


@celery_app.task(queue="swarm.segment", bind=True, max_retries=2)
def segment_agent_task(self, clip_id: str, transcript: str, analysis_type: str) -> dict:
    try:
        logger.info(f"[swarm:segment] clip={clip_id} type={analysis_type}")
        return {"clip_id": clip_id, "agent": "SegmentAnalyzeSwarmAgent",
                "analysis_type": analysis_type, "segments": [],
                "cost_usd": 0.002, "model_used": "gpt-5.4-mini"}
    except Exception as e:
        raise self.retry(exc=e)


@celery_app.task(queue="swarm.edit", bind=True, max_retries=2)
def edit_agent_task(self, clip_id: str, edit_request: str, clip_context: dict) -> dict:
    try:
        logger.info(f"[swarm:edit] clip={clip_id}")
        return {"clip_id": clip_id, "agent": "EditSwarmAgent",
                "edit_instructions": "", "cost_usd": 0.005, "model_used": "claude-sonnet-4.6"}
    except Exception as e:
        raise self.retry(exc=e)


@celery_app.task(queue="swarm.hooks")
def aggregate_swarm_results(results: list, clip_id: str) -> dict:
    total_cost = sum(r.get("cost_usd", 0) for r in results if isinstance(r, dict))
    hooks = [r.get("hook", "") for r in results if isinstance(r, dict) and r.get("agent") == "HookSwarmAgent"]
    best_hook = hooks[0] if hooks else ""
    logger.info(f"[swarm:aggregate] clip={clip_id} agents={len(results)} cost=${total_cost:.4f}")
    return {"clip_id": clip_id, "best_hook": best_hook, "all_hooks": hooks,
            "total_cost_usd": total_cost, "agent_results": results}


def execute_hook_swarm(clip_id: str, transcript: str, personas: list, platform: str = "tiktok"):
    task_group = group(hook_agent_task.s(clip_id, transcript, persona, platform) for persona in personas)
    return task_group.apply_async()


def execute_remix_swarm(clip_id: str, original_hook: str, target_platforms: list):
    task_group = group(remix_agent_task.s(clip_id, original_hook, platform) for platform in target_platforms)
    return task_group.apply_async()


def execute_ab_test_swarm(clip_id: str, hook: str, strategies: list):
    task_group = group(ab_test_agent_task.s(clip_id, hook, strategy) for strategy in strategies)
    return task_group.apply_async()


def execute_full_swarm_analysis(clip_id: str, transcript: str, platform: str = "tiktok"):
    task_group = group(
        hook_agent_task.s(clip_id, transcript, "hype_beast", platform),
        hook_agent_task.s(clip_id, transcript, "storyteller", platform),
        hook_agent_task.s(clip_id, transcript, "educator", platform),
        segment_agent_task.s(clip_id, transcript, "viral_score"),
        safety_agent_task.s(clip_id, transcript),
        music_match_agent_task.s(clip_id, transcript),
        thumbnail_agent_task.s(clip_id, transcript),
        post_agent_task.s(clip_id, "", platform),
        ab_test_agent_task.s(clip_id, "", "curiosity_gap"),
    )
    return chord(task_group)(aggregate_swarm_results.s(clip_id))
