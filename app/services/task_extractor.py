import re

class TaskExtractor:
    def extract(self, text: str):
        tasks = []

        patterns = [
            r"צריך\s+(.*)",
            r"להכין\s+(.*)",
            r"to\s+do\s+(.*)",
            r"prepare\s+(.*)"
        ]

        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                tasks.append({
                    "title": match.group(1).strip(),
                })

        return tasks
