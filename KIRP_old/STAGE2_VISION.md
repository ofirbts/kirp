# Stage 2 – Vision Reconstruction
## KIRP v1: North Star, Identity, and Design Philosophy

**Date:** 2025-01-25  
**Input:** Stage 1 diagnosis, README, SYSTEM_CONTRACT, roadmap, and code structure.

---

## 1. Inferred Original Intent

From README, SYSTEM_CONTRACT, roadmap, and code:

- **KIRP** was conceived as an **operating system for AI agents** — not a chatbot, but infrastructure that gives agents **memory**, **execution**, **governance**, and **learning**.
- **Gap it addresses:** Most AI systems respond to prompts, forget past actions, and cannot safely operate inside real organizational tools (Notion, WhatsApp, etc.). KIRP bridges that by **event-sourcing every action**, **RAG for context**, **human-in-the-loop for critical steps**, and **explicit self-improvement** from logs.
- **Flow:** Input (API / WhatsApp) → event stored (MongoDB) → context retrieved (Qdrant RAG) → agent decides → governance check (if required) → execution (Notion, etc.) → logs analyzed for improvement.
- **Invariants:** No state mutation without event; agent state reconstructable; all decisions explainable.
- **Non-goals:** No hidden learning, no silent self-modification.

The **vision was clear**. Implementation drifted into multiple configs, duplicate abstractions, broken imports, stubs, and unmounted routers — but the **intent** is recoverable from docs and structure.

---

## 2. KIRP v1 Vision Statement

> **KIRP v1** is a **minimal, event-sourced agent OS** that lets a **single core agent** ingest knowledge, answer questions, and execute approved actions (e.g. Notion) — with **one event store**, **one RAG store**, and **one config** — so that every decision is **auditable**, **explainable**, and **replayable**.

---

## 3. North Star (Central Purpose)

**Controlled execution with memory.**

- The agent **remembers** (RAG) and **acts** (tools) — but **only** through **events** and **explicit governance**.
- **North Star:** *Every user request flows through: event → RAG context → agent decision → (optional) approval → execution → event.* No silent mutations, no hidden learning.
- Success = **one clean path** from input to outcome, with **full traceability** and **explainability** at every step.

---

## 4. Core Identity

**Event-sourced agent OS with a single core agent.**

- **OS:** KIRP provides **memory** (RAG), **event store** (audit + replay), **governance** (approval gates), and **tools** (e.g. Notion, WhatsApp). The agent runs *on* this OS.
- **Single core agent:** One primary agent (conversational + RAG + execution). No competing `CoreAgent`/`OmniAgent`/`ExecutorAgent` variants; one **core agent** with clear responsibilities.
- **Event-sourced:** Events are the **source of truth**. State is derived from events; agent state is **reconstructable** from the log.
- **Explainable:** Decisions are grounded in **retrieved context** and **explicit prompts**; ranking and reasoning are **visible** (e.g. for dashboards and self-improvement).

---

## 5. Design Philosophy (One Paragraph)

**Simplicity over cleverness; stability over features; clarity over complexity.**  
KIRP v1 favors **one** config, **one** event store, **one** vector store, and **one** core agent over multiple competing abstractions. Every feature must **reduce** cognitive load and **increase** traceability: no silent self-modification, no hidden learning, no duplicate auth or storage layers. The system is **minimal** by design — small, understandable, and easy to evolve. New capabilities (e.g. extra tools, channels) are added only when they **integrate cleanly** into the single event → RAG → agent → execution flow and **preserve** the invariants (no mutation without event, reconstructable state, explainable decisions).

---

## 6. Strategic Implications for v1

| Area | v1 Stance |
|------|-----------|
| **Config** | One source of truth (e.g. `app.config` or env-backed settings). No Streamlit in core backend config. |
| **Events** | One event store (MongoDB). Redis only for **queues** (worker jobs), not a second event log. |
| **RAG** | One vector store abstraction (e.g. `vector_store`). No qdrant_store / sharded_store duplication. |
| **Agent** | One **core agent**: ingest-aware, RAG-backed, tool-capable. No CoreAgent vs OmniAgent vs ExecutorAgent split. |
| **Auth** | One `get_current_user`; no auth bypass (e.g. fake Depends on `/health`); no backdoors. |
| **APIs** | Mounted routers only. No inline stubs (`/agent/query`, `/dashboard/summary`) that override real implementations. |
| **Self-improvement** | Explicit: analyzers read **events** and **logs**, suggest changes. No hidden model updates. |

---

## 7. Summary

- **North Star:** Controlled execution with memory — one event → RAG → agent → (optional) approval → execution → event flow.
- **Identity:** Event-sourced agent OS with a **single core agent**, one event store, one RAG store.
- **Philosophy:** Simplicity > cleverness; stability > features; clarity > complexity; minimal, traceable, explainable.

---

*Next: **Stage 3 – Redesign Planning** (after your confirmation).*
