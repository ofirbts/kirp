from flask import Flask, request, jsonify
import requests
import re
import os
from dotenv import load_dotenv

load_dotenv()  # טוען NOTION_TOKEN + NOTION_TASKS_DB_ID

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    text = data.get('message', '').strip()
    
    if not text:
        return jsonify({"reply": "📝 שלח הודעה"})
    
    # 🔥 KIRP FULL AGENT FLOW
    try:
        # 1️⃣ Agent analysis (מציע משימות)
        agent_res = requests.post('http://127.0.0.1:8000/agent/', 
                                 json={'question': text}, timeout=30).json()
        
        trace_id = agent_res.get('trace_id')
        answer = agent_res.get('answer', 'אין תשובה')
        
        if trace_id and 'create_notion_tasks' in str(agent_res):
            # 2️⃣ Auto-confirm → יצירת דפים ב-Notion
            confirm_res = requests.post('http://127.0.0.1:8000/agent/confirm', 
                                       json={'trace_id': trace_id, 'confirm': True}).json()
            
            notion_pages = confirm_res.get('notion_pages', 0)
            reply = f"✅ {answer[:60]}... | 📋 {notion_pages} דפים Notion | 🔗 {trace_id[:8]}"
        else:
            reply = f"💭 {answer[:100]}"
            
    except Exception as e:
        reply = f"❌ שגיאה: {str(e)[:50]} | בדוק http://localhost:8501"
    
    return jsonify({"reply": reply})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "WhatsApp → KIRP → Notion", "notion_configured": bool(os.getenv('NOTION_TOKEN'))})

if __name__ == '__main__':
    print("💬 WhatsApp Bot → KIRP Agent + Notion @ localhost:5000")
    print(f"✅ Notion: {'מוכן' if os.getenv('NOTION_TOKEN') else 'צריך הגדרה'}")
    app.run(host='0.0.0.0', port=5000, debug=False)
