"""
System Control dashboard data: ports, Docker containers, processes, health.
Used by GET /system-dashboard to render system_dashboard.html.
"""

import re
import subprocess
import urllib.request
import urllib.error
from pathlib import Path


def _run(cmd: list[str], timeout: int = 5) -> tuple[str, int]:
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).resolve().parent.parent,
        )
        return (r.stdout or "") + (r.stderr or ""), r.returncode
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "", -1


def _check_http(url: str, timeout: int = 2) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 400
    except Exception:
        return False


def get_ports() -> list[dict]:
    out, _ = _run(["lsof", "-iTCP", "-sTCP:LISTEN", "-P", "-n"])
    rows = []
    for line in out.strip().split("\n")[1:]:
        parts = line.split()
        if len(parts) >= 3:
            cmd, pid, user = parts[0], parts[1], parts[2]
            node = parts[-1] if parts else ""
            port_match = re.search(r":(\d+)(/|$)", node)
            port = port_match.group(1) if port_match else ""
            if port:
                rows.append({"command": cmd, "pid": pid, "user": user, "port": port, "node": node})
    return rows[:50]


def get_docker_containers() -> list[dict]:
    out, code = _run(["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"])
    if code != 0:
        return []
    rows = []
    for line in out.strip().split("\n"):
        if "\t" in line:
            parts = line.split("\t", 2)
            name = parts[0]
            status = parts[1] if len(parts) > 1 else ""
            ports = parts[2] if len(parts) > 2 else ""
            rows.append({"name": name, "status": status, "ports": ports})
    return rows


def get_processes() -> list[dict]:
    out, _ = _run(["ps", "aux"])
    rows = []
    for line in out.strip().split("\n")[1:]:
        if any(x in line for x in ("uvicorn", "api.main", "node", "next", "streamlit", "python")):
            parts = line.split(None, 10)
            if len(parts) >= 11:
                rows.append({
                    "user": parts[0],
                    "pid": parts[1],
                    "cpu": parts[2],
                    "mem": parts[3],
                    "command": parts[10][:80] if len(parts[10]) > 80 else parts[10],
                })
    return rows[:20]


def get_health() -> list[dict]:
    endpoints = [
        ("KIRP API (8000)", "http://127.0.0.1:8000/health"),
        ("Brand OS API (8002)", "http://127.0.0.1:8002/health"),
        ("Monitoring (8001)", "http://127.0.0.1:8001/metrics"),
        ("Brand OS UI (3001)", "http://127.0.0.1:3001"),
        ("Streamlit (8501)", "http://127.0.0.1:8501"),
    ]
    return [{"name": n, "url": u, "ok": _check_http(u)} for n, u in endpoints]


def get_system_data() -> dict:
    docker_available = _run(["docker", "info"])[1] == 0
    lsof_available = _run(["which", "lsof"])[1] == 0
    return {
        "ports": get_ports() if lsof_available else [],
        "containers": get_docker_containers() if docker_available else [],
        "processes": get_processes(),
        "health": get_health(),
        "docker_available": docker_available,
        "lsof_available": lsof_available,
    }
