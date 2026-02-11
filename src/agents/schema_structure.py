"""
Schema Structure Agent — Builds schemas: tasks, projects, life areas, categories.

Uses LLM to extract structured entities from events and RAG context.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from datetime import datetime, timezone

from src.core.agent_framework import AgentSpec, AutonomyLevel
from src.core.schema_engine import SchemaEngine, SchemaEntity
from src.core.llm_router import get_llm_for_task

logger = logging.getLogger(__name__)


async def _handler(
    tenant_id: str,
    space_id: str,
    user_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """
    Extract and upsert schema nodes from RAG + events using LLM.
    """
    rag = context.get("rag_response")
    schema_engine: SchemaEngine | None = context.get("schema_engine")
    events = context.get("events", [])
    
    if not schema_engine:
        return {"ok": False, "error": "missing_schema_engine"}
    
    # Build context text
    context_text = ""
    if rag and hasattr(rag, "context_text"):
        context_text = rag.context_text
    elif rag:
        context_text = str(rag)
    
    # Add recent events
    if events:
        event_texts = [f"- [{e.source}] {e.content[:200]}" for e in events[:10]]
        context_text += "\n\nRecent Events:\n" + "\n".join(event_texts)
    
    if not context_text.strip():
        return {"ok": True, "nodes_upserted": 0, "message": "No context to extract from"}
    
    # LLM extraction prompt
    prompt = f"""
Analyze the following context and extract structured entities:

Context:
{context_text[:4000]}

Extract:
1. TASKS: Individual actionable items with status (pending, in_progress, completed, blocked) and priority (low, medium, high, critical)
2. PROJECTS: Collections of related tasks
3. LIFE_AREAS: High-level life domains (work, health, relationships, etc.)
4. CATEGORIES: Organizational groupings

For each entity, identify:
- Title (required)
- Description (if available)
- Status (for tasks: pending, in_progress, completed, blocked)
- Priority (for tasks: low, medium, high, critical)
- Parent relationship (e.g., task belongs to project, project belongs to life_area)
- Due date (if mentioned)

Return JSON in this format:
{{
  "tasks": [
    {{
      "title": "Task title",
      "description": "Optional description",
      "status": "pending|in_progress|completed|blocked",
      "priority": "low|medium|high|critical",
      "parent_title": "Project or Life Area name (if applicable)",
      "due_date": "YYYY-MM-DD (if mentioned)"
    }}
  ],
  "projects": [
    {{
      "title": "Project name",
      "description": "Optional description",
      "parent_title": "Life Area name (if applicable)"
    }}
  ],
  "life_areas": [
    {{
      "title": "Life area name",
      "description": "Optional description"
    }}
  ],
  "categories": [
    {{
      "title": "Category name",
      "description": "Optional description"
    }}
  ]
}}

Only extract entities that are clearly mentioned. Be conservative - quality over quantity.
"""
    
    try:
        # Schema extraction / enrichment → bulk provider.
        llm = get_llm_for_task("bulk")
        response = await llm.invoke(prompt, temperature=0.3, max_tokens=2000)
        
        # Parse JSON response
        try:
            # Extract JSON from response (may have markdown code blocks)
            response_text = response.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse LLM response as JSON: %s. Response: %s", e, response[:200])
            return {"ok": True, "nodes_upserted": 0, "error": "json_parse_failed", "raw_response": response[:500]}
        
        # Build parent mapping (title -> id)
        parent_map: dict[str, str] = {}
        nodes_created = 0
        
        # Process life_areas first (no parents)
        for life_area in data.get("life_areas", []):
            title = life_area.get("title", "").strip()
            if not title:
                continue
            node_id = await schema_engine.upsert_node(
                tenant_id=tenant_id,
                space_id=space_id,
                entity=SchemaEntity.LIFE_AREA,
                title=title,
                description=life_area.get("description"),
                metadata={"extracted_by": "SchemaStructureAgent", "user_id": user_id},
            )
            parent_map[title.lower()] = node_id
            nodes_created += 1
        
        # Process projects (may have life_area parent)
        for project in data.get("projects", []):
            title = project.get("title", "").strip()
            if not title:
                continue
            parent_id = None
            parent_title = project.get("parent_title", "").strip().lower()
            if parent_title in parent_map:
                parent_id = parent_map[parent_title]
            
            node_id = await schema_engine.upsert_node(
                tenant_id=tenant_id,
                space_id=space_id,
                entity=SchemaEntity.PROJECT,
                title=title,
                description=project.get("description"),
                parent_id=parent_id,
                metadata={"extracted_by": "SchemaStructureAgent", "user_id": user_id},
            )
            parent_map[title.lower()] = node_id
            nodes_created += 1
        
        # Process tasks (may have project or life_area parent)
        for task in data.get("tasks", []):
            title = task.get("title", "").strip()
            if not title:
                continue
            parent_id = None
            parent_title = task.get("parent_title", "").strip().lower()
            if parent_title in parent_map:
                parent_id = parent_map[parent_title]
            
            # Parse due date
            due_date = None
            due_str = task.get("due_date")
            if due_str:
                try:
                    due_date = datetime.fromisoformat(due_str.replace("Z", "+00:00"))
                except Exception:
                    pass
            
            await schema_engine.upsert_node(
                tenant_id=tenant_id,
                space_id=space_id,
                entity=SchemaEntity.TASK,
                title=title,
                description=task.get("description"),
                parent_id=parent_id,
                status=task.get("status", "pending"),
                priority=task.get("priority", "medium"),
                due_date=due_date,
                metadata={"extracted_by": "SchemaStructureAgent", "user_id": user_id},
            )
            nodes_created += 1
        
        # Process categories
        for category in data.get("categories", []):
            title = category.get("title", "").strip()
            if not title:
                continue
            await schema_engine.upsert_node(
                tenant_id=tenant_id,
                space_id=space_id,
                entity=SchemaEntity.CATEGORY,
                title=title,
                description=category.get("description"),
                metadata={"extracted_by": "SchemaStructureAgent", "user_id": user_id},
            )
            nodes_created += 1
        
        logger.info("SchemaStructureAgent extracted %d nodes from context", nodes_created)
        return {
            "ok": True,
            "nodes_upserted": nodes_created,
            "breakdown": {
                "life_areas": len(data.get("life_areas", [])),
                "projects": len(data.get("projects", [])),
                "tasks": len(data.get("tasks", [])),
                "categories": len(data.get("categories", [])),
            },
            "explanation": "schema_structure_llm_extraction",
        }
    except Exception as e:
        logger.exception("SchemaStructureAgent failed: %s", e)
        return {"ok": False, "error": str(e)}


class SchemaStructureAgent:
    """Builds and maintains schemas from events."""

    @staticmethod
    async def run(
        tenant_id: str,
        space_id: str,
        user_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        return await _handler(tenant_id, space_id, user_id, context)


schema_structure_spec = AgentSpec(
    name="SchemaStructureAgent",
    type="schema",
    triggers=["ingest", "schema_refresh"],
    tools=["rag", "schema", "llm"],
    autonomy=AutonomyLevel.FULL,
    tenant_scopes=[],
    description="Builds schemas: tasks, projects, life areas, categories.",
    handler=_handler,
)
