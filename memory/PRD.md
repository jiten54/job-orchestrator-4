# Distributed Workflow Orchestrator - PRD

## Original Problem Statement
Build a production-grade "Distributed Workflow Orchestrator with Real-Time Monitoring, Fault Tolerance, and DevOps Observability" similar to CERN's distributed computing platform.

## Architecture
- **Backend**: FastAPI (REST + WebSocket) with in-memory job queue, async worker engine, retry system
- **Frontend**: React + Tailwind + Shadcn UI dark command-center dashboard
- **Database**: MongoDB (available, but jobs managed in-memory for speed — production would use Redis/Kafka)
- **Real-time**: WebSocket push for job updates and log streaming

## User Personas
- DevOps engineers monitoring job pipelines
- System administrators triggering recovery actions
- Data engineers managing compute/pipeline workloads

## Core Requirements
- Async job execution (compute + pipeline types)
- Fault tolerance with configurable failure rate and auto-retry
- Real-time WebSocket monitoring dashboard
- Structured observability (logging, metrics, health checks)
- Manual and automatic recovery mechanisms

## What's Been Implemented (2026-03-29)
### Backend (5 modules)
- `config.py` - Configurable system parameters (workers, retry limits, failure rate)
- `models.py` - Domain models (Job, JobMetrics, HealthResponse, LogEntry, WSMessage)
- `queue_manager.py` - In-memory job queue + retry queue with WebSocket broadcast
- `worker.py` - Async worker engine with 3 concurrent workers, failure simulation
- `server.py` - Full API gateway (13 endpoints + WebSocket)

### API Endpoints
- POST /api/jobs — Create job
- POST /api/jobs/batch — Batch create
- GET /api/jobs — List with filters
- GET /api/jobs/{id} — Get job
- POST /api/jobs/{id}/retry — Retry job
- POST /api/jobs/retry-all — Retry all failed
- POST /api/recovery/auto — Auto-recovery
- GET /api/health — Health check
- GET /api/metrics — System metrics
- GET /api/logs — Structured logs
- GET /api/config — System config
- WS /api/ws — Real-time updates

### Frontend (7 components)
- Dashboard.jsx — Main orchestrator view
- MetricCards.jsx — 8 KPI metric cards
- JobTable.jsx — Filterable job table with retry actions
- LogsPanel.jsx — Terminal-style live log stream
- CreateJobDialog.jsx — Job creation dialog with batch mode
- useWebSocket.js — Auto-reconnecting WebSocket hook

## Test Results
- Backend: 100% (13/13 endpoints)
- Frontend: 95% (19/20 features, minor toast positioning fixed)

## Prioritized Backlog
### P0 (Critical) — All Done
### P1 (Important)
- Persist jobs to MongoDB for durability
- Redis-backed queue for horizontal scaling
- Job cancellation API
### P2 (Nice to Have)
- Kafka integration for event streaming
- Prometheus metrics export
- Grafana dashboard templates
- Docker compose for local dev
- CI/CD pipeline (GitHub Actions)
- Role-based access control
- Job scheduling/cron support

## Next Tasks
1. Persist jobs to MongoDB for restart durability
2. Add job cancellation functionality
3. Add recharts-based analytics (job throughput, failure trends over time)
4. Dockerize with docker-compose
5. Add WebSocket heartbeat monitoring
