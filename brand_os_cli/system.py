"""
Brand OS / KIRP System Control CLI.
Commands: status, ports, docker, processes, kill-port, restart, health.
Invokes scripts in scripts/ or runs inline checks.
"""

import os
import subprocess
import sys
from pathlib import Path

import click

# Repo root: parent of brand_os_cli
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _script_path(name: str) -> Path:
    p = SCRIPTS_DIR / name
    return p if p.exists() else Path()


def _run_script(script_name: str, *args: str) -> int:
    path = _script_path(script_name)
    if not path:
        click.echo(f"Script not found: scripts/{script_name}", err=True)
        return 1
    cmd = [str(path), *args]
    try:
        return subprocess.run(cmd, cwd=REPO_ROOT).returncode
    except Exception as e:
        click.echo(f"Error running script: {e}", err=True)
        return 1


@click.group()
def system():
    """System control & observability: ports, Docker, processes, health, restart."""


@system.command("status")
def status_cmd():
    """Full system status: ports, Docker, processes, CPU/RAM, health checks."""
    sys.exit(_run_script("system_status.sh") or 0)


@system.command("ports")
@click.argument("port", type=int, required=False)
def ports_cmd(port: int | None):
    """List listening ports; optionally filter by PORT."""
    args = [str(port)] if port else []
    sys.exit(_run_script("ports.sh", *args) or 0)


@system.command("docker")
@click.argument("args", nargs=-1)
def docker_cmd(args: tuple[str, ...]):
    """Docker containers status. Use: brandos system docker restart CONTAINER to restart."""
    sys.exit(_run_script("docker_status.sh", *args) or 0)


@system.command("processes")
@click.option("--tree", is_flag=True, help="Show process tree")
def processes_cmd(tree: bool):
    """Show Python/Node/Uvicorn processes and CPU/RAM."""
    args = ["--tree"] if tree else []
    sys.exit(_run_script("process_status.sh", *args) or 0)


@system.command("kill-port")
@click.argument("port", type=int, required=True)
def kill_port_cmd(port: int):
    """Kill the process that owns PORT."""
    sys.exit(_run_script("kill_port.sh", str(port)) or 0)


@system.command("restart")
@click.argument("service", type=str, required=True)
def restart_cmd(service: str):
    """Restart a Docker container or show hint for local service (e.g. kirp-api, brand-os-api)."""
    sys.exit(_run_script("restart_service.sh", service) or 0)


@system.command("health")
def health_cmd():
    """Check health of API, Monitoring, UI endpoints."""
    import urllib.request
    import urllib.error

    endpoints = [
        ("KIRP API (8000)", "http://127.0.0.1:8000/health"),
        ("Brand OS API (8002)", "http://127.0.0.1:8002/health"),
        ("Monitoring (8001)", "http://127.0.0.1:8001/metrics"),
        ("Brand OS UI (3001)", "http://127.0.0.1:3001"),
        ("Streamlit (8501)", "http://127.0.0.1:8501"),
    ]
    failed = 0
    for name, url in endpoints:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as r:
                if 200 <= r.status < 400:
                    click.echo(click.style("[OK] ", fg="green") + f"{name} — {url}")
                else:
                    click.echo(click.style("[FAIL] ", fg="red") + f"{name} — {url} ({r.status})")
                    failed += 1
        except Exception as e:
            click.echo(click.style("[FAIL] ", fg="red") + f"{name} — {url} — {e}")
            failed += 1
    sys.exit(1 if failed else 0)
