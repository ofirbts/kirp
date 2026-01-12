import traceback
import asyncio
import inspect
import sys
import os  # חדש

# ---------------------------------------------------
# 0) ANSI COLORS
# ---------------------------------------------------
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


print(f"\n{BOLD}{CYAN}=== KIRP DEEP TEST SUITE START ==={RESET}\n")

# ---------------------------------------------------
# 1) PATCHES / MOCKS – חשוב: לפני imports של Agent/MemoryHub
# ---------------------------------------------------

# 1.0 – Mock ל-Embeddings כדי שלא נצטרך OPENAI_API_KEY
class EmbeddingsMock:
    def __call__(self, text):
        # מאפשר להשתמש בו כ-embedding_function(text)
        return [0.0] * 10

    def embed_documents(self, texts):
        return [[0.0] * 10 for _ in texts]

    def embed_query(self, text):
        return [0.0] * 10


try:
    from app.rag import embedder
    embedder.get_embeddings = lambda: EmbeddingsMock()
    # נוודא גם שלא ייתקע על משתנה סביבה
    os.environ["OPENAI_API_KEY"] = "TEST_KEY_FOR_UNIT_TESTS"
    print(f"{GREEN}✔ Patched Embeddings with EmbeddingsMock{RESET}")
except Exception as e:
    print(f"{YELLOW}⚠ לא הצלחתי לפאצ'ר app.rag.embedder – בדיקות add_text עלולות לנסות Embeddings אמיתי. ({e}){RESET}")


# 1.1 – Vector Store Mock
class VectorStoreMock:
    def __init__(self):
        self.docs = []

    def similarity_search_with_score(self, query, k=5):
        # מחזיר רשימה ריקה – מספיק כדי לא להפיל את MemoryHub
        return []

    @property
    def docstore(self):
        class DS:
            _dict = {}
        return DS()

try:
    from app.rag import vector_store
    vector_store._store = VectorStoreMock()
    vector_store.get_vector_store = lambda: vector_store._store
    print(f"{GREEN}✔ Patched VectorStore with VectorStoreMock{RESET}")
except Exception as e:
    print(f"{YELLOW}⚠ לא הצלחתי לטעון app.rag.vector_store – חלק מהבדיקות ידלגו. ({e}){RESET}")


# 1.2 – LLM Mock (למנוע קריאה אמיתית ל־OpenAI)
class LLMClientMock:
    async def apredict(self, prompt: str) -> str:
        if "Context:" in prompt:
            return "Mocked answer based on context."
        return "Mocked LLM answer."

llm_patched = False
try:
    from app.llm import client as llm_client_module

    def get_llm_mock():
        return LLMClientMock()

    llm_client_module.get_llm = get_llm_mock
    llm_patched = True
    print(f"{GREEN}✔ Patched LLM client with LLMClientMock{RESET}")
except Exception as e:
    print(f"{YELLOW}⚠ לא הצלחתי לטעון app.llm.client – בדיקות Agent ייתכן שיקראו ל־LLM אמיתי. ({e}){RESET}")

# ---------------------------------------------------
# 2) IMPORTS – עכשיו כשה־Mocks בפנים
# ---------------------------------------------------

errors_in_imports = []

try:
    from app.core.intent_engine import IntentEngine
    print(f"{GREEN}✔ Loaded IntentEngine{RESET}")
except Exception as e:
    print(f"{RED}✘ Failed to import IntentEngine: {e}{RESET}")
    traceback.print_exc()
    errors_in_imports.append("IntentEngine")
    IntentEngine = None

try:
    from app.agent.agent import agent
    print(f"{GREEN}✔ Loaded Agent{RESET}")
except Exception as e:
    print(f"{RED}✘ Failed to import Agent: {e}{RESET}")
    traceback.print_exc()
    errors_in_imports.append("Agent")
    Agent = None

try:
    from app.core.memory_hub import MemoryHub
    print(f"{GREEN}✔ Loaded MemoryHub{RESET}")
except Exception as e:
    print(f"{RED}✘ Failed to import MemoryHub: {e}{RESET}")
    traceback.print_exc()
    errors_in_imports.append("MemoryHub")
    MemoryHub = None

try:
    from app.core.persistence import PersistenceManager
    print(f"{GREEN}✔ Loaded PersistenceManager{RESET}")
except Exception as e:
    print(f"{RED}✘ Failed to import PersistenceManager: {e}{RESET}")
    traceback.print_exc()
    errors_in_imports.append("PersistenceManager")
    PersistenceManager = None

# ננסה לטעון RAG (אם קיים)
try:
    from app.rag.retriever import retrieve_context
    from app.rag.rag_engine import generate_answer
    rag_available = True
    print(f"{GREEN}✔ Loaded RAG components (retriever + rag_engine){RESET}")
except Exception as e:
    rag_available = False
    print(f"{YELLOW}⚠ RAG components not fully available: {e}{RESET}")


# ---------------------------------------------------
# 3) TEST REGISTRATION INFRA
# ---------------------------------------------------

results = []

def test(name):
    """Decorator לרישום בדיקות."""
    def wrapper(func):
        results.append((name, func))
        return func
    return wrapper


# ---------------------------------------------------
# 4) TESTS – INTENT ENGINE
# ---------------------------------------------------
if IntentEngine is not None:

    @test("IntentEngine – store_memory (Hebrew, long tier)")
    def _():
        ie = IntentEngine()
        r = ie.classify("תזכור שהפרויקט הזה נקרא KIRP")
        assert r["intent"] == "store_memory", r
        assert r["tier"] in ("short", "long"), r

    @test("IntentEngine – store_memory (English)")
    def _():
        ie = IntentEngine()
        r = ie.classify("remember this please")
        assert r["intent"] == "store_memory", r

    @test("IntentEngine – ignore intent")
    def _():
        ie = IntentEngine()
        r = ie.classify("ok thanks")
        assert r["intent"] == "ignore", r

    @test("IntentEngine – answer_only default")
    def _():
        ie = IntentEngine()
        r = ie.classify("מה מזג האוויר?")
        assert r["intent"] == "answer_only", r

else:
    print(f"{YELLOW}⚠ Skipping IntentEngine tests – import failed{RESET}")


# ---------------------------------------------------
# 5) TESTS – MEMORY HUB
# ---------------------------------------------------
if MemoryHub is not None:

    @test("MemoryHub – add_text basic + no crash")
    def _():
        hub = MemoryHub()
        added = hub.add_text("זה טקסט לבדיקה", source="test")
        # dedup יכול להחזיר None, אז נבדוק שאין קריסה:
        assert "added" in hub._stats
        assert isinstance(hub._stats["added"], int)

    @test("MemoryHub – search does not crash")
    def _():
        hub = MemoryHub()
        res = hub.search("טקסט", k=3)
        assert isinstance(res, list)

    @test("MemoryHub – snapshot safe")
    def _():
        hub = MemoryHub()
        snap = hub.snapshot(limit=10)
        assert "stats" in snap
        assert "recent_memories" in snap

else:
    print(f"{YELLOW}⚠ Skipping MemoryHub tests – import failed{RESET}")


# ---------------------------------------------------
# 6) TESTS – PERSISTENCE
# ---------------------------------------------------
if PersistenceManager is not None:

    @test("Persistence – event writing + reading")
    def _():
        event_id = PersistenceManager.append_event("test_event", {"x": 1})
        events = PersistenceManager.read_events(limit=50)
        assert any(ev["id"] == event_id for ev in events)

else:
    print(f"{YELLOW}⚠ Skipping Persistence tests – import failed{RESET}")


# ---------------------------------------------------
# 7) TESTS – AGENT CORE FLOWS
# ---------------------------------------------------
if Agent is not None:

    @test("Agent – ignore flow returns 👍")
    def _():
        agent = Agent()
        result = asyncio.run(agent.query("ok"))
        assert result["answer_text"] == "👍", result

    @test("Agent – store_memory flow returns 🧠")
    def _():
        agent = Agent()
        result = asyncio.run(agent.query("תזכור שהפרויקט הזה נקרא KIRP"))
        assert "🧠" in result["answer_text"], result
        # לא נוודא Vector Store, אבל נוודא שלא קרס

    @test("Agent – answer_only flow with RAG (mocked LLM)")
    def _():
        agent = Agent()
        result = asyncio.run(agent.query("מה זה KIRP?"))
        assert "answer_text" in result
        assert "sources" in result

else:
    print(f"{YELLOW}⚠ Skipping Agent tests – import failed{RESET}")


# ---------------------------------------------------
# 8) TESTS – RAG (אם זמין)
# ---------------------------------------------------
if rag_available:

    @test("RAG – retrieve_context does not crash")
    def _():
        res = retrieve_context("KIRP", k=3)
        assert isinstance(res, list)

    @test("RAG – generate_answer returns string")
    def _():
        ctx = retrieve_context("KIRP", k=3)
        ans = generate_answer(ctx, "What is KIRP?")
        assert isinstance(ans, str)

else:
    print(f"{YELLOW}⚠ Skipping RAG tests – components missing{RESET}")


# ---------------------------------------------------
# 9) META TEST – SOURCE MAPPING / DIAGNOSTICS
# ---------------------------------------------------

@test("Meta – IntentEngine comes from correct file")
def _():
    if IntentEngine is None:
        raise AssertionError("IntentEngine not imported")
    import app.core.intent_engine as ie_mod
    path = inspect.getfile(ie_mod.IntentEngine)
    assert "intent_engine.py" in path


# ---------------------------------------------------
# 10) RUNNER
# ---------------------------------------------------

def run_all_tests():
    passed = 0
    failed = 0
    failures_detail = []

    print(f"\n{BOLD}==============================")
    print("   🔥 KIRP TEST SUITE 🔥")
    print("==============================\n" + RESET)

    for name, func in results:
        try:
            func()
            print(f"{GREEN}✔ {name}{RESET}")
            passed += 1
        except Exception as e:
            print(f"{RED}✘ {name}{RESET}")
            print(f"{RED}  → {e}{RESET}")
            traceback.print_exc()
            failed += 1
            failures_detail.append((name, e))

    print(f"\n{BOLD}==============================")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print("=============================={RESET}\n")

    if failed == 0:
        print(f"{GREEN}{BOLD}🎉 כל הבדיקות עברו בהצלחה! המפה נקייה.{RESET}")
    else:
        print(f"{RED}{BOLD}⚠ יש תקלות – מפת כשלים מפורטת:{RESET}\n")
        for name, e in failures_detail:
            print(f"{RED}- טסט: {name}{RESET}")
            print(f"  סוג שגיאה: {type(e).__name__}")
            print(f"  פירוט: {e}")
        print("\n" + f"{YELLOW}בדוק את ה־tracebacks למעלה לאבחנה מעמיקה יותר.{RESET}")


if __name__ == "__main__":
    run_all_tests()
    print(f"\n{BOLD}{CYAN}=== KIRP DEEP TEST SUITE END ==={RESET}\n")
