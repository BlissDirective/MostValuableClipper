#!/bin/bash
# =============================================================================
# MVC Worker Deployment Script — Fly.io Machines
# =============================================================================
set -e

APP_NAME="${FLY_APP_NAME:-mvc-worker}"
REGION="${FLY_REGION:-lax}"

echo "========================================"
echo "  MVC Worker Deployment"
echo "========================================"

# --- Deploy AI Workers (2 machines) ---
echo "[Deploy] AI Workers (2x performance-2x)..."
for i in 1 2; do
    fly machine run . \
        --app "$APP_NAME" \
        --dockerfile Dockerfile.worker \
        --env CELERY_QUEUES="pipeline.transcribe,pipeline.safety,pipeline.enrich,swarm.hooks,swarm.post,swarm.ab_test,swarm.music,swarm.thumbnail,swarm.safety,swarm.segment,swarm.edit" \
        --env CELERY_CONCURRENCY=20 \
        --env WORKER_TYPE=ai \
        --env REDIS_URL="$REDIS_URL" \
        --vm-size performance-2x \
        --vm-memory 2048 \
        --region "$REGION" \
        --autostop=false \
        --metadata fly_process_group=ai-worker \
        2>/dev/null || echo "  AI worker $i may already exist"
done

# --- Deploy FFmpeg Workers (2 machines) ---
echo "[Deploy] FFmpeg Workers (2x performance-4x)..."
for i in 1 2; do
    fly machine run . \
        --app "$APP_NAME" \
        --dockerfile Dockerfile.worker \
        --env CELERY_QUEUES="pipeline.generate,pipeline.thumbnail" \
        --env CELERY_CONCURRENCY=2 \
        --env WORKER_TYPE=ffmpeg \
        --env REDIS_URL="$REDIS_URL" \
        --vm-size performance-4x \
        --vm-memory 4096 \
        --region "$REGION" \
        --autostop=false \
        --metadata fly_process_group=ffmpeg-worker \
        2>/dev/null || echo "  FFmpeg worker $i may already exist"
done

# --- Deploy I/O Workers (2 machines) ---
echo "[Deploy] I/O Workers (2x performance-2x)..."
for i in 1 2; do
    fly machine run . \
        --app "$APP_NAME" \
        --dockerfile Dockerfile.worker \
        --env CELERY_QUEUES="pipeline.download,pipeline.upload" \
        --env CELERY_CONCURRENCY=30 \
        --env WORKER_TYPE=io \
        --env REDIS_URL="$REDIS_URL" \
        --vm-size performance-2x \
        --vm-memory 1024 \
        --region "$REGION" \
        --autostop=false \
        --metadata fly_process_group=io-worker \
        2>/dev/null || echo "  I/O worker $i may already exist"
done

# --- Deploy Beat (scheduler) ---
echo "[Deploy] Celery Beat scheduler..."
fly machine run . \
    --app "$APP_NAME" \
    --dockerfile Dockerfile.worker \
    --env REDIS_URL="$REDIS_URL" \
    --vm-size shared-cpu-1x \
    --vm-memory 512 \
    --region "$REGION" \
    --autostop=false \
    --metadata fly_process_group=beat \
    --command "celery -A app.core.celery_config.celery_app beat -l info --scheduler celery.beat.PersistentScheduler -s /data/celerybeat-schedule" \
    2>/dev/null || echo "  Beat may already exist"

echo "========================================"
echo "  Deployment Complete!"
echo "  App: $APP_NAME"
echo "  Region: $REGION"
echo "========================================"
