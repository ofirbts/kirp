#!/bin/bash
set -e

echo "🚀 KIRP PRODUCTION LAUNCHER"

BASE_DIR=~/projects/kirp
cd $BASE_DIR
source venv/bin/activate

cleanup() {
  echo "🛑 Shutting down KIRP..."
  kill $API_PID $UI_PID $BOT_PID $DASHBOARD_PID 2>/dev/null || true
}
trap cleanup EXIT

echo "🧠 Starting API..."
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
sleep 3

echo "💬 Starting WhatsApp bot..."
python whatsapp-bot.py &
BOT_PID=$!
sleep 2

echo "📊 Starting Streamlit UI..."
cd ui
streamlit run app.py --server.port 8501 &
UI_PID=$!
cd $BASE_DIR

echo "📟 Starting Dashboard..."
python3 -m http.server 8080 &
DASHBOARD_PID=$!

sleep 2
echo "🧪 Health check..."
curl -sf http://127.0.0.1:8000/health && echo "✅ API OK"

echo ""
echo "✅ KIRP IS LIVE"
echo "🌐 Dashboard: http://127.0.0.1:8080/dashboard.html"
echo "📊 UI:        http://localhost:8501"
echo "🧠 API:       http://127.0.0.1:8000/docs"
echo "💬 WhatsApp:  http://localhost:5000"
echo ""

wait
