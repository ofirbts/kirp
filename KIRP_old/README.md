# 📡 KIRP OS
### An Agentic Operating System for Controlled Autonomous AI

KIRP OS is an event-driven framework designed to orchestrate autonomous AI agents **that actually execute tasks**, not just generate text.

Unlike traditional AI bots, KIRP OS introduces:
- Long-term neural memory
- Human-in-the-loop governance
- Self-optimizing agent behavior
- Real enterprise integrations

---

## 🚀 Why KIRP OS Exists

Most AI systems today:
- Respond to prompts
- Forget past actions
- Cannot safely operate inside real organizational tools

**KIRP OS solves this gap** by acting as an Operating System for agents — with memory, execution, governance, and learning loops.

---

## 🧠 Core Concepts

### Event-Driven Architecture
Every action is an event stored in MongoDB, enabling:
- Full auditability
- Replayable workflows
- Robust failure recovery

### Neural Memory (RAG)
Qdrant Vector DB stores contextual knowledge and execution history.
Before every decision, agents retrieve relevant past context instead of hallucinating.

### Active Governance (Human-in-the-loop)
Critical actions pause execution and request human approval via WhatsApp.
This enables autonomy without losing control.

### Self-Improving Agents
Background workers analyze success/failure logs and iteratively improve prompts and decision strategies.

---

## 🛠 Tech Stack

- **Backend:** FastAPI (Python, async-first)
- **Event Store:** MongoDB
- **Vector DB:** Qdrant
- **Async Workers:** Redis
- **UI / Admin:** Streamlit
- **Integrations:** WhatsApp API, Notion API

---

## 🏗 System Flow

1. Input arrives (API / WhatsApp)
2. Event is stored in MongoDB
3. Context retrieved from Qdrant (RAG)
4. Agent decides next action
5. Governance check (if required)
6. Execution via external tools (Notion)
7. Logs analyzed for self-improvement

---

## 📈 Future Directions

- Kubernetes-based scaling
- Local LLM support (Ollama / Llama)
- WebSocket-based real-time UI
- Multi-agent collaboration protocols

---

**Built by Ofir Betesh**  
