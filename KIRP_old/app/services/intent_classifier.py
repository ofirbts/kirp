from enum import Enum

class IntentType(str, Enum):
    MEMORY = "memory"
    TASK = "task"
    BOTH = "both"
    QUERY = "query"
    CALENDAR = "calendar"
    LIST = "list"

class IntentClassifier:
    TASK_KEYWORDS = [
        "צריך", "לעשות", "להכין", "לטפל", "משימות",
        "todo", "to do", "plan", "prepare"
    ]

    CALENDAR_KEYWORDS = [
        "פגישה", "יומן", "ביום", "בשעה",
        "meeting", "schedule"
    ]

    LIST_KEYWORDS = [
        "רשימה", "list", "checklist"
    ]

    def classify(self, text: str) -> IntentType:
        lowered = text.lower()

        if any(k in lowered for k in self.CALENDAR_KEYWORDS):
            return IntentType.CALENDAR

        if any(k in lowered for k in self.LIST_KEYWORDS):
            return IntentType.LIST

        if any(k in lowered for k in self.TASK_KEYWORDS):
            return IntentType.BOTH

        return IntentType.MEMORY
