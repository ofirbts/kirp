import os
import sys

def check_kirp_readiness():
    required_paths = [
        "data/knowledge_base",
        "data/profiles",
        "logs"
    ]
    
    print("🔍 Starting KIRP System Health Check...")
    
    # 1. בדיקת תיקיות
    for path in required_paths:
        if not os.path.exists(path):
            print(f"⚠️ Path missing: {path}. Creating it...")
            os.makedirs(path, exist_ok=True)
        else:
            print(f"✅ {path} is ready.")

    # 2. בדיקת קובץ ה-Roadmap הקבוע
    roadmap_path = "data/knowledge_base/company_roadmap.md"
    if not os.path.exists(roadmap_path):
        print(f"📝 Creating initial roadmap at {roadmap_path}...")
        with open(roadmap_path, "w") as f:
            f.write("# KIRP Roadmap\n\n- [ ] System Initialized")
    
    # 3. בדיקת קובץ ה-Persona (אם קיים)
    persona_path = "data/profiles/ofir.json"
    if not os.path.exists(persona_path):
        print(f"👤 Warning: Persona file {persona_path} not found. Agent will use default profile.")

    print("\n🚀 System is ready to boot!")

if __name__ == "__main__":
    check_kirp_readiness()