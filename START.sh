#!/usr/bin/env bash
# KIRP Intelligence OS — Unified Control & Launch Center
# Full stack, backend only, UI only, health, ports, restart, validation.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="${REPO_ROOT}/scripts"
PORTS_MONITORED="8000 3000 8501 6333 6379 5432 27017 9092 2181 8181 9090 8081"

_ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
_fail() { echo -e "${RED}[FAIL]${NC} $*"; }
_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
_head() { echo -e "${CYAN}$*${NC}"; }

has_cmd() { command -v "$1" >/dev/null 2>&1; }

run_script() {
  [ -x "${SCRIPTS_DIR}/$1" ] && "${SCRIPTS_DIR}/$1" "${@:2}" || _warn "Script not found: scripts/$1"
}

# ---------- PORTS ----------

port_owner() {
  local port="$1"
  if has_cmd lsof; then
    lsof -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | head -1 || true
  else
    echo ""
  fi
}

scan_ports() {
  _head "Port scan (monitored: $PORTS_MONITORED)"
  for port in $PORTS_MONITORED; do
    pid=$(port_owner "$port")
    if [ -n "$pid" ]; then
      cmd=$(ps -o comm= -p "$pid" 2>/dev/null || echo "?")
      echo -e "  ${RED}✗${NC} Port $port → PID $pid ($cmd)"
    else
      echo -e "  ${GREEN}✔${NC} Port $port → free"
    fi
  done
}

fix_ports() {
  scan_ports
  echo ""
  _head "Kill processes on specific ports"
  echo "Enter ports to free (space-separated, empty to skip):"
  read -r ports
  [ -z "${ports:-}" ] && return
  for port in $ports; do
    pid=$(port_owner "$port")
    if [ -z "$pid" ]; then
      _info "Port $port already free"
      continue
    fi
    echo -n "Kill PID $pid on port $port? (y/N): "
    read -r c
    if [[ "$c" =~ ^[yY]$ ]]; then
      if [ -x "${SCRIPTS_DIR}/kill_port.sh" ]; then
        "${SCRIPTS_DIR}/kill_port.sh" "$port"
      else
        kill -9 "$pid" || _warn "Failed to kill $pid"
      fi
      _ok "Freed port $port"
    else
      _warn "Skipped port $port"
    fi
  done
}

# ---------- DOCKER / SERVICES ----------

docker_status() {
  _head "Docker compose status"
  (cd "$REPO_ROOT" && docker compose ps -a) || _warn "docker compose ps failed"
}

restart_specific_service() {
  echo -n "Service name to restart (e.g. kirp-api, kirp-worker, kirp-agent-processor): "
  read -r svc
  [ -z "$svc" ] && return
  (cd "$REPO_ROOT" && docker compose restart "$svc") && _ok "Restarted $svc" || _fail "Failed to restart $svc"
}

start_backend_only() {
  _head "Starting backend stack (Docker only, no UI)…"
  cd "$REPO_ROOT"
  docker compose up -d --build
  _ok "Backend stack requested (kirp-api, worker, qdrant, redis, postgres, kafka, etc.)"
}

# ---------- UI ----------

start_ui_only() {
  _head "Starting unified KIRP UI (Next.js on port 3100)…"
  cd "$REPO_ROOT"
  if [ ! -d "node_modules" ]; then
    _info "node_modules missing → running npm install"
    npm install
  fi
  # Run in background so the menu stays available
  npm run dev >/tmp/kirp-ui.log 2>&1 &
  UI_PID=$!
  _ok "UI started (PID $UI_PID, http://localhost:3100)"
  _info "Logs: tail -f /tmp/kirp-ui.log"
}

open_uis() {
  _head "Opening UIs in browser"
  open_url() {
    local url="$1"
    if has_cmd xdg-open; then
      xdg-open "$url" >/dev/null 2>&1 || true
    elif has_cmd open; then
      open "$url" >/dev/null 2>&1 || true
    else
      _info "Open manually: $url"
    fi
  }

  open_url "http://localhost:3100"          # Unified KIRP UI
  open_url "http://localhost:8501"          # Streamlit dashboard
  open_url "http://localhost:8081"          # Mongo Express
  open_url "http://localhost:9090"          # Prometheus
  open_url "http://localhost:6333/dashboard" # Qdrant UI
  _ok "UI tabs opened (where supported)"
}

# ---------- VALIDATION ----------

validate_ui() {
  if [ -x "${SCRIPTS_DIR}/validate_ui.sh" ]; then
    _head "Running UI validation (scripts/validate_ui.sh)…"
    "${SCRIPTS_DIR}/validate_ui.sh" "http://localhost:3100" "http://localhost:8000"
  else
    _warn "scripts/validate_ui.sh not found"
  fi
}

# ---------- FULL DEV FLOW ----------

start_full_stack() {
  _head "Full dev stack: backend (Docker) + UI (Next.js) + dev auth"
  cd "$REPO_ROOT"

  # 1) Quick port scan before start
  _info "Quick port scan before start:"
  scan_ports

  # 2) Start backend
  docker compose up -d --build || { _fail "docker compose failed (is Docker running?)"; return 1; }
  _ok "Backend stack up (docker compose)"

  # 3) Start UI
  if [ ! -d "node_modules" ]; then
    _info "node_modules missing → running npm install"
    npm install
  fi
  npm run dev >/tmp/kirp-ui.log 2>&1 &
  UI_PID=$!
  _ok "UI started (PID $UI_PID, http://localhost:3100)"

  # 4) Reminder for auth env
  _info "For no-401 dev mode, run backend with ENV=development or SKIP_AUTH=1 (already configured in docker image if set)."
  _info "UI → backend base: NEXT_PUBLIC_API_URL (default http://localhost:8000)."

  # 5) Optional validation
  validate_ui
}

# ---------- MENU ----------

main_menu() {
  clear
  _head "═══════════════════════════════════════════════════════"
  _head "   KIRP Intelligence OS — START CENTER"
  _head "═══════════════════════════════════════════════════════"
  echo ""
  echo "  🔵 1 — Start Full Dev Stack (Backend + UI)"
  echo "  🔵 2 — System Status (Docker + Ports)"
  echo "  🔵 3 — Run UI Validation (scripts/validate_ui.sh)"
  echo "  🔵 4 — Tail Logs for a Service"
  echo ""
  echo "  🔵 5 — Start Only Backend (no UI)"
  echo "  🔵 6 — Start Only UI"
  echo "  🔵 7 — Restart Specific Service (Docker)"
  echo "  🔵 8 — Stop All Docker Services"
  echo "  🔵 9 — Fix Ports (kill processes on ports)"
  echo ""
  echo "  🔵 10 — Open UIs (KIRP UI, Dashboard, Qdrant, etc.)"
  echo ""
  echo "  0 — Exit"
  echo ""
  echo -n "> "
}

tail_logs() {
  echo -n "Service name (e.g. kirp-api, kirp-worker, kirp-agent-processor): "
  read -r svc
  [ -z "$svc" ] && return
  docker logs -f "$svc" || _warn "No such container: $svc"
}

stop_all_docker() {
  cd "$REPO_ROOT"
  docker compose down || _warn "docker compose down failed"
  _ok "All docker services stopped"
}

system_status() {
  _head "System Status"
  docker_status
  echo ""
  scan_ports
}

main() {
  cd "$REPO_ROOT"
  while true; do
    main_menu
    read -r choice
    case "$choice" in
      1) start_full_stack ;;
      2) system_status ;;
      3) validate_ui ;;
      4) tail_logs ;;
      5) start_backend_only ;;
      6) start_ui_only ;;
      7) restart_specific_service ;;
      8) stop_all_docker ;;
      9) fix_ports ;;
      10) open_uis ;;
      0) echo "Bye 👋"; exit 0 ;;
      *) _warn "Invalid choice" ;;
    esac
    echo ""
    read -r -p "Press Enter to continue..."
  done
}

main "$@"
