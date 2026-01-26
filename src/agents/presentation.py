"""
Presentation Agent — Generates live views: Kanban, Timeline, Calendar, Mind Map, Brand Content.

Builds structured views from schema nodes and RAG context.
"""

from __future__ import annotations

import logging
from typing import Any
from datetime import datetime, timezone

from src.core.agent_framework import AgentSpec, AutonomyLevel
from src.core.schema_engine import SchemaEngine, SchemaEntity
from src.core.llm_client import get_llm

logger = logging.getLogger(__name__)


async def _handler(
    tenant_id: str,
    space_id: str,
    user_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """
    Produce view payloads for Kanban, Timeline, Calendar, Mind Map, or Brand Content.
    """
    schema_engine: SchemaEngine | None = context.get("schema_engine")
    schema_nodes = context.get("schema_nodes", [])
    rag = context.get("rag_response")
    view_type = context.get("view_type", "kanban")
    idea = context.get("idea")  # For brand content generation
    
    # If schema_nodes is empty but we have schema_engine, fetch nodes
    if not schema_nodes and schema_engine:
        try:
            schema_nodes = await schema_engine.list_nodes(tenant_id=tenant_id, space_id=space_id)
        except Exception as e:
            logger.warning("Failed to fetch schema nodes: %s", e)
    
    # Brand content generation (legacy migration)
    if view_type == "brand_content" or idea:
        return await _generate_brand_content(idea or "", rag, user_id)
    
    # Build view-specific structure
    if view_type == "kanban":
        return await _generate_kanban(schema_nodes, tenant_id, space_id, schema_engine)
    elif view_type == "timeline":
        return await _generate_timeline(schema_nodes, tenant_id, space_id, schema_engine)
    elif view_type == "calendar":
        return await _generate_calendar(schema_nodes, tenant_id, space_id, schema_engine)
    elif view_type == "mindmap":
        return await _generate_mindmap(schema_nodes, tenant_id, space_id, schema_engine)
    else:
        return {"ok": False, "error": f"Unknown view_type: {view_type}"}


async def _generate_brand_content(idea: str, rag: Any, user_id: str) -> dict[str, Any]:
    """Generate brand content (LinkedIn post, etc.) from idea."""
    if not idea:
        return {"ok": False, "error": "No idea provided"}
    
    context_text = ""
    if rag and hasattr(rag, "context_text"):
        context_text = rag.context_text[:1000]
    
    prompt = f"""
Generate professional LinkedIn-style content from this idea:

Idea: {idea}

Context (if relevant):
{context_text}

Create:
1. A compelling headline (with emoji if appropriate)
2. A body (3-4 paragraphs, engaging, actionable)
3. A call-to-action

Return JSON:
{{
  "headline": "🚀 Headline here",
  "body": "Paragraph 1...\n\nParagraph 2...\n\nParagraph 3...",
  "cta": "Call to action",
  "tone": "professional",
  "format": "linkedin_post"
}}
"""
    
    try:
        llm = get_llm()
        response = await llm.invoke(prompt, temperature=0.7, max_tokens=1000)
        
        # Parse JSON
        import json
        response_text = response.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        data = json.loads(response_text)
        return {
            "ok": True,
            "idea": idea,
            "headline": data.get("headline", ""),
            "body": data.get("body", ""),
            "cta": data.get("cta", ""),
            "tone": data.get("tone", "professional"),
            "format": data.get("format", "linkedin_post"),
            "user_id": user_id,
        }
    except Exception as e:
        logger.exception("Brand content generation failed: %s", e)
        return {"ok": False, "error": str(e)}


async def _generate_kanban(
    schema_nodes: list[dict[str, Any]],
    tenant_id: str,
    space_id: str,
    schema_engine: SchemaEngine | None,
) -> dict[str, Any]:
    """Generate Kanban board structure from tasks."""
    # Filter tasks
    tasks = [n for n in schema_nodes if n.get("entity") == SchemaEntity.TASK.value]
    
    # Group by status
    columns = {
        "pending": {"id": "pending", "title": "To Do", "items": []},
        "in_progress": {"id": "in_progress", "title": "In Progress", "items": []},
        "completed": {"id": "completed", "title": "Done", "items": []},
        "blocked": {"id": "blocked", "title": "Blocked", "items": []},
    }
    
    for task in tasks:
        status = task.get("status", "pending")
        column = columns.get(status, columns["pending"])
        column["items"].append({
            "id": task.get("id"),
            "title": task.get("title"),
            "description": task.get("description"),
            "priority": task.get("priority", "medium"),
            "due_date": task.get("due_date"),
        })
    
    return {
        "ok": True,
        "view": {
            "type": "kanban",
            "columns": list(columns.values()),
            "total_items": len(tasks),
        },
        "explanation": "presentation_kanban",
    }


async def _generate_timeline(
    schema_nodes: list[dict[str, Any]],
    tenant_id: str,
    space_id: str,
    schema_engine: SchemaEngine | None,
) -> dict[str, Any]:
    """Generate timeline view from tasks and events."""
    tasks = [n for n in schema_nodes if n.get("entity") == SchemaEntity.TASK.value]
    
    # Sort by due_date or created_at
    timeline_items = []
    for task in tasks:
        due_date = task.get("due_date")
        created_at = task.get("created_at")
        date = due_date or created_at
        
        timeline_items.append({
            "id": task.get("id"),
            "title": task.get("title"),
            "date": date,
            "type": "task",
            "status": task.get("status"),
            "priority": task.get("priority"),
        })
    
    timeline_items.sort(key=lambda x: x.get("date") or "", reverse=True)
    
    return {
        "ok": True,
        "view": {
            "type": "timeline",
            "items": timeline_items,
            "total_items": len(timeline_items),
        },
        "explanation": "presentation_timeline",
    }


async def _generate_calendar(
    schema_nodes: list[dict[str, Any]],
    tenant_id: str,
    space_id: str,
    schema_engine: SchemaEngine | None,
) -> dict[str, Any]:
    """Generate calendar view from tasks with due dates."""
    tasks = [n for n in schema_nodes if n.get("entity") == SchemaEntity.TASK.value and n.get("due_date")]
    
    # Group by date
    calendar = {}
    for task in tasks:
        due_date = task.get("due_date")
        if due_date:
            date_key = due_date.split("T")[0] if "T" in due_date else due_date.split(" ")[0]
            if date_key not in calendar:
                calendar[date_key] = []
            calendar[date_key].append({
                "id": task.get("id"),
                "title": task.get("title"),
                "status": task.get("status"),
                "priority": task.get("priority"),
            })
    
    return {
        "ok": True,
        "view": {
            "type": "calendar",
            "events": calendar,
            "total_items": len(tasks),
        },
        "explanation": "presentation_calendar",
    }


async def _generate_mindmap(
    schema_nodes: list[dict[str, Any]],
    tenant_id: str,
    space_id: str,
    schema_engine: SchemaEngine | None,
) -> dict[str, Any]:
    """Generate mind map structure from schema hierarchy."""
    # Build tree structure
    node_map = {n["id"]: {**n, "children": []} for n in schema_nodes}
    roots = []
    
    for node in schema_nodes:
        parent_id = node.get("parent_id")
        if parent_id and parent_id in node_map:
            node_map[parent_id]["children"].append(node_map[node["id"]])
        else:
            roots.append(node_map[node["id"]])
    
    return {
        "ok": True,
        "view": {
            "type": "mindmap",
            "roots": roots,
            "total_nodes": len(schema_nodes),
        },
        "explanation": "presentation_mindmap",
    }


class PresentationAgent:
    """Live views for dashboard."""

    @staticmethod
    async def run(
        tenant_id: str,
        space_id: str,
        user_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        return await _handler(tenant_id, space_id, user_id, context)


presentation_spec = AgentSpec(
    name="PresentationAgent",
    type="presentation",
    triggers=["view_request", "dashboard_refresh"],
    tools=["schema", "rag"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Generates live views: Kanban, Timeline, Calendar, Mind Map.",
    handler=_handler,
)
