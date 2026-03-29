"""
Configuration module for the Distributed Workflow Orchestrator.
All system parameters are configurable via environment variables with sensible defaults.
Designed for future migration to Redis/Kafka-backed configuration.
"""
import os

# Worker configuration
WORKER_COUNT = int(os.environ.get("WORKER_COUNT", "3"))
WORKER_POLL_INTERVAL = float(os.environ.get("WORKER_POLL_INTERVAL", "1.0"))

# Job execution
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
FAILURE_PROBABILITY = float(os.environ.get("FAILURE_PROBABILITY", "0.3"))
MIN_EXECUTION_TIME = float(os.environ.get("MIN_EXECUTION_TIME", "2.0"))
MAX_EXECUTION_TIME = float(os.environ.get("MAX_EXECUTION_TIME", "8.0"))

# Pipeline stage configuration
PIPELINE_STAGES = ["extract", "transform", "load", "validate"]
PIPELINE_STAGE_MIN_TIME = float(os.environ.get("PIPELINE_STAGE_MIN_TIME", "1.0"))
PIPELINE_STAGE_MAX_TIME = float(os.environ.get("PIPELINE_STAGE_MAX_TIME", "3.0"))

# Logging
LOG_BUFFER_SIZE = int(os.environ.get("LOG_BUFFER_SIZE", "500"))

# System
SYSTEM_NAME = "CERN-WFO"
SYSTEM_VERSION = "1.0.0"
