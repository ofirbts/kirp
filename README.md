# KIRP – Retrieval-Augmented Generation Backend

KIRP is a modular backend system implementing a full **Retrieval-Augmented Generation (RAG)** pipeline.
It is designed as a foundation for personal knowledge management systems that transform unstructured data into queryable intelligence.

---

## Project Overview

The system ingests raw text data, embeds it into a vector space, stores it in a FAISS vector database, and enables natural-language querying via a Large Language Model (LLM) using retrieved context.

This project focuses on **clarity of architecture**, **observability**, and **extensibility**, rather than a single demo script.

---

## Core RAG Flow

1. **Ingest** unstructured text data via API  
2. **Chunk & Embed** text using an embedding model  
3. **Store** embeddings in a FAISS vector store  
4. **Retrieve** relevant chunks based on user questions  
5. **Generate** grounded answers using an LLM  

---

## Architecture

app/
├── api/
│ ├── ingest.py # Data ingestion endpoints
│ ├── query.py # RAG query endpoint
│ ├── debug.py # Observability & diagnostics
│ └── health.py # Health checks
│
├── rag/
│ ├── embedder.py # Embedding model logic
│ ├── vector_store.py # FAISS vector store handling
│ └── qa_engine.py # Retrieval + LLM answering
│
├── storage/
│ └── jobs.py # (Optional) background job tracking
│
├── main.py # FastAPI application entry point


---

## Observability & Debugging

The system includes dedicated debug endpoints to inspect internal state:

- Vector store initialization status
- Number of indexed vectors

This makes the system explainable, testable, and production-oriented.

---

## API Endpoints

| Endpoint | Method | Description |
|-------|------|-----------|
| `/ingest/` | POST | Ingest new knowledge |
| `/query/` | POST | Ask questions over stored knowledge |
| `/debug/vector-store` | GET | Inspect vector store state |
| `/health/` | GET | Health check |

---

## Tech Stack

- **FastAPI** – Backend framework  
- **LangChain** – RAG orchestration  
- **FAISS** – Vector similarity search  
- **Python 3.10+**

---

## Current Status

✅ End-to-end RAG pipeline operational  
✅ Modular, extensible architecture  
🔜 Persisted vector store  
🔜 Metadata enrichment & evaluation  
🔜 Multi-source ingestion (email, notes, documents)

---

## Vision

KIRP is designed to evolve into a personal knowledge intelligence system that:
- Synchronizes data from multiple sources
- Categorizes and connects ideas
- Exports structured knowledge to tools like Notion or Obsidian

---

## Running the Project

uvicorn app.main:app --reload

Then open:
http://127.0.0.1:8000/docs

## Author

Ofir Betesh
## 🎬 LIVE DEMO

### 1. Ingest Memory
```bash
curl -X POST "http://127.0.0.1:8000/ingest/" -H "Content-Type: application/json" -d '{"text":"Buy milk tomorrow"}'
# → {"memory_type":"task","chunks_added":1}
2. Agent Discovery
bash
curl -X POST "http://127.0.0.1:8000/agent/" -H "Content-Type: application/json" -d '{"question":"What tasks?"}'
# → "Found 1 tasks. Suggestion: create_notion_tasks"
3. Execute Action
bash
curl -X POST "http://127.0.0.1:8000/agent/confirm/TRACE_ID" -H "Content-Type: application/json" -d '{"confirm":true}'
# → Notion page created!
📊 PRODUCTION FEATURES
✅ Persistent FAISS vector store

✅ memory_type classification (task/event/note)

✅ Agentic workflow (suggest → confirm → execute)

✅ Confidence scoring + trace_id observability

✅ Notion integration (live tasks)
