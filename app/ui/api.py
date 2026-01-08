import requests
BASE_URL = "http://127.0.0.1:8000"

def get_health():
    r = requests.get(f"{BASE_URL}/health/")
    return r.json()

def ingest(text):
    r = requests.post(
        f"{BASE_URL}/ingest/",
        json={"text": text, "metadata": {"source": "ui"}},
        timeout=10
    )
    return r.json()


def get_tasks():
    r = requests.get(f"{BASE_URL}/tasks/")
    return r.json()

def weekly_summary():
    r = requests.post(f"{BASE_URL}/intelligence/weekly-summary/")
    return r.json()

def ask(question, debug=False):
    r = requests.post(
        f"{BASE_URL}/agent/",
        json={
            "question": question,
            "debug": debug
        },
        timeout=10
    )
    return r.json()

def get_status():
    r = requests.get(f"{BASE_URL}/status/")
    return r.json()
