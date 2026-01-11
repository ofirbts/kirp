import redis
import json
from typing import Any, Dict, List

from app.llm.client import get_llm
from app.core.persistence import PersistenceManager
from app.core.explainability import ExplanationBuilder
from app.core.metrics import Metrics
from app.core.observability import Observability
from app.core.invariants import assert_invariant
from app.core.memory_hub import MemoryHub
from app.core.intent_engine import IntentEngine

AGENT_PROMPT = """
You are an intelligent, precise assistant.

Context:
{context}

Answer clearly and concisely.
"""

class Agent:
    def __init__(self) -> None:
        self.metrics = Metrics()
        self.observability = Observability()
        self.explainer = ExplanationBuilder()
        self.memory_hub = MemoryHub()
        self.intent_engine = IntentEngine()
        
        # חיבור ל-Redis לצורך עדכון ה-UI
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

        self._state: Dict[str, Any] = {
            "total_queries": 0,
            "last_answer": None,
        }

    # ---------- State ----------

    def dump_state(self) -> Dict[str, Any]:
        return {"state": self._state}

    def load_state(self, data: Dict[str, Any]) -> None:
        self._state = data.get("state", self._state)

    def reset(self) -> None:
        self._state = {"total_queries": 0, "last_answer": None}

    # ---------- Core Query ----------

    async def query(self, question: str) -> Dict[str, Any]:
        try:
            # 1. זיהוי כוונה
            intent = self.intent_engine.classify(question)

            # עדכון UI ב-Redis - הודעה שהתקבלה שאילתה
            self._push_to_ui("processing", {"query": question, "intent": intent["intent"]})

            # 2. טיפול במקרים של התעלמות
            if intent["intent"] == "ignore":
                return {
                    "answer_text": "👍",
                    "sources": [],
                    "explanation": None,
                }

            # 3. שמירת זיכרון (החשוד העיקרי בקריסה שלך)
            if intent["intent"] == "store_memory":
                memory_id = self.memory_hub.add_text(
                    content=question,
                    source="user",
                    tier=intent.get("tier", "short"),
                    session_id="default",
                )

                PersistenceManager.append_event(
                    "memory_stored",
                    {
                        "content": question,
                        "tier": intent.get("tier", "short"),
                        "memory_id": memory_id,
                    },
                )
                
                # עדכון UI ב-Redis - נשמר זיכרון
                self._push_to_ui("memory_stored", {"content": question})

                return {
                    "answer_text": "🧠 נשמר. אזכור את זה.",
                    "sources": [],
                    "explanation": {
                        "type": "intent_store",
                        "reason": "User explicitly asked to remember",
                    },
                }

            # 4. שאילתה רגילה (RAG)
            assert_invariant(question, "Query cannot be empty")

            self.metrics.inc("queries")
            self.observability.record_query()

            # חיפוש בזיכרון
            memories = self.memory_hub.search(question, k=5)
            context = "\n".join(m["text"] for m in memories) if memories else ""

            # קריאה ל-LLM
            llm = get_llm()
            answer = await llm.apredict(
                AGENT_PROMPT.format(context=context)
            )

            self._state["total_queries"] += 1
            self._state["last_answer"] = answer

            explanation = self.explainer.explain(
                reason="RAG answer",
                inputs={"query": question, "memories": len(memories)},
                outcome={"answer": answer},
            )

            PersistenceManager.append_event(
                "agent_query",
                {
                    "query": question,
                    "memories": len(memories),
                },
            )

            # עדכון סופי ל-UI - תשובה מוכנה
            self._push_to_ui("completed", {"query": question, "answer": answer})

            return {
                "answer_text": answer,
                "sources": memories,
                "explanation": explanation,
            }

        except Exception as e:
            # הדפסה בולטת במיוחד לטרמינל כדי לאתר את השגיאה
            print("\n" + "="*50)
            print(f"❌ AGENT ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            print("="*50 + "\n")
            
            # זריקת השגיאה הלאה כדי ש-FastAPI ידע שהייתה בעיה
            raise e
        self._push_to_ui("completed", {"query": question, "answer": answer})
        
    def _push_to_ui(self, status: str, data: dict):
        """פונקציית עזר לדחיפת נתונים ל-Redis עבור ה-UI"""
        try:
            payload = json.dumps({"status": status, **data})
            self.redis_client.lpush("kirp:memory:recent", payload)
            self.redis_client.ltrim("kirp:memory:recent", 0, 19) # שומר 20 פעולות אחרונות
        except Exception as e:
            print(f"Failed to push to Redis UI: {e}")

agent = Agent()