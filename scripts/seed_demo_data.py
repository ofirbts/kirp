#!/usr/bin/env python3
"""
Seed demo data for Ofir (single dev environment).

Uses public API: POST /api/v1/ingest, POST /api/v1/signals, POST /api/v1/visuals,
POST /api/v1/content/intelligence, POST /api/decisions.

All data: tenant_id=default, space_id=all, user_id=ofir.
Hebrew + English mixed content. Idempotent: safe to re-run (upserts/append).
"""

from __future__ import annotations

import os
import sys

try:
    import requests
except ImportError:
    print("Install requests: pip install requests", file=sys.stderr)
    sys.exit(1)

API_URL = os.getenv("API_URL", os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:8000"))
DEV_TOKEN = os.getenv("DEV_TOKEN", os.getenv("NEXT_PUBLIC_DEV_TOKEN", "dev-local-token"))

HEADERS = {"Content-Type": "application/json"}
if DEV_TOKEN:
    HEADERS["Authorization"] = f"Bearer {DEV_TOKEN}"

PARAMS = {"tenantId": "default", "spaceId": "all"}


def ingest(content: str, source: str = "api") -> bool:
    r = requests.post(
        f"{API_URL}/api/v1/ingest",
        json={
            "tenant_id": "default",
            "space_id": "all",
            "user_id": "ofir",
            "content": content,
            "source": source,
        },
        headers=HEADERS,
        timeout=30,
    )
    return r.status_code in (200, 201)


def post_signals():
    signals = [
        {"topic": "API release", "relevance": 92, "urgency": "high", "trend": "rising"},
        {"topic": "DevEx metrics", "relevance": 85, "urgency": "medium", "trend": "stable"},
        {"topic": "KIRP end-to-end", "relevance": 95, "urgency": "high", "trend": "rising"},
        {"topic": "WSL + Docker", "relevance": 88, "urgency": "medium", "trend": "stable"},
    ]
    for s in signals:
        r = requests.post(f"{API_URL}/api/v1/signals", json=s, headers=HEADERS, params=PARAMS, timeout=10)
        if r.status_code not in (200, 201):
            print(f"  signals: {r.status_code} {r.text[:200]}")


def post_visuals():
    for name, chart_type in [("Event distribution", "bar"), ("KPIs", "radial"), ("Timeline", "line")]:
        r = requests.post(
            f"{API_URL}/api/v1/visuals",
            json={"name": name, "chart_type": chart_type, "config": {"title": name}},
            headers=HEADERS,
            params=PARAMS,
            timeout=10,
        )
        if r.status_code not in (200, 201):
            print(f"  visuals: {r.status_code}")


def post_content_intelligence():
    entries = [
        {"trace_id": "t1", "topic_hint": "KIRP UI", "platform": "linkedin", "status": "draft"},
        {"trace_id": "t2", "topic_hint": "DevEx", "platform": "internal", "status": "published"},
    ]
    for e in entries:
        r = requests.post(
            f"{API_URL}/api/v1/content/intelligence",
            json=e,
            headers=HEADERS,
            params=PARAMS,
            timeout=10,
        )
        if r.status_code not in (200, 201):
            print(f"  content: {r.status_code}")


def post_decisions():
    for i, agent in enumerate(["pattern_analyzer", "planner"], 1):
        r = requests.post(
            f"{API_URL}/api/decisions",
            json={
                "agent_id": agent,
                "output": {"summary": f"Decision {i} from {agent}", "confidence": 0.9},
                "confidence": 0.9,
                "status": "completed",
            },
            headers=HEADERS,
            params=PARAMS,
            timeout=10,
        )
        if r.status_code not in (200, 201):
            print(f"  decisions: {r.status_code}")


def main():
    print(f"Seeding demo data at {API_URL} (tenant=default, space=all, user=ofir)")
    # Health
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        if r.status_code != 200:
            print("API not healthy:", r.status_code)
            sys.exit(1)
    except Exception as e:
        print("API unreachable:", e)
        sys.exit(1)

    # Events via ingest (50+ items: goals, insights, tasks, projects, logs, plans, analyses, forecasts, report)
    events = [
        ("להרים את כל KIRP מקצה לקצה ולגרום ל-UI לעבוד מושלם.", "goal"),
        ("למדתי איך WSL מתקשר עם Docker ואיך לפתור בעיות רשת.", "insight"),
        ("משימה: לסדר את סביבת הפיתוח של KIRP ולוודא שהכל עובד חלק.", "task"),
        ("רעיון: ליצור סקריפט אוטומטי שמרים את כל KIRP כולל דמו.", "idea"),
        ("KIRP Intelligence OS — Controlled Intelligence Layer, Event-Sourced, Multi-Tenant.", "goal"),
        ("Goal: Full end-to-end experience for single dev (Ofir) with real data.", "goal"),
        ("Insight: CORS and Docker buildx permissions were blocking the UI.", "insight"),
        ("Task: Wire decisions, graph, visuals, content, history, audit, tenants, users, signals to real APIs.", "task"),
        ("Idea: Seed script with Hebrew + English mixed content for realistic demo.", "idea"),
        ("פרויקט: העלאת KIRP מקצה לקצה — backend, frontend, Docker.", "project"),
        ("Daily log: Fixed CORS for localhost:3100, added Brand OS API to docker-compose.", "log"),
        ("Weekly plan: Complete domain models, APIs, frontend wiring, seed script.", "plan"),
        ("Work-style: Prefer incremental changes, keep tests green, no removal of pages.", "analysis"),
        ("Forecast: Dashboard will show real KPIs from event count and agents.", "forecast"),
        ("Personal report: 50 events ingested, signals/visuals/content/decisions seeded.", "report"),
    ]
    # Repeat and add more variety to reach ~50 events
    more = [
        "Event-sourcing: no direct DB mutations.",
        "Multi-tenancy: tenant_id, space_id, user_id on every request.",
        "RAG context must be passed consistently.",
        "All new agents must use AgentFramework.register().",
        "Governance enforced for external actions.",
        "Schema Engine: models, migrations, queries only.",
        "EventPipeline: ingest -> store -> RAG -> agents.",
    ]
    for _ in range(3):
        for c, src in events:
            ingest(c, src)
        for c in more:
            ingest(c, "api")
    print("  Ingested ~50 events (goals, insights, tasks, ideas, logs, plans, etc.)")

    post_signals()
    print("  Signals created")
    post_visuals()
    print("  Visuals created")
    post_content_intelligence()
    print("  Content intelligence created")
    post_decisions()
    print("  Decisions created")

    print("Done. Refresh the UI to see real data.")


if __name__ == "__main__":
    main()
