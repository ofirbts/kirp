"""
Alerts — SLO breaches, critical failures, governance violations.

Integrates with Prometheus alerting, PagerDuty, etc.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Alert:
    severity: AlertSeverity
    rule: str
    message: str
    labels: dict[str, str]
    value: float | None = None
    fired_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.fired_at is None:
            self.fired_at = datetime.now(timezone.utc)


class AlertEngine:
    """Evaluate rules, emit alerts. Persist to ELK / Prometheus."""

    def __init__(self) -> None:
        self._rules: list[dict[str, Any]] = []

    def add_rule(self, name: str, condition: str, severity: AlertSeverity, labels: dict[str, str] | None = None) -> None:
        """Register alert rule."""
        self._rules.append({
            "name": name,
            "condition": condition,
            "severity": severity,
            "labels": labels or {},
        })

    async def evaluate(self, metrics: dict[str, Any]) -> list[Alert]:
        """Evaluate rules against current metrics. Return fired alerts."""
        alerts: list[Alert] = []
        # TODO: Evaluate conditions (e.g. worker_failures > 10, ingest_latency > 5s)
        for r in self._rules:
            # Placeholder: no actual eval
            pass
        return alerts

    async def fire(self, alert: Alert) -> None:
        """Persist and forward alert (e.g. PagerDuty, webhook)."""
        logger.warning("ALERT %s %s: %s", alert.severity.value, alert.rule, alert.message)
        # TODO: Persist to DB; send to PagerDuty/webhook
