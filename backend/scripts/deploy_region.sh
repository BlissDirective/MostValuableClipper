#!/bin/bash
# =============================================================================
# Regional Worker Deployment Script (Phase 4)
# Deploys worker pools to specific Fly.io regions.
#
# Usage:
#   ./scripts/deploy_region.sh lax    # Deploy to Los Angeles
#   ./scripts/deploy_region.sh iad    # Deploy to Washington DC
#   ./scripts/deploy_region.sh fra    # Deploy to Frankfurt
#   ./scripts/deploy_region.sh all    # Deploy to all regions
# =============================================================================
set -e

REGION="${1:-lax}"
APP_NAME="${FLY_APP_NAME:-mvc-worker}"
REDIS_URL="${REDIS_URL:-}"

if [ -z "$REDIS_URL" ]; then
    echo "[FATAL] REDIS_URL environment variable required"
    exit 1
fi

# Worker configurations per region
# Format: "queue_list|concurrency|vm_size|memory_mb|count"
declare -A REGION_AI_WORKERS=(
    [lax]="pipeline.transcribe,pipeline.safety,pipeline.enrich,swarm.hooks,swarm.post,swarm.ab_test,swarm.music,swarm.thumbnail,swarm.safety,swarm.segment,swarm.edit|20|performance-2x|2048|4"
    [iad]="pipeline.transcribe,pipeline.safety,pipeline.enrich,swarm.hooks,swarm.post,swarm.ab_test,swarm.music,swarm.thumbnail,swarm.safety,swarm.segment,swarm.edit|15|performance-2x|2048|3"
    [fra]="pipeline.transcribe,pipeline.safety,pipeline.enrich,swarm.hooks,swarm.post,swarm.ab_test|10|performance-2x|2048|2"
)

declare -A REGION_FFMPEG_WORKERS=(
    [lax]="pipeline.generate,pipeline.thumbnail|2|performance-4x|4096|2"
    [iad]="pipeline.generate,pipeline.thumbnail|2|performance-4x|4096|2"
    [fra]="pipeline.generate,pipeline.thumbnail|2|performance-4x|4096|1"
)

deploy_to_region() {
    local r="$1"
    echo "========================================"
    echo "  Deploying to region: $r"
    echo "========================================"

    # AI Workers
    local ai_cfg="${REGION_AI_WORKERS[$r]}"
    if [ -n "$ai_cfg" ]; then
        IFS='|' read -r queues conc vm_size memory count <<< "$ai_cfg"
        echo "[Deploy] AI Workers ($count x $vm_size)..."
        for i in $(seq 1 $count); do
            fly machine run . \
                --app "$APP_NAME" \
                --dockerfile Dockerfile.worker \
                --env CELERY_QUEUES="$queues" \
                --env CELERY_CONCURRENCY="$conc" \
                --env WORKER_TYPE="ai" \
                --env REDIS_URL="$REDIS_URL" \
                --env DEPLOY_REGION="$r" \
                --vm-size "$vm_size" \
                --vm-memory "$memory" \
                --region "$r" \
                --autostop=false \
                --metadata fly_process_group="ai-${r}" \
                2>/dev/null || echo "  AI worker ${r}-${i} may already exist"
        done
    fi

    # FFmpeg Workers
    local ff_cfg="${REGION_FFMPEG_WORKERS[$r]}"
    if [ -n "$ff_cfg" ]; then
        IFS='|' read -r queues conc vm_size memory count <<< "$ff_cfg"
        echo "[Deploy] FFmpeg Workers ($count x $vm_size)..."
        for i in $(seq 1 $count); do
            fly machine run . \
                --app "$APP_NAME" \
                --dockerfile Dockerfile.worker \
                --env CELERY_QUEUES="$queues" \
                --env CELERY_CONCURRENCY="$conc" \
                --env WORKER_TYPE="ffmpeg" \
                --env REDIS_URL="$REDIS_URL" \
                --env DEPLOY_REGION="$r" \
                --vm-size "$vm_size" \
                --vm-memory "$memory" \
                --region "$r" \
                --autostop=false \
                --metadata fly_process_group="ffmpeg-${r}" \
                2>/dev/null || echo "  FFmpeg worker ${r}-${i} may already exist"
        done
    fi

    echo "[Done] Region $r deployed"
}

# Main
case "$REGION" in
    all)
        for r in lax iad fra; do
            deploy_to_region "$r"
        done
        ;;
    lax|iad|fra)
        deploy_to_region "$REGION"
        ;;
    *)
        echo "Unknown region: $REGION"
        echo "Usage: $0 {lax|iad|fra|all}"
        exit 1
        ;;
esac

echo "========================================"
echo "  Deployment Complete!"
echo "========================================"
