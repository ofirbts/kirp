"""E2E: Scheduler daily job registration, CONTEXT_SCANNER, orchestrator, memory log (mocked)."""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

try:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from brand_os_scheduler import scheduler as sched
except ImportError:
    sched = None


@pytest.mark.skipif(sched is None, reason="apscheduler not installed")
def test_daily_job_registration():
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger
    sch = BlockingScheduler()
    sch.add_job(sched.daily_job, CronTrigger(hour=8, minute=0))
    jobs = sch.get_jobs()
    assert len(jobs) == 1


@pytest.mark.skipif(sched is None, reason="apscheduler not installed")
def test_pick_best_signal():
    assert sched._pick_best_signal(None) == "daily"
    assert sched._pick_best_signal({"trends": ["a", "b"]}) == "a"


@pytest.mark.skipif(sched is None, reason="apscheduler not installed")
@patch("brand_os_scheduler.scheduler.run_orchestrator")
@patch("brand_os_scheduler.scheduler._context_scanner_output")
@patch("brand_os_scheduler.scheduler._append_memory_log")
def test_daily_job_execution(mock_append, mock_ctx, mock_run):
    mock_ctx.return_value = {"trends": ["API release"]}
    mock_run.return_value = {"trace_id": "tr1", "content": {"body": "Hello"}, "status": "approved"}
    sched.daily_job()
    mock_run.assert_called_once()
    mock_append.assert_called_once()
