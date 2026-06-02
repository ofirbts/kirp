# System Control & Observability — KIRP / Brand OS

Full visibility into ports, Docker containers, processes, health, and resource usage. Use scripts or the `brandos system` CLI.

---

## Overview

| Component | Purpose |
|-----------|---------|
| **scripts/** | Shell scripts: system_status, ports, docker_status, process_status, kill_port, restart_service |
| **brandos system** | CLI: status, ports, docker, processes, kill-port, restart, health |
| **Monitoring /system-dashboard** | Web dashboard: ports, containers, processes, health, actions |

---

## 1. Scripts

All scripts live in `scripts/`. Make them executable once: `chmod +x scripts/*.sh`.

### 1.1 system_status.sh

**Master status:** active ports, Docker containers, Python/Node/Uvicorn processes, CPU/RAM top, health checks.

```bash
./scripts/system_status.sh
```

Output:
- Listening ports (8000, 8001, 8002, 3001, 8501, etc.)
- Docker containers (names, status, ports)
- Relevant processes (uvicorn, node, streamlit)
- Top CPU and memory usage
- Health: KIRP API (8000), Brand OS API (8002), Monitoring (8001), UI (3001), Streamlit (8501) — green OK / red FAIL

**Requirements:** `lsof` (Linux: `sudo apt-get install lsof`, macOS: `brew install lsof`), `docker` (optional), `curl`.

---

### 1.2 ports.sh

**List listening ports** with process, PID, user, port.

```bash
./scripts/ports.sh           # all listening ports
./scripts/ports.sh 8000       # only port 8000
```

If a port is blocked, the script suggests: `./scripts/kill_port.sh <port>`.

---

### 1.3 docker_status.sh

**Docker containers:** status, ports, health, memory (docker stats).

```bash
./scripts/docker_status.sh
```

Restart a container:

```bash
./scripts/docker_status.sh restart kirp-api
```

---

### 1.4 process_status.sh

**Python/Node/Uvicorn/Streamlit processes** with CPU and RAM.

```bash
./scripts/process_status.sh
./scripts/process_status.sh --tree    # include process tree
```

---

### 1.5 kill_port.sh

**Free a port** by killing the process that owns it. Uses SIGTERM, then SIGKILL if needed.

```bash
./scripts/kill_port.sh 8000
```

**Use when:** Port 8000 is in use and you want to run Brand OS API locally on 8000, or another service on that port.

---

### 1.6 restart_service.sh

**Restart a Docker container** or get a hint for local services.

```bash
./scripts/restart_service.sh kirp-api
./scripts/restart_service.sh brand-os-api   # prints hint: run uvicorn ... --port 8002
./scripts/restart_service.sh monitoring     # hint: uvicorn brand_os_monitoring.app:app --port 8001
./scripts/restart_service.sh ui            # hint: npm run dev
```

---

## 2. CLI: brandos system

After `pip install -e .`, the `brandos system` group is available.

| Command | Description |
|---------|-------------|
| `brandos system status` | Full system status (runs system_status.sh) |
| `brandos system ports [PORT]` | List ports (runs ports.sh) |
| `brandos system docker [restart CONTAINER]` | Docker status or restart (runs docker_status.sh) |
| `brandos system processes [--tree]` | Python/Node processes (runs process_status.sh) |
| `brandos system kill-port PORT` | Kill process on PORT (runs kill_port.sh) |
| `brandos system restart SERVICE` | Restart container or show hint (runs restart_service.sh) |
| `brandos system health` | HTTP health checks for API, Monitoring, UI, Streamlit |

**Examples:**

```bash
brandos system status
brandos system ports 8000
brandos system docker restart kirp-api
brandos system kill-port 8002
brandos system restart kirp-api
brandos system health
```

---

## 3. Debugging Port Conflicts

**Symptom:** `Address already in use` when starting uvicorn or another service.

**Steps:**

1. **See who uses the port:**
   ```bash
   ./scripts/ports.sh 8000
   # or
   brandos system ports 8000
   ```

2. **Option A — Free the port:**
   ```bash
   ./scripts/kill_port.sh 8000
   # or
   brandos system kill-port 8000
   ```
   Then start your service again.

3. **Option B — Use another port:**
   - Brand OS API: `uvicorn api.main:app --reload --port 8002`
   - Set `BRAND_OS_API_URL=http://127.0.0.1:8002` for CLI/UI.

4. **Check Docker:** If KIRP runs in Docker, `kirp-api` often uses 8000. Either stop that container or run Brand OS API on 8002.

---

## 4. Restarting Services

**Docker container:**
```bash
./scripts/restart_service.sh kirp-api
# or
brandos system docker restart kirp-api
```

**Local process (Brand OS API, Monitoring, UI):** The script only prints the command to run. Stop the process (Ctrl+C) and start it again, e.g.:
- Brand OS API: `uvicorn api.main:app --reload --port 8002`
- Monitoring: `uvicorn brand_os_monitoring.app:app --port 8001 --reload`
- UI: `npm run dev` (unified KIRP UI at repo root)

---

## 5. Inspecting Logs

**Docker container logs:**
```bash
docker logs kirp-api
docker logs -f kirp-worker    # follow
```

**Local uvicorn:** Logs go to stdout; redirect if needed:
```bash
uvicorn api.main:app --reload --port 8002 2>&1 | tee api.log
```

**Scheduler:**
```bash
python run_scheduler.py 2>&1 | tee scheduler.log
```

---

## 6. Monitoring Health

**Quick check:**
```bash
brandos system health
```

**Endpoints:**

| Service | URL | Expected |
|---------|-----|----------|
| KIRP API | http://127.0.0.1:8000/health | 200 |
| Brand OS API | http://127.0.0.1:8002/health | 200 |
| Monitoring | http://127.0.0.1:8001/metrics | 200 |
| Brand OS UI | http://127.0.0.1:3001 | 200 |
| Streamlit | http://127.0.0.1:8501 | 200 |

**Web dashboard:** Open http://127.0.0.1:8001/system-dashboard (after starting the monitoring app) to see ports, containers, processes, health, and suggested actions.

---

## 7. Cleanup: Zombie Processes

**Find and kill processes on a port:**
```bash
./scripts/kill_port.sh 8000
```

**Find Python/Node processes:**
```bash
./scripts/process_status.sh
# Then kill by PID if needed: kill -TERM <PID>
```

**Docker:** Restart a crashing container:
```bash
./scripts/restart_service.sh kirp-agent-processor
```

---

## 8. Requirements

- **Linux (WSL2) or macOS**
- **lsof** — for port listing and kill_port (install if missing)
- **docker** — optional; scripts detect and skip if not installed
- **curl** — for health checks in system_status.sh
- **ps** — for process_status (usually present)

---

## 9. File Reference

| File | Purpose |
|------|---------|
| scripts/system_status.sh | Master status |
| scripts/ports.sh | Listening ports |
| scripts/docker_status.sh | Docker containers + restart |
| scripts/process_status.sh | Python/Node processes |
| scripts/kill_port.sh | Kill process on port |
| scripts/restart_service.sh | Restart container or hint |
| brand_os_cli/system.py | CLI group `brandos system` |
| brand_os_monitoring/system_dashboard.py | Data for /system-dashboard |
| brand_os_monitoring/templates/system_dashboard.html | System dashboard UI |
| docs/SYSTEM_CONTROL.md | This file |
