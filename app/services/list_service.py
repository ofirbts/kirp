class ListService:
    @staticmethod
    def extract_and_create(text: str) -> list:
        # דוגמה:
        return [{
            "name": "Auto List",
            "items": [
                line.strip("- ")
                for line in text.splitlines()
                if line.strip()
            ]
        }]
