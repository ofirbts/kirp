"""
Life Objects extraction — Task, Project, Commitment, LifeArea from event content.

Used by EventPipeline after ingest. Classification + NLP date extraction → SchemaEngine.upsert_node.
"""

from __future__ import annotations

import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from src.models.schema import SchemaEntity, LIFE_AREA_NAMES

logger = logging.getLogger(__name__)

# ----- Explicit date patterns (ISO, due 2025-02-15, by Feb 15, etc.) -----
_DATE_PATTERNS = [
    (re.compile(r"(?:due|by|until)\s+(\d{4}-\d{2}-\d{2})", re.I), "%Y-%m-%d"),
    (re.compile(r"(?:due|by)\s+(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", re.I), None),
    (re.compile(r"(\d{4}-\d{2}-\d{2})"), "%Y-%m-%d"),
    (re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})"), None),
]

# ----- Relative / NLP date patterns -----
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _rel_tomorrow_morning(d: datetime) -> datetime:
    return (d + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)


def _rel_tomorrow_evening(d: datetime) -> datetime:
    return (d + timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)


def _rel_tomorrow(d: datetime) -> datetime:
    return (d + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)


def _rel_next_week(d: datetime) -> datetime:
    return (d + timedelta(days=7)).replace(hour=12, minute=0, second=0, microsecond=0)


def _rel_next_month(d: datetime) -> datetime:
    return (d.replace(day=1) + timedelta(days=32)).replace(day=1, hour=12, minute=0, second=0, microsecond=0)


def _rel_in_days(m: re.Match, d: datetime) -> datetime:
    return (d + timedelta(days=int(m.group(1)))).replace(hour=12, minute=0, second=0, microsecond=0)


def _rel_in_weeks(m: re.Match, d: datetime) -> datetime:
    return (d + timedelta(weeks=int(m.group(1)))).replace(hour=12, minute=0, second=0, microsecond=0)


_RELATIVE_ONE_ARG = [
    (re.compile(r"\btomorrow\s+morning\b", re.I), _rel_tomorrow_morning),
    (re.compile(r"\btomorrow\s+evening\b", re.I), _rel_tomorrow_evening),
    (re.compile(r"\btomorrow\b", re.I), _rel_tomorrow),
    (re.compile(r"\btoday\s+evening\b", re.I), lambda d: d.replace(hour=18, minute=0, second=0, microsecond=0)),
    (re.compile(r"\bnext\s+week\b", re.I), _rel_next_week),
    (re.compile(r"\bnext\s+month\b", re.I), _rel_next_month),
]
_RELATIVE_TWO_ARG = [
    (re.compile(r"\bin\s+(\d+)\s+days?\b", re.I), _rel_in_days),
    (re.compile(r"\bin\s+(\d+)\s+weeks?\b", re.I), _rel_in_weeks),
]
for i, day in enumerate(_WEEKDAYS):
    _RELATIVE_ONE_ARG.append((re.compile(rf"\bnext\s+{day}\s+evening\b", re.I), lambda d, wd=i: _next_weekday(d, wd, hour=18)))
    _RELATIVE_ONE_ARG.append((re.compile(rf"\bnext\s+{day}\b", re.I), lambda d, wd=i: _next_weekday(d, wd, hour=12)))


def _next_weekday(base: datetime, weekday: int, hour: int = 12) -> datetime:
    """Next occurrence of weekday (0=Monday .. 6=Sunday)."""
    days_ahead = (weekday - base.weekday() + 7) % 7
    if days_ahead == 0:
        days_ahead = 7
    d = base + timedelta(days=days_ahead)
    return d.replace(hour=hour, minute=0, second=0, microsecond=0)


def parse_due_date(text: str, base_date: datetime | None = None) -> datetime | None:
    """
    Extract a due date from text: explicit (ISO, due 2025-02-15) and NLP relative
    ("tomorrow morning", "next Tuesday evening", "in 2 days", etc.).
    Returns timezone-aware UTC datetime or None.
    """
    if not text or not text.strip():
        return None
    base = base_date or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)

    # 1) Try relative / NLP patterns first (two-arg: need match)
    # Hebrew: מחר בבוקר, מחר בערב, שבוע הבא, יום שלישי בערב (Sunday=6, Mon=0, Tue=1, ..., Sat=5)
    _hebrew_weekdays_py = {"ראשון": 6, "שני": 0, "שלישי": 1, "רביעי": 2, "חמישי": 3, "שישי": 4, "שבת": 5}
    _hebrew_phrases = [("מחר בבוקר", _rel_tomorrow_morning), ("מחר בערב", _rel_tomorrow_evening), ("מחר", _rel_tomorrow), ("שבוע הבא", _rel_next_week), ("בשבוע הבא", _rel_next_week)]
    for phrase, fn in _hebrew_phrases:
        if phrase in text:
            try:
                dt = fn(base)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
    for day_hebrew, wd in _hebrew_weekdays_py.items():
        if f"יום {day_hebrew} בערב" in text:
            try:
                dt = _next_weekday(base, wd, hour=18)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
        if f"יום {day_hebrew}" in text:
            try:
                dt = _next_weekday(base, wd, hour=12)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
    for pattern, fn in _RELATIVE_TWO_ARG:
        m = pattern.search(text)
        if m:
            try:
                dt = fn(m, base)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
    for pattern, fn in _RELATIVE_ONE_ARG:
        m = pattern.search(text)
        if m:
            try:
                dt = fn(base)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass

    # 2) Explicit date patterns
    for pattern, fmt in _DATE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        try:
            if fmt == "%Y-%m-%d":
                dt = datetime.strptime(m.group(1), fmt)
            elif fmt is None and len(m.groups()) == 3:
                g1, g2, g3 = m.groups()
                if len(g3) == 4:
                    y = int(g3)
                    a, b = int(g1), int(g2)
                    if a > 12:
                        d, mo = a, b
                    elif b > 12:
                        mo, d = a, b
                    else:
                        mo, d = a, b
                    dt = datetime(y, mo, d)
                else:
                    continue
            else:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            continue
    return None


def classify_content(content: str) -> SchemaEntity:
    """
    Classify event content into Task, Project, Commitment, LifeArea, or default Task.
    Rule-based; can be extended with an LLM classification agent later.
    """
    if not content or not content.strip():
        return SchemaEntity.TASK
    lower = content.strip().lower()

    # Commitment: promises, meetings, deadlines, "have to", "need to", "promised", "meeting with"
    commitment_marks = [
        "promised", "commitment", "committed", "meeting with", "call with",
        "have to", "need to", "must ", "should ", "deadline", "appointment",
        "scheduled", "rsvp", "confirm", "attend", "meeting at", "call at",
    ]
    if any(m in lower for m in commitment_marks):
        return SchemaEntity.COMMITMENT

    # Project: multi-step, "project", "launch", "build", "plan for"
    project_marks = ["project:", "project -", "launch ", "build ", "plan for", "roadmap", "milestone"]
    if any(m in lower for m in project_marks):
        return SchemaEntity.PROJECT

    # Life area: explicit domain (work, family, health, learning)
    for area in LIFE_AREA_NAMES:
        if area.lower() in lower or f"#{area.lower()}" in lower:
            return SchemaEntity.LIFE_AREA

    # Default: actionable item as Task
    return SchemaEntity.TASK


def extract_life_objects(
    content: str,
    event_id: str | None = None,
    user_id: str | None = None,
    source: str | None = None,
) -> list[dict[str, Any]]:
    """
    Extract Life Objects from event content: classification + NLP date + title.
    Returns list of dicts: entity, title, due_date, context, and for Commitment: owner, source_event_id in metadata.
    Every non-empty content yields at least one object (Task by default).
    """
    if not content or not content.strip():
        return []
    objects: list[dict[str, Any]] = []
    due = parse_due_date(content)
    first_line = content.strip().split("\n")[0].strip() if "\n" in content else content.strip()
    title = (first_line[:500] + "…") if len(first_line) > 500 else first_line
    if not title:
        title = "(no title)"

    entity = classify_content(content)
    meta: dict[str, Any] = {}
    if event_id:
        meta["source_event_id"] = event_id
    if user_id:
        meta["owner"] = user_id
    if source:
        meta["source"] = source

    # Commitment: ensure due_date and owner for obligations
    if entity == SchemaEntity.COMMITMENT:
        meta["source_event_id"] = meta.get("source_event_id") or ""
        meta["owner"] = meta.get("owner") or "unknown"

    # If content mentions a canonical Life Area, record it in metadata (canonical nodes created by ensure_life_areas)
    lower = content.lower()
    for area in LIFE_AREA_NAMES:
        if area.lower() in lower:
            meta["life_area"] = area
            break

    objects.append({
        "entity": entity,
        "title": title,
        "due_date": due,
        "context": content[:2000] if len(content) > 2000 else (content or None),
        "metadata": meta,
    })
    return objects
