from __future__ import annotations

import pytest

from src.control_plane.policy_engine.engine import PolicyEngine
from src.control_plane.policy_engine.registry import RuleRegistry
from src.control_plane.policy_engine.rules import Rule, RuleAction
from src.control_plane.verification.policy_tests import assert_policy_allows


def test_policy_deny_by_default() -> None:
    eng = PolicyEngine(RuleRegistry())
    assert eng.decide("x", {"k": True}) == RuleAction.DENY


def test_policy_allow_when_rule_matches() -> None:
    reg = RuleRegistry()
    reg.register(
        Rule("r1", RuleAction.ALLOW, "doc", frozenset({"tenant_id"})),
    )
    eng = PolicyEngine(reg)
    assert eng.decide("doc", {"tenant_id": "t1"}) == RuleAction.ALLOW


def test_policy_deny_overrides_allow() -> None:
    reg = RuleRegistry()
    reg.register(Rule("a", RuleAction.ALLOW, "doc", frozenset({"tenant_id"})))
    reg.register(Rule("d", RuleAction.DENY, "doc", frozenset({"tenant_id", "blocked"})))
    eng = PolicyEngine(reg)
    assert eng.decide("doc", {"tenant_id": "t1", "blocked": True}) == RuleAction.DENY


def test_assert_policy_allows() -> None:
    reg = RuleRegistry()
    reg.register(Rule("a", RuleAction.ALLOW, "x", frozenset({"ok"})))
    eng = PolicyEngine(reg)
    assert_policy_allows(eng, "x", {"ok": True})


def test_assert_policy_allows_raises() -> None:
    eng = PolicyEngine(RuleRegistry())
    with pytest.raises(AssertionError):
        assert_policy_allows(eng, "x", {})
