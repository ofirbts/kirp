# src/compat/legacy_agents.py

"""
Compatibility layer for legacy KIRP agents.
Allows the new architecture to run even if old modules are missing.
"""

from dataclasses import dataclass
from typing import Any, Dict


# -----------------------------
#  BRAND / CONTENT ORCHESTRATOR
# -----------------------------
@dataclass
class BrandContentRequest:
    idea: str
    user_id: str | None = None
    tone: str | None = "professional"
    format: str | None = "linkedin_post"


class OrchestratorAgent:
    """
    Stub orchestrator for brand/content generation.
    The new system can replace this later with a real LLM/RAG pipeline.
    """

    async def generate(self, request: BrandContentRequest) -> Dict[str, Any]:
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
#  COMMAND EXECUTOR (LEGACY)
# -----------------------------
class CommandExecutorAgent:
    """
    Stub executor for legacy command execution.
    """

    async def process_task(self, event: dict) -> bool:
        print(f"[Executor] Received event: {event}")
        return True


command_executor_spec = {
    "name": "command_executor",
    "description": "Stub executor for legacy compatibility",
}
