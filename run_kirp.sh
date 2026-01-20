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

run_stack() {
    echo "--------------------------------"
    echo "🧹 Quick Clean..."
    docker-compose down --remove-orphans
    
    echo "🐳 Starting Full Stack..."
    docker-compose up -d --build
    
    echo "🧠 Services are up! Opening UI..."
    (
        sleep 5
        if command -v explorer.exe > /dev/null; then explorer.exe $UI_URL
        elif command -v xdg-open > /dev/null; then xdg-open $UI_URL
        fi
    ) &

    echo "📺 LIVE LOGS (Press Ctrl+C to STOP EVERYTHING)"
    echo "------------------------------------------------"
    # מציג לוגים של הכל כדי שתראה אם משהו קורס
    docker-compose logs -f
}

run_seed() {
    echo "--------------------------------"
    echo "🔋 Injecting Knowledge Seed..."
    docker-compose up -d mongodb
    sleep 3
    if docker-compose run --rm kirp-api python seed_data.py; 
    then
        echo "✅ Intelligence Seeded successfully!"
    else
        echo "❌ Seed failed!"
        exit 1
    fi
}

echo "🚀 KIRP OS - Universal Launcher v8.7"
echo "--------------------------------"
echo "1) 🚀 Full Boot (Clean + Start + Live Logs)"
echo "2) 🔋 Seed + Boot (Fresh Data + Logs)"
echo "3) 🛑 Stop Services"
echo "4) 🧹 Hard Reset (Full Clean + Seed + Logs)"
echo "5) 📜 View Logs Only"
echo "--------------------------------"

read -p "Select option [1-5]: " opt

case $opt in
1)
    echo "Running Pre-Flight Auto-Fix..."
    bash diagnostic.sh --fix  # הרצת הדיאגנוסטיקה עם דגל תיקון
    docker-compose up -d
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
    echo "🧹 Performing Hard Reset..."
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