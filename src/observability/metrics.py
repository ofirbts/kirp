"""
Prometheus metrics — Counters, gauges, histograms.

Used by API, workers, agents, RAG, event pipeline.
When DISABLE_PROMETHEUS=1, all metrics are no-op (avoids multiprocess conflicts).
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_DISABLED = os.getenv("DISABLE_PROMETHEUS", "").lower() in ("1", "true", "yes")

try:
    from prometheus_client import Counter, Gauge, Histogram
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = Gauge = Histogram = None  # type: ignore


def _metrics_enabled() -> bool:
    return not _DISABLED and PROMETHEUS_AVAILABLE


class MetricsCollector:
    """Prometheus-backed metrics. Namespace prefix: kirp_."""

    def __init__(self, namespace: str = "kirp") -> None:
        self._ns = namespace
        if not _metrics_enabled():
            if _DISABLED:
                logger.debug("Prometheus disabled (DISABLE_PROMETHEUS=1); metrics no-op")
            else:
                logger.warning("prometheus_client not installed; metrics no-op")
            self._counters: dict[str, Any] = {}
            self._gauges: dict[str, Any] = {}
            self._histograms: dict[str, Any] = {}
            return
        self._counters = {}
        self._gauges = {}
        self._histograms = {}

    def _key(self, name: str) -> str:
        return f"{self._ns}_{name}"

    def inc(self, name: str, value: int = 1, labels: dict[str, str] | None = None) -> None:
        """Increment counter."""
        if not _metrics_enabled():
            return
        k = self._key(name)
        if k not in self._counters:
            self._counters[k] = Counter(k, name, list(labels.keys()) if labels else [])
        self._counters[k].labels(**(labels or {})).inc(value)

    def gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set gauge."""
        if not _metrics_enabled():
            return
        k = self._key(name)
        if k not in self._gauges:
            self._gauges[k] = Gauge(k, name, list(labels.keys()) if labels else [])
        self._gauges[k].labels(**(labels or {})).set(value)

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Observe histogram (e.g. latency). With no labels use .observe() directly."""
        if not _metrics_enabled():
            return
        k = self._key(name)
        if k not in self._histograms:
            label_list = list(labels.keys()) if labels else []
            self._histograms[k] = Histogram(k, name, label_list)
        h = self._histograms[k]
        if labels:
            h.labels(**labels).observe(value)
        else:
            h.observe(value)


def normalize_path_for_metrics(path: str) -> str:
    """
    Reduce path cardinality for metrics: replace UUIDs and numeric IDs with _id_.
    """
    import re
    segments = path.strip("/").split("/")
    out = []
    uuid_re = re.compile(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )
    for seg in segments:
        if uuid_re.match(seg) or (seg.isdigit() and len(seg) <= 20):
            out.append("_id_")
        else:
            out.append(seg)
    return "/" + "/".join(out) if out else "/"
