#!/usr/bin/env bash
# Kill the process that owns the given port. Uses SIGTERM then SIGKILL.
# Usage: ./scripts/kill_port.sh <port>
# Example: ./scripts/kill_port.sh 8000
# Works on Linux (WSL2) and macOS.

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

_ok()  { echo -e "${GREEN}[OK]${NC} $*"; }
_fail(){ echo -e "${RED}[FAIL]${NC} $*"; }
_warn(){ echo -e "${YELLOW}[WARN]${NC} $*"; }

PORT="$1"
if [ -z "$PORT" ]; then
  echo "Usage: $0 <port>"
  echo "Example: $0 8000"
  exit 1
fi

if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
  _fail "Port must be a number"
  exit 1
fi

if ! command -v lsof >/dev/null 2>&1; then
  _fail "lsof not installed. Install with: sudo apt-get install lsof (Linux) or brew install lsof (macOS)"
  exit 1
fi

PIDS=$(lsof -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null)
if [ -z "$PIDS" ]; then
  _warn "No process listening on port $PORT"
  exit 0
fi

for PID in $PIDS; do
  _warn "Sending SIGTERM to PID $PID (port $PORT)"
  kill -TERM "$PID" 2>/dev/null && _ok "SIGTERM sent to $PID" || _fail "Could not send SIGTERM to $PID"
done

# Wait briefly then SIGKILL if still alive
sleep 2
for PID in $PIDS; do
  if kill -0 "$PID" 2>/dev/null; then
    _warn "Process $PID still alive; sending SIGKILL"
    kill -KILL "$PID" 2>/dev/null && _ok "SIGKILL sent to $PID" || _fail "Could not kill $PID"
  fi
done

_ok "Port $PORT should be free now."
