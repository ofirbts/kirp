import logging
from app.llm.client import get_llm
from app.core.memory_hub import MemoryHub
from app.core.intent_engine import IntentEngine
from app.integrations.whatsapp_gateway import get_whatsapp_gateway

logger = logging.getLogger(__name__)

AGENT_PROMPT = """You are KIRP OS. Answer based on context:
Context: {context}
Question: {question}
Answer:"""

class Agent:
    def __init__(self):
        self.memory_hub = MemoryHub()
        self.intent_engine = IntentEngine()
        self.whatsapp = get_whatsapp_gateway()

    async def query(self, question: str, sender_phone: str = None) -> dict:
        intent = self.intent_engine.classify(question)
        
        if intent["intent"] == "store_memory":
            self.memory_hub.add_text(question, source="user")
            ans = "🧠 זיכרון נשמר במערכת KIRP."
        else:
            memories = self.memory_hub.search(question, k=3)
            context = "\n".join([m['text'] for m in memories])
            ans = await get_llm().apredict(AGENT_PROMPT.format(context=context, question=question))

        # שליחה לוואטסאפ אם יש מספר שולח
        if sender_phone:
            self.whatsapp.send_message(to=sender_phone, text=ans)
            
        return {"answer_text": ans, "sources": memories if intent["intent"] != "store_memory" else []}

agent = Agent()
