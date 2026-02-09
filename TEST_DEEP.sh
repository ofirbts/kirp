#!/bin/bash

echo "======================================================="
echo "🧪 KIRP OS — Deep System Audit (Full Stack Validation)"
echo "======================================================="

API="http://localhost:8000"

echo ""
echo "🔐 1. Auth & Identity"
curl -s -o /dev/null -w "  /auth/me → %{http_code}\n" $API/api/v1/auth/me

echo ""
echo "📦 2. Core Data APIs"
curl -s -o /dev/null -w "  /tasks → %{http_code}\n" "$API/api/v1/tasks?tenant_id=default&limit=20"
curl -s -o /dev/null -w "  /nodes → %{http_code}\n" "$API/api/v1/nodes?tenant_id=default&limit=20"
curl -s -o /dev/null -w "  /history → %{http_code}\n" "$API/api/v1/history?tenant_id=default&limit=20"

echo ""
echo "🤖 3. Agents & Intelligence"
curl -s -o /dev/null -w "  /agents → %{http_code}\n" "$API/api/v1/agents"
curl -s -o /dev/null -w "  /ask → %{http_code}\n" -X POST "$API/api/v1/ask" \
  -H "Content-Type: application/json" \
  -d '{"query":"Explain what KIRP OS is."}'

echo ""
echo "🧠 4. RAG / Embeddings / Qdrant"
curl -s -o /dev/null -w "  Qdrant /collections → %{http_code}\n" http://localhost:6333/collections

echo ""
echo "📨 5. Notifications"
curl -s -o /dev/null -w "  /notifications/unread-count → %{http_code}\n" \
  "$API/api/v1/notifications/unread-count?tenant_id=default&user_id=default"

echo ""
echo "📡 6. WebSocket (upgrade check)"
curl -s -o /dev/null -w "  WS /ws/notifications → %{http_code}\n" \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  "$API/ws/notifications?tenant_id=default&user_id=default"

echo ""
echo "🏢 7. Multi‑Tenant Isolation"
curl -s -o /dev/null -w "  /tasks (tenant=default) → %{http_code}\n" \
  "$API/api/v1/tasks?tenant_id=default&limit=5"
curl -s -o /dev/null -w "  /tasks (tenant=random) → %{http_code}\n" \
  "$API/api/v1/tasks?tenant_id=12345678&limit=5"

echo ""
echo "📊 8. Observability"
curl -s -o /dev/null -w "  /observability/health → %{http_code}\n" "$API/observability/health"
curl -s -o /dev/null -w "  /observability/metrics/snapshot → %{http_code}\n" "$API/observability/metrics/snapshot"

echo ""
echo "🎉 Deep Audit Complete"
echo "======================================================="
