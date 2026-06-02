from __future__ import annotations

from src.observability.metrics import MetricsCollector

_collector = MetricsCollector(namespace="kirp_control_plane")


def inc(name: str, value: int = 1, labels: dict[str, str] | None = None) -> None:
    _collector.inc(name, value=value, labels=labels)
