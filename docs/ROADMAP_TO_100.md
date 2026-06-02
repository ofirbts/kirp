# מה נשאר כדי להגיע ל־100% של המערכת

תבסס על הארכיטקטורה (.cursorrules), הקוד הקיים וה־TODOs בפרויקט.

---

## ✅ מה כבר עובד (מהסשן הזה)

- **Gmail** — חיבור OAuth, refresh token, Sync, Inbox.
- **Calendar** — חיבור נפרד, Sync, אירועים מ־7 ימים אחרונים, Inbox.
- **WhatsApp** — Twilio webhook (כולל ngrok), חתימה מאחורי proxy, שמירה ל־tenant/user נכון, Inbox + History, **התראה בפעמון**.
- **Connections UI** — Sync ל־WhatsApp (לניקוי שגיאות), הצגת שגיאות ברורה.
- **Auth** — `dev@localhost` / סיסמה מתאימה, JWT.

---

## 🔴 חסר או לא גמור (למאה אחוז)

### 1. אבטחה ותצורה

| נושא | מצב | פעולה מוצעת |
|------|-----|-------------|
| **KIRP_ENCRYPTION_KEY** | חסר/קצר → placeholder | להגדיר מפתח 32+ תווים ב־.env (production) להצפנת טוקנים. |
| **תפקידים (Roles)** | TODO: "Implement role assignment in database" | להשלים שמירה/קריאה של roles ב־DB ולא רק ב־JWT. |

### 2. API שלא מומשו

| endpoint | מצב | הערה |
|----------|-----|------|
| **Task retry** | 501 Not implemented | `src/api/tasks.py` — להשלים לוגיקת retry. |
| **Workflow trigger** | 501 Not implemented | `src/api/workflows.py` — לחבר ל־workflow engine אם קיים. |

### 3. Governance ו־Policy

| נושא | מצב | הערה |
|------|-----|------|
| **Policy engine** | Placeholder (simulated_risk) | `src/api/governance.py` — לחבר ל־OPA/מנוע מדיניות אמיתי. |
| **אישורים (approvals)** | TODO: "Trigger the tool that requested approval" | להשלים זרימת אישור → ביצוע פעולה. |

### 4. Observability ✅

| נושא | מצב | הערה |
|------|-----|------|
| **Alerts** | מיושם | `src/observability/alerts.py` — evaluate (תנאי threshold), fire (לוג + ALERT_WEBHOOK_URL אופציונלי). |
| **LLM usage** | מיושם | תגובה יציבה על 4xx/5xx (ללא raise_for_status), הפחתת רעש לוג httpx. |

### 5. Agents ו־Pipeline

| נושא | מצב | הערה |
|------|-----|------|
| **Schema Engine** | קיים ורץ | להרחיב לפי צורך (חוק: "Do NOT write raw SQL until Schema Engine is fully implemented"). |
| **Self-improvement agent** | TODO: Analyze patterns, emit events | להשלים לוגיקת ניתוח והמלצות. |
| **Conflict/Planner** | מקורות נתונים placeholder | לחבר ל־Calendar + commitments אמיתיים. |

### 6. Tenants / Spaces (DB) ✅

| נושא | מצב | הערה |
|------|-----|------|
| **Tenant/Space queries** | מיושם | `src/auth/tenants.py` — get_tenant (כולל slug default), get_space, list_spaces, ensure_private_space עם Postgres. |

### 7. פרודקשן

| נושא | פעולה |
|------|--------|
| **Environment** | .env.production עם מפתחות אמיתיים, BASE_URL/FRONTEND_URL נכונים. |
| **Webhook URL** | Twilio/ספקים מצביעים ל־API גלוי (לא ngrok ב־prod אלא דומיין קבוע). |
| **Celery** | וידוא ש־worker + beat רצים (או ב־Docker) ל־Gmail/Calendar sync על טיימר. |

---

## 🟡 אופציונלי (שיפור UX / יציבות)

- **Tests** — טסטים ל־multi-tenant, event-sourcing, governance (מוזכר ב־.cursorrules).
- **Dashboard** — טסטים E2E ל־Connections, Inbox, Notifications.
- **WhatsApp send** — תיקון `from_` ב־Twilio (כרגע placeholder) אם שולחים הודעות יזומות.
- **הסתרת/טיפול ב־LLM usage errors** — כדי שלא יופיעו 400/404 בלוגים אם לא רלוונטי.

---

## סיכום עדיפויות

1. **חובה ל־production:**  
   `KIRP_ENCRYPTION_KEY`, תצורת .env.production, Webhook URL גלוי, Celery (אם צריך sync אוטומטי).

2. **לסגירת פערים פונקציונליים:**  
   Role assignment ב־DB, Task retry, Workflow trigger, חיבור Policy engine ו־Approvals.

3. **לשיפור איכות:**  
   Observability alerts, תיקון/החלפת LLM usage APIs, טסטים.

אחרי סעיפים 1–2 המערכת קרובה ל־100% לפי ההגדרות בפרויקט; סעיף 3 מקרב ל־100% ברמת יציבות וניטור.
