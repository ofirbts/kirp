"""Agent execution binds llm_run_context so LLMClient records llm_call_* on RunController."""

from __future__ import annotations

import asyncio
import uuid

import pytest

import src.core.run_controller as rcmod
from src.core.agent_engine import AgentExecutionEngine


def test_execute_run_binds_llm_run_id_for_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        c = rcmod.RunController(redis_ping_max_attempts=1)

        async def _no_redis(self: rcmod.RunController) -> object:
            return None

        monkeypatch.setattr(rcmod.RunController, "_redis_client", _no_redis)
        monkeypatch.setattr(rcmod, "_run_controller", c)

        rid = uuid.uuid4()
        await c.create_run("agent_run", "default", run_id=str(rid))

        engine = AgentExecutionEngine("redis://127.0.0.1:9")

        async def _engine_no_redis(self: AgentExecutionEngine) -> object:
            return None

        monkeypatch.setattr(AgentExecutionEngine, "_redis_client", _engine_no_redis)

        async def handler(
            tenant_id: str,
            space_id: str,
            user_id: str,
            context: dict,
        ) -> dict:
            from src.core.llm_run_context import get_llm_run_id, get_llm_tenant_id

            assert get_llm_run_id() == str(rid)
            assert get_llm_tenant_id() == "default"
            return {"ok": True}

        out = await engine.execute_run(
            rid,
            "TestAgent",
            "default",
            "all",
            "user1",
            {},
            handler,
        )
        assert out.get("ok") is True

        from src.core.llm_run_context import get_llm_run_id

        assert get_llm_run_id() is None

    asyncio.run(_run())


def test_execute_run_resets_context_after_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        c = rcmod.RunController(redis_ping_max_attempts=1)

        async def _no_redis(self: rcmod.RunController) -> object:
            return None

        monkeypatch.setattr(rcmod.RunController, "_redis_client", _no_redis)
        monkeypatch.setattr(rcmod, "_run_controller", c)

        rid = uuid.uuid4()
        await c.create_run("agent_run", "default", run_id=str(rid))

        engine = AgentExecutionEngine("redis://127.0.0.1:9")

        async def _engine_no_redis(self: AgentExecutionEngine) -> object:
            return None

        monkeypatch.setattr(AgentExecutionEngine, "_redis_client", _engine_no_redis)

        async def handler(**kwargs: object) -> dict:
            raise RuntimeError("boom")

        try:
            await engine.execute_run(rid, "X", "default", "all", "u", {}, handler)
        except RuntimeError:
            pass
        else:
            raise AssertionError("expected RuntimeError")

        from src.core.llm_run_context import get_llm_run_id

        assert get_llm_run_id() is None

    asyncio.run(_run())


def test_run_agent_and_log_binds_when_run_id_in_context(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        seen: list[str | None] = []

        class FW:
            async def run(self, name: str, tid: str, sid: str, uid: str, ctx: dict) -> dict:
                from src.core.llm_run_context import get_llm_run_id, get_llm_tenant_id

                seen.append((get_llm_run_id(), get_llm_tenant_id()))
                return {"ok": True}

        class FakeLogs:
            async def append(self, *args: object, **kwargs: object) -> None:
                return None

        monkeypatch.setattr("src.core.agent_scheduler.get_agent_logs_store", lambda: FakeLogs())

        from src.core.agent_scheduler import AgentScheduler

        sched = AgentScheduler(FW(), None)
        await sched.run_agent_and_log(
            "AnyAgent",
            "default",
            "all",
            "u",
            "manual",
            initial_context={"run_id": "run_test_bind"},
        )
        assert seen == [("run_test_bind", "default")]

        from src.core.llm_run_context import get_llm_run_id

        assert get_llm_run_id() is None

    asyncio.run(_run())
