# src/compat/legacy_agents.py

"""
Legacy Agent Compatibility Layer — DEPRECATED

This module is kept for backward compatibility but is no longer used.
All functionality has been migrated to:
- OrchestratorAgent → PresentationAgent (brand_content view type)
- CommandExecutorAgent → MetaAgent (command routing)

This file will be removed in a future version.
"""

from dataclasses import dataclass
from typing import Any, Dict
import warnings


# -----------------------------
#  BRAND / CONTENT ORCHESTRATOR (DEPRECATED)
# -----------------------------
@dataclass
class BrandContentRequest:
    """Deprecated: Use PresentationAgent with view_type='brand_content' instead."""
    idea: str
    user_id: str | None = None
    tone: str | None = "professional"
    format: str | None = "linkedin_post"


class OrchestratorAgent:
    """
    DEPRECATED: Use PresentationAgent with view_type='brand_content' instead.
    
    This stub is kept for backward compatibility only.
    """

    async def generate(self, request: BrandContentRequest) -> Dict[str, Any]:
        warnings.warn(
            "OrchestratorAgent is deprecated. Use PresentationAgent with view_type='brand_content' instead.",
            DeprecationWarning,
            stacklevel=2
        )
        idea = request.idea.strip()
        return {
            "idea": idea,
            "headline": f"🚀 {idea}",
            "body": (
                f"{idea} is a powerful direction.\n\n"
                f"Here are 3 angles you can use:\n"
                f"1. Problem → why this matters now\n"
                f"2. Your unique approach\n"
                f"3. Clear outcomes\n"
            ),
            "tone": request.tone,
            "format": request.format,
            "user_id": request.user_id,
        }


# -----------------------------
#  COMMAND EXECUTOR (DEPRECATED)
# -----------------------------
class CommandExecutorAgent:
    """
    DEPRECATED: Use MetaAgent for command routing instead.
    
    This stub is kept for backward compatibility only.
    """

    async def process_task(self, event: dict) -> bool:
        warnings.warn(
            "CommandExecutorAgent is deprecated. Use MetaAgent for command routing instead.",
            DeprecationWarning,
            stacklevel=2
        )
        print(f"[Executor] Received event: {event}")
        return True


command_executor_spec = {
    "name": "command_executor",
    "description": "Deprecated: Use MetaAgent instead",
}
