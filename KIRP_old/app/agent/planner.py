from typing import Dict

class PlannerAgent:
    def plan(self, question: str, user_id: str) -> Dict:
        # המתכנן מעביר את ה-user_id הלאה לכל שלבי הביצוע
        return {
            "action": "answer",
            "query": question,
            "user_id": user_id
        }