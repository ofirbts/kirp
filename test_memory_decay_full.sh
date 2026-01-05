#!/bin/bash
set -e

echo "🧪 === בדיקת Memory Decay מלאה ==="
cd ~/projects/kirp

# 1. נקה והכן
pkill uvicorn || true
docker-compose up -d mongo
sleep 3

# 2. הכנס 3 זיכרונות
echo "1️⃣ הכנסת זיכרונות..."
uvicorn app.main:app --reload > /dev/null &
sleep 3
for msg in "קנה חלב" "פגישה דניאל 14:00" "שלח הצעת מחיר"; do
  curl -s -X POST "http://127.0.0.1:8000/ingest/" \
    -H "Content-Type: application/json" \
    -d "{\"source\":\"test\",\"content\":\"$msg\",\"timestamp\":\"2026-01-05T10:00:00Z\"}" > /dev/null
done

# 3. זייף תאריכים ישנים
echo "2️⃣ זיוף תאריכים ישנים..."
docker exec kirp-mongo mongosh kirp_db --quiet <<EOF
db.memories.updateMany({}, {\$set: {last_updated: ISODate("2023-01-01"), strength: 5}})
