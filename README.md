# Bundlescope

AI-powered Kubernetes support bundle analyzer. Upload a [Troubleshoot](https://troubleshoot.sh) support bundle, get evidence-grounded findings, root cause analysis, and remediation steps.

![Bundlescope](https://img.shields.io/badge/status-prototype-blue) ![Next.js](https://img.shields.io/badge/frontend-Next.js_14-black) ![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688) ![GPT-4o](https://img.shields.io/badge/AI-GPT--4o-412991)

## How It Works

Bundlescope runs a **4-pass analysis pipeline**:

1. **Heuristic Triage** — Deterministic pattern matching for known K8s failures (CrashLoopBackOff, OOMKilled, ImagePullBackOff, exit codes, probe failures). Fast, reliable, no AI needed.
2. **AI Deep Analysis** — Per-namespace LLM analysis with focused context: pod specs, log excerpts, events. Domain-specific prompts with K8s expertise.
3. **Root Cause Synthesis** — Connects findings into causal chains. "A caused B caused C. Fix A first."
4. **Remediation** — Specific kubectl commands and config changes for each finding.

Results stream in real-time via SSE — watch findings appear as the engine works.

## Quick Start

### With Docker Compose

```bash
git clone <repo-url> && cd bundlescope
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
docker compose up --build
```

Open http://localhost:3000 and upload a support bundle.

### Local Development

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
OPENAI_API_KEY=your-key uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

## Generating a Test Bundle

If you have a Kubernetes cluster (kind/minikube):

```bash
# Create a cluster with intentional failures
./scripts/setup-test-cluster.sh

# Generate a support bundle
./scripts/generate-bundle.sh
```

This creates `samples/sample-bundle.tar.gz` with OOMKilled, CrashLoopBackOff, ImagePullBackOff, and probe failure scenarios.

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────┐
│  Next.js 14     │     │  FastAPI Backend                         │
│  Dark Theme UI  │────▶│                                          │
│  shadcn/ui      │ SSE │  Upload → Parse → Heuristic → AI → SSE  │
│  Streaming      │◀────│                                          │
└─────────────────┘     └──────────────────────────────────────────┘
                                        │
                                        ▼
                                   OpenAI GPT-4o
```

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Backend | Python, FastAPI, Pydantic |
| AI | OpenAI GPT-4o (configurable) |
| Streaming | Server-Sent Events |
| Deployment | Docker Compose |

## Features

- **Drag-and-drop upload** with real-time extraction progress
- **Streaming analysis** — findings appear live via SSE
- **Evidence-grounded findings** — every issue cites actual log lines, events, configs
- **Health score** — 0-100 cluster health assessment
- **Severity filtering** — Critical / Warning / Info with counts
- **Timeline view** — chronological event cascade
- **Interactive chat** — ask follow-up questions about the bundle
- **Remediation steps** — specific kubectl commands and config fixes

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o` | Model to use |
| `OPENAI_BASE_URL` | No | OpenAI default | Custom API endpoint |

## Project Structure

```
bundlescope/
├── frontend/          Next.js app
│   ├── src/app/       Pages (upload, analysis dashboard)
│   ├── src/components/ UI components
│   └── src/lib/       API client, types, hooks
├── backend/           FastAPI app
│   ├── routers/       API endpoints
│   ├── services/      Bundle parser, heuristic engine, AI analyzer
│   ├── models/        Pydantic data models
│   └── prompts/       LLM prompt templates
├── scripts/           Test cluster setup
└── docker-compose.yml One-command deployment
```
