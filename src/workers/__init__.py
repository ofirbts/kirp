"""Celery workers — ingest, WhatsApp, notifications, agent triggers."""

# Don't import tasks here to avoid circular imports
# Celery will discover tasks automatically via include=["src.workers.tasks"] in celery_app.py

__all__ = ["celery_app"]
