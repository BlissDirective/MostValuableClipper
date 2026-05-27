#!/bin/bash
# =============================================================================
# MVC Worker Startup Script
# Handles graceful shutdown, queue selection, and health reporting.
# Usage: ./scripts/start_worker.sh <worker_type>
#   worker_type: ai | ffmpeg | io | multi
# =============================================================================
set -e

WORKER_TYPE=${1:-${WORKER_TYPE:-"multi"}}
REDIS_URL=${REDIS_URL:-"redis://localhost:6379/0"}
CONCURRENCY=${CELERY_CONCURRENCY:-10}
LOG_LEVEL=${CELERY_LOG_LEVEL:-"info"}

# Queue configuration per worker type
declare -A QUEUES=(
    [ai]="pipeline.transcribe,pipeline.safety,pipeline.enrich,swarm.hooks,swarm.post,swarm.ab_test,swarm.music,swarm.thumbnail,swarm.safety,swarm.segment,swarm.edit"
    [ffmpeg]="pipeline.generate,pipeline.thumbnail"
    [io]="pipeline.download,pipeline.upload"
    [multi]="pipeline.download,pipeline.transcribe,pipeline.segment,pipeline.generate,pipeline.safety,pipeline.enrich,pipeline.thumbnail,pipeline.upload"
)

declare -A CONCURRENCY_MAP=(
    [ai]=20
    [ffmpeg]=2
    [io]=30
    [multi]=10
)

QUEUE=${QUEUES[$WORKER_TYPE]:-${QUEUES[multi]}}
CONCURRENCY=${CONCURRENCY_MAP[$WORKER_TYPE]:-$CONCURRENCY}

# Validate environment
if [ -z "$REDIS_URL" ]; then
    echo "[FATAL] REDIS_URL is not set"
    exit 1
fi

echo "========================================"
echo "  MVC Worker Starting"
echo "========================================"
echo "  Type:       $WORKER_TYPE"
echo "  Queues:     $QUEUE"
echo "  Concurrency: $CONCURRENCY"
echo "  Redis:      $REDIS_URL"
echo "========================================"

# Graceful shutdown handler
cleanup() {
    echo "[Worker] SIGTERM received — stopping gracefully..."
    kill -TERM "$CELERY_PID" 2>/dev/null || true
    wait "$CELERY_PID"
    echo "[Worker] Stopped"
    exit 0
}
trap cleanup SIGTERM SIGINT

# Start Celery worker
celery -A app.core.celery_config.celery_app worker \
    -Q "$QUEUE" \
    -c "$CONCURRENCY" \
    -l "$LOG_LEVEL" \
    -n "${WORKER_TYPE}-worker@%h" \
    --without-gossip \
    --without-mingle \
    --without-heartbeat \
    --max-tasks-per-child=1000 \
    &

CELERY_PID=$!
echo "[Worker] Started with PID $CELERY_PID"

# Wait for worker process
wait "$CELERY_PID"
