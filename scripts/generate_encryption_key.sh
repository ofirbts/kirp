#!/usr/bin/env bash
# Generate a 32-byte base64 key for KIRP_ENCRYPTION_KEY.
# Usage: ./scripts/generate_encryption_key.sh
# Add to .env: KIRP_ENCRYPTION_KEY=<output>

set -e
echo "Add to .env:"
echo "KIRP_ENCRYPTION_KEY=$(openssl rand -base64 32)"
