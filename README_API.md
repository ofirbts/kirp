# Brand OS v3 API — Complete Documentation

FastAPI app that runs the Brand OS v3 orchestrator and returns `final_output_format`. The system includes Python SDK, CLI, scheduler, monitoring dashboard, Next.js UI, integrations (WhatsApp, LinkedIn), KIRP integration, n8n workflow, and E2E test suite.

---

## Full System Overview

Brand OS v3 is a multi-agent pipeline that produces on-brand, platform-adapted content (headline, body, hook, CTA, visual spec) from tenant_id, platform, and topic_hint. Config and agent definitions live under `brand_os_v3/config/` and `brand_os_v3/agents/`. The pipeline runs: CONTEXT_SCANNER → STRATEGIC_PLANNER → TECHNICAL_STORYTELLER → HUMAN_EDGE → IDENTITY_GUARDIAN → SKEPTICAL_CTO → VISUAL_GENERATOR → GROWTH_ANALYST, with two gatekeepers that can reject and trigger one revision loop each.

**Components:**
- **Core** (brand_os_v3/) — config, agents, workflow, execution, KIRP, n8n
- **SDK** (brand_os_sdk/) — Python SDK: load_identity, load_voice, list_agents, run_orchestrator, handle_kirp_event
- **API** (api/) — FastAPI: POST /brand-os/run, GET /health
- **CLI** (brand_os_cli/) — Click: brandos run, brandos daily, brandos signals, brandos agents
- **Scheduler** (brand_os_scheduler/) — APScheduler daily job at 08:00
- **Monitoring** (brand_os_monitoring/) — FastAPI + Jinja2: /metrics, /dashboard
- **UI** (unified KIRP UI at repo root) — Next.js 14: /dashboard, /run, /history, /agents, /visuals, Mission Control, etc.
- **Integrations** (brand_os_integrations/) — Twilio WhatsApp, LinkedIn API v2
- **E2E tests** (tests_e2e/) — 11 test groups (config, SDK, API, KIRP, CLI, scheduler, monitoring, integrations, n8n, UI, Docker)

---

## Architecture (ASCII)

```
  Client / CLI / n8n / KIRP / Scheduler
         │
         ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  FastAPI api/main.py                                             │
  │  POST /brand-os/run  →  brand_os_sdk.run_orchestrator()          │
  │  GET  /health        →  {"status": "ok"}                        │
  └──────────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  brand_os_sdk (Python)                                           │
  │  config_loader: load_identity(), load_voice(), list_agents()    │
  │  orchestrator: run_orchestrator(input_payload)                  │
  │  kirp_integration: handle_kirp_event(event)                      │
  └──────────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  brand_os_v3/                                                    │
  │  config/, agents/, workflow/, execution/, kirp/, n8n/            │
  └──────────────────────────────────────────────────────────────────┘
         │
         ├─── Publish: WhatsApp (Twilio), LinkedIn (API v2)
         ├─── Monitor: brand_os_monitoring (/metrics, /dashboard)
         └─── UI: brand_os_ui (Next.js 14)
```

---

## Prerequisites

- Python 3.10+
- Node.js 18+ (for unified UI)
- Brand OS v3 assets under `brand_os_v3/` (config, agents, execution, workflow)

---

## Install

From repo root:

```bash
pip install -e .
```

Or install dependencies only:

```bash
pip install "fastapi>=0.109.0" "uvicorn[standard]>=0.27.0" "pydantic>=2.0.0" \
            "click>=8.0.0" "requests>=2.28.0" "apscheduler>=3.10.0" \
            "jinja2>=3.1.0" "twilio>=8.0.0"
```

---

## Run the API (Local)

From repo root:

```bash
uvicorn api.main:app --reload
```

- API base: `http://127.0.0.1:8000`
- OpenAPI docs: `http://127.0.0.1:8000/docs`
- Health: `GET /health` → `{"status": "ok", "service": "brand-os-v3-api"}`

---

## API Usage

### POST /brand-os/run

Runs the Brand OS v3 pipeline and returns final_output_format.

**Request body:**

```json
{
  "tenant_id": "tenant-1",
  "platform": "linkedin",
  "topic_hint": "API release",
  "trace_id": null,
  "extra_context": null
}
```

- **tenant_id** (required) — Tenant identifier
- **platform** (required) — linkedin | twitter | whatsapp
- **topic_hint** (required) — Topic hint for content generation
- **trace_id** (optional) — Trace ID; generated if omitted
- **extra_context** (optional) — Object with optional `signals` and `memory_entries` arrays

**Response:** final_output_format

```json
{
  "trace_id": "tr_12345",
  "tenant_id": "tenant-1",
  "platform": "linkedin",
  "topic_hint": "API release",
  "content": {
    "headline": "Auth as one line of config",
    "body": "What if you could ship every release without last-minute fires?\n\nWe just shipped an API change...",
    "hook_used": "What if you could ship every release without last-minute fires?",
    "cta_used": "Try it free →"
  },
  "visual_spec": {
    "image_prompt": "Minimal diagram: one line of code next to a lock icon...",
    "aspect_ratio": "1.91:1",
    "format": "png",
    "alt_text": "Diagram showing auth as one line of config with lock icon."
  },
  "recommendations": {
    "suggested_timing": "Tuesday or Wednesday 9am local",
    "hook_rotation": ["h1", "h2"],
    "cta_rotation": ["c1", "c2"],
    "next_topic_hints": ["DevEx metrics", "Security vs speed"]
  },
  "status": "approved"
}
```

**Errors:**

- 503 — Brand OS config not found (e.g. missing brand_os_v3/)
- 400 — Invalid input (missing required fields or wrong types)
- 422 — Validation error (Pydantic)

---

## SDK Usage

### Load config and agents

```python
from brand_os_sdk import load_identity, load_voice, list_agents

identity = load_identity()  # config/00_Master_Identity_Core.json
voice = load_voice()        # config/03_Voice_Engine.json
agents = list_agents()      # ['CONTEXT_SCANNER', 'GROWTH_ANALYST', ...]
```

### Run the orchestrator

```python
from brand_os_sdk import run_orchestrator

result = run_orchestrator({
    "tenant_id": "tenant-1",
    "platform": "linkedin",
    "topic_hint": "API release",
    "extra_context": {"signals": [], "memory_entries": []},
})
# result: trace_id, tenant_id, platform, topic_hint, content, visual_spec, recommendations, status
```

---

## CLI Usage

### Install

After `pip install -e .`, the `brandos` command is available.

### Commands

**brandos run "<topic>"**

```bash
brandos run "API release" --tenant tenant-1 --platform linkedin --api
```

Prints: content, visual spec, recommendations, status.

**brandos daily**

```bash
brandos daily --tenant tenant-1 --platform linkedin --send-whatsapp +1234567890
```

Runs CONTEXT_SCANNER → pick best signal → run orchestrator → optional WhatsApp → append to memory log.

**brandos signals**

```bash
brandos signals --tenant tenant-1 --platform linkedin
```

Prints: world_context, trends, signals_used, memory_summary.

**brandos agents**

```bash
brandos agents
```

Prints: list of agents from brand_os_v3/agents/.

---

## Scheduler Usage

### Start the scheduler

```bash
python run_scheduler.py
```

Daily job at 08:00: CONTEXT_SCANNER → pick best signal → run orchestrator → optional WhatsApp → append to memory log.

**Env:** `BRAND_OS_TENANT_ID`, `BRAND_OS_PLATFORM`, `BRAND_OS_WHATSAPP_TO`

---

## Monitoring Dashboard

### Start the monitoring app

```bash
uvicorn brand_os_monitoring.app:app --port 8001 --reload
```

- Base: `http://127.0.0.1:8001`
- `/metrics` — JSON: total_runs, approved, rejected_identity, rejected_cto, avg_revisions, top_hooks, top_pillars
- `/dashboard` — HTML with Chart.js (doughnut: status distribution; bar: top topics)

Data source: `brand_os_v3/storage/content_memory_log.jsonl`

---

## UI Usage

### Start the UI

From repo root (unified KIRP UI):

```bash
npm run dev
```

- UI: `http://localhost:3100`

### Pages

- **/** — Home (links to dashboard and run)
- **/dashboard** — Latest runs, API health
- **/run** — Form to trigger POST /brand-os/run; displays result (content + visual spec)
- **/history** — Past runs from content memory log
- **/agents** — Agent definitions
- **/visuals** — Generated visual prompts

---

## Integrations

### WhatsApp (Twilio)

```python
from brand_os_integrations.whatsapp import send_whatsapp
send_whatsapp("+1234567890", "Hello from Brand OS!")
```

Env: `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_WHATSAPP_FROM`

### LinkedIn (API v2)

```python
from brand_os_integrations.linkedin import post_text, post_image
post_text("Hello from Brand OS!")
```

Env: `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN`, `LINKEDIN_ASSET_URN` (for images)

---

## Config Path

By default the SDK reads from `brand_os_v3/` next to the repo root. Override:

```bash
export BRAND_OS_V3_PATH=/path/to/brand_os_v3
uvicorn api.main:app --reload
```

---

## KIRP Integration

The SDK module **`brand_os_sdk.kirp_integration`** exposes **`handle_kirp_event(event: dict) -> Optional[dict]`** to route KIRP events:

| event_type | Behavior | Return |
|------------|----------|--------|
| **brand_os_run_started** or **brand_os_v3.workflow.started** | Runs orchestrator | final_output_format or None |
| **agent_completed** or **brand_os_v3.*.completed** | Acknowledge | `{"ack": true, "route": "agent_completed", "trace_id": ...}` |
| **gatekeeper_decision** or **brand_os_v3.identity.rejected** or **brand_os_v3.cto.rejected** | Acknowledge | `{"ack": true, "route": "gatekeeper_decision", "trace_id": ...}` |
| **run_completed** or **brand_os_v3.workflow.completed** | Acknowledge | `{"ack": true, "route": "run_completed", "trace_id": ...}` |
| **run_failed** | Acknowledge | `{"ack": true, "route": "run_failed", "trace_id": ...}` |

**Example event JSON:**

```json
{
  "event_type": "brand_os_run_started",
  "payload": {
    "tenant_id": "tenant-1",
    "platform": "linkedin",
    "topic_hint": "API release",
    "trace_id": "trace-001",
    "extra_context": {"signals": [], "memory_entries": []}
  }
}
```

**Example (Python):**

```python
from brand_os_sdk.kirp_integration import handle_kirp_event

event = {
    "event_type": "brand_os_run_started",
    "payload": {"tenant_id": "tenant-1", "platform": "linkedin", "topic_hint": "API release"}
}
result = handle_kirp_event(event)
# result: trace_id, content, visual_spec, recommendations, status, ...
```

Full KIRP event mapping and governance: **brand_os_v3/KIRP_INTEGRATION.md**.

---

## Deployment

### Local (API)

```bash
pip install "fastapi>=0.109.0" "uvicorn[standard]>=0.27.0" "pydantic>=2.0.0"
export BRAND_OS_V3_PATH=/path/to/brand_os_v3   # optional
uvicorn api.main:app --reload
```

API: `http://127.0.0.1:8000`

### Local (UI)

```bash
cd .  # repo root
npm install
npm run dev
```

UI: `http://localhost:3001`

### Docker (API)

```bash
docker build -f Dockerfile.brand_os_api -t brand-os-api .
docker run -p 8000:8000 brand-os-api
```

API: `http://localhost:8000`

### Docker (UI)

Create `Dockerfile` for UI (if needed):

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3001
CMD ["node", "server.js"]
```

Build and run:

```bash
cd .  # repo root
docker build -t brand-os-ui .
docker run -p 3001:3001 -e NEXT_PUBLIC_BRAND_OS_API_URL=http://host.docker.internal:8000 brand-os-ui
```

UI: `http://localhost:3001`

### n8n

Import **brand_os_v3/n8n/brand_os_v3_workflow.json** into n8n. Run with Manual Trigger; supply tenant_id, platform, topic_hint. For production: replace Code stubs with HTTP calls to the Brand OS API.

---

## E2E Tests

From repo root:

```bash
pytest -q tests_e2e/
```

**Test groups:**
- test_config_validity — Validate all JSON/YAML
- test_sdk — load_identity, load_voice, list_agents, run_orchestrator
- test_api — GET /health, POST /brand-os/run
- test_kirp_integration — handle_kirp_event routes
- test_cli — brandos commands
- test_scheduler — Daily job, mocks
- test_monitoring — /metrics, /dashboard
- test_integrations — send_whatsapp, post_text (mocked)
- test_n8n_workflow — name, nodes, connections
- test_ui_build — unified UI structure (app/, package.json at repo root)
- test_docker — Dockerfile.brand_os_api exists

---

## Resources

- **brand_os_v3/README.md** — System overview, architecture, modules, quick start, how to extend
- **brand_os_v3/KIRP_INTEGRATION.md** — KIRP events, governance, agent_specs alignment, SDK handle_kirp_event
- **brand_os_v3/OPERATIONS_MANUAL.md** — Full operations guide (setup, usage, deployment, cloud, CI/CD, multi-tenant, auto-learning, analytics)
- **brand_os_v3/FILE_MAP.md** — Complete file list, purpose, interactions, module, dependency graph, learning guide
- **Monitoring dashboard** — `http://127.0.0.1:8001/dashboard`
- **UI** — `http://localhost:3001`
