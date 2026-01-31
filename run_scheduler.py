#!/usr/bin/env python3
"""Run Brand OS v3 scheduler (daily job at 08:00)."""
from brand_os_scheduler.scheduler import start_scheduler

if __name__ == "__main__":
    start_scheduler()
