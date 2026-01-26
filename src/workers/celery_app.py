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
    },
)
