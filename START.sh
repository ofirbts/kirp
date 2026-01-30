#!/usr/bin/env bash

set -euo pipefail

API_SERVICE="kirp-api"
MONGO_SERVICE="kirp-mongodb"
POSTGRES_SERVICE="kirp-postgres"
QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
API_BASE_URL="${KIRP_API_BASE_URL:-http://localhost:8000}"

header() {
  clear
  echo "🚀 KIRP Enterprise — Control Center"
  echo "==================================="
  echo "1) Start full stack (docker compose up -d --build)"
  echo "2) Start specific services"
  echo "3) Stop all services"
  echo "4) Stop a service"
  echo "5) Restart a service"
  echo "6) Show docker compose status"
  echo "7) Tail logs for a service"
  echo "8) Run Alembic migrations (API container)"
  echo "9) Full cleanup (docker compose down -v)"
  echo "10) Open UI (Dashboard / Grafana / Prometheus / Mongo Express)"
  echo "11) Seed menu (Postgres / Mongo / Qdrant / Kafka)"
  echo "12) Health checks (API / Mongo / Postgres / Qdrant)"
  echo "13) DB checks (Mongo / Postgres / Qdrant)"
  echo "0) Exit"
  echo "==================================="
}

wait_for_services() {
  local services=("$API_SERVICE" "$MONGO_SERVICE" "$POSTGRES_SERVICE")
  echo "🔍 Waiting for core services to become healthy..."
  for svc in "${services[@]}"; do
    echo "   → $svc"
    for i in {1..30}; do
      local status
      status=$(docker inspect --format='{{"{{"}}.State.Health.Status{{"}}"}}' "$svc" 2>/dev/null || echo "starting")
      if [[ "$status" == "healthy" ]]; then
        echo "      ✔ $svc healthy"
        break
      fi
      if [[ "$status" == "unhealthy" ]]; then
        echo "      ❌ $svc reported unhealthy"
        exit 1
      fi
      sleep 2
    done
  done
  echo "✅ Core services reported healthy (or started)."
}

open_ui_menu() {
  echo ""
  echo "🌐 Open UI"
  echo "1) Dashboard (http://localhost:3000)"
  echo "2) Grafana   (http://localhost:3001)"
  echo "3) Prometheus (http://localhost:9090)"
  echo "4) Mongo Express (http://localhost:8081)"
  echo "0) Back"
  read -r -p "> " choice

  case "$choice" in
    1) xdg-open http://localhost:3000 >/dev/null 2>&1 || open http://localhost:3000 ;;
    2) xdg-open http://localhost:3001 >/dev/null 2>&1 || open http://localhost:3001 ;;
    3) xdg-open http://localhost:9090 >/dev/null 2>&1 || open http://localhost:9090 ;;
    4) xdg-open http://localhost:8081 >/dev/null 2>&1 || open http://localhost:8081 ;;
    *) ;;
  esac
}

seed_menu() {
  clear
  echo "🌱 Seed Menu"
  echo "=============================="
  echo "1) Seed Postgres (Tenants/Users/RBAC)"
  echo "2) Seed Mongo (Events via /ingest)"
  echo "3) Seed Qdrant (Embeddings backfill)"
  echo "4) Seed Kafka (optional)"
  echo "5) Seed ALL (1 → 2 → 3)"
  echo "0) Back"
  echo "=============================="
  read -r -p "> " seed_choice

  case "$seed_choice" in
    1) python3 -m tools.seed_postgres ;;
    2) python3 -m tools.seed_mongo ;;
    3) python3 -m tools.seed_qdrant ;;
    4) python3 -m tools.seed_kafka ;;
    5)
      python3 -m tools.seed_postgres
      python3 -m tools.seed_mongo
      python3 -m tools.seed_qdrant
      ;;
    *) ;;
  esac
}

health_checks() {
  echo "🔍 API health check:"
  curl -s "${API_BASE_URL}/observability/health" | jq || echo "API health check failed"

  echo ""
  echo "🔍 Checking Qdrant:"
  curl -s "${QDRANT_URL}/collections" | jq || echo "Qdrant check failed"

  echo ""
  echo "🔍 Checking Mongo:"
  docker compose exec "${MONGO_SERVICE}" mongosh --eval "db.runCommand({ ping: 1 })" || echo "Mongo ping failed"

  echo ""
  echo "🔍 Checking Postgres:"
  docker compose exec "${POSTGRES_SERVICE}" psql -U kirp_user -d kirp -c "SELECT NOW();" || echo "Postgres check failed"
}

db_checks() {
  echo "📦 Mongo — Number of events:"
  docker compose exec "${MONGO_SERVICE}" mongosh --eval "use kirp; db.events.countDocuments();" || echo "Mongo query failed"

  echo ""
  echo "🗃️ Postgres — Number of tenants:"
  docker compose exec "${POSTGRES_SERVICE}" psql -U kirp_user -d kirp -c "SELECT COUNT(*) FROM tenants;" || echo "Postgres query failed"

  echo ""
  echo "🧠 Qdrant — Collections:"
  curl -s "${QDRANT_URL}/collections" | jq || echo "Qdrant query failed"
}

while true; do
  header
  read -r -p "> " option

  case "$option" in
    1)
      echo "🐳 Starting the whole system..."
      docker compose up -d --build --remove-orphans
      wait_for_services
      ;;
    2)
      echo "🟡 Partial startup — enter service names (space‑separated):"
      read -r -p "Services: " svcs
      docker compose up -d $svcs
      ;;
    3)
      echo "🛑 Stopping all services..."
      docker compose down
      ;;
    4)
      read -r -p "Service name to stop: " svc
      docker compose stop "$svc"
      ;;
    5)
      read -r -p "Service name to restart: " svc
      docker compose restart "$svc"
      ;;
    6)
      docker compose ps
      ;;
    7)
      read -r -p "Service name to log: " svc
      docker compose logs -f "$svc"
      ;;
    8)
      echo "🧩 Running Alembic migrations in ${API_SERVICE}..."
      docker compose exec "${API_SERVICE}" alembic upgrade head
      ;;
    9)
      echo "⚠️ Full cleanup (volumes will be removed)..."
      docker compose down -v
      ;;
    10)
      open_ui_menu
      ;;
    11)
      seed_menu
      ;;
    12)
      health_checks
      ;;
    13)
      db_checks
      ;;
    0)
      echo "Goodbye 👋"
      exit 0
      ;;
    *)
      echo "❌ Invalid choice"
      ;;
  esac

  echo ""
  read -r -p "Press Enter to continue..."
done