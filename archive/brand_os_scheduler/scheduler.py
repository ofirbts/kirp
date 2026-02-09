"""
Brand OS v3 scheduler — daily job at 08:00.
Steps: CONTEXT_SCANNER → pick best signal → run_orchestrator → send_whatsapp (optional) → append Content Memory Log.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

try:
    from brand_os_sdk import run_orchestrator
    from brand_os_sdk.config_loader import _base_path, _read_json
    from brand_os_sdk.orchestrator import _stub_run_agent
except ImportError:
    run_orchestrator = None
    _base_path = _read_json = _stub_run_agent = None

try:
    from brand_os_integrations.whatsapp import send_whatsapp
except ImportError:
    send_whatsapp = None


def _memory_log_path() -> Path:
    base = Path(os.environ.get("BRAND_OS_V3_PATH", Path(__file__).resolve().parent.parent / "brand_os_v3"))
    return base / "storage" / "content_memory_log.jsonl"


def _append_memory_log(entry: dict) -> None:
    path = _memory_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _context_scanner_output(tenant_id: str, platform: str, topic_hint: str) -> dict | None:
    if run_orchestrator is None or _base_path is None or _read_json is None or _stub_run_agent is None:
        return None
    base = _base_path()
    state = {"trace_id": f"sched-{datetime.utcnow().strftime('%Y%m%d%H%M')}", "tenant_id": tenant_id, "platform": platform, "topic_hint": topic_hint}
    out = _stub_run_agent("CONTEXT_SCANNER", state, base)
    return out


def _pick_best_signal(ctx_out: dict | None) -> str:
    if not ctx_out:
        return "daily"
    trends = ctx_out.get("trends", [])
    return trends[0] if trends else "daily"


def daily_job() -> None:
    tenant_id = os.environ.get("BRAND_OS_TENANT_ID", "default")
    platform = os.environ.get("BRAND_OS_PLATFORM", "linkedin")
    whatsapp_to = os.environ.get("BRAND_OS_WHATSAPP_TO")
    ctx_out = _context_scanner_output(tenant_id, platform, "daily")
    topic_hint = _pick_best_signal(ctx_out)
    if run_orchestrator is None:
        return
    result = run_orchestrator({"tenant_id": tenant_id, "platform": platform, "topic_hint": topic_hint})
    if not result:
        return
    body = (result.get("content") or {}).get("body", "")
    if whatsapp_to and body and send_whatsapp:
        send_whatsapp(whatsapp_to, body[:1000])
    log_entry = {
        "trace_id": result.get("trace_id"),
        "tenant_id": tenant_id,
        "platform": platform,
        "topic_hint": topic_hint,
        "body_hash": str(hash(body)),
        "published_at": datetime.utcnow().isoformat() + "Z",
        "status": result.get("status"),
    }
    _append_memory_log(log_entry)


def start_scheduler() -> None:
    scheduler = BlockingScheduler()
    scheduler.add_job(daily_job, CronTrigger(hour=8, minute=0))
    scheduler.start()


if __name__ == "__main__":
    start_scheduler()
