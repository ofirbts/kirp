import time
import requests

BASE = "http://127.0.0.1:8000"

def main():
    print("=== LOAD TEST (1000 queries) ===")
    start = time.time()

    for i in range(1000):
        requests.post(BASE + "/agent/query", json={"question": f"test {i}"})

    end = time.time()
    print("Total time:", end - start)
    print("Avg per query:", (end - start) / 1000)

if __name__ == "__main__":
    main()
