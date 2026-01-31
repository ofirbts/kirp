# Brand OS v3 API

Minimal FastAPI app that runs the Brand OS v3 orchestrator and returns `final_output_format` from `EXECUTION_TEMPLATE.json`. The system also includes a Python SDK (`brand_os_sdk`) and KIRP integration (`handle_kirp_event`).

---

## Full System Overview

Brand OS v3 is a multi-agent pipeline that produces on-brand, platform-adapted content (headline, body, hook, CTA, visual spec) from tenant_id, platform, and topic_hint. Config and agent definitions live under `brand_os_v3/config/` and `brand_os_v3/agents/`. The pipeline runs: CONTEXT_SCANNER → STRATEGIC_PLANNER → TECHNICAL_STORYTELLER → HUMAN_EDGE → IDENTITY_GUARDIAN → SKEPTICAL_CTO → VISUAL_GENERATOR → GROWTH_ANALYST, with two gatekeepers (IDENTITY_GUARDIAN, SKEPTICAL_CTO) that can reject and trigger one revision loop each. The API exposes a single run endpoint; the SDK exposes load_identity, load_voice, list_agents, run_orchestrator, and handle_kirp_event for KIRP event routing.

---

## Architecture (ASCII)

```
  Client / n8n / KIRP
         │
         ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  FastAPI api/main.py                                        │
  │  POST /brand-os/run  →  brand_os_sdk.run_orchestrator()     │
  │  GET  /health        →  {"status": "ok"}                   │
  └─────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  brand_os_sdk (Python)                                      │
  │  config_loader: load_identity(), load_voice(), list_agents │
  │  orchestrator: run_orchestrator(input_payload)             │
  │  kirp_integration: handle_kirp_event(event)                 │
  └─────────────────────────────────────────────────────────────┘
         │
         ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  brand_os_v3/                                               │
  │  config/, agents/, workflow/, execution/, kirp/, n8n/       │
  └─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- Python 3.10+
- Brand OS v3 assets under `brand_os_v3/` (config, agents, execution, workflow)

---

## Install

From the repo root (same directory as `pyproject.toml`):

```bash
pip install -e .
```

Or install dependencies only:

```bash
pip install "fastapi>=0.109.0" "uvicorn[standard]>=0.27.0" "pydantic>=2.0.0"
```

---

## Run the API (Local)

From the repo root:

```bash
uvicorn api.main:app --reload
```

- API base: `http://127.0.0.1:8000`
- OpenAPI docs: `http://127.0.0.1:8000/docs`
- Health: `GET http://127.0.0.1:8000/health` → `{"status": "ok", "service": "brand-os-v3-api"}`

---

## API Usage

### POST /brand-os/run

Runs the Brand OS v3 pipeline and returns the final_output_format.

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

- **tenant_id** (required) — Tenant identifier.
- **platform** (required) — One of: linkedin, twitter, whatsapp.
- **topic_hint** (required) — Topic hint for content generation.
- **trace_id** (optional) — Trace ID; generated if omitted.
- **extra_context** (optional) — Object with optional `signals` and `memory_entries` arrays for context.

**Response:** final_output_format from EXECUTION_TEMPLATE:

- **trace_id**, **tenant_id**, **platform**, **topic_hint**
- **content**: headline, body, hook_used, cta_used
- **visual_spec**: image_prompt, aspect_ratio, format, alt_text
- **recommendations**: suggested_timing, hook_rotation, cta_rotation, next_topic_hints
- **status**: `approved` | `rejected_identity` | `rejected_cto`

**Errors:**

- 503 — Brand OS config not found (e.g. missing brand_os_v3/).
- 400 — Invalid input (missing required fields or wrong types).

---

## SDK Usage

The Python SDK lives under `brand_os_sdk/`. It reads config and agents from `brand_os_v3/config/` and `brand_os_v3/agents/` (path from env `BRAND_OS_V3_PATH` or default repo sibling).

**Exports:**

- **load_identity()** — Load Master Identity Core from `config/00_Master_Identity_Core.json`.
- **load_voice()** — Load Voice Engine from `config/03_Voice_Engine.json`.
- **list_agents()** — List agent IDs from `agents/*.json` (e.g. CONTEXT_SCANNER, STRATEGIC_PLANNER, …).
- **run_orchestrator(input_payload: dict) -> dict** — Run the pipeline; returns final_output_format. input_payload must include tenant_id, platform, topic_hint; optional trace_id, extra_context.

**Example:**

```python
from brand_os_sdk import load_identity, load_voice, list_agents, run_orchestrator

identity = load_identity()
voice = load_voice()
agents = list_agents()

result = run_orchestrator({
    "tenant_id": "tenant-1",
    "platform": "linkedin",
    "topic_hint": "API release",
    "extra_context": {"signals": [], "memory_entries": []},
})
# result: trace_id, tenant_id, platform, topic_hint, content, visual_spec, recommendations, status
```

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
| **brand_os_run_started** or **brand_os_v3.workflow.started** | Runs orchestrator | final_output_format (same as POST /brand-os/run) or None |
| **agent_completed** or any **brand_os_v3.*.completed** | Acknowledge | `{"ack": true, "route": "agent_completed", "trace_id": ...}` |
| **gatekeeper_decision** or **brand_os_v3.identity.rejected** or **brand_os_v3.cto.rejected** | Acknowledge | `{"ack": true, "route": "gatekeeper_decision", "trace_id": ...}` |
| **run_completed** or **brand_os_v3.workflow.completed** | Acknowledge | `{"ack": true, "route": "run_completed", "trace_id": ...}` |
| **run_failed** | Acknowledge | `{"ack": true, "route": "run_failed", "trace_id": ...}` |

**Example event JSON (start a run and get result):**

```json
{
  "event_type": "brand_os_run_started",
  "payload": {
    "tenant_id": "tenant-1",
    "platform": "linkedin",
    "topic_hint": "API release",
    "trace_id": "trace-001",
    "extra_context": {
      "signals": [],
      "memory_entries": []
    }
  }
}
```

**Example (Python):**

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
# result is the final_output_format dict (trace_id, content, visual_spec, recommendations, status, ...)
```

Event types **brand_os_v3.workflow.started**, **brand_os_v3.*.completed**, **brand_os_v3.identity.rejected**, **brand_os_v3.cto.rejected**, and **brand_os_v3.workflow.completed** are also recognized and routed as above. Full KIRP event mapping and governance alignment: **brand_os_v3/KIRP_INTEGRATION.md**.

---

## Deployment Instructions

### Local (API)

From repo root:

```bash
pip install "fastapi>=0.109.0" "uvicorn[standard]>=0.27.0" "pydantic>=2.0.0"
export BRAND_OS_V3_PATH=/path/to/brand_os_v3   # optional
uvicorn api.main:app --reload
```

API: `http://127.0.0.1:8000`. POST /brand-os/run with tenant_id, platform, topic_hint.

### Local (SDK only)

From repo root, ensure `brand_os_v3/` is present (or set BRAND_OS_V3_PATH). Then use `from brand_os_sdk import run_orchestrator` and call `run_orchestrator({"tenant_id": "...", "platform": "...", "topic_hint": "..."})`.

### Docker (API)

From repo root:

```bash
docker build -f Dockerfile.brand_os_api -t brand-os-api .
docker run -p 8000:8000 brand-os-api
```

The image copies `brand_os_v3/`, `brand_os_sdk/`, and `api/`, sets `BRAND_OS_V3_PATH=/app/brand_os_v3` and `PYTHONPATH=/app`, and runs `uvicorn api.main:app --host 0.0.0.0 --port 8000`. API: `http://localhost:8000`. POST /brand-os/run with the same body as above.

### n8n

Import **brand_os_v3/n8n/brand_os_v3_workflow.json** into n8n. Run with Manual Trigger; supply tenant_id, platform, topic_hint in the trigger payload. For production, you can call the Brand OS API from an n8n HTTP Request node instead of the embedded Code stubs. See **brand_os_v3/README.md** for the full n8n workflow explanation.
