# KIRP → Ultimate Second Brain — Roadmap

## סטטוס נוכחי (תמצית)

- **בסיס ארכיטקטורי:** ~30–40% — Event Store, RAG, SchemaEngine, Agents, Multi-tenant, אינטגרציות בסיסיות.
- **חוויית "Second Brain":** ~20% — אין עדיין Tasks/Timeline/Life Areas ו־connectors אוטונומיים.
- **Overall vs Vision:** ~3–4/10.

## Phase 1 — מה אפשר לממש עכשיו (עד סוף מוגדר)

מטרה: **חיווט Schema לפייפליין + Notion connector בסיסי + Tasks UI** — כך ש־"חילוץ אובייקטי חיים מאירועים" ו־"רשימת משימות מה-Schema" יעבדו באמת.

### 1.1 חיבור EventPipeline → SchemaEngine (Life Objects)

- **מה:** אחרי ingest (EventStore + RAG), שלב נוסף: Agent/Rule שמזהה אם האירוע הוא Task/Commitment/Project/LifeArea.
- **איפה בקוד:** `EventPipeline` (או שלב חדש אחרי RAG) → קורא ל־`SchemaEngine.upsert_node` עם:
  - `entity`: Task / Commitment / Project / LifeArea (לפי מודל קיים ב־SchemaEngine).
  - `due_date`, `source_event_id`, `context` (מטה־דאטה מהאירוע).
- **NLP מינימלי:** זיהוי תאריכים פשוט ("מחר", "שבוע הבא", "יום שלישי") — אפשר ספריית dateparser או regex + hebrew/datetime, ולשמור כ־`due_date`.
- **תוצאה:** כל אירוע רלוונטי יוצר/מעדכן צומת ב־Schema (Task/Commitment וכו').

### 1.2 Notion Connector (Pull → Ingest)

- **מה:** Job/Worker (scheduled או on-demand) שמושך מדפי Notion DB (לפי `NOTION_DATABASE_ID` / `NOTION_TASKS_DB_ID`) וממיר ל־events.
- **איפה:** שימוש ב־`NotionIntegration` הקיים; worker חדש או task ב־Celery:
  - Pull pages (with optional cursor for incremental).
  - לכל דף: `POST /api/v1/ingest` או הזרקה ישירה ל־EventStore עם `source=notion`, `external_id=notion_page_id`.
- **אידמפוטנטיות:** בדיקה לפי `external_id` + `source` כדי לא ליצור כפילויות.
- **תוצאה:** משימות מ־Notion נכנסות ל־KIRP כאירועים ואז עוברות את אותו pipeline (כולל חילוץ ל־Schema).

### 1.3 API ל־Tasks (מתוך SchemaEngine)

- **מה:** endpoint חדש, למשל `GET /api/v1/tasks` (או הרחבה של domain קיים), שקורא ל־SchemaEngine:
  - `list_nodes` עם filter ל־entity=Task (ואולי Commitment).
  - מחזיר רשימה עם `id`, `title`, `due_date`, `source`, `source_event_id`, `tenant_id`, `space_id`.
- **איפה:** router חדש או הרחבה של `v1_domain` / `decisions`; שירות שקורא ל־SchemaEngine.
- **תוצאה:** ה־UI יכול להציג "רשימת משימות" אמיתית מהמערכת.

### 1.4 Tasks UI (Second-Brain UX מינימלי)

- **מה:** דף (או טאב) "Tasks" ב־Next.js:
  - טבלה/רשימה של Tasks מ־`GET /api/v1/tasks`.
  - עמודות: כותרת, due_date, מקור (notion/ingest/whatsapp), סטטוס אם קיים.
  - אופציונלי: פילטר לפי tenant/space, חיפוש.
- **איפה:** דף חדש תחת `app/(dashboard)/tasks/page.tsx` (או תחת content/history) + קריאה מ־apiClient.
- **תוצאה:** משתמש רואה משימות שמגיעות מ־ingest ומ־Notion — צעד ראשון ל־"מוח שני".

### 1.5 אופציונלי ב־Phase 1

- **CommandExecutor → Notion:** קריאה ל־`NotionIntegration.create_task` כשמחליטים על פעולה "create task" (מממשק או מ־agent). כבר יש אינטגרציה; צריך לחבר ל־CommandExecutor audit.
- **Timeline מינימלי:** הצגת Tasks ממוינים לפי `due_date` (ללא עדיין ReminderAgent).

---

## מה נדרש ממך (מבחינתי) כדי לבצע Phase 1

1. **אישור scope:** שההגדרה למעלה (Schema wiring + Notion pull + Tasks API + Tasks UI) היא מה שאתה רוצה כ־Phase 1.
2. **משתני סביבה:** ש־Notion (ו־API של KIRP) מוגדרים ונגישים (כבר יש NOTION_* ב־.env).
3. **לא נדרש ממני:** תכנון ארוך טווח של כל ה־P2–P3; אפשר להשאיר כ־"Phase 2" במסמך ולממש בהמשך.

---

## Phase 2–3 (לאחר Phase 1)

- **P2:** FutureObligationsAgent, ReminderAgent, SuggestFilters; שכבת importance/future/noise מעל RAG.
- **P3:** Space membership + visibility; UI מלא של Timeline / Life Areas / "My brain" vs "Team brain"; Notion bi-directional (webhooks, conflict policy).

---

## Bottom line

- **"בשלמות" את כל הרשימה** — לא ניתן במסגרת אחת; זה roadmap לכמה phases.
- **Phase 1 כפי שמתואר** — ניתן לממש עד סוף מוגדר: חיווט Schema לפייפליין, Notion connector (pull → ingest), API ל־Tasks, ודף Tasks ב־UI.
- אם תרצה, השלב הבא הוא **לממש את Phase 1 בקוד** (להתחיל מ־1.1 ואז 1.2, 1.3, 1.4).
