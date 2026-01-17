#!/bin/bash

# צבעים להודעות
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 KIRP OS - Universal Launcher v5.0${NC}"
echo "--------------------------------"
echo "1) 🛠️  Development Mode (Local venv + Docker DBs)"
echo "2) 🐳 Container Mode (Full Docker Stack)"
echo "3) 🛑 Stop all services"
echo "4) 🧹 Clean Session + Restart" 
read -p "Select option [1-4]: " opt

case $opt in
    1)
        echo -e "${GREEN}Starting LOCAL mode...${NC}"
        export RUNNING_IN_DOCKER=false
        
        # 1. הרמת מסדי הנתונים ב-Docker
        echo -e "${BLUE}📡 Starting Databases (Qdrant, Redis, Mongo)...${NC}"
        docker-compose up -d qdrant redis mongodb
        
        # 2. בדיקה והתקנה של ה-Venv
        if [ ! -d "venv" ]; then
            echo -e "${YELLOW}Creating virtual environment...${NC}"
            python3 -m venv venv
        fi
        
        source venv/bin/activate
        echo -e "${YELLOW}Checking dependencies...${NC}"
        pip install -r requirements.txt | grep -v 'already satisfied'

        # 3. בדיקת זמינות ה-DB (חשוב מאוד לפני הרצת ה-API)
        echo -e "${YELLOW}Waiting for databases to be ready...${NC}"
        sleep 3

        # 4. הרצת ה-API ברקע
        echo -e "${BLUE}⚙️  Starting FastAPI Backend...${NC}"
        python3 -m uvicorn app.main:app --reload --port 8000 &
        API_PID=$!
        
        # 5. הרצת ה-UI (Streamlit)
        echo -e "${BLUE}🖥️  Starting Streamlit UI...${NC}"
        # מוודא ש-Streamlit מזהה את ה-Python הנכון
        python3 -m streamlit run app/ui/main_ui.py --server.port 8501
        
        # ניקוי בסיום (הריגת ה-API כשסוגרים את ה-UI)
        trap "kill $API_PID" EXIT
        ;;
    2)
        echo -e "${GREEN}Starting FULL DOCKER mode...${NC}"
        export RUNNING_IN_DOCKER=true
        docker-compose up --build
        ;;
    3)
        echo -e "${RED}Stopping all services...${NC}"
        docker-compose down
        ;;
    4)
        echo -e "${YELLOW}🧹 Cleaning session state...${NC}"
        docker-compose down
        rm -rf ~/.streamlit/credentials.toml 
        docker volume prune -f
        echo -e "${GREEN}✅ Cleaned! Run option 2 now.${NC}"
        ;;
    *)
        echo "Invalid option"
        ;;
esac
