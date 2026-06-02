"""
Brand memory — ContentMemory, LessonsMemory. Append-only, queryable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# In-memory stubs (replace with file/DB later)
_content: list[dict[str, Any]] = []
_lessons: list[dict[str, Any]] = []


@dataclass
class ContentMemory:
    date: str
    topic: str
    type: str
    hook: str
    content: str
    engagement_metrics: dict[str, Any] | None = None
    emotional_feedback: str | None = None

    def save(self) -> None:
        _content.append({
            "date": self.date,
            "topic": self.topic,
            "type": self.type,
            "hook": self.hook,
            "content": self.content,
        })


@dataclass
class LessonsMemory:
    what_worked: str
    what_failed: str
    hypothesis: str

    def save(self) -> None:
        _lessons.append({
            "what_worked": self.what_worked,
            "what_failed": self.what_failed,
            "hypothesis": self.hypothesis,
        })


def get_memory() -> tuple[list[ContentMemory], list[LessonsMemory]]:
    content = [ContentMemory(**c) for c in _content[-20:]]
    lessons = [LessonsMemory(**l) for l in _lessons[-10:]]
    return content, lessons
