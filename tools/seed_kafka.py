"""
Seed Kafka topics with synthetic events derived from seed/seed_definition.json.

This script is optional and assumes a Kafka broker is available and reachable.
It does not need to run for dashboards to work; the primary state is seeded via
the API and EventStore. Use this if you want live Kafka traffic for replay or
integration tests.
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

try:
  from kafka import KafkaProducer  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
  KafkaProducer = None  # type: ignore


SEED_PATH = Path(__file__).resolve().parent.parent / "seed" / "seed_definition.json"


def load_seed_definition() -> Dict[str, Any]:
  with SEED_PATH.open("r", encoding="utf-8") as f:
    return json.load(f)


def main() -> None:
  if KafkaProducer is None:
    raise SystemExit(
      "kafka-python is not installed. Install it with `pip install kafka-python` "
      "or skip running seed_kafka.py if you don't need Kafka seeding."
    )

  seed = load_seed_definition()
  topics = seed["topics"]
  broker = os.getenv("KAFKA_BROKER_URL", "localhost:9092")

  producer = KafkaProducer(
    bootstrap_servers=[broker],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
  )

  random.seed(42)

  for topic_cfg in topics:
    topic = topic_cfg["topic"]
    volume = int(topic_cfg.get("volumePerDay", 100))
    for idx in range(volume):
      payload = {
        "id": f"{topic}-{idx}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "severity": random.choice(list(topic_cfg.get("severity", {"info": 1.0}).keys())),
        "message": f"Synthetic event {idx} on {topic}",
      }
      producer.send(topic, value=payload)

  producer.flush()
  print("Seeded Kafka topics based on seed_definition.json")


if __name__ == "__main__":
  main()

