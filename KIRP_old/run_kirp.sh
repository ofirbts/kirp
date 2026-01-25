#!/bin/bash

UI_URL="http://localhost:8501"

# פונקציה שתתבצע ברגע שתלחץ Ctrl+C
cleanup() {
    echo -e "\n🛑 Ctrl+C detected. Shutting down KIRP Stack..."
    docker-compose down
    exit 0
}

# הגדרת המלכודת
trap cleanup SIGINT

# פונקציה להורדת מודל ה-AI בתוך Ollama
ensure_ai_model() {
    echo "🧠 Ensuring Llama 3 is ready in Ollama..."
    docker-compose up -d ollama
    sleep 2
    # הורדה שקטה של המודל
    docker exec -it kirp-ollama ollama pull llama3
    echo "✅ AI Model (Llama3) is ready."
}

run_stack() {
    echo "--------------------------------"
    echo "🧹 Quick Clean..."
    docker-compose down --remove-orphans
    
    echo "🐳 Starting Full Stack (API, UI, Worker, DBs, Ollama)..."
    docker-compose up -d --build
    
    # צעד קריטי להרצת ה-AI
    ensure_ai_model
    
    >echo "🚀 Services are up! Opening UI..."
    (
        sleep 5
        if command -v explorer.exe > /dev/null; then explorer.exe $UI_URL
        elif command -v xdg-open > /dev/null; then xdg-open $UI_URL
        fi
    ) &

    echo "📺 LIVE LOGS (Press Ctrl+C to STOP EVERYTHING)"
    echo "------------------------------------------------"
    docker-compose logs -f
}

run_seed() {
    echo "--------------------------------"
    echo "🔋 Injecting Knowledge Seed..."
    docker-compose up -d mongodb
    sleep 3
    # בדיקה אם הקובץ קיים פיזית לפני שמנסים להריץ
    if [ -f "app/scripts/seed_data.py" ]; then
        if docker-compose run --rm kirp-api python app/scripts/seed_data.py; then
            echo "✅ Intelligence Seeded successfully!"
        else
            echo "❌ Seed script failed during execution."
        fi
    else
        echo "⚠️  Seed file app/scripts/seed_data.py not found. Skipping seed..."
    fi
}

echo "🚀 KIRP OS - Universal Launcher v9.0 (Ollama Optimized)"
echo "--------------------------------"
echo "1) 🚀 Full Boot (Start + AI Setup + Live Logs)"
echo "2) 🔋 Seed + Boot (Fresh Data + AI + Logs)"
echo "3) 🛑 Stop Services"
echo "4) 🧹 Hard Reset (Clean Volumes + Fresh Seed + Logs)"
echo "5) 📜 View Logs Only (API & Worker)"
echo "--------------------------------"

read -p "Select option [1-5]: " opt

case $opt in
1)
    run_stack
    ;;
2)
    docker-compose down
    run_seed
    run_stack
    ;;
3)
    echo "🛑 Stopping Services..."
    docker-compose down
    ;;
4)
    echo "🧹 Performing Hard Reset (Deleting Database Volumes)..."
    docker-compose down -v
    run_seed
    run_stack
    ;;
5)
    docker-compose logs -f kirp-api kirp-worker
    ;;
*)
    echo "❌ Invalid option"
    ;;
esac