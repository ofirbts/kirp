"""
Metrics Agent — Writes to Elasticsearch / Prometheus bridge.

Emits metrics for observability.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.core.integrations import get_elasticsearch_client

logger = logging.getLogger(__name__)


@dataclass
class MetricRecord:
    """Single metric record."""

    name: str
    value: float
    labels: dict[str, str]
    timestamp: datetime | None = None


class MetricsAgent:
    """Metrics agent for Elasticsearch / observability."""

    INDEX = "kirp-metrics"

    def __init__(self) -> None:
        self.es = get_elasticsearch_client()
        self._ensure_index()

    def _ensure_index(self) -> None:
        """Create Elasticsearch index if missing."""
        if self.es is None:
            return
        try:
            if not self.es.indices.exists(index=self.INDEX):
                self.es.indices.create(index=self.INDEX, ignore=400)
                logger.info("MetricsAgent created index: %s", self.INDEX)
        except Exception as e:
            logger.error("MetricsAgent index creation failed: %s", e)

    def emit(self, metric: MetricRecord) -> bool:
        """Emit metric to Elasticsearch."""
        if self.es is None:
            logger.warning("Elasticsearch not available")
            return False
        try:
            doc = {
                "name": metric.name,
                "value": metric.value,
                "labels": metric.labels,
                "timestamp": (metric.timestamp or datetime.now(timezone.utc)).isoformat(),
            }
            self.es.index(index=self.INDEX, document=doc)
            logger.debug("MetricsAgent emitted: %s = %s", metric.name, metric.value)
            return True
        except Exception as e:
            logger.error("MetricsAgent emit failed: %s", e)
            return False
