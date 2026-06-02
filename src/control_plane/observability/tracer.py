from __future__ import annotations

import contextvars

_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("cp_trace_id", default=None)


def set_trace_id(trace_id: str | None) -> contextvars.Token[str | None]:
    return _trace_id.set(trace_id)


def get_trace_id() -> str | None:
    return _trace_id.get()


def reset_trace_id(token: contextvars.Token[str | None]) -> None:
    _trace_id.reset(token)
