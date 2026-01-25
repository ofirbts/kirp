"""
OpenTelemetry traces — Spans for pipeline, RAG, agents, integrations.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger(__name__)

_tracer: Any = None


def get_tracer(name: str = "kirp", version: str = "0.1.0") -> Any:
    """Return OTel tracer. Lazy init."""
    global _tracer
    if _tracer is not None:
        return _tracer
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(name, version)
        logger.info("OpenTelemetry tracer initialized")
        return _tracer
    except ImportError:
        logger.warning("opentelemetry not installed; tracing no-op")
        _tracer = None
        return None


@contextmanager
def span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    """Context manager for a trace span."""
    t = get_tracer()
    if t is None:
        yield None
        return
    with t.start_as_current_span(name) as s:
        if attributes:
            for k, v in attributes.items():
                s.set_attribute(k, str(v))
        yield s
