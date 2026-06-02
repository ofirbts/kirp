# KIRP — החזון, מה המערכת עושה, ומה ה-UI באמת מציג

**עודכן:** לפי מצב הקוד הנוכחי (main.py, apiClient, agent_registry, SideNav).

---

## החזון (מהכללים)

**Controlled Intelligence Layer · Event-Sourced · Multi-Tenant · Zero Leakage**

- כל שינוי דרך אירועים (אין מוטציות ישירות ל-DB).
- רב-tenant: תמיד tenant_id, space_id, user_id.
- RAG + Agents: הקשר עובר עקבי, אין קריאות LLM מחוץ ל-agents.
- Governance: פעולות חיצוניות דרך מנוע המדיניות.

---

## מה המערכת **באמת** יודעת לעשות (ה-API)

### Endpoints במרכז (src/main.py)

| יכולת | endpoint | תיאור |
|--------|----------|--------|
| **Health** | `GET /health`, `GET /healthz` | בדיקת חיים. |
| **סטטיסטיקות** | `GET /api/v1/stats` | knowledge_items, agents, notifications. |
| **Ingest** | `POST /api/v1/ingest` | הזרמת תוכן → Event Store + RAG + pipeline. |
| **RAG Query** | `POST /api/v1/query` | חיפוש סמנטי + תשובה (וקטורים + LLM). |
| **Ask** | `POST /api/v1/ask` | שאילתת RAG מפושטת. |
| **Agents** | `GET /api/v1/agents` | רשימת agents עם last_run. |
| **Run Agent** | `POST /api/v1/agents/{agent_id}/run` | הרצת agent ידנית. |
| **Agent logs/actions** | `GET /api/v1/agents/logs`, `GET /api/v1/agents/actions` | לוגים ופעולות של agents. |
| **Agent status** | `GET /api/v1/agents/{agent_id}/status` | סטטוס agent. |
| **Insights** | `GET /api/v1/insights` | Insights מ-InsightsEngine. |
| **Notion sync** | `POST /api/v1/notion/sync` | סנכרון Notion. |

### Auth (src/api/v1_auth.py)

| יכולת | endpoint | תיאור |
|--------|----------|--------|
| **Signup** | `POST /api/v1/auth/signup` | הרשמה + tenant + token. |
| **Login** | `POST /api/v1/auth/login` | התחברות + token. |
| **Me** | `GET /api/v1/auth/me` | משתמש נוכחי מ-JWT. כשמשתמש **SKIP_AUTH=1** ואין (או לא תקף) Bearer — מחזיר משתמש default (tenant_id=default) כדי למנוע 403. |

### Routers נוספים (מה-mount ב-main.py)

| Router | prefix/תחום | יכולות עיקריות |
|--------|-------------|-----------------|
| **v1_tasks** | `/api/v1` | משימות: list, create, get, update. |
| **v1_history** | `/api/v1` | היסטוריה (timeline) לפי tenant/user. |
| **v1_notifications** | `/api/v1` | התראות: list, unread count, mark read. |
| **v1_connections** | `/api/v1/connections` | Gmail, Calendar, Slack, Notion — OAuth, connect, sync, validate. |
| **v1_graph** | `/api/v1` | גרף: nodes, edges. |
| **v1_context** | `/api/v1/context` | accessible-spaces, spaces. |
| **v1_reminders** | `/api/v1` | תזכורות: upcoming, preferences. |
| **v1_ingestion** | `/api/v1` | ingest (אם מוגדר ב-router). |
| **v1_execute** | `/api/v1` | הרצת agent (אם מוגדר ב-router). |
| **v1_domain** | `/api/v1` | דומיינים / content intelligence. |
| **ws_notifications** | — | WebSocket `/ws/notifications` — התראות בזמן אמת. |
| **events** | `/api` | אירועים (EventStore). |
| **agents** | `/api/agents` | רשימת agents + run. |
| **decisions** | `/api/decisions` | החלטות. |
| **graph** | `/api/graph` | גרף. |
| **audit_api** | `/api/audit` | רשומות audit. |
| **governance** | `/governance` | Governance / אישורים. |
| **observability** | `/observability` | health, metrics/snapshot. |
| **tenants** | `/api/tenants` | tenants + spaces. |
| **users** | `/api/users` | users, roles. |
| **realtime_ws** | `/ws` | WebSocket כללי (ערוצים). |
| **brand** | — | Brand OS. |
| **whatsapp_os** | — | WhatsApp. |
| **command** | — | פקודות. |
| **auth** | `/auth` | Auth כללי. |

---

## Agents רשומים (src/core/agent_registry.py + specs.py)

- **Legacy (מחוץ ל-Phase5):** PatternAnalyzer, Planner, Forecaster, RiskOpportunity, SchemaStructure, Presentation, SelfImprovement, Meta, FutureObligations, Reminder.
- **Phase5 (specs.py):** PlannerAgent, InsightAgentV2, ReminderAgentV2, ExecutionAgent, OverloadAgent, ConflictAgent.

סה״כ רישום: כל ה-legacy + 6 מ-Phase5 (הרישום המרכזי ב-`register_all_agents`).

---

## מה ב-UI **כן** מחובר לאמת (מציג נתונים אמיתיים)

- **Dashboard** — `getStats`, `listEvents`, `listAgents`, Quick Ingest (`ingestV1`).
- **Tasks** — `listTasksV1`, `createTaskV1`, nodes.
- **Agents** — `listAgentsV1`, `runAgentV1`, `getAgentLogsV1`, `getAgentActionsV1`; כפתור Run.
- **History** — `listHistoryV1`.
- **Connections** — `listConnections`, OAuth, sync, validate.
- **Graph** — `getGraphV1` / `getGraph`.
- **Insights** — `getInsightsV1`.
- **Think** — `queryV1` / `askV1`.
- **Notifications (Activity)** — `listNotificationsV1`, `getUnreadCountV1`, WebSocket.
- **Observability** — `getObservabilityHealth`, `getMetricsSnapshot` (מבוסס על health אמיתי).
- **Mission Control** — קורא ל-`getObservabilityHealth()` מה-backend.
- **Tenants, Audit, Signals, Visuals, Content, Decisions** — דפים וקריאות ב-apiClient; נתונים אמיתיים אם ה-backend מחזיר.

---

## מה ב-UI **לא** רלוונטי או מוגבל

| דף | הערה |
|----|------|
| **System Control** | `/api/system/ports`, `/api/system/containers` — mock; רלוונטי רק ל-dev. בע production להשתמש ב-Mission Control. |
| **Dev / Run** | תלוי ב-Brand OS API (פורט נפרד); לא רלוונטי כשמריצים רק את ה-API הראשי. |
| **Pipeline** | יש רשימת agents אמיתית; בלוקים ויזואליים עם שמות קבועים (Context Scanner וכו') — סטייל Brand OS, לא רשימת ה-agents של KIRP. |

---

## מה ה-UI **יכול** להציג אבל עדיין לא מלא

1. **דף בית** — מסר ברור: "Controlled Intelligence · Event-Sourced · Multi-Tenant" + כניסה מהירה ל-Dashboard / Ingest.
2. **Observability** — ויזואליזציה עשירה יותר מבוססת metrics אמיתיים (למשל healthy vs degraded).

---

## שינויים שבוצעו (מצב נוכחי)

1. **Auth** — כש-**SKIP_AUTH=1** ואין Bearer (או לא תקף), `/api/v1/auth/me` מחזיר משתמש default (tenant_id=default) כדי שה-UI לא יקבל 401 ו-403.
2. **Frontend** — כש-**NEXT_PUBLIC_SKIP_AUTH=1** ואין טוקן, `loadUser()` קורא ל-`meV1()` ומעדכן tenant store ל-default.
3. **Mission Control** — משתמש ב-`getObservabilityHealth()` מה-backend.
4. **Observability** — כרטיסים/גרף מבוססים על נתוני health.
5. **apiClient** — `runAgent`, `runAgentV1`, `getAgentLogsV1`, `getAgentActionsV1`, connections, auth (signupV1, loginV1, meV1).
6. **דף Agents** — כפתור Run, הרצת agent והצגת לוגים/פעולות.
7. **Dashboard** — Quick Ingest (טופס + `ingestV1`).
8. **System Control** — הערה: Local development only; ב-production להשתמש ב-Mission Control.

---

## קבצים שמשקפים יכולות (לעדכון המסמך)

| קובץ | מה מתעדכן לפיו |
|------|------------------|
| **src/main.py** | רשימת כל ה-`include_router` וה-endpoints ישירים (stats, ingest, query, agents, insights, notion). |
| **src/api/v1_auth.py** | לוגיקת /me (כולל default user ב-SKIP_AUTH). |
| **src/api/v1_*.py** | כל ה-V1 APIs (tasks, history, notifications, connections, graph, context, reminders וכו'). |
| **src/api/ws_notifications.py** | WebSocket התראות. |
| **lib/apiClient.ts** | אובייקט **apiClient** — כל הפונקציות שה-UI קורא להן. |
| **components/navigation/SideNav.tsx** | **NAV_ITEMS** — קישורי התפריט הראשי (Dashboard, Activity, Second Brain, Graph, Connections, Tasks, Think, Insights, Agents, History). |
| **app/(dashboard)/** | דפים קיימים (dashboard, tasks, agents, history, connections, graph, insights, think, notifications, observability, mission-control, tenants, governance/audit, settings/users-roles, second-brain, וכו'). |
| **src/core/agent_registry.py** | רשימת ה-agents שנרשמים ב-`register_all_agents`. |
| **src/core/agents/specs.py** | מפרט Phase5 agents (PlannerAgent, InsightAgentV2, ReminderAgentV2, ExecutionAgent, OverloadAgent, ConflictAgent). |

כשמוסיפים endpoint חדש, פונקציה ב-apiClient, פריט בתפריט או agent — מעדכנים את הקוד ואז מעדכנים את המסמך הזה בהתאם.
