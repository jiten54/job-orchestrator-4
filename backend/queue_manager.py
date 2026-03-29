"""
Job Queue Manager - In-memory queue system with retry support.
Manages job lifecycle, state transitions, and broadcasts updates via WebSocket.
Designed as a drop-in replacement point for Redis/Kafka in production.
"""
import asyncio
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional
from models import Job, JobStatus, JobType, JobMetrics, LogEntry
from config import LOG_BUFFER_SIZE
import json
import logging

logger = logging.getLogger("queue_manager")


class ConnectionManager:
    """WebSocket connection manager for broadcasting real-time updates."""

    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected WebSocket clients."""
        dead = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead.append(conn)
        for conn in dead:
            self.disconnect(conn)


class JobQueueManager:
    """
    Central job queue with state management.
    In-memory implementation — production would use Redis Streams or Kafka topics.
    Thread-safe via asyncio locks.
    """

    def __init__(self, ws_manager: ConnectionManager):
        self.jobs: Dict[str, Job] = {}
        self.pending_queue: deque = deque()
        self.retry_queue: deque = deque()
        self.log_buffer: deque = deque(maxlen=LOG_BUFFER_SIZE)
        self.ws_manager = ws_manager
        self._lock = asyncio.Lock()
        self.start_time = datetime.now(timezone.utc)
        # Idempotency tracking: set of job IDs currently being processed
        self._processing: set = set()

    async def add_job(self, job: Job) -> Job:
        """Add a new job to the pending queue."""
        async with self._lock:
            self.jobs[job.id] = job
            self.pending_queue.append(job.id)

        await self._log("INFO", "queue_manager", f"Job {job.id} ({job.type.value}) enqueued", job_id=job.id)
        await self._broadcast_event("job_created", job)
        return job

    async def dequeue_job(self) -> Optional[Job]:
        """Pull next job from pending queue. Returns None if empty."""
        async with self._lock:
            if not self.pending_queue:
                return None
            job_id = self.pending_queue.popleft()
            # Idempotency check: skip if already being processed
            if job_id in self._processing:
                return None
            job = self.jobs.get(job_id)
            if job and job.status == JobStatus.PENDING:
                self._processing.add(job_id)
                return job
            return None

    async def update_job_status(self, job_id: str, status: JobStatus,
                                 worker_id: str = None, error: str = None,
                                 pipeline_stage: str = None, execution_time: float = None):
        """Transition job to new state with full audit trail."""
        async with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return
            job.status = status
            job.updated_at = datetime.now(timezone.utc).isoformat()
            if worker_id:
                job.worker_id = worker_id
            if error:
                job.error_message = error
            if pipeline_stage:
                job.pipeline_stage = pipeline_stage
            if execution_time is not None:
                job.execution_time = execution_time
            if status == JobStatus.COMPLETED:
                job.completed_at = datetime.now(timezone.utc).isoformat()
                self._processing.discard(job_id)
            elif status == JobStatus.FAILED:
                self._processing.discard(job_id)

        level = "ERROR" if status == JobStatus.FAILED else "INFO"
        msg = f"Job {job_id} -> {status.value}"
        if error:
            msg += f" | {error}"
        if pipeline_stage:
            msg += f" | stage: {pipeline_stage}"
        await self._log(level, "state_machine", msg, job_id=job_id, worker_id=worker_id)
        await self._broadcast_event("job_updated", job)

    async def enqueue_retry(self, job_id: str):
        """Move a failed job to retry queue if within retry limits."""
        async with self._lock:
            job = self.jobs.get(job_id)
            if not job or job.retries >= job.max_retries:
                return False
            job.retries += 1
            job.status = JobStatus.RETRYING
            job.updated_at = datetime.now(timezone.utc).isoformat()
            job.error_message = None
            self.retry_queue.append(job_id)

        await self._log("WARNING", "retry_engine", f"Job {job_id} queued for retry ({job.retries}/{job.max_retries})", job_id=job_id)
        await self._broadcast_event("job_retrying", job)
        return True

    async def process_retry_queue(self):
        """Move jobs from retry queue back to pending queue."""
        moved = 0
        async with self._lock:
            while self.retry_queue:
                job_id = self.retry_queue.popleft()
                job = self.jobs.get(job_id)
                if job:
                    job.status = JobStatus.PENDING
                    job.updated_at = datetime.now(timezone.utc).isoformat()
                    self.pending_queue.append(job_id)
                    moved += 1
        if moved > 0:
            await self._log("INFO", "retry_engine", f"Moved {moved} jobs from retry queue to pending")
        return moved

    async def retry_all_failed(self) -> int:
        """Retry all permanently failed jobs (exceeded max retries)."""
        count = 0
        async with self._lock:
            for job in self.jobs.values():
                if job.status == JobStatus.FAILED and job.retries >= job.max_retries:
                    job.retries = 0
                    job.status = JobStatus.PENDING
                    job.error_message = None
                    job.updated_at = datetime.now(timezone.utc).isoformat()
                    self.pending_queue.append(job.id)
                    count += 1
        if count > 0:
            await self._log("WARNING", "recovery", f"Reset and re-enqueued {count} permanently failed jobs")
            await self._broadcast_event("bulk_retry", {"count": count})
        return count

    async def auto_recovery(self) -> dict:
        """
        Auto-recovery: retries all eligible failed jobs and processes retry queue.
        Simulates a circuit-breaker reset.
        """
        retried = await self.retry_all_failed()
        moved = await self.process_retry_queue()
        await self._log("INFO", "recovery", f"Auto-recovery complete: {retried} reset, {moved} requeued")
        return {"reset_jobs": retried, "requeued_jobs": moved}

    def get_jobs(self, status: str = None, job_type: str = None) -> List[dict]:
        """Get all jobs with optional filtering. Returns dicts safe for JSON."""
        jobs = list(self.jobs.values())
        if status:
            jobs = [j for j in jobs if j.status.value == status]
        if job_type:
            jobs = [j for j in jobs if j.type.value == job_type]
        # Sort by updated_at descending
        jobs.sort(key=lambda j: j.updated_at, reverse=True)
        return [j.model_dump() for j in jobs]

    def get_job(self, job_id: str) -> Optional[dict]:
        """Get a single job by ID."""
        job = self.jobs.get(job_id)
        return job.model_dump() if job else None

    def get_metrics(self, worker_count: int = 0) -> dict:
        """Compute current system metrics."""
        jobs = list(self.jobs.values())
        total = len(jobs)
        completed = sum(1 for j in jobs if j.status == JobStatus.COMPLETED)
        failed = sum(1 for j in jobs if j.status == JobStatus.FAILED)
        running = sum(1 for j in jobs if j.status == JobStatus.RUNNING)
        pending = sum(1 for j in jobs if j.status == JobStatus.PENDING)
        retrying = sum(1 for j in jobs if j.status == JobStatus.RETRYING)

        finished = completed + failed
        success_rate = (completed / finished * 100) if finished > 0 else 0.0
        failure_rate = (failed / finished * 100) if finished > 0 else 0.0

        exec_times = [j.execution_time for j in jobs if j.execution_time is not None]
        avg_exec = sum(exec_times) / len(exec_times) if exec_times else 0.0
        total_retries = sum(j.retries for j in jobs)

        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()

        return JobMetrics(
            total_jobs=total,
            pending=pending,
            running=running,
            completed=completed,
            failed=failed,
            retrying=retrying,
            success_rate=round(success_rate, 1),
            failure_rate=round(failure_rate, 1),
            avg_execution_time=round(avg_exec, 2),
            total_retries=total_retries,
            worker_count=worker_count,
            uptime_seconds=round(uptime, 1),
        ).model_dump()

    def get_logs(self, limit: int = 100) -> List[dict]:
        """Return recent structured log entries."""
        logs = list(self.log_buffer)
        return [l.model_dump() for l in logs[-limit:]]

    async def _log(self, level: str, source: str, message: str, job_id: str = None, worker_id: str = None):
        """Create structured log entry and broadcast."""
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            source=source,
            message=message,
            job_id=job_id,
            worker_id=worker_id,
        )
        self.log_buffer.append(entry)
        # Also log to Python logger
        log_fn = getattr(logger, level.lower(), logger.info)
        log_fn(f"[{source}] {message}")
        # Broadcast log to WS clients
        await self.ws_manager.broadcast({
            "event": "log",
            "data": entry.model_dump(),
            "timestamp": entry.timestamp,
        })

    async def _broadcast_event(self, event: str, data):
        """Broadcast a job event to WebSocket clients."""
        payload = data.model_dump() if hasattr(data, 'model_dump') else data
        await self.ws_manager.broadcast({
            "event": event,
            "data": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
