import re
from typing import Dict

class IntentEngine:
    """Classifies user intent to decide which tools or logic to invoke."""
    
    STORE_PATTERNS = [r"תזכור", r"תשמור", r"save", r"remember", r"store"]
    ANALYZE_PATTERNS = [r"סכם", r"תנתח", r"summarize", r"analyze", r"list", r"רשימה"]

    def classify(self, text: str) -> Dict[str, str]:
        lowered = text.lower().strip()
        
        for p in self.ANALYZE_PATTERNS:
            if re.search(p, lowered):
                return {"intent": "analyze_context"}
                
        for p in self.STORE_PATTERNS:
            if re.search(p, lowered):
                return {"intent": "store_memory"}
                
        return {"intent": "query_memory"}