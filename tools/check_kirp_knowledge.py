import json

def main():
    print("=== KNOWLEDGE INTEGRITY TEST ===")

    with open("storage/knowledge.json") as f:
        data = json.load(f)

    print("Total entries:", len(data))

    for i, entry in enumerate(data[-10:]):
        assert "content" in entry
        assert "source" in entry
        assert "ts" in entry
        print(f"Entry {i} OK")

if __name__ == "__main__":
    main()
