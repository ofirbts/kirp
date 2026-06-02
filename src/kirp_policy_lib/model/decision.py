from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


@dataclass(frozen=True)
class PolicyResult:
    rule_id: str
    matched: bool
    effect: Verdict


@dataclass(frozen=True)
class EvaluationDecision:
    verdict: Verdict
    reason: str
    tenant_id: str | None
    policy_results: tuple[PolicyResult, ...] = ()
    trace_id: str = ""


@dataclass
class EvaluationConfig:
    require_tenant_for_mutations: bool = True
    deny_wildcard_tenant: bool = True
    allow_read_without_tenant: bool = True
    mutation_methods: frozenset[str] = field(
        default_factory=lambda: frozenset({"POST", "PUT", "PATCH", "DELETE"})
    )
