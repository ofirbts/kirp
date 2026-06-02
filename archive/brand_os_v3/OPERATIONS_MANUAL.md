# Brand OS v3.0 — Operations Manual

Complete production-grade operations guide for Brand OS v3: setup, deployment, usage, cloud deployment, CI/CD, multi-tenancy, auto-learning, and analytics.

---

## 1. Overview

Brand OS v3 is a multi-agent content pipeline that produces on-brand, platform-adapted content (headline, body, hook, CTA, visual spec) from tenant_id, platform, and topic_hint. The system includes:

- **Config** (brand_os_v3/config/) — identity, voice, agent mesh, world context, platform distribution, memory, hooks, visual identity
- **Agents** (brand_os_v3/agents/) — 8 agents: CONTEXT_SCANNER, STRATEGIC_PLANNER, TECHNICAL_STORYTELLER, HUMAN_EDGE, IDENTITY_GUARDIAN, SKEPTICAL_CTO, VISUAL_GENERATOR, GROWTH_ANALYST
- **Workflow** (brand_os_v3/workflow/) — orchestration flow with gatekeeper loops
- **Execution** (brand_os_v3/execution/) — EXECUTION_TEMPLATE with system prompt, agent order, revision rules
- **KIRP** (brand_os_v3/kirp/) — governance policy, agent specs, workflow mapping (YAML)
- **n8n** (brand_os_v3/n8n/) — real n8n workflow export
- **SDK** (brand_os_sdk/) — Python SDK: load_identity, load_voice, list_agents, run_orchestrator, handle_kirp_event
- **API** (api/) — FastAPI: POST /brand-os/run, GET /health
- **CLI** (brand_os_cli/) — Click CLI: brandos run, brandos daily, brandos signals, brandos agents
- **Scheduler** (brand_os_scheduler/) — APScheduler daily job at 08:00
- **Monitoring** (brand_os_monitoring/) — FastAPI + Jinja2: /metrics, /dashboard
- **UI** (brand_os_ui/) — Next.js 14 App Router: /dashboard, /run, /history, /agents, /visuals
- **Integrations** (brand_os_integrations/) — Twilio WhatsApp, LinkedIn API v2
- **E2E tests** (tests_e2e/) — 11 test groups (config, SDK, API, KIRP, CLI, scheduler, monitoring, integrations, n8n, UI, Docker)

---

## 2. Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           BRAND OS v3 ECOSYSTEM                             │
└────────────────────────────────────────────────────────────────────────────┘
         │
         ├─── Trigger (CLI, API, n8n, KIRP event, Scheduler)
         │
         ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR (brand_os_sdk.run_orchestrator)                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Prepare Input → CONTEXT_SCANNER → STRATEGIC_PLANNER →               │  │
│  │ TECHNICAL_STORYTELLER → HUMAN_EDGE → IDENTITY_GUARDIAN (gatekeeper) │  │
│  │ → IF approved → SKEPTICAL_CTO (gatekeeper) → IF approved →          │  │
│  │ VISUAL_GENERATOR → Logging → GROWTH_ANALYST → Final Output          │  │
│  │                                                                      │  │
│  │ Revision loops: IDENTITY_GUARDIAN reject → HUMAN_EDGE (max 1)       │  │
│  │                 SKEPTICAL_CTO reject → HUMAN_EDGE (max 1)            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  OUTPUT (final_output_format)                                              │
│  trace_id, tenant_id, platform, topic_hint                                 │
│  content: headline, body, hook_used, cta_used                              │
│  visual_spec: image_prompt, aspect_ratio, format, alt_text                 │
│  recommendations: suggested_timing, hook_rotation, cta_rotation, topics    │
│  status: approved | rejected_identity | rejected_cto                       │
└────────────────────────────────────────────────────────────────────────────┘
         │
         ├─── Publish (WhatsApp, LinkedIn, log to memory)
         └─── Monitor (brand_os_monitoring /metrics, /dashboard)
```

---

## 3. Environment Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ (for brand_os_ui)
- Docker (optional)
- n8n (optional)

### Install Python dependencies

From repo root:

```bash
pip install -e .
```

Or install dependencies only:

```bash
pip install "fastapi>=0.109.0" "uvicorn[standard]>=0.27.0" "pydantic>=2.0.0" \
            "click>=8.0.0" "requests>=2.28.0" "apscheduler>=3.10.0" \
            "jinja2>=3.1.0" "twilio>=8.0.0" "pytest>=7.0.0" "pyyaml>=6.0.0"
```

### Install UI dependencies

From `brand_os_ui/`:

```bash
cd brand_os_ui
npm install
```

### Environment variables

Create `.env` in repo root:

```bash
# Brand OS v3 config path (default: repo_root/brand_os_v3)
BRAND_OS_V3_PATH=/path/to/brand_os_v3

# API URL for CLI (default: http://127.0.0.1:8000)
BRAND_OS_API_URL=http://127.0.0.1:8000

# Scheduler settings
BRAND_OS_TENANT_ID=default
BRAND_OS_PLATFORM=linkedin
BRAND_OS_WHATSAPP_TO=+1234567890

# Twilio WhatsApp
TWILIO_SID=your_sid
TWILIO_TOKEN=your_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# LinkedIn API v2
LINKEDIN_ACCESS_TOKEN=your_token
LINKEDIN_PERSON_URN=urn:li:person:YOUR_ID
LINKEDIN_ASSET_URN=urn:li:digitalmediaAsset:YOUR_ASSET_ID

# UI API URL (default: http://127.0.0.1:8000)
NEXT_PUBLIC_BRAND_OS_API_URL=http://127.0.0.1:8000
```

---

## 4. API Usage

### Start the API

From repo root:

```bash
uvicorn api.main:app --reload
```

- Base: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`

### Endpoints

**GET /health**

```bash
curl http://127.0.0.1:8000/health
```

Response: `{"status": "ok", "service": "brand-os-v3-api"}`

**POST /brand-os/run**

```bash
curl -X POST http://127.0.0.1:8000/brand-os/run \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-1",
    "platform": "linkedin",
    "topic_hint": "API release"
  }'
```

Response:

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

---

## 5. SDK Usage

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

### Handle KIRP events

```python
from brand_os_sdk.kirp_integration import handle_kirp_event

event = {
    "event_type": "brand_os_run_started",
    "payload": {
        "tenant_id": "tenant-1",
        "platform": "linkedin",
        "topic_hint": "API release"
    }
}
result = handle_kirp_event(event)
# result is final_output_format or ack dict
```

---

## 6. CLI Usage

### Install

After `pip install -e .`, the `brandos` command is available.

### Commands

**brandos run "<topic>"**

```bash
brandos run "API release" --tenant tenant-1 --platform linkedin --api
```

Options:
- `--tenant`, `-t` — Tenant ID (default: default)
- `--platform`, `-p` — linkedin | twitter | whatsapp (default: linkedin)
- `--trace-id` — Optional trace ID
- `--api` / `--sdk` — Use API (default) or SDK

Output: content, visual spec, recommendations, status.

**brandos daily**

```bash
brandos daily --tenant tenant-1 --platform linkedin --send-whatsapp +1234567890
```

Steps: CONTEXT_SCANNER → pick best signal → run orchestrator → optional WhatsApp → append to content memory log.

**brandos signals**

```bash
brandos signals --tenant tenant-1 --platform linkedin
```

Runs CONTEXT_SCANNER and prints world_context, trends, signals_used, memory_summary.

**brandos agents**

```bash
brandos agents
```

Prints list of agents from brand_os_v3/agents/.

---

## 7. Scheduler Usage

### Start the scheduler

From repo root:

```bash
python run_scheduler.py
```

Or:

```bash
python -m brand_os_scheduler.scheduler
```

The scheduler runs a daily job at 08:00 (local time) that:
1. Runs CONTEXT_SCANNER via SDK
2. Picks the highest-relevance signal (or "daily" if none)
3. Runs run_orchestrator()
4. Sends WhatsApp message (if `BRAND_OS_WHATSAPP_TO` is set)
5. Appends to content memory log (brand_os_v3/storage/content_memory_log.jsonl)

Environment variables:
- `BRAND_OS_TENANT_ID` (default: default)
- `BRAND_OS_PLATFORM` (default: linkedin)
- `BRAND_OS_WHATSAPP_TO` (optional: phone number)

---

## 8. Monitoring Dashboard

### Start the monitoring app

From repo root:

```bash
uvicorn brand_os_monitoring.app:app --port 8001 --reload
```

- Base: `http://127.0.0.1:8001`

### Endpoints

**GET /metrics** — JSON:

```json
{
  "total_runs": 42,
  "approved": 38,
  "rejected_identity": 2,
  "rejected_cto": 2,
  "avg_revisions": 0.0,
  "top_hooks": [{"topic": "API release", "count": 5}, ...],
  "top_pillars": [{"platform": "linkedin", "count": 30}, ...]
}
```

**GET /dashboard** — HTML with Chart.js (doughnut: status distribution; bar: top topics).

Data source: `brand_os_v3/storage/content_memory_log.jsonl` (or path from `BRAND_OS_V3_PATH`).

---

## 9. UI Usage

### Start the UI

From `brand_os_ui/`:

```bash
npm run dev
```

- UI: `http://localhost:3001`

### Pages

- **/** — Home (links to dashboard and run)
- **/dashboard** — Latest runs, API health
- **/run** — Form to trigger POST /brand-os/run (tenant, platform, topic_hint); displays result (content + visual spec)
- **/history** — Past runs from content memory log (stub: calls /api/history)
- **/agents** — Agent definitions (calls /api/agents)
- **/visuals** — Generated visual prompts (calls /api/visuals)

### Build for production

```bash
cd brand_os_ui
npm run build
npm start
```

---

## 10. WhatsApp Integration

### Setup

Install Twilio SDK:

```bash
pip install "twilio>=8.0.0"
```

Set environment variables:

```bash
export TWILIO_SID=your_sid
export TWILIO_TOKEN=your_token
export TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

### Send a message

```python
from brand_os_integrations.whatsapp import send_whatsapp

result = send_whatsapp("+1234567890", "Hello from Brand OS!")
# result: {"ok": True, "sid": "SM...", "status": "sent"} or {"ok": False, "error": "..."}
```

---

## 11. LinkedIn Integration

### Setup

Get a LinkedIn access token (OAuth 2.0) with permissions: `w_member_social`. Set:

```bash
export LINKEDIN_ACCESS_TOKEN=your_token
export LINKEDIN_PERSON_URN=urn:li:person:YOUR_ID
```

### Post text

```python
from brand_os_integrations.linkedin import post_text

result = post_text("Hello from Brand OS!")
# result: {"ok": True, "status": 201, "data": {...}} or {"ok": False, "error": "..."}
```

### Post image

First register an image via LinkedIn Assets API (upload image, get asset URN). Then:

```bash
export LINKEDIN_ASSET_URN=urn:li:digitalmediaAsset:YOUR_ASSET_ID
```

```python
from brand_os_integrations.linkedin import post_image

result = post_image("Check out this visual.", "Minimal diagram")
# result: {"ok": True, ...} or {"ok": False, "error": "..."}
```

---

## 12. n8n Workflow Usage

### Import

Open n8n, go to Workflows → Import from File → select `brand_os_v3/n8n/brand_os_v3_workflow.json`.

### Run

1. Open the workflow "Brand OS v3 — Master Orchestrator".
2. Click "Execute Workflow" (Manual Trigger).
3. In the trigger payload, provide:
   ```json
   {
     "tenant_id": "tenant-1",
     "platform": "linkedin",
     "topic_hint": "API release"
   }
   ```
4. Execute. The workflow runs: Prepare Input → CONTEXT_SCANNER → … → Final Output JSON.
5. Read the output from the "Final Output JSON" node.

### Nodes

- **Manual Trigger** — Start
- **Prepare Input** — Code: normalizes input, sets trace_id
- **CONTEXT_SCANNER** — Code: stub context_brief
- **STRATEGIC_PLANNER** — Code: stub content_brief
- **TECHNICAL_STORYTELLER** — Code: stub draft
- **HUMAN_EDGE** — Code: stub human_draft
- **IDENTITY_GUARDIAN** — Code: identity_result (approved, score, reasons, suggested_fixes)
- **Identity Approved?** — IF: true → SKEPTICAL_CTO; false → Revision (Identity)
- **Revision (Identity)** — Code: revises draft; loops back to HUMAN_EDGE
- **SKEPTICAL_CTO** — Code: cto_result (approved, claims_checked, issues, suggested_fixes)
- **CTO Approved?** — IF: true → VISUAL_GENERATOR; false → Revision (CTO)
- **Revision (CTO)** — Code: revises draft; loops back to HUMAN_EDGE
- **VISUAL_GENERATOR** — HTTP Request (placeholder URL); continueOnFail
- **Visual Brief Fallback** — Code: builds visual_spec from input or SKEPTICAL_CTO context
- **Logging** — Code: logs trace_id, tenant_id, platform, event
- **Final Output JSON** — Set: assembles content, visual, gatekeeper_results, timestamp

For production: replace Code stubs with HTTP calls to the Brand OS API or an LLM.

---

## 13. E2E Tests

### Run all tests

From repo root:

```bash
pytest -q tests_e2e/
```

### Test groups

- **test_config_validity.py** — Validate all JSON (config, agents, workflow, execution) and YAML (kirp)
- **test_sdk.py** — load_identity, load_voice, list_agents, run_orchestrator
- **test_api.py** — FastAPI TestClient: GET /health, POST /brand-os/run (valid + 422)
- **test_kirp_integration.py** — handle_kirp_event routes
- **test_cli.py** — CliRunner: brandos agents, run, signals, daily
- **test_scheduler.py** — Daily job registration, _pick_best_signal, daily_job (mocked; skips if apscheduler missing)
- **test_monitoring.py** — /metrics, /dashboard HTML
- **test_integrations.py** — send_whatsapp (env + Twilio mock), post_text (env + LinkedIn mock)
- **test_n8n_workflow.py** — name, nodes, connections, no orphans
- **test_ui_build.py** — brand_os_ui package.json, next.config, app dir, pages (skips if brand_os_ui missing)
- **test_docker.py** — Dockerfile.brand_os_api exists and content

---

## 14. Docker Deployment

### Build the API image

From repo root:

```bash
docker build -f Dockerfile.brand_os_api -t brand-os-api .
```

### Run the API container

```bash
docker run -p 8000:8000 \
  -e BRAND_OS_V3_PATH=/app/brand_os_v3 \
  brand-os-api
```

API: `http://localhost:8000`. POST /brand-os/run with tenant_id, platform, topic_hint.

### Build the UI image

From `brand_os_ui/`:

```bash
docker build -t brand-os-ui .
```

Dockerfile for UI (create `brand_os_ui/Dockerfile`):

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

Run:

```bash
docker run -p 3001:3001 \
  -e NEXT_PUBLIC_BRAND_OS_API_URL=http://host.docker.internal:8000 \
  brand-os-ui
```

UI: `http://localhost:3001`.

---

## 15. Troubleshooting

### API returns 503 (config not found)

- Check `BRAND_OS_V3_PATH` points to the correct directory.
- Verify `brand_os_v3/config/` and `brand_os_v3/agents/` exist.

### API returns 400 (invalid input)

- Ensure tenant_id, platform, topic_hint are provided.
- platform must be one of: linkedin, twitter, whatsapp.

### CLI fails with "SDK not available"

- Install brand_os_sdk: `pip install -e .` from repo root.
- Check `BRAND_OS_V3_PATH` is set or brand_os_v3/ is next to the repo root.

### Scheduler doesn't run

- Install apscheduler: `pip install "apscheduler>=3.10.0"`.
- Run `python run_scheduler.py` (blocks; runs daily at 08:00).

### Monitoring dashboard shows 0 runs

- Run the pipeline at least once (API, CLI, or SDK).
- Check `brand_os_v3/storage/content_memory_log.jsonl` exists and has entries.

### UI pages return 404 for /api/history, /api/agents, /api/visuals

- Those are Next.js API routes (stubs). They return empty arrays or default data.
- For production: implement API routes that read from content memory log or the Brand OS API.

### WhatsApp send fails

- Check `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_WHATSAPP_FROM` are set.
- Verify phone number is E.164 format (e.g. +1234567890).
- Install twilio: `pip install "twilio>=8.0.0"`.

### LinkedIn post fails

- Check `LINKEDIN_ACCESS_TOKEN` is valid (OAuth 2.0 with `w_member_social` scope).
- For post_image: upload image via LinkedIn Assets API first and set `LINKEDIN_ASSET_URN`.

### n8n workflow nodes fail

- Replace Code-node stubs with HTTP calls to the Brand OS API or an LLM.
- For VISUAL_GENERATOR: provide a real image generation API URL or remove the HTTP node.

---

## (A) Production Deployment Guide (Cloud)

### Railway

**Deploy API**

1. Create a new Railway project.
2. Add a service: "Deploy from GitHub repo" → select your repo.
3. Set root directory: `/` (or leave blank).
4. Set start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   - `BRAND_OS_V3_PATH=/app/brand_os_v3`
   - `PORT=8000` (Railway auto-sets this)
6. Deploy. Railway builds and runs the API.
7. Get the public URL: `https://<app>.railway.app`.

**Deploy UI**

1. Add a new service: "Deploy from GitHub repo" → same repo.
2. Set root directory: `brand_os_ui`.
3. Set build command: `npm install && npm run build`.
4. Set start command: `npm start`.
5. Add environment variable: `NEXT_PUBLIC_BRAND_OS_API_URL=https://<api-service>.railway.app`.
6. Deploy. Railway builds and runs the UI.

**Scaling:** Railway auto-scales; set replicas in service settings. For high load, use Railway's horizontal scaling or move to Kubernetes.

**Health checks:** Railway pings `/health` (API) or `/` (UI) every 60s. Ensure GET /health returns 200.

**Logs:** Railway dashboard → service → Logs.

---

### Render

**Deploy API**

1. Create a new Web Service: "Connect repository" → select your repo.
2. Set root directory: `/`.
3. Set build command: `pip install -e .`.
4. Set start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`.
5. Add environment variables:
   - `BRAND_OS_V3_PATH=/opt/render/project/src/brand_os_v3`
   - `PYTHON_VERSION=3.12`
6. Deploy. Render builds and runs the API.
7. Get the public URL: `https://<app>.onrender.com`.

**Deploy UI**

1. Create a new Static Site or Web Service: "Connect repository" → same repo.
2. Set root directory: `brand_os_ui`.
3. Set build command: `npm install && npm run build`.
4. Set publish directory: `.next` (or use Web Service with start command `npm start`).
5. Add environment variable: `NEXT_PUBLIC_BRAND_OS_API_URL=https://<api-service>.onrender.com`.
6. Deploy.

**Scaling:** Render auto-scales Web Services. For Static Sites, use CDN. For high load, upgrade to Team plan or use Render's autoscaling.

**Health checks:** Render pings `/health` every 30s. Configure in service settings.

**Logs:** Render dashboard → service → Logs.

---

### Fly.io

**Deploy API**

1. Install flyctl: `curl -L https://fly.io/install.sh | sh`.
2. From repo root: `fly launch --name brand-os-api --region ord --no-deploy`.
3. Edit `fly.toml`:
   ```toml
   app = "brand-os-api"
   primary_region = "ord"

   [build]
     dockerfile = "Dockerfile.brand_os_api"

   [env]
     BRAND_OS_V3_PATH = "/app/brand_os_v3"

   [[services]]
     internal_port = 8000
     protocol = "tcp"

     [[services.ports]]
       handlers = ["http"]
       port = 80

     [[services.ports]]
       handlers = ["tls", "http"]
       port = 443

     [[services.http_checks]]
       interval = "30s"
       timeout = "5s"
       method = "GET"
       path = "/health"
   ```
4. Deploy: `fly deploy`.
5. Get URL: `https://brand-os-api.fly.dev`.

**Deploy UI**

1. From `brand_os_ui/`: `fly launch --name brand-os-ui --region ord --no-deploy`.
2. Edit `fly.toml`:
   ```toml
   app = "brand-os-ui"
   primary_region = "ord"

   [build]
     dockerfile = "Dockerfile"

   [env]
     NEXT_PUBLIC_BRAND_OS_API_URL = "https://brand-os-api.fly.dev"

   [[services]]
     internal_port = 3001
     protocol = "tcp"

     [[services.ports]]
       handlers = ["http"]
       port = 80

     [[services.ports]]
       handlers = ["tls", "http"]
       port = 443
   ```
3. Deploy: `fly deploy`.
4. Get URL: `https://brand-os-ui.fly.dev`.

**Scaling:** `fly scale count 2` (horizontal). `fly scale vm shared-cpu-2x` (vertical).

**Health checks:** Defined in `fly.toml` (http_checks).

**Logs:** `fly logs`.

---

### Vercel (UI only)

1. Connect your repo to Vercel.
2. Set root directory: `brand_os_ui`.
3. Framework preset: Next.js.
4. Add environment variable: `NEXT_PUBLIC_BRAND_OS_API_URL=https://<api-url>`.
5. Deploy. Vercel builds and deploys the UI.
6. Get URL: `https://<app>.vercel.app`.

**Scaling:** Vercel auto-scales serverless. No config needed.

**Health checks:** Vercel monitors uptime automatically.

**Logs:** Vercel dashboard → Deployments → Logs.

---

## (B) CI/CD Pipeline (GitHub Actions)

### Full YAML pipeline

Create `.github/workflows/brand_os_v3.yml`:

```yaml
name: Brand OS v3 CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Install Python deps
        run: pip install -e .
      - name: Install test deps
        run: pip install pytest pyyaml
      - name: Run E2E tests
        run: pytest -q tests_e2e/
      - name: Install UI deps
        working-directory: brand_os_ui
        run: npm ci
      - name: Build UI
        working-directory: brand_os_ui
        run: npm run build

  build-api:
    runs-on: ubuntu-latest
    needs: test
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      - name: Build and push API
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile.brand_os_api
          push: true
          tags: ${{ secrets.DOCKER_USERNAME }}/brand-os-api:latest

  deploy-railway:
    runs-on: ubuntu-latest
    needs: build-api
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Railway
        run: |
          curl -X POST https://api.railway.app/v1/projects/${{ secrets.RAILWAY_PROJECT_ID }}/services/${{ secrets.RAILWAY_SERVICE_ID }}/deploy \
            -H "Authorization: Bearer ${{ secrets.RAILWAY_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{"branch":"main"}'
```

### Secrets management

In GitHub repo → Settings → Secrets and variables → Actions, add:

- `DOCKER_USERNAME` — Docker Hub username
- `DOCKER_PASSWORD` — Docker Hub password or token
- `RAILWAY_TOKEN` — Railway API token (from Railway dashboard → Account → Tokens)
- `RAILWAY_PROJECT_ID` — Railway project ID (from project URL)
- `RAILWAY_SERVICE_ID` — Railway service ID (from service settings)

### Branch strategy

- **main** — Production; triggers build + deploy
- **develop** — Staging; triggers test only
- **feature/** — PRs; triggers test only

---

## (C) Multi-Tenant Mode

### Structure tenant folders

```
brand_os_v3/
  tenants/
    tenant-1/
      identity.json       (override 00_Master_Identity_Core)
      voice.json          (override 03_Voice_Engine)
      hooks.json          (override 05_Hook_Library)
      memory_log.jsonl    (tenant-specific content log)
      signals/            (tenant-specific signals)
    tenant-2/
      identity.json
      voice.json
      hooks.json
      memory_log.jsonl
      signals/
  config/                 (default/fallback config)
  agents/                 (shared agent definitions)
  ...
```

### Isolate per tenant

**Identity, voice, hooks:** Load from `tenants/<tenant_id>/identity.json` if present; else fall back to `config/00_Master_Identity_Core.json`.

**Memory logs:** Write to `tenants/<tenant_id>/memory_log.jsonl` instead of `storage/content_memory_log.jsonl`.

**Signals:** Store tenant-specific signals in `tenants/<tenant_id>/signals/`.

### Extend the orchestrator

Update `brand_os_sdk/config_loader.py`:

```python
def _tenant_path(tenant_id: str, base: Path) -> Path:
    return base / "tenants" / tenant_id

def load_identity(tenant_id: str | None = None, base: Path | None = None) -> dict[str, Any]:
    root = base or _base_path()
    if tenant_id:
        tenant_file = _tenant_path(tenant_id, root) / "identity.json"
        if tenant_file.exists():
            return _read_json(tenant_file)
    return _read_json(root / "config" / "00_Master_Identity_Core.json")
```

Update `brand_os_sdk/orchestrator.py` to accept tenant_id and pass to load_identity, load_voice, etc.

### Example folder structure

```
brand_os_v3/tenants/acme/
  identity.json:
    {
      "brand_name": "Acme Corp",
      "mission": "We make shipping simple.",
      "values": [...],
      "tone_profile": {...},
      "constraints": {...},
      "audience_archetypes": [...]
    }
  voice.json:
    {
      "voice_id": "acme-v1",
      "sentence_rules": {...},
      "vocabulary": {...},
      "platform_adaptations": {...}
    }
  hooks.json:
    {
      "hooks": [...],
      "ctas": [...],
      "openers": [...]
    }
  memory_log.jsonl:
    {"trace_id": "tr1", "tenant_id": "acme", "platform": "linkedin", "body_hash": "...", "published_at": "2025-01-29T12:00:00Z", "status": "approved"}
```

---

## (D) Auto-Learning Feedback Loop

### Collect engagement data

After publishing content (WhatsApp, LinkedIn), collect:

- impressions
- engagement_rate
- clicks
- shares
- comments

Store in content memory log:

```json
{
  "content_id": "cnt-abc123",
  "tenant_id": "tenant-1",
  "platform": "linkedin",
  "body_hash": "sha256:...",
  "published_at": "2025-01-29T14:00:00Z",
  "trace_id": "trace-xyz",
  "topic_hint": "API release",
  "performance": {
    "impressions": 1200,
    "engagement_rate": 0.04,
    "clicks": 48,
    "shares": 5,
    "comments": 3
  }
}
```

### Update hooks, tone, platform distribution

**Hooks:** Analyze top-performing hooks (engagement_rate > 0.05). Add to `config/05_Hook_Library.json`:

```python
import json
from pathlib import Path
from collections import Counter

def analyze_hooks(memory_log_path: Path) -> list[dict]:
    entries = []
    with open(memory_log_path) as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    high_engagement = [e for e in entries if e.get("performance", {}).get("engagement_rate", 0) > 0.05]
    hooks = Counter(e.get("hook_used", "") for e in high_engagement if e.get("hook_used"))
    return [{"hook": k, "count": v} for k, v in hooks.most_common(10)]

def update_hook_library(new_hooks: list[str], library_path: Path) -> None:
    with open(library_path, "r+") as f:
        lib = json.load(f)
        existing_ids = {h["id"] for h in lib.get("hooks", [])}
        for i, hook_text in enumerate(new_hooks):
            hook_id = f"h_auto_{i}"
            if hook_id not in existing_ids:
                lib["hooks"].append({
                    "id": hook_id,
                    "text": hook_text,
                    "category": "question",
                    "platforms": ["linkedin", "twitter"],
                    "usage_count": 0,
                    "max_uses_per_month": 4
                })
        f.seek(0)
        json.dump(lib, f, indent=2)
        f.truncate()
```

**Tone:** Compute avg tone_deviation for approved vs rejected. If avg tone_deviation for approved < 0.1, keep current tone. If rejected_identity has high tone_deviation (> 0.2), adjust tone_profile in Master Identity.

**Platform distribution:** Track engagement_rate per platform. If linkedin avg > 0.05 and twitter avg < 0.02, prioritize linkedin in routing_rules.

### Integrate with Google Sheets

Use `gspread` to write performance data:

```python
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def append_to_sheet(trace_id: str, platform: str, engagement_rate: float) -> None:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("google_credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("Brand OS Performance").sheet1
    sheet.append_row([trace_id, platform, engagement_rate])
```

### Integrate with Supabase

Use Supabase Python client:

```python
from supabase import create_client, Client

url = "https://your-project.supabase.co"
key = "your_anon_key"
supabase: Client = create_client(url, key)

def log_to_supabase(entry: dict) -> None:
    supabase.table("brand_os_runs").insert({
        "trace_id": entry["trace_id"],
        "tenant_id": entry["tenant_id"],
        "platform": entry["platform"],
        "status": entry["status"],
        "engagement_rate": entry.get("performance", {}).get("engagement_rate", 0),
        "published_at": entry["published_at"],
    }).execute()
```

---

## (E) Analytics Layer

### Metrics to track

- **Hook performance** — engagement_rate per hook_id
- **Pillar performance** — engagement_rate per topic_hint (pillar)
- **Platform performance** — engagement_rate per platform
- **Revision rate** — (rejected_identity + rejected_cto) / total_runs
- **Approval rate** — approved / total_runs
- **Avg revisions per run** — (sum of revision_count_identity + revision_count_cto) / total_runs

### Compute metrics

```python
import json
from pathlib import Path
from collections import defaultdict

def compute_analytics(memory_log_path: Path) -> dict:
    entries = []
    with open(memory_log_path) as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    
    total_runs = len(entries)
    approved = sum(1 for e in entries if e.get("status") == "approved")
    rejected_identity = sum(1 for e in entries if e.get("status") == "rejected_identity")
    rejected_cto = sum(1 for e in entries if e.get("status") == "rejected_cto")
    
    approval_rate = approved / total_runs if total_runs else 0
    revision_rate = (rejected_identity + rejected_cto) / total_runs if total_runs else 0
    
    hook_engagement = defaultdict(list)
    pillar_engagement = defaultdict(list)
    platform_engagement = defaultdict(list)
    
    for e in entries:
        hook = e.get("hook_used", "")
        pillar = e.get("topic_hint", "")
        platform = e.get("platform", "")
        eng = e.get("performance", {}).get("engagement_rate", 0)
        if hook:
            hook_engagement[hook].append(eng)
        if pillar:
            pillar_engagement[pillar].append(eng)
        if platform:
            platform_engagement[platform].append(eng)
    
    def avg(vals: list) -> float:
        return sum(vals) / len(vals) if vals else 0
    
    return {
        "total_runs": total_runs,
        "approval_rate": approval_rate,
        "revision_rate": revision_rate,
        "hook_performance": {k: avg(v) for k, v in hook_engagement.items()},
        "pillar_performance": {k: avg(v) for k, v in pillar_engagement.items()},
        "platform_performance": {k: avg(v) for k, v in platform_engagement.items()},
    }
```

### Visualize in monitoring dashboard

Update `brand_os_monitoring/app.py`:

```python
@app.get("/analytics")
def analytics() -> dict:
    from brand_os_monitoring.analytics import compute_analytics
    return compute_analytics(MEMORY_LOG)
```

Create `brand_os_monitoring/analytics.py` with the `compute_analytics` function above.

Update `brand_os_monitoring/templates/dashboard.html` to add a new section:

```html
<div class="chart-container">
  <h2>Hook performance (avg engagement)</h2>
  <canvas id="hookChart" width="400" height="200"></canvas>
</div>
<script>
  fetch('/analytics')
    .then(r => r.json())
    .then(data => {
      const hookPerf = data.hook_performance || {};
      new Chart(document.getElementById('hookChart'), {
        type: 'bar',
        data: {
          labels: Object.keys(hookPerf),
          datasets: [{ label: 'Avg engagement', data: Object.values(hookPerf), backgroundColor: '#00D4AA' }]
        },
        options: { scales: { y: { beginAtZero: true } } }
      });
    });
</script>
```

### Example JSON schemas

**Performance entry:**

```json
{
  "content_id": "cnt-abc123",
  "tenant_id": "tenant-1",
  "platform": "linkedin",
  "body_hash": "sha256:abc123...",
  "published_at": "2025-01-29T14:00:00Z",
  "trace_id": "trace-xyz",
  "topic_hint": "API release",
  "hook_used": "h1",
  "cta_used": "c1",
  "performance": {
    "impressions": 1200,
    "engagement_rate": 0.04,
    "clicks": 48,
    "shares": 5,
    "comments": 3
  }
}
```

**Analytics output:**

```json
{
  "total_runs": 42,
  "approval_rate": 0.9,
  "revision_rate": 0.1,
  "hook_performance": {
    "h1": 0.045,
    "h2": 0.038
  },
  "pillar_performance": {
    "API release": 0.042,
    "DevEx": 0.039
  },
  "platform_performance": {
    "linkedin": 0.041,
    "twitter": 0.035,
    "whatsapp": 0.028
  }
}
```

---

## 16. Quick Start (Zero to Production)

### Local development

```bash
# 1. Clone repo
git clone <repo-url> && cd kirp

# 2. Install Python deps
pip install -e .

# 3. Run API
uvicorn api.main:app --reload
# API: http://127.0.0.1:8000

# 4. Run UI (separate terminal)
cd brand_os_ui
npm install
npm run dev
# UI: http://localhost:3001

# 5. Run CLI
brandos run "API release" --tenant tenant-1 --platform linkedin

# 6. Run scheduler (separate terminal)
python run_scheduler.py

# 7. Run monitoring (separate terminal)
uvicorn brand_os_monitoring.app:app --port 8001 --reload
# Dashboard: http://127.0.0.1:8001/dashboard

# 8. Run E2E tests
pytest -q tests_e2e/
```

### Production (Railway)

```bash
# 1. Push to GitHub
git push origin main

# 2. Railway: create project, link repo, add API service
# Set start command: uvicorn api.main:app --host 0.0.0.0 --port $PORT
# Add env: BRAND_OS_V3_PATH=/app/brand_os_v3

# 3. Railway: add UI service (root: brand_os_ui)
# Set build: npm install && npm run build
# Set start: npm start
# Add env: NEXT_PUBLIC_BRAND_OS_API_URL=https://<api-service>.railway.app

# 4. Deploy
# Railway auto-deploys on push to main

# 5. Get URLs
# API: https://<api-service>.railway.app
# UI: https://<ui-service>.railway.app
```

---

## 17. Advanced Configuration

### Custom agent

1. Add `brand_os_v3/agents/MY_AGENT.json` with role, input_schema, output_schema, prompt_template, example_input, example_output.
2. Add to `brand_os_v3/config/04_Agent_Mesh_Protocol.json` (agents array, flow_order).
3. Add to `brand_os_v3/execution/EXECUTION_TEMPLATE.json` (agent_invocation_order).
4. Add node in `brand_os_v3/workflow/master_orchestrator_workflow.json` (nodes, connections).
5. Add entry in `brand_os_v3/kirp/agent_specs.yaml` and `brand_os_v3/kirp/workflow_mapping.yaml`.
6. Update `brand_os_sdk/orchestrator.py` to invoke MY_AGENT in the pipeline.

### Custom platform

1. Add platform entry in `brand_os_v3/config/08_Platform_Distribution_Map.json` (id, name, enabled, limits, content_rules).
2. Add platform_adaptations in `brand_os_v3/config/03_Voice_Engine.json`.
3. Extend platform enum in agent input_schemas (e.g. CONTEXT_SCANNER, STRATEGIC_PLANNER).
4. Update `brand_os_v3/workflow/master_orchestrator_workflow.json` platform_variants.
5. Add platform variant logic in TECHNICAL_STORYTELLER or HUMAN_EDGE (or a dedicated variant node).

### Custom gatekeeper

1. Add `brand_os_v3/agents/MY_GATEKEEPER.json` with gatekeeper_logic (approve_condition, on_reject, on_approve).
2. Insert in flow_order between HUMAN_EDGE and VISUAL_GENERATOR (or after SKEPTICAL_CTO).
3. Add IF node and revision loop in workflow and n8n.
4. Add to gatekeeper_invocation_order and revision_loop_rules in EXECUTION_TEMPLATE.json.
5. Update KIRP governance_policy and workflow_mapping.

---

## 18. Monitoring and Observability

### Logs

- **API logs:** uvicorn outputs to stdout; capture with `uvicorn api.main:app --log-config log_config.json`.
- **Scheduler logs:** APScheduler logs to stdout; redirect to file: `python run_scheduler.py > scheduler.log 2>&1`.
- **UI logs:** Next.js logs to stdout; capture in Docker or cloud platform.

### Metrics

- **API:** Add Prometheus metrics with `prometheus-fastapi-instrumentator`.
- **Scheduler:** Log job execution time and success/failure to a metrics file or Prometheus.
- **Monitoring dashboard:** `/metrics` endpoint returns JSON; scrape with Prometheus or send to Datadog/New Relic.

### Alerts

- **API down:** Monitor GET /health; alert if 5xx or timeout.
- **Scheduler failure:** Monitor scheduler.log for exceptions; alert if no runs in 24h.
- **High rejection rate:** Monitor `/metrics` for `revision_rate > 0.3`; alert if sustained.

---

## 19. Security

### API

- Add authentication: FastAPI dependency with API key or JWT.
- Rate limiting: use `slowapi` or nginx rate limit.
- CORS: configure `CORSMiddleware` in `api/main.py` for UI origin.

### Secrets

- Store in environment variables or secret manager (AWS Secrets Manager, Railway secrets, Render env vars).
- Never commit `.env` or credentials to git.

### KIRP governance

- Enforce identity_constraints and agent_constraints from `brand_os_v3/kirp/governance_policy.yaml`.
- Audit all runs: log trace_id, tenant_id, platform, approved/rejected to event store.

---

## 20. Backup and Recovery

### Backup content memory log

```bash
cp brand_os_v3/storage/content_memory_log.jsonl backups/content_memory_log_$(date +%Y%m%d).jsonl
```

Schedule daily backups with cron:

```bash
0 2 * * * cp /path/to/brand_os_v3/storage/content_memory_log.jsonl /path/to/backups/content_memory_log_$(date +\%Y\%m\%d).jsonl
```

### Restore

```bash
cp backups/content_memory_log_20250129.jsonl brand_os_v3/storage/content_memory_log.jsonl
```

### Backup config

```bash
tar -czf brand_os_v3_config_$(date +%Y%m%d).tar.gz brand_os_v3/config/ brand_os_v3/agents/ brand_os_v3/kirp/
```

---

## 21. Performance Tuning

### API

- Use `uvicorn --workers 4` for multi-process.
- Use gunicorn: `gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker`.
- Cache config: load identity/voice once at startup; store in global or Redis.

### Orchestrator

- Parallelize agent calls (if agents are independent): use `asyncio.gather` or `concurrent.futures`.
- Cache agent outputs: if topic_hint is the same within 1h, return cached result.

### UI

- Use Next.js static export for pages that don't change: `output: "export"` in next.config.js.
- Use CDN (Vercel, Cloudflare) for static assets.

---

## 22. Extending the System

### Add a new integration (e.g. Twitter API v2)

1. Create `brand_os_integrations/twitter.py`:
   ```python
   import os
   import requests

   def post_tweet(text: str) -> dict:
       token = os.environ.get("TWITTER_BEARER_TOKEN")
       if not token:
           return {"ok": False, "error": "TWITTER_BEARER_TOKEN not set"}
       url = "https://api.twitter.com/2/tweets"
       headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
       data = {"text": text}
       r = requests.post(url, headers=headers, json=data, timeout=30)
       if r.status_code == 201:
           return {"ok": True, "data": r.json()}
       return {"ok": False, "error": r.text}
   ```
2. Export from `brand_os_integrations/__init__.py`: `from brand_os_integrations.twitter import post_tweet`.
3. Use in CLI or scheduler: `from brand_os_integrations.twitter import post_tweet; post_tweet(body[:280])`.

### Add a new page to the UI

1. Create `brand_os_ui/app/my-page/page.tsx`:
   ```tsx
   export default function MyPage() {
     return <div><h1>My Page</h1></div>;
   }
   ```
2. Add link in `brand_os_ui/components/Layout.tsx`:
   ```tsx
   <Link href="/my-page" className="hover:underline">My Page</Link>
   ```

### Add a new CLI command

1. Edit `brand_os_cli/main.py`:
   ```python
   @brandos.command("my-command")
   @click.option("--arg", default="value")
   def my_command(arg: str):
       """My custom command."""
       click.echo(f"Running with {arg}")
   ```
2. Run: `brandos my-command --arg test`.

---

## 23. Troubleshooting (Extended)

### API slow (> 5s per request)

- Check agent stub execution time (if using real LLM, optimize prompts or use streaming).
- Cache config: load identity/voice once at startup.
- Use async: convert orchestrator to async and use `asyncio.gather` for parallel agent calls.

### Scheduler doesn't send WhatsApp

- Check `BRAND_OS_WHATSAPP_TO` is set.
- Check `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_WHATSAPP_FROM` are valid.
- Check Twilio account balance and WhatsApp sandbox approval.

### LinkedIn post returns 401

- Check `LINKEDIN_ACCESS_TOKEN` is valid (OAuth 2.0 with `w_member_social` scope).
- Refresh token if expired (LinkedIn tokens expire after 60 days).

### UI shows "API error"

- Check `NEXT_PUBLIC_BRAND_OS_API_URL` points to the running API.
- Check CORS: add `CORSMiddleware` in `api/main.py`:
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3001"], allow_methods=["*"], allow_headers=["*"])
  ```

### E2E tests fail with "ModuleNotFoundError"

- Install missing deps: `pip install pytest pyyaml apscheduler twilio`.
- Run from repo root: `pytest -q tests_e2e/`.

### Docker build fails

- Check Dockerfile.brand_os_api exists.
- Check brand_os_v3/, brand_os_sdk/, api/ are present.
- Run: `docker build -f Dockerfile.brand_os_api -t brand-os-api . --progress=plain` to see full output.

---

## 24. Maintenance

### Update config

1. Edit `brand_os_v3/config/00_Master_Identity_Core.json` (mission, values, tone, constraints).
2. Restart API: `uvicorn api.main:app --reload` (auto-reloads if using --reload).
3. Verify: `brandos run "test" --sdk` and check output aligns with new identity.

### Update agent

1. Edit `brand_os_v3/agents/<AGENT_ID>.json` (prompt_template, example_output).
2. Restart API or SDK (config is loaded at runtime).
3. Run E2E tests: `pytest -q tests_e2e/test_sdk.py`.

### Update workflow

1. Edit `brand_os_v3/workflow/master_orchestrator_workflow.json` (nodes, connections, gatekeeper_loops).
2. Restart API.
3. Re-import n8n workflow if using n8n.

### Rotate hooks

1. Edit `brand_os_v3/config/05_Hook_Library.json` (add/remove hooks, update usage_count, max_uses_per_month).
2. Restart API.
3. Run: `brandos run "test"` and verify new hooks are used.

---

## 25. Support and Resources

- **README:** `brand_os_v3/README.md` — full system overview, file map, agent map, workflow map, run instructions, extension guide.
- **KIRP Integration:** `brand_os_v3/KIRP_INTEGRATION.md` — KIRP events, governance, agent_specs alignment, SDK handle_kirp_event.
- **API README:** `README_API.md` (repo root) — API usage, SDK usage, KIRP integration, deployment.
- **E2E tests:** `tests_e2e/` — 11 test groups; run with `pytest -q tests_e2e/`.
- **Monitoring:** `http://127.0.0.1:8001/dashboard` — metrics and charts.

---

## Appendix A: Full Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| BRAND_OS_V3_PATH | Path to brand_os_v3/ | repo_root/brand_os_v3 | No |
| BRAND_OS_API_URL | API base URL for CLI | http://127.0.0.1:8000 | No |
| BRAND_OS_TENANT_ID | Tenant ID for scheduler | default | No |
| BRAND_OS_PLATFORM | Platform for scheduler | linkedin | No |
| BRAND_OS_WHATSAPP_TO | Phone number for scheduler WhatsApp | (none) | No |
| TWILIO_SID | Twilio account SID | (none) | Yes (for WhatsApp) |
| TWILIO_TOKEN | Twilio auth token | (none) | Yes (for WhatsApp) |
| TWILIO_WHATSAPP_FROM | Twilio WhatsApp number | whatsapp:+14155238886 | No |
| LINKEDIN_ACCESS_TOKEN | LinkedIn OAuth token | (none) | Yes (for LinkedIn) |
| LINKEDIN_PERSON_URN | LinkedIn person URN | urn:li:person:me | No |
| LINKEDIN_ASSET_URN | LinkedIn asset URN (for images) | (none) | Yes (for post_image) |
| NEXT_PUBLIC_BRAND_OS_API_URL | API URL for UI | http://127.0.0.1:8000 | No |

---

## Appendix B: File Structure

```
kirp/
  brand_os_v3/
    config/                     (8 JSON: identity, voice, mesh, world, platform, memory, hook, visual)
    agents/                     (8 JSON: CONTEXT_SCANNER, STRATEGIC_PLANNER, ...)
    workflow/                   (master_orchestrator_workflow.json)
    execution/                  (EXECUTION_TEMPLATE.json)
    kirp/                       (governance_policy.yaml, agent_specs.yaml, workflow_mapping.yaml)
    n8n/                        (brand_os_v3_workflow.json)
    storage/                    (content_memory_log.jsonl)
    README.md
    KIRP_INTEGRATION.md
    OPERATIONS_MANUAL.md
  brand_os_sdk/
    __init__.py
    config_loader.py
    orchestrator.py
    kirp_integration.py
  api/
    __init__.py
    main.py
  brand_os_cli/
    __init__.py
    main.py
  brand_os_scheduler/
    __init__.py
    scheduler.py
  brand_os_monitoring/
    __init__.py
    app.py
    templates/
      dashboard.html
  brand_os_integrations/
    __init__.py
    whatsapp.py
    linkedin.py
  brand_os_ui/
    app/
      layout.tsx
      page.tsx
      globals.css
      dashboard/page.tsx
      run/page.tsx
      history/page.tsx
      agents/page.tsx
      visuals/page.tsx
      api/
        history/route.ts
        agents/route.ts
        visuals/route.ts
    components/
      Layout.tsx
      PostCard.tsx
      VisualCard.tsx
      AgentCard.tsx
      RunForm.tsx
    lib/
      api.ts
    package.json
    next.config.js
    tailwind.config.js
    tsconfig.json
    postcss.config.js
    next-env.d.ts
  tests_e2e/
    __init__.py
    test_config_validity.py
    test_sdk.py
    test_api.py
    test_kirp_integration.py
    test_cli.py
    test_scheduler.py
    test_monitoring.py
    test_integrations.py
    test_n8n_workflow.py
    test_ui_build.py
    test_docker.py
  pyproject.toml
  Dockerfile.brand_os_api
  run_scheduler.py
  README_API.md
```

---

## Appendix C: Agent Prompt Templates

Each agent JSON under `brand_os_v3/agents/` includes a `prompt_template` field. To customize agent behavior:

1. Edit the prompt_template in the agent JSON.
2. Restart the API or SDK.
3. Run: `brandos run "test"` and verify output.

Example: Update IDENTITY_GUARDIAN to be more strict:

```json
{
  "prompt_template": "You are the Identity Guardian for Brand OS. Your job is to verify the polished draft aligns with the brand's Master Identity. You are VERY STRICT: approve only if alignment is >= 0.9 and tone_deviation <= 0.1. ..."
}
```

---

## Appendix D: Deployment Checklist

- [ ] Set all required environment variables (TWILIO, LINKEDIN, BRAND_OS_V3_PATH, etc.)
- [ ] Run E2E tests: `pytest -q tests_e2e/` (all pass)
- [ ] Build API Docker image: `docker build -f Dockerfile.brand_os_api -t brand-os-api .`
- [ ] Build UI: `cd brand_os_ui && npm run build`
- [ ] Deploy API to cloud (Railway, Render, Fly.io)
- [ ] Deploy UI to cloud (Vercel, Railway, Render)
- [ ] Configure CORS in API for UI origin
- [ ] Set up monitoring: `/metrics` endpoint, Prometheus scrape, or Datadog agent
- [ ] Set up alerts: API health, scheduler runs, rejection rate
- [ ] Set up backups: content memory log, config files
- [ ] Test end-to-end: POST /brand-os/run from UI, verify output
- [ ] Document custom config (tenant-specific identity, voice, hooks)
- [ ] Set up CI/CD: GitHub Actions workflow (test, build, deploy)
- [ ] Enable auto-learning: collect engagement data, update hooks/tone

---

## Appendix E: Example Workflows

### Workflow 1: Daily LinkedIn post

1. Scheduler runs at 08:00.
2. CONTEXT_SCANNER picks best signal (e.g. "API release").
3. Orchestrator runs: CONTEXT_SCANNER → … → GROWTH_ANALYST.
4. Output: content (headline, body, hook, CTA), visual_spec, recommendations, status=approved.
5. CLI or integration posts to LinkedIn: `post_text(content["body"])`.
6. Collect engagement data (impressions, clicks) after 24h.
7. Append to memory log with performance.
8. Auto-learning: analyze top hooks, update hook library.

### Workflow 2: On-demand run via UI

1. User opens `http://localhost:3001/run`.
2. Fills form: tenant_id, platform, topic_hint.
3. Clicks "Run".
4. UI calls POST /brand-os/run.
5. API runs orchestrator.
6. UI displays content, visual spec, recommendations, status.
7. User copies content and publishes manually or via integration.

### Workflow 3: KIRP event-driven run

1. KIRP emits event: `{"event_type": "brand_os_run_started", "payload": {"tenant_id": "t1", "platform": "linkedin", "topic_hint": "API"}}`.
2. KIRP worker calls `handle_kirp_event(event)`.
3. SDK runs orchestrator.
4. Result is returned to KIRP.
5. KIRP logs event: `brand_os_v3.workflow.completed` with trace_id, status.

---

## Appendix F: Glossary

- **Agent** — A step in the pipeline (e.g. CONTEXT_SCANNER, IDENTITY_GUARDIAN).
- **Gatekeeper** — An agent that approves or rejects (IDENTITY_GUARDIAN, SKEPTICAL_CTO).
- **Revision loop** — When a gatekeeper rejects, the draft is revised and re-submitted (max 1 per gatekeeper).
- **trace_id** — Unique identifier for a run (e.g. tr_12345).
- **tenant_id** — Identifier for a tenant (multi-tenancy).
- **platform** — Target platform: linkedin, twitter, whatsapp.
- **topic_hint** — Topic for content generation (e.g. "API release").
- **final_output_format** — Output schema: trace_id, tenant_id, platform, topic_hint, content, visual_spec, recommendations, status.
- **KIRP** — Knowledge, Identity, Reasoning, Policy (governance framework).
- **n8n** — Workflow automation tool (visual workflow editor).

---

**End of Operations Manual**
