from __future__ import annotations

from src.kirp_policy_lib.core.engine import PolicyEngine
from src.kirp_policy_lib.core.evaluator import evaluate_envelope, evaluate_request_like
from src.kirp_policy_lib.core.policy import Policy, default_builtin_policy, merge_policies, policy_from_groups
from src.kirp_policy_lib.core.rule_factories import (
    rule_deny_method_in,
    rule_deny_path_prefix,
    rule_deny_path_unless_any_role,
)
from src.kirp_policy_lib.core.rules import Rule, RuleGroup
from src.kirp_policy_lib.decision_log import DecisionRecord, InMemoryDecisionLog
from src.kirp_policy_lib.model.decision import EvaluationConfig, EvaluationDecision, PolicyResult, Verdict
from src.kirp_policy_lib.model.request import OperationType, RequestEnvelope
from src.kirp_policy_lib.model.tenant import TenantContext, extract_tenant_id, resolve_tenant_context
from src.kirp_policy_lib.shadow.analyzer import ShadowRow, StaticRouteDefinition, shadow_analyze
from src.kirp_policy_lib.shadow.batch import (
    RegressionDiffReport,
    evaluate_many,
    format_diff_report,
    regression_compare,
    snapshots_from_batch,
)
from src.kirp_policy_lib.tracing.graph import DecisionTrace, DecisionTraceBuilder, TraceNode, flatten_trace_to_rows
from src.kirp_policy_lib.tracing.trace import trace_depth, trace_ordered_steps

__all__ = [
    "DecisionRecord",
    "DecisionTrace",
    "DecisionTraceBuilder",
    "EvaluationConfig",
    "EvaluationDecision",
    "InMemoryDecisionLog",
    "OperationType",
    "Policy",
    "PolicyEngine",
    "PolicyResult",
    "RegressionDiffReport",
    "RequestEnvelope",
    "Rule",
    "RuleGroup",
    "ShadowRow",
    "StaticRouteDefinition",
    "TenantContext",
    "TraceNode",
    "Verdict",
    "default_builtin_policy",
    "evaluate_envelope",
    "evaluate_many",
    "evaluate_request_like",
    "extract_tenant_id",
    "flatten_trace_to_rows",
    "format_diff_report",
    "merge_policies",
    "policy_from_groups",
    "regression_compare",
    "resolve_tenant_context",
    "rule_deny_method_in",
    "rule_deny_path_prefix",
    "rule_deny_path_unless_any_role",
    "shadow_analyze",
    "snapshots_from_batch",
    "trace_depth",
    "trace_ordered_steps",
]
