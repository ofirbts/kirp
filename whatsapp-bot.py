from flask import Flask, request
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    text = data['message']
    
    # Forward to KIRP
    kirp_response = requests.post(
        'http://127.0.0.1:8000/ingest/',
        json={'text': text}
    ).json()
    
    return {"reply": f"✅ Saved: {kirp_response['memory_type']}"}

if __name__ == '__main__':
    app.run(port=5000)
