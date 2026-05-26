"""
Pipeline State Machine Models
Replaces inline LangGraph execution with durable, trackable state transitions.
Each clip progresses through discrete stages; state is persisted to PostgreSQL.
"""
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
import json
import uuid


class PipelineStage(str, Enum):
    QUEUED = "queued"
    DOWNLOAD = "download"
    EXTRACT_AUDIO = "extract_audio"
    TRANSCRIBE = "transcribe"
    DETECT_SEGMENTS = "detect_segments"
    GENERATE_CLIPS = "generate_clips"
    SAFETY_CHECK = "safety_check"
    ENRICH_CONTENT = "enrich_content"
    CREATE_THUMBNAILS = "create_thumbnails"
    UPLOAD_ASSETS = "upload_assets"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

    @classmethod
    def ordered_stages(cls) -> List["PipelineStage"]:
        return [
            cls.QUEUED, cls.DOWNLOAD, cls.EXTRACT_AUDIO, cls.TRANSCRIBE,
            cls.DETECT_SEGMENTS, cls.GENERATE_CLIPS, cls.SAFETY_CHECK,
            cls.ENRICH_CONTENT, cls.CREATE_THUMBNAILS, cls.UPLOAD_ASSETS, cls.COMPLETED,
        ]

    def next_stage(self) -> Optional["PipelineStage"]:
        ordered = self.ordered_stages()
        try:
            idx = ordered.index(self)
            return ordered[idx + 1] if idx + 1 < len(ordered) else None
        except ValueError:
            return None

    @property
    def queue_name(self) -> str:
        mapping = {
            self.DOWNLOAD: "pipeline.download", self.EXTRACT_AUDIO: "pipeline.transcribe",
            self.TRANSCRIBE: "pipeline.transcribe", self.DETECT_SEGMENTS: "pipeline.segment",
            self.GENERATE_CLIPS: "pipeline.generate", self.SAFETY_CHECK: "pipeline.safety",
            self.ENRICH_CONTENT: "pipeline.enrich", self.CREATE_THUMBNAILS: "pipeline.thumbnail",
            self.UPLOAD_ASSETS: "pipeline.upload",
        }
        return mapping.get(self, "pipeline.download")


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class StageExecution:
    stage: str
    attempt_number: int = 1
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    duration_ms: Optional[int] = None
    worker_id: Optional[str] = None
    cost_usd: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        for key in ["started_at", "completed_at"]:
            if data.get(key):
                data[key] = data[key].isoformat()
        return data


@dataclass
class PipelineState:
    clip_id: str
    source_id: str
    pipeline_id: str
    user_id: str
    current_stage: PipelineStage = PipelineStage.QUEUED
    status: PipelineStatus = PipelineStatus.PENDING
    stage_history: List[StageExecution] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_cost_usd: float = 0.0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    transcription: Optional[Dict[str, Any]] = None
    segments: Optional[List[Dict[str, Any]]] = None
    generated_clips: Optional[List[Dict[str, Any]]] = None
    safety_result: Optional[Dict[str, Any]] = None
    thumbnails: Optional[List[str]] = None
    r2_urls: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def transition_to(self, stage: PipelineStage, worker_id: Optional[str] = None) -> StageExecution:
        self.current_stage = stage
        if self.status not in (PipelineStatus.RUNNING, PipelineStatus.RETRYING):
            self.status = PipelineStatus.RUNNING
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc)
        execution = StageExecution(
            stage=stage.value, attempt_number=self.retry_count + 1,
            started_at=datetime.now(timezone.utc), status="running", worker_id=worker_id
        )
        self.stage_history.append(execution)
        return execution

    def mark_stage_success(self, stage: PipelineStage, cost_usd: float = 0.0,
                           tokens_in: int = 0, tokens_out: int = 0,
                           metadata_update: Optional[Dict[str, Any]] = None) -> None:
        now = datetime.now(timezone.utc)
        for exec_record in reversed(self.stage_history):
            if exec_record.stage == stage.value and exec_record.status == "running":
                exec_record.status = "success"
                exec_record.completed_at = now
                if exec_record.started_at:
                    exec_record.duration_ms = int((now - exec_record.started_at).total_seconds() * 1000)
                exec_record.cost_usd = cost_usd
                self.total_cost_usd += cost_usd
                self.total_tokens_input += tokens_in
                self.total_tokens_output += tokens_out
                break
        if metadata_update:
            self.metadata.update(metadata_update)
        next_stage = stage.next_stage()
        if next_stage:
            self.current_stage = next_stage
        else:
            self.status = PipelineStatus.COMPLETED
            self.completed_at = now

    def mark_stage_failed(self, stage: PipelineStage, error_message: str,
                          error_type: str = "unknown", retryable: bool = True) -> None:
        now = datetime.now(timezone.utc)
        for exec_record in reversed(self.stage_history):
            if exec_record.stage == stage.value and exec_record.status == "running":
                exec_record.status = "failed"
                exec_record.completed_at = now
                exec_record.error_message = error_message
                exec_record.error_type = error_type
                if exec_record.started_at:
                    exec_record.duration_ms = int((now - exec_record.started_at).total_seconds() * 1000)
                break
        if retryable and self.retry_count < self.max_retries:
            self.status = PipelineStatus.RETRYING
            self.retry_count += 1
        else:
            self.status = PipelineStatus.FAILED
            self.completed_at = now

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["current_stage"] = self.current_stage.value
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["started_at"] = self.started_at.isoformat() if self.started_at else None
        data["completed_at"] = self.completed_at.isoformat() if self.completed_at else None
        data["stage_history"] = [h.to_dict() for h in self.stage_history]
        return data
