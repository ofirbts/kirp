# app/api/__init__.py - מייבא modules (לא routers!)
from . import health, ingest, ingest_batch, debug, query, tasks

__all__ = ['health', 'ingest', 'ingest_batch', 'debug', 'query', 'tasks']
