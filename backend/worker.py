"""
Worker Engine - Async job processors for the Distributed Workflow Orchestrator.
Simulates distributed worker behavior with configurable failure rates.
Each worker runs as an independent asyncio task.
"""
import asyncio
import random
import logging
from datetime import datetime, timezone
from models import JobStatus, JobType
from config import (
    FAILURE_PROBABILITY, MIN_EXECUTION_TIME, MAX_EXECUTION_TIME,
    PIPELINE_STAGES, PIPELINE_STAGE_MIN_TIME, PIPELINE_STAGE_MAX_TIME,
    WORKER_POLL_INTERVAL,
)

logger = logging.getLogger("worker_engine")


class WorkerEngine:
    """
    Manages a pool of async workers that continuously process jobs from the queue.
    Each worker is an independent coroutine that pulls from the shared queue manager.
    """

    def __init__(self, queue_manager, worker_count: int = 3):
        self.queue_manager = queue_manager
        self.worker_count = worker_count
        self.workers = []
        self._running = False
        self.active_workers = 0

    async def start(self):
        """Start the worker pool and the retry processor."""
        self._running = True
        logger.info(f"Starting {self.worker_count} workers")
        await self.queue_manager._log("INFO", "worker_engine", f"Initializing {self.worker_count} worker threads")

        for i in range(self.worker_count):
            worker_id = f"W-{i:02d}"
            task = asyncio.create_task(self._worker_loop(worker_id))
            self.workers.append(task)

        # Retry queue processor runs separately
        retry_task = asyncio.create_task(self._retry_loop())
        self.workers.append(retry_task)

    async def stop(self):
        """Gracefully shut down all workers."""
        self._running = False
        for task in self.workers:
            task.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        logger.info("All workers stopped")

    async def _worker_loop(self, worker_id: str):
        """
        Main worker loop: continuously polls for jobs and executes them.
        Handles failures and triggers retries.
        """
        await self.queue_manager._log("INFO", worker_id, f"Worker {worker_id} online")

        while self._running:
            try:
                job = await self.queue_manager.dequeue_job()
                if job is None:
                    await asyncio.sleep(WORKER_POLL_INTERVAL)
                    continue

                self.active_workers += 1

                # Transition to RUNNING
                await self.queue_manager.update_job_status(
                    job.id, JobStatus.RUNNING, worker_id=worker_id
                )

                # Execute based on job type
                try:
                    if job.type == JobType.COMPUTE:
                        exec_time = await self._execute_compute(job, worker_id)
                    else:
                        exec_time = await self._execute_pipeline(job, worker_id)

                    # Simulate random failure
                    if random.random() < FAILURE_PROBABILITY:
                        error_msg = random.choice([
                            "SegFault in compute kernel",
                            "Memory allocation exceeded",
                            "Network partition detected",
                            "Timeout: execution exceeded threshold",
                            "Data corruption in input stream",
                            "Worker heartbeat lost",
                        ])
                        raise RuntimeError(error_msg)

                    # Job completed successfully
                    await self.queue_manager.update_job_status(
                        job.id, JobStatus.COMPLETED, worker_id=worker_id,
                        execution_time=exec_time
                    )

                except RuntimeError as e:
                    # Job failed — attempt retry
                    await self.queue_manager.update_job_status(
                        job.id, JobStatus.FAILED, worker_id=worker_id,
                        error=str(e), execution_time=exec_time if 'exec_time' in dir() else None
                    )
                    # Enqueue for retry if within limits
                    retried = await self.queue_manager.enqueue_retry(job.id)
                    if not retried:
                        await self.queue_manager._log(
                            "ERROR", worker_id,
                            f"Job {job.id} permanently failed (retries exhausted)",
                            job_id=job.id, worker_id=worker_id
                        )

                self.active_workers -= 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} unexpected error: {e}")
                self.active_workers = max(0, self.active_workers - 1)
                await asyncio.sleep(WORKER_POLL_INTERVAL)

    async def _execute_compute(self, job, worker_id: str) -> float:
        """Simulate a compute-bound job with random execution time."""
        exec_time = random.uniform(MIN_EXECUTION_TIME, MAX_EXECUTION_TIME)
        await self.queue_manager._log(
            "INFO", worker_id,
            f"Executing compute job {job.id} (est. {exec_time:.1f}s)",
            job_id=job.id, worker_id=worker_id
        )
        await asyncio.sleep(exec_time)
        return round(exec_time, 2)

    async def _execute_pipeline(self, job, worker_id: str) -> float:
        """Simulate a multi-stage pipeline job (ETL-like)."""
        total_time = 0
        for stage in PIPELINE_STAGES:
            stage_time = random.uniform(PIPELINE_STAGE_MIN_TIME, PIPELINE_STAGE_MAX_TIME)
            await self.queue_manager.update_job_status(
                job.id, JobStatus.RUNNING, worker_id=worker_id,
                pipeline_stage=stage
            )
            await self.queue_manager._log(
                "INFO", worker_id,
                f"Pipeline {job.id} stage: {stage} ({stage_time:.1f}s)",
                job_id=job.id, worker_id=worker_id
            )
            await asyncio.sleep(stage_time)
            total_time += stage_time

            # Each stage has its own small failure chance
            if random.random() < (FAILURE_PROBABILITY * 0.3):
                raise RuntimeError(f"Pipeline stage '{stage}' failed: data integrity check")

        return round(total_time, 2)

    async def _retry_loop(self):
        """Periodically process the retry queue, moving jobs back to pending."""
        while self._running:
            try:
                await asyncio.sleep(5)
                await self.queue_manager.process_retry_queue()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Retry loop error: {e}")
