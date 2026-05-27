"""
Batch API Service — 50% Cost Reduction for Overnight Processing (Phase 4)

OpenAI and DeepSeek offer batch APIs at 50% discount with 24-hour turnaround.
This service manages the full batch lifecycle: submission, polling, and result
retrieval for high-volume, non-real-time tasks.

Eligible tasks (non-real-time, high volume):
  - safety_check, hashtag_optimize, thumbnail_text, music_match,
    moderation_classify, content_enrich, metadata_extract

Usage:
    batch = BatchAPIService()
    job_id = await batch.submit("safety_check", prompts=["text1", "text2", ...])
    # ... up to 24 hours later ...
    results = await batch.retrieve_results(job_id)
"""
from __future__ import annotations

import logging
import json
import os
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class BatchJobStatus(str, Enum):
    SUBMITTED = "submitted"
    VALIDATING = "validating"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"


@dataclass
class BatchJob:
    """Represents a batch API job."""
    job_id: str
    task_type: str
    model_used: str
    provider: str
    total_requests: int
    status: BatchJobStatus = BatchJobStatus.SUBMITTED
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    api_job_id: Optional[str] = None
    results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    estimated_cost_usd: float = 0.0
    actual_cost_usd: float = 0.0
    discount_applied: float = 0.5  # 50% off

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "task_type": self.task_type,
            "model_used": self.model_used,
            "provider": self.provider,
            "total_requests": self.total_requests,
            "status": self.status.value,
            "submitted_at": self.submitted_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
            "actual_cost_usd": round(self.actual_cost_usd, 4),
            "savings_usd": round(self.estimated_cost_usd - self.actual_cost_usd, 4),
            "results_count": len(self.results),
            "errors_count": len(self.errors),
        }


class BatchAPIService:
    """Manage batch API jobs for cost-efficient overnight processing.

    Providers supporting batch APIs:
      - OpenAI: 50% discount, 24h SLA
      - DeepSeek: 50% discount, 24h SLA
      - Anthropic: 50% discount (limited beta)

    Ineligible (real-time only):
      - hook_generate, edit_instructions (PREMIUM creative tasks)
      - caption_generate (user-facing, needs immediate response)
    """

    # Tasks eligible for batch processing (all ECONOMY + some STANDARD)
    # Must exist in TASK_MODEL_MAP with ECONOMY or STANDARD tier
    ELIGIBLE_TASKS = {
        "safety_check", "hashtag_optimize", "thumbnail_text",
        "music_match", "moderation_classify", "content_enrich",
        "ab_test_variants", "transcription_route",
    }

    # Provider batch API endpoints
    BATCH_ENDPOINTS = {
        "openai": "https://api.openai.com/v1/batches",
        "deepseek": "https://api.deepseek.com/v1/batches",
    }

    def __init__(self, redis_client=None):
        self._jobs: Dict[str, BatchJob] = {}
        self.redis = redis_client

    def is_eligible(self, task_type: str) -> bool:
        """Check if a task type is eligible for batch API processing."""
        return task_type in self.ELIGIBLE_TASKS

    async def submit(self, task_type: str, prompts: List[str],
                     system_prompt: Optional[str] = None,
                     temperature: float = 0.5,
                     model_override: Optional[str] = None) -> str:
        """Submit a batch job for overnight processing.

        Args:
            task_type: The LLMRouter task type
            prompts: List of prompts to process
            system_prompt: Optional system prompt for all requests
            temperature: Sampling temperature
            model_override: Force a specific model

        Returns:
            job_id: Internal job ID for status tracking
        """
        if not self.is_eligible(task_type):
            raise ValueError(f"Task '{task_type}' is not eligible for batch API. "
                           f"Eligible: {self.ELIGIBLE_TASKS}")

        if not prompts:
            raise ValueError("No prompts provided for batch processing")

        job_id = str(uuid.uuid4())

        # Select model via router
        from app.services.llm_router import get_router
        router = get_router()
        model_cfg = router.select_model(task_type, force_model=model_override)

        if not model_cfg.supports_batch:
            logger.warning(f"[Batch] Model {model_cfg.model_id} may not support batch API. "
                          "Falling back to parallel individual calls.")
            return await self._fallback_parallel(task_type, prompts, system_prompt, temperature, job_id)

        # Create batch file (OpenAI format)
        batch_file_id = await self._upload_batch_file(
            model_cfg, prompts, system_prompt, temperature
        )

        # Submit batch job to provider
        api_job_id = await self._submit_to_provider(model_cfg, batch_file_id)

        # Track job
        estimated_cost = model_cfg.estimate_cost_usd(
            sum(len(p) for p in prompts),  # rough token estimate
            model_cfg.avg_output_tokens * len(prompts)
        ) * 0.5  # 50% discount

        job = BatchJob(
            job_id=job_id, task_type=task_type,
            model_used=model_cfg.model_id, provider=model_cfg.provider,
            total_requests=len(prompts),
            api_job_id=api_job_id,
            estimated_cost_usd=estimated_cost,
            status=BatchJobStatus.SUBMITTED,
        )
        self._jobs[job_id] = job

        logger.info(f"[Batch] Submitted {task_type} job: {job_id} "
                   f"requests={len(prompts)} model={model_cfg.model_id} "
                   f"est_cost=${estimated_cost:.4f} (50% off)")

        return job_id

    async def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a batch job."""
        job = self._jobs.get(job_id)
        if not job:
            return None

        # Poll provider for updated status
        if job.api_job_id and job.status not in (BatchJobStatus.COMPLETED, BatchJobStatus.FAILED):
            await self._poll_provider_status(job)

        return job.to_dict()

    async def retrieve_results(self, job_id: str) -> List[Dict[str, Any]]:
        """Retrieve completed batch results.

        Polls the provider API until the job completes (or times out).
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Unknown batch job: {job_id}")

        if job.status == BatchJobStatus.COMPLETED and job.results:
            return job.results

        # Poll until complete (with timeout)
        max_wait_hours = 24
        check_interval_seconds = 300  # 5 minutes
        max_checks = (max_wait_hours * 3600) // check_interval_seconds

        for check in range(max_checks):
            await self._poll_provider_status(job)

            if job.status == BatchJobStatus.COMPLETED:
                await self._download_results(job)
                logger.info(f"[Batch] Job {job_id} completed: "
                           f"results={len(job.results)} errors={len(job.errors)} "
                           f"cost=${job.actual_cost_usd:.4f}")
                return job.results

            if job.status == BatchJobStatus.FAILED:
                logger.error(f"[Batch] Job {job_id} failed")
                raise RuntimeError(f"Batch job {job_id} failed")

            await asyncio.sleep(check_interval_seconds)

        raise TimeoutError(f"Batch job {job_id} did not complete within {max_wait_hours} hours")

    async def list_jobs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all batch jobs, optionally filtered by status."""
        jobs = self._jobs.values()
        if status:
            jobs = [j for j in jobs if j.status.value == status]
        return [j.to_dict() for j in sorted(jobs, key=lambda x: x.submitted_at, reverse=True)]

    # ------------------------------------------------------------------
    # Provider API Integration
    # ------------------------------------------------------------------

    async def _upload_batch_file(self, model_cfg, prompts: List[str],
                                 system_prompt: Optional[str], temperature: float) -> str:
        """Upload a JSONL batch file to the provider."""
        import httpx

        api_key = os.environ.get(model_cfg.env_key, "")
        lines = []
        for i, prompt in enumerate(prompts):
            request = {
                "custom_id": f"request-{i}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": model_cfg.model_id,
                    "messages": [
                        *( [{"role": "system", "content": system_prompt}] if system_prompt else [] ),
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": model_cfg.max_output_tokens,
                }
            }
            lines.append(json.dumps(request))

        jsonl_content = "\n".join(lines)

        # Upload file
        upload_url = "https://api.openai.com/v1/files" if model_cfg.provider == "openai" else \
                     "https://api.deepseek.com/v1/files"

        headers = {"Authorization": f"Bearer {api_key}"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                upload_url,
                headers=headers,
                data={"purpose": "batch"},
                files={"file": ("batch.jsonl", jsonl_content, "application/jsonl")},
            )
            resp.raise_for_status()
            return resp.json()["id"]

    async def _submit_to_provider(self, model_cfg, batch_file_id: str) -> str:
        """Submit the batch job to the provider."""
        import httpx

        api_key = os.environ.get(model_cfg.env_key, "")
        endpoint = self.BATCH_ENDPOINTS.get(model_cfg.provider)
        if not endpoint:
            raise ValueError(f"No batch endpoint for provider: {model_cfg.provider}")

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "input_file_id": batch_file_id,
            "endpoint": "/v1/chat/completions",
            "completion_window": "24h",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["id"]

    async def _poll_provider_status(self, job: BatchJob) -> None:
        """Poll the provider for updated job status."""
        import httpx

        if not job.api_job_id:
            return

        endpoint = self.BATCH_ENDPOINTS.get(job.provider)
        if not endpoint:
            return

        api_key = os.environ.get(
            "OPENAI_API_KEY" if job.provider == "openai" else "DEEPSEEK_API_KEY", ""
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{endpoint}/{job.api_job_id}",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()

                status_map = {
                    "validating": BatchJobStatus.VALIDATING,
                    "in_progress": BatchJobStatus.IN_PROGRESS,
                    "finalizing": BatchJobStatus.IN_PROGRESS,
                    "completed": BatchJobStatus.COMPLETED,
                    "failed": BatchJobStatus.FAILED,
                    "expired": BatchJobStatus.EXPIRED,
                    "cancelling": BatchJobStatus.CANCELLING,
                    "cancelled": BatchJobStatus.CANCELLED,
                }

                new_status = status_map.get(data.get("status"), job.status)
                if new_status != job.status:
                    job.status = new_status
                    logger.info(f"[Batch] Job {job.job_id} status: {new_status.value}")

                # Track cost if available
                if data.get("request_counts"):
                    counts = data["request_counts"]
                    completed = counts.get("completed", 0)
                    failed = counts.get("failed", 0)
                    job.results = [{"status": "completed"}] * completed
                    job.errors = [{"status": "failed"}] * failed

        except Exception as e:
            logger.warning(f"[Batch] Status poll failed for {job.job_id}: {e}")

    async def _download_results(self, job: BatchJob) -> None:
        """Download completed batch results from provider."""
        import httpx

        if not job.api_job_id:
            return

        endpoint = self.BATCH_ENDPOINTS.get(job.provider)
        if not endpoint:
            return

        api_key = os.environ.get(
            "OPENAI_API_KEY" if job.provider == "openai" else "DEEPSEEK_API_KEY", ""
        )

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(
                    f"{endpoint}/{job.api_job_id}",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()

                if data.get("output_file_id"):
                    file_resp = await client.get(
                        f"https://api.openai.com/v1/files/{data['output_file_id']}/content"
                        if job.provider == "openai" else
                        f"https://api.deepseek.com/v1/files/{data['output_file_id']}/content",
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    file_resp.raise_for_status()

                    results = []
                    for line in file_resp.text.strip().split("\n"):
                        if line:
                            results.append(json.loads(line))
                    job.results = results

                job.completed_at = datetime.now(timezone.utc)
                job.actual_cost_usd = float(data.get("cost", {}).get("total_tokens", 0)) * 0.000002  # rough estimate

        except Exception as e:
            logger.error(f"[Batch] Result download failed for {job.job_id}: {e}")

    async def _fallback_parallel(self, task_type: str, prompts: List[str],
                                  system_prompt: Optional[str], temperature: float,
                                  job_id: str) -> str:
        """Fallback: process batch via parallel individual calls (no 50% discount)."""
        from app.services.llm_router import get_router
        router = get_router()

        logger.info(f"[Batch] Using parallel fallback for {len(prompts)} prompts")

        results = await router.call_batch(task_type, prompts, system_prompt, temperature)

        job = BatchJob(
            job_id=job_id, task_type=task_type,
            model_used="parallel_fallback", provider="none",
            total_requests=len(prompts),
            status=BatchJobStatus.COMPLETED,
            results=[r if isinstance(r, dict) else {"error": str(r)} for r in results],
            discount_applied=0.0,
        )
        self._jobs[job_id] = job

        return job_id


# Singleton
_batch_service: Optional[BatchAPIService] = None


def get_batch_service(redis_client=None) -> BatchAPIService:
    global _batch_service
    if _batch_service is None:
        _batch_service = BatchAPIService(redis_client=redis_client)
    return _batch_service
