"""
Celery Configuration for MVC Distributed Pipeline
Phase 1 of the scaling plan: queue topology, routing, and broker setup.
"""
from celery import Celery
from kombu import Queue, Exchange
import os

REDIS_URL = os.environ.get("REDIS_URL", os.environ.get("UPSTASH_REDIS_URL", "redis://localhost:6379/0"))

PIPELINE_QUEUES = [
    Queue("priority.critical", Exchange("priority"), routing_key="priority.critical"),
    Queue("pipeline.download", Exchange("pipeline"), routing_key="pipeline.download"),
    Queue("pipeline.transcribe", Exchange("pipeline"), routing_key="pipeline.transcribe"),
    Queue("pipeline.segment", Exchange("pipeline"), routing_key="pipeline.segment"),
    Queue("pipeline.generate", Exchange("pipeline"), routing_key="pipeline.generate"),
    Queue("pipeline.safety", Exchange("pipeline"), routing_key="pipeline.safety"),
    Queue("pipeline.enrich", Exchange("pipeline"), routing_key="pipeline.enrich"),
    Queue("pipeline.thumbnail", Exchange("pipeline"), routing_key="pipeline.thumbnail"),
    Queue("pipeline.upload", Exchange("pipeline"), routing_key="pipeline.upload"),
    Queue("swarm.hooks", Exchange("swarm"), routing_key="swarm.hooks"),
    Queue("swarm.remix", Exchange("swarm"), routing_key="swarm.remix"),
    Queue("swarm.post", Exchange("swarm"), routing_key="swarm.post"),
    Queue("swarm.ab_test", Exchange("swarm"), routing_key="swarm.ab_test"),
    Queue("swarm.music", Exchange("swarm"), routing_key="swarm.music"),
    Queue("swarm.thumbnail", Exchange("swarm"), routing_key="swarm.thumbnail"),
    Queue("swarm.safety", Exchange("swarm"), routing_key="swarm.safety"),
    Queue("swarm.segment", Exchange("swarm"), routing_key="swarm.segment"),
    Queue("swarm.edit", Exchange("swarm"), routing_key="swarm.edit"),
    Queue("batch.overnight", Exchange("batch"), routing_key="batch.overnight"),
    Queue("metrics.aggregate", Exchange("metrics"), routing_key="metrics.aggregate"),
]

TASK_ROUTES = {
    "app.workers.pipeline_tasks.download_source": {"queue": "pipeline.download"},
    "app.workers.pipeline_tasks.transcribe": {"queue": "pipeline.transcribe"},
    "app.workers.pipeline_tasks.detect_segments": {"queue": "pipeline.segment"},
    "app.workers.pipeline_tasks.generate_clips": {"queue": "pipeline.generate"},
    "app.workers.pipeline_tasks.safety_check": {"queue": "pipeline.safety"},
    "app.workers.pipeline_tasks.enrich_content": {"queue": "pipeline.enrich"},
    "app.workers.pipeline_tasks.create_thumbnails": {"queue": "pipeline.thumbnail"},
    "app.workers.pipeline_tasks.upload_assets": {"queue": "pipeline.upload"},
    "app.workers.swarm_tasks.hook_agent_task": {"queue": "swarm.hooks"},
    "app.workers.swarm_tasks.remix_agent_task": {"queue": "swarm.remix"},
    "app.workers.swarm_tasks.post_agent_task": {"queue": "swarm.post"},
    "app.workers.swarm_tasks.ab_test_agent_task": {"queue": "swarm.ab_test"},
    "app.workers.swarm_tasks.music_match_agent_task": {"queue": "swarm.music"},
    "app.workers.swarm_tasks.thumbnail_agent_task": {"queue": "swarm.thumbnail"},
    "app.workers.swarm_tasks.safety_agent_task": {"queue": "swarm.safety"},
    "app.workers.swarm_tasks.segment_agent_task": {"queue": "swarm.segment"},
    "app.workers.swarm_tasks.edit_agent_task": {"queue": "swarm.edit"},
    "app.workers.batch_tasks.overnight_safety_batch": {"queue": "batch.overnight"},
    "app.workers.batch_tasks.overnight_hashtag_batch": {"queue": "batch.overnight"},
    "app.workers.batch_tasks.metrics_sync": {"queue": "metrics.aggregate"},
}


def make_celery(app_name: str = "mvc_pipeline") -> Celery:
    celery = Celery(app_name)
    celery.conf.update(
        broker_url=REDIS_URL,
        result_backend=REDIS_URL,
        broker_connection_retry_on_startup=True,
        broker_transport_options={"visibility_timeout": 43200},
        result_expires=86400,
        result_extended=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        task_queues=PIPELINE_QUEUES,
        task_routes=TASK_ROUTES,
        task_default_queue="pipeline.download",
        task_default_exchange="pipeline",
        task_default_routing_key="pipeline.download",
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_time_limit=1800,
        task_soft_time_limit=1500,
        task_default_retry_delay=30,
        task_max_retries=3,
        task_default_rate_limit="60/m",
        worker_send_task_events=True,
        task_send_sent_event=True,
        event_serializer="json",
    )
    return celery


celery_app = make_celery()
