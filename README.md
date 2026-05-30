# ArmorScan AI

ArmorScan AI is a local-first security auditing platform with a Next.js operator console, a FastAPI orchestration API, an asynchronous Celery worker, and a Python agent pipeline that performs recon, safe validation, scanner orchestration, correlation, and reporting.

The system is designed for authorized testing only. It expects you to register targets, verify authorization, queue governed scans, watch live execution, review findings, and export reports.

## What This Repo Contains

- `frontend/` - Next.js operator UI
- `backend/` - FastAPI API, database models, services, and Celery task entrypoints
- `agents/` - the ArmorScan agent runtime, specialist agents, and scanner integrations
- `docker-compose.yml` - local multi-service stack
- `README.md` - this guide

## High-Level Architecture

```mermaid
flowchart LR
    U[Operator] --> FE[Next.js Frontend]
    FE -->|REST| API[FastAPI Backend]
    FE -->|WebSocket| API

    API --> DB[(PostgreSQL)]
    API --> REDIS[(Redis)]
    API -->|enqueue scans queue| W[Celery Worker]

    W --> AG[ArmorScan Agent Pipeline]
    AG --> PW[Playwright browser recon]
    AG --> ENG[Scanner engines]
    AG --> AI[Groq / OpenAI / Anthropic]

    ENG --> ZAP[OWASP ZAP]
    ENG --> NUC[nuclei]
    ENG --> SAST[semgrep / bandit]
    ENG --> SUP[gitleaks / trivy]

    API --> REP[Reports: JSON / Markdown / PDF / SARIF]
```

## Core Flow

1. Sign in or create an account.
2. Register a target and choose the target type.
3. Prove authorization for the target when required.
4. Create or select a scan profile.
5. Queue a scan.
6. The backend records the scan and dispatches a Celery task to the `scans` queue.
7. The worker runs the agent pipeline, scanner engines, and safe validation steps.
8. Findings, evidence, and trace data are stored in PostgreSQL.
9. The UI receives live updates over WebSocket.
10. Export the report as JSON, Markdown, PDF, or SARIF.

## Agent Architecture

The agent runtime is implemented as a LangGraph-compatible workflow with a sequential fallback when `langgraph` is unavailable. The main pipeline is:

1. `planner`
2. `recon`
3. `browser_workflow`
4. `api_discovery`
5. `repo_sast`
6. `supply_chain`
7. `scanner_registry`
8. `engines`
9. `evidence_normalization`
10. `analysis`
11. `exploit`
12. `correlation`
13. `retest`
14. `reporter`

### Specialist Agents

The specialist layer lives in `agents/armorscan/specialists.py` and currently includes:

- `browser_workflow_agent`
- `api_discovery_agent`
- `repo_sast_agent`
- `dependency_supply_chain_agent`
- `scanner_registry_agent`
- `evidence_normalization_agent`
- `correlation_agent`
- `retest_agent`

### What Each Stage Does

- `planner` builds the governed scan plan and allowed actions.
- `recon` performs passive HTTP and browser reconnaissance.
- `browser_workflow` maps forms, uploads, workflows, and JavaScript-discovered surfaces.
- `api_discovery` finds API endpoints and routes.
- `repo_sast` inventories repository routes and source surfaces for GitHub scans.
- `supply_chain` inspects dependency and infrastructure surfaces for GitHub scans.
- `scanner_registry` advertises which engines are available for the current scan type.
- `engines` runs the external scanner engines.
- `evidence_normalization` turns browser, HTTP, API, repo, and scanner data into normalized evidence.
- `analysis` drafts candidate findings with LLM assistance and fallback heuristics.
- `exploit` performs safe, policy-checked validation probes.
- `correlation` links findings to evidence and adjusts confidence.
- `retest` prepares safe retest checks for confirmed issues.
- `reporter` synthesizes the final report payload.

## Supported Scan Types

- `url` - public web target scanning
- `api` - API-oriented scanning
- `github` - repository and supply-chain analysis

## Frontend Modules

The Next.js app exposes these main operator areas:

- Dashboard
- Organizations
- Targets
- Scans
- Findings
- Reports
- Platform
- Audit
- Login

The frontend uses `NEXT_PUBLIC_API_BASE_URL` and derives the WebSocket URL from that same base.

## Backend API Surface

All API routes are mounted under `/api/v1`.

- `/auth` - register, login, current user
- `/organizations` - organizations, teams, and membership context
- `/targets` - target CRUD and authorization proof workflow
- `/scans` - queue, inspect, cancel, retry, duplicate, pause, and resume scans
- `/findings` - list findings, update status, add evidence, comments, and suppression
- `/reports` - export JSON, Markdown, PDF, and SARIF reports
- `/platform` - platform metadata, scan profiles, and operational data
- `/audit` - audit and governance events
- `/ws` - live scan event stream

### Common Target Authorization Flow

For a web target, the typical authorization sequence is:

1. Create the target.
2. Request a proof challenge.
3. Fulfill the challenge through DNS, HTTP, meta tag, GitHub file, or manual attestation.
4. Verify the proof.
5. Queue the scan once the target is authorized.

## Scanner and Tooling Support

The agent registry currently knows about these engines:

- `nuclei` - template-driven web checks
- `zap-baseline` - OWASP ZAP passive/baseline scanning
- `semgrep` - source code scanning
- `bandit` - Python security linting
- `gitleaks` - secret scanning
- `trivy` - dependency, filesystem, container, and IaC scanning

Scanner availability is detected at runtime. If an engine is not installed, the scan keeps going and records the missing tool instead of failing the whole job.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript |
| Backend API | FastAPI, SQLAlchemy, Pydantic |
| Async jobs | Celery |
| Workflow engine | LangGraph-compatible agent pipeline |
| Browser recon | Playwright |
| Database | PostgreSQL |
| Queue / events | Redis |
| Reports | JSON, Markdown, PDF, SARIF |
| AI providers | Groq, OpenAI, Anthropic |

## Repository Layout

```text
ArmorScan AI/
|-- frontend/            # Next.js operator UI
|-- backend/             # FastAPI app, services, models, worker tasks
|-- agents/              # Agent pipeline, scanners, runtime helpers
|-- docker-compose.yml   # Local stack
|-- userflow.md          # Product flow reference
|-- AI-Powered Web Security Auditor Design.md
|-- README.md
```

## Local Setup

### Prerequisites

- Docker Desktop and Docker Compose
- Node.js 20+
- Python 3.12+
- Chromium for Playwright if you run the worker outside Docker

### Option 1: Run Everything with Docker

1. Create a root `.env` file.

```env
SECRET_KEY=change-me
DATABASE_URL=postgresql+asyncpg://armorscan:armorscan@postgres:5432/armorscan
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
ALLOWED_ORIGINS=["http://localhost:3000"]
GROQ_API_KEY=your_key_here
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
ARMORIQ_API_KEY=
ARMORIQ_API_URL=https://api.armoriq.ai
```

2. Start the stack.

```powershell
docker compose up --build -d
```

3. Run migrations.

```powershell
docker compose exec backend alembic upgrade head
```

4. Open the app.

- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Flower: `http://localhost:5555`

### Option 2: Run in Development Mode

Use this when you want hot reload.

#### 1. Start Postgres and Redis

```powershell
docker compose up -d postgres redis
```

#### 2. Set backend environment

Create a root `.env` file.

```env
SECRET_KEY=change-me
DATABASE_URL=postgresql+asyncpg://armorscan:armorscan@localhost:5432/armorscan
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
ALLOWED_ORIGINS=["http://localhost:3000"]
GROQ_API_KEY=your_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=openai/gpt-oss-20b
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
ARMORIQ_API_KEY=
ARMORIQ_API_URL=https://api.armoriq.ai
```

At least one AI provider key should be present for agent reasoning.

#### 3. Start the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r ..\agents\requirements.txt
playwright install chromium
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

#### 4. Start the worker

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
celery -A app.core.celery_app worker --loglevel=info -Q scans --pool=solo --concurrency=1
```

#### 5. Start the frontend

Create `frontend/.env.local`.

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Then run:

```powershell
cd frontend
npm install
npm run dev
```

## Local URLs

| Service | URL |
|---|---|
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| Health | `http://localhost:8000/health` |
| Flower | `http://localhost:5555` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |

## Environment Notes

- Backend settings are loaded from `.env` files at the repo root or from `backend/../.env` when launched from the backend directory.
- Frontend runtime config lives in `frontend/.env.local`.
- The frontend reads `NEXT_PUBLIC_API_BASE_URL`; its WebSocket stream is derived from that value.
- The Celery worker consumes the `scans` queue.
- On Windows, Celery runs with the solo pool and concurrency 1.
- The `agents` service in `docker-compose.yml` is a tooling container, not the main worker process.

## Optional Security Tooling

The scan workflow can use these local tools when installed and available on `PATH`:

- `nuclei`
- `zap-baseline.py` or a local ZAP runtime
- `semgrep`
- `bandit`
- `trivy`
- `gitleaks`

They are not required to boot the application, but they improve scanner coverage.

## Operational Notes

- The backend verifies database connectivity on startup but does not apply migrations automatically.
- The worker is responsible for executing scans; the API only schedules and orchestrates them.
- The report layer includes JSON, Markdown, PDF, and SARIF exports.
- Findings include status tracking, evidence, comments, suppression, and remediation history.
- The agent pipeline records trace data so operators can inspect each stage of the scan.
