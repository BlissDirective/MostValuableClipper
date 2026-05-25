"""Swarm batch service — cost-optimized batch execution with shared context.

Manages batch swarm jobs that process multiple clips with:
1. Shared source analysis context (one transcript → multiple hooks)
2. Sequential or parallel execution based on priority
3. Sub-linear cost pricing (batch discounts)
4. Progress tracking with partial result streaming
"""

import logging
import uuid
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from app.models import (
    SwarmBatchJob, SwarmBatchJobStatus, SwarmBatchClipResult,
    SwarmJobType, SwarmJobStatus
)
from app.services.database import supabase
from app.services.queue import QueueService, CacheService

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Scale Constants
# ─────────────────────────────────────────────────────────────

WAVE_SIZE = 50              # Clips per partition wave
MAX_CONCURRENT_BATCHES = 2  # Per-user concurrent limit
MAX_DAILY_CLIPS = 500       # Per-user daily clip limit
MAX_RETRIES = 2             # Retry attempts per failed clip
RETRY_DELAYS = [5, 15]      # Seconds between retries (exponential)

PRIORITY_SCORES = {
    "speed": 100,      # Process first
    "balanced": 50,    # Middle
    "cost": 10,        # Process last
}


# ─────────────────────────────────────────────────────────────
# Batch Cost Pricing (sub-linear)
# ─────────────────────────────────────────────────────────────

BATCH_COSTS = {
    "hook":       {"base": 50,  "per_clip": 3,  "per_agent": 2},
    "remix":      {"base": 200, "per_clip": 15, "per_agent": 5},
    "post":       {"base": 10,  "per_clip": 1,  "per_agent": 1},
    "ab_test":    {"base": 30,  "per_clip": 5,  "per_agent": 2},
    "music_match": {"base": 20,  "per_clip": 2,  "per_agent": 1},
    "thumbnail":  {"base": 15,  "per_clip": 1,  "per_agent": 1},
    "safety":     {"base": 10,  "per_clip": 1,  "per_agent": 1},
    "hooks_analysis": {"base": 80,  "per_clip": 8,  "per_agent": 2},
    "segment_analyze": {"base": 50,  "per_clip": 5,  "per_agent": 2},
    "edit":       {"base": 150, "per_clip": 12, "per_agent": 5},
}


def calculate_batch_cost(pool_type: str, clip_count: int, agent_count: int) -> int:
    """Calculate batch cost in cents with sub-linear pricing."""
    pricing = BATCH_COSTS.get(pool_type, {"base": 50, "per_clip": 5, "per_agent": 2})
    return (
        pricing["base"] +
        pricing["per_clip"] * clip_count +
        pricing["per_agent"] * agent_count
    )


def calculate_individual_cost(pool_type: str, clip_count: int, agent_count: int) -> int:
    """Calculate what it would cost to process each clip individually."""
    per_clip = SwarmConfigService.DEFAULT_COSTS.get(pool_type, 5) * agent_count
    return per_clip * clip_count


# ─────────────────────────────────────────────────────────────
# Shared Batch Context
# ─────────────────────────────────────────────────────────────

class BatchContext:
    """Shared analysis results reused across clips from the same source.
    
    Loads source-level analysis once (transcript, energy peaks, faces)
    and provides per-clip context slices to minimize redundant API calls.
    """

    def __init__(self, source_id: str):
        self.source_id = source_id
        self.transcript: Optional[str] = None
        self.transcript_segments: List[dict] = []
        self.energy_peaks: List[float] = []
        self.face_segments: List[dict] = []
        self.audio_fingerprint: Optional[dict] = None
        self._loaded = False

    async def load(self) -> None:
        if self._loaded:
            return
        
        try:
            # Load transcript from clips table or source metadata
            result = supabase.table("clips").select("source_id, metadata, transcript") \
                .eq("source_id", self.source_id).limit(1).execute()
            
            if result.data:
                data = result.data[0]
                metadata = data.get("metadata", {})
                self.transcript = data.get("transcript") or metadata.get("transcript")
                self.transcript_segments = metadata.get("transcript_segments", [])
                self.energy_peaks = metadata.get("energy_peaks", [])
                self.face_segments = metadata.get("face_segments", [])
                self.audio_fingerprint = metadata.get("audio_fingerprint")
        except Exception as e:
            logger.warning(f"[BatchContext] Failed to load context for {self.source_id}: {e}")
        
        self._loaded = True

    def get_context_for_clip(self, clip_id: str, segment: Optional[dict] = None) -> dict:
        """Extract relevant portion of shared context for a specific clip."""
        if not self._loaded:
            return {"source_id": self.source_id}
        
        context = {
            "source_id": self.source_id,
            "transcript": self.transcript,
        }
        
        if segment and self.transcript_segments:
            start, end = segment.get("start", 0), segment.get("end", 0)
            # Extract transcript segments within clip range
            relevant = [
                s for s in self.transcript_segments
                if s.get("start", 0) <= end and s.get("end", 0) >= start
            ]
            context["transcript_segments"] = relevant
            context["clip_segment"] = segment
        
        if segment and self.energy_peaks:
            start, end = segment.get("start", 0), segment.get("end", 0)
            peaks_in_range = [p for p in self.energy_peaks if start <= p <= end]
            context["energy_peaks"] = peaks_in_range
        
        if self.face_segments:
            context["face_segments"] = self.face_segments
        
        if self.audio_fingerprint:
            context["audio_fingerprint"] = self.audio_fingerprint
        
        return context


async def build_batch_context(clip_ids: List[str]) -> Dict[str, BatchContext]:
    """Build shared context for all clips grouped by source.
    
    Returns a dict mapping source_id -> BatchContext.
    """
    # Fetch clip source info
    try:
        result = supabase.table("clips").select("id, source_id, start_time, end_time, metadata") \
            .in_("id", clip_ids).execute()
        
        clips_data = result.data or []
    except Exception as e:
        logger.warning(f"[BatchService] Failed to fetch clip sources: {e}")
        clips_data = []
    
    # Group by source
    source_to_clips: Dict[str, List[dict]] = {}
    clip_to_segment: Dict[str, dict] = {}
    
    for clip in clips_data:
        source_id = clip.get("source_id")
        if not source_id:
            continue
        
        if source_id not in source_to_clips:
            source_to_clips[source_id] = []
        
        source_to_clips[source_id].append(clip)
        
        clip_to_segment[clip["id"]] = {
            "start": clip.get("start_time", 0),
            "end": clip.get("end_time", 0),
        }
    
    # Load context for each source
    contexts: Dict[str, BatchContext] = {}
    for source_id in source_to_clips:
        ctx = BatchContext(source_id)
        await ctx.load()
        contexts[source_id] = ctx
    
    return contexts, clip_to_segment


# ─────────────────────────────────────────────────────────────
# Swarm Batch Service
# ─────────────────────────────────────────────────────────────

class SwarmBatchService:
    """Execute swarm operations on batches of clips with shared context."""

    def __init__(self, orchestrator=None):
        self.orchestrator = orchestrator
        self._running_batches: Dict[str, asyncio.Task] = {}

    async def execute_batch(
        self,
        clip_ids: List[str],
        pool_type: str,
        user_id: str,
        agent_count: Optional[int] = None,
        strategy_filter: Optional[List[str]] = None,
        priority: str = "balanced",
        top_k: Optional[int] = None,
        shared_context: bool = True,
        custom_options: Optional[Dict[str, Any]] = None,
        progress_callback = None,
        clip_result_callback = None,
    ) -> Dict[str, Any]:
        """Execute a batch swarm job.
        
        Args:
            clip_ids: List of clip IDs to process
            pool_type: Swarm pool type
            user_id: User ID
            agent_count: Agents per clip (None = use user's allocation)
            strategy_filter: Strategy/persona filter
            priority: cost | balanced | speed
            top_k: Only process top N clips
            shared_context: Whether to share source analysis across clips
            custom_options: Additional options passed to the orchestrator
        
        Returns:
            Batch execution result dict
        """
        start_time = time.time()
        batch_id = str(uuid.uuid4())
        
        # Validate pool type
        valid_pools = [
            "hook", "remix", "post", "ab_test", "music_match",
            "thumbnail", "safety", "hooks_analysis", "segment_analyze", "edit"
        ]
        if pool_type not in valid_pools:
            return {"error": f"Invalid pool_type: {pool_type}. Must be one of {valid_pools}", "batch_id": None}
        
        # Get user config
        config = await SwarmConfigService.get_config(user_id)
        allocated = config.get_pool_agents(pool_type)
        requested = agent_count if agent_count is not None else allocated
        per_clip_agents = min(requested, allocated)
        
        if per_clip_agents <= 0:
            return {"error": f"{pool_type} swarm disabled or limit reached", "batch_id": None}
        
        if pool_type not in config.enabled_pools:
            return {"error": f"{pool_type} swarm pool disabled", "batch_id": None}
        
        # Apply top-k filtering
        clips_to_process = clip_ids
        if top_k and top_k < len(clip_ids):
            # For balanced mode, we might want to analyze all but only deep-process top_k
            # For now, simple truncation — later: base-score filtering
            clips_to_process = clip_ids[:top_k]
        
        total_clips = len(clips_to_process)
        total_agents = per_clip_agents * total_clips
        
        # Check budget
        batch_cost = calculate_batch_cost(pool_type, total_clips, per_clip_agents)
        if not await SwarmConfigService.check_budget(user_id, pool_type, total_agents):
            return {"error": "Daily budget exceeded for batch operation", "batch_id": None}
        
        # Build shared context if enabled
        batch_contexts = {}
        clip_segments = {}
        if shared_context:
            try:
                batch_contexts, clip_segments = await build_batch_context(clips_to_process)
            except Exception as e:
                logger.warning(f"[BatchService] Context build failed: {e}")
        
        # Create batch job record
        batch_job = SwarmBatchJob(
            batch_id=batch_id,
            user_id=user_id,
            pool_type=SwarmJobType(pool_type),
            clip_ids=clips_to_process,
            total_clips=total_clips,
            processed_clips=0,
            status=SwarmBatchJobStatus.queued,
            shared_context={
                "sources_loaded": list(batch_contexts.keys()),
                "context_enabled": shared_context,
            } if batch_contexts else None,
            agent_count=per_clip_agents,
            strategy_filter=strategy_filter,
            custom_options=custom_options,
        )
        
        try:
            supabase.table("swarm_batch_jobs").insert(batch_job.model_dump(mode="json")).execute()
        except Exception as e:
            logger.warning(f"[BatchService] Failed to create batch job: {e}")
        
        # Update status to running
        batch_job.status = SwarmBatchJobStatus.running
        batch_job.updated_at = datetime.now(timezone.utc)
        try:
            supabase.table("swarm_batch_jobs").update({
                "status": "running",
                "updated_at": batch_job.updated_at.isoformat(),
                "results_summary": {
                    "estimated_cost_cents": batch_cost,
                    "priority": priority,
                    "shared_context": shared_context,
                    "waves": len(self._partition_clips(clips_to_process)),
                },
            }).eq("batch_id", batch_id).execute()
        except Exception as e:
            logger.warning(f"[BatchService] Failed to update batch status: {e}")
        
        # Partition into waves for scale
        waves = self._partition_clips(clips_to_process)
        total_waves = len(waves)
        all_results: List[Dict[str, Any]] = []
        total_completed = 0
        total_failed = 0
        total_cost = 0
        
        logger.info(
            f"[BatchService] Batch {batch_id}: {total_clips} clips "
            f"partitioned into {total_waves} wave(s)"
        )
        
        for wave_idx, wave_clips in enumerate(waves, 1):
            # Check if batch was cancelled
            job_check = await self.get_batch_job(batch_id)
            if job_check and job_check.get("status") == "cancelled":
                logger.info(f"[BatchService] Batch {batch_id} cancelled during wave {wave_idx}")
                break
            
            # Cost throttling: re-check budget between waves for large batches
            if total_waves > 1 and wave_idx > 1:
                remaining_cost = batch_cost - total_cost
                if not await SwarmConfigService.check_budget(user_id, pool_type, per_clip_agents * len(wave_clips)):
                    logger.warning(f"[BatchService] Budget exceeded after wave {wave_idx-1}, stopping")
                    # Update status
                    try:
                        supabase.table("swarm_batch_jobs").update({
                            "status": "partial",
                            "error": f"Budget exhausted after {wave_idx-1}/{total_waves} waves",
                        }).eq("batch_id", batch_id).execute()
                    except Exception:
                        pass
                    break
            
            # Execute wave
            wave_results = await self._execute_wave(
                wave_num=wave_idx,
                total_waves=total_waves,
                batch_id=batch_id,
                clips=wave_clips,
                pool_type=pool_type,
                user_id=user_id,
                agent_count=per_clip_agents,
                strategy_filter=strategy_filter,
                batch_contexts=batch_contexts,
                clip_segments=clip_segments,
                custom_options=custom_options,
                priority=priority,
                progress_callback=progress_callback,
                clip_result_callback=clip_result_callback,
            )
            
            all_results.extend(wave_results)
            
            # Update counters
            wave_completed = len([r for r in wave_results if r.get("status") == "completed"])
            wave_failed = len([r for r in wave_results if r.get("status") == "failed"])
            wave_cost = sum(r.get("cost_cents", 0) for r in wave_results)
            
            total_completed += wave_completed
            total_failed += wave_failed
            total_cost += wave_cost
            
            # Update wave progress
            try:
                supabase.table("swarm_batch_jobs").update({
                    "processed_clips": total_completed,
                    "failed_clips": total_failed,
                    "cost_cents": total_cost,
                    "current_clip_id": wave_clips[-1] if wave_clips else None,
                    "results_summary": {
                        "wave": wave_idx,
                        "total_waves": total_waves,
                        "wave_completed": wave_completed,
                        "wave_failed": wave_failed,
                        "total_completed": total_completed,
                        "total_failed": total_failed,
                        "total_cost_cents": total_cost,
                        "estimated_cost_cents": batch_cost,
                    },
                }).eq("batch_id", batch_id).execute()
            except Exception as e:
                logger.warning(f"[BatchService] Wave progress update failed: {e}")
        
        # Calculate final stats
        actual_cost = total_cost
        
        # Final progress update
        if progress_callback:
            await progress_callback(
                batch_id=batch_id,
                processed=total_completed,
                total=total_clips,
                failed=total_failed,
                current_status="completed",
                detail=f"Batch completed: {total_completed} succeeded, {total_failed} failed ({total_waves} waves)",
            )
        
        # Update batch job as completed
        duration_ms = int((time.time() - start_time) * 1000)
        final_status = "completed" if total_failed == 0 else "partial" if total_completed > 0 else "failed"
        batch_job.status = SwarmBatchJobStatus.completed if final_status == "completed" else SwarmBatchJobStatus.failed
        batch_job.processed_clips = total_completed
        batch_job.failed_clips = total_failed
        batch_job.cost_cents = actual_cost
        batch_job.completed_at = datetime.now(timezone.utc)
        batch_job.results_summary = {
            "total_clips": total_clips,
            "completed": total_completed,
            "failed": total_failed,
            "waves": total_waves,
            "duration_ms": duration_ms,
            "actual_cost_cents": actual_cost,
            "estimated_cost_cents": batch_cost,
        }
        
        try:
            supabase.table("swarm_batch_jobs").update({
                "status": final_status,
                "processed_clips": total_completed,
                "failed_clips": total_failed,
                "cost_cents": actual_cost,
                "completed_at": batch_job.completed_at.isoformat(),
                "results_summary": batch_job.results_summary,
            }).eq("batch_id", batch_id).execute()
        except Exception as e:
            logger.warning(f"[BatchService] Failed to finalize batch job: {e}")
        
        # Decrement rate limit counter
        await self._decrement_user_batch_count(user_id)
        
        # Calculate savings
        individual_cost = calculate_individual_cost(pool_type, total_clips, per_clip_agents)
        savings_pct = round((1 - actual_cost / max(individual_cost, 1)) * 100, 1) if individual_cost > 0 else 0
        
        return {
            "batch_id": batch_id,
            "pool_type": pool_type,
            "total_clips": total_clips,
            "processed_clips": total_completed,
            "failed_clips": total_failed,
            "waves": total_waves,
            "status": final_status,
            "results": all_results,
            "cost_cents": actual_cost,
            "estimated_cost_usd": round(actual_cost / 100, 2),
            "savings_percent": savings_pct,
            "duration_ms": duration_ms,
            "created_at": batch_job.created_at.isoformat(),
            "completed_at": batch_job.completed_at.isoformat() if batch_job.completed_at else None,
        }

    async def _execute_single_clip(
        self,
        batch_id: str,
        clip_id: str,
        pool_type: str,
        user_id: str,
        agent_count: int,
        strategy_filter: Optional[List[str]],
        shared_context: Optional[dict],
        custom_options: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute swarm on a single clip within a batch."""
        result_id = str(uuid.uuid4())
        clip_start = time.time()
        
        # Create per-clip result record
        clip_result = SwarmBatchClipResult(
            result_id=result_id,
            batch_id=batch_id,
            clip_id=clip_id,
            agent_index=0,
            status="pending",
        )
        try:
            supabase.table("swarm_batch_clip_results").insert(clip_result.model_dump(mode="json")).execute()
        except Exception as e:
            logger.warning(f"[BatchService] Failed to create clip result: {e}")
        
        try:
            # Build execution params with shared context
            options = dict(custom_options or {})
            if shared_context:
                options["shared_context"] = shared_context
            
            # Map strategy_filter to the correct backend field
            if strategy_filter:
                strategy_map = {
                    "hook": "persona_filter",
                    "remix": "strategy_filter",
                    "ab_test": "strategy_filter",
                    "music_match": "strategy_filter",
                    "thumbnail": "style_filter",
                    "safety": "sensitivity_filter",
                    "hooks_analysis": "method_filter",
                    "segment_analyze": "strategy_filter",
                    "edit": "recipe_filter",
                    "post": None,
                }
                field = strategy_map.get(pool_type)
                if field:
                    options[field] = strategy_filter
            
            # Execute via orchestrator
            swarm_result = await self._dispatch_to_orchestrator(
                pool_type=pool_type,
                clip_id=clip_id,
                user_id=user_id,
                agent_count=agent_count,
                options=options,
            )
            
            duration_ms = int((time.time() - clip_start) * 1000)
            
            # Update clip result
            clip_result.status = "completed" if "error" not in swarm_result else "failed"
            clip_result.result_data = swarm_result
            clip_result.cost_cents = swarm_result.get("total_cost_cents", 0)
            clip_result.duration_ms = duration_ms
            if "error" in swarm_result:
                clip_result.error_message = swarm_result["error"]
            
            try:
                supabase.table("swarm_batch_clip_results").update({
                    "status": clip_result.status,
                    "result_data": clip_result.result_data,
                    "cost_cents": clip_result.cost_cents,
                    "duration_ms": clip_result.duration_ms,
                    "error_message": clip_result.error_message,
                }).eq("result_id", result_id).execute()
            except Exception as e:
                logger.warning(f"[BatchService] Failed to update clip result: {e}")
            
            return {
                "clip_id": clip_id,
                "status": clip_result.status,
                "result_data": swarm_result,
                "cost_cents": clip_result.cost_cents,
                "duration_ms": duration_ms,
                "error_message": clip_result.error_message,
            }
        
        except Exception as e:
            logger.error(f"[BatchService] Clip {clip_id} failed: {e}")
            duration_ms = int((time.time() - clip_start) * 1000)
            
            try:
                supabase.table("swarm_batch_clip_results").update({
                    "status": "failed",
                    "error_message": str(e),
                    "duration_ms": duration_ms,
                }).eq("result_id", result_id).execute()
            except Exception as ue:
                logger.warning(f"[BatchService] Failed to update failed result: {ue}")
            
            return {
                "clip_id": clip_id,
                "status": "failed",
                "result_data": None,
                "cost_cents": 0,
                "duration_ms": duration_ms,
                "error_message": str(e),
            }

    async def _dispatch_to_orchestrator(
        self,
        pool_type: str,
        clip_id: str,
        user_id: str,
        agent_count: int,
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Dispatch a single clip to the appropriate orchestrator method."""
        if not self.orchestrator:
            return {"error": "Orchestrator not available", "job_id": None}
        
        if pool_type == "hook":
            return await self.orchestrator.execute_hook_swarm(
                clip_id=clip_id,
                user_id=user_id,
                platform=options.get("platform", "tiktok"),
                agent_count=agent_count,
                persona_filter=options.get("persona_filter"),
            )
        elif pool_type == "remix":
            return await self.orchestrator.execute_remix_swarm(
                clip_id=clip_id,
                user_id=user_id,
                agent_count=agent_count,
                strategy_filter=options.get("strategy_filter"),
            )
        elif pool_type == "post":
            return await self.orchestrator.execute_post_swarm(
                clip_id=clip_id,
                user_id=user_id,
                accounts=options.get("accounts", []),
                hooks=options.get("hooks"),
                agent_count=agent_count,
            )
        elif pool_type == "ab_test":
            return await self.orchestrator.execute_ab_test_swarm(
                test_id=options.get("test_id", clip_id),
                user_id=user_id,
                clip_id=clip_id,
                agent_count=agent_count,
                strategy_filter=options.get("strategy_filter"),
            )
        elif pool_type == "music_match":
            return await self.orchestrator.execute_music_match_swarm(
                clip_id=clip_id,
                user_id=user_id,
                agent_count=agent_count,
                strategy_filter=options.get("strategy_filter"),
                segment_data=options.get("segment_data"),
            )
        elif pool_type == "thumbnail":
            return await self.orchestrator.execute_thumbnail_swarm(
                clip_id=clip_id,
                user_id=user_id,
                agent_count=agent_count,
                style_filter=options.get("style_filter"),
            )
        elif pool_type == "safety":
            return await self.orchestrator.execute_safety_swarm(
                clip_id=clip_id,
                user_id=user_id,
                agent_count=agent_count,
                sensitivity_filter=options.get("sensitivity_filter"),
            )
        elif pool_type == "hooks_analysis":
            return await self.orchestrator.execute_hooks_analysis_swarm(
                clip_id=clip_id,
                user_id=user_id,
                platform=options.get("platform", "tiktok"),
                agent_count=agent_count,
                method_filter=options.get("method_filter"),
            )
        elif pool_type == "segment_analyze":
            return await self.orchestrator.execute_segment_analyze_swarm(
                clip_id=clip_id,
                user_id=user_id,
                agent_count=agent_count,
                strategy_filter=options.get("strategy_filter"),
            )
        elif pool_type == "edit":
            return await self.orchestrator.execute_edit_swarm(
                clip_id=clip_id,
                user_id=user_id,
                agent_count=agent_count,
                recipe_filter=options.get("recipe_filter"),
            )
        else:
            return {"error": f"Unknown pool type: {pool_type}", "job_id": None}

    async def _execute_sequential(
        self, batch_id, clips, pool_type, user_id, agent_count,
        strategy_filter, batch_contexts, clip_segments, custom_options,
        progress_callback=None, clip_result_callback=None,
    ) -> List[Dict[str, Any]]:
        """Execute clips one at a time (cost-optimized)."""
        results = []
        for i, clip_id in enumerate(clips):
            # Get shared context for this clip
            shared = None
            if batch_contexts and clip_id in clip_segments:
                seg = clip_segments[clip_id]
                # Find source context
                for ctx in batch_contexts.values():
                    shared = ctx.get_context_for_clip(clip_id, seg)
                    break
            
            result = await self._execute_single_clip(
                batch_id, clip_id, pool_type, user_id, agent_count,
                strategy_filter, shared, custom_options
            )
            results.append(result)
            
            completed_count = len([r for r in results if r.get("status") == "completed"])
            failed_count = len([r for r in results if r.get("status") == "failed"])
            
            # Progress callback
            if progress_callback:
                try:
                    await progress_callback(
                        batch_id=batch_id,
                        processed=completed_count,
                        total=len(clips),
                        failed=failed_count,
                        current_clip=clip_id,
                        current_status="processing",
                        detail=f"Processed clip {i+1}/{len(clips)}",
                    )
                except Exception as e:
                    logger.warning(f"[BatchService] Progress callback failed: {e}")
            
            if clip_result_callback:
                try:
                    await clip_result_callback(batch_id, clip_id, result)
                except Exception as e:
                    logger.warning(f"[BatchService] Clip result callback failed: {e}")
            
            # Update processed count
            try:
                supabase.table("swarm_batch_jobs").update({
                    "processed_clips": completed_count,
                    "failed_clips": failed_count,
                }).eq("batch_id", batch_id).execute()
            except Exception as e:
                logger.warning(f"[BatchService] Progress update failed: {e}")
        
        return results

    async def _execute_parallel(
        self, batch_id, clips, pool_type, user_id, agent_count,
        strategy_filter, batch_contexts, clip_segments, custom_options,
        progress_callback=None, clip_result_callback=None,
    ) -> List[Dict[str, Any]]:
        """Execute all clips in parallel (speed-optimized)."""
        completed_count = [0]
        failed_count = [0]
        
        async def run_clip(clip_id: str) -> Dict[str, Any]:
            shared = None
            if batch_contexts and clip_id in clip_segments:
                seg = clip_segments[clip_id]
                for ctx in batch_contexts.values():
                    shared = ctx.get_context_for_clip(clip_id, seg)
                    break
            
            result = await self._execute_single_clip(
                batch_id, clip_id, pool_type, user_id, agent_count,
                strategy_filter, shared, custom_options
            )
            
            # Update counters
            if result.get("status") == "completed":
                completed_count[0] += 1
            else:
                failed_count[0] += 1
            
            # Progress callback
            if progress_callback:
                try:
                    await progress_callback(
                        batch_id=batch_id,
                        processed=completed_count[0],
                        total=len(clips),
                        failed=failed_count[0],
                        current_clip=clip_id,
                        current_status="processing",
                        detail="Parallel processing clip",
                    )
                except Exception as e:
                    logger.warning(f"[BatchService] Progress callback failed: {e}")
            
            if clip_result_callback:
                try:
                    await clip_result_callback(batch_id, clip_id, result)
                except Exception as e:
                    logger.warning(f"[BatchService] Clip result callback failed: {e}")
            
            return result
        
        # Launch all at once
        tasks = [run_clip(cid) for cid in clips]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Normalize exceptions to error dicts
        normalized = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                normalized.append({
                    "clip_id": clips[i],
                    "status": "failed",
                    "error_message": str(res),
                    "cost_cents": 0,
                    "duration_ms": 0,
                })
                failed_count[0] += 1
            else:
                normalized.append(res)
        
        # Update final count
        try:
            supabase.table("swarm_batch_jobs").update({
                "processed_clips": completed_count[0],
                "failed_clips": failed_count[0],
            }).eq("batch_id", batch_id).execute()
        except Exception as e:
            logger.warning(f"[BatchService] Final progress update failed: {e}")
        
        return normalized

    async def _execute_balanced(
        self, batch_id, clips, pool_type, user_id, agent_count,
        strategy_filter, batch_contexts, clip_segments, custom_options,
        progress_callback=None, clip_result_callback=None,
    ) -> List[Dict[str, Any]]:
        """Execute with limited concurrency (default: 5 at a time)."""
        semaphore = asyncio.Semaphore(5)
        completed_count = [0]
        failed_count = [0]
        
        async def run_clip_limited(clip_id: str) -> Dict[str, Any]:
            async with semaphore:
                shared = None
                if batch_contexts and clip_id in clip_segments:
                    seg = clip_segments[clip_id]
                    for ctx in batch_contexts.values():
                        shared = ctx.get_context_for_clip(clip_id, seg)
                        break
                
                result = await self._execute_single_clip(
                    batch_id, clip_id, pool_type, user_id, agent_count,
                    strategy_filter, shared, custom_options
                )
                
                # Update counters
                if result.get("status") == "completed":
                    completed_count[0] += 1
                else:
                    failed_count[0] += 1
                
                # Progress callback
                if progress_callback:
                    try:
                        await progress_callback(
                            batch_id=batch_id,
                            processed=completed_count[0],
                            total=len(clips),
                            failed=failed_count[0],
                            current_clip=clip_id,
                            current_status="processing",
                            detail="Processing clip with concurrency limit",
                        )
                    except Exception as e:
                        logger.warning(f"[BatchService] Progress callback failed: {e}")
                
                if clip_result_callback:
                    try:
                        await clip_result_callback(batch_id, clip_id, result)
                    except Exception as e:
                        logger.warning(f"[BatchService] Clip result callback failed: {e}")
                
                # Update progress
                try:
                    supabase.table("swarm_batch_jobs").update({
                        "processed_clips": completed_count[0],
                        "failed_clips": failed_count[0],
                    }).eq("batch_id", batch_id).execute()
                except Exception as e:
                    logger.warning(f"[BatchService] Progress update failed: {e}")
                
                return result
        
        tasks = [run_clip_limited(cid) for cid in clips]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        normalized = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                normalized.append({
                    "clip_id": clips[i],
                    "status": "failed",
                    "error_message": str(res),
                    "cost_cents": 0,
                    "duration_ms": 0,
                })
                failed_count[0] += 1
            else:
                normalized.append(res)
        
        return normalized

    # ─────────────────────────────────────────────────────────────
    # Job Management
    # ─────────────────────────────────────────────────────────────

    async def list_batch_jobs(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List batch jobs for a user."""
        try:
            result = supabase.table("swarm_batch_jobs").select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(limit).offset(offset).execute()
            return result.data or []
        except Exception as e:
            logger.warning(f"[BatchService] Failed to list batch jobs: {e}")
            return []

    async def get_batch_job(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get a batch job by ID."""
        try:
            result = supabase.table("swarm_batch_jobs").select("*") \
                .eq("batch_id", batch_id).single().execute()
            return result.data
        except Exception as e:
            logger.debug(f"[BatchService] Batch job not found: {e}")
            return None

    async def get_batch_clip_results(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get per-clip results for a batch job."""
        try:
            result = supabase.table("swarm_batch_clip_results").select("*") \
                .eq("batch_id", batch_id) \
                .order("created_at", asc=True).execute()
            return result.data or []
        except Exception as e:
            logger.warning(f"[BatchService] Failed to get clip results: {e}")
            return []

    async def cancel_batch_job(self, batch_id: str) -> bool:
        """Cancel a running batch job."""
        try:
            job = await self.get_batch_job(batch_id)
            if not job or job.get("status") not in ("queued", "running"):
                return False
            
            supabase.table("swarm_batch_jobs").update({
                "status": "cancelled",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("batch_id", batch_id).execute()
            
            # Cancel any running tasks
            if batch_id in self._running_batches:
                task = self._running_batches[batch_id]
                if not task.done():
                    task.cancel()
                del self._running_batches[batch_id]
            
            # Decrement rate limit counter
            await self._decrement_user_batch_count(job.get("user_id"))
            
            return True
        except Exception as e:
            logger.warning(f"[BatchService] Failed to cancel batch: {e}")
            return False

    # ─────────────────────────────────────────────────────────────
    # Scale Features (Phase 3)
    # ─────────────────────────────────────────────────────────────

    async def _check_rate_limits(self, user_id: str, clip_count: int) -> tuple[bool, str]:
        """Check if user is within rate limits.
        
        Returns (allowed, reason).
        """
        cache = CacheService()
        
        # Check concurrent batches
        active_key = f"user:{user_id}:active_batches"
        active_count = await cache.get(active_key) or 0
        
        if active_count >= MAX_CONCURRENT_BATCHES:
            return False, f"Maximum {MAX_CONCURRENT_BATCHES} concurrent batches reached"
        
        # Check daily clip limit
        daily_key = f"user:{user_id}:daily_clips"
        daily_count = await cache.get(daily_key) or 0
        
        if daily_count + clip_count > MAX_DAILY_CLIPS:
            return False, f"Daily clip limit ({MAX_DAILY_CLIPS}) would be exceeded"
        
        return True, ""

    async def _increment_user_batch_count(self, user_id: str, clip_count: int):
        """Increment user's active batch and daily clip counters."""
        cache = CacheService()
        
        # Increment concurrent batches
        active_key = f"user:{user_id}:active_batches"
        active = await cache.get(active_key) or 0
        await cache.set(active_key, active + 1, ttl_seconds=86400)
        
        # Increment daily clips
        daily_key = f"user:{user_id}:daily_clips"
        daily = await cache.get(daily_key) or 0
        await cache.set(daily_key, daily + clip_count, ttl_seconds=86400)

    async def _decrement_user_batch_count(self, user_id: str):
        """Decrement user's active batch counter."""
        cache = CacheService()
        active_key = f"user:{user_id}:active_batches"
        active = await cache.get(active_key) or 0
        
        if active > 0:
            await cache.set(active_key, active - 1, ttl_seconds=86400)

    def _partition_clips(self, clips: List[str]) -> List[List[str]]:
        """Partition clips into waves for large batches.
        
        Each wave contains at most WAVE_SIZE clips.
        """
        if len(clips) <= WAVE_SIZE:
            return [clips]
        
        return [clips[i:i + WAVE_SIZE] for i in range(0, len(clips), WAVE_SIZE)]

    async def _execute_with_retry(
        self,
        batch_id: str,
        clip_id: str,
        pool_type: str,
        user_id: str,
        agent_count: int,
        strategy_filter: Optional[List[str]],
        shared_context: Optional[dict],
        custom_options: Optional[Dict[str, Any]],
        progress_callback = None,
    ) -> Dict[str, Any]:
        """Execute a single clip with retry logic.
        
        Retries up to MAX_RETRIES times with exponential backoff.
        """
        for attempt in range(MAX_RETRIES + 1):
            result = await self._execute_single_clip(
                batch_id, clip_id, pool_type, user_id, agent_count,
                strategy_filter, shared_context, custom_options
            )
            
            if result.get("status") == "completed" or attempt >= MAX_RETRIES:
                # Add retry metadata
                if attempt > 0:
                    result["retries"] = attempt
                    result["retry_note"] = f"Succeeded after {attempt} retries"
                return result
            
            # Failed — wait before retry
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            logger.info(
                f"[BatchService] Retry {attempt + 1}/{MAX_RETRIES} for clip {clip_id} "
                f"in batch {batch_id} (delay={delay}s)"
            )
            
            if progress_callback:
                try:
                    await progress_callback(
                        batch_id=batch_id,
                        processed=0,
                        total=1,
                        failed=0,
                        current_clip=clip_id,
                        current_status="retrying",
                        detail=f"Retrying clip (attempt {attempt + 1}/{MAX_RETRIES})",
                    )
                except Exception:
                    pass
            
            await asyncio.sleep(delay)
        
        return result  # Return last failure

    async def _execute_wave(
        self,
        wave_num: int,
        total_waves: int,
        batch_id: str,
        clips: List[str],
        pool_type: str,
        user_id: str,
        agent_count: int,
        strategy_filter: Optional[List[str]],
        batch_contexts: Dict[str, Any],
        clip_segments: Dict[str, Any],
        custom_options: Optional[Dict[str, Any]],
        priority: str,
        progress_callback = None,
        clip_result_callback = None,
    ) -> List[Dict[str, Any]]:
        """Execute a single wave of clips.
        
        Uses priority-based execution strategy within the wave.
        """
        logger.info(
            f"[BatchService] Wave {wave_num}/{total_waves}: "
            f"{len(clips)} clips, priority={priority}"
        )
        
        exec_kwargs = {
            "batch_id": batch_id,
            "pool_type": pool_type,
            "user_id": user_id,
            "agent_count": agent_count,
            "strategy_filter": strategy_filter,
            "batch_contexts": batch_contexts,
            "clip_segments": clip_segments,
            "custom_options": custom_options,
            "progress_callback": progress_callback,
            "clip_result_callback": clip_result_callback,
        }
        
        if priority == "cost":
            return await self._execute_sequential(clip_ids=clips, **exec_kwargs)
        elif priority == "speed":
            return await self._execute_parallel(clip_ids=clips, **exec_kwargs)
        else:
            # Balanced: parallel but with concurrency limit
            return await self._execute_balanced(clip_ids=clips, **exec_kwargs)

    # ─────────────────────────────────────────────────────────────
    # Batch Templates
    # ─────────────────────────────────────────────────────────────

    async def create_template(
        self,
        user_id: str,
        name: str,
        pool_type: str,
        agent_count: int,
        strategy_filter: Optional[List[str]] = None,
        priority: str = "balanced",
        shared_context: bool = True,
        custom_options: Optional[Dict[str, Any]] = None,
        is_default: bool = False,
    ) -> Dict[str, Any]:
        """Create a batch configuration template."""
        from app.models import SwarmBatchTemplate
        
        template = SwarmBatchTemplate(
            template_id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            pool_type=SwarmJobType(pool_type),
            agent_count=agent_count,
            strategy_filter=strategy_filter,
            priority=priority,
            shared_context=shared_context,
            custom_options=custom_options or {},
            is_default=is_default,
        )
        
        try:
            supabase.table("swarm_batch_templates").insert(
                template.model_dump(mode="json")
            ).execute()
            
            # If setting as default, unset others
            if is_default:
                supabase.table("swarm_batch_templates").update({
                    "is_default": False
                }).eq("user_id", user_id).neq("template_id", template.template_id).execute()
            
            return {"template_id": template.template_id, "success": True}
        except Exception as e:
            logger.warning(f"[BatchService] Failed to create template: {e}")
            return {"error": str(e), "success": False}

    async def list_templates(self, user_id: str) -> List[Dict[str, Any]]:
        """List all batch templates for a user."""
        try:
            result = supabase.table("swarm_batch_templates").select("*") \
                .eq("user_id", user_id) \
                .order("is_default", desc=True) \
                .order("created_at", desc=True).execute()
            return result.data or []
        except Exception as e:
            logger.warning(f"[BatchService] Failed to list templates: {e}")
            return []

    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a single template by ID."""
        try:
            result = supabase.table("swarm_batch_templates").select("*") \
                .eq("template_id", template_id).single().execute()
            return result.data
        except Exception as e:
            logger.debug(f"[BatchService] Template not found: {e}")
            return None

    async def delete_template(self, template_id: str, user_id: str) -> bool:
        """Delete a template."""
        try:
            # Verify ownership
            template = await self.get_template(template_id)
            if not template or template.get("user_id") != user_id:
                return False
            
            supabase.table("swarm_batch_templates").delete() \
                .eq("template_id", template_id).execute()
            return True
        except Exception as e:
            logger.warning(f"[BatchService] Failed to delete template: {e}")
            return False

    # ─────────────────────────────────────────────────────────────
    # Queue-based Async Execution
    # ─────────────────────────────────────────────────────────────

    async def enqueue_batch(
        self,
        clip_ids: List[str],
        pool_type: str,
        user_id: str,
        agent_count: Optional[int] = None,
        strategy_filter: Optional[List[str]] = None,
        priority: str = "balanced",
        top_k: Optional[int] = None,
        shared_context: bool = True,
        custom_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Enqueue a batch job for async background processing.
        
        Creates the batch job record and adds it to the Redis queue.
        Returns immediately with the batch_id for polling.
        """
        from app.services.queue import QueueService
        
        batch_id = str(uuid.uuid4())
        
        # Validate
        valid_pools = [
            "hook", "remix", "post", "ab_test", "music_match",
            "thumbnail", "safety", "hooks_analysis", "segment_analyze", "edit"
        ]
        if pool_type not in valid_pools:
            return {"error": f"Invalid pool_type: {pool_type}", "batch_id": None}
        
        # Get user config for allocation
        config = await SwarmConfigService.get_config(user_id)
        allocated = config.get_pool_agents(pool_type)
        requested = agent_count if agent_count is not None else allocated
        per_clip_agents = min(requested, allocated)
        
        if per_clip_agents <= 0:
            return {"error": f"{pool_type} swarm disabled or limit reached", "batch_id": None}
        
        if pool_type not in config.enabled_pools:
            return {"error": f"{pool_type} swarm pool disabled", "batch_id": None}
        
        # Apply top-k
        clips_to_process = clip_ids
        if top_k and top_k < len(clip_ids):
            clips_to_process = clip_ids[:top_k]
        
        total_clips = len(clips_to_process)
        total_agents = per_clip_agents * total_clips
        
        # Check rate limits
        allowed, reason = await self._check_rate_limits(user_id, total_clips)
        if not allowed:
            return {"error": reason, "batch_id": None}
        
        # Check budget
        batch_cost = calculate_batch_cost(pool_type, total_clips, per_clip_agents)
        if not await SwarmConfigService.check_budget(user_id, pool_type, total_agents):
            return {"error": "Daily budget exceeded for batch operation", "batch_id": None}
        
        # Increment rate limit counters
        await self._increment_user_batch_count(user_id, total_clips)
        
        # Create batch job record as queued
        batch_job = SwarmBatchJob(
            batch_id=batch_id,
            user_id=user_id,
            pool_type=SwarmJobType(pool_type),
            clip_ids=clips_to_process,
            total_clips=total_clips,
            processed_clips=0,
            failed_clips=0,
            status=SwarmBatchJobStatus.queued,
            agent_count=per_clip_agents,
            strategy_filter=strategy_filter,
            custom_options=custom_options,
            cost_cents=batch_cost,
            results_summary={
                "estimated_cost_cents": batch_cost,
                "priority": priority,
                "shared_context": shared_context,
                "waves": len(self._partition_clips(clips_to_process)),
            },
        )
        
        try:
            supabase.table("swarm_batch_jobs").insert(batch_job.model_dump(mode="json")).execute()
        except Exception as e:
            logger.warning(f"[BatchService] Failed to create batch job record: {e}")
            return {"error": f"Failed to create batch job: {e}", "batch_id": None}
        
        # Enqueue to Redis
        queue = QueueService()
        job_data = {
            "job_id": batch_id,
            "batch_id": batch_id,
            "clip_ids": clips_to_process,
            "pool_type": pool_type,
            "user_id": user_id,
            "agent_count": per_clip_agents,
            "strategy_filter": strategy_filter,
            "priority": priority,
            "shared_context": shared_context,
            "custom_options": custom_options,
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            await queue.enqueue_with_priority("swarm_batch", job_data, priority=PRIORITY_SCORES.get(priority, 50))
        except Exception as e:
            logger.error(f"[BatchService] Failed to enqueue batch job: {e}")
            # Rollback: mark as failed
            try:
                supabase.table("swarm_batch_jobs").update({
                    "status": "failed",
                    "error": f"Enqueue failed: {e}",
                }).eq("batch_id", batch_id).execute()
            except:
                pass
            return {"error": f"Failed to enqueue batch: {e}", "batch_id": None}
        
        # Calculate savings preview
        individual_cost = calculate_individual_cost(pool_type, total_clips, per_clip_agents)
        savings_pct = round((1 - batch_cost / max(individual_cost, 1)) * 100, 1) if individual_cost > 0 else 0
        
        logger.info(
            f"[BatchService] Enqueued batch {batch_id}: "
            f"{total_clips} clips, pool={pool_type}, priority={priority}"
        )
        
        return {
            "batch_id": batch_id,
            "pool_type": pool_type,
            "total_clips": total_clips,
            "processed_clips": 0,
            "failed_clips": 0,
            "status": "queued",
            "results": [],
            "cost_cents": batch_cost,
            "estimated_cost_usd": round(batch_cost / 100, 2),
            "savings_percent": savings_pct,
            "duration_ms": 0,
            "created_at": batch_job.created_at.isoformat(),
            "completed_at": None,
            "message": f"Batch queued with {total_clips} clips. Processing will begin shortly.",
        }

    async def estimate_batch_cost(self, batch_id: str) -> Dict[str, Any]:
        """Estimate cost for a batch job."""
        job = await self.get_batch_job(batch_id)
        if not job:
            return {"error": "Batch job not found"}
        
        pool_type = job.get("pool_type")
        total_clips = job.get("total_clips", 0)
        agent_count = job.get("agent_count", 1)
        
        batch_cost = calculate_batch_cost(pool_type, total_clips, agent_count)
        individual_cost = calculate_individual_cost(pool_type, total_clips, agent_count)
        savings_pct = round((1 - batch_cost / max(individual_cost, 1)) * 100, 1)
        
        return {
            "batch_id": batch_id,
            "pool_type": pool_type,
            "total_clips": total_clips,
            "agent_count": agent_count,
            "batch_cost_cents": batch_cost,
            "batch_cost_usd": round(batch_cost / 100, 2),
            "individual_cost_cents": individual_cost,
            "individual_cost_usd": round(individual_cost / 100, 2),
            "savings_cents": individual_cost - batch_cost,
            "savings_percent": savings_pct,
            "pricing": BATCH_COSTS.get(pool_type, {}),
        }
