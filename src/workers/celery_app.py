"""
Celery app — Workers for ingest, WhatsApp, notifications, agent triggers.

Broker: Redis. Backend: Redis.
"""

from __future__ import annotations

import os
import logging
from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

broker = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/1"))
backend = os.getenv("CELERY_RESULT_BACKEND", broker)

# Log broker/backend for diagnostics
logger.info("Celery broker: %s", broker)
logger.info("Celery backend: %s", backend)

celery_app = Celery(
    "kirp",
    broker=broker,
    backend=backend,
    include=["src.workers.tasks"],
)

# Note: Tasks are auto-discovered by Celery when the module is loaded
# No need to import them here (would cause circular import with tasks.py)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "src.workers.tasks.ingest_task": {"queue": "ingest"},
        "src.workers.tasks.whatsapp_send_task": {"queue": "whatsapp"},
        "src.workers.tasks.daily_intelligence_task": {"queue": "scheduled"},
        "src.workers.tasks.self_improvement_task": {"queue": "scheduled"},
        "src.workers.tasks.demo_data_generator_task": {"queue": "scheduled"},
        "src.workers.tasks.refresh_missing_embeddings_task": {"queue": "scheduled"},
        "src.workers.tasks.agent_run_task": {"queue": "agents"},
        "src.workers.tasks.drain_agent_queue_task": {"queue": "agents"},
        "src.workers.tasks.gmail_sync_task": {"queue": "ingest"},
        "src.workers.tasks.calendar_sync_task": {"queue": "ingest"},
        "src.workers.tasks.slack_sync_task": {"queue": "ingest"},
        "src.workers.tasks.notion_sync_task": {"queue": "ingest"},
        "src.workers.tasks.reminder_run_task": {"queue": "scheduled"},
    },
    beat_schedule={
        "daily-intelligence-08:00": {
            "task": "daily_intelligence_task",
            "schedule": crontab(hour=8, minute=0),
            "args": ("ofir", "default", "private"),
        },
        "self-improvement-daily": {
            "task": "self_improvement_task",
            "schedule": crontab(hour=2, minute=0),
            "args": ("default",),
        },
        "refresh-embeddings-hourly": {
            "task": "refresh_missing_embeddings_task",
            "schedule": crontab(minute=0),
            "args": ("default-tenant", None, 500),
        },
        "drain-agent-queue": {
            "task": "drain_agent_queue_task",
            "schedule": 10.0,
            "args": (),
        },
        "notion-sync-quarterly": {
            "task": "notion_sync_task",
            "schedule": crontab(minute=0, hour="*/2"),
            "args": ("default", "all", "system"),
        },
        "gmail-sync-hourly": {
            "task": "gmail_sync_task",
            "schedule": crontab(minute=5, hour="*"),
            "args": ("default", "all", "system", 50),
        },
        "calendar-sync-hourly": {
            "task": "calendar_sync_task",
            "schedule": crontab(minute=10, hour="*"),
            "args": ("default", "all", "system", 100),
        },
        "reminder-run-hourly": {
            "task": "reminder_run_task",
            "schedule": crontab(minute=30, hour="*"),
            "kwargs": {"tenant_id": "default", "space_id": "all", "user_id": "system", "horizon_days": 7},
        },
    },
)
