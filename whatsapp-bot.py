from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json() or {}
        text = data.get('message', '').strip()
        
        if not text:
            return jsonify({"reply": "📝 שלח הודעה"})
        
        # 🔥 קריאה ל-API החי
        resp = requests.post('http://127.0.0.1:8000/agent/', 
                           json={'question': text}, 
                           timeout=30)
        
        if resp.status_code != 200:
            return jsonify({"reply": f"❌ API {resp.status_code}"})
        
        result = resp.json()
        reply = result.get('answer', 'אין תשובה')[:100]
        
        return jsonify({"reply": f"✅ {reply} | 🔗 {result.get('trace_id', 'no-trace')[:8]}"})
    
    except requests.exceptions.ConnectionError:
        return jsonify({"reply": "❌ API 8000 לא זמין"})
    except Exception as e:
        return jsonify({"reply": f"❌ שגיאה: {str(e)[:50]}"})

@app.route('/health', methods=['GET'])
def health():
    try:
        api_status = requests.get('http://127.0.0.1:8000/health', timeout=5).status_code == 200
    except:
        api_status = False
    return jsonify({"status": "WhatsApp Bot", "api_alive": api_status})

if __name__ == '__main__':
    print("💬 WhatsApp Bot → KIRP @ localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
