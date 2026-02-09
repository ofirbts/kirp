# Brand OS v3.0 — Complete System Documentation

A production-ready, modular, multi-agent Brand Operating System with config, agents, workflow, execution template, Python SDK, FastAPI, CLI, scheduler, monitoring dashboard, Next.js UI, integrations (WhatsApp, LinkedIn), KIRP integration, n8n export, and E2E test suite.

---

## Full System Overview

Brand OS v3 produces on-brand, platform-adapted content (headline, body, hook, CTA, visual spec) from tenant_id, platform, and topic_hint. The system runs a pipeline of eight agents in order, with two gatekeepers (IDENTITY_GUARDIAN, SKEPTICAL_CTO) that can reject and trigger one revision loop each.

**Core components:**
- **Config** (`brand_os_v3/config/`) — 8 JSON files: identity, voice, agent mesh, world context, platform distribution, memory, hooks, visual identity
- **Agents** (`brand_os_v3/agents/`) — 8 agent JSON files with role, input/output schemas, prompt templates, examples, gatekeeper logic
- **Workflow** (`brand_os_v3/workflow/`) — Orchestration flow with gatekeeper loops, platform variants, logging
- **Execution** (`brand_os_v3/execution/`) — EXECUTION_TEMPLATE with system prompt, agent order, revision rules
- **KIRP** (`brand_os_v3/kirp/`) — 3 YAML files: governance policy, agent specs, workflow mapping
- **n8n** (`brand_os_v3/n8n/`) — Real n8n workflow export (executable without modification)

**Modules:**
- **SDK** (`brand_os_sdk/`) — Python SDK: load_identity, load_voice, list_agents, run_orchestrator, handle_kirp_event
- **API** (`api/`) — FastAPI: POST /brand-os/run, GET /health
- **CLI** (`brand_os_cli/`) — Click CLI: brandos run, brandos daily, brandos signals, brandos agents
- **Scheduler** (`brand_os_scheduler/`) — APScheduler daily job at 08:00 (auto-run pipeline)
- **Monitoring** (`brand_os_monitoring/`) — FastAPI + Jinja2: /metrics (JSON), /dashboard (HTML with Chart.js)
- **UI** (`brand_os_ui/`) — Next.js 14 App Router: /dashboard, /run, /history, /agents, /visuals
- **Integrations** (`brand_os_integrations/`) — Twilio WhatsApp, LinkedIn API v2
- **E2E tests** (`tests_e2e/`) — 11 test groups: config, SDK, API, KIRP, CLI, scheduler, monitoring, integrations, n8n, UI, Docker

---

## Architecture Diagram (ASCII)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                        BRAND OS v3 COMPLETE ECOSYSTEM                          │
└───────────────────────────────────────────────────────────────────────────────┘
         │
         ├─── Triggers: CLI (brandos), API (POST /brand-os/run), n8n, KIRP, Scheduler
         │
         ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR (brand_os_sdk.run_orchestrator)                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ Prepare Input → CONTEXT_SCANNER → STRATEGIC_PLANNER →                  │  │
│  │ TECHNICAL_STORYTELLER → HUMAN_EDGE → IDENTITY_GUARDIAN (gatekeeper) →  │  │
│  │ IF approved → SKEPTICAL_CTO (gatekeeper) → IF approved →               │  │
│  │ VISUAL_GENERATOR → Logging → GROWTH_ANALYST → Final Output             │  │
│  │                                                                         │  │
│  │ Revision loops:                                                         │  │
│  │   IDENTITY_GUARDIAN reject → Revision → HUMAN_EDGE (max 1)             │  │
│  │   SKEPTICAL_CTO reject → Revision → HUMAN_EDGE (max 1)                 │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│  OUTPUT (final_output_format)                                                 │
│  trace_id, tenant_id, platform, topic_hint                                    │
│  content: headline, body, hook_used, cta_used                                 │
│  visual_spec: image_prompt, aspect_ratio, format, alt_text                    │
│  recommendations: suggested_timing, hook_rotation, cta_rotation, topics       │
│  status: approved | rejected_identity | rejected_cto                          │
└───────────────────────────────────────────────────────────────────────────────┘
         │
         ├─── Publish: WhatsApp (Twilio), LinkedIn (API v2), log to memory
         ├─── Monitor: brand_os_monitoring (/metrics, /dashboard)
         └─── UI: brand_os_ui (Next.js 14: /dashboard, /run, /history, /agents, /visuals)
```

---

## Config Layer (8 JSON files)

| File | Description |
|------|--------------|
| 00_Master_Identity_Core.json | brand_name, mission, values, tone_profile, constraints, audience_archetypes; rules; thresholds; enums; examples |
| 02_Content_Memory_Log.json | log_schema, retention, usage_rules, dedup_rules; rules; thresholds; examples |
| 03_Voice_Engine.json | voice_id, sentence_rules, vocabulary, platform_adaptations; rules; thresholds; enums; examples |
| 04_Agent_Mesh_Protocol.json | agents, flow_order, handoff_schema, contracts; rules; thresholds; enums; examples |
| 05_Hook_Library.json | hooks, ctas, openers; rules; thresholds; enums; examples |
| 06_Visual_Identity.json | colors, typography, imagery_rules, output_specs; rules; thresholds; enums; examples |
| 07_World_Context_Engine.json | sources, refresh_policies, signal_schema, weighting; rules; thresholds; enums; examples |
| 08_Platform_Distribution_Map.json | platforms, variant_schema, routing_rules; rules; thresholds; enums; examples |

---

## Agent Descriptions (8 agents)

| Agent | Role | Phase | Inputs From | Outputs To |
|-------|------|-------|-------------|------------|
| CONTEXT_SCANNER | Scan and synthesize world context (signals, trends, memory) | context | trigger | STRATEGIC_PLANNER |
| STRATEGIC_PLANNER | Turn world context into strategy brief (angle, key_points, hook, CTA) | strategy | CONTEXT_SCANNER | TECHNICAL_STORYTELLER |
| TECHNICAL_STORYTELLER | Draft first version (headline, body, hook_used, cta_used) | creation | STRATEGIC_PLANNER | HUMAN_EDGE |
| HUMAN_EDGE | Polish draft for clarity and platform-native feel; accepts revision_notes | creation | TECHNICAL_STORYTELLER (or revision) | IDENTITY_GUARDIAN |
| IDENTITY_GUARDIAN | Gatekeeper: approve if identity_alignment ≥ 0.85 and tone_deviation ≤ 0.15; else reject with revision_notes | quality | HUMAN_EDGE | SKEPTICAL_CTO (if approved) / HUMAN_EDGE (revision, max 1) |
| SKEPTICAL_CTO | Gatekeeper: approve if technical_accuracy ≥ 0.85 and overclaim_risk ≤ 0.2; else reject with revision_notes | quality | IDENTITY_GUARDIAN | VISUAL_GENERATOR (if approved) / HUMAN_EDGE (revision, max 1) |
| VISUAL_GENERATOR | Produce visual_spec (image_prompt, aspect_ratio, format, alt_text) | distribution | SKEPTICAL_CTO | final output |
| GROWTH_ANALYST | Advisory: recommendations (suggested_timing, hook_rotation, cta_rotation, next_topic_hints) | distribution | final content | advisory |

---

## Workflow Explanation

1. **Trigger** — Input: tenant_id, platform, topic_hint; optional trace_id, signals, memory_entries.
2. **Prepare Input** — Generate trace_id if missing; attach config (identity, voice, hooks, platform, visual).
3. **CONTEXT_SCANNER** — Output: world_context, trends, signals_used, memory_summary.
4. **STRATEGIC_PLANNER** — Output: strategy_brief (angle, key_points, suggested_hook_id, suggested_cta_id, tone_note).
5. **TECHNICAL_STORYTELLER** — Output: draft (headline, body, hook_used, cta_used).
6. **HUMAN_EDGE** — Output: polished_draft.
7. **IDENTITY_GUARDIAN** — Output: approved, identity_alignment, tone_deviation, revision_notes. If approved=false, pass revision_notes to HUMAN_EDGE and re-run HUMAN_EDGE → IDENTITY_GUARDIAN once (max one identity revision).
8. **IF Identity Approved?** — Yes → SKEPTICAL_CTO; No (after revision) → set status=rejected_identity and stop.
9. **SKEPTICAL_CTO** — Output: approved, technical_accuracy, overclaim_risk, revision_notes. If approved=false, pass revision_notes to HUMAN_EDGE and re-run HUMAN_EDGE → IDENTITY_GUARDIAN → SKEPTICAL_CTO once (max one CTO revision).
10. **IF CTO Approved?** — Yes → VISUAL_GENERATOR; No (after revision) → set status=rejected_cto and stop.
11. **VISUAL_GENERATOR** — Output: visual_spec (image_prompt, aspect_ratio, format, alt_text).
12. **Logging** — Log trace_id, tenant_id, platform, approved/rejected.
13. **GROWTH_ANALYST** — Output: recommendations.
14. **Final Output** — Assemble: trace_id, tenant_id, platform, topic_hint, content, visual_spec, recommendations, status.

Defined in: `workflow/master_orchestrator_workflow.json`, `execution/EXECUTION_TEMPLATE.json`.

---

## Modules

### Python SDK (`brand_os_sdk/`)

**Exports:**
- `load_identity()` — Load Master Identity Core from config/00_Master_Identity_Core.json
- `load_voice()` — Load Voice Engine from config/03_Voice_Engine.json
- `list_agents()` — List agent IDs from agents/*.json
- `run_orchestrator(input_payload: dict) -> dict` — Run the pipeline; returns final_output_format
- `handle_kirp_event(event: dict) -> Optional[dict]` — Route KIRP events; for brand_os_run_started runs orchestrator

**Example:**
```python
from brand_os_sdk import run_orchestrator
result = run_orchestrator({"tenant_id": "t1", "platform": "linkedin", "topic_hint": "API release"})
```

### FastAPI (`api/`)

**Endpoints:**
- `GET /health` → `{"status": "ok", "service": "brand-os-v3-api"}`
- `POST /brand-os/run` → final_output_format (trace_id, content, visual_spec, recommendations, status)

**Run:** `uvicorn api.main:app --reload` → `http://127.0.0.1:8000`

### CLI (`brand_os_cli/`)

**Commands:**
- `brandos run "<topic>"` — Calls API or SDK; prints content, visual spec, recommendations
- `brandos daily` — Runs CONTEXT_SCANNER, picks best signal, runs orchestrator, optional WhatsApp, appends to memory log
- `brandos signals` — Runs CONTEXT_SCANNER; prints world_context, trends
- `brandos agents` — Prints list of agents

**Install:** `pip install -e .` → `brandos` command available

### Scheduler (`brand_os_scheduler/`)

Daily job at 08:00: CONTEXT_SCANNER → pick best signal → run_orchestrator → optional WhatsApp → append to memory log.

**Run:** `python run_scheduler.py` (blocks; runs daily at 08:00)

**Env:** `BRAND_OS_TENANT_ID`, `BRAND_OS_PLATFORM`, `BRAND_OS_WHATSAPP_TO`

### Monitoring (`brand_os_monitoring/`)

**Endpoints:**
- `GET /metrics` — JSON: total_runs, approved, rejected_identity, rejected_cto, avg_revisions, top_hooks, top_pillars
- `GET /dashboard` — HTML with Chart.js (doughnut: status distribution; bar: top topics)

**Run:** `uvicorn brand_os_monitoring.app:app --port 8001 --reload` → `http://127.0.0.1:8001`

**Data source:** `brand_os_v3/storage/content_memory_log.jsonl`

### UI (`brand_os_ui/`)

Next.js 14 App Router with pages: /, /dashboard, /run, /history, /agents, /visuals.

**Run:** `cd brand_os_ui && npm run dev` → `http://localhost:3001`

**Components:** Layout, PostCard, VisualCard, AgentCard, RunForm

**API client:** `lib/api.ts` — `runBrandOs()`, `healthCheck()`

**Theme:** Primary #0A2540, secondary #00D4AA, accent #FF6B35 (from Visual Identity)

### Integrations (`brand_os_integrations/`)

**WhatsApp (Twilio):**
```python
from brand_os_integrations.whatsapp import send_whatsapp
send_whatsapp("+1234567890", "Hello")
```
Env: `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_WHATSAPP_FROM`

**LinkedIn (API v2):**
```python
from brand_os_integrations.linkedin import post_text, post_image
post_text("Hello from Brand OS!")
```
Env: `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN`, `LINKEDIN_ASSET_URN` (for images)

### E2E Tests (`tests_e2e/`)

11 test groups: config validity, SDK, API, KIRP integration, CLI, scheduler, monitoring, integrations, n8n workflow, UI build, Docker.

**Run:** `pytest -q tests_e2e/` → 38 passed, 3 skipped

---

## Quick Start

### Local development

```bash
# 1. Install Python deps
pip install -e .

# 2. Run API
uvicorn api.main:app --reload
# API: http://127.0.0.1:8000

# 3. Run UI (separate terminal)
cd brand_os_ui && npm install && npm run dev
# UI: http://localhost:3001

# 4. Run CLI
brandos run "API release" --tenant tenant-1 --platform linkedin

# 5. Run scheduler (separate terminal)
python run_scheduler.py

# 6. Run monitoring (separate terminal)
uvicorn brand_os_monitoring.app:app --port 8001 --reload
# Dashboard: http://127.0.0.1:8001/dashboard

# 7. Run E2E tests
pytest -q tests_e2e/
```

### Docker

```bash
# Build API
docker build -f Dockerfile.brand_os_api -t brand-os-api .
docker run -p 8000:8000 brand-os-api
# API: http://localhost:8000

# Build UI (create brand_os_ui/Dockerfile first; see OPERATIONS_MANUAL.md)
cd brand_os_ui && docker build -t brand-os-ui .
docker run -p 3001:3001 -e NEXT_PUBLIC_BRAND_OS_API_URL=http://host.docker.internal:8000 brand-os-ui
# UI: http://localhost:3001
```

---

## KIRP Event Mapping

Defined in `kirp/workflow_mapping.yaml` and `kirp/governance_policy.yaml`.

| Trigger | KIRP event | Payload fields |
|--------|------------|----------------|
| Workflow started | brand_os_v3.workflow.started | trace_id, tenant_id, platform, topic_hint |
| Agent step complete | brand_os_v3.workflow.step | trace_id, node_id, approved_or_rejected, revision_notes_if_any |
| Workflow completed | brand_os_v3.workflow.completed | trace_id, tenant_id, platform, status, content_headline, visual_spec_format |
| Identity rejected | brand_os_v3.identity.rejected | trace_id, identity_alignment, tone_deviation, revision_notes |
| CTO rejected | brand_os_v3.cto.rejected | trace_id, technical_accuracy, overclaim_risk, revision_notes |

Agent completion events: brand_os_v3.context_scanner.completed, brand_os_v3.strategic_planner.completed, … (one per agent).

Governance rules (governance_policy.yaml): identity_must_align, no_forbidden_topics, no_forbidden_claims, technical_accuracy, agent_order, revision_loop_max.

Full KIRP integration: `brand_os_v3/KIRP_INTEGRATION.md`.

---

## n8n Workflow

Import `n8n/brand_os_v3_workflow.json` into n8n. Run with Manual Trigger; supply tenant_id, platform, topic_hint.

**Nodes:** Manual Trigger, Prepare Input, CONTEXT_SCANNER, STRATEGIC_PLANNER, TECHNICAL_STORYTELLER, HUMAN_EDGE, IDENTITY_GUARDIAN, Identity Approved?, SKEPTICAL_CTO, CTO Approved?, Revision (Identity), Revision (CTO), VISUAL_GENERATOR (HTTP placeholder), Visual Brief Fallback, Logging, Final Output JSON.

**Connections:** Trigger → Prepare → CONTEXT_SCANNER → … → HUMAN_EDGE → IDENTITY_GUARDIAN → IF → SKEPTICAL_CTO → IF → VISUAL_GENERATOR → Fallback → Logging → Final Output. Rejection branches loop back to HUMAN_EDGE.

Executable in n8n without modification. For production: replace Code stubs with HTTP calls to Brand OS API or LLM.

---

## File Map

| Path | Description |
|------|--------------|
| config/*.json | 8 config files (identity, voice, mesh, world, platform, memory, hook, visual) |
| agents/*.json | 8 agent files (role, input/output schema, prompt, examples, gatekeeper logic) |
| workflow/master_orchestrator_workflow.json | Trigger, nodes, connections, flow_order, gatekeeper_loops, final_output_schema |
| execution/EXECUTION_TEMPLATE.json | orchestrator_system_prompt, user_prompt_template, agent/gatekeeper order, revision_loop rules, final_output_format |
| kirp/*.yaml | 3 YAML files (governance_policy, agent_specs, workflow_mapping) |
| n8n/brand_os_v3_workflow.json | n8n workflow export (Manual Trigger → … → Final Output) |
| README.md | This file (system overview, architecture, modules, quick start, KIRP, n8n, file map, how to extend) |
| KIRP_INTEGRATION.md | KIRP events, governance, agent_specs alignment, SDK handle_kirp_event |
| OPERATIONS_MANUAL.md | Full operations guide (setup, usage, deployment, CI/CD, multi-tenant, auto-learning, analytics) |
| FILE_MAP.md | Complete file list, purpose, interactions, module, dependency graph, learning guide |

**SDK:** brand_os_sdk/ (config_loader, orchestrator, kirp_integration, __init__)

**API:** api/ (main.py, __init__)

**CLI:** brand_os_cli/ (main.py, __init__)

**Scheduler:** brand_os_scheduler/ (scheduler.py, __init__); run_scheduler.py

**Monitoring:** brand_os_monitoring/ (app.py, templates/dashboard.html, __init__)

**UI:** brand_os_ui/ (app/, components/, lib/, package.json, next.config.js, tailwind.config.js, tsconfig.json, postcss.config.js, next-env.d.ts)

**Integrations:** brand_os_integrations/ (whatsapp.py, linkedin.py, __init__)

**E2E tests:** tests_e2e/ (11 test files: test_config_validity, test_sdk, test_api, test_kirp_integration, test_cli, test_scheduler, test_monitoring, test_integrations, test_n8n_workflow, test_ui_build, test_docker)

**Root:** pyproject.toml, Dockerfile.brand_os_api, README_API.md

---

## How to Extend

### Add a new agent

1. Add `agents/<ID>.json` with role, input_schema, output_schema, prompt_template, example_input, example_output.
2. Add to `config/04_Agent_Mesh_Protocol.json` (agents array, flow_order).
3. Add to `execution/EXECUTION_TEMPLATE.json` (agent_invocation_order).
4. Add node and connections in `workflow/master_orchestrator_workflow.json` and `n8n/brand_os_v3_workflow.json`.
5. Add entry in `kirp/agent_specs.yaml` and `kirp/workflow_mapping.yaml`.
6. Update `brand_os_sdk/orchestrator.py` to invoke the new agent.

### Add a new platform

1. Add platform entry in `config/08_Platform_Distribution_Map.json` (id, name, enabled, limits, content_rules).
2. Add platform_adaptations in `config/03_Voice_Engine.json`.
3. Extend platform enum in agent input_schemas (CONTEXT_SCANNER, STRATEGIC_PLANNER, etc.).
4. Update `workflow/master_orchestrator_workflow.json` platform_variants.
5. Add platform variant logic in TECHNICAL_STORYTELLER or HUMAN_EDGE.

### Add a new gatekeeper

1. Add `agents/<ID>.json` with gatekeeper_logic (approve_condition, on_reject, on_approve).
2. Insert in flow_order between HUMAN_EDGE and VISUAL_GENERATOR (or after SKEPTICAL_CTO).
3. Add IF node and revision loop in workflow and n8n.
4. Add to gatekeeper_invocation_order and revision_loop_rules in EXECUTION_TEMPLATE.json.
5. Update KIRP governance_policy and workflow_mapping.

### Add a new integration

1. Create `brand_os_integrations/<platform>.py` with post function.
2. Export from `brand_os_integrations/__init__.py`.
3. Use in CLI or scheduler.

### Add a new UI page

1. Create `brand_os_ui/app/<page>/page.tsx`.
2. Add link in `brand_os_ui/components/Layout.tsx`.

### Add a new CLI command

1. Edit `brand_os_cli/main.py`: add `@brandos.command("<name>")` function.
2. Run: `brandos <name>`.

---

## Resources

- **OPERATIONS_MANUAL.md** — Full operations guide (setup, usage, deployment, cloud, CI/CD, multi-tenant, auto-learning, analytics, troubleshooting)
- **KIRP_INTEGRATION.md** — KIRP events, governance, agent_specs alignment, SDK handle_kirp_event
- **README_API.md** (repo root) — API usage, SDK usage, KIRP integration, deployment
- **FILE_MAP.md** — Complete file list, purpose, interactions, module, dependency graph, learning guide
- **E2E tests** — `tests_e2e/` (11 test groups); run with `pytest -q tests_e2e/`
- **Monitoring** — `http://127.0.0.1:8001/dashboard` (metrics and charts)
