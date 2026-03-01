"""
M3 IdentityOS — Memory schemas and store interface.

Collections (spec 6.1): identity_profiles, reflection_entries, micro_actions,
weekly_synthesis, monthly_evolution. All tenant_id + user_id scoped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


# --- Document schemas (spec 6.1) ---

@dataclass
class IdentityProfile:
    """identity_profiles: user identity vector and pillar state."""
    user_id: str
    tenant_id: str
    space_id: str
    identity_vector: list[float] = field(default_factory=list)
    pillar_scores: dict[str, float] = field(default_factory=dict)
    ideal_self_vector: list[float] | None = None
    updated_at: datetime | None = None
    source_event_id: str | None = None


@dataclass
class ReflectionEntry:
    """reflection_entries: daily reflection per user."""
    user_id: str
    tenant_id: str
    space_id: str
    reflection_date: str  # ISO date or YYYY-MM-DD
    reflection_text: str
    pillar_scores: dict[str, float] = field(default_factory=dict)
    mood: str = ""
    embedding: list[float] = field(default_factory=list)
    source_event_id: str | None = None
    created_at: datetime | None = None
    id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class MicroAction:
    """micro_actions: single micro-action with status."""
    action_id: str
    user_id: str
    tenant_id: str
    space_id: str
    title: str
    pillar: str = ""
    status: str = "pending"  # pending | completed | snoozed
    due_by: str | None = None  # ISO8601
    roi_score: float = 0.0
    source_event_id: str | None = None
    completed_at: str | None = None
    feedback: str = ""


@dataclass
class WeeklySynthesis:
    """weekly_synthesis: week summary and trends."""
    synthesis_id: str
    user_id: str
    tenant_id: str
    space_id: str
    week_start: str  # YYYY-MM-DD
    week_end: str
    summary: str
    pillar_trends: dict[str, Any] = field(default_factory=dict)
    insights: list[str] = field(default_factory=list)
    source_event_id: str | None = None
    created_at: datetime | None = None


@dataclass
class MonthlyEvolution:
    """monthly_evolution: monthly identity trajectory."""
    evolution_id: str
    user_id: str
    tenant_id: str
    space_id: str
    month: str  # YYYY-MM
    trajectory: list[dict[str, Any]] = field(default_factory=list)
    new_goals: list[str] = field(default_factory=list)
    pillar_shifts: dict[str, Any] = field(default_factory=dict)
    source_event_id: str | None = None
    created_at: datetime | None = None


# --- Store interface (tenant/user scoped; audit via source_event_id) ---

class M3MemoryStore:
    """
    M3 Typed Memory: identity_profiles, reflection_entries, micro_actions,
    weekly_synthesis, monthly_evolution. All access filtered by tenant_id and user_id.
    Default implementation is stub (in-memory / no-op); wire to Qdrant/Schema later.
    """

    def __init__(self) -> None:
        self._reflections: list[dict[str, Any]] = []
        self._micro_actions: list[dict[str, Any]] = []
        self._syntheses: list[dict[str, Any]] = []
        self._evolutions: list[dict[str, Any]] = []
        self._profiles: dict[tuple[str, str], dict[str, Any]] = {}

    async def connect(self) -> None:
        """Optional: connect to backing store."""
        pass

    # Identity profiles (one per user or overwrite)
    async def get_identity_profile(self, tenant_id: str, user_id: str) -> IdentityProfile | None:
        key = (tenant_id, user_id)
        raw = self._profiles.get(key)
        if not raw:
            return None
        return IdentityProfile(
            user_id=raw["user_id"],
            tenant_id=raw["tenant_id"],
            space_id=raw["space_id"],
            identity_vector=raw.get("identity_vector", []),
            pillar_scores=raw.get("pillar_scores", {}),
            ideal_self_vector=raw.get("ideal_self_vector"),
            updated_at=raw.get("updated_at"),
            source_event_id=raw.get("source_event_id"),
        )

    async def upsert_identity_profile(
        self,
        tenant_id: str,
        user_id: str,
        space_id: str,
        identity_vector: list[float],
        pillar_scores: dict[str, float],
        source_event_id: str | None = None,
        ideal_self_vector: list[float] | None = None,
    ) -> None:
        from datetime import datetime, timezone
        key = (tenant_id, user_id)
        self._profiles[key] = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "space_id": space_id,
            "identity_vector": identity_vector,
            "pillar_scores": pillar_scores,
            "ideal_self_vector": ideal_self_vector,
            "updated_at": datetime.now(timezone.utc),
            "source_event_id": source_event_id,
        }

    # Reflection entries
    async def list_reflections(
        self,
        tenant_id: str,
        user_id: str,
        limit: int = 50,
        before_date: str | None = None,
    ) -> list[ReflectionEntry]:
        filtered = [
            r for r in self._reflections
            if r.get("tenant_id") == tenant_id and r.get("user_id") == user_id
        ]
        if before_date:
            filtered = [r for r in filtered if (r.get("reflection_date") or "") <= before_date]
        filtered.sort(key=lambda r: r.get("reflection_date") or "", reverse=True)
        out = []
        for r in filtered[:limit]:
            out.append(ReflectionEntry(
                user_id=r["user_id"],
                tenant_id=r["tenant_id"],
                space_id=r["space_id"],
                reflection_date=r.get("reflection_date", ""),
                reflection_text=r.get("reflection_text", ""),
                pillar_scores=r.get("pillar_scores", {}),
                mood=r.get("mood", ""),
                embedding=r.get("embedding", []),
                source_event_id=r.get("source_event_id"),
                created_at=r.get("created_at"),
                id=r.get("id", str(uuid4())),
            ))
        return out

    async def append_reflection(
        self,
        tenant_id: str,
        user_id: str,
        space_id: str,
        reflection_date: str,
        reflection_text: str,
        pillar_scores: dict[str, float] | None = None,
        mood: str = "",
        source_event_id: str | None = None,
        embedding: list[float] | None = None,
    ) -> ReflectionEntry:
        from datetime import datetime, timezone
        entry = {
            "id": str(uuid4()),
            "user_id": user_id,
            "tenant_id": tenant_id,
            "space_id": space_id,
            "reflection_date": reflection_date,
            "reflection_text": reflection_text,
            "pillar_scores": pillar_scores or {},
            "mood": mood,
            "embedding": embedding or [],
            "source_event_id": source_event_id,
            "created_at": datetime.now(timezone.utc),
        }
        self._reflections.append(entry)
        return ReflectionEntry(
            user_id=entry["user_id"],
            tenant_id=entry["tenant_id"],
            space_id=entry["space_id"],
            reflection_date=entry["reflection_date"],
            reflection_text=entry["reflection_text"],
            pillar_scores=entry["pillar_scores"],
            mood=entry["mood"],
            embedding=entry["embedding"],
            source_event_id=entry["source_event_id"],
            created_at=entry["created_at"],
            id=entry["id"],
        )

    # Micro actions
    async def list_micro_actions(
        self,
        tenant_id: str,
        user_id: str,
        status: str | None = None,
        limit: int = 100,
    ) -> list[MicroAction]:
        filtered = [
            a for a in self._micro_actions
            if a.get("tenant_id") == tenant_id and a.get("user_id") == user_id
        ]
        if status:
            filtered = [a for a in filtered if a.get("status") == status]
        out = []
        for a in filtered[:limit]:
            out.append(MicroAction(
                action_id=a.get("action_id", ""),
                user_id=a["user_id"],
                tenant_id=a["tenant_id"],
                space_id=a["space_id"],
                title=a.get("title", ""),
                pillar=a.get("pillar", ""),
                status=a.get("status", "pending"),
                due_by=a.get("due_by"),
                roi_score=float(a.get("roi_score", 0)),
                source_event_id=a.get("source_event_id"),
                completed_at=a.get("completed_at"),
                feedback=a.get("feedback", ""),
            ))
        return out

    async def upsert_micro_action(
        self,
        tenant_id: str,
        user_id: str,
        space_id: str,
        action_id: str,
        title: str,
        pillar: str = "",
        status: str = "pending",
        due_by: str | None = None,
        roi_score: float = 0.0,
        source_event_id: str | None = None,
        completed_at: str | None = None,
        feedback: str = "",
    ) -> None:
        existing = [a for a in self._micro_actions if a.get("action_id") == action_id]
        if existing:
            idx = self._micro_actions.index(existing[0])
            self._micro_actions[idx] = {
                "action_id": action_id,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "space_id": space_id,
                "title": title,
                "pillar": pillar,
                "status": status,
                "due_by": due_by,
                "roi_score": roi_score,
                "source_event_id": source_event_id,
                "completed_at": completed_at,
                "feedback": feedback,
            }
        else:
            self._micro_actions.append({
                "action_id": action_id,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "space_id": space_id,
                "title": title,
                "pillar": pillar,
                "status": status,
                "due_by": due_by,
                "roi_score": roi_score,
                "source_event_id": source_event_id,
                "completed_at": completed_at,
                "feedback": feedback,
            })

    # Weekly synthesis
    async def list_weekly_syntheses(
        self,
        tenant_id: str,
        user_id: str,
        limit: int = 24,
    ) -> list[WeeklySynthesis]:
        filtered = [
            s for s in self._syntheses
            if s.get("tenant_id") == tenant_id and s.get("user_id") == user_id
        ]
        filtered.sort(key=lambda s: s.get("week_start") or "", reverse=True)
        return [
            WeeklySynthesis(
                synthesis_id=s.get("synthesis_id", ""),
                user_id=s["user_id"],
                tenant_id=s["tenant_id"],
                space_id=s["space_id"],
                week_start=s.get("week_start", ""),
                week_end=s.get("week_end", ""),
                summary=s.get("summary", ""),
                pillar_trends=s.get("pillar_trends", {}),
                insights=s.get("insights", []),
                source_event_id=s.get("source_event_id"),
                created_at=s.get("created_at"),
            )
            for s in filtered[:limit]
        ]

    async def append_weekly_synthesis(
        self,
        tenant_id: str,
        user_id: str,
        space_id: str,
        synthesis_id: str,
        week_start: str,
        week_end: str,
        summary: str,
        pillar_trends: dict[str, Any] | None = None,
        insights: list[str] | None = None,
        source_event_id: str | None = None,
    ) -> None:
        from datetime import datetime, timezone
        self._syntheses.append({
            "synthesis_id": synthesis_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "space_id": space_id,
            "week_start": week_start,
            "week_end": week_end,
            "summary": summary,
            "pillar_trends": pillar_trends or {},
            "insights": insights or [],
            "source_event_id": source_event_id,
            "created_at": datetime.now(timezone.utc),
        })

    # Monthly evolution
    async def list_monthly_evolutions(
        self,
        tenant_id: str,
        user_id: str,
        limit: int = 12,
    ) -> list[MonthlyEvolution]:
        filtered = [
            e for e in self._evolutions
            if e.get("tenant_id") == tenant_id and e.get("user_id") == user_id
        ]
        filtered.sort(key=lambda e: e.get("month") or "", reverse=True)
        return [
            MonthlyEvolution(
                evolution_id=e.get("evolution_id", ""),
                user_id=e["user_id"],
                tenant_id=e["tenant_id"],
                space_id=e["space_id"],
                month=e.get("month", ""),
                trajectory=e.get("trajectory", []),
                new_goals=e.get("new_goals", []),
                pillar_shifts=e.get("pillar_shifts", {}),
                source_event_id=e.get("source_event_id"),
                created_at=e.get("created_at"),
            )
            for e in filtered[:limit]
        ]

    async def append_monthly_evolution(
        self,
        tenant_id: str,
        user_id: str,
        space_id: str,
        evolution_id: str,
        month: str,
        trajectory: list[dict[str, Any]],
        new_goals: list[str] | None = None,
        pillar_shifts: dict[str, Any] | None = None,
        source_event_id: str | None = None,
    ) -> None:
        from datetime import datetime, timezone
        self._evolutions.append({
            "evolution_id": evolution_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "space_id": space_id,
            "month": month,
            "trajectory": trajectory,
            "new_goals": new_goals or [],
            "pillar_shifts": pillar_shifts or {},
            "source_event_id": source_event_id,
            "created_at": datetime.now(timezone.utc),
        })


# Singleton for use by agents and API (can be replaced with a store that uses Qdrant/Schema)
_m3_store: M3MemoryStore | None = None


def get_m3_memory_store() -> M3MemoryStore:
    """Return the shared M3 memory store (stub by default)."""
    global _m3_store
    if _m3_store is None:
        _m3_store = M3MemoryStore()
    return _m3_store
