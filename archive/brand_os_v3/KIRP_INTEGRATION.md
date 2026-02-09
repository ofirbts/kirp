# Brand OS v3 — KIRP Integration

How Brand OS v3 maps to KIRP events, governance, and agent specs using `brand_os_v3/kirp/*.yaml`, and how the Python SDK routes events via `handle_kirp_event()`.

---

## 1. KIRP Events That Map to Brand OS

Defined in **`kirp/workflow_mapping.yaml`**:

| Trigger | KIRP event | Payload fields |
|--------|------------|----------------|
| Workflow started | `brand_os_v3.workflow.started` | trace_id, tenant_id, platform, topic_hint |
| Agent step complete | `brand_os_v3.workflow.step` | trace_id, node_id, approved_or_rejected, revision_notes_if_any |
| Workflow completed | `brand_os_v3.workflow.completed` | trace_id, tenant_id, platform, status, content_headline, visual_spec_format |
| Identity rejected | `brand_os_v3.identity.rejected` | trace_id, identity_alignment, tone_deviation, revision_notes |
| CTO rejected | `brand_os_v3.cto.rejected` | trace_id, technical_accuracy, overclaim_risk, revision_notes |

**Agent completion events** (from `agent_to_kirp_event` in workflow_mapping.yaml):

- `brand_os_v3.context_scanner.completed` → CONTEXT_SCANNER
- `brand_os_v3.strategic_planner.completed` → STRATEGIC_PLANNER
- `brand_os_v3.technical_storyteller.completed` → TECHNICAL_STORYTELLER
- `brand_os_v3.human_edge.completed` → HUMAN_EDGE
- `brand_os_v3.identity_guardian.completed` / `brand_os_v3.identity.rejected` → IDENTITY_GUARDIAN
- `brand_os_v3.skeptical_cto.completed` / `brand_os_v3.cto.rejected` → SKEPTICAL_CTO
- `brand_os_v3.visual_generator.completed` → VISUAL_GENERATOR
- `brand_os_v3.growth_analyst.completed` → GROWTH_ANALYST

**Routing:** Each step completion routes to the next node (or to a revision loop) per `routing_rules` in workflow_mapping.yaml.

---

## 2. How governance_policy.yaml Constrains Agents

**`kirp/governance_policy.yaml`** defines:

**Rules**

- **identity_must_align** — Content must align with Master Identity: `identity_alignment >= 0.85` and `tone_deviation <= 0.15`; else reject with revision_notes.
- **no_forbidden_topics** — No `forbidden_topics` from Master Identity in content.
- **no_forbidden_claims** — No `forbidden_claims` from Master Identity in content.
- **technical_accuracy** — SKEPTICAL_CTO must pass: `technical_accuracy >= 0.85`, `overclaim_risk <= 0.2`; else reject with revision_notes.
- **agent_order** — Agents must run in flow_order (CONTEXT_SCANNER → … → GROWTH_ANALYST); violation → log warning.
- **revision_loop_max** — At most one revision per gatekeeper (IDENTITY_GUARDIAN, SKEPTICAL_CTO); else stop and emit status.

**identity_constraints** — Source: `config/00_Master_Identity_Core.json`. Checks: mission_alignment, values_no_contradiction, tone_match, constraints_respected (no forbidden topics/claims; required disclaimers when applicable).

**agent_constraints** — Per agent: allowed inputs and required outputs. Examples:

- CONTEXT_SCANNER: inputs trace_id, tenant_id, platform, topic_hint, signals, memory_entries → outputs world_context, trends, signals_used, memory_summary.
- STRATEGIC_PLANNER: inputs world_context, trends, memory_summary, brand_mission, audience_archetypes, hook_library → outputs strategy_brief.
- HUMAN_EDGE: inputs draft, voice_rules, revision_notes → outputs polished_draft.
- IDENTITY_GUARDIAN: inputs polished_draft, master_identity → outputs approved, identity_alignment, tone_deviation, revision_notes.
- SKEPTICAL_CTO: inputs polished_draft, strategy_brief, world_context → outputs approved, technical_accuracy, overclaim_risk, revision_notes.
- VISUAL_GENERATOR: inputs polished_draft, visual_identity → outputs visual_spec.
- GROWTH_ANALYST: inputs final_content, performance_history → outputs recommendations.

The pipeline must respect these inputs/outputs and rule thresholds so governance stays consistent with the policy file.

---

## 3. How agent_specs.yaml Aligns With brand_os_v3/agents/*.json

**`kirp/agent_specs.yaml`** lists one entry per Brand OS agent and ties it to the JSON definitions:

- **id** — Matches the agent JSON filename (e.g. `CONTEXT_SCANNER` ↔ `agents/CONTEXT_SCANNER.json`).
- **name**, **version**, **role** — Same semantics as in the corresponding `brand_os_v3/agents/<ID>.json` (name, version, role).
- **input_schema_ref** / **output_schema_ref** — Point at the JSON file and fragment, e.g. `brand_os_v3/agents/CONTEXT_SCANNER.json#input_schema` and `#output_schema`. The actual schemas live in those agent JSON files.
- **governance_tags** — Phase and kind: context, strategy, creation, quality, distribution; gatekeeper vs non_gatekeeper; revision_target, advisory. Used for routing and audit.
- **kirp_event_on_complete** — Event to emit when the agent finishes (e.g. `brand_os_v3.context_scanner.completed`).
- **kirp_event_on_reject** — For gatekeepers only (IDENTITY_GUARDIAN, SKEPTICAL_CTO): event on reject (e.g. `brand_os_v3.identity.rejected`, `brand_os_v3.cto.rejected`).

So: **agent_specs.yaml** is the KIRP-facing registry (ids, phases, schema refs, event names); **agents/*.json** hold the full definitions (input_schema, output_schema, prompt_template, example_output, gatekeeper_logic). Keeping agent_specs in sync with the JSON files keeps event names, routing, and governance aligned.

---

## 4. SDK Event Handling: handle_kirp_event()

The Python SDK module **`brand_os_sdk.kirp_integration`** exposes **`handle_kirp_event(event: dict) -> Optional[dict]`** to route KIRP events.

**Routes:**

| event_type | Behavior | Return value |
|------------|----------|--------------|
| `brand_os_run_started` or `brand_os_v3.workflow.started` | Runs `run_orchestrator(payload)` | final_output_format (trace_id, content, visual_spec, recommendations, status) or None on error |
| `agent_completed` or any `brand_os_v3.*.completed` | Acknowledge agent step | `{"ack": true, "route": "agent_completed", "trace_id": ...}` |
| `gatekeeper_decision` or `brand_os_v3.identity.rejected` or `brand_os_v3.cto.rejected` | Acknowledge gatekeeper decision | `{"ack": true, "route": "gatekeeper_decision", "trace_id": ...}` |
| `run_completed` or `brand_os_v3.workflow.completed` | Acknowledge run completed | `{"ack": true, "route": "run_completed", "trace_id": ...}` |
| `run_failed` | Acknowledge run failed | `{"ack": true, "route": "run_failed", "trace_id": ...}` |

**Event shape:** The function accepts `event_type` from `event["event_type"]`, `event["type"]`, or `event["event"]`, and `payload` from `event["payload"]` or the whole `event`.

---

## 5. Example Event JSON (Start a Run)

To start a run and get the orchestrator result, send an event with `event_type: "brand_os_run_started"` (or `brand_os_v3.workflow.started`) and a payload with tenant_id, platform, topic_hint:

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

Pass this to `handle_kirp_event(event)`. The return value is the full final_output_format (same shape as `POST /brand-os/run`):

- trace_id, tenant_id, platform, topic_hint
- content: headline, body, hook_used, cta_used
- visual_spec: image_prompt, aspect_ratio, format, alt_text
- recommendations: suggested_timing, hook_rotation, cta_rotation, next_topic_hints
- status: approved | rejected_identity | rejected_cto

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

---

## 6. Audit Fields

From **governance_policy.yaml** and **workflow_mapping.yaml**, audit_fields for Brand OS v3 events include:

- trace_id, tenant_id, platform, topic_hint
- node_id, approved, revision_count_identity, revision_count_cto
- status, timestamp, agent_invocations

Use these when emitting or persisting KIRP events for audit and debugging.
