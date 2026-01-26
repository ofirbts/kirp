#!/bin/bash
# ============================================
#   KIRP Enterprise — Interactive Control Menu
# ============================================

set -e

show_menu() {
  clear
  echo "🚀 KIRP Enterprise — Control Menu"
  echo "=========================================="
  echo "Select an action:"
  echo ""
  echo "1) Start full system (build + health checks)"
  echo "2) Stop all services"
  echo "3) Restart a specific service"
  echo "4) Show service status"
  echo "5) Connect to MongoDB shell"
  echo "6) Connect to PostgreSQL shell"
  echo "7) View logs for a service"
  echo "8) Run database migrations (Alembic)"
  echo "9) Full cleanup (docker compose down -v)"
  echo "10) Open UI tools (Dashboard / Grafana / Prometheus)"
  echo ""
  echo "0) Exit"
  echo "=========================================="
}

wait_for_services() {
  SERVICES=("kirp-postgres" "kirp-redis" "kirp-mongodb" "kirp-kafka" "kirp-zookeeper" "kirp-opa" "kirp-qdrant")

  echo "⏳ Waiting for services to become healthy..."
  for SERVICE in "${SERVICES[@]}"; do
    echo "🔍 Checking $SERVICE..."
    for i in {1..30}; do
      STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$SERVICE" 2>/dev/null || echo "starting")
      if [[ "$STATUS" == "healthy" ]]; then
        echo "   ✔ $SERVICE is healthy"
        break
      fi
      if [[ "$STATUS" == "unhealthy" ]]; then
        echo "   ❌ $SERVICE is unhealthy — aborting"
        exit 1
      fi
      sleep 2
    done
  done
  echo "✅ All core services are healthy"
}

open_ui_menu() {
  echo ""
  echo "בחר מה לפתוח:"
  echo "1) Dashboard (8501)"
  echo "2) Grafana (3000)"
  echo "3) Prometheus (9090)"
  echo "4) Mongo Express (8081)"
  echo "0) חזרה"
  read -p "> " choice

  case $choice in
    1) xdg-open http://localhost:8501 >/dev/null 2>&1 || open http://localhost:8501 ;;
    2) xdg-open http://localhost:3000 >/dev/null 2>&1 || open http://localhost:3000 ;;
    3) xdg-open http://localhost:9090 >/dev/null 2>&1 || open http://localhost:9090 ;;
    4) xdg-open http://localhost:8081 >/dev/null 2>&1 || open http://localhost:8081 ;;
  esac
}

while true; do
  show_menu
  read -p "> " option

  case $option in

    1)
      echo "🐳 מפעיל את כל המערכת..."
      docker compose up -d --build --remove-orphans
      wait_for_services
      ;;

    2)
      echo "🛑 עוצר את כל המערכת..."
      docker compose down
      ;;

    3)
      read -p "שם השירות להפעלה מחדש: " svc
      docker compose restart "$svc"
      ;;

    4)
      docker compose ps
      ;;

    5)
      docker exec -it kirp-mongodb mongosh "mongodb://root:example@localhost:27017/?authSource=admin"
      ;;

    6)
      docker exec -it kirp-postgres psql -U kirp_user -d kirp
      ;;

    7)
      read -p "שם השירות לצפייה בלוגים: " svc
      docker compose logs -f "$svc"
      ;;

    8)
      docker compose exec kirp-api alembic upgrade head
      ;;

    9)
      echo "⚠️ מבצע ניקוי מלא..."
      docker compose down -v
      ;;

    10)
      open_ui_menu
      ;;

    0)
      echo "להתראות 👋"
      exit 0
      ;;

    *)
      echo "❌ בחירה לא תקינה"
      ;;
  esac

  echo ""
  read -p "לחץ Enter להמשך..."
done
