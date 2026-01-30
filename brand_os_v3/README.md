# Brand OS v3.0 — Complete Specification

A complete, modular, multi-agent Brand Operating System with four layers:

1. **World Context Engine** — External signals, trends, and constraints.
2. **Cognitive Core** — Identity + Voice (Master Identity Core, Voice Engine).
3. **Agent Factory** — All agents + gatekeepers (CONTEXT_SCANNER → … → IDENTITY_GUARDIAN → SKEPTICAL_CTO).
4. **Distribution & Memory** — Platform variants, visual generation, Content Memory, Growth Analyst.

---

## Full Explanation of All Layers

### Layer 1: World Context Engine

- **Purpose:** Shape what we say and when by ingesting industry news, competitor activity, audience sentiment, calendar, and product releases.
- **Config:** `07_World_Context_Engine.json` (sources, signals, rules, thresholds).
- **Agent:** CONTEXT_SCANNER — outputs relevant_signals, recommended_angle, risks, opportunities.

### Layer 2: Cognitive Core (Identity + Voice)

- **Purpose:** Define who the brand is (identity, boundaries, voice) and how it sounds (tone, style, vocabulary).
- **Config:** `00_Master_Identity_Core.json` (identity, voice, boundaries, rules, examples), `03_Voice_Engine.json` (tone_axes, style_rules, vocabulary, thresholds).
- **Agents:** STRATEGIC_PLANNER consumes context + identity and produces content brief (headline, hook, CTA, platform_notes).

### Layer 3: Agent Factory (Content + Gatekeepers)

- **Purpose:** Draft content, add human edge, then pass through two gatekeepers (Identity, CTO).
- **Agents:**
  - TECHNICAL_STORYTELLER — full post from content brief in brand voice.
  - HUMAN_EDGE — one concrete detail and warmth.
  - IDENTITY_GUARDIAN (gatekeeper) — approve/reject on identity + voice; on reject, revision loop (max 2) via TECHNICAL_STORYTELLER.
  - SKEPTICAL_CTO (gatekeeper) — approve/reject on factual/claim defensibility; on reject, revision loop (max 2).

### Layer 4: Distribution & Memory

- **Purpose:** Produce platform-specific variants, generate visual brief, log run and performance.
- **Config:** `08_Platform_Distribution_Map.json`, `06_Visual_Identity.json`, `02_Content_Memory_Log.json`.
- **Agents:** VISUAL_GENERATOR (image prompt + aspect ratio + alt text per platform), GROWTH_ANALYST (log workflow output, optional composite_score, recommendations).

---

## File Map

| Section | Path | Description |
|--------|------|--------------|
| Config | `config/00_Master_Identity_Core.json` | Identity, voice, boundaries, rules, thresholds, examples |
| Config | `config/03_Voice_Engine.json` | Tone axes, style rules, vocabulary, thresholds, platform modifiers |
| Config | `config/04_Agent_Mesh_Protocol.json` | Agent order, handoff schema, conflict resolution, timeouts, logging |
| Config | `config/07_World_Context_Engine.json` | Sources, signals, rules, thresholds, output schema |
| Config | `config/08_Platform_Distribution_Map.json` | Per-platform rules (LinkedIn, Twitter, WhatsApp) |
| Config | `config/02_Content_Memory_Log.json` | Storage, performance schema, similarity rules, thresholds |
| Config | `config/05_Hook_Library.json` | Hook categories (question, statistic, story, contrarian, direct_value) |
| Config | `config/06_Visual_Identity.json` | Brand colors, imagery, generation prompts, rules |
| Agents | `agents/CONTEXT_SCANNER.json` | World context agent |
| Agents | `agents/STRATEGIC_PLANNER.json` | Content strategy agent |
| Agents | `agents/TECHNICAL_STORYTELLER.json` | Copywriting agent |
| Agents | `agents/HUMAN_EDGE.json` | Human-edge agent |
| Agents | `agents/IDENTITY_GUARDIAN.json` | Identity gatekeeper |
| Agents | `agents/SKEPTICAL_CTO.json` | Claims gatekeeper |
| Agents | `agents/VISUAL_GENERATOR.json` | Visual brief agent |
| Agents | `agents/GROWTH_ANALYST.json` | Memory + recommendations agent |
| Workflow | `workflow/master_orchestrator_workflow.json` | n8n-style nodes, connections, gatekeeper loops, platform variants, example run |
| Execution | `execution/EXECUTION_TEMPLATE.json` | Orchestrator prompt, user prompt, agent order, revision rules, final output format |
| KIRP | `kirp/governance_policy.yaml` | OPA policy bundle for Brand OS |
| KIRP | `kirp/agent_specs.yaml` | YAML definitions for all agents |
| KIRP | `kirp/workflow_mapping.yaml` | Brand OS → KIRP event types and routing |
| n8n | `n8n/brand_os_v3_workflow.json` | Executable n8n workflow export |

---

## Agent Map

| Agent | Layer | Input | Output | Gatekeeper |
|-------|--------|--------|--------|-------------|
| CONTEXT_SCANNER | world_context | tenant_id, platform, topic_hint | relevant_signals, recommended_angle, risks, opportunities | No |
| STRATEGIC_PLANNER | cognitive | context_brief, platform, identity_core | headline, key_message, hook_type, hook_text, cta, platform_notes | No |
| TECHNICAL_STORYTELLER | content | content_brief, platform, voice_engine, max_length | body, hook, cta, hashtags, full_text, word_count | No |
| HUMAN_EDGE | content | draft, platform, identity_core | body, hook, cta, full_text, concrete_detail_used, human_edge_notes | No |
| IDENTITY_GUARDIAN | gatekeeper | draft, identity_core, voice_engine | approved, score, reasons, suggested_fixes | Yes |
| SKEPTICAL_CTO | gatekeeper | draft, identity_core | approved, claims_checked, issues, suggested_fixes | Yes |
| VISUAL_GENERATOR | distribution | approved_draft, platform, visual_identity | prompt, aspect_ratio, alt_text | No |
| GROWTH_ANALYST | memory | workflow_output, trace_id | logged, composite_score, summary, recommendations | No |

---

## Workflow Map

1. **Start** → Load Config (all 8 JSON configs).
2. **CONTEXT_SCANNER** → STRATEGIC_PLANNER → TECHNICAL_STORYTELLER → HUMAN_EDGE.
3. **IDENTITY_GUARDIAN** → If approved → SKEPTICAL_CTO. If rejected → TECHNICAL_STORYTELLER (revision) → HUMAN_EDGE → IDENTITY_GUARDIAN (max 2 revisions).
4. **SKEPTICAL_CTO** → If approved → Platform variants (LinkedIn, Twitter, WhatsApp) → VISUAL_GENERATOR. If rejected → TECHNICAL_STORYTELLER (revision) → HUMAN_EDGE → IDENTITY_GUARDIAN → SKEPTICAL_CTO (max 2 revisions).
5. **VISUAL_GENERATOR** → Logging → GROWTH_ANALYST → Final Output JSON.

---

## How to Run the System

1. **Config:** Ensure all files in `config/` are loaded (paths or env pointing to `brand_os_v3/config/`).
2. **Input:** Provide `tenant_id`, `platform` (linkedin | twitter | whatsapp), `topic_hint`, `trace_id`.
3. **Orchestrator:** Use `execution/EXECUTION_TEMPLATE.json` → `orchestrator_system_prompt` and `user_prompt_template` (fill `{{tenant_id}}`, `{{platform}}`, `{{topic_hint}}`, `{{trace_id}}`, `{{platforms}}`).
4. **Agent order:** Invoke agents in `agent_invocation_order`. For gatekeepers, if rejected, run `revision_loop` (max 2 per gatekeeper).
5. **Output:** Assemble JSON per `final_output_format` and return.

**n8n:** Import `n8n/brand_os_v3_workflow.json` into n8n, configure credentials (OpenAI/API for agent nodes, optional Google Sheets for logging), then run with Manual Trigger or webhook input.

**KIRP:** Ingest `kirp/governance_policy.yaml`, `kirp/agent_specs.yaml`, and `kirp/workflow_mapping.yaml` per KIRP docs to enforce governance and route events.

---

## How to Extend the System

- **New config:** Add a JSON file under `config/` and reference it in Load Config and in the agent(s) that need it.
- **New agent:** Add a JSON file under `agents/` with role, responsibilities, input_schema, output_schema, prompt_template, failure_modes. Insert in `04_Agent_Mesh_Protocol.json` and in workflow between the appropriate nodes; update `execution/EXECUTION_TEMPLATE.json` → `agent_invocation_order`.
- **New platform:** Add an entry in `08_Platform_Distribution_Map.json` (platforms) and in workflow `platform_variants`; add a platform variant node and connect to VISUAL_GENERATOR.
- **New gatekeeper:** Add agent JSON with `gatekeeper_logic` (on_approve, on_reject, max_revisions, revision_agent). Insert in mesh protocol and workflow after the correct step; add an IF node and revision loop.
- **New hook type:** Add a category in `05_Hook_Library.json` and extend STRATEGIC_PLANNER prompt/output (hook_type enum).
