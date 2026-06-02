"""
Built-in Agents — Pattern, Planner, Forecaster, Risk/Opportunity, Schema, Presentation, Self-Improvement.
Plus: Scraper, KafkaEvent, Metrics.

Each agent has an AgentSpec and optional handler for the framework.
"""

from src.agents.pattern_analyzer import PatternAnalyzerAgent, pattern_analyzer_spec
from src.agents.planner import TodayTomorrowPlannerAgent, planner_spec
from src.agents.forecaster import ForecasterAgent, forecaster_spec
from src.agents.risk_opportunity import RiskOpportunityAgent, risk_opportunity_spec
from src.agents.schema_structure import SchemaStructureAgent, schema_structure_spec
from src.agents.presentation import PresentationAgent, presentation_spec
from src.agents.self_improvement import SelfImprovementAgent, self_improvement_spec
from src.agents.scraper_agent import ScraperAgent, ScraperTask
from src.agents.kafka_event_agent import KafkaEventAgent, EventEnvelope
from src.agents.metrics_agent import MetricsAgent, MetricRecord
from src.agents.meta_agent import MetaAgent, meta_agent_spec
from src.compat.legacy_agents import CommandExecutorAgent, command_executor_spec

__all__ = [
    "PatternAnalyzerAgent",
    "pattern_analyzer_spec",
    "TodayTomorrowPlannerAgent",
    "planner_spec",
    "ForecasterAgent",
    "forecaster_spec",
    "RiskOpportunityAgent",
    "risk_opportunity_spec",
    "SchemaStructureAgent",
    "schema_structure_spec",
    "PresentationAgent",
    "presentation_spec",
    "SelfImprovementAgent",
    "self_improvement_spec",
    "ScraperAgent",
    "ScraperTask",
    "KafkaEventAgent",
    "EventEnvelope",
    "MetricsAgent",
    "MetricRecord",
    "MetaAgent",
    "meta_agent_spec",
    "CommandExecutorAgent",
    "command_executor_spec",
]
