import sys
import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

print("🧠 Initializing vector store for standalone script...")
try:
    from app.rag.vector_store import load_vector_store, debug_info
    load_vector_store()
    print("✅ Vector store ready:", debug_info())
except Exception as e:
    print("❌ Failed to initialize vector store:", e)

import json
import requests
from datetime import datetime

from app.rag.self_improving_agent import self_improving_query

# טעינת מודולים פנימיים
from app.rag import (
    retriever,
    retrieval_pipeline,
    rag_engine,
    agent_rag,
    long_term_memory,
    self_improving_agent,
)

API_URL = "http://127.0.0.1:8000"


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"🔍 {title}")
    print("=" * 60)


def module_exists(module):
    return module is not None


def check_functions(module, func_names):
    return {name: hasattr(module, name) for name in func_names}


def check_imports():
    print_header("MODULE IMPORT CHECK")

    modules = {
        "retriever": retriever,
        "retrieval_pipeline": retrieval_pipeline,
        "rag_engine": rag_engine,
        "agent_rag": agent_rag,
        "long_term_memory": long_term_memory,
        "self_improving_agent": self_improving_agent,
    }

    for name, mod in modules.items():
        print(f"Module {name}: exists={module_exists(mod)}")
        if name == "retriever":
            print("  Functions:", check_functions(mod, ["retrieve_context"]))
        if name == "retrieval_pipeline":
            print(
                "  Functions:",
                check_functions(
                    mod,
                    [
                        "retrieval_pipeline",
                        "semantic_dedup",
                        "logical_dedup",
                        "build_explanation",
                    ],
                ),
            )
        if name == "rag_engine":
            print(
                "  Functions:",
                check_functions(
                    mod,
                    [
                        "generate_answer",
                        "format_context_for_answer",
                    ],
                ),
            )
        if name == "agent_rag":
            print(
                "  Functions:",
                check_functions(
                    mod,
                    [
                        "detect_intents",
                        "agent_rag_pipeline",
                    ],
                ),
            )
        if name == "long_term_memory":
            print(
                "  Functions:",
                check_functions(
                    mod,
                    [
                        "update_session_memory",
                        "summarize_session",
                        "session_rag_pipeline",
                    ],
                ),
            )
        if name == "self_improving_agent":
            print(
                "  Functions:",
                check_functions(
                    mod,
                    [
                        "self_improving_query",
                    ],
                ),
            )


def check_vector_store():
    print_header("VECTOR STORE CHECK")

    try:
        from app.rag.vector_store import get_vector_store
        store = get_vector_store()
        count = store.index.ntotal
        print(f"✅ Vector store loaded successfully ({count} vectors)")
    except Exception as e:
        print(f"❌ Vector store error: {e}")


def check_faiss_integrity():
    print_header("FAISS INTEGRITY CHECK")

    try:
        from app.rag.vector_store import get_vector_store
        store = get_vector_store()

        results = store.similarity_search("test", k=1)
        if results:
            print("Sample search result:", results[0].page_content[:50], "...")
            print("✅ FAISS integrity OK")
        else:
            print("⚠️ FAISS returned no results for 'test'")
    except Exception as e:
        print("❌ FAISS integrity failed:", e)


def check_metadata_consistency():
    print_header("METADATA CONSISTENCY CHECK")

    try:
        from app.rag.vector_store import get_vector_store
        store = get_vector_store()
        docs = store.similarity_search("test", k=5)

        for doc in docs:
            meta = doc.metadata
            if not isinstance(meta, dict):
                print("❌ Metadata is not a dict:", meta)
                return
            if "id" not in meta:
                print("⚠️ Missing 'id' in metadata:", meta)
            if "embedding" not in meta:
                print("⚠️ Missing 'embedding' in metadata:", meta)

        print("✅ Metadata consistency OK")
    except Exception as e:
        print("❌ Metadata consistency failed:", e)


def check_embedding_shape():
    print_header("EMBEDDING SHAPE CHECK")

    try:
        from app.rag.vector_store import get_vector_store
        store = get_vector_store()
        docs = store.similarity_search("test", k=3)

        for doc in docs:
            emb = doc.metadata.get("embedding")
            if emb is None:
                print("⚠️ Missing embedding")
                continue
            if not isinstance(emb, list):
                print("❌ Embedding is not a list:", emb)
                return
            if len(emb) < 10:
                print("⚠️ Embedding seems too short:", len(emb))

        print("✅ Embedding shape OK")
    except Exception as e:
        print("❌ Embedding shape failed:", e)


def check_dedup_correctness():
    print_header("DEDUP CORRECTNESS CHECK")

    try:
        from app.rag.retrieval_pipeline import semantic_dedup

        sample = [
            {"text": "hello world", "embedding": [1, 0, 0]},
            {"text": "hello world", "embedding": [1, 0, 0]},
            {"text": "different text", "embedding": [0, 1, 0]},
        ]

        deduped = semantic_dedup(sample)
        if len(deduped) == 2:
            print("✅ Dedup correctness OK")
        else:
            print("❌ Dedup incorrect, length:", len(deduped), "data:", deduped)
    except Exception as e:
        print("❌ Dedup correctness failed:", e)


def check_api_query():
    print_header("API /query CHECK")

    payload = {
        "question": "How do we price the premium subscription?",
        "k": 3,
        "session_id": "healthcheck",
    }

    try:
        r = requests.post(f"{API_URL}/query/", json=payload)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print("✅ /query OK")
            if "answer_text" in data:
                print("Answer preview:", data["answer_text"][:120], "...")
            if "confidence_overall" in data:
                print("Confidence:", data["confidence_overall"])
            elif "explain_summary" in data and isinstance(
                data["explain_summary"], dict
            ):
                print(
                    "Confidence:",
                    data["explain_summary"].get("confidence_overall"),
                )
        else:
            print("❌ /query returned error:", r.text)
    except Exception as e:
        print("❌ /query failed:", e)


def check_latency():
    print_header("LATENCY CHECK")

    import time
    payload = {
        "question": "test latency",
        "k": 3,
        "session_id": "latency_test",
    }

    try:
        start = time.time()
        r = requests.post(f"{API_URL}/query/", json=payload)
        end = time.time()

        if r.status_code == 200:
            print(f"✅ Latency OK: {round(end - start, 3)}s")
        else:
            print(f"❌ Latency test failed: {r.text}")
    except Exception as e:
        print("❌ Latency test error:", e)


def check_memory_usage():
    print_header("MEMORY USAGE CHECK")

    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss / (1024 * 1024)
        print(f"Current memory usage: {round(mem, 2)} MB")
        print("✅ Memory usage check OK")
    except Exception as e:
        print("❌ Memory usage check failed:", e)


def check_api_stream():
    print_header("API /query/stream CHECK")

    payload = {
        "question": "How do we price the premium subscription?",
        "k": 3,
        "session_id": "healthcheck",
    }

    try:
        r = requests.post(
            f"{API_URL}/query/stream",
            json=payload,
            stream=True,
        )
        print(f"Status: {r.status_code}")

        if r.status_code != 200:
            print("❌ /query/stream error:", r.text)
            return

        print("Streaming first 5 chunks:")
        counter = 0
        for line in r.iter_lines():
            if line:
                print("  ", line.decode())
                counter += 1
                if counter >= 5:
                    break

        print("✅ /query/stream OK")

    except Exception as e:
        print("❌ /query/stream failed:", e)


def check_agent_pipeline():
    print_header("AGENT RAG CHECK")

    try:
        result = agent_rag.agent_rag_pipeline(
            "How do we price the premium subscription?",
            session_id="healthcheck_agent",
            k=3,
        )
        print("Answer preview:", result["answer_text"][:120], "...")
        print("Explain summary:", result.get("explain_summary"))
        print("✅ Agent pipeline OK")
    except Exception as e:
        print("❌ Agent pipeline failed:", e)


def check_long_term_memory():
    print_header("LONG TERM MEMORY CHECK")

    try:
        result = long_term_memory.session_rag_pipeline(
            "How do we price the premium subscription?",
            session_id="healthcheck_ltm",
            k=3,
        )
        print(
            "Session summary preview:",
            result["session_summary"][:120],
            "...",
        )
        print("✅ Long-term memory OK")
    except Exception as e:
        print("❌ Long-term memory failed:", e)


def check_self_improving():
    print_header("SELF IMPROVING AGENT CHECK")

    try:
        result = self_improving_agent.self_improving_query(
            "How do we price the premium subscription?",
            session_id="healthcheck_self",
            k=3,
            feedback=0.9,
        )
        explain = result.get("explain_summary", {})
        print(
            "Adjusted confidence:",
            explain.get("confidence_overall"),
        )
        print("✅ Self-improving agent OK")
    except Exception as e:
        print("❌ Self-improving agent failed:", e)


def test_basic_rag():
    print_header("BASIC RAG RETRIEVAL TEST")

    session_id = "test_session_full"
    question = "What is the pricing plan for premium users?"
    print("=== Testing basic RAG retrieval ===")
    memories = retriever.retrieve_context(question, k=5)
    print(f"Retrieved {len(memories)} memories")
    answer_text = rag_engine.generate_answer(memories, question)
    print("Generated answer:\n", answer_text[:300], "...\n")


def test_self_improving_local():
    print_header("SELF IMPROVING (LOCAL PIPELINE) TEST")

    session_id = "test_session_full"
    question = "How should we price the premium subscription?"
    print("=== Testing self-improving agent ===")
    result = self_improving_query(question, session_id, k=5, feedback=0.9)
    print("Answer text:", result["answer_text"][:300], "...")
    explain = result.get("explain_summary", {})
    print("Confidence overall:", explain.get("confidence_overall"))
    print("Session summary:", result["session_summary"][:300], "...")


def main():
    print("\n=== KIRP FULL SYSTEM CHECK ===\n")

    check_imports()
    check_vector_store()
    check_api_query()
    check_api_stream()
    check_agent_pipeline()
    check_long_term_memory()
    check_self_improving()
    check_latency()
    check_memory_usage()
    check_faiss_integrity()
    check_metadata_consistency()
    check_embedding_shape()
    check_dedup_correctness()
    test_basic_rag()
    test_self_improving_local()

    print("\n=== DONE ===\n")


if __name__ == "__main__":
    main()
