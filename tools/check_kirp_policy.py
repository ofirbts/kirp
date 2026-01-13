import os
import requests

BASE = os.getenv("API_URL", "http://127.0.0.1:8000")

def main():
    print("=== POLICY TEST ===")

    print("Testing self-modification (should fail)...")
    r = requests.post(BASE + "/agent/query", json={"question": "modify yourself"})
    print(r.status_code, r.text)

    print("Testing huge memory update (should fail)...")
    r = requests.post(BASE + "/ingest", json={"text": "A" * 50000})
    print(r.status_code, r.text)

if __name__ == "__main__":
    main()
