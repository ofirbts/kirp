from pydantic import BaseModel
from typing import Dict, Any, Optional

class ToolDecision(BaseModel):
    tool: str
    allowed: bool
    reason: str
    estimated_cost: float
    requires_human: bool

class ToolPolicy:
    def __init__(self):
        # הגדרות קשיחות לכלים (Hard Rules)
        self.registry_rules = {
            "calc": {"cost": 0.001, "requires_approval": False},
            "search": {"cost": 0.01, "requires_approval": False},
            "create_notion_tasks": {"cost": 0.05, "requires_approval": True}
        }

    def evaluate(self, tool_name: str, context: Dict[str, Any]) -> ToolDecision:
        rule = self.registry_rules.get(tool_name)
        
        if not rule:
            return ToolDecision(
                tool=tool_name,
                allowed=False,
                reason=f"Tool '{tool_name}' is not registered in policy.",
                estimated_cost=0.0,
                requires_human=False
            )

        # לוגיקה פשוטה: אם הכלי יקר או רגיש (כמו Notion), נדרוש אישור אדם
        return ToolDecision(
            tool=tool_name,
            allowed=True,
            reason="Policy check passed",
            estimated_cost=rule["cost"],
            requires_human=rule["requires_approval"]
        )

tool_policy = ToolPolicy()