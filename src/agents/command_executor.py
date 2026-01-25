# src/agents/command_executor.py

from typing import Optional


class CommandExecutorAgent:
    """
    Modernized executor agent for KIRP.
    Executes approved events into concrete actions (e.g., creating tasks in Notion).
    """

    async def process_task(self, event: dict) -> bool:
        """
        Processes a single approved event.

        Expected event structure:
        {
            "id": "...",
            "status": "approved",
            "data": {
                "task": "Some task title"
            },
            "user_id": "..."
        }
        """

        if not event:
            return False

        if event.get("status") != "approved":
            return False

        title = event.get("data", {}).get("task", "Untitled Task")

        # Placeholder for actual execution logic (Notion, etc.)
        print(f"[CommandExecutor] Executing task: {title} (event_id={event['id']})")

        return True


# Spec used by meta-agent / agent registry
command_executor_spec = {
    "name": "command_executor",
    "description": "Executes approved commands (e.g., creating tasks)",
    "capabilities": ["task_execution", "event_processing"],
}
