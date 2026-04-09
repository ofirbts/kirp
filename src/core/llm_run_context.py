"""
Context for attributing LLM invocations to a RunController run_id (timeline steps).

Set around code that calls LLMClient.invoke while a pipeline run is active.
"""

from __future__ import annotations

import contextvars

_llm_run_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("llm_run_id", default=None)
_llm_tenant_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("llm_tenant_id", default=None)


def set_llm_run_id(run_id: str | None) -> contextvars.Token[str | None]:
    return _llm_run_id.set(run_id)


def reset_llm_run_id(token: contextvars.Token[str | None]) -> None:
    _llm_run_id.reset(token)


def get_llm_run_id() -> str | None:
    return _llm_run_id.get()


def set_llm_tenant_id(tenant_id: str | None) -> contextvars.Token[str | None]:
    return _llm_tenant_id.set(tenant_id)


def reset_llm_tenant_id(token: contextvars.Token[str | None]) -> None:
    _llm_tenant_id.reset(token)


def get_llm_tenant_id() -> str | None:
    return _llm_tenant_id.get()
