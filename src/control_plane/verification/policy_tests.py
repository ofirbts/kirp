from __future__ import annotations

from src.control_plane.policy_engine.engine import PolicyEngine
from src.control_plane.policy_engine.rules import RuleAction


def assert_policy_allows(engine: PolicyEngine, resource_type: str, context: dict[str, object]) -> None:
    if engine.decide(resource_type, context) != RuleAction.ALLOW:
        raise AssertionError("policy denied")
