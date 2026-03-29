"""
Domain models for the Distributed Workflow Orchestrator.
Strict job lifecycle: pending -> running -> completed | failed -> retrying -> pending
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from enum import Enum
from datetime import datetime, timezone
import uuid


class JobType(str, Enum):
    COMPUTE = "compute"
    PIPELINE = "pipeline"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class Job(BaseModel):
    """Core job entity with full lifecycle tracking."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    type: JobType
    status: JobStatus = JobStatus.PENDING
    retries: int = 0
    max_retries: int = 3
    worker_id: Optional[str] = None
    error_message: Optional[str] = None
    pipeline_stage: Optional[str] = None
    execution_time: Optional[float] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None


class JobCreate(BaseModel):
    """Request body for creating a new job."""
    name: str
    type: JobType = JobType.COMPUTE
    max_retries: int = 3


class JobMetrics(BaseModel):
    """System-wide job metrics for observability."""
    total_jobs: int = 0
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    retrying: int = 0
    success_rate: float = 0.0
    failure_rate: float = 0.0
    avg_execution_time: float = 0.0
    total_retries: int = 0
    worker_count: int = 0
    uptime_seconds: float = 0.0


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    system: str
    version: str
    workers_active: int
    queue_depth: int
    uptime_seconds: float


class LogEntry(BaseModel):
    """Structured log entry."""
    timestamp: str
    level: str
    source: str
    message: str
    job_id: Optional[str] = None
    worker_id: Optional[str] = None


class WSMessage(BaseModel):
    """WebSocket message envelope."""
    event: str
    data: dict
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
