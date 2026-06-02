"""
Data integrity checks for KIRP Enterprise.

This script performs lightweight consistency checks across MongoDB and Postgres.

Usage:
    python scripts/data_integrity_check.py
"""

from __future__ import annotations

import os
from typing import Any

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import asyncpg


MONGO_URI = os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin")
POSTGRES_URI = os.getenv("POSTGRES_URI", "postgresql://kirp_user:kirp_password@localhost:5432/kirp")


async def check_mongo() -> None:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client["kirp"]

    print("Checking tasks / nodes (SchemaEngine projections live in Postgres; here we check event-derived docs)...")

    # Notifications: user/tenant fields sanity
    count_bad_notifications = await db.notifications.count_documents(
        {"$or": [{"tenant_id": {"$in": [None, ""]}}, {"user_id": {"$in": [None, ""]}}]}
    )
    if count_bad_notifications:
        print(f"  WARN: {count_bad_notifications} notifications missing tenant_id or user_id")
    else:
        print("  OK: all notifications have tenant_id and user_id")

    # History: tenant_id + created_at
    bad_history = await db.history.count_documents(
        {"$or": [{"tenant_id": {"$in": [None, ""]}}, {"created_at": {"$exists": False}}]}
    )
    if bad_history:
        print(f"  WARN: {bad_history} history entries missing tenant_id or created_at")
    else:
        print("  OK: all history entries have tenant_id and created_at")

    # Agent actions: tenant isolation
    bad_actions = await db.agent_actions.count_documents(
        {"$or": [{"tenant_id": {"$in": [None, ""]}}, {"status": {"$exists": False}}]}
    )
    if bad_actions:
        print(f"  WARN: {bad_actions} agent_actions missing tenant_id or status")
    else:
        print("  OK: all agent_actions have tenant_id and status")


async def check_postgres() -> None:
    print("Checking Postgres schema entities...")
    conn = await asyncpg.connect(POSTGRES_URI)
    try:
        # Basic checks on tasks / commitments / projects via generic nodes table.
        rows = await conn.fetch(
            "SELECT id, tenant_id, entity, parent_id, due_date FROM schema_nodes LIMIT 500"
        )
        missing_tenant = [r for r in rows if not r["tenant_id"]]
        if missing_tenant:
            print(f"  WARN: {len(missing_tenant)} nodes missing tenant_id")
        else:
            print("  OK: all sampled nodes have tenant_id")

        # Commitments should have due dates
        bad_commitments = [
            r for r in rows if r["entity"] == "commitment" and r["due_date"] is None
        ]
        if bad_commitments:
            print(f"  WARN: {len(bad_commitments)} commitments without due_date (sampled)")
        else:
            print("  OK: sampled commitments have due_date")
    finally:
        await conn.close()


async def main() -> None:
    await check_mongo()
    try:
        await check_postgres()
    except Exception as e:
        print(f"Postgres checks skipped or failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())

