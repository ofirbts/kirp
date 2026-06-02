"""
Production alerting: failed run steps and failure-rate thresholds (Redis-backed).

Hooks from RunController.update_step. Optional Slack webhook (ALERT_SLACK_WEBHOOK_URL).
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Count toward success denominator (terminal healthy signals, not every micro-step).
_TERMINAL_SUCCESS_STEPS = frozenset(
    {
        "pipeline_complete",
        "agent_execute_complete",
        "kafka_processed",
    }
)

_ACTIVE_KEY = "tenant:{tenant_id}:alerts:active"
_FAIL_KEY = "tenant:{tenant_id}:alert:h:{bucket}:failures"
_OK_KEY = "tenant:{tenant_id}:alert:h:{bucket}:successes"


def _hour_bucket() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H")


async def _redis() -> Any:
    from src.core.integrations import get_redis_async

    return get_redis_async()


def _failures_threshold() -> int:
    try:
        return max(1, int(os.getenv("ALERT_FAILURES_PER_HOUR", "5")))
    except ValueError:
        return 5


def _failure_rate_threshold() -> float:
    try:
        return float(os.getenv("ALERT_FAILURE_RATE_THRESHOLD", "0.2"))
    except ValueError:
        return 0.2


def _min_samples_for_rate() -> int:
    try:
        return max(3, int(os.getenv("ALERT_MIN_SAMPLES_FOR_RATE", "10")))
    except ValueError:
        return 10


async def _incr_key(key: str) -> int:
    r = await _redis()
    if r is None:
        return 0
    try:
        n = await r.incr(key)
        await r.expire(key, int(os.getenv("ALERT_COUNTER_TTL_SEC", "7200")))
        return int(n)
    except Exception as e:
        logger.warning("alerting incr failed %s: %s", key, e)
        return 0


async def _read_int(key: str) -> int:
    r = await _redis()
    if r is None:
        return 0
    try:
        v = await r.get(key)
        return int(v) if v is not None else 0
    except Exception:
        return 0


async def _load_active(tenant_id: str) -> list[dict[str, Any]]:
    r = await _redis()
    if r is None:
        return []
    key = _ACTIVE_KEY.format(tenant_id=tenant_id)
    try:
        raw = await r.get(key)
        if not raw:
            return []
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("alerting load active failed: %s", e)
        return []


async def _save_active(tenant_id: str, alerts: list[dict[str, Any]]) -> None:
    r = await _redis()
    if r is None:
        return
    key = _ACTIVE_KEY.format(tenant_id=tenant_id)
    try:
        trimmed = alerts[:50]
        await r.set(
            key,
            json.dumps(trimmed),
            ex=int(os.getenv("ALERT_ACTIVE_TTL_SEC", str(86400 * 7))),
        )
    except Exception as e:
        logger.warning("alerting save active failed: %s", e)


async def _append_alert(
    tenant_id: str,
    *,
    alert_type: str,
    severity: str,
    message: str,
    meta: dict[str, Any] | None = None,
) -> None:
    alerts = await _load_active(tenant_id)
    now = datetime.now(timezone.utc).isoformat()
    # Dedupe same type in the same hour bucket
    bucket = _hour_bucket()
    for a in alerts:
        if a.get("type") == alert_type and str(a.get("meta", {}).get("hour_bucket")) == bucket:
            a["message"] = message
            a["raised_at"] = now
            a["severity"] = severity
            a["meta"] = {**(a.get("meta") or {}), **(meta or {}), "hour_bucket": bucket}
            await _save_active(tenant_id, alerts)
            return

    row = {
        "id": str(uuid.uuid4()),
        "type": alert_type,
        "severity": severity,
        "message": message,
        "raised_at": now,
        "meta": {**(meta or {}), "hour_bucket": bucket},
    }
    alerts.insert(0, row)
    await _save_active(tenant_id, alerts)
    await _notify_channels(tenant_id, row)


async def _notify_channels(tenant_id: str, alert: dict[str, Any]) -> None:
    msg = alert.get("message", "")
    logger.error(
        "[ALERT] tenant=%s type=%s severity=%s %s",
        tenant_id,
        alert.get("type"),
        alert.get("severity"),
        msg,
    )
    url = (os.getenv("ALERT_SLACK_WEBHOOK_URL") or "").strip()
    if not url:
        return
    try:
        import httpx

        text = f"*KIRP alert* — tenant `{tenant_id}`\n*{alert.get('type')}* ({alert.get('severity')})\n{msg}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json={"text": text})
    except Exception as e:
        logger.warning("alerting slack webhook failed: %s", e)


async def _evaluate_thresholds(tenant_id: str, run_id: str | None, step_name: str | None) -> None:
    bucket = _hour_bucket()
    fk = _FAIL_KEY.format(tenant_id=tenant_id, bucket=bucket)
    sk = _OK_KEY.format(tenant_id=tenant_id, bucket=bucket)
    f_ct = await _read_int(fk)
    s_ct = await _read_int(sk)
    th = _failures_threshold()
    if f_ct >= th:
        await _append_alert(
            tenant_id,
            alert_type="hourly_failures",
            severity="warning",
            message=f"{f_ct} failed run steps this hour (threshold {th})",
            meta={"failures": f_ct, "run_id": run_id, "step": step_name},
        )

    total = f_ct + s_ct
    if total >= _min_samples_for_rate():
        rate = f_ct / total
        if rate > _failure_rate_threshold():
            await _append_alert(
                tenant_id,
                alert_type="high_failure_rate",
                severity="critical",
                message=(
                    f"Failure rate {rate:.2f} exceeds {_failure_rate_threshold():.2f} "
                    f"({f_ct} fails / {total} terminal signals this hour)"
                ),
                meta={"rate": rate, "failures": f_ct, "successes": s_ct},
            )


async def on_run_controller_step(
    tenant_id: str,
    run_id: str,
    step_name: str,
    status: str,
) -> None:
    """Call from RunController.update_step after persisting state."""
    if not tenant_id or tenant_id == "*":
        return
    st = str(status or "").lower()
    bucket = _hour_bucket()
    if st == "failed":
        key = _FAIL_KEY.format(tenant_id=tenant_id, bucket=bucket)
        await _incr_key(key)
        await _evaluate_thresholds(tenant_id, run_id, step_name)
    elif st in ("completed", "success", "accepted") and step_name in _TERMINAL_SUCCESS_STEPS:
        key = _OK_KEY.format(tenant_id=tenant_id, bucket=bucket)
        await _incr_key(key)
        await _evaluate_thresholds(tenant_id, run_id, step_name)


async def get_active_alerts(tenant_id: str) -> list[dict[str, Any]]:
    """Active alerts for API / dashboard."""
    return await _load_active(tenant_id)


class Alerting:
    """Facade for spec / explicit calls (e.g. cron re-check)."""

    @staticmethod
    async def check_run_alerts(tenant_id: str) -> list[dict[str, Any]]:
        """Re-evaluate thresholds from current Redis counters (no new failure event)."""
        if not tenant_id or tenant_id == "*":
            return []
        await _evaluate_thresholds(tenant_id, None, None)
        return await get_active_alerts(tenant_id)
