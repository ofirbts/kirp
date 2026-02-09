# Brand OS v3.0 — Complete File Map

Complete list of every file and folder in the Brand OS v3 ecosystem, with purpose, interactions, module assignment, dependency graph, and learning guide.

---

## 1. Complete File List

### Core (brand_os_v3/)

**Config (brand_os_v3/config/)**

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| 00_Master_Identity_Core.json | Canonical brand identity: brand_name, mission, values, tone_profile, constraints, audience_archetypes; rules; thresholds; enums; examples | Core | Loaded by SDK config_loader; injected into IDENTITY_GUARDIAN, STRATEGIC_PLANNER; used in governance_policy |
| 02_Content_Memory_Log.json | Schema for logging past content: log_schema, retention, usage_rules, dedup_rules; rules; thresholds; examples | Core | Schema reference for memory log storage (brand_os_v3/storage/content_memory_log.jsonl); used by CONTEXT_SCANNER, monitoring dashboard |
| 03_Voice_Engine.json | Linguistic rules: voice_id, sentence_rules, vocabulary, platform_adaptations; rules; thresholds; enums; examples | Core | Loaded by SDK; injected into TECHNICAL_STORYTELLER, HUMAN_EDGE; used for tone/style checks |
| 04_Agent_Mesh_Protocol.json | Orchestration: agents, flow_order, handoff_schema, contracts; rules; thresholds; enums; examples | Core | Defines agent execution order; used by orchestrator to sequence agents |
| 05_Hook_Library.json | Reusable hooks, CTAs, openers; rules; thresholds; enums; examples | Core | Loaded by SDK; injected into STRATEGIC_PLANNER; used to pick hooks/CTAs |
| 06_Visual_Identity.json | Visual guidelines: colors, typography, imagery_rules, output_specs; rules; thresholds; enums; examples | Core | Loaded by SDK; injected into VISUAL_GENERATOR; used for UI theme (brand_os_ui tailwind.config) |
| 07_World_Context_Engine.json | External signals: sources, refresh_policies, signal_schema, weighting; rules; thresholds; enums; examples | Core | Schema for signals passed to CONTEXT_SCANNER; used by CLI signals command |
| 08_Platform_Distribution_Map.json | Platform-specific rules: platforms, variant_schema, routing_rules; rules; thresholds; enums; examples | Core | Loaded by SDK; injected into TECHNICAL_STORYTELLER, HUMAN_EDGE; used for platform limits |

**Agents (brand_os_v3/agents/)**

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| CONTEXT_SCANNER.json | Agent: scan/synthesize world context; input_schema, output_schema, prompt_template, example_input, example_output | Core | Invoked first by orchestrator; outputs world_context, trends, memory_summary → STRATEGIC_PLANNER |
| STRATEGIC_PLANNER.json | Agent: turn context into strategy brief; input_schema, output_schema, prompt_template, examples | Core | Invoked after CONTEXT_SCANNER; outputs strategy_brief → TECHNICAL_STORYTELLER |
| TECHNICAL_STORYTELLER.json | Agent: draft first version; input_schema, output_schema, prompt_template, examples | Core | Invoked after STRATEGIC_PLANNER; outputs draft → HUMAN_EDGE |
| HUMAN_EDGE.json | Agent: polish draft; input_schema, output_schema, prompt_template, examples | Core | Invoked after TECHNICAL_STORYTELLER or revision; outputs polished_draft → IDENTITY_GUARDIAN |
| IDENTITY_GUARDIAN.json | Gatekeeper: identity + tone; input_schema, output_schema, prompt_template, gatekeeper_logic, examples | Core | Invoked after HUMAN_EDGE; outputs approved, identity_alignment, tone_deviation, revision_notes; if reject → revision loop to HUMAN_EDGE |
| SKEPTICAL_CTO.json | Gatekeeper: technical accuracy + overclaim; input_schema, output_schema, prompt_template, gatekeeper_logic, examples | Core | Invoked after IDENTITY_GUARDIAN (if approved); outputs approved, technical_accuracy, overclaim_risk, revision_notes; if reject → revision loop to HUMAN_EDGE |
| VISUAL_GENERATOR.json | Agent: produce visual spec; input_schema, output_schema, prompt_template, examples | Core | Invoked after SKEPTICAL_CTO (if approved); outputs visual_spec → final output |
| GROWTH_ANALYST.json | Agent: recommendations; input_schema, output_schema, prompt_template, examples | Core | Invoked last; outputs recommendations → final output |

**Workflow (brand_os_v3/workflow/)**

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| master_orchestrator_workflow.json | Orchestration flow: trigger, nodes, connections, flow_order, gatekeeper_loops, platform_variants, logging_logic, visual_generation_logic, final_output_schema, example_workflow_run | Core | Defines agent execution order and gatekeeper loops; used by SDK orchestrator and n8n workflow |

**Execution (brand_os_v3/execution/)**

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| EXECUTION_TEMPLATE.json | orchestrator_system_prompt, user_prompt_template, agent_invocation_order, gatekeeper_invocation_order, revision_loop rules, final_output_format, example_final_output | Core | Loaded by SDK orchestrator; defines agent order, revision rules, output schema |

**KIRP (brand_os_v3/kirp/)**

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| governance_policy.yaml | Governance rules, identity_constraints, agent_constraints, audit_fields, event_triggers, examples | Core | Defines rules for IDENTITY_GUARDIAN, SKEPTICAL_CTO; used by KIRP for policy enforcement |
| agent_specs.yaml | Agent definitions for KIRP: id, name, version, role, input/output refs, governance_tags, kirp_event_on_complete/reject | Core | Maps agents to KIRP events; used by KIRP for routing and audit |
| workflow_mapping.yaml | Agent-to-KIRP-event mapping, routing_rules, audit_fields, examples | Core | Defines event triggers (workflow.started, workflow.step, workflow.completed, identity.rejected, cto.rejected); used by SDK handle_kirp_event |

**n8n (brand_os_v3/n8n/)**

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| brand_os_v3_workflow.json | Real n8n workflow export: name, nodes, connections, settings, meta, pinData, versionId, tags | Core | Importable into n8n; executable without modification; nodes call Code stubs (replace with HTTP to API for production) |

**Documentation (brand_os_v3/)**

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| README.md | System overview, architecture, modules, quick start, KIRP, n8n, file map, how to extend | Core | Entry point for developers; links to KIRP_INTEGRATION, OPERATIONS_MANUAL, FILE_MAP |
| KIRP_INTEGRATION.md | KIRP events, governance, agent_specs alignment, SDK handle_kirp_event, example event JSON | Core | KIRP integration guide; used by KIRP developers |
| OPERATIONS_MANUAL.md | Full operations guide: setup, usage, deployment, cloud, CI/CD, multi-tenant, auto-learning, analytics, troubleshooting | Core | Complete ops guide; used by DevOps and developers |
| FILE_MAP.md | This file: complete file list, purpose, interactions, module, dependency graph, learning guide | Core | Reference for understanding the system structure |

**Storage (brand_os_v3/storage/)**

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| content_memory_log.jsonl | Content memory log: one JSON per line (trace_id, tenant_id, platform, body_hash, published_at, status, performance) | Core | Appended by CLI daily, scheduler; read by monitoring dashboard; used by CONTEXT_SCANNER for dedup |

---

### SDK (brand_os_sdk/)

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| __init__.py | Exports: load_identity, load_voice, list_agents, run_orchestrator | SDK | Entry point for SDK; imported by API, CLI, scheduler |
| config_loader.py | Load config/agents from brand_os_v3: _base_path, _read_json, load_identity, load_voice, list_agents | SDK | Used by orchestrator, CLI, scheduler to load config |
| orchestrator.py | run_orchestrator: runs agent pipeline per EXECUTION_TEMPLATE and workflow; stub execution using agent example_outputs | SDK | Called by API, CLI, scheduler, KIRP integration; returns final_output_format |
| kirp_integration.py | handle_kirp_event: routes KIRP events (brand_os_run_started, agent_completed, gatekeeper_decision, run_completed, run_failed) | SDK | Called by KIRP workers; for brand_os_run_started calls run_orchestrator |

---

### API (api/)

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| __init__.py | Package marker | API | None |
| main.py | FastAPI app: GET /health, POST /brand-os/run (calls run_orchestrator) | API | Entry point for API; imports brand_os_sdk.run_orchestrator; returns final_output_format |

---

### CLI (brand_os_cli/)

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| __init__.py | Package marker | CLI | None |
| main.py | Click CLI: brandos run, brandos daily, brandos signals, brandos agents | CLI | Imports brand_os_sdk (run_orchestrator, load_identity, etc.); calls API or SDK; appends to memory log |

---

### Scheduler (brand_os_scheduler/)

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| __init__.py | Package marker | Scheduler | None |
| scheduler.py | APScheduler daily job at 08:00: CONTEXT_SCANNER → pick best signal → run_orchestrator → optional WhatsApp → append to memory log | Scheduler | Imports brand_os_sdk (run_orchestrator, _stub_run_agent); imports brand_os_integrations.whatsapp; appends to content_memory_log.jsonl |

**Root (repo root)**

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| run_scheduler.py | Script to start scheduler (calls brand_os_scheduler.scheduler.start_scheduler) | Scheduler | Entry point for scheduler; run with `python run_scheduler.py` |

---

### Monitoring (brand_os_monitoring/)

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| __init__.py | Package marker | Monitoring | None |
| app.py | FastAPI app: GET /metrics (JSON), GET /dashboard (HTML with Chart.js) | Monitoring | Reads brand_os_v3/storage/content_memory_log.jsonl; uses Jinja2Templates for dashboard.html |
| templates/dashboard.html | Jinja2 template: HTML dashboard with Chart.js (doughnut: status distribution; bar: top topics) | Monitoring | Rendered by app.py /dashboard endpoint; receives metrics dict |

---

### UI (brand_os_ui/)

**Root (brand_os_ui/)**

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| package.json | Node.js deps: next, react, react-dom, tailwindcss, typescript | UI | Defines scripts: dev, build, start, lint |
| next.config.js | Next.js config: reactStrictMode | UI | Used by Next.js build |
| tailwind.config.js | TailwindCSS config: colors (primary #0A2540, secondary #00D4AA, accent #FF6B35 from Visual Identity) | UI | Used by PostCSS and Next.js |
| tsconfig.json | TypeScript config: target ES2017, lib dom/esnext, paths @/* | UI | Used by Next.js and TypeScript compiler |
| postcss.config.js | PostCSS config: tailwindcss, autoprefixer | UI | Used by Next.js build |
| next-env.d.ts | Next.js type declarations | UI | Auto-generated; used by TypeScript |

**App (brand_os_ui/app/)**

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| layout.tsx | Root layout: imports globals.css, wraps children in Layout component | UI | Used by all pages; imports components/Layout |
| page.tsx | Home page: links to /dashboard and /run | UI | Entry point; uses Next.js Link |
| globals.css | Global styles: Tailwind base/components/utilities; body bg-neutral-50 text-primary | UI | Imported by layout.tsx |
| dashboard/page.tsx | Dashboard page: shows API health, latest runs (stub) | UI | Calls lib/api.healthCheck; displays PostCard components |
| run/page.tsx | Run page: form to trigger POST /brand-os/run | UI | Imports components/RunForm |
| history/page.tsx | History page: past runs from content memory log | UI | Calls /api/history (Next.js API route); displays PostCard components |
| agents/page.tsx | Agents page: agent definitions | UI | Calls /api/agents (Next.js API route); displays AgentCard components |
| visuals/page.tsx | Visuals page: generated visual prompts | UI | Calls /api/visuals (Next.js API route); displays VisualCard components |
| api/history/route.ts | Next.js API route: GET /api/history → [] (stub) | UI | Called by history/page.tsx |
| api/agents/route.ts | Next.js API route: GET /api/agents → agent list (default 8 agents) | UI | Called by agents/page.tsx |
| api/visuals/route.ts | Next.js API route: GET /api/visuals → [] (stub) | UI | Called by visuals/page.tsx |

**Components (brand_os_ui/components/)**

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| Layout.tsx | Header with nav (Dashboard, Run, History, Agents, Visuals); wraps children | UI | Used by app/layout.tsx |
| PostCard.tsx | Display content: headline, body, hook_used, cta_used, status, trace_id | UI | Used by dashboard, run, history pages |
| VisualCard.tsx | Display visual spec: image_prompt, aspect_ratio, format, alt_text, trace_id | UI | Used by run, visuals pages |
| AgentCard.tsx | Display agent: id, name, role, phase | UI | Used by agents page |
| RunForm.tsx | Form to trigger POST /brand-os/run; displays result (PostCard + VisualCard) | UI | Used by run/page.tsx; calls lib/api.runBrandOs |

**Lib (brand_os_ui/lib/)**

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| api.ts | API client: runBrandOs(payload), healthCheck(); types: RunPayload, RunResult | UI | Used by components/RunForm, app/dashboard/page.tsx; calls Brand OS API (POST /brand-os/run, GET /health) |

---

### Integrations (brand_os_integrations/)

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| __init__.py | Exports: send_whatsapp, post_text, post_image | Integrations | Entry point for integrations |
| whatsapp.py | Twilio WhatsApp: send_whatsapp(to, message); env: TWILIO_SID, TWILIO_TOKEN, TWILIO_WHATSAPP_FROM | Integrations | Used by CLI daily, scheduler; calls Twilio API |
| linkedin.py | LinkedIn API v2: post_text(content), post_image(content, image_prompt); env: LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN, LINKEDIN_ASSET_URN | Integrations | Used by CLI or custom scripts; calls LinkedIn UGC API |

---

### E2E Tests (tests_e2e/)

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| __init__.py | Package marker | Tests | None |
| test_config_validity.py | Validate all JSON (config, agents, workflow, execution) and YAML (kirp) | Tests | Loads files from brand_os_v3; asserts valid JSON/YAML |
| test_sdk.py | Test load_identity, load_voice, list_agents, run_orchestrator; validate output schema | Tests | Imports brand_os_sdk; calls SDK functions; asserts output shape matches EXECUTION_TEMPLATE |
| test_api.py | Test FastAPI: GET /health, POST /brand-os/run (valid + 422) | Tests | Uses FastAPI TestClient; imports api.main.app; asserts response structure |
| test_kirp_integration.py | Test handle_kirp_event routes (brand_os_run_started, agent_completed, gatekeeper_decision, run_completed, run_failed) | Tests | Imports brand_os_sdk.kirp_integration; calls handle_kirp_event; asserts routing |
| test_cli.py | Test CLI: brandos agents, run, signals, daily | Tests | Uses click.testing.CliRunner; imports brand_os_cli.main.brandos; invokes commands |
| test_scheduler.py | Test scheduler: daily job registration, _pick_best_signal, daily_job (mocked) | Tests | Imports brand_os_scheduler.scheduler; mocks run_orchestrator, _context_scanner_output, _append_memory_log; skips if apscheduler missing |
| test_monitoring.py | Test monitoring: GET /metrics, GET /dashboard (HTML) | Tests | Uses FastAPI TestClient; imports brand_os_monitoring.app.app; asserts response structure |
| test_integrations.py | Test integrations: send_whatsapp (env + Twilio mock), post_text (env + LinkedIn mock) | Tests | Imports brand_os_integrations; mocks twilio.rest.Client, urllib.request.urlopen; skips if twilio missing |
| test_n8n_workflow.py | Test n8n workflow: name, nodes, connections, no orphans | Tests | Loads brand_os_v3/n8n/brand_os_v3_workflow.json; asserts structure |
| test_ui_build.py | Test UI: package.json, next.config, app dir, pages exist | Tests | Checks brand_os_ui/ structure; skips if brand_os_ui missing |
| test_docker.py | Test Docker: Dockerfile.brand_os_api exists and content | Tests | Reads Dockerfile.brand_os_api; asserts FROM, python, uvicorn, EXPOSE |

---

### Root (repo root)

| File | Purpose | Module | Interactions |
|------|---------|--------|--------------|
| pyproject.toml | Project metadata, dependencies (fastapi, uvicorn, pydantic, click, requests, apscheduler, jinja2, twilio), packages (app, brand_os_sdk, api, brand_os_cli, brand_os_scheduler, brand_os_monitoring, brand_os_integrations), scripts (brandos = brand_os_cli.main:main) | Root | Used by pip install -e .; defines entry point for brandos CLI |
| Dockerfile.brand_os_api | Docker image for API: Python 3.12-slim, copies brand_os_v3, brand_os_sdk, api; installs fastapi, uvicorn, pydantic; CMD uvicorn api.main:app | Root | Used by docker build -f Dockerfile.brand_os_api; runs API on port 8000 |
| README_API.md | API documentation: overview, architecture, prerequisites, install, run, API usage, SDK usage, CLI usage, scheduler, monitoring, UI, integrations, KIRP, deployment, E2E tests, resources | Root | Entry point for API/SDK/CLI/scheduler/monitoring/UI/integrations; links to brand_os_v3 docs |
| run_scheduler.py | Script to start scheduler: imports brand_os_scheduler.scheduler.start_scheduler; calls start_scheduler() | Root | Entry point for scheduler; run with python run_scheduler.py |

---

## 2. Module Assignment

| Module | Files | Purpose |
|--------|-------|---------|
| **Core** | brand_os_v3/ (config, agents, workflow, execution, kirp, n8n, docs, storage) | Config, agent definitions, orchestration flow, KIRP governance, n8n workflow, documentation |
| **SDK** | brand_os_sdk/ (__init__, config_loader, orchestrator, kirp_integration) | Python SDK: load config, run orchestrator, handle KIRP events |
| **API** | api/ (__init__, main) | FastAPI: POST /brand-os/run, GET /health |
| **CLI** | brand_os_cli/ (__init__, main) | Click CLI: brandos run, brandos daily, brandos signals, brandos agents |
| **Scheduler** | brand_os_scheduler/ (__init__, scheduler); run_scheduler.py | APScheduler daily job: auto-run pipeline at 08:00 |
| **Monitoring** | brand_os_monitoring/ (__init__, app, templates/dashboard.html) | FastAPI + Jinja2: /metrics, /dashboard |
| **UI** | brand_os_ui/ (app, components, lib, config files) | Next.js 14 App Router: /dashboard, /run, /history, /agents, /visuals |
| **Integrations** | brand_os_integrations/ (__init__, whatsapp, linkedin) | Twilio WhatsApp, LinkedIn API v2 |
| **Tests** | tests_e2e/ (11 test files) | E2E test suite: config, SDK, API, KIRP, CLI, scheduler, monitoring, integrations, n8n, UI, Docker |
| **Root** | pyproject.toml, Dockerfile.brand_os_api, README_API.md | Project config, Docker build, API documentation |

---

## 3. Dependency Graph (Text-Based)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BRAND OS v3 DEPENDENCIES                         │
└─────────────────────────────────────────────────────────────────────────┘

Core (brand_os_v3/)
  ├─ config/*.json (no deps; loaded by SDK)
  ├─ agents/*.json (no deps; loaded by SDK)
  ├─ workflow/*.json (no deps; loaded by SDK)
  ├─ execution/*.json (no deps; loaded by SDK)
  ├─ kirp/*.yaml (no deps; used by KIRP)
  ├─ n8n/*.json (no deps; imported by n8n)
  └─ docs (README, KIRP_INTEGRATION, OPERATIONS_MANUAL, FILE_MAP)

SDK (brand_os_sdk/)
  ├─ config_loader → brand_os_v3/config/, brand_os_v3/agents/
  ├─ orchestrator → config_loader, brand_os_v3/execution/, brand_os_v3/workflow/
  ├─ kirp_integration → orchestrator
  └─ __init__ → config_loader, orchestrator

API (api/)
  └─ main → brand_os_sdk (run_orchestrator)

CLI (brand_os_cli/)
  └─ main → brand_os_sdk (run_orchestrator, load_identity, list_agents), requests (for API calls)

Scheduler (brand_os_scheduler/)
  └─ scheduler → brand_os_sdk (run_orchestrator, _stub_run_agent), brand_os_integrations.whatsapp

Monitoring (brand_os_monitoring/)
  └─ app → brand_os_v3/storage/content_memory_log.jsonl, templates/dashboard.html

UI (brand_os_ui/)
  ├─ lib/api → Brand OS API (POST /brand-os/run, GET /health)
  ├─ components → lib/api
  ├─ app/pages → components, lib/api
  └─ app/api/routes → (stubs; no external deps)

Integrations (brand_os_integrations/)
  ├─ whatsapp → twilio.rest.Client
  └─ linkedin → urllib.request (LinkedIn API v2)

Tests (tests_e2e/)
  ├─ test_config_validity → brand_os_v3/ (config, agents, workflow, execution, kirp)
  ├─ test_sdk → brand_os_sdk
  ├─ test_api → api.main
  ├─ test_kirp_integration → brand_os_sdk.kirp_integration
  ├─ test_cli → brand_os_cli.main
  ├─ test_scheduler → brand_os_scheduler.scheduler
  ├─ test_monitoring → brand_os_monitoring.app
  ├─ test_integrations → brand_os_integrations
  ├─ test_n8n_workflow → brand_os_v3/n8n/
  ├─ test_ui_build → brand_os_ui/
  └─ test_docker → Dockerfile.brand_os_api

Root
  ├─ pyproject.toml → defines packages and entry points
  ├─ Dockerfile.brand_os_api → copies brand_os_v3, brand_os_sdk, api
  ├─ README_API.md → references all modules
  └─ run_scheduler.py → brand_os_scheduler.scheduler
```

---

## 4. How to Learn the System

### Beginner Path (Start here)

1. **Read brand_os_v3/README.md** — System overview, architecture, modules.
2. **Read README_API.md** — API usage, SDK usage, CLI usage.
3. **Run the API:** `uvicorn api.main:app --reload` → POST /brand-os/run with curl or Postman.
4. **Run the CLI:** `brandos run "API release"` → see content, visual spec, recommendations.
5. **Explore config:** Open `brand_os_v3/config/00_Master_Identity_Core.json` and `brand_os_v3/config/03_Voice_Engine.json` → understand identity and voice.
6. **Explore agents:** Open `brand_os_v3/agents/CONTEXT_SCANNER.json` and `brand_os_v3/agents/IDENTITY_GUARDIAN.json` → understand agent structure (role, input_schema, output_schema, prompt_template, gatekeeper_logic).
7. **Run E2E tests:** `pytest -q tests_e2e/` → verify everything works.

### Intermediate Path (Extend the system)

1. **Read brand_os_v3/OPERATIONS_MANUAL.md** — Full operations guide (setup, usage, deployment, troubleshooting).
2. **Read brand_os_v3/KIRP_INTEGRATION.md** — KIRP events, governance, agent_specs alignment, SDK handle_kirp_event.
3. **Explore workflow:** Open `brand_os_v3/workflow/master_orchestrator_workflow.json` and `brand_os_v3/execution/EXECUTION_TEMPLATE.json` → understand orchestration flow, gatekeeper loops, revision rules.
4. **Explore SDK:** Open `brand_os_sdk/orchestrator.py` → understand how run_orchestrator works (agent invocation, gatekeeper logic, stub execution).
5. **Run the UI:** `cd brand_os_ui && npm run dev` → explore /dashboard, /run, /history, /agents, /visuals.
6. **Run the scheduler:** `python run_scheduler.py` → see daily job at 08:00 (or test with `brandos daily`).
7. **Run the monitoring dashboard:** `uvicorn brand_os_monitoring.app:app --port 8001` → explore /metrics, /dashboard.
8. **Add a custom agent:** Follow "How to Extend" in brand_os_v3/README.md → add agents/MY_AGENT.json, update config/04_Agent_Mesh_Protocol.json, execution/EXECUTION_TEMPLATE.json, workflow, n8n, kirp, SDK.
9. **Add a custom platform:** Follow "How to Extend" → add platform in config/08_Platform_Distribution_Map.json, config/03_Voice_Engine.json, agent input_schemas, workflow.

### Advanced Path (Production deployment, multi-tenant, auto-learning)

1. **Read brand_os_v3/OPERATIONS_MANUAL.md sections (A)–(E):**
   - (A) Production Deployment Guide (Railway, Render, Fly.io, Vercel)
   - (B) CI/CD Pipeline (GitHub Actions)
   - (C) Multi-Tenant Mode (tenant folders, isolation, orchestrator extension)
   - (D) Auto-Learning Feedback Loop (engagement data, update hooks/tone, Google Sheets/Supabase)
   - (E) Analytics Layer (metrics, compute functions, dashboard integration)
2. **Deploy to Railway:** Follow OPERATIONS_MANUAL.md section (A) → deploy API and UI to Railway.
3. **Set up CI/CD:** Follow OPERATIONS_MANUAL.md section (B) → create `.github/workflows/brand_os_v3.yml` with test, build, deploy steps.
4. **Enable multi-tenancy:** Follow OPERATIONS_MANUAL.md section (C) → create `brand_os_v3/tenants/<tenant_id>/` folders with identity.json, voice.json, hooks.json, memory_log.jsonl; update SDK config_loader to load tenant-specific config.
5. **Enable auto-learning:** Follow OPERATIONS_MANUAL.md section (D) → collect engagement data, analyze top hooks, update hook library, integrate with Google Sheets or Supabase.
6. **Enable analytics:** Follow OPERATIONS_MANUAL.md section (E) → compute hook/pillar/platform performance, revision/approval rates; add /analytics endpoint to monitoring; visualize in dashboard.
7. **Explore KIRP governance:** Open `brand_os_v3/kirp/governance_policy.yaml` → understand rules, identity_constraints, agent_constraints; open `brand_os_v3/kirp/agent_specs.yaml` → understand agent-to-KIRP-event mapping.
8. **Explore n8n workflow:** Import `brand_os_v3/n8n/brand_os_v3_workflow.json` into n8n → run with Manual Trigger → explore nodes, connections, revision loops; replace Code stubs with HTTP calls to Brand OS API for production.
9. **Integrate with external systems:** Use `brand_os_sdk.kirp_integration.handle_kirp_event` to route KIRP events; call from KIRP workers or webhooks; for brand_os_run_started, orchestrator runs and returns result.
10. **Scale and optimize:** Follow OPERATIONS_MANUAL.md section 21 (Performance Tuning) → use multi-process uvicorn, cache config, parallelize agent calls, use CDN for UI.

---

## 5. Learning Resources

- **brand_os_v3/README.md** — System overview, architecture, modules, quick start, how to extend
- **brand_os_v3/KIRP_INTEGRATION.md** — KIRP events, governance, agent_specs alignment, SDK handle_kirp_event
- **brand_os_v3/OPERATIONS_MANUAL.md** — Full operations guide (setup, usage, deployment, cloud, CI/CD, multi-tenant, auto-learning, analytics, troubleshooting)
- **brand_os_v3/FILE_MAP.md** — This file (complete file list, purpose, interactions, module, dependency graph, learning guide)
- **README_API.md** (repo root) — API usage, SDK usage, CLI usage, scheduler, monitoring, UI, integrations, KIRP, deployment, E2E tests
- **E2E tests** (tests_e2e/) — 11 test groups; run with `pytest -q tests_e2e/`
- **Monitoring dashboard** — `http://127.0.0.1:8001/dashboard` (metrics and charts)
- **UI** — `http://localhost:3001` (dashboard, run, history, agents, visuals)

---

## 6. File Interactions Summary

**Config → SDK → API/CLI/Scheduler**
- Config files (brand_os_v3/config/) are loaded by SDK (config_loader).
- SDK (orchestrator) runs agents per EXECUTION_TEMPLATE and workflow.
- API (api/main) calls SDK run_orchestrator.
- CLI (brand_os_cli/main) calls SDK run_orchestrator or API.
- Scheduler (brand_os_scheduler/scheduler) calls SDK run_orchestrator.

**Agents → SDK → Output**
- Agent files (brand_os_v3/agents/) define input/output schemas, prompt templates, examples.
- SDK (orchestrator) loads agent specs and uses example_outputs for stub execution.
- Output (final_output_format) is returned to API, CLI, scheduler, KIRP.

**KIRP → SDK → Orchestrator**
- KIRP events (workflow_mapping.yaml) are routed by SDK (kirp_integration).
- For brand_os_run_started, SDK calls run_orchestrator and returns result.
- For agent_completed, gatekeeper_decision, run_completed, run_failed, SDK returns ack.

**n8n → Workflow → Output**
- n8n workflow (brand_os_v3/n8n/brand_os_v3_workflow.json) defines nodes and connections.
- Nodes call Code stubs (or HTTP to API for production).
- Output is assembled in Final Output JSON node.

**UI → API → SDK → Output**
- UI (brand_os_ui) calls API (POST /brand-os/run) via lib/api.ts.
- API calls SDK run_orchestrator.
- SDK returns final_output_format.
- UI displays content, visual spec, recommendations, status in PostCard and VisualCard.

**Integrations → External APIs**
- WhatsApp (brand_os_integrations/whatsapp) calls Twilio API.
- LinkedIn (brand_os_integrations/linkedin) calls LinkedIn UGC API.
- Used by CLI daily, scheduler, or custom scripts.

**Monitoring → Memory Log → Dashboard**
- Monitoring (brand_os_monitoring/app) reads content_memory_log.jsonl.
- Computes metrics: total_runs, approved, rejected_identity, rejected_cto, top_hooks, top_pillars.
- Renders dashboard.html with Chart.js.

**Tests → All Modules**
- E2E tests (tests_e2e/) import and test all modules (Core, SDK, API, CLI, scheduler, monitoring, integrations, n8n, UI, Docker).
- Run with pytest -q tests_e2e/.

---

**End of FILE_MAP.md**
