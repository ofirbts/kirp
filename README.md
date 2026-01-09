# KIRP — Deterministic Multi-Agent Intelligence Platform

KIRP is a deterministic, event-driven, multi-agent RAG system designed for
replayable intelligence, observability, and controlled evolution.

This is not a chatbot.
This is an **Agent Platform**.

---

## 🎯 Core Guarantees (Locked)

- Deterministic replay: agent state = function(events)
- Event-sourced decision making
- Multi-agent orchestration (Planner, Executor, Critic, Verifier)
- Unified knowledge plane (vector store + replay)
- Snapshot + fast restore
- Tenant-isolated memory
- Explainability for every decision
- Observability (QPS, drift, memory, replay)
- Tool-enabled agents (Phase 1)

---

## �� Architecture Overview


User / API
↓
PlannerAgent
↓
ExecutorAgent
↓
Core Agent
├── RAG (FAISS / Qdrant)
├── MemoryManager (short/mid/long)
├── KnowledgeStore
├── ToolAgent
├── Critic / Verifier
↓
Events → Persistence → Replay

---

## 🔁 Replay & Determinism

All state mutations emit events.
Replaying the same event stream produces the same state.

Replay is certified via:
tools/assert_replay_deterministic.py

---

## 📊 Observability

- Query rate (QPS)
- Retrieval drift
- Memory growth
- Agent state
- Vector store health

Available via:
- REST API
- Streamlit Dashboard

---

## 🧩 Multi-Agent System

- Planner — decomposes intent
- Executor — executes plans
- Critic — evaluates answers
- Verifier — checks consistency
- Negotiation engine — resolves conflicts

---

## 🛠 Tool Usage (Phase 1)

Tools are invoked via deterministic heuristics.
Autonomous LLM-based tool selection is **explicitly out of scope** for this phase.

---

## 🚫 Explicitly Not Included

- Autonomous self-modifying agents
- Black-box learning without events
- Non-replayable memory
- Hidden prompts or policies

---

## �� Validation

Run full system check:
```bash
python tools/check_kirp_full.py

Replay certification:
python tools/assert_replay_deterministic.py

📦 Status

Engineering Closed
Further changes require explicit version bump and contract update.
