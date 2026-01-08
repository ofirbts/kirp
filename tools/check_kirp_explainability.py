from app.core.persistence import PersistenceManager

def main():
    print("=== EXPLAINABILITY COMPLETENESS TEST ===")

    events = PersistenceManager.read_events(limit=200)

    explanations = [e for e in events if e["type"] == "explanation"]

    print("Total explanations:", len(explanations))

    for e in explanations[-10:]:
        payload = e["payload"]
        assert "reason" in payload
        assert "inputs" in payload
        assert "outcome" in payload
        print("Explanation OK:", payload["reason"])

if __name__ == "__main__":
    main()
