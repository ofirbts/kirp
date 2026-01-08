# app/scripts/offline_learn.py
from app.core.persistence import PersistenceManager
from app.core.offline_learning import OfflineLearner


def main():
    events = PersistenceManager.read_events(limit=200_000)
    learner = OfflineLearner()
    report = learner.analyze(events)

    print("=== OFFLINE LEARNING REPORT ===")
    for k, v in report.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
