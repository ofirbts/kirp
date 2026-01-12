import os
import sys
import requests
import asyncio
import traceback
from datetime import datetime

# ANSI Colors for Pro Output
G, R, Y, C, B, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[96m", "\033[1m", "\033[0m"

class KIRPUltimateCheck:
    def __init__(self):
        self.results = []
        self.base_url = "http://127.0.0.1:8000"

    def log(self, category, name, status, detail=""):
        icon = f"{G}✔{RESET}" if status else f"{R}✘{RESET}"
        self.results.append({"cat": category, "name": name, "status": status})
        print(f"{icon} [{category}] {name} {f'-> {Y}{detail}{RESET}' if detail else ''}")

    async def run(self):
        print(f"\n{B}{C}🚀 STARTING KIRP ULTIMATE SYSTEM AUDIT{RESET}")
        print(f"Timestamp: {datetime.now().isoformat()}\n" + "="*50)

        # --- שלב 1: ארכיטקטורה וקבצים ---
        critical_files = [
            "app/main.py", "app/agent/agent.py", "app/rag/vector_store.py",
            "app/core/intent_engine.py", ".env", "docker-compose.yml"
        ]
        for f in critical_files:
            exists = os.path.exists(f)
            self.log("ARCH", f"File: {f}", exists, "" if exists else "MISSING!")

        # --- שלב 2: סביבה וקונפיגורציה ---
        load_dotenv_success = False
        try:
            from dotenv import load_dotenv
            load_dotenv()
            load_dotenv_success = True
        except: pass
        
        env_keys = ["OPENAI_API_KEY", "MONGO_URI", "NOTION_TOKEN"]
        for key in env_keys:
            val = os.getenv(key)
            self.log("ENV", f"Var: {key}", bool(val), "Check your .env" if not val else "Loaded")

        # --- שלב 3: בדיקת לוגיקה פנימית (MOCK) ---
        print(f"\n{B}🧠 Testing Core Logic (Intent/Agent)...{RESET}")
        try:
            from app.core.intent_engine import IntentEngine
            ie = IntentEngine()
            res = ie.classify("תזכור שהפרויקט נקרא KIRP")
            self.log("LOGIC", "Intent Classification", res["intent"] == "store_memory")
        except Exception as e:
            self.log("LOGIC", "Intent Engine", False, str(e))

        # --- שלב 4: בדיקת Live (אם הדוקר למעלה) ---
        print(f"\n{B}🌐 Testing Live Endpoints (Docker)...{RESET}")
        try:
            r = requests.get(f"{self.base_url}/health", timeout=2)
            self.log("LIVE", "API Health", r.status_code == 200)
        except:
            self.log("LIVE", "API Health", False, "Is Docker running?")

        # --- שלב 5: בדיקת אינטגרציית Notion ---
        print(f"\n{B}🔌 Checking Integrations...{RESET}")
        notion_file = "app/services/notion.py"
        file_exists = os.path.exists(notion_file)
        
        if file_exists:
            # בדיקה שהקובץ לא ריק ומכיל את המילים הנכונות
            with open(notion_file, "r") as f:
                content = f.read()
                is_valid = "class NotionService" in content and "notion =" in content
            self.log("INTEGRATION", "Notion Service File", is_valid, "File exists and is structured" if is_valid else "File structure issue")
        else:
            self.log("INTEGRATION", "Notion Service File", False, "Missing app/services/notion.py")
            
        self.summary()

    def summary(self):
        passed = len([r for r in self.results if r['status']])
        total = len(self.results)
        print("\n" + "="*50)
        print(f"{B}FINAL SUMMARY: {passed}/{total} Passed{RESET}")
        if passed == total:
            print(f"{G}{B}🎉 SYSTEM IS PRODUCTION READY!{RESET}")
        else:
            print(f"{R}{B}⚠️ SYSTEM HAS ISSUES - CHECK LOGS ABOVE{RESET}")
        print("="*50 + "\n")

if __name__ == "__main__":
    checker = KIRPUltimateCheck()
    asyncio.run(checker.run())