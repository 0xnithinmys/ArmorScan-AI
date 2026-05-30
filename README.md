# ArmorScan AI

ArmorScan AI is a security auditing platform with a web control plane, a FastAPI orchestration API, asynchronous scan workers, and AI-assisted scanning agents.

It is built for a local workflow where you can:
- register approved targets
- verify target authorization
- queue governed scans for URLs, APIs, and repositories
- stream scan progress live
- review findings and evidence
- export reports in multiple formats

## Project Summary

ArmorScan AI is organized as a local-first security operations application:
- the `frontend` is the operator dashboard
- the `backend` is the API and orchestration layer
- the `worker` executes scan jobs asynchronously
- the `agents` package performs the actual scan workflow
- PostgreSQL stores operational data and Redis powers queues plus live events

In practice, the product flow is simple:
1. create an account
2. register a target
3. verify that the target is authorized
4. queue a governed scan
5. review findings
6. export the final report

## What This Project Includes

| Area | Purpose |
|---|---|
| Frontend | Next.js dashboard for auth, targets, scans, findings, reports, and audit events |
| Backend | FastAPI API for auth, target management, scan orchestration, findings, reports, and WebSocket events |
| Worker | Celery worker that executes scan jobs asynchronously |
| Agents | Python scan workflow that performs recon, browser analysis, API discovery, repo inspection, risk analysis, and reporting |
| Storage | PostgreSQL for persistent data and Redis for Celery plus live event streaming |

## Core Capabilities

- Target registry for `url`, `api`, and `github` scan targets
- Authorization proof flow for DNS TXT, HTTP file, meta tag, GitHub file, or manual attestation
- Governed scan execution with signed intent plans and policy decisions
- Live scan updates over WebSocket
- Findings workflow with status changes, evidence, comments, suppression, and history
- Report export in `json`, `markdown`, `pdf`, and `sarif`
- Audit trail for key policy and execution events

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Backend API | FastAPI, Pydantic, SQLAlchemy |
| Async Jobs | Celery |
| Scan Workflow | Python agent pipeline with LangGraph-compatible workflow structure |
| Browser Automation | Playwright |
| Database | PostgreSQL |
| Queue and Event Transport | Redis |
| Reports | JSON, Markdown, PDF, SARIF |

## Architecture

```mermaid
flowchart LR
    U[User in Browser] --> FE[Next.js Frontend\nlocalhost:3000]
    FE -->|REST| API[FastAPI Backend\nlocalhost:8000/api/v1]
    FE -->|WebSocket| API

    API --> DB[(PostgreSQL)]
    API --> REDIS[(Redis)]
    API -->|Dispatch scan job| W[Celery Worker\nscans queue]

    W --> AG[ArmorScan Agents\nLangGraph workflow]
    AG --> PW[Playwright]
    AG --> SE[Scanning engines]

    W --> DB
    W --> REDIS
    API --> REP[Report exports\nJSON / Markdown / PDF / SARIF]
```

## Scan Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Frontend
    participant API as Backend API
    participant Policy as Policy Engine
    participant Worker as Celery Worker
    participant Agents as Scan Agents
    participant DB as PostgreSQL

    User->>UI: Register or sign in
    User->>UI: Create target
    UI->>API: POST /auth and POST /targets
    User->>UI: Verify target authorization
    UI->>API: POST /targets/{id}/proofs/challenge and /authorize
    User->>UI: Queue scan
    UI->>API: POST /scans
    API->>Policy: Evaluate request and sign intent plan
    API->>Worker: Dispatch scan job
    Worker->>Agents: Run scan workflow
    Agents-->>Worker: Findings, trace, report data
    Worker->>DB: Persist scan state and findings
    API-->>UI: REST responses and live WebSocket events
    User->>UI: Export report
    UI->>API: GET /reports/{scan_id}/*
```

## Main Product Areas

| Module | What you do there |
|---|---|
| Dashboard | View the overall platform state |
| Targets | Create targets and manage authorization verification |
| Scans | Queue new scans, watch live progress, inspect intent plans |
| Findings | Review prioritized findings and update remediation status |
| Reports | Export scan output in operational formats |
| Audit | Review governance and execution events |
| Login | Register a user and sign in locally |

## How It Works Locally

When running locally, the app behaves like this:

1. The frontend calls the backend at `/api/v1`
2. The backend validates the request, creates the scan record, and signs an intent plan
3. The backend dispatches a Celery task to the `scans` queue
4. The worker runs the scan workflow from the `agents` package
5. Findings, trace data, and reports are stored in PostgreSQL
6. Live events are streamed back to the UI through WebSocket updates

## API Surface

| Endpoint Group | Purpose |
|---|---|
| `/api/v1/auth` | Register, log in, and fetch the current user |
| `/api/v1/organizations` | Organization and access context |
| `/api/v1/targets` | Target CRUD and authorization proof workflows |
| `/api/v1/scans` | Queue, inspect, cancel, and fetch scan-related data |
| `/api/v1/findings` | List findings, update status, add evidence and comments |
| `/api/v1/reports` | Export PDF, Markdown, JSON, and SARIF reports |
| `/api/v1/audit` | Review audit and policy events |
| `/api/v1/ws` | Live scan event stream |

## Repository Layout

```text
ArmorScan AI/
|-- frontend/          # Next.js application
|-- backend/           # FastAPI application and Celery worker code
|-- agents/            # Scan workflow and agent tooling
|-- docker-compose.yml # Local multi-service stack
|-- README.md
```

## Local Setup

### Prerequisites

- Docker Desktop with Docker Compose
- Node.js 20+
- Python 3.12+
- Chromium install for Playwright when running the worker outside Docker

### Option 1: Run with Docker

This is the fastest way to start the full stack locally.

1. Create a root `.env` file in the repository.

```env
SECRET_KEY=change-me
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

3. Run database migrations.

```powershell
docker compose exec backend alembic upgrade head
```

4. Open the app.

- Frontend: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Flower: `http://localhost:5555`

5. Create a local user account from the login page, then:
- add a target
- complete or record an authorization proof
- queue a scan
- watch live scan events
- review findings and export reports

### First Local Run Checklist

After the app is up, use this order:

1. Open `http://localhost:3000`
2. Create a local account from the login screen
3. Add a target in the Targets module
4. Complete a proof flow or record a manual attestation
5. Open Scans and queue a scan
6. Watch the live scan stream
7. Open Findings to review results
8. Open Reports to export JSON, Markdown, PDF, or SARIF

### Option 2: Run in Development Mode

Use this when you want hot reload for the frontend and backend.

#### 1. Start infrastructure only

```powershell
docker compose up -d postgres redis
```

#### 2. Configure backend and worker environment

Create a root `.env` file with the values below.

```env
SECRET_KEY=change-me
DATABASE_URL=postgresql+asyncpg://armorscan:armorscan@localhost:5432/armorscan
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
ALLOWED_ORIGINS=["http://localhost:3000"]
GROQ_API_KEY=your_key_here
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
ARMORIQ_API_KEY=
ARMORIQ_API_URL=https://api.armoriq.ai
```

At least one AI provider key should be set for agent reasoning.

#### 3. Start the backend API

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

#### 4. Start the scan worker in a new terminal

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
celery -A app.core.celery_app worker --loglevel=info -Q scans --pool=solo --concurrency=1
```

#### 5. Start the frontend

Create `frontend/.env.local`:

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
| Flower | `http://localhost:5555` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |

## Optional Security Tooling

The scan workflow can use additional local tools when they are available on your machine.

- `nuclei`
- `semgrep`
- `bandit`
- `trivy`
- `gitleaks`
- `zap-baseline.py`

These are not required to boot the app, but they improve scanner coverage when installed and available on `PATH`.

## Environment Notes

- Backend settings load from the root `.env` file
- Frontend local settings should go in `frontend/.env.local`
- The frontend uses `NEXT_PUBLIC_API_BASE_URL`
- The backend requires PostgreSQL and Redis to be reachable before scans can run successfully
- AI-assisted scan reasoning requires at least one provider key such as `GROQ_API_KEY` or `OPENAI_API_KEY`

## Notes

- The backend does not apply migrations automatically on startup. Run `alembic upgrade head` before using the API against a new database.
- The Celery worker is the service that runs scans. The separate `agents` container in `docker-compose.yml` is a tooling container, not the main execution path.
- The frontend derives its WebSocket connection from `NEXT_PUBLIC_API_BASE_URL`, so you only need to set that one frontend environment variable for local development.
