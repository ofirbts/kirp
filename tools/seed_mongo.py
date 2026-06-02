"""
Seed event data via the public ingest API, populating MongoDB, Qdrant, and
downstream projections through the EventPipeline.

This script:
- Reads seed/seed_definition.json
- Synthesizes events over the last N days per tenant/space/topic
- Calls POST /api/v1/ingest with realistic content

Notes:
- Requires a user with WRITE permission on "event" for each tenant/space
  (or use user_id=system-seed with ENV=development/local for RBAC bypass).
- Assumes the KIRP API is running and reachable.

To avoid OpenAI usage during seeding, set on the API (e.g. in .env or
docker-compose environment):
  PIPELINE_SEED_MODE=true
This skips embeddings, schema extraction, agents, and governance in the
ingest pipeline so events are stored in Mongo (and optionally Kafka) only.
You can later run seed_qdrant to backfill embeddings, or set
DISABLE_EMBEDDINGS, DISABLE_SCHEMA_EXTRACTION, DISABLE_AGENTS, DISABLE_GOVERNANCE
individually.
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import httpx


SEED_PATH = Path(__file__).resolve().parent.parent / "seed" / "seed_definition.json"


def load_seed_definition() -> Dict[str, Any]:
  with SEED_PATH.open("r", encoding="utf-8") as f:
    return json.load(f)


def pick_with_distribution(options: List[Tuple[str, float]]) -> str:
  r = random.random()
  acc = 0.0
  for value, weight in options:
    acc += weight
    if r <= acc:
      return value
  return options[-1][0]


def build_synthetic_events(seed: Dict[str, Any]) -> List[Dict[str, Any]]:
  tenants = seed["tenants"]
  topics = seed["topics"]
  event_types = seed.get("eventTypes", [])
  volume_cfg = seed["volumeTargets"]["perTenant"]
  events_range = volume_cfg["events_30_days"]
  total_days = int(seed.get("timeHorizon", {}).get("days", 30))
  spikes = seed.get("timeHorizon", {}).get("spikes", [])

  now = datetime.now(timezone.utc)
  start = now - timedelta(days=total_days)

  events: List[Dict[str, Any]] = []

  for tenant in tenants:
    tenant_id = tenant["id"]
    for space in tenant.get("spaces", []):
      space_id = space["id"]
      target_events = random.randint(events_range[0], events_range[1])
      per_day = max(1, target_events // total_days)

      for day_idx in range(total_days):
        day = start + timedelta(days=day_idx)
        day_multiplier = 1.0
        for spike in spikes:
          if spike.get("day") == day_idx + 1:
            # modest 2x multiplier on spike days
            day_multiplier = 2.0
        day_events = int(per_day * day_multiplier)

        for _ in range(day_events):
          topic_cfg = random.choice(topics)
          topic = topic_cfg["topic"]
          sev_dist = topic_cfg.get("severity", {"info": 1.0})
          severity = pick_with_distribution(list(sev_dist.items()))

          # Match an event type if possible
          matching_types = [et for et in event_types if et.get("topic") == topic]
          et = random.choice(matching_types) if matching_types else None

          ts = day + timedelta(
            seconds=random.randint(0, 23 * 3600 + 59 * 60),
          )
          payload_preview = ""
          if et:
            if et["eventType"] == "rag.query.executed":
              payload_preview = "RAG query executed for tenant insights"
            elif et["eventType"] == "security.alert.raised":
              payload_preview = "Security alert raised in environment"
            else:
              payload_preview = f"Event {et['eventType']} on topic {topic}"
          else:
            payload_preview = f"{topic} event ({severity})"

          events.append(
            {
              "tenant_id": tenant_id,
              "space_id": space_id,
              "severity": severity,
              "topic": topic,
              "timestamp": ts,
              "payload_preview": payload_preview,
            }
          )

  return events


async def run(base_url: str, token: str | None = None) -> None:
  seed = load_seed_definition()
  events = build_synthetic_events(seed)

  headers: Dict[str, str] = {"Content-Type": "application/json"}
  if token:
    headers["Authorization"] = f"Bearer {token}"

  url = base_url.rstrip("/") + "/api/v1/ingest"

  async with httpx.AsyncClient(timeout=30.0) as client:
    for ev in events:
      body = {
        "tenant_id": ev["tenant_id"],
        "space_id": ev["space_id"],
        "user_id": "system-seed",
        "source": "seed-script",
        "content": (
          f"[{ev['topic']}] {ev['payload_preview']} "
          f"(severity={ev['severity']}, ts={ev['timestamp'].isoformat()})"
        ),
      }
      try:
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()
      except Exception as exc:  # pragma: no cover - best-effort seeding
        print("Ingest failed for event", ev, "error:", exc)

  print(f"Seeded {len(events)} events via /api/v1/ingest")


def main() -> None:
  import asyncio

  random.seed(42)
  base_url = os.getenv("KIRP_API_BASE_URL", "http://localhost:8000")
  token = os.getenv("KIRP_API_TOKEN")
  asyncio.run(run(base_url=base_url, token=token))


if __name__ == "__main__":
  main()

