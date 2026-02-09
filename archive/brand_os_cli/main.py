"""
Brand OS v3 CLI — Click-based.
Commands: run, daily, signals, agents.
Entry point: brandos
"""

import os
import json
import click
import requests
from pathlib import Path

try:
    from brand_os_sdk import load_identity, load_voice, list_agents, run_orchestrator
    from brand_os_sdk.config_loader import _base_path, _read_json
except ImportError:
    load_identity = load_voice = list_agents = run_orchestrator = None
    _base_path = _read_json = None

API_BASE = os.environ.get("BRAND_OS_API_URL", "http://127.0.0.1:8000")


def _run_via_api(tenant_id: str, platform: str, topic_hint: str, trace_id: str | None = None) -> dict | None:
    url = f"{API_BASE}/brand-os/run"
    payload = {"tenant_id": tenant_id, "platform": platform, "topic_hint": topic_hint}
    if trace_id:
        payload["trace_id"] = trace_id
    try:
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        click.echo(f"API error: {e}", err=True)
        return None


def _context_scanner_output(tenant_id: str, platform: str, topic_hint: str) -> dict | None:
    if run_orchestrator is None:
        click.echo("SDK not available; install brand_os_sdk.", err=True)
        return None
    base = _base_path()
    agent_path = base / "agents" / "CONTEXT_SCANNER.json"
    if not agent_path.exists():
        click.echo("CONTEXT_SCANNER.json not found.", err=True)
        return None
    spec = _read_json(agent_path)
    from brand_os_sdk.orchestrator import _stub_run_agent
    state = {"trace_id": "cli-signals", "tenant_id": tenant_id, "platform": platform, "topic_hint": topic_hint}
    out = _stub_run_agent("CONTEXT_SCANNER", state, base)
    return out


def _memory_log_path() -> Path:
    base = Path(os.environ.get("BRAND_OS_V3_PATH", Path(__file__).resolve().parent.parent / "brand_os_v3"))
    return base / "storage" / "content_memory_log.jsonl"


def _append_memory_log(entry: dict) -> None:
    path = _memory_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


@click.group()
def brandos():
    """Brand OS v3 CLI — run, daily, signals, agents, system."""


@brandos.command("run")
@click.argument("topic", type=str)
@click.option("--tenant", "-t", default="default", help="Tenant ID")
@click.option("--platform", "-p", type=click.Choice(["linkedin", "twitter", "whatsapp"]), default="linkedin")
@click.option("--trace-id", default=None, help="Trace ID")
@click.option("--api/--sdk", "use_api", default=True, help="Use API (default) or SDK")
def run(topic: str, tenant: str, platform: str, trace_id: str | None, use_api: bool):
    """Run Brand OS pipeline for TOPIC. Prints post, visual prompt, recommendations."""
    if use_api:
        result = _run_via_api(tenant, platform, topic, trace_id)
    else:
        if run_orchestrator is None:
            click.echo("SDK not available.", err=True)
            return
        payload = {"tenant_id": tenant, "platform": platform, "topic_hint": topic}
        if trace_id:
            payload["trace_id"] = trace_id
        result = run_orchestrator(payload)
    if not result:
        raise SystemExit(1)
    click.echo("=== CONTENT ===")
    content = result.get("content", {})
    click.echo(content.get("headline", ""))
    click.echo(content.get("body", ""))
    click.echo("\n=== VISUAL SPEC ===")
    vs = result.get("visual_spec", {})
    click.echo(f"Prompt: {vs.get('image_prompt', '')}")
    click.echo(f"Format: {vs.get('format', '')} {vs.get('aspect_ratio', '')}")
    click.echo("\n=== RECOMMENDATIONS ===")
    rec = result.get("recommendations", {})
    click.echo(f"Timing: {rec.get('suggested_timing', '')}")
    click.echo(f"Next topics: {rec.get('next_topic_hints', [])}")
    click.echo(f"\nStatus: {result.get('status', '')}")


@brandos.command("daily")
@click.option("--tenant", "-t", default="default")
@click.option("--platform", "-p", type=click.Choice(["linkedin", "twitter", "whatsapp"]), default="linkedin")
@click.option("--send-whatsapp", default=None, help="Phone number to send result via WhatsApp")
def daily(tenant: str, platform: str, send_whatsapp: str | None):
    """Run CONTEXT_SCANNER, pick best signal, run orchestrator, optionally send WhatsApp, append to memory log."""
    if run_orchestrator is None:
        click.echo("SDK not available.", err=True)
        raise SystemExit(1)
    ctx_out = _context_scanner_output(tenant, platform, "daily")
    if not ctx_out:
        click.echo("No context; using topic_hint 'daily'.", err=True)
        topic_hint = "daily"
    else:
        trends = ctx_out.get("trends", [])
        topic_hint = trends[0] if trends else "daily"
    result = run_orchestrator({"tenant_id": tenant, "platform": platform, "topic_hint": topic_hint})
    if not result:
        click.echo("Orchestrator failed.", err=True)
        raise SystemExit(1)
    body = (result.get("content") or {}).get("body", "")
    if send_whatsapp and body:
        try:
            from brand_os_integrations.whatsapp import send_whatsapp as sw
            r = sw(send_whatsapp, body[:1000])
            click.echo(f"WhatsApp: {r}")
        except Exception as e:
            click.echo(f"WhatsApp error: {e}", err=True)
    log_entry = {
        "trace_id": result.get("trace_id"),
        "tenant_id": tenant,
        "platform": platform,
        "topic_hint": topic_hint,
        "body_hash": str(hash(body)),
        "published_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "status": result.get("status"),
    }
    _append_memory_log(log_entry)
    click.echo(f"Run complete. Status: {result.get('status')}. Logged to content memory.")


@brandos.command("signals")
@click.option("--tenant", "-t", default="default")
@click.option("--platform", "-p", type=click.Choice(["linkedin", "twitter", "whatsapp"]), default="linkedin")
def signals(tenant: str, platform: str):
    """Run CONTEXT_SCANNER and print signals/trends."""
    out = _context_scanner_output(tenant, platform, "signals")
    if not out:
        raise SystemExit(1)
    click.echo("World context: " + str(out.get("world_context", "")))
    click.echo("Trends: " + str(out.get("trends", [])))
    click.echo("Signals used: " + str(out.get("signals_used", [])))
    click.echo("Memory summary: " + str(out.get("memory_summary", "")))


@brandos.command("agents")
def agents_cmd():
    """Print list of agents from SDK list_agents()."""
    if list_agents is None:
        click.echo("SDK not available.", err=True)
        raise SystemExit(1)
    agents_list = list_agents()
    for a in agents_list:
        click.echo(a)


try:
    from brand_os_cli.system import system as system_group
    brandos.add_command(system_group, "system")
except ImportError:
    pass


def main():
    brandos()


if __name__ == "__main__":
    main()
