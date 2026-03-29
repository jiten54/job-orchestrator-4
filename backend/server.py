"""
Distributed Workflow Orchestrator - API Gateway
FastAPI application serving as the entry point for job management,
real-time monitoring, and system observability.
"""
from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from models import Job, JobCreate, JobType, HealthResponse
from queue_manager import JobQueueManager, ConnectionManager
from worker import WorkerEngine
from config import (
    WORKER_COUNT, MAX_RETRIES, FAILURE_PROBABILITY,
    SYSTEM_NAME, SYSTEM_VERSION,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Structured logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-18s | %(levelname)-7s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger("orchestrator")

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Core system components
ws_manager = ConnectionManager()
queue_manager = JobQueueManager(ws_manager)
worker_engine = WorkerEngine(queue_manager, worker_count=WORKER_COUNT)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: start workers on boot, stop on shutdown."""
    logger.info(f"{SYSTEM_NAME} v{SYSTEM_VERSION} starting...")
    logger.info(f"Config: workers={WORKER_COUNT}, max_retries={MAX_RETRIES}, failure_rate={FAILURE_PROBABILITY}")
    await worker_engine.start()
    yield
    logger.info("Shutting down workers...")
    await worker_engine.stop()
    client.close()


app = FastAPI(title=SYSTEM_NAME, version=SYSTEM_VERSION, lifespan=lifespan)
api_router = APIRouter(prefix="/api")


# ─── Job CRUD ───────────────────────────────────────────────────────────────

@api_router.post("/jobs")
async def create_job(payload: JobCreate):
    """Create a new job and enqueue it for processing."""
    job = Job(
        name=payload.name,
        type=payload.type,
        max_retries=payload.max_retries,
    )
    created = await queue_manager.add_job(job)
    return created.model_dump()


@api_router.post("/jobs/batch")
async def create_batch_jobs(count: int = Query(default=5, ge=1, le=50)):
    """Create multiple jobs at once for load testing."""
    jobs = []
    for i in range(count):
        job_type = JobType.COMPUTE if i % 3 != 0 else JobType.PIPELINE
        job = Job(
            name=f"batch-{job_type.value}-{i:03d}",
            type=job_type,
            max_retries=MAX_RETRIES,
        )
        await queue_manager.add_job(job)
        jobs.append(job.model_dump())
    return {"created": len(jobs), "jobs": jobs}


@api_router.get("/jobs")
async def list_jobs(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
):
    """List all jobs with optional status/type filters."""
    return queue_manager.get_jobs(status=status, job_type=type)


@api_router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get a specific job by ID."""
    job = queue_manager.get_job(job_id)
    if not job:
        return {"error": "Job not found"}, 404
    return job


# ─── Recovery & Retry ───────────────────────────────────────────────────────

@api_router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str):
    """Retry a specific failed job."""
    job = queue_manager.jobs.get(job_id)
    if not job:
        return {"error": "Job not found"}
    if job.status.value not in ("failed",):
        return {"error": f"Cannot retry job in {job.status.value} state"}
    job.retries = 0
    job.status = "pending"
    job.error_message = None
    job.updated_at = datetime.now(timezone.utc).isoformat()
    queue_manager.pending_queue.append(job.id)
    await queue_manager._log("INFO", "api", f"Manual retry triggered for job {job_id}", job_id=job_id)
    await queue_manager._broadcast_event("job_retrying", job)
    return {"status": "retrying", "job_id": job_id}


@api_router.post("/jobs/retry-all")
async def retry_all_failed():
    """Retry all permanently failed jobs."""
    count = await queue_manager.retry_all_failed()
    return {"retried": count}


@api_router.post("/recovery/auto")
async def auto_recovery():
    """Trigger automatic recovery: reset failed jobs and process retry queue."""
    result = await queue_manager.auto_recovery()
    return result


# ─── Observability ──────────────────────────────────────────────────────────

@api_router.get("/health")
async def health_check():
    """System health check endpoint."""
    uptime = (datetime.now(timezone.utc) - queue_manager.start_time).total_seconds()
    return HealthResponse(
        status="healthy",
        system=SYSTEM_NAME,
        version=SYSTEM_VERSION,
        workers_active=worker_engine.active_workers,
        queue_depth=len(queue_manager.pending_queue),
        uptime_seconds=round(uptime, 1),
    ).model_dump()


@api_router.get("/metrics")
async def get_metrics():
    """System metrics for monitoring dashboard."""
    return queue_manager.get_metrics(worker_count=WORKER_COUNT)


@api_router.get("/logs")
async def get_logs(limit: int = Query(default=100, ge=1, le=500)):
    """Recent structured log entries."""
    return queue_manager.get_logs(limit=limit)


@api_router.get("/config")
async def get_config():
    """Current system configuration."""
    return {
        "worker_count": WORKER_COUNT,
        "max_retries": MAX_RETRIES,
        "failure_probability": FAILURE_PROBABILITY,
        "system": SYSTEM_NAME,
        "version": SYSTEM_VERSION,
    }


# ─── WebSocket ──────────────────────────────────────────────────────────────

@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time job status and log streaming."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; client can send commands
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"event": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


# ─── Mount & Middleware ─────────────────────────────────────────────────────

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
