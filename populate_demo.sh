#!/bin/bash

API="http://localhost:8000"
TOKEN="dev-local-token"

echo "🚀 Starting full KIRP demo population for Ofir..."
echo "==================================================="

post() {
  curl -s -X POST "$API/api/v1/ingest" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "$1" > /dev/null
}

echo "📌 Adding 50 events..."
for i in {1..50}; do
  post "{
    \"tenant_id\": \"default\",
    \"space_id\": \"all\",
    \"user_id\": \"ofir\",
    \"content\": \"אירוע #$i: תיעוד פעילות, מחשבה או פעולה של אופיר במהלך היום.\"
  }"
done

echo "💡 Adding 20 insights..."
for i in {1..20}; do
  post "{
    \"tenant_id\": \"default\",
    \"space_id\": \"all\",
    \"user_id\": \"ofir\",
    \"content\": \"תובנה #$i: תובנה אישית של אופיר לגבי עבודה, למידה או תהליכים.\"
  }"
done

echo "📝 Adding 10 tasks..."
for i in {1..10}; do
  post "{
    \"tenant_id\": \"default\",
    \"space_id\": \"all\",
    \"user_id\": \"ofir\",
    \"content\": \"משימה #$i: משימה שאופיר צריך לבצע השבוע.\"
  }"
done

echo "📁 Adding 5 projects..."
for i in {1..5}; do
  post "{
    \"tenant_id\": \"default\",
    \"space_id\": \"all\",
    \"user_id\": \"ofir\",
    \"content\": \"פרויקט #$i: פרויקט שאופיר עובד עליו, כולל מטרות ותתי-משימות.\"
  }"
done

echo "📘 Adding 5 daily logs..."
for i in {1..5}; do
  post "{
    \"tenant_id\": \"default\",
    \"space_id\": \"all\",
    \"user_id\": \"ofir\",
    \"content\": \"יומן יום #$i: סיכום היום של אופיר, כולל מה עבד טוב ומה פחות.\"
  }"
done

echo "📅 Adding 3 weekly plans..."
for i in {1..3}; do
  post "{
    \"tenant_id\": \"default\",
    \"space_id\": \"all\",
    \"user_id\": \"ofir\",
    \"content\": \"תוכנית שבועית #$i: מטרות, משימות ויעדים לשבוע הקרוב.\"
  }"
done

echo "🧠 Adding 3 work style analyses..."
for i in {1..3}; do
  post "{
    \"tenant_id\": \"default\",
    \"space_id\": \"all\",
    \"user_id\": \"ofir\",
    \"content\": \"ניתוח סגנון עבודה #$i: דפוסים, חוזקות, והרגלי עבודה של אופיר.\"
  }"
done

echo "🔮 Adding 2 forecasts..."
for i in {1..2}; do
  post "{
    \"tenant_id\": \"default\",
    \"space_id\": \"all\",
    \"user_id\": \"ofir\",
    \"content\": \"תחזית #$i: מה צפוי לקרות בשבוע הקרוב מבחינת עומסים, משימות והזדמנויות.\"
  }"
done

echo "📊 Adding 1 personal report..."
post "{
  \"tenant_id\": \"default\",
  \"space_id\": \"all\",
  \"user_id\": \"ofir\",
  \"content\": \"דוח אישי: סיכום פעילות, תובנות, התקדמות, ואתגרים של אופיר בתקופה האחרונה.\"
}"

echo "🎉 Demo population complete! Check the UI → Events, Insights, Agents, Dashboard"

