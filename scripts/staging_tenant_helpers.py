from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parents[1]

_PLACEHOLDER_HOSTS = frozenset({"staging", "staging.example.com", "example.com", "localhost.example"})
_PLACEHOLDER_MARKERS = ("...", "staging...", "your-staging", "REPLACE_ME")


def load_repo_dotenv() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env", override=False)


def create_smoke_token(user_id: str, tenant_id: str) -> str:
    load_repo_dotenv()
    import importlib

    import src.auth.jwt as jwt_mod

    importlib.reload(jwt_mod)
    return jwt_mod.create_access_token(
        {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "roles": ["user"],
        }
    )


def validate_api_url(url: str) -> str | None:
    raw = (url or "").strip()
    if not raw:
        return "KIRP_API_URL is empty"
    for marker in _PLACEHOLDER_MARKERS:
        if marker in raw:
            return f"KIRP_API_URL looks like a placeholder ({marker!r})"
    try:
        parsed = urlparse(raw)
    except ValueError:
        return "KIRP_API_URL is not a valid URL"
    if parsed.scheme not in ("http", "https"):
        return "KIRP_API_URL must use http or https"
    host = (parsed.hostname or "").lower()
    if not host:
        return "KIRP_API_URL has no hostname"
    if host in _PLACEHOLDER_HOSTS:
        return f"KIRP_API_URL hostname {host!r} is a placeholder — set the real staging host"
    if host.endswith("...") or ".." in host:
        return "KIRP_API_URL hostname looks incomplete"
    if re.fullmatch(r"staging\.?", host):
        return "KIRP_API_URL hostname looks like an unfinished staging host"
    return None


def events_json_contains_marker(body: str, marker: str) -> bool:
    try:
        data = json.loads(body).get("data") or []
    except json.JSONDecodeError:
        return False
    blob = json.dumps(data, default=str)
    return marker in blob


def fetch_events(api_base: str, token: str, *, timeout_sec: float = 20.0) -> tuple[int, str]:
    url = f"{api_base.rstrip('/')}/api/v1/events?limit=200"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except (TimeoutError, urllib.error.URLError, OSError):
        return 0, ""


def kafka_host_hint() -> str | None:
    bootstrap = (os.getenv("KAFKA_BOOTSTRAP_SERVERS") or "").strip()
    if bootstrap in ("localhost:9092", "127.0.0.1:9092"):
        return (
            "KAFKA_BOOTSTRAP_SERVERS uses port 9092; for host-side API/worker use "
            "localhost:9093 (docker-compose PLAINTEXT_HOST listener)"
        )
    return None


def _count_host_kafka_processors() -> int:
    import subprocess

    try:
        proc = subprocess.run(
            ["pgrep", "-fc", "src.workers.kafka_processor"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        return 0
    if proc.returncode not in (0, 1):
        return 0
    try:
        return max(0, int((proc.stdout or "").strip() or "0"))
    except ValueError:
        return 0


def _count_docker_kafka_processors() -> int:
    import subprocess

    try:
        proc = subprocess.run(
            [
                "docker",
                "ps",
                "--format",
                "{{.Names}}",
                "--filter",
                "name=agent-processor",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 0
    if proc.returncode != 0:
        return 0
    return len([line for line in (proc.stdout or "").splitlines() if line.strip()])


def kafka_consumer_hint() -> str | None:
    host = _count_host_kafka_processors()
    docker = _count_docker_kafka_processors()
    if host > 1:
        return f"{host} host kafka_processor processes — run only one consumer"
    if host >= 1 and docker >= 1:
        return (
            "host and docker kafka consumers both running — use one: "
            "./scripts/run_local_kafka_processor.sh OR docker agent-processor only"
        )
    if host == 0 and docker == 0:
        return (
            "no kafka consumer detected — start ./scripts/run_local_kafka_processor.sh "
            "(KAFKA_BOOTSTRAP_SERVERS=localhost:9093)"
        )
    return None


def poll_events_for_marker(
    api_base: str,
    token: str,
    marker: str,
    *,
    timeout_sec: int = 180,
    interval_sec: float = 2.0,
    request_timeout_sec: float = 20.0,
) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        status, body = fetch_events(api_base, token, timeout_sec=request_timeout_sec)
        if status == 200 and events_json_contains_marker(body, marker):
            return True
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        time.sleep(min(interval_sec, remaining))
    return False


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) >= 2 and args[0] == "token":
        if len(args) != 3:
            print("usage: staging_tenant_helpers.py token USER_ID TENANT_ID", file=sys.stderr)
            return 2
        print(create_smoke_token(args[1], args[2]), end="")
        return 0
    if len(args) >= 2 and args[0] == "poll":
        if len(args) != 4:
            print("usage: staging_tenant_helpers.py poll API_BASE TOKEN MARKER", file=sys.stderr)
            return 2
        ok = poll_events_for_marker(
            args[1],
            args[2],
            args[3],
            timeout_sec=int(os.getenv("STAGING_SMOKE_POLL_SEC", "180")),
            request_timeout_sec=float(os.getenv("STAGING_SMOKE_REQUEST_SEC", "20")),
        )
        return 0 if ok else 1
    if len(args) == 1:
        err = validate_api_url(args[0])
        if err:
            print(err)
            return 1
        return 0
    print("usage: validate URL | poll API TOKEN MARKER", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
