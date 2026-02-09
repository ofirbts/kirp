"""
Centralized Agent Registry — Register all agents in one place.

Used by main.py, workers, and other components to ensure consistent agent registration.
"""

from __future__ import annotations

import logging
from typing import Any

from src.core.agent_framework import AgentFramework
from src.agents import (
    pattern_analyzer_spec,
    planner_spec,
    forecaster_spec,
    risk_opportunity_spec,
    schema_structure_spec,
    presentation_spec,
    self_improvement_spec,
)
from src.agents.meta_agent import meta_agent_spec
from src.agents.future_obligations import future_obligations_spec
from src.agents.reminder_agent import reminder_agent_spec
from src.core.agents.specs import PHASE5_AGENT_SPECS

logger = logging.getLogger(__name__)


def register_all_agents(agent_framework: AgentFramework) -> None:
    """
    Register all built-in agents with the framework.
    This ensures consistent registration across all components.
    """
    agents = [
        pattern_analyzer_spec,
        planner_spec,
        forecaster_spec,
        risk_opportunity_spec,
        schema_structure_spec,
        presentation_spec,
        self_improvement_spec,
        meta_agent_spec,
        future_obligations_spec,
        reminder_agent_spec,
        *PHASE5_AGENT_SPECS,
    ]
    
    for spec in agents:
        agent_framework.register(spec)
        logger.debug("Registered agent: %s", spec.name)
    
    logger.info("Registered %d agents", len(agents))


def get_agent_framework_with_all_agents() -> AgentFramework:
    """
    Create and return an AgentFramework with all agents registered.
    Convenience function for components that need a fully configured framework.
    """
    af = AgentFramework()
    register_all_agents(af)
    return af
