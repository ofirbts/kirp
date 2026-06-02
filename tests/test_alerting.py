"""src/core/alerting — Redis counters and active alerts."""

from __future__ import annotations

import asyncio
import json

import pytest

from src.core.alerting import (
    get_active_alerts,
    on_run_controller_step,
)


class _FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str | int | float] = {}

    async def incr(self, key: str) -> int:
        cur = int(self.kv.get(key, 0))
        cur += 1
        self.kv[key] = cur
        return cur

    async def expire(self, *_a: object, **_k: object) -> None:
        return

    async def get(self, key: str) -> str | None:
        if key not in self.kv:
            return None
        v = self.kv[key]
        if isinstance(v, (int, float)):
            return str(v)
        return str(v)

    async def set(self, key: str, value: str | bytes, ex: int | None = None) -> None:
        if isinstance(value, bytes):
            value = value.decode()
        self.kv[key] = value


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> _FakeRedis:
    fr = _FakeRedis()

    async def _r() -> _FakeRedis:
        return fr

    monkeypatch.setattr("src.core.alerting._redis", _r)
    return fr


def test_five_failures_raise_hourly_alert(fake_redis: _FakeRedis, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALERT_FAILURES_PER_HOUR", "5")

    async def _go() -> None:
        for i in range(5):
            await on_run_controller_step("default", f"run_{i}", "kafka_failed", "failed")
        alerts = await get_active_alerts("default")
        assert len(alerts) >= 1
        assert any(a.get("type") == "hourly_failures" for a in alerts)

    asyncio.run(_go())


def test_failure_rate_alert(fake_redis: _FakeRedis, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALERT_MIN_SAMPLES_FOR_RATE", "10")
    monkeypatch.setenv("ALERT_FAILURE_RATE_THRESHOLD", "0.2")

    async def _go() -> None:
        # 3 failures + 8 terminal successes = 11 samples, rate 3/11 > 0.2
        for _ in range(3):
            await on_run_controller_step("acme", "r1", "x", "failed")
        for _ in range(8):
            await on_run_controller_step("acme", "r1", "pipeline_complete", "completed")
        alerts = await get_active_alerts("acme")
        types = {a.get("type") for a in alerts}
        assert "high_failure_rate" in types

    asyncio.run(_go())


def test_get_active_empty_without_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    fr = _FakeRedis()

    async def _r() -> _FakeRedis:
        return fr

    monkeypatch.setattr("src.core.alerting._redis", _r)

    async def _go() -> None:
        assert await get_active_alerts("zzz") == []

    asyncio.run(_go())
