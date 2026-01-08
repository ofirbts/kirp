from typing import Dict
from app.models.trace import Trace, TraceEvent

_TRACE_STORE: Dict[str, Trace] = {}

def create_trace(question: str) -> Trace:
    trace = Trace(question=question)
    _TRACE_STORE[trace.trace_id] = trace
    return trace

def log_event(trace_id: str, event_type: str, payload: dict):
    trace = _TRACE_STORE.get(trace_id)
    if not trace:
        return
    trace.events.append(
        TraceEvent(type=event_type, payload=payload)
    )

def get_trace(trace_id: str) -> Trace | None:
    return _TRACE_STORE.get(trace_id)
