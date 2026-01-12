import logging
from app.llm.client import get_llm
from app.core.memory_hub import MemoryHub
from app.core.intent_engine import IntentEngine
from app.integrations.whatsapp_gateway import get_whatsapp_gateway

logger = logging.getLogger(__name__)

AGENT_PROMPT = """You are KIRP OS.
Use the provided context to answer accurately.

Context:
{context}

Question:
{question}

Answer:
"""

class Agent:
    def __init__(self):
        self.memory = MemoryHub()
        self.intent_engine = IntentEngine()
        self.whatsapp = get_whatsapp_gateway()

    async def query(self, question: str, sender_phone: str | None = None):
        intent = self.intent_engine.classify(question)

        if intent["intent"] == "store_memory":
            self.memory.add_text(question, source="user", tier=intent.get("tier", "short"))
            answer = "🧠 הזיכרון נשמר בהצלחה."
            sources = []
        else:
            memories = self.memory.search(question, k=3)
            context = "\n".join(m["text"] for m in memories)
            prompt = AGENT_PROMPT.format(context=context, question=question)
            answer = await get_llm().apredict(prompt)
            sources = memories

        if sender_phone:
            self.whatsapp.send_message(to=sender_phone, text=answer)

        return {
            "answer_text": answer,
            "sources": sources
        }

agent = Agent()
