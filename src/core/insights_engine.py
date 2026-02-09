"""
Insights Engine — Real insights from Events, Tasks, Projects, Commitments, Schedules, Life Areas.

Produces workload summaries, patterns, commitment risk, connections, and personalized
recommendations. No generic text; everything is derived from collected data.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any

from src.models.schema import SchemaEntity

logger = logging.getLogger(__name__)


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SourceEntity:
    entity: str
    id: str
    title: str | None = None


@dataclass
class Insight:
    id: str
    type: str  # workload | pattern | commitment | connection | recommendation
    category: str  # human-readable: Workload, Pattern, Commitment, Connection, Recommendation
    title: str
    body: str
    data: dict[str, Any]
    confidence: float
    source_entities: list[SourceEntity]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "category": self.category,
            "title": self.title,
            "body": self.body,
            "data": self.data,
            "confidence": self.confidence,
            "source_entities": [
                {"entity": s.entity, "id": s.id, "title": s.title} for s in self.source_entities
            ],
            "created_at": self.created_at,
        }


class InsightsEngine:
    """
    Builds insights from schema nodes (tasks, projects, commitments, life areas),
    upcoming obligations, and recent events. Recommendations feel like "someone knows me."
    """

    def __init__(self, schema_engine: Any, event_store: Any) -> None:
        self._schema = schema_engine
        self._store = event_store

    async def compute_insights(
        self,
        tenant_id: str,
        space_id: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list[Insight]:
        """
        Compute all insights for the given tenant/space. Returns sorted list (recommendations first, then by confidence).
        """
        insights: list[Insight] = []
        now = _now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        next_week = now + timedelta(days=7)

        try:
            nodes = await self._schema.list_nodes(
                tenant_id=tenant_id,
                space_id=space_id,
                limit=1000,
                use_cache=False,
            )
            obligations = await self._schema.list_upcoming_obligations(
                tenant_id=tenant_id,
                space_id=space_id,
                due_from=now,
                due_to=next_week,
                limit=200,
            )
            events: list[Any] = []
            try:
                event_list = await self._store.list(
                    tenant_id=tenant_id,
                    space_id=space_id or None,
                    user_id=user_id,
                    since=week_ago,
                    limit=500,
                )
                events = event_list
            except Exception as e:
                logger.warning("InsightsEngine: event_store.list failed: %s", e)

            tasks = [n for n in nodes if n.get("entity") == SchemaEntity.TASK.value]
            commitments = [n for n in nodes if n.get("entity") == SchemaEntity.COMMITMENT.value]
            projects = [n for n in nodes if n.get("entity") == SchemaEntity.PROJECT.value]
            life_areas = [n for n in nodes if n.get("entity") == SchemaEntity.LIFE_AREA.value]

            # --- Workload ---
            overdue_tasks = []
            today_tasks = []
            completed_this_week = []
            for t in tasks:
                due = _parse_dt(t.get("due_date"))
                status = (t.get("status") or "").lower()
                if status == "completed":
                    updated = _parse_dt(t.get("updated_at"))
                    if updated and updated >= week_ago:
                        completed_this_week.append(t)
                    continue
                if due:
                    if due < now:
                        overdue_tasks.append(t)
                    elif due.date() == today_start.date():
                        today_tasks.append(t)

            total_active = len([t for t in tasks if (t.get("status") or "").lower() != "completed"])
            insights.append(_insight_workload_summary(
                total_tasks=len(tasks),
                total_active=total_active,
                overdue_count=len(overdue_tasks),
                today_count=len(today_tasks),
                completed_this_week=len(completed_this_week),
                obligations_this_week=len(obligations),
                events_last_7_days=len(events),
            ))

            if overdue_tasks:
                insights.append(_insight_overdue(overdue_tasks))
            if today_tasks:
                insights.append(_insight_today_focus(today_tasks))

            # --- Commitments & risk ---
            commitment_insights = _insights_commitments(commitments, now)
            insights.extend(commitment_insights)

            # --- Patterns ---
            if completed_this_week:
                insights.append(_insight_completion_pattern(completed_this_week))
            if events:
                insights.append(_insight_event_activity(events, week_ago, now))

            # --- Connections ---
            tasks_with_source = [t for t in tasks if (t.get("metadata") or {}).get("source_event_id")]
            if tasks_with_source or projects:
                insights.append(_insight_connections(
                    tasks_with_events=len(tasks_with_source),
                    events_count=len(events),
                    projects_count=len(projects),
                    life_areas_count=len(life_areas),
                ))

            # --- Project progress ---
            for proj in projects[:10]:
                child_tasks = [t for t in tasks if t.get("parent_id") == proj.get("id")]
                if not child_tasks:
                    continue
                done = len([t for t in child_tasks if (t.get("status") or "").lower() == "completed"])
                pct = round(100 * done / len(child_tasks))
                if pct >= 50 or pct == 100:
                    insights.append(_insight_project_progress(proj, done, len(child_tasks), pct))

            # --- Recommendations ---
            recs = _recommendations(
                overdue_tasks=overdue_tasks,
                today_tasks=today_tasks,
                obligations=obligations,
                commitments=commitments,
                projects=projects,
                tasks=tasks,
                now=now,
            )
            insights.extend(recs)

        except Exception as e:
            logger.exception("InsightsEngine.compute_insights failed: %s", e)
            insights.append(_insight_error(str(e)))

        # Sort: recommendations first, then by confidence desc
        type_order = {"recommendation": 0, "workload": 1, "commitment": 2, "pattern": 3, "connection": 4}
        insights.sort(key=lambda i: (type_order.get(i.type, 5), -i.confidence))
        return insights[:limit]


def _insight_workload_summary(
    total_tasks: int,
    total_active: int,
    overdue_count: int,
    today_count: int,
    completed_this_week: int,
    obligations_this_week: int,
    events_last_7_days: int,
) -> Insight:
    data = {
        "total_tasks": total_tasks,
        "active_tasks": total_active,
        "overdue": overdue_count,
        "due_today": today_count,
        "completed_this_week": completed_this_week,
        "obligations_this_week": obligations_this_week,
        "events_last_7_days": events_last_7_days,
    }
    body_parts = []
    if total_active > 0:
        body_parts.append(f"{total_active} active task(s).")
    if overdue_count > 0:
        body_parts.append(f"{overdue_count} overdue.")
    if today_count > 0:
        body_parts.append(f"{today_count} due today.")
    if completed_this_week > 0:
        body_parts.append(f"You completed {completed_this_week} this week.")
    if obligations_this_week > 0:
        body_parts.append(f"{obligations_this_week} commitment(s) or task(s) due in the next 7 days.")
    if events_last_7_days > 0:
        body_parts.append(f"{events_last_7_days} events in the last 7 days.")
    body = " ".join(body_parts) if body_parts else "No task or event data yet. Add tasks and events to see workload insights."
    return Insight(
        id=str(uuid.uuid4()),
        type="workload",
        category="Workload",
        title="Workload at a glance",
        body=body,
        data=data,
        confidence=0.9,
        source_entities=[],
        created_at=_now().isoformat(),
    )


def _insight_overdue(tasks: list[dict]) -> Insight:
    titles = [t.get("title") or "Untitled" for t in tasks[:5]]
    return Insight(
        id=str(uuid.uuid4()),
        type="recommendation",
        category="Recommendation",
        title="Overdue tasks need attention",
        body=f"You have {len(tasks)} overdue task(s). Consider tackling: " + ", ".join(titles[:3]) + ("." if len(titles) <= 3 else " and others."),
        data={"count": len(tasks), "sample_titles": titles},
        confidence=0.95,
        source_entities=[SourceEntity("task", t.get("id", ""), t.get("title")) for t in tasks[:5]],
        created_at=_now().isoformat(),
    )


def _insight_today_focus(tasks: list[dict]) -> Insight:
    titles = [t.get("title") or "Untitled" for t in tasks[:5]]
    return Insight(
        id=str(uuid.uuid4()),
        type="workload",
        category="Workload",
        title="Today's focus",
        body=f"{len(tasks)} task(s) due today: " + ", ".join(titles[:3]) + ("." if len(titles) <= 3 else " and others."),
        data={"count": len(tasks), "titles": titles},
        confidence=0.9,
        source_entities=[SourceEntity("task", t.get("id", ""), t.get("title")) for t in tasks[:5]],
        created_at=_now().isoformat(),
    )


def _get_risk(due: datetime | None, status: str | None, now: datetime) -> str | None:
    if (status or "").lower() == "blocked":
        return "blocked"
    if not due:
        return None
    if due < now:
        return "late"
    days = (due - now).total_seconds() / (24 * 3600)
    if days <= 2:
        return "at_risk"
    return None


def _insights_commitments(commitments: list[dict], now: datetime) -> list[Insight]:
    out: list[Insight] = []
    late = []
    at_risk = []
    blocked = []
    for c in commitments:
        status = (c.get("status") or "").lower()
        if status == "completed":
            continue
        due = _parse_dt(c.get("due_date"))
        risk = _get_risk(due, status, now)
        if risk == "late":
            late.append(c)
        elif risk == "at_risk":
            at_risk.append(c)
        elif risk == "blocked":
            blocked.append(c)

    if late:
        out.append(Insight(
            id=str(uuid.uuid4()),
            type="commitment",
            category="Commitment",
            title="Late commitments",
            body=f"{len(late)} commitment(s) are past due: " + ", ".join((c.get("title") or "Untitled") for c in late[:3]),
            data={"count": len(late), "risk": "late"},
            confidence=0.95,
            source_entities=[SourceEntity("commitment", c.get("id", ""), c.get("title")) for c in late[:5]],
            created_at=now.isoformat(),
        ))
    if at_risk:
        out.append(Insight(
            id=str(uuid.uuid4()),
            type="commitment",
            category="Commitment",
            title="Commitments due soon",
            body=f"{len(at_risk)} commitment(s) due in the next 2 days.",
            data={"count": len(at_risk), "risk": "at_risk"},
            confidence=0.85,
            source_entities=[SourceEntity("commitment", c.get("id", ""), c.get("title")) for c in at_risk[:5]],
            created_at=now.isoformat(),
        ))
    if blocked:
        out.append(Insight(
            id=str(uuid.uuid4()),
            type="commitment",
            category="Commitment",
            title="Blocked commitments",
            body=f"{len(blocked)} commitment(s) are blocked.",
            data={"count": len(blocked), "risk": "blocked"},
            confidence=0.9,
            source_entities=[SourceEntity("commitment", c.get("id", ""), c.get("title")) for c in blocked[:5]],
            created_at=now.isoformat(),
        ))
    return out


def _insight_completion_pattern(completed_this_week: list[dict]) -> Insight:
    return Insight(
        id=str(uuid.uuid4()),
        type="pattern",
        category="Pattern",
        title="Completion momentum",
        body=f"You completed {len(completed_this_week)} task(s) this week. Keep the momentum.",
        data={"completed_this_week": len(completed_this_week)},
        confidence=0.8,
        source_entities=[],
        created_at=_now().isoformat(),
    )


def _insight_event_activity(events: list[Any], week_ago: datetime, now: datetime) -> Insight:
    count = len(events)
    return Insight(
        id=str(uuid.uuid4()),
        type="pattern",
        category="Pattern",
        title="Recent activity",
        body=f"{count} event(s) in the last 7 days — your knowledge base is growing.",
        data={"events_last_7_days": count},
        confidence=0.75,
        source_entities=[],
        created_at=now.isoformat(),
    )


def _insight_connections(
    tasks_with_events: int,
    events_count: int,
    projects_count: int,
    life_areas_count: int,
) -> Insight:
    parts = []
    if tasks_with_events > 0:
        parts.append(f"{tasks_with_events} task(s) linked to events")
    if projects_count > 0:
        parts.append(f"{projects_count} project(s)")
    if life_areas_count > 0:
        parts.append(f"{life_areas_count} life area(s)")
    body = "Connections: " + ", ".join(parts) + "." if parts else "Events, tasks, and projects are connected."
    return Insight(
        id=str(uuid.uuid4()),
        type="connection",
        category="Connection",
        title="Your second brain structure",
        body=body,
        data={
            "tasks_linked_to_events": tasks_with_events,
            "events": events_count,
            "projects": projects_count,
            "life_areas": life_areas_count,
        },
        confidence=0.85,
        source_entities=[],
        created_at=_now().isoformat(),
    )


def _insight_project_progress(proj: dict, done: int, total: int, pct: int) -> Insight:
    title = proj.get("title") or "Project"
    if pct == 100:
        body = f"'{title}' is complete. All {total} tasks done."
    else:
        body = f"'{title}' is {pct}% complete ({done}/{total} tasks)."
    return Insight(
        id=str(uuid.uuid4()),
        type="pattern",
        category="Pattern",
        title=f"Project: {title}",
        body=body,
        data={"project_id": proj.get("id"), "done": done, "total": total, "pct": pct},
        confidence=0.85,
        source_entities=[SourceEntity("project", proj.get("id", ""), title)],
        created_at=_now().isoformat(),
    )


def _recommendations(
    overdue_tasks: list[dict],
    today_tasks: list[dict],
    obligations: list[dict],
    commitments: list[dict],
    projects: list[dict],
    tasks: list[dict],
    now: datetime,
) -> list[Insight]:
    recs: list[Insight] = []
    if overdue_tasks and not any(r.type == "recommendation" and "overdue" in r.body.lower() for r in recs):
        top = overdue_tasks[0]
        recs.append(Insight(
            id=str(uuid.uuid4()),
            type="recommendation",
            category="Recommendation",
            title="Start here",
            body=f"Tackle '{top.get('title') or 'Untitled'}' first — it's overdue.",
            data={"task_id": top.get("id")},
            confidence=0.95,
            source_entities=[SourceEntity("task", top.get("id", ""), top.get("title"))],
            created_at=now.isoformat(),
        ))
    if obligations and len(obligations) >= 3:
        recs.append(Insight(
            id=str(uuid.uuid4()),
            type="recommendation",
            category="Recommendation",
            title="Upcoming load",
            body=f"You have {len(obligations)} items due in the next 7 days. Consider planning your week.",
            data={"obligations_count": len(obligations)},
            confidence=0.85,
            source_entities=[],
            created_at=now.isoformat(),
        ))
    active_projects = [p for p in projects if any(
        (t.get("status") or "").lower() != "completed"
        for t in tasks if t.get("parent_id") == p.get("id")
    )]
    if len(active_projects) > 3:
        recs.append(Insight(
            id=str(uuid.uuid4()),
            type="recommendation",
            category="Recommendation",
            title="Focus areas",
            body=f"You have {len(active_projects)} active project(s). Consider focusing on one or two to reduce context-switching.",
            data={"active_projects": len(active_projects)},
            confidence=0.75,
            source_entities=[],
            created_at=now.isoformat(),
        ))
    return recs


def _insight_error(message: str) -> Insight:
    return Insight(
        id=str(uuid.uuid4()),
        type="workload",
        category="Workload",
        title="Insights temporarily unavailable",
        body=message,
        data={"error": message},
        confidence=0.0,
        source_entities=[],
        created_at=_now().isoformat(),
    )
