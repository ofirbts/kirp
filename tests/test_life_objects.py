from __future__ import annotations

from src.core.life_objects import classify_content, extract_life_objects
from src.models.schema import SchemaEntity


def test_info_prefix_does_not_project_task() -> None:
    text = "מידע: המשתמש מעדיף לעבוד בבוקר."
    assert classify_content(text) == SchemaEntity.CATEGORY
    assert extract_life_objects(text, event_id="e1", user_id="u1", source="dashboard") == []


def test_hebrew_task_with_date_projects_task() -> None:
    text = "משימה: להגיש דוח מחר בבוקר"
    assert classify_content(text) == SchemaEntity.TASK
    out = extract_life_objects(text, event_id="e2", user_id="u1", source="dashboard")
    assert len(out) == 1
    assert out[0]["entity"] == SchemaEntity.TASK
    assert out[0]["due_date"] is not None
