"""RunController aggregate state and Redis hash serialization."""

from __future__ import annotations

import asyncio

import pytest

from src.core.run_controller import RunController, RunState


def test_overall_state_uses_last_status_per_step_name(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        rc = RunController(redis_ping_max_attempts=1)

        async def _no_redis(self: RunController) -> object:
            return None

        monkeypatch.setattr(RunController, "_redis_client", _no_redis)

        rid = "run_test_dup_steps"
        await rc.create_run("ingest", "t1", run_id=rid)
        await rc.update_step(rid, "kafka_received", "processing")
        await rc.update_step(rid, "kafka_received", "completed")
        await rc.update_step(rid, "pipeline_start", "processing")
        await rc.update_step(rid, "pipeline_start", "completed")
        await rc.update_step(rid, "pipeline_complete", "completed")
        st = await rc.get_run_status(rid)
        assert st is not None
        assert st["state"] == "completed"

    asyncio.run(_run())


def test_overall_state_api_publish_only_not_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    """After ingest API: kafka_emitted must not imply run-complete (worker/pipeline pending)."""

    async def _run() -> None:
        rc = RunController(redis_ping_max_attempts=1)

        async def _no_redis(self: RunController) -> object:
            return None

        monkeypatch.setattr(RunController, "_redis_client", _no_redis)

        rid = "run_api_only"
        await rc.create_run("ingest", "t1", run_id=rid)
        await rc.update_step(rid, "kafka_emitted", "completed")
        st = await rc.get_run_status(rid)
        assert st is not None
        assert st["state"] == "accepted"

    asyncio.run(_run())


def test_hash_mapping_roundtrip() -> None:
    rc = RunController()
    s = RunState(
        run_id="run_x",
        workflow_type="ingest",
        tenant_id="t1",
        idempotency_key=None,
        state="completed",
        trace_id="tr1",
        steps=[{"step": "history_write", "status": "completed", "error": None, "ts": "2026-01-01T00:00:00+00:00"}],
    )
    h = rc._state_to_hash_mapping(s)
    out = rc._run_state_from_hash(h)
    assert out is not None
    assert out.run_id == "run_x"
    assert out.state == "completed"
    assert len(out.steps) == 1
    assert out.steps[0]["step"] == "history_write"


class _FakeRedis:
    """Minimal async Redis stub for partition-key assertions."""

    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.strings: dict[str, str] = {}

    async def delete(self, key: str) -> None:
        self.hashes.pop(key, None)

    async def hset(self, key: str, mapping: dict[str, str] | None = None, **kwargs: str) -> None:
        if mapping:
            self.hashes.setdefault(key, {}).update(mapping)
        if kwargs:
            self.hashes.setdefault(key, {}).update(kwargs)

    async def expire(self, key: str, ttl: int) -> None:
        pass

    async def set(self, key: str, val: str, ex: int | None = None) -> None:
        self.strings[key] = val

    async def get(self, key: str) -> str | None:
        return self.strings.get(key)

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))


def test_partitioned_redis_keys_two_tenants(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        fake = _FakeRedis()
        rc = RunController(redis_ping_max_attempts=1)
        rc._redis = fake
        await rc.create_run("ingest", "tenant_a", run_id="run_alpha")
        await rc.create_run("ingest", "tenant_b", run_id="run_beta")
        assert "tenant:tenant_a:run_alpha" in fake.hashes
        assert "tenant:tenant_b:run_beta" in fake.hashes
        assert fake.strings.get("run_lookup:run_alpha") == "tenant_a"
        assert fake.strings.get("run_lookup:run_beta") == "tenant_b"
        a = await rc.get_run_state("run_alpha", tenant_id="tenant_a")
        b = await rc.get_run_state("run_beta", tenant_id="tenant_b")
        assert a is not None and a.tenant_id == "tenant_a"
        assert b is not None and b.tenant_id == "tenant_b"

    asyncio.run(_run())
