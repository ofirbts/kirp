# KIRP OS - Strategic Roadmap & Tasks 2026

## 🎯 High-Level Vision
Building an autonomous, event-driven OS that handles business logic via WhatsApp and Notion with zero-latency RAG.

## 📅 Weekly Schedule: Jan 18 - Jan 25
| Day | Focus Area | Priority | Status |
| :--- | :--- | :--- | :--- |
| Monday | Core API Stability | CRITICAL | DONE |
| Tuesday | Persona & Agent Logic | HIGH | IN_PROGRESS |
| Wednesday | RAG Knowledge Seeding | HIGH | TODO |
| Thursday | WhatsApp Integration Test | MEDIUM | TODO |

## 🛠 Active Task Backlog
- [ ] **Task ID: TK-101** | Persona-Based Response System.
  - Context: Agent must distinguish between 'Ofir' (Direct) and 'Guest' (Educational).
- [ ] **Task ID: TK-102** | Local File System Watcher.
  - Context: Worker needs to scan `/data/knowledge_base` every 60 minutes.
- [ ] **Task ID: TK-103** | WhatsApp Flow Validation.
  - Context: Ensure `wa_gateway` correctly handles incoming RAG responses.

## 💡 System Context for AI Agent
When the user asks "What's on my plate?", look at the Weekly Schedule and the Task Backlog. Prioritize CRITICAL tasks first.