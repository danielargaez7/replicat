<p align="center">
  <img src="https://img.shields.io/badge/status-production--ready-brightgreen" alt="Status" />
  <img src="https://img.shields.io/badge/frontend-Next.js_16-black" alt="Next.js" />
  <img src="https://img.shields.io/badge/backend-FastAPI-009688" alt="FastAPI" />
  <img src="https://img.shields.io/badge/AI-GPT--4o-412991" alt="GPT-4o" />
  <img src="https://img.shields.io/badge/tests-71_passing-brightgreen" alt="Tests" />
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License" />
</p>

# Bundlescope

**AI-powered Kubernetes support bundle analyzer.** Upload a [Troubleshoot](https://troubleshoot.sh) support bundle, get evidence-grounded findings, root cause analysis, and actionable remediation steps — streamed in real time.

Bundlescope bridges the gap between raw observability data and actionable insight, intelligently deciding which parts of that bridge need AI and which don't.

---

## Why Bundlescope?

Debugging a Kubernetes cluster from a support bundle is like reading a novel written by 50 different authors in 50 different languages. Bundlescope reads it for you.

- **Not another "send everything to GPT" tool.** The 4-pass pipeline uses deterministic heuristics first, AI second. Fast, reliable, and cost-efficient.
- **Evidence-grounded.** Every finding cites the actual log line, event, or config that proves it. No hallucinated diagnostics.
- **Real-time streaming.** Watch findings appear live as the analysis progresses — no waiting for the full pipeline to finish.
- **Graceful degradation.** No API key? No problem. Heuristic analysis runs without any external dependencies.

---

## How It Works

Bundlescope runs a **4-pass analysis pipeline** on every support bundle:

```
┌─────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  1. HEURISTIC │──▶│  2. AI DEEP  │──▶│ 3. SYNTHESIS │──▶│ 4. REMEDIATE │
│    TRIAGE     │   │   ANALYSIS   │   │  ROOT CAUSE  │   │    ACTION    │
│               │   │              │   │              │   │              │
│ Pattern match │   │ Per-namespace│   │ Causal chain │   │ kubectl cmds │
│ known K8s     │   │ LLM analysis │   │ "A caused B  │   │ config fixes │
│ failures      │   │ with focused │   │  caused C.   │   │ for each     │
│               │   │ context      │   │  Fix A first"│   │ finding      │
│ Zero API calls│   │              │   │              │   │              │
└─────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
     Fast &              Smart             Connected           Actionable
   Deterministic       & Targeted          Narrative            & Specific
```

**Pass 1: Heuristic Triage** — Deterministic pattern matching for known Kubernetes failure signatures: CrashLoopBackOff, OOMKilled (exit code 137), ImagePullBackOff, probe failures, node pressure conditions. Fast, reliable, no AI needed.

**Pass 2: AI Deep Analysis** — Per-namespace LLM analysis with curated context windows: pod specs, error-line log excerpts, correlated events. Domain-specific prompts include K8s expertise (exit code tables, common failure cascades).

**Pass 3: Root Cause Synthesis** — Connects findings across namespaces into causal chains. Identifies the root issue and prioritizes what to fix first.

**Pass 4: Remediation** — Generates specific `kubectl` commands and config changes for each finding. Copy-paste ready.

---

## Quick Start

### With Docker Compose (Recommended)

```bash
git clone https://github.com/danielargaez7/replicat.git && cd replicat
cp .env.example .env
```

Edit `.env` and add your OpenAI API key (optional — heuristic analysis works without it):

```env
OPENAI_API_KEY=sk-your-key-here
```

```bash
docker compose up --build
```

Open **http://localhost:3000** and upload a support bundle.

### Local Development

**Backend:**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**.

### Generating a Test Bundle

If you have a Kubernetes cluster (kind/minikube):

```bash
# Create a cluster with intentional failures
./scripts/setup-test-cluster.sh

# Generate a support bundle
./scripts/generate-bundle.sh
```

This creates `samples/sample-bundle.tar.gz` with OOMKilled, CrashLoopBackOff, ImagePullBackOff, and probe failure scenarios — perfect for testing the full pipeline.

---

## Features

### Command Center Dashboard

- **Health Score Gauge** — SVG ring visualization with real-time animated scoring (0-100)
- **Severity Distribution** — Donut chart breaking down Critical / Warning / Info findings
- **Priority Alerts** — Top findings sorted by severity with color-coded indicators
- **Root Cause Analysis** — Terminal-style panel with causal chain narrative
- **Bottom Stats Grid** — At-a-glance metrics with progress bars

### Analysis Engine

- **Drag-and-drop upload** with real-time extraction progress
- **Streaming analysis** — findings appear live via Server-Sent Events
- **Evidence-grounded findings** — every issue cites actual log lines, events, and configs
- **Severity filtering** — filter findings by Critical / Warning / Info
- **Timeline view** — chronological event cascade with severity-coded dots
- **Interactive AI chat** — ask follow-up questions about the bundle with suggested prompts
- **Remediation steps** — specific kubectl commands and config fixes for each finding

### Design

- **Glassmorphism UI** — frosted glass panels with backdrop blur throughout
- **Material Design 3** color system with 40+ semantic tokens
- **Space Grotesk + Manrope** typography with Material Symbols icons
- **Floating crystal animations** with pink/purple glow and sparkle particle effects
- **Obsidian grid** background with scanning line and fog overlay effects
- **Sidebar navigation** with active state indicators
- **Fully responsive** — works on desktop and tablet

### Security & Production Readiness

- **Request ID tracking** — every request/response tagged with a unique UUID for tracing
- **OWASP security headers** — X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, HSTS, Referrer-Policy, Permissions-Policy
- **Upload size limits** — 500MB max enforced at middleware AND stream level (defense in depth)
- **Path traversal protection** — `Path.resolve()` with prefix validation on all file access
- **Input sanitization** — control character stripping, prompt injection detection, max length enforcement
- **UUID validation** — all analysis IDs validated before database queries (blocks SQL injection)
- **Rate limiting** — SlowAPI with configurable per-endpoint limits (upload: 10/min, chat: 20/min, analysis: 30/min)
- **Global exception handler** — catches unhandled errors, returns safe JSON responses, never leaks stack traces
- **Request logging** — structured logs with method, path, status code, duration, and request ID
- **CORS configuration** — explicit origin whitelist with configurable env var
- **OpenAI timeout** — 30s timeout with graceful error messages
- **Docs disabled in production** — `/docs` endpoint only available in non-production environments

---

## Architecture

```
┌──────────────────────┐        ┌───────────────────────────────────────────┐
│  Next.js 16          │        │  FastAPI Backend                          │
│  React 19            │        │                                           │
│  Tailwind CSS 4      │───────▶│  Upload → Parse → Heuristic → AI → SSE   │
│  Material Design 3   │  SSE   │                                           │
│  Glassmorphism UI    │◀───────│  Middleware: Security │ Rate Limit │ Logs  │
│                      │        │                                           │
└──────────────────────┘        └──────────────┬────────────────────────────┘
                                               │
                                    ┌──────────┼──────────┐
                                    │          │          │
                                    ▼          ▼          ▼
                               PostgreSQL    Redis    OpenAI GPT-4o
                               (storage)    (cache)   (AI analysis)
```

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, Material Symbols |
| Backend | Python, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) |
| Database | PostgreSQL with asyncpg |
| Cache | Redis with 24-hour TTL |
| AI | OpenAI GPT-4o (configurable model and base URL) |
| Streaming | Server-Sent Events (SSE) |
| Security | SlowAPI rate limiting, OWASP headers, path traversal protection |
| Testing | pytest with 71 tests (async, in-memory SQLite) |
| Deployment | Docker Compose |

---

## Project Structure

```
bundlescope/
├── frontend/                    Next.js 16 application
│   ├── src/app/                 Pages (upload homepage, analysis dashboard)
│   ├── src/components/
│   │   ├── analysis/            Domain components (HealthScore, FindingCard, ChatPanel, etc.)
│   │   └── ui/                  Base UI components (shadcn/ui primitives)
│   └── src/lib/                 API client, TypeScript types, hooks
│
├── backend/                     FastAPI application
│   ├── routers/                 API endpoints (upload, analysis, chat)
│   ├── services/                Bundle parser, heuristic engine, AI analyzer, pipeline
│   ├── models/                  Pydantic data models
│   ├── prompts/                 LLM prompt templates
│   ├── middleware.py            Security headers, request ID, logging, upload limits
│   ├── security.py              Path traversal, input sanitization, validation
│   ├── rate_limit.py            SlowAPI rate limiting configuration
│   ├── cache.py                 Redis cache management
│   └── tests/                   71 tests across 7 test files
│       ├── test_security.py     Path traversal, sanitization, validation (20 tests)
│       ├── test_api_upload.py   Upload endpoint tests (9 tests)
│       ├── test_api_analysis.py Analysis endpoint tests (8 tests)
│       ├── test_api_chat.py     Chat endpoint tests (5 tests)
│       ├── test_middleware.py   Middleware tests (6 tests)
│       ├── test_cache.py        Cache operation tests (7 tests)
│       └── test_models.py       Pydantic model tests (9 tests)
│
├── scripts/                     Test cluster setup and bundle generation
├── samples/                     Sample support bundles
├── docker-compose.yml           One-command deployment (app + PostgreSQL + Redis)
└── .env.example                 Environment variable template
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | No* | — | OpenAI API key (*heuristic analysis works without it) |
| `OPENAI_MODEL` | No | `gpt-4o` | LLM model to use |
| `OPENAI_BASE_URL` | No | OpenAI default | Custom API endpoint (for OpenAI-compatible APIs) |
| `DATABASE_URL` | No | Local PostgreSQL | PostgreSQL connection string |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection string |
| `CORS_ORIGINS` | No | `localhost:3000,3001` | Comma-separated allowed origins |
| `BUNDLESCOPE_ENV` | No | `development` | Set to `production` to disable `/docs` |
| `RATE_LIMIT_UPLOAD` | No | `10/minute` | Upload endpoint rate limit |
| `RATE_LIMIT_CHAT` | No | `20/minute` | Chat endpoint rate limit |
| `RATE_LIMIT_ANALYSIS` | No | `30/minute` | Analysis endpoint rate limit |
| `RATE_LIMIT_DEFAULT` | No | `60/minute` | Default rate limit for all endpoints |

---

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

```
========================= 71 passed in 0.67s =========================
```

Tests run against an in-memory SQLite database with mocked Redis — no external services needed.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload a support bundle (.tar.gz / .tgz) |
| `GET` | `/api/analyses` | List all analyses |
| `GET` | `/api/analyses/{id}` | Get analysis metadata |
| `GET` | `/api/analysis/{id}` | Get complete analysis results |
| `GET` | `/api/analysis/{id}/stream` | SSE stream for real-time analysis |
| `GET` | `/api/analysis/{id}/logs?path=` | Retrieve specific log files |
| `GET` | `/api/analysis/{id}/files` | Get bundle file tree |
| `POST` | `/api/analysis/{id}/chat` | Chat about analysis results |
| `GET` | `/health` | Health check (API + PostgreSQL + Redis) |

---

## Design Philosophy

> The most important architectural choice: **don't treat this as a "send everything to GPT" problem.**

Support bundles contain structured, well-defined data — pod statuses, exit codes, event reasons, resource states. Many failure modes are deterministic and well-documented. Using AI for what pattern matching can do is wasteful and less reliable.

The 4-pass pipeline means the system produces useful results **even when the AI layer is unavailable**. The heuristic pass catches the most common and well-understood failures instantly. AI is reserved for the nuanced work: correlating signals across namespaces, identifying cascading failures, and generating human-readable root cause narratives.

Every finding in Bundlescope cites specific evidence: the actual exit code, the actual event message, the actual log line. No "there might be issues with your deployment."

---

## What's Next

- **Agentic investigation** — Give the LLM tools to query the bundle (`get_pod_logs`, `get_events`, `check_resource_limits`) and let it investigate iteratively
- **Bundle comparison** — Diff two bundles to see what changed between them
- **Pattern library** — Learn new failure signatures from resolved support cases
- **Structured report export** — PDF/Markdown reports for sharing with teams
- **Authentication** — API key / JWT / OAuth2 for multi-tenant deployments
