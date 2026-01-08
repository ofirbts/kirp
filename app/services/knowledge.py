import json
import os
from datetime import datetime

PATH = "storage/knowledge.json"

class KnowledgeStore:
    def __init__(self):
        if not os.path.exists(PATH):
            with open(PATH, "w") as f:
                json.dump([], f)

    def add(self, content: str, source: str):
        with open(PATH, "r") as f:
            data = json.load(f)

        data.append({
            "content": content,
            "source": source,
            "ts": datetime.utcnow().isoformat()
        })

        with open(PATH, "w") as f:
            json.dump(data, f, indent=2)

    def all(self):
        with open(PATH) as f:
            return json.load(f)
