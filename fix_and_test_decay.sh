#!/bin/bash
cd ~/projects/kirp

echo "🔧 מסדר MongoDB + בדיקת Decay..."
pkill uvicorn || true

# 1. MongoDB מלא
docker-compose up -d
sleep 5

# 2. שרת + זיכרונות
uvicorn app.main:app --reload > /dev/null &
sleep 5

echo "📥 מכניס זיכרונות..."
curl -s -X POST "http://127.0.0.1:8000/ingest/" \
  -H "Content-Type: application/json" \
  -d '{"source":"test","content":"קנה חלב","timestamp":"2026-01-05T10:00:00Z"}' > /dev/null

curl -s -X POST "http://127.0.0.1:8000/ingest/" \
  -H "Content-Type: application/json" \
  -d '{"source":"test","content":"פגישה דניאל","timestamp":"2026-01-05T10:00:00Z"}' > /dev/null

# 3. זייף תאריכים
echo "🕰️  מזייף תאריכים ישנים..."
docker exec -it $(docker ps | grep mongo | awk '{print $1}') mongosh kirp_db --quiet <<EOF
db.memories.updateMany({}, {\$set: {last_updated: ISODate("2023-01-01"), strength: 5}})
