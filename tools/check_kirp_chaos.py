import random
import requests
from pprint import pprint

BASE = "http://127.0.0.1:8000"

def chaos_ingest():
    texts = [
        "", " ", None, 123, {}, [], "A" * 50000,
        "🔥 Chaos test", "שלום", "💥💥💥", "DROP TABLE users;"
    ]
    t = random.choice(texts)
    try:
        r = requests.post(BASE + "/ingest", json={"text": t})
        return r.status_code, r.text
    except Exception as e:
        return "ERROR", str(e)

def main():
    print("=== CHAOS TEST ===")
    for i in range(20):
        print(f"\n--- Chaos iteration {i} ---")
        pprint(chaos_ingest())

if __name__ == "__main__":
    main()
