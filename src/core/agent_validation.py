"""
Agent Output Validation — JSON schema validation for all agent outputs.

Ensures agent responses match expected schemas for reliability and type safety.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import jsonschema
    from jsonschema import validate, ValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    logger.warning("jsonschema not installed; validation will be lenient")


# Agent output schemas
AGENT_SCHEMAS: dict[str, dict[str, Any]] = {
    "PatternAnalyzerAgent": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "patterns": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "description": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "evidence": {"type": "string"},
                    },
                    "required": ["type", "description"],
                },
            },
            "summary": {"type": "string"},
            "explanation": {"type": "string"},
        },
        "required": ["ok"],
    },
    "TodayTomorrowPlannerAgent": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "plan": {
                "type": "object",
                "properties": {
                    "today": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string"},
                                "priority": {"type": "string"},
                                "reason": {"type": "string"},
                            },
                            "required": ["action"],
                        },
                    },
                    "tomorrow": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string"},
                                "priority": {"type": "string"},
                            },
                            "required": ["action"],
                        },
                    },
                    "critical": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string"},
                                "urgency": {"type": "string"},
                            },
                            "required": ["action"],
                        },
                    },
                },
            },
            "explanation": {"type": "string"},
        },
        "required": ["ok"],
    },
    "ForecasterAgent": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "forecast": {
                "type": "object",
                "properties": {
                    "tomorrow_load": {"type": "string"},
                    "bottlenecks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "severity": {"type": "string"},
                            },
                        },
                    },
                    "upcoming_issues": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "issue": {"type": "string"},
                                "probability": {"type": "number", "minimum": 0, "maximum": 1},
                                "impact": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "explanation": {"type": "string"},
        },
        "required": ["ok"],
    },
    "RiskOpportunityAgent": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "items": {
                "type": "object",
                "properties": {
                    "risks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "severity": {"type": "string"},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "description": {"type": "string"},
                            },
                        },
                    },
                    "opportunities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "impact": {"type": "string"},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "description": {"type": "string"},
                            },
                        },
                    },
                    "missed_follow_ups": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string"},
                                "original_date": {"type": "string"},
                                "urgency": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "explanation": {"type": "string"},
        },
        "required": ["ok"],
    },
    "SchemaStructureAgent": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "nodes_upserted": {"type": "integer", "minimum": 0},
            "breakdown": {
                "type": "object",
                "properties": {
                    "life_areas": {"type": "integer"},
                    "projects": {"type": "integer"},
                    "tasks": {"type": "integer"},
                    "categories": {"type": "integer"},
                },
            },
            "explanation": {"type": "string"},
        },
        "required": ["ok"],
    },
    "PresentationAgent": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "view": {"type": "object"},
            "explanation": {"type": "string"},
        },
        "required": ["ok"],
    },
    "SelfImprovementAgent": {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "target": {"type": "string"},
                        "description": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
            "explanation": {"type": "string"},
        },
        "required": ["ok"],
    },
}


def validate_agent_output(agent_name: str, output: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Validate agent output against JSON schema.
    Returns (is_valid, error_message).
    """
    if not JSONSCHEMA_AVAILABLE:
        # Lenient validation if jsonschema not available
        if not isinstance(output, dict):
            return False, "Output must be a dictionary"
        if "ok" not in output:
            return False, "Output must have 'ok' field"
        return True, None
    
    schema = AGENT_SCHEMAS.get(agent_name)
    if not schema:
        # No schema defined - allow but warn
        logger.debug("No schema defined for agent: %s", agent_name)
        return True, None
    
    try:
        validate(instance=output, schema=schema)
        return True, None
    except ValidationError as e:
        error_msg = f"Validation failed: {e.message} at {'.'.join(str(p) for p in e.path)}"
        logger.warning("Agent %s output validation failed: %s", agent_name, error_msg)
        return False, error_msg
    except Exception as e:
        logger.error("Validation error for agent %s: %s", agent_name, e)
        return False, str(e)


def normalize_agent_output(agent_name: str, output: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize and fix common issues in agent output.
    Returns normalized output.
    """
    normalized = output.copy()
    
    # Ensure 'ok' field exists
    if "ok" not in normalized:
        normalized["ok"] = True
    
    # Ensure boolean is actually boolean
    if isinstance(normalized.get("ok"), str):
        normalized["ok"] = normalized["ok"].lower() in ("true", "1", "yes", "ok")
    
    # Validate and return
    is_valid, error = validate_agent_output(agent_name, normalized)
    if not is_valid:
        logger.warning("Agent %s output normalization: %s", agent_name, error)
        # Still return normalized output, but mark as potentially invalid
        normalized["_validation_error"] = error
    
    return normalized
