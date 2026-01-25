"""
Prometheus metrics — Counters, gauges, histograms.

Used by API, workers, agents, RAG, event pipeline.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Gauge, Histogram
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = Gauge = Histogram = None  # type: ignore


class MetricsCollector:
    """Prometheus-backed metrics. Namespace prefix: kirp_."""

    def __init__(self, namespace: str = "kirp") -> None:
        self._ns = namespace
        if not PROMETHEUS_AVAILABLE:
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
        if not PROMETHEUS_AVAILABLE:
            return
        k = self._key(name)
        if k not in self._counters:
            self._counters[k] = Counter(k, name, list(labels.keys()) if labels else [])
        self._counters[k].labels(**(labels or {})).inc(value)

    def gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set gauge."""
        if not PROMETHEUS_AVAILABLE:
            return
        k = self._key(name)
        if k not in self._gauges:
            self._gauges[k] = Gauge(k, name, list(labels.keys()) if labels else [])
        self._gauges[k].labels(**(labels or {})).set(value)

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Observe histogram (e.g. latency)."""
        if not PROMETHEUS_AVAILABLE:
            return
        k = self._key(name)
        if k not in self._histograms:
            self._histograms[k] = Histogram(k, name, list(labels.keys()) if labels else [])
        self._histograms[k].labels(**(labels or {})).observe(value)
