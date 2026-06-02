"""
Run Brand OS v3 orchestrator: EXECUTION_TEMPLATE + workflow logic.
Agents are executed in-process with deterministic stubs (example_outputs); plug in LLM later.
"""

import json
import copy
from pathlib import Path
from typing import Any

from brand_os_sdk.config_loader import _base_path, _read_json

_AGENT_ORDER = [
    "CONTEXT_SCANNER",
    "STRATEGIC_PLANNER",
    "TECHNICAL_STORYTELLER",
    "HUMAN_EDGE",
    "IDENTITY_GUARDIAN",
    "SKEPTICAL_CTO",
    "VISUAL_GENERATOR",
    "GROWTH_ANALYST",
]


def _load_agent(agent_id: str, base: Path) -> dict[str, Any]:
    path = base / "agents" / f"{agent_id}.json"
    return _read_json(path)


def _load_execution_template(base: Path) -> dict[str, Any]:
    return _read_json(base / "execution" / "EXECUTION_TEMPLATE.json")


def _stub_run_agent(agent_id: str, state: dict[str, Any], base: Path) -> dict[str, Any]:
    """Run agent stub: merge example_output into state, with trace_id/tenant_id/platform/topic_hint overridden."""
    spec = _load_agent(agent_id, base)
    out = spec.get("example_output") or {}
    out = copy.deepcopy(out)
    for k in ("trace_id", "tenant_id", "platform", "topic_hint"):
        if k in state:
            out[k] = state[k]
    return out


def run_orchestrator(input_payload: dict[str, Any], base: Path | None = None) -> dict[str, Any]:
    """
    Run the Brand OS v3 pipeline per EXECUTION_TEMPLATE and workflow.
    input_payload must include: tenant_id, platform, topic_hint.
    Optional: trace_id, extra_context (signals, memory_entries).
    Returns final_output_format (trace_id, tenant_id, platform, topic_hint, content, visual_spec, recommendations, status).
    """
    root = base if base is not None else _base_path()
    template = _load_execution_template(root)
    tenant_id = input_payload["tenant_id"]
    platform = input_payload["platform"]
    topic_hint = input_payload["topic_hint"]
    trace_id = input_payload.get("trace_id") or f"tr_{id(input_payload)}_{hash(str(input_payload)) % 10**8}"
    extra = input_payload.get("extra_context") or {}
    signals = extra.get("signals", [])
    memory_entries = extra.get("memory_entries", [])

    state: dict[str, Any] = {
        "trace_id": trace_id,
        "tenant_id": tenant_id,
        "platform": platform,
        "topic_hint": topic_hint,
        "signals": signals,
        "memory_entries": memory_entries,
    }
    revision_count_identity = 0
    revision_count_cto = 0
    identity_approved = True
    cto_approved = True
    polished_draft: dict[str, Any] = {}
    visual_spec: dict[str, Any] = {}
    recommendations: dict[str, Any] = {}

    # CONTEXT_SCANNER
    ctx_out = _stub_run_agent("CONTEXT_SCANNER", state, root)
    state["world_context"] = ctx_out.get("world_context", "")
    state["trends"] = ctx_out.get("trends", [])
    state["memory_summary"] = ctx_out.get("memory_summary", "")

    # STRATEGIC_PLANNER (inject identity mission)
    identity = _read_json(root / "config" / "00_Master_Identity_Core.json")
    state["brand_mission"] = identity.get("mission", "")
    state["audience_archetypes"] = identity.get("audience_archetypes", [])
    strat_out = _stub_run_agent("STRATEGIC_PLANNER", state, root)
    state["strategy_brief"] = strat_out.get("strategy_brief", {})

    # TECHNICAL_STORYTELLER
    story_out = _stub_run_agent("TECHNICAL_STORYTELLER", state, root)
    state["draft"] = story_out.get("draft", {})

    # HUMAN_EDGE
    def run_human_edge(revision_notes: str = "") -> None:
        state["revision_notes"] = revision_notes
        human_out = _stub_run_agent("HUMAN_EDGE", state, root)
        state["polished_draft"] = human_out.get("polished_draft", state.get("draft", {}))

    run_human_edge()
    polished_draft = state["polished_draft"]

    # IDENTITY_GUARDIAN
    state["master_identity"] = identity
    id_out = _stub_run_agent("IDENTITY_GUARDIAN", state, root)
    identity_approved = id_out.get("approved", True)
    if not identity_approved and revision_count_identity < 1:
        revision_count_identity += 1
        run_human_edge(id_out.get("revision_notes", ""))
        polished_draft = state["polished_draft"]
        id_out = _stub_run_agent("IDENTITY_GUARDIAN", state, root)
        identity_approved = id_out.get("approved", True)

    if not identity_approved:
        status = "rejected_identity"
    else:
        # SKEPTICAL_CTO
        state["strategy_brief"] = state.get("strategy_brief", {})
        state["world_context"] = state.get("world_context", "")
        cto_out = _stub_run_agent("SKEPTICAL_CTO", state, root)
        cto_approved = cto_out.get("approved", True)
        if not cto_approved and revision_count_cto < 1:
            revision_count_cto += 1
            run_human_edge(cto_out.get("revision_notes", ""))
            polished_draft = state["polished_draft"]
            state["master_identity"] = identity
            _ = _stub_run_agent("IDENTITY_GUARDIAN", state, root)
            cto_out = _stub_run_agent("SKEPTICAL_CTO", state, root)
            cto_approved = cto_out.get("approved", True)
        if not cto_approved:
            status = "rejected_cto"
        else:
            status = "approved"
            # VISUAL_GENERATOR
            state["visual_identity"] = _read_json(root / "config" / "06_Visual_Identity.json").get("examples", {}).get("identity") or {}
            vis_out = _stub_run_agent("VISUAL_GENERATOR", state, root)
            visual_spec = vis_out.get("visual_spec", {
                "image_prompt": "Minimal diagram, brand-aligned.",
                "aspect_ratio": "1.91:1",
                "format": "png",
                "alt_text": "Generated visual.",
            })

    # GROWTH_ANALYST (always run for recommendations)
    state["final_content"] = {
        "headline": polished_draft.get("headline", ""),
        "body": polished_draft.get("body", ""),
        "hook_used": polished_draft.get("hook_used", ""),
        "cta_used": polished_draft.get("cta_used", ""),
    }
    growth_out = _stub_run_agent("GROWTH_ANALYST", state, root)
    recommendations = growth_out.get("recommendations", {})

    if not visual_spec:
        visual_spec = {
            "image_prompt": "Minimal diagram, brand-aligned.",
            "aspect_ratio": "1.91:1",
            "format": "png",
            "alt_text": "Generated visual.",
        }

    return {
        "trace_id": trace_id,
        "tenant_id": tenant_id,
        "platform": platform,
        "topic_hint": topic_hint,
        "content": {
            "headline": polished_draft.get("headline", ""),
            "body": polished_draft.get("body", ""),
            "hook_used": polished_draft.get("hook_used", ""),
            "cta_used": polished_draft.get("cta_used", ""),
        },
        "visual_spec": visual_spec,
        "recommendations": recommendations,
        "status": status,
    }
