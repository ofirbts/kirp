"""
Seed Qdrant embeddings for existing events using the backend RAG engine.

This script:
- Connects to the EventStore and RAGEngine using the same configuration as the API
- Finds events without embeddings in the last N days
- Generates embeddings and upserts them into Qdrant

It is effectively an on-demand version of the refresh_missing_embeddings_task.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List


def _env(key: str, default: str) -> str:
  return os.environ.get(key, default)


async def run(days: int = 30, limit: int = 1000) -> None:
  # Use env vars only so this script runs without pydantic_settings (e.g. host Python).
  mongo_uri = _env("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin")
  qdrant_url = _env("QDRANT_URL", "http://localhost:6333")
  qdrant_collection = _env("QDRANT_COLLECTION", "kirp_vectors")

  try:
    from src.core.config import get_settings
    settings = get_settings()
    mongo_uri = settings.mongo_uri
    qdrant_url = settings.qdrant_url
    qdrant_collection = settings.qdrant_collection
  except Exception:
    pass  # Use env defaults above

  from src.core.event_store import EventStore
  from src.core.rag_engine import RAGEngine

  store = EventStore(mongo_uri)
  await store.connect()

  rag = RAGEngine(qdrant_url=qdrant_url, collection=qdrant_collection)
  await rag.connect()
  if getattr(rag, "_embedder", None) is None:
    print("OPENAI_API_KEY not set; skipping embedding seed. Set OPENAI_API_KEY to populate Qdrant embeddings.")
    return

  since = datetime.now(timezone.utc) - timedelta(days=days)

  db = store._db  # type: ignore[attr-defined]

  # For simplicity, we refresh embeddings across all tenants/spaces.
  q: Dict[str, Any] = {"embedding": [], "timestamp": {"$gte": since}}
  cursor = db.events.find(q).sort("timestamp", -1).limit(limit)
  docs: List[Dict[str, Any]] = await cursor.to_list(length=limit)

  points: List[Dict[str, Any]] = []
  for doc in docs:
    tenant_id = doc.get("tenant_id")
    space_id = doc.get("space_id") or "default"
    content = doc.get("content") or doc.get("payload") or ""
    if not content:
      continue
    try:
      emb = await rag.embed(str(content))
    except Exception as exc:  # pragma: no cover - best-effort
      print("Embedding failed for", doc.get("_id"), "error:", exc)
      continue
    doc["embedding"] = emb
    points.append(
      {
        "id": doc["_id"],
        "embedding": emb,
        "content": content,
        "source": doc.get("source", "unknown"),
        "user_id": doc.get("user_id", ""),
        "tenant_id": tenant_id,
        "space_id": space_id,
      }
    )

  # Group by tenant/space for upserts
  by_scope: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
  for p in points:
    key = (p["tenant_id"], p["space_id"])
    by_scope.setdefault(key, []).append(p)

  for (tenant_id, space_id), scoped_points in by_scope.items():
    await rag.upsert(scoped_points, tenant_id=tenant_id, space_id=space_id)
    # Persist updated embeddings back to Mongo
    for p in scoped_points:
      await db.events.update_one({"_id": p["id"]}, {"$set": {"embedding": p["embedding"]}})

  print(f"Seeded embeddings for {len(points)} events into Qdrant")


def main() -> None:
  days = int(os.getenv("KIRP_SEED_QDRANT_DAYS", "30"))
  limit = int(os.getenv("KIRP_SEED_QDRANT_LIMIT", "1000"))
  asyncio.run(run(days=days, limit=limit))


if __name__ == "__main__":
  main()

