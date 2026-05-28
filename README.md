# ArmorScan AI

> **AI-native autonomous web security auditing platform.**
> Combines LangGraph multi-agent reasoning with Playwright browser automation and ArmorIQ cryptographic intent verification to deliver intelligent, explainable, and governed vulnerability detection.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Product Vision](#product-vision)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Multi-Agent System](#multi-agent-system)
- [AI Agent Workflow (ReAct)](#ai-agent-workflow-react)
- [Scan Pipeline](#scan-pipeline)
- [Database Design](#database-design)
- [Security & Governance](#security--governance)
- [Risk Scoring System](#risk-scoring-system)
- [Report Generation](#report-generation)
- [CI/CD Integration](#cicd-integration)
- [Quick Start](#quick-start)
- [Service URLs](#service-urls)
- [Roadmap](#roadmap)

---

## Problem Statement

Traditional SAST/DAST tools suffer from **90%+ false positive rates** due to rigid, signature-based rules that lack contextual awareness of an application's business logic. Modern SPAs with dynamic routing and async APIs break legacy crawlers. Meanwhile, unconstrained AI agents introduce severe risks — over 50% of malicious prompts succeed against agentic systems, with unconfined agents executing up to 80% of malicious intents.

**ArmorScan AI** solves this by marrying LLM contextual reasoning with deterministic browser automation, all governed by cryptographic intent verification.

---

## Product Vision

ArmorScan AI transforms vulnerability detection from a rigid scanning process into an **intelligent, explainable, governed agentic workflow**:

- **Input flexibility** — accepts a deployed URL, GitHub repository, or API endpoint
- **Autonomous crawling** — maps interactive surfaces including inputs, routes, auth systems, upload fields
- **Intelligent testing** — generates context-aware payloads for SQLi, XSS, SSTI, SSRF, CSRF, command injection, prompt injection, API misuse
- **Explainable output** — developer-friendly reports detailing *what*, *where*, *why*, *attack vectors*, *severity*, *reproduction steps*, and *fix code*
- **Cryptographic governance** — every tool invocation verified against a signed intent plan via ArmorIQ

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │              Next.js 14 (App Router) + TypeScript + Tailwind        │   │
│   │                                                                     │   │
│   │  Landing Page ─── Scan Config ─── Live Console ─── Report Dashboard │   │
│   │  Finding Detail ─── Audit Log ─── Scan History ─── Auth Pages       │   │
│   └───────────────────────────────┬─────────────────────────────────────┘   │
│                                   │ REST + WebSocket                        │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
┌───────────────────────────────────┼─────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                                 │
│                                   │                                         │
│   ┌───────────────────────────────▼─────────────────────────────────────┐   │
│   │                    FastAPI Gateway (Python)                          │   │
│   │                                                                     │   │
│   │  /auth ── /targets ── /scans ── /findings ── /reports ── /audit     │   │
│   │                    WebSocket: /ws/scans/{id}/stream                  │   │
│   └──────────┬──────────────────────────────┬───────────────────────────┘   │
│              │                              │                               │
│   ┌──────────▼──────────┐       ┌───────────▼───────────────────────┐      │
│   │   PostgreSQL 16     │       │   Redis 7                         │      │
│   │                     │       │                                   │      │
│   │  Users, Targets,    │       │  Celery Broker + Result Backend   │      │
│   │  Scans, Findings,   │       │  Semantic Cache                   │      │
│   │  Audit Logs         │       │  Pub/Sub (real-time trace stream) │      │
│   └─────────────────────┘       └───────────┬───────────────────────┘      │
│                                              │                              │
└──────────────────────────────────────────────┼──────────────────────────────┘
                                               │
┌──────────────────────────────────────────────┼──────────────────────────────┐
│                           AGENT LAYER                                       │
│                                              │                              │
│   ┌──────────────────────────────────────────▼──────────────────────────┐   │
│   │                Celery Workers (scans queue)                          │   │
│   │                                                                     │   │
│   │  ┌───────────────────────────────────────────────────────────────┐  │   │
│   │  │              LangGraph State Machine (ReAct Loop)             │  │   │
│   │  │                                                               │  │   │
│   │  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │  │   │
│   │  │  │  Recon   │──▶│ Analysis │──▶│ Exploit  │──▶│ Reporter │  │  │   │
│   │  │  │  Agent   │   │  Agent   │   │  Agent   │   │  Agent   │  │  │   │
│   │  │  └────┬─────┘   └──────────┘   └────┬─────┘   └──────────┘  │  │   │
│   │  │       │                              │                        │  │   │
│   │  └───────┼──────────────────────────────┼────────────────────────┘  │   │
│   └──────────┼──────────────────────────────┼──────────────────────────┘   │
│              │                              │                               │
│   ┌──────────▼──────────┐       ┌───────────▼───────────────────────┐      │
│   │ Playwright (headless)│       │   ArmorIQ Policy Engine          │      │
│   │                     │       │                                   │      │
│   │ Accessibility Tree  │       │  ArmorClaw Plugin (intercepts     │      │
│   │ DOM Interaction     │       │  every tool call, validates       │      │
│   │ Network Interception│       │  against signed intent token)     │      │
│   │ Payload Injection   │       │  Fail-closed architecture         │      │
│   └─────────────────────┘       └───────────────────────────────────┘      │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    External Scanning Tools                          │   │
│   │                                                                     │   │
│   │  Nuclei (CVE templates)  ──  Semgrep/Bandit/Trivy (SAST)           │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| **Frontend** | Next.js 14 + TypeScript + Tailwind CSS | App Router with Server Components, Suspense, and Server Actions for reactive dashboards |
| **Backend API** | FastAPI + Pydantic v2 + async SQLAlchemy | High-performance async, native type validation for LLM-generated JSON |
| **Migrations** | Alembic | Async-compatible PostgreSQL schema versioning |
| **Task Queue** | Celery + Redis | Distributed long-running scan jobs decoupled from the API |
| **AI Agents** | LangGraph + LangChain | Cyclic stateful multi-agent workflows with built-in memory |
| **Primary LLM** | Claude 3.5 Sonnet | Industry-leading code reasoning, massive context, strict prompt adherence |
| **Fallback LLM** | GPT-4o | Deep logic engine for complex business logic flaw validation |
| **Local LLM** | Llama 3.1 (8B/70B) via Ollama | High-volume summarization and template generation to reduce API costs |
| **Browser Automation** | Playwright (headless Chromium) | Accessibility tree extraction, SPA crawling, payload injection |
| **Database** | PostgreSQL 16 | ACID-compliant relational storage for all entities |
| **Policy Engine** | ArmorIQ SDK + ArmorClaw | Cryptographic intent verification, prompt injection protection |
| **Scanning** | Nuclei, Semgrep, Bandit, Trivy | Deterministic CVE checks and static analysis baselines |

---

## Project Structure

```
ArmorScan AI/
├── frontend/                    # Next.js 14 App Router
│   ├── src/
│   │   ├── app/                 # App Router pages & layouts
│   │   └── ...
│   ├── Dockerfile
│   ├── .prettierrc
│   └── package.json
│
├── backend/                     # FastAPI API Gateway
│   ├── app/
│   │   ├── main.py              # App entry point + lifespan
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic settings (.env)
│   │   │   ├── database.py      # Async SQLAlchemy engine + sessions
│   │   │   ├── security.py      # JWT + bcrypt
│   │   │   └── celery_app.py    # Celery configuration
│   │   ├── api/v1/
│   │   │   ├── router.py        # Composes all endpoint modules
│   │   │   └── endpoints/
│   │   │       ├── auth.py      # Register, login, JWT
│   │   │       ├── targets.py   # Asset CRUD + authorization proofs
│   │   │       ├── scans.py     # Initiate, status, cancel
│   │   │       ├── findings.py  # List, filter, update status
│   │   │       ├── reports.py   # PDF / JSON / SARIF export
│   │   │       ├── audit.py     # ArmorIQ audit events
│   │   │       └── ws.py        # WebSocket real-time scan stream
│   │   ├── models/              # SQLAlchemy ORM models (Phase 3)
│   │   └── workers/
│   │       └── scan_worker.py   # Celery scan task
│   ├── alembic/                 # Database migrations
│   ├── requirements.txt
│   ├── pyproject.toml           # Ruff + pytest + mypy
│   └── Dockerfile
│
├── agents/                      # LangGraph Multi-Agent System
│   ├── armorscan/
│   │   ├── graph.py             # State machine: Recon → Analysis → Exploit → Report
│   │   ├── state.py             # ScanState TypedDict (shared state)
│   │   ├── agents/              # Agent implementations (Phase 4)
│   │   │   ├── recon.py
│   │   │   ├── analysis.py
│   │   │   ├── exploit.py
│   │   │   └── reporter.py
│   │   └── tools/               # Tool wrappers (Phase 4-5)
│   │       ├── playwright_tools.py
│   │       ├── nuclei_tools.py
│   │       └── http_tools.py
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── Dockerfile
│
├── infra/                       # Kubernetes manifests (Phase 10)
├── docker-compose.yml           # Full local dev stack (7 services)
├── .env / .env.example
├── .gitignore
└── README.md
```

---

## Multi-Agent System

ArmorScan AI decomposes scanning into 4 specialized agents, each with a distinct role:

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│    RECON     │────▶│    ANALYSIS      │────▶│  EXPLOIT/VALIDATE    │────▶│    REPORTER      │
│    Agent     │     │    Agent         │     │    Agent             │     │    Agent         │
├─────────────┤     ├─────────────────┤     ├──────────────────────┤     ├─────────────────┤
│ Playwright   │     │ State graph     │     │ Payload generation   │     │ Log translation │
│ + Firecrawl  │     │ + CWE/CVE DB    │     │ + safe injection     │     │ + dev-friendly  │
│              │     │ correlation     │     │ + false positive     │     │   narrative     │
│ Outputs:     │     │                 │     │   filtering (ReAct)  │     │                 │
│ - Routes     │     │ Outputs:        │     │                      │     │ Outputs:        │
│ - Forms      │     │ - Prioritized   │     │ Outputs:             │     │ - Structured    │
│ - Inputs     │     │   attack surface│     │ - Validated findings │     │   findings JSON │
│ - Tech stack │     │                 │     │ - PoC evidence       │     │ - Reports       │
│ - State graph│     │                 │     │                      │     │                 │
└─────────────┘     └─────────────────┘     └──────────────────────┘     └─────────────────┘
```

| Agent | Role | LLM |
|---|---|---|
| **Reconnaissance** | Surface mapping — crawls SPA via Playwright, extracts accessibility tree, discovers routes/forms/inputs/APIs | Claude 3.5 Sonnet |
| **Vulnerability Analysis** | Strategic planner — correlates discovered endpoints with CWE/CVE databases, prioritizes attack matrix | Claude 3.5 Sonnet |
| **Exploitation & Validation** | Offensive engine — crafts context-aware payloads, injects via Playwright/HTTP, filters false positives with proof-of-concept validation | Claude 3.5 Sonnet / GPT-4o |
| **Reporting & Triage** | Communication layer — translates dense execution logs into structured, developer-friendly narratives | Llama 3.1 (local) |

---

## AI Agent Workflow (ReAct)

Each agent operates on a **Reason → Act → Observe → Reflect** state machine:

```
          ┌──────────────────────────────────────────────────────────────┐
          │                                                              │
          ▼                                                              │
    ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐    │
    │   IDLE   │────▶│ PLANNING │────▶│EXECUTING │────▶│OBSERVING │    │
    │          │     │          │     │          │     │          │    │
    │ Awaits   │     │ Generate │     │ Invoke   │     │ Capture  │    │
    │ scan job │     │ intent   │     │ tools    │     │ results  │    │
    │          │     │ plan →   │     │ via MCP  │     │ (HTTP,   │    │
    │          │     │ ArmorIQ  │     │          │     │  DOM,    │    │
    │          │     │ sign it  │     │          │     │  a11y)   │    │
    └──────────┘     └──────────┘     └──────────┘     └────┬─────┘    │
                                                            │          │
                                                            ▼          │
                                                      ┌──────────┐    │
                                                      │REFLECTING│    │
                                                      │          │    │
                                                      │ CoT      │────┘
                                                      │ analysis │ (loop back if ambiguous)
                                                      │ false    │
                                                      │ positive │──────▶ ┌───────────┐
                                                      │ filter   │        │ COMPLETED │
                                                      └──────────┘        └───────────┘
```

---

## Scan Pipeline

```
User submits target
        │
        ▼
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│ 1. INGESTION &      │────▶│ 2. CRAWLER-BASED     │────▶│ 3. CONTEXTUAL       │
│    POLICY GATING    │     │    DISCOVERY          │     │    ANALYSIS         │
│                     │     │                      │     │                     │
│ • Verify ownership  │     │ • Playwright FSM     │     │ • Detect tech stack │
│ • Load ArmorIQ      │     │ • Click, fill, nav   │     │ • Formulate         │
│   policies          │     │ • Map all routes,    │     │   targeted plan     │
│ • DNS TXT / meta /  │     │   forms, inputs      │     │ • Skip irrelevant   │
│   OAuth check       │     │ • Network intercept  │     │   payloads          │
└─────────────────────┘     └──────────────────────┘     └──────────┬──────────┘
                                                                    │
        ┌───────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│ 4. DYNAMIC PAYLOAD  │────▶│ 5. RESPONSE          │────▶│ 6. TRIAGE           │
│    GENERATION       │     │    ANALYSIS           │     │                     │
│                     │     │                      │     │ • Cross-reference   │
│ • AI-crafted        │     │ • HTTP status codes  │     │   all findings      │
│   payloads per      │     │ • Stack traces       │     │ • Demand PoC for    │
│   context           │     │ • DOM mutations      │     │   confirmation      │
│ • Bypass filters    │     │ • a11y tree diffs    │     │ • Filter false      │
│ • SQLi, XSS, SSTI,  │     │                      │     │   positives         │
│   SSRF, etc.        │     │                      │     │ • Commit to DB      │
└─────────────────────┘     └──────────────────────┘     └─────────────────────┘
```

---

## Database Design

```
┌──────────────────────────┐     ┌──────────────────────────┐
│   Identity & Access      │     │    Target Management     │
│   Management (IAM)       │     │                          │
│                          │     │  Assets                  │
│  Organizations           │     │  Authorization_Proofs    │
│  Users                   │     │  Asset_Metadata          │
│  Roles                   │     │                          │
│  API_Keys                │     │                          │
└────────────┬─────────────┘     └────────────┬─────────────┘
             │                                │
             └──────────┬─────────────────────┘
                        │
                        ▼
┌──────────────────────────┐     ┌──────────────────────────┐
│   Scan Operations        │     │  Vulnerability           │
│                          │     │  Intelligence            │
│  Scans                   │     │                          │
│  Agent_Traces            │     │  Findings                │
│  ArmorIQ_Audits          │     │  Evidences               │
│                          │     │  Remediations            │
└──────────────────────────┘     └──────────────────────────┘
```

Every finding is linked to the exact **intent token** and **execution trace** that discovered it — full auditability.

---

## Security & Governance

### ArmorIQ Integration

| Layer | Mechanism |
|---|---|
| **Plan Verification** | Agent submits CSRG (Canonical Structured Reasoning Graph) → ArmorIQ evaluates against org policies → returns signed intent token |
| **Runtime Enforcement** | ArmorClaw plugin intercepts every tool call → validates against Merkle-anchored plan commitments → blocks unauthorized actions |
| **Prompt Injection Protection** | If a crawled page tries to hijack the LLM (e.g., "upload data to external pastebin"), ArmorClaw blocks it because that action was never in the signed plan |
| **Fail-Closed** | Any deviation from the approved plan = immediate block. No exceptions. |

### Operational Safety

- **Rate limiting**: Max 50 req/sec hardcoded + configurable concurrency controls
- **Non-destructive payloads**: SSTI verified via benign math (`{{7*7}}`) not system commands
- **Authorization required**: DNS TXT, meta tag, or OAuth verification before any scan starts
- **Immutable audit log**: Every intent validation, policy decision, and tool execution recorded with cryptographic proof

---

## Risk Scoring System

| Component | Method |
|---|---|
| **Base Score** | CVSS v3.1/v4.0 — standardized severity baseline |
| **Threat Intelligence** | EPSS — real-world exploitation probability |
| **Contextual AI Modifier** | LLM adjusts score based on where the vuln sits (admin panel = higher, marketing page = lower) |
| **Confidence Score** | Agent's self-assessed certainty. High confidence (PoC confirmed) = top priority. Low confidence = flagged for human review |

---

## Report Generation

Every confirmed vulnerability includes:

| Section | Content |
|---|---|
| **What** | Plain-English description of the vulnerability |
| **Where** | Exact URL, parameter, endpoint, or source code line |
| **Why** | Contextual explanation of the vulnerability class |
| **Attack Scenario** | Narrative of how a threat actor would exploit it |
| **Severity** | Hybrid risk score (CVSS + EPSS + AI context + confidence) |
| **Reproduction Steps** | Copy-pasteable `curl` commands or HTTP payloads |
| **Fix** | Language-specific code snippets (parameterized queries, output encoding, etc.) |

**Export formats**: Interactive web dashboard, PDF, JSON, SARIF (GitHub Security tab)

---

## CI/CD Integration

```
Pull Request Created
        │
        ▼
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│ Webhook triggers    │────▶│ Differential scan    │────▶│ SARIF upload to     │
│ ArmorScan CI action │     │ (only changed routes │     │ GitHub Security tab │
│                     │     │  from git diff)      │     │                     │
└─────────────────────┘     └──────────────────────┘     └──────────┬──────────┘
                                                                    │
                                                          ┌─────────▼──────────┐
                                                          │ Policy Gate        │
                                                          │                    │
                                                          │ CVSS > 7.0 →      │
                                                          │ Block PR merge     │
                                                          └────────────────────┘
```

---

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Node.js 20+
- Python 3.12+

### 1. Clone & configure
```bash
git clone https://github.com/0xnithinmys/ArmorScan-AI.git
cd ArmorScan-AI
cp .env.example .env
# Fill in your API keys
```

### 2. Start all services (Docker)
```bash
docker compose up -d
```

### 3. Or run individually for development

**Frontend** (hot reload):
```bash
cd frontend
npm install
npm run dev
```

**Backend** (hot reload):
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Optional scanner CLIs** (Phase 7):
```bash
pip install semgrep bandit
# Install nuclei separately from ProjectDiscovery, then ensure `nuclei` is on PATH.
```

**Report exports** (Phase 8):
- JSON: `GET /api/v1/reports/{scan_id}/json`
- SARIF: `GET /api/v1/reports/{scan_id}/sarif`
- PDF: `GET /api/v1/reports/{scan_id}/pdf`
- Markdown: `GET /api/v1/reports/{scan_id}/markdown`

**Celery worker**:
```bash
cd backend
celery -A app.core.celery_app worker --loglevel=info -Q scans
```

---

## Service URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Celery Flower | http://localhost:5555 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

---

## Roadmap

- [x] **Phase 1** — Project foundation & monorepo setup
- [x] **Phase 2** — Frontend dashboard & UI (Next.js)
- [x] **Phase 3** — Backend API (FastAPI + PostgreSQL)
- [x] **Phase 4** — AI agent system (LangGraph)
- [x] **Phase 5** — Browser automation (Playwright)
- [x] **Phase 6** — Policy engine (ArmorIQ)
- [x] **Phase 7** — Scanning engines (Nuclei, Semgrep, Bandit)
- [x] **Phase 8** — Risk scoring & reporting engine
- [ ] **Phase 9** — CI/CD integration
- [ ] **Phase 10** — Production deployment (K8s)
- [ ] **Phase 11** — Testing & QA

### Future

- Multimodal Vision Language Models for canvas/clickjacking detection
- Deep RL-trained agents via self-play against vulnerable apps
- Autonomous remediation — auto-generate and submit fix PRs
- Continuous adversarial simulation against production environments

---

