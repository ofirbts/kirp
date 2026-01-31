# Brand OS v3.0 — Full Documentation

A complete, modular, multi-agent Brand Operating System: config, agents, workflow, execution template, Python SDK, FastAPI, KIRP integration, and n8n export.

---

## Full System Overview

Brand OS v3 produces on-brand, platform-adapted content (headline, body, hook, CTA, visual spec) from tenant_id, platform, and topic_hint. It runs a pipeline of eight agents in order, with two gatekeepers (IDENTITY_GUARDIAN, SKEPTICAL_CTO) that can reject and trigger one revision loop each. Config lives under `brand_os_v3/config/`, agent definitions under `brand_os_v3/agents/`, orchestration under `brand_os_v3/workflow/` and `brand_os_v3/execution/`. KIRP governance and event mapping live under `brand_os_v3/kirp/`. The system can be run via the Python SDK (`brand_os_sdk`), the FastAPI app (`api/main.py`), or the n8n workflow (`brand_os_v3/n8n/brand_os_v3_workflow.json`).

---

## Architecture Diagram (ASCII)

```
                    ┌─────────────────────────────────────────────────────────────────┐
                    │                        BRAND OS v3                               │
                    └─────────────────────────────────────────────────────────────────┘
                                                              │
     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
     │   Trigger    │     │   Config     │     │   Execution   │     │   Output     │
     │ tenant_id    │────▶│ brand_os_v3/ │────▶│ EXECUTION_   │────▶│ final_output │
     │ platform     │     │ config/      │     │ TEMPLATE     │     │ _format      │
     │ topic_hint   │     │ agents/     │     │ workflow/    │     │ content      │
     └──────────────┘     └──────────────┘     └──────────────┘     │ visual_spec  │
              │                     │                    │           │ status       │
              │                     │                    │           └──────────────┘
              ▼                     ▼                    ▼
     ┌─────────────────────────────────────────────────────────────────────────────┐
     │                         AGENT PIPELINE (flow_order)                          │
     │                                                                              │
     │  Prepare Input ──▶ CONTEXT_SCANNER ──▶ STRATEGIC_PLANNER ──▶ TECHNICAL_      │
     │                                                                 STORYTELLER  │
     │         │                    │                    │                    │     │
     │         ▼                    ▼                    ▼                    ▼     │
     │  HUMAN_EDGE ◀──────── Revision (Identity) ◀── IDENTITY_GUARDIAN ──▶ IF?     │
     │       │                    │                         │                  │     │
     │       │                    │                         ▼                  │     │
     │       │                    │              SKEPTICAL_CTO ◀─────────────────┘   │
     │       │                    │                    │                            │
     │       │                    └──────── Revision (CTO) ◀────────── IF?           │
     │       │                              │                            │           │
     │       ▼                              ▼                            ▼           │
     │  VISUAL_GENERATOR ──▶ Logging ──▶ GROWTH_ANALYST ──▶ Final Output            │
     │                                                                              │
     └─────────────────────────────────────────────────────────────────────────────┘
              │                     │                    │
              ▼                     ▼                    ▼
     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
     │  Python SDK  │     │  FastAPI     │     │  n8n         │
     │ brand_os_   │     │ api/main.py  │     │ brand_os_v3_ │
     │ sdk         │     │ POST /brand- │     │ workflow     │
     │ run_        │     │ os/run       │     │ .json        │
     │ orchestrator│     │              │     │              │
     └──────────────┘     └──────────────┘     └──────────────┘
              │                     │                    │
              └─────────────────────┴────────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  KIRP Integration    │
                         │  kirp/*.yaml         │
                         │  handle_kirp_event() │
                         └──────────────────────┘
```

---

## Config Layer

Config files under `brand_os_v3/config/` define identity, voice, agent mesh, world context, platform distribution, content memory, hooks, and visual identity.

| File | Description |
|------|--------------|
| 00_Master_Identity_Core.json | brand_name, mission, values, tone_profile, constraints, audience_archetypes; rules; thresholds (identity_alignment_min_score, tone_deviation_max); enums; examples |
| 02_Content_Memory_Log.json | log_schema, retention, usage_rules, dedup_rules; rules; thresholds; examples |
| 03_Voice_Engine.json | voice_id, sentence_rules, vocabulary, platform_adaptations; rules; thresholds; enums; examples |
| 04_Agent_Mesh_Protocol.json | agents (id, name, phase, inputs_from, outputs_to), flow_order, handoff_schema, contracts; rules; thresholds; enums; examples |
| 05_Hook_Library.json | hooks, ctas, openers; rules; thresholds; enums; examples |
| 06_Visual_Identity.json | colors, typography, imagery_rules, output_specs; rules; thresholds; enums; examples |
| 07_World_Context_Engine.json | sources, refresh_policies, signal_schema, weighting; rules; thresholds; enums; examples |
| 08_Platform_Distribution_Map.json | platforms, variant_schema, routing_rules; rules; thresholds; enums; examples |

---

## Agent Descriptions

Agents under `brand_os_v3/agents/` each have role, responsibilities, input_schema, output_schema, prompt_template, failure_modes, example_input, example_output, and gatekeeper_logic (for gatekeepers).

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

1. **Trigger** — Input: tenant_id, platform, topic_hint; optional trace_id, signals, memory_entries (extra_context).
2. **Prepare Input** — Generate trace_id if missing; attach config (identity, voice, hooks, platform, visual).
3. **CONTEXT_SCANNER** — Output: world_context, trends, signals_used, memory_summary.
4. **STRATEGIC_PLANNER** — Output: strategy_brief (angle, key_points, suggested_hook_id, suggested_cta_id, tone_note).
5. **TECHNICAL_STORYTELLER** — Output: draft (headline, body, hook_used, cta_used).
6. **HUMAN_EDGE** — Output: polished_draft.
7. **IDENTITY_GUARDIAN** — Output: approved, identity_alignment, tone_deviation, revision_notes. If approved=false, pass revision_notes to HUMAN_EDGE and re-run HUMAN_EDGE → IDENTITY_GUARDIAN once (max one identity revision).
8. **IF Identity Approved?** — Yes → SKEPTICAL_CTO; No (after revision) → set status=rejected_identity and stop, or retry once.
9. **SKEPTICAL_CTO** — Output: approved, technical_accuracy, overclaim_risk, revision_notes. If approved=false, pass revision_notes to HUMAN_EDGE and re-run HUMAN_EDGE → IDENTITY_GUARDIAN → SKEPTICAL_CTO once (max one CTO revision).
10. **IF CTO Approved?** — Yes → VISUAL_GENERATOR; No (after revision) → set status=rejected_cto and stop, or retry once.
11. **VISUAL_GENERATOR** — Output: visual_spec (image_prompt, aspect_ratio, format, alt_text).
12. **Logging** — Log trace_id, tenant_id, platform, approved/rejected.
13. **GROWTH_ANALYST** — Output: recommendations.
14. **Final Output** — Assemble: trace_id, tenant_id, platform, topic_hint, content, visual_spec, recommendations, status (approved | rejected_identity | rejected_cto).

Defined in: `workflow/master_orchestrator_workflow.json`, `execution/EXECUTION_TEMPLATE.json`.

---

## API Usage

The FastAPI app lives at `api/main.py` (repo root). Run from repo root:

```bash
uvicorn api.main:app --reload
```

- Base URL: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`
- Health: `GET /health` → `{"status": "ok", "service": "brand-os-v3-api"}`
- Run pipeline: `POST /brand-os/run`

**POST /brand-os/run** — Body: tenant_id (required), platform (required), topic_hint (required), trace_id (optional), extra_context (optional). Response: final_output_format (trace_id, tenant_id, platform, topic_hint, content, visual_spec, recommendations, status). 503 if config not found; 400 on invalid input.

See `README_API.md` (repo root) for full API and deployment details.

---

## SDK Usage

The Python SDK lives under `brand_os_sdk/` (repo root). It reads config and agents from `brand_os_v3/config/` and `brand_os_v3/agents/` (path from `BRAND_OS_V3_PATH` or default repo sibling).

**Exports:**

- `load_identity()` — Load Master Identity Core from `config/00_Master_Identity_Core.json`.
- `load_voice()` — Load Voice Engine from `config/03_Voice_Engine.json`.
- `list_agents()` — List agent IDs from `agents/*.json` (e.g. CONTEXT_SCANNER, STRATEGIC_PLANNER, …).
- `run_orchestrator(input_payload: dict) -> dict` — Run the pipeline per EXECUTION_TEMPLATE and workflow; returns final_output_format. input_payload must include tenant_id, platform, topic_hint; optional trace_id, extra_context (signals, memory_entries).

**Example:**

```python
from brand_os_sdk import load_identity, load_voice, list_agents, run_orchestrator

identity = load_identity()
voice = load_voice()
agents = list_agents()  # ['CONTEXT_SCANNER', 'GROWTH_ANALYST', ...]

result = run_orchestrator({
    "tenant_id": "tenant-1",
    "platform": "linkedin",
    "topic_hint": "API release",
})
# result: trace_id, tenant_id, platform, topic_hint, content, visual_spec, recommendations, status
```

**KIRP integration:** `brand_os_sdk.kirp_integration.handle_kirp_event(event)` routes KIRP events; for event_type `brand_os_run_started` or `brand_os_v3.workflow.started` it runs the orchestrator and returns the result. See `brand_os_v3/KIRP_INTEGRATION.md` and `README_API.md`.

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

Agent completion events: brand_os_v3.context_scanner.completed, brand_os_v3.strategic_planner.completed, … (one per agent). Gatekeeper reject events: brand_os_v3.identity.rejected, brand_os_v3.cto.rejected.

Governance rules (governance_policy.yaml): identity_must_align, no_forbidden_topics, no_forbidden_claims, technical_accuracy, agent_order, revision_loop_max. identity_constraints and agent_constraints define allowed inputs and required outputs per agent.

Full mapping and alignment with `agents/*.json` is in `brand_os_v3/KIRP_INTEGRATION.md`.

---

## n8n Workflow Explanation

The file `n8n/brand_os_v3_workflow.json` is a real n8n workflow export. Import it into n8n to run the pipeline visually.

**Nodes:**

- **Manual Trigger** — Start with tenant_id, platform, topic_hint (and optionally trace_id, signals, memory_entries).
- **Prepare Input** — Code node: normalizes input and sets trace_id.
- **CONTEXT_SCANNER** — Code node: produces context_brief (stub).
- **STRATEGIC_PLANNER** — Code node: produces content_brief (stub).
- **TECHNICAL_STORYTELLER** — Code node: produces draft.
- **HUMAN_EDGE** — Code node: produces human_draft.
- **IDENTITY_GUARDIAN** — Code node: identity_result (approved, score, reasons, suggested_fixes).
- **Identity Approved?** — IF node: true → SKEPTICAL_CTO; false → Revision (Identity).
- **Revision (Identity)** — Code node: revises draft from identity_result.suggested_fixes; connects back to HUMAN_EDGE.
- **SKEPTICAL_CTO** — Code node: cto_result (approved, claims_checked, issues, suggested_fixes).
- **CTO Approved?** — IF node: true → VISUAL_GENERATOR; false → Revision (CTO).
- **Revision (CTO)** — Code node: revises draft from cto_result; connects back to HUMAN_EDGE.
- **VISUAL_GENERATOR** — HTTP Request node (placeholder URL); continueOnFail true.
- **Visual Brief Fallback** — Code node: builds visual_spec from input or SKEPTICAL_CTO context when HTTP is not used or fails.
- **Logging** — Code node: logs trace_id, tenant_id, platform, event.
- **Final Output JSON** — Set node: assembles content, visual, context_brief, content_brief, gatekeeper_results, timestamp.

**Connections:** Manual Trigger → Prepare Input → CONTEXT_SCANNER → … → HUMAN_EDGE → IDENTITY_GUARDIAN → Identity Approved? → (true) SKEPTICAL_CTO → CTO Approved? → (true) VISUAL_GENERATOR → Visual Brief Fallback → Logging → Final Output JSON. Rejection branches go to Revision (Identity) or Revision (CTO) then back to HUMAN_EDGE.

Executable in n8n without modification. For production, replace Code-node stubs with HTTP calls to an LLM or the Brand OS API.

---

## Deployment Instructions

### Local (API)

From repo root:

```bash
pip install "fastapi>=0.109.0" "uvicorn[standard]>=0.27.0" "pydantic>=2.0.0"
export BRAND_OS_V3_PATH=/path/to/brand_os_v3   # optional; default is repo sibling
uvicorn api.main:app --reload
```

API: `http://127.0.0.1:8000`. POST /brand-os/run with tenant_id, platform, topic_hint.

### Local (SDK only)

From repo root, ensure `brand_os_v3/` is present (or set BRAND_OS_V3_PATH). Then:

```python
from brand_os_sdk import run_orchestrator
result = run_orchestrator({"tenant_id": "t1", "platform": "linkedin", "topic_hint": "API"})
```

### Docker (API)

From repo root:

```bash
docker build -f Dockerfile.brand_os_api -t brand-os-api .
docker run -p 8000:8000 brand-os-api
```

Image copies brand_os_v3/, brand_os_sdk/, api/ and sets BRAND_OS_V3_PATH=/app/brand_os_v3. API: `http://localhost:8000`.

### n8n

Import `brand_os_v3/n8n/brand_os_v3_workflow.json` into n8n. Run with Manual Trigger; supply tenant_id, platform, topic_hint in the trigger payload.

---

## File Map

| Path | Description |
|------|--------------|
| config/00_Master_Identity_Core.json | Identity, mission, values, tone, constraints, audience |
| config/02_Content_Memory_Log.json | Log schema, retention, usage_rules, dedup_rules |
| config/03_Voice_Engine.json | Voice id, sentence_rules, vocabulary, platform_adaptations |
| config/04_Agent_Mesh_Protocol.json | Agents, flow_order, handoff_schema, contracts |
| config/05_Hook_Library.json | Hooks, ctas, openers |
| config/06_Visual_Identity.json | Colors, typography, imagery_rules, output_specs |
| config/07_World_Context_Engine.json | Sources, refresh_policies, signal_schema, weighting |
| config/08_Platform_Distribution_Map.json | Platforms, variant_schema, routing_rules |
| agents/*.json | Role, input/output schema, prompt_template, examples, gatekeeper_logic |
| workflow/master_orchestrator_workflow.json | Trigger, nodes, connections, flow_order, gatekeeper_loops, final_output_schema |
| execution/EXECUTION_TEMPLATE.json | orchestrator_system_prompt, user_prompt_template, agent/gatekeeper order, revision_loop rules, final_output_format |
| kirp/governance_policy.yaml | Rules, identity_constraints, agent_constraints, event_triggers |
| kirp/agent_specs.yaml | Agent definitions, input/output refs, governance tags, kirp_event_* |
| kirp/workflow_mapping.yaml | event_triggers, routing_rules, agent_to_kirp_event |
| n8n/brand_os_v3_workflow.json | n8n workflow export (Manual Trigger → … → Final Output) |
| KIRP_INTEGRATION.md | KIRP events, governance, agent_specs alignment, SDK routes |

---

## How to Extend

- **New agent:** Add `agents/<ID>.json`; add to config/04_Agent_Mesh_Protocol.json and execution/EXECUTION_TEMPLATE.json; add node and connections in workflow and n8n workflow; add entry in kirp/agent_specs.yaml and kirp/workflow_mapping.yaml.
- **New platform:** Add platform in config/08_Platform_Distribution_Map.json and config/03_Voice_Engine.json platform_adaptations; extend platform enum in agent input_schemas and workflow.
- **New gatekeeper:** Add agent JSON with gatekeeper_logic; insert in flow_order; add IF node and revision loop in workflow and n8n; add to gatekeeper_invocation_order and revision_loop_rules; update KIRP policy and mapping.
- **New config file:** Add JSON under config/; reference from Agent Mesh Protocol or execution template; inject into agents as needed.
