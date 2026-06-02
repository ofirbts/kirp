"""
BaseAgent — Unified agent interface for Agents 2.0.

Fields: name, description, triggers (time-based, event-based).
run(tenant_id, space_id) returns list of actions and/or insights.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents. run() returns actions and insights."""

    name: str = ""
    description: str = ""
    triggers: list[str] = []  # e.g. "scheduled", "manual", "new_event", "new_task"

    @abstractmethod
    async def run(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str = "system",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run the agent. Returns dict with:
        - actions: list of action docs (agent, type, payload) for ExecutionAgent
        - insights: list of insight dicts (title, body, data)
        - ok: bool
        - error: optional str
        """
        pass

    def log_success(self, message: str, **kwargs: Any) -> None:
        logger.info("Agent %s: %s %s", self.name, message, kwargs)

    def log_error(self, message: str, exc: Exception | None = None, **kwargs: Any) -> None:
        logger.warning("Agent %s: %s %s %s", self.name, message, kwargs, exc)
