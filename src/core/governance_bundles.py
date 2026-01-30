"""
Governance Policy Bundles — OPA bundle versioning, enforcement hooks, multi-tenant isolation.

- Policy bundles: named + versioned (Postgres or file)
- Enforcement hook: check + audit in one call
- Multi-tenant isolation enforced at hook level
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.core.governance import GovernanceEngine, GovernanceCheck

logger = logging.getLogger(__name__)


@dataclass
class PolicyBundle:
    """Named, versioned policy bundle (metadata; OPA holds actual Rego)."""

    name: str
    version: str
    engine: str = "opa"
    path: str | None = None  # OPA path e.g. kirp/governance
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GovernanceEnforcement:
    """
    Enforcement hooks: run OPA check and log audit in one call.
    Ensures multi-tenant isolation (tenant_id required).
    """

    def __init__(self, engine: GovernanceEngine) -> None:
        self._engine = engine

    async def enforce(
        self,
        tenant_id: str,
        space_id: str,
        user_id: str,
        action: str,
        resource: str,
        resource_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> GovernanceCheck:
        """
        Run policy check; if denied or requires_approval, log audit and return.
        Caller must not proceed if check.allowed is False or check.requires_approval is True (until approved).
        """
        if not tenant_id or tenant_id == "*":
            await self._engine.log_audit(
                tenant_id=tenant_id or "unknown",
                user_id=user_id,
                action=action,
                resource=resource,
                result="denied",
                details={"reason": "tenant_id required", "resource_id": resource_id},
            )
            return GovernanceCheck(allowed=False, reason="tenant_id required (multi-tenant isolation)", requires_approval=False)

        check = await self._engine.check(
            tenant_id=tenant_id,
            space_id=space_id,
            user_id=user_id,
            action=action,
            resource=resource,
            context=context,
        )

        await self._engine.log_audit(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource=resource,
            result="allowed" if check.allowed else "denied",
            details={
                "reason": check.reason,
                "resource_id": resource_id,
                "policy_id": check.policy_id,
                "risk_score": check.risk_score,
                "requires_approval": check.requires_approval,
            },
        )
        return check
