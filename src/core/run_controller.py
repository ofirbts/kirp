"""
Run Controller — authoritative run state tracker.

Stores run lifecycle in Redis under partitioned keys `tenant:{tenant_id}:{run_id}`
plus `run_lookup:{run_id}` → tenant_id for resolution without an explicit tenant.
Legacy `run:{run_id}` is still read when enabled for migration (RUN_CONTROLLER_READ_LEGACY_KEYS).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


def infer_llm_route_from_steps(steps: list[dict[str, Any]]) -> str | None:
    """Last logical LLM route from RunController steps (llm_call_<route>)."""
    for s in reversed(steps or []):
        name = str(s.get("step") or "")
        if name.startswith("llm_call_"):
            return name[9:] or None
    return None


@dataclass
class RunState:
    run_id: str
    workflow_type: str
    tenant_id: str
    idempotency_key: str | None
    state: str = "accepted"
    trace_id: str | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)
    cost: float = 0.0
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _truthy_env(name: str, default: str = "1") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in ("1", "true", "yes", "on")


class RunController:
    def __init__(
        self,
        *,
        redis_ping_max_attempts: int = 5,
        redis_ping_base_delay_sec: float = 0.4,
    ) -> None:
        self.run_states: dict[str, RunState] = {}
        self._redis: Any = None
        self._redis_hard_disabled: bool = False
        self._redis_retry_not_before: float = 0.0
        self._redis_ping_max_attempts = max(1, redis_ping_max_attempts)
        self._redis_ping_base_delay_sec = redis_ping_base_delay_sec
        # Optional default tenant when get_run_state(run_id) is called without tenant_id (worker hint).
        self._default_tenant_for_keys: str | None = None

    async def _redis_client(self) -> Any:
        if self._redis_hard_disabled:
            return None
        now = time.monotonic()
        if self._redis is not None:
            return self._redis
        if now < self._redis_retry_not_before:
            return None
        try:
            import redis.asyncio as redis

            client = redis.from_url(
                os.getenv("REDIS_URL", "redis://redis:6379/0"),
                decode_responses=True,
            )
            last_err: Exception | None = None
            for attempt in range(1, self._redis_ping_max_attempts + 1):
                try:
                    await client.ping()
                    self._redis = client
                    self._redis_retry_not_before = 0.0
                    logger.info("RunController Redis connected (attempt %s)", attempt)
                    return self._redis
                except Exception as e:
                    last_err = e
                    logger.warning(
                        "RunController Redis ping attempt %s/%s failed: %s",
                        attempt,
                        self._redis_ping_max_attempts,
                        e,
                    )
                    if attempt < self._redis_ping_max_attempts:
                        await asyncio.sleep(self._redis_ping_base_delay_sec * attempt)
            try:
                await client.aclose()
            except Exception:
                pass
            self._redis_retry_not_before = now + 15.0
            logger.warning(
                "RunController Redis unavailable after %s attempts, backing off 15s: %s",
                self._redis_ping_max_attempts,
                last_err,
            )
            return None
        except Exception as e:
            logger.warning("RunController Redis client init failed, in-memory only: %s", e)
            self._redis_hard_disabled = True
            return None

    async def redis_health(self) -> bool:
        """True if Redis client is active and responds to PING."""
        if self._redis_hard_disabled:
            return False
        r = await self._redis_client()
        if r is None:
            return False
        try:
            return bool(await r.ping())
        except Exception as e:
            logger.warning("RunController redis_health failed: %s", e)
            self._redis = None
            self._redis_retry_not_before = time.monotonic() + 10.0
            return False

    async def create_run(
        self,
        workflow_type: str,
        tenant_id: str,
        idempotency_key: str | None = None,
        trace_id: str | None = None,
        run_id: str | None = None,
    ) -> str:
        rid = run_id or f"run_{uuid4().hex}"
        existing = await self.get_run_state(rid, tenant_id=tenant_id)
        if existing is not None:
            if existing.tenant_id and existing.tenant_id != tenant_id:
                logger.warning(
                    "create_run run_id=%s exists for tenant=%s, requested tenant=%s",
                    rid,
                    existing.tenant_id,
                    tenant_id,
                )
            return rid
        state = RunState(
            run_id=rid,
            workflow_type=workflow_type,
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
            state="accepted",
        )
        await self.set_run_state(rid, state)
        await self.update_step(rid, "api_accepted", "accepted")
        return rid

    def update_key_prefix(self, tenant_id: str | None) -> None:
        """
        Set default tenant for Redis key resolution when get_run_state(run_id) is called
        without tenant_id (e.g. single-tenant worker batch). Does not change stored data.
        """
        self._default_tenant_for_keys = tenant_id

    @staticmethod
    def partition_run_key(tenant_id: str, run_id: str) -> str:
        """Redis key for run state: tenant:{tenant_id}:{run_id}."""
        return f"tenant:{tenant_id}:{run_id}"

    def _legacy_run_key(self, run_id: str) -> str:
        return f"run:{run_id}"

    def _lookup_key(self, run_id: str) -> str:
        return f"run_lookup:{run_id}"

    def _state_to_hash_mapping(self, state: RunState) -> dict[str, str]:
        d = asdict(state)
        return {
            "state": str(d.get("state") or ""),
            "steps": json.dumps(d.get("steps") or []),
            "workflow_type": str(d.get("workflow_type") or ""),
            "tenant_id": str(d.get("tenant_id") or ""),
            "run_id": str(d.get("run_id") or ""),
            "trace_id": d.get("trace_id") or "",
            "idempotency_key": d.get("idempotency_key") or "",
            "cost": str(float(d.get("cost") or 0.0)),
            "started_at": str(d.get("started_at") or ""),
            "updated_at": str(d.get("updated_at") or ""),
        }

    @staticmethod
    def _run_state_from_hash(h: dict[str, str]) -> RunState | None:
        if not h:
            return None
        rid = h.get("run_id")
        if not rid:
            return None
        steps_raw = h.get("steps") or "[]"
        try:
            steps = json.loads(steps_raw) if isinstance(steps_raw, str) else steps_raw
        except json.JSONDecodeError:
            steps = []
        tid = h.get("trace_id") or None
        if tid == "":
            tid = None
        ikey = h.get("idempotency_key") or None
        if ikey == "":
            ikey = None
        try:
            cost = float(h.get("cost") or 0.0)
        except (TypeError, ValueError):
            cost = 0.0
        return RunState(
            run_id=rid,
            workflow_type=h.get("workflow_type") or "",
            tenant_id=h.get("tenant_id") or "",
            idempotency_key=ikey,
            state=h.get("state") or "accepted",
            trace_id=tid,
            steps=list(steps) if isinstance(steps, list) else [],
            cost=cost,
            started_at=h.get("started_at") or "",
            updated_at=h.get("updated_at") or "",
        )

    async def set_run_state(self, run_id: str, state: RunState) -> None:
        state.updated_at = datetime.now(timezone.utc).isoformat()
        self.run_states[run_id] = state
        redis = await self._redis_client()
        if redis is not None:
            try:
                tid = state.tenant_id or ""
                if not tid or tid == "*":
                    logger.warning("RunController set_run_state missing tenant_id for run_id=%s", run_id)
                mapping = self._state_to_hash_mapping(state)
                ttl = 86400 * 7
                if tid and tid != "*":
                    pkey = self.partition_run_key(tid, run_id)
                    await redis.delete(pkey)
                    await redis.hset(pkey, mapping=mapping)
                    await redis.expire(pkey, ttl)
                    await redis.set(self._lookup_key(run_id), tid, ex=ttl)
                if _truthy_env("RUN_CONTROLLER_WRITE_LEGACY_RUN_KEY", "0"):
                    lk = self._legacy_run_key(run_id)
                    await redis.delete(lk)
                    await redis.hset(lk, mapping=mapping)
                    await redis.expire(lk, ttl)
            except Exception as e:
                logger.warning("RunController set redis failed for %s: %s", run_id, e)

    async def _read_state_from_redis_hash_key(self, redis: Any, key: str) -> RunState | None:
        h: dict[str, str] = {}
        try:
            h = await redis.hgetall(key)
        except Exception as e:
            err = str(e).upper()
            if "WRONGTYPE" not in err:
                raise
            logger.debug("RunController WRONGTYPE at %s, trying GET", key)
        if h:
            parsed = self._run_state_from_hash(h)
            if parsed is not None:
                return parsed
        try:
            raw = await redis.get(key)
            if raw:
                data = json.loads(raw)
                return RunState(**data)
        except Exception:
            pass
        return None

    async def get_run_state(self, run_id: str, tenant_id: str | None = None) -> RunState | None:
        if run_id in self.run_states:
            st = self.run_states[run_id]
            if tenant_id and st.tenant_id and st.tenant_id != tenant_id:
                return None
            return st

        redis = await self._redis_client()
        if redis is None:
            return None

        eff_tenant = tenant_id
        if eff_tenant is None:
            try:
                raw_tid = await redis.get(self._lookup_key(run_id))
                if raw_tid:
                    eff_tenant = str(raw_tid)
            except Exception as e:
                logger.debug("RunController run_lookup read failed: %s", e)
        if eff_tenant is None:
            eff_tenant = self._default_tenant_for_keys

        try:
            if eff_tenant:
                pkey = self.partition_run_key(eff_tenant, run_id)
                got = await self._read_state_from_redis_hash_key(redis, pkey)
                if got is not None:
                    return got
            if _truthy_env("RUN_CONTROLLER_READ_LEGACY_KEYS", "1"):
                got = await self._read_state_from_redis_hash_key(redis, self._legacy_run_key(run_id))
                if got is not None:
                    return got
        except Exception as e:
            logger.warning("RunController read redis failed for %s: %s", run_id, e)
        return None

    async def update_step(
        self,
        run_id: str,
        step_name: str,
        status: str,
        error: str | None = None,
        cost_delta: float = 0.0,
    ) -> RunState | None:
        state = await self.get_run_state(run_id)
        if state is None:
            return None
        state.steps.append(
            {
                "step": step_name,
                "status": status,
                "error": error,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )
        state.cost = float(state.cost or 0.0) + float(cost_delta or 0.0)
        state.state = self._compute_overall_state(state.steps)
        await self.set_run_state(run_id, state)
        try:
            from src.core.alerting import on_run_controller_step

            await on_run_controller_step(state.tenant_id, run_id, step_name, status)
        except Exception as e:
            logger.debug("RunController alerting hook failed: %s", e)
        return state

    async def get_run_status(self, run_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
        state = await self.get_run_state(run_id, tenant_id=tenant_id)
        return asdict(state) if state else None

    async def get_recent_runs(self, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """
        Recent runs for a tenant (newest `started_at` first).
        Merges in-process `run_states` with Redis keys `tenant:{tenant_id}:*` (SCAN);
        legacy `run:*` is included only when RUN_CONTROLLER_SCAN_LEGACY_FOR_LIST=1.
        """
        lim = max(1, min(int(limit), 200))
        by_id: dict[str, RunState] = {}
        for rid, st in self.run_states.items():
            if st.tenant_id == tenant_id:
                by_id[rid] = st

        prefix = f"tenant:{tenant_id}:"
        redis = await self._redis_client()
        if redis is not None:
            try:
                async for key in redis.scan_iter(match=f"{prefix}*", count=200):
                    if not key.startswith(prefix):
                        continue
                    rid = key[len(prefix) :]
                    if not rid:
                        continue
                    st = await self.get_run_state(rid, tenant_id=tenant_id)
                    if st is None or st.tenant_id != tenant_id:
                        continue
                    by_id[rid] = st
                if _truthy_env("RUN_CONTROLLER_SCAN_LEGACY_FOR_LIST", "0"):
                    async for key in redis.scan_iter(match="run:*", count=200):
                        if not key.startswith("run:"):
                            continue
                        rid = key[4:]
                        if not rid:
                            continue
                        st = await self.get_run_state(rid)
                        if st is None or st.tenant_id != tenant_id:
                            continue
                        by_id[rid] = st
            except Exception as e:
                logger.warning("RunController get_recent_runs scan failed: %s", e)

        rows = list(by_id.values())
        rows.sort(key=lambda s: s.started_at or "", reverse=True)
        rows = rows[:lim]
        return [
            {
                "run_id": s.run_id,
                "state": s.state,
                "started_at": s.started_at,
                "steps_count": len(s.steps),
                "workflow_type": s.workflow_type,
                "trace_id": s.trace_id,
                "model": infer_llm_route_from_steps(s.steps),
                "cost": float(s.cost or 0.0),
            }
            for s in rows
        ]

    @staticmethod
    def parse_partitioned_run_key(key: str) -> tuple[str, str] | None:
        """Parse `tenant:{tenant_id}:{run_id}` → (tenant_id, run_id). Tenant id must not contain ':'."""
        if not key.startswith("tenant:"):
            return None
        rest = key[7:]
        idx = rest.find(":")
        if idx < 0:
            return None
        return rest[:idx], rest[idx + 1 :]

    async def list_run_ids_by_state(
        self,
        state_filter: str,
        limit: int = 50,
        *,
        tenant_id: str | None = None,
    ) -> list[str]:
        """
        Run ids whose aggregate `state` matches `state_filter`.
        If tenant_id is set, only SCAN `tenant:{tenant_id}:*`. If None, SCAN all `tenant:*` keys
        (plus legacy `run:*` when RUN_CONTROLLER_SCAN_LEGACY_FOR_LIST=1).
        """
        lim = max(1, min(int(limit), 200))
        target = (state_filter or "").lower()
        seen: set[str] = set()
        out: list[str] = []

        for rid, st in self.run_states.items():
            if tenant_id and st.tenant_id != tenant_id:
                continue
            if st.state.lower() == target and rid not in seen:
                out.append(rid)
                seen.add(rid)
                if len(out) >= lim:
                    return out[:lim]

        redis = await self._redis_client()
        if redis is not None:
            try:
                if tenant_id:
                    p = f"tenant:{tenant_id}:"
                    async for key in redis.scan_iter(match=f"{p}*", count=200):
                        if not key.startswith(p):
                            continue
                        rid = key[len(p) :]
                        if not rid or rid in seen:
                            continue
                        st = await self.get_run_state(rid, tenant_id=tenant_id)
                        if st is None or st.state.lower() != target:
                            continue
                        out.append(rid)
                        seen.add(rid)
                        if len(out) >= lim:
                            return out[:lim]
                else:
                    async for key in redis.scan_iter(match="tenant:*", count=200):
                        parsed = self.parse_partitioned_run_key(key)
                        if parsed is None:
                            continue
                        tid, rid = parsed
                        if not rid or rid in seen:
                            continue
                        st = await self.get_run_state(rid, tenant_id=tid)
                        if st is None or st.state.lower() != target:
                            continue
                        out.append(rid)
                        seen.add(rid)
                        if len(out) >= lim:
                            return out[:lim]
                    if _truthy_env("RUN_CONTROLLER_SCAN_LEGACY_FOR_LIST", "0"):
                        async for key in redis.scan_iter(match="run:*", count=200):
                            if not key.startswith("run:"):
                                continue
                            rid = key[4:]
                            if not rid or rid in seen:
                                continue
                            st = await self.get_run_state(rid)
                            if st is None or st.state.lower() != target:
                                continue
                            out.append(rid)
                            seen.add(rid)
                            if len(out) >= lim:
                                break
            except Exception as e:
                logger.warning("RunController list_run_ids_by_state scan failed: %s", e)

        return out[:lim]

    def _compute_overall_state(self, steps: list[dict[str, Any]]) -> str:
        if not steps:
            return "accepted"
        last_by_step: dict[str, str] = {}
        for s in steps:
            name = str(s.get("step", ""))
            if not name:
                continue
            last_by_step[name] = str(s.get("status", "")).lower()
        statuses = list(last_by_step.values())
        has_fail = any(s in ("failed", "error") for s in statuses)
        has_success = any(s in ("completed", "success") for s in statuses)
        has_processing = any(s in ("processing", "running") for s in statuses)
        if has_fail and has_success:
            return "partial"
        if has_fail:
            return "failed"
        if has_processing:
            return "processing"
        if all(s in ("completed", "success", "accepted") for s in statuses):
            return "completed"
        return "accepted"


_run_controller: RunController | None = None


def get_run_controller() -> RunController:
    global _run_controller
    if _run_controller is None:
        _run_controller = RunController()
    return _run_controller

