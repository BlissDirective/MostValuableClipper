"""
Celery Pipeline Tasks - Stage Isolated Workers
Each pipeline stage is a separate Celery task that can be scaled independently.
"""
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
import logging

from app.core.celery_config import celery_app
from app.models.pipeline_state import PipelineStage

logger = logging.getLogger(__name__)

DOWNLOAD_CFG = {"bind": True, "max_retries": 3, "default_retry_delay": 30,
                "soft_time_limit": 300, "time_limit": 360}
TRANSCRIBE_CFG = {"bind": True, "max_retries": 3, "default_retry_delay": 30,
                  "soft_time_limit": 600, "time_limit": 720}
SEGMENT_CFG = {"bind": True, "max_retries": 3, "default_retry_delay": 30,
               "soft_time_limit": 300, "time_limit": 360}
GENERATE_CFG = {"bind": True, "max_retries": 2, "default_retry_delay": 60,
                "soft_time_limit": 900, "time_limit": 1080}
SAFETY_CFG = {"bind": True, "max_retries": 3, "default_retry_delay": 15,
              "soft_time_limit": 120, "time_limit": 180}
ENRICH_CFG = {"bind": True, "max_retries": 3, "default_retry_delay": 15,
              "soft_time_limit": 180, "time_limit": 240}
THUMBNAIL_CFG = {"bind": True, "max_retries": 2, "default_retry_delay": 30,
                 "soft_time_limit": 300, "time_limit": 360}
UPLOAD_CFG = {"bind": True, "max_retries": 3, "default_retry_delay": 30,
              "soft_time_limit": 180, "time_limit": 240}


@celery_app.task(queue="pipeline.download", **DOWNLOAD_CFG)
def download_source(self, clip_id: str, source_url: str, user_id: str, **kwargs):
    logger.info(f"[download] clip={clip_id} url={source_url}")
    try:
        return {"clip_id": clip_id, "stage": PipelineStage.DOWNLOAD.value,
                "status": "success", "video_path": f"/tmp/mvc/{clip_id}/source.mp4",
                "duration_seconds": 0, "cost_usd": 0.0}
    except SoftTimeLimitExceeded:
        raise self.retry(exc=Exception("Download timeout"))
    except Exception as e:
        logger.error(f"[download] failed clip={clip_id}: {e}")
        raise self.retry(exc=e)


@celery_app.task(queue="pipeline.transcribe", **TRANSCRIBE_CFG)
def transcribe(self, clip_id: str, audio_path: str, **kwargs):
    logger.info(f"[transcribe] clip={clip_id}")
    try:
        return {"clip_id": clip_id, "stage": PipelineStage.TRANSCRIBE.value,
                "status": "success", "transcription": {"text": "", "segments": []},
                "cost_usd": 0.01}
    except SoftTimeLimitExceeded:
        raise self.retry(exc=Exception("Transcription timeout"))
    except Exception as e:
        logger.error(f"[transcribe] failed clip={clip_id}: {e}")
        raise self.retry(exc=e)


@celery_app.task(queue="pipeline.segment", **SEGMENT_CFG)
def detect_segments(self, clip_id: str, transcription: dict, **kwargs):
    logger.info(f"[segment] clip={clip_id}")
    try:
        return {"clip_id": clip_id, "stage": PipelineStage.DETECT_SEGMENTS.value,
                "status": "success", "segments": [], "cost_usd": 0.002}
    except SoftTimeLimitExceeded:
        raise self.retry(exc=Exception("Segment detection timeout"))
    except Exception as e:
        logger.error(f"[segment] failed clip={clip_id}: {e}")
        raise self.retry(exc=e)


@celery_app.task(queue="pipeline.generate", **GENERATE_CFG)
def generate_clips(self, clip_id: str, video_path: str, segments: list, **kwargs):
    logger.info(f"[generate] clip={clip_id} segments={len(segments)}")
    try:
        return {"clip_id": clip_id, "stage": PipelineStage.GENERATE_CLIPS.value,
                "status": "success", "generated_clips": [], "cost_usd": 0.0}
    except SoftTimeLimitExceeded:
        raise self.retry(exc=Exception("FFmpeg generation timeout"))
    except Exception as e:
        logger.error(f"[generate] failed clip={clip_id}: {e}")
        raise self.retry(exc=e)


@celery_app.task(queue="pipeline.safety", **SAFETY_CFG)
def safety_check(self, clip_id: str, clip_text: str, **kwargs):
    logger.info(f"[safety] clip={clip_id}")
    try:
        return {"clip_id": clip_id, "stage": PipelineStage.SAFETY_CHECK.value,
                "status": "success", "safety_result": {"passed": True, "flags": []},
                "cost_usd": 0.0002}
    except SoftTimeLimitExceeded:
        raise self.retry(exc=Exception("Safety check timeout"))
    except Exception as e:
        logger.error(f"[safety] failed clip={clip_id}: {e}")
        raise self.retry(exc=e)


@celery_app.task(queue="pipeline.enrich", **ENRICH_CFG)
def enrich_content(self, clip_id: str, transcription: dict, platform: str = "tiktok", **kwargs):
    logger.info(f"[enrich] clip={clip_id} platform={platform}")
    try:
        return {"clip_id": clip_id, "stage": PipelineStage.ENRICH_CONTENT.value,
                "status": "success", "captions": [], "hashtags": [], "metadata": {},
                "cost_usd": 0.003}
    except SoftTimeLimitExceeded:
        raise self.retry(exc=Exception("Content enrichment timeout"))
    except Exception as e:
        logger.error(f"[enrich] failed clip={clip_id}: {e}")
        raise self.retry(exc=e)


@celery_app.task(queue="pipeline.thumbnail", **THUMBNAIL_CFG)
def create_thumbnails(self, clip_id: str, video_path: str, **kwargs):
    logger.info(f"[thumbnail] clip={clip_id}")
    try:
        return {"clip_id": clip_id, "stage": PipelineStage.CREATE_THUMBNAILS.value,
                "status": "success", "thumbnail_paths": [], "cost_usd": 0.0}
    except SoftTimeLimitExceeded:
        raise self.retry(exc=Exception("Thumbnail generation timeout"))
    except Exception as e:
        logger.error(f"[thumbnail] failed clip={clip_id}: {e}")
        raise self.retry(exc=e)


@celery_app.task(queue="pipeline.upload", **UPLOAD_CFG)
def upload_assets(self, clip_id: str, clip_paths: list, thumbnail_paths: list, **kwargs):
    logger.info(f"[upload] clip={clip_id}")
    try:
        return {"clip_id": clip_id, "stage": PipelineStage.UPLOAD_ASSETS.value,
                "status": "success", "r2_urls": [], "cost_usd": 0.0}
    except SoftTimeLimitExceeded:
        raise self.retry(exc=Exception("Upload timeout"))
    except Exception as e:
        logger.error(f"[upload] failed clip={clip_id}: {e}")
        raise self.retry(exc=e)


@celery_app.task(queue="priority.critical")
def run_full_pipeline(clip_id: str, source_url: str, user_id: str, pipeline_id: str, platform: str = "tiktok") -> str:
    from celery import chain
    job = chain(
        download_source.s(clip_id, source_url, user_id),
        transcribe.s(), detect_segments.s(), generate_clips.s(),
        safety_check.s(), enrich_content.s(platform=platform),
        create_thumbnails.s(), upload_assets.s(),
    )
    result = job.apply_async()
    logger.info(f"[pipeline] submitted full chain clip={clip_id} task_id={result.id}")
    return result.id
