"""
Governance Engine — OPA policies, approvals, audit.

Every agent action must be:
- Logged
- Explainable
- Reversible
- Governed by policy (OPA)
- Optionally require human approval
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


@dataclass
class GovernanceCheck:
    """Result of a governance check."""

    allowed: bool
    reason: str
    requires_approval: bool
    policy_id: str | None = None
    risk_score: float = 0.0


class GovernanceEngine:
    """
    Policy-based governance. OPA integration; approval workflows; audit trail.
    """

    def __init__(self, opa_url: str | None = None) -> None:
        self._opa_url = opa_url or "http://localhost:8181"
        self._enabled = bool(opa_url)

    async def check(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str,
        action: str,
        resource: str,
        context: dict[str, Any] | None = None,
    ) -> GovernanceCheck:
        """
        Run OPA policy check. Returns risk score, approval requirement.
        """
        if not self._enabled:
            return GovernanceCheck(
                allowed=True,
                reason="Governance disabled (no OPA)",
                requires_approval=False,
                risk_score=0.0,
            )

        # Calculate risk score
        risk_score = self._calculate_risk_score(action, resource, context or {})

        try:
            import httpx
            ctx = context or {}
            payload = {
                "input": {
                    "tenant_id": tenant_id,
                    "space_id": space_id,
                    "user_id": user_id,
                    "user_tenant_id": tenant_id,  # TODO: Get from user lookup
                    "action": action,
                    "resource": resource,
                    "resource_type": ctx.get("resource_type", "event"),
                    "sensitivity": ctx.get("sensitivity", "private"),
                    "agent_autonomy": ctx.get("agent_autonomy", "full"),
                    "approved": ctx.get("approved", False),
                    "cross_tenant_grant": ctx.get("cross_tenant_grant", False),
                    "user_role": ctx.get("user_role", "member"),
                    "space_owner_id": ctx.get("space_owner_id", user_id),
                    "space_members": ctx.get("space_members", [user_id]),
                    "roles": ctx.get("roles", []),
                    "resource_owner_id": ctx.get("resource_owner_id", user_id),
                    "risk_score": risk_score,
                    "event_type": ctx.get("event_type"),
                    "module": ctx.get("module"),
                    "identity_entropy_score": ctx.get("identity_entropy_score"),
                }
            }
            async with httpx.AsyncClient() as client:
                # Use /allow endpoint (returns bool); full /governance can 500 depending on policy load
                r = await client.post(
                    f"{self._opa_url}/v1/data/kirp/governance/allow",
                    json=payload,
                    timeout=5.0,
                )
            if r.status_code != 200:
                return GovernanceCheck(
                    allowed=False,
                    reason=f"OPA error: {r.status_code}",
                    requires_approval=True,
                    risk_score=risk_score,
                )
            data = r.json()
            result = data.get("result")
            # M3: identity_entropy_score >= 0.6 → require human approval (WhatsApp)
            m3_escalate = False
            if ctx.get("identity_entropy_score") is not None:
                try:
                    m3_escalate = float(ctx["identity_entropy_score"]) >= 0.6
                except (TypeError, ValueError):
                    pass
            # OPA returns full document at kirp.governance; fallback if result is bool (single-rule query)
            if isinstance(result, bool):
                return GovernanceCheck(
                    allowed=result,
                    reason="allowed" if result else "denied_by_policy",
                    requires_approval=m3_escalate or (risk_score >= 0.7),
                    risk_score=risk_score,
                )
            if not isinstance(result, dict):
                result = {}
            return GovernanceCheck(
                allowed=result.get("allow", False),
                reason=result.get("reason", "policy"),
                requires_approval=result.get("requires_approval", risk_score >= 0.7) or m3_escalate,
                policy_id=result.get("policy_id"),
                risk_score=risk_score,
            )
        except Exception as e:
            logger.warning("Governance check failed: %s", e)
            return GovernanceCheck(
                allowed=False,
                reason=str(e),
                requires_approval=True,
                risk_score=risk_score,
            )

    def _calculate_risk_score(self, action: str, resource: str, context: dict[str, Any]) -> float:
        """Calculate risk score (0.0-1.0)."""
        score = 0.0
        if action == "delete":
            score += 0.4
        if context.get("sensitivity") == "confidential":
            score += 0.3
        if context.get("resource_type") == "governance":
            score += 0.2
        if context.get("agent_autonomy") == "full":
            score += 0.1
        return min(score, 1.0)

    async def log_audit(
        self,
        tenant_id: str,
        user_id: str,
        action: str,
        resource: str,
        result: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append to audit trail. Persist to PostgreSQL."""
        try:
            from src.models.event import AuditLog
            from src.models.base import Base
            from sqlalchemy.orm import Session
            from src.core.integrations import get_postgres_session

            session = get_postgres_session()
            if session:
                audit = AuditLog(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    action=action,
                    resource=resource,
                    resource_id=details.get("resource_id") if details else None,
                    result=result,
                    policy_id=details.get("policy_id") if details else None,
                    risk_score=details.get("risk_score") if details else None,
                    details=details or {},
                    timestamp=datetime.now(timezone.utc),
                )
                session.add(audit)
                session.commit()
                session.close()
        except Exception as e:
            logger.error("Audit log failed: %s", e)
        logger.info(
            "AUDIT tenant=%s user=%s action=%s resource=%s result=%s",
            tenant_id, user_id, action, resource, result,
        )
