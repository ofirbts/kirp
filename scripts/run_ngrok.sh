#!/usr/bin/env bash
# Expose local API so Twilio can reach the WhatsApp webhook.
# Usage: ./scripts/run_ngrok.sh [port]
# Then set in Twilio Console → WhatsApp Sandbox → "When a message comes in":
#   https://<the-ngrok-URL>/api/v1/webhooks/whatsapp

set -e
PORT="${1:-8000}"

# Load NGROK_AUTHTOKEN from .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | grep 'NGROK_AUTHTOKEN=' | xargs)
fi

if [ -z "$NGROK_AUTHTOKEN" ]; then
  echo "NGROK_AUTHTOKEN not set. Add it to .env or: export NGROK_AUTHTOKEN=your_token"
  exit 1
fi

# Configure ngrok (idempotent)
ngrok config add-authtoken "$NGROK_AUTHTOKEN" 2>/dev/null || true

echo "Starting ngrok on port $PORT. Set Twilio webhook to: https://<this-ngrok-url>/api/v1/webhooks/whatsapp"
exec ngrok http "$PORT"
