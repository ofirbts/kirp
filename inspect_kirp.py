import os
import re

# הגדרות הצבעים לטרמינל
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# הגדרות החיפוש
ALERTS = ["print\(", "DEBUG", "status =", "event =", "processing", "demo", "test", "TODO", "pass"]
SUSPECTS = ["redis\.lpush", "FAISS\.from_texts", "eval\(", "except:.*pass", "if False:"]

def inspect_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.splitlines()

    stats = {"alerts": [], "suspects": [], "imports": []}
    
    # ניתוח imports (למי הוא מחובר)
    stats["imports"] = re.findall(r"from app\.(.*?) import", content)
    
    for i, line in enumerate(lines):
        # חיפוש אדומים
        for pattern in ALERTS:
            if re.search(pattern, line):
                stats["alerts"].append((i+1, line.strip(), pattern))
        
        # חיפוש צהובים (חריג: redis בתוך memory_redis זה חוקי)
        for pattern in SUSPECTS:
            if re.search(pattern, line):
                if "redis" in pattern and "memory_redis.py" in file_path: continue
                if "FAISS" in pattern and "vector_store.py" in file_path: continue
                stats["suspects"].append((i+1, line.strip(), pattern))
    
    return stats

def run_inspector():
    project_root = "./app"
    print(f"{BOLD}{BLUE}=== KIRP OS ARCHITECTURE INSPECTOR ==={RESET}\n")
    
    for root, dirs, files in os.walk(project_root):
        for file in files:
            if file.endswith(".py") and "__init__" not in file:
                path = os.path.join(root, file)
                res = inspect_file(path)
                
                # קביעת ציון לקובץ
                color = GREEN
                status = "✅ CLEAN CORE"
                if res["alerts"]: 
                    color = RED
                    status = "🚨 CONTAINS JUNK"
                elif res["suspects"]:
                    color = YELLOW
                    status = "⚠️ ARCHITECTURAL LEAK"
                
                print(f"{BOLD}{color}[{status}]{RESET} {path}")
                print(f"   🔗 Connected to: {', '.join(res['imports']) if res['imports'] else 'None'}")
                
                for line_num, text, pat in res["alerts"]:
                    print(f"   {RED}  L{line_num}: found '{pat}' -> {text}{RESET}")
                for line_num, text, pat in res["suspects"]:
                    print(f"   {YELLOW}  L{line_num}: leak '{pat}' -> {text}{RESET}")
                print("-" * 50)

if __name__ == "__main__":
    run_inspector()