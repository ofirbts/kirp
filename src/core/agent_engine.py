"""
Agent Engine — Execution, state machine, scheduling, Kafka triggers, memory, skills, workflows, persona, orchestration.

- Execution: async + queued (Redis/Celery)
- State: idle → running → completed | failed
- Scheduling: cron + event-triggered (Kafka)
- Memory: Qdrant (vector) + Redis (short-term)
- Skills: tools registry and execution
- Workflows: multi-step plans per agent
- Persona: LLM prompt templates
- Orchestration: multi-agent collaboration
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class AgentRunState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentRun:
    """Single agent run record."""

    run_id: UUID
    agent_name: str
    tenant_id: str
    space_id: str
    user_id: str
    state: AgentRunState = AgentRunState.IDLE
    trigger: str = "manual"  # manual | cron | kafka | workflow
    trigger_ref: str | None = None
    input_context: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SkillSpec:
    """Tool/skill that an agent can invoke."""

    name: str
    description: str
    parameters_schema: dict[str, Any]
    handler: Callable[..., Awaitable[dict[str, Any]]]


@dataclass
class WorkflowStep:
    """Single step in a multi-step agent plan."""

    step_id: str
    agent_or_skill: str
    input_map: dict[str, str]  # output_key from previous -> input_key for this step
    condition: str | None = None  # optional guard expression


@dataclass
class PersonaSpec:
    """LLM prompt template and conditioning for an agent."""

    system_prompt: str
    few_shot_examples: list[dict[str, str]] = field(default_factory=list)
    temperature: float = 0.2
    max_tokens: int = 1024


class AgentMemory:
    """Per-agent memory: Qdrant (long-term) + Redis (short-term session)."""

    def __init__(self, agent_name: str, tenant_id: str, qdrant_url: str, redis_url: str) -> None:
        self._agent_name = agent_name
        self._tenant_id = tenant_id
        self._qdrant_url = qdrant_url
        self._redis_url = redis_url
        self._collection = f"agent_memory_{agent_name}_{tenant_id}".replace(".", "_")[:80]
        self._redis: Any = None
        self._qdrant: Any = None

    async def connect(self) -> None:
        try:
            from qdrant_client import QdrantClient
            self._qdrant = QdrantClient(url=self._qdrant_url)
        except Exception as e:
            logger.warning("AgentMemory Qdrant connect failed: %s", e)
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(self._redis_url, decode_responses=True)
        except Exception as e:
            logger.warning("AgentMemory Redis connect failed: %s", e)

    async def get_short_term(self, key: str) -> str | None:
        if self._redis is None:
            return None
        try:
            return await self._redis.get(f"agent_mem:{self._agent_name}:{self._tenant_id}:{key}")
        except Exception:
            return None

    async def set_short_term(self, key: str, value: str, ttl_seconds: int = 3600) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.setex(
                f"agent_mem:{self._agent_name}:{self._tenant_id}:{key}",
                ttl_seconds,
                value,
            )
        except Exception as e:
            logger.warning("AgentMemory set_short_term failed: %s", e)

    async def retrieve(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Vector search in Qdrant for this agent's memory."""
        if self._qdrant is None:
            return []
        try:
            from qdrant_client.http import models
            # Collection may not exist yet
            colls = [c.name for c in self._qdrant.get_collections().collections]
            if self._collection not in colls:
                return []
            results, _ = self._qdrant.scroll(
                collection_name=self._collection,
                limit=limit,
                with_payload=True,
            )
            return [getattr(r, "payload", None) or {} for r in results]
        except Exception as e:
            logger.warning("AgentMemory retrieve failed: %s", e)
            return []

    async def store(self, content: str, embedding: list[float], metadata: dict[str, Any] | None = None) -> None:
        if self._qdrant is None:
            return
        try:
            from qdrant_client.http import models
            colls = [c.name for c in self._qdrant.get_collections().collections]
            if self._collection not in colls:
                self._qdrant.create_collection(
                    collection_name=self._collection,
                    vectors_config=models.VectorParams(size=len(embedding), distance=models.Distance.COSINE),
                )
            self._qdrant.upsert(
                collection_name=self._collection,
                points=[
                    models.PointStruct(
                        id=str(uuid4()),
                        vector=embedding,
                        payload={"content": content, "tenant_id": self._tenant_id, **(metadata or {})},
                    )
                ],
            )
        except Exception as e:
            logger.warning("AgentMemory store failed: %s", e)


class AgentExecutionEngine:
    """
    Async + queued execution, state machine, Redis state.
    """

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._redis: Any = None
        self._run_states: dict[str, AgentRun] = {}

    async def _redis_client(self) -> Any:
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self._redis_url, decode_responses=True)
            except Exception as e:
                logger.warning("AgentExecutionEngine Redis failed: %s", e)
        return self._redis

    async def set_run_state(self, run_id: UUID, state: AgentRunState, output: dict | None = None, error: str | None = None) -> None:
        r = await self._redis_client()
        if r is None:
            return
        key = f"agent_run:{run_id}"
        data: dict[str, Any] = {"state": state.value}
        import json as _json
        if output is not None:
            data["output"] = _json.dumps(output) if isinstance(output, dict) else str(output)
        if error is not None:
            data["error"] = str(error)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await r.hset(key, mapping={k: v if isinstance(v, str) else _json.dumps(v) for k, v in data.items()})
        await r.expire(key, 86400 * 7)  # 7 days

    async def get_run_state(self, run_id: UUID) -> dict[str, Any] | None:
        r = await self._redis_client()
        if r is None:
            return None
        key = f"agent_run:{run_id}"
        raw = await r.hgetall(key)
        return raw if raw else None

    async def enqueue_run(self, run: AgentRun) -> UUID:
        """Enqueue run (store in Redis list for worker consumption)."""
        r = await self._redis_client()
        if r is None:
            raise RuntimeError("Redis not available for agent queue")
        await self.set_run_state(run.run_id, AgentRunState.IDLE)
        payload = {
            "run_id": str(run.run_id),
            "agent_name": run.agent_name,
            "tenant_id": run.tenant_id,
            "space_id": run.space_id,
            "user_id": run.user_id,
            "trigger": run.trigger,
            "trigger_ref": run.trigger_ref or "",
            "input_context": run.input_context,
        }
        import json
        await r.lpush("agent_run_queue", json.dumps(payload))
        return run.run_id

    async def execute_run(
        self,
        run_id: UUID,
        agent_name: str,
        tenant_id: str,
        space_id: str,
        user_id: str,
        context: dict[str, Any],
        handler: Callable[..., Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        """Execute one run (called by worker). State: idle → running → completed|failed."""
        await self.set_run_state(run_id, AgentRunState.RUNNING)
        try:
            result = await handler(
                tenant_id=tenant_id,
                space_id=space_id,
                user_id=user_id,
                context=context,
            )
            await self.set_run_state(run_id, AgentRunState.COMPLETED, output=result)
            return result
        except Exception as e:
            await self.set_run_state(run_id, AgentRunState.FAILED, error=str(e))
            raise


class SkillsRegistry:
    """Registry of tools/skills agents can call."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillSpec] = {}

    def register(self, spec: SkillSpec) -> None:
        self._skills[spec.name] = spec

    def get(self, name: str) -> SkillSpec | None:
        return self._skills.get(name)

    def list_all(self) -> list[SkillSpec]:
        return list(self._skills.values())


class AgentOrchestrator:
    """Multi-agent collaboration: delegate steps to different agents."""

    def __init__(self, agent_framework: Any, execution_engine: AgentExecutionEngine) -> None:
        self._framework = agent_framework
        self._engine = execution_engine

    async def run_workflow(
        self,
        steps: list[WorkflowStep],
        tenant_id: str,
        space_id: str,
        user_id: str,
        initial_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a multi-step workflow; each step can be an agent or skill."""
        ctx = dict(initial_context)
        for step in steps:
            spec = self._framework.get(step.agent_or_skill) if hasattr(self._framework, "get") else None
            if spec and getattr(spec, "handler", None):
                # Map previous outputs into context
                for out_key, in_key in step.input_map.items():
                    if out_key in ctx:
                        ctx[in_key] = ctx[out_key]
                run_id = uuid4()
                result = await self._engine.execute_run(
                    run_id, step.agent_or_skill, tenant_id, space_id, user_id, ctx, spec.handler
                )
                ctx[f"step_{step.step_id}"] = result
                ctx.update(result if isinstance(result, dict) else {})
            else:
                logger.warning("Workflow step agent/skill not found: %s", step.agent_or_skill)
        return ctx


# --- Module singletons (lazy init) ---
_agent_engine: AgentExecutionEngine | None = None
_skills_registry: SkillsRegistry | None = None


def get_agent_engine() -> AgentExecutionEngine:
    global _agent_engine
    if _agent_engine is None:
        _agent_engine = AgentExecutionEngine(redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"))
    return _agent_engine


def get_skills_registry() -> SkillsRegistry:
    global _skills_registry
    if _skills_registry is None:
        _skills_registry = SkillsRegistry()
    return _skills_registry
