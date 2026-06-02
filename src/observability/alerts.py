"""
Alerts — SLO breaches, critical failures, governance violations.

Integrates with Prometheus alerting, PagerDuty, etc.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# Condition: "metric_name op value" e.g. "worker_failures > 10", "ingest_latency_sec >= 5"
_CONDITION_RE = re.compile(r"^\s*(\w+)\s*(>=?|<=?|==?|!=)\s*([\d.]+)\s*$")


def _evaluate_condition(condition: str, metrics: dict[str, Any]) -> tuple[bool, float | None]:
    """Parse condition and check against metrics. Returns (triggered, current_value)."""
    m = _CONDITION_RE.match(condition)
    if not m:
        return False, None
    name, op, raw_val = m.groups()
    try:
        threshold = float(raw_val)
    except ValueError:
        return False, None
    val = metrics.get(name)
    if val is None:
        return False, None
    try:
        current = float(val)
    except (TypeError, ValueError):
        return False, None
    if op == ">":
        triggered = current > threshold
    elif op == ">=":
        triggered = current >= threshold
    elif op == "<":
        triggered = current < threshold
    elif op == "<=":
        triggered = current <= threshold
    elif op == "==":
        triggered = current == threshold
    elif op == "!=":
        triggered = current != threshold
    else:
        triggered = False
    return triggered, current


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
        for r in self._rules:
            triggered, current = _evaluate_condition(r["condition"], metrics)
            if triggered:
                alerts.append(Alert(
                    severity=r["severity"],
                    rule=r["name"],
                    message=f"Rule {r['name']} triggered: {r['condition']} (current={current})",
                    labels=dict(r["labels"]),
                    value=current,
                ))
        return alerts

    async def fire(self, alert: Alert) -> None:
        """Persist and forward alert (log + optional webhook)."""
        logger.warning("ALERT %s %s: %s", alert.severity.value, alert.rule, alert.message)
        webhook_url = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
        if webhook_url:
            try:
                import httpx
                payload = {
                    "severity": alert.severity.value,
                    "rule": alert.rule,
                    "message": alert.message,
                    "labels": alert.labels,
                    "value": alert.value,
                    "fired_at": alert.fired_at.isoformat() if alert.fired_at else None,
                }
                async with httpx.AsyncClient() as client:
                    resp = await client.post(webhook_url, json=payload, timeout=10.0)
                    if resp.status_code >= 400:
                        logger.warning("Alert webhook returned %s: %s", resp.status_code, resp.text)
            except Exception as e:
                logger.warning("Alert webhook failed: %s", e)
