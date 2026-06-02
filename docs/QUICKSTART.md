# KIRP — איך להתחיל לראות משהו (Quick Start)

סכמה מדויקת כדי להריץ את המערכת locally ולהיכנס לדאשבורד (כולל M3 Identity).

**English / ops:** RunController Redis keys, pipeline vs post-ingest, metrics scrape paths, and the doc-linked **regression test index** live in **`SYSTEM_STATUS.md`** at the repo root.

**Architecture (flows, components):** **`SYSTEM_ARCHITECTURE.md`** at the repo root (cross-links back to **`SYSTEM_STATUS.md`** for operational truth).

---

## 1. דרישות

- **Docker** ו-**Docker Compose** מותקנים.
- (אופציונלי) אם יש לך **Node 18+** ו-**Python 3.10+** — אפשר להריץ פרונט או API מקומית בלי Docker; כאן מתמקדים ב-**Docker** כי זה הכי פשוט.

---

## 2. קובץ סביבה

- יש כבר `.env.development` — ה-API וה-Agent Processor ב-Docker משתמשים בו.
- אם חסר, העתק מ-`.env.example`:
  ```bash
  cp .env.example .env.development
  ```
- **להתחיל בלי LLM/M3:** לא חייבים למלא מפתחות. להרצה מינימלית אפשר להשאיר ריק: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `M3_ESCALATION_PHONE`.

---

## 3. הרצת כל השירותים (Docker)

משורש הפרויקט:

```bash
cd ~/projects/kirp

# (אופציונלי) אם יש בעיות הרשאות עם buildx:
# chmod +x scripts/reset_buildx.sh && ./scripts/reset_buildx.sh

docker compose down
docker compose up -d --build
```

- הבילד יכול לקחת כמה דקות (API, Dashboard, Qdrant, וכו').
- אחרי שכל הקונטיינרים up, חכה ~1–2 דקות עד שה-API עובר health check.

---

## 4. בדיקה שהכל רץ

```bash
# API
curl -s http://localhost:8000/health | head -5

# M3 מודול
curl -s http://localhost:8000/api/v1/m3/health

# דאשבורד (בדפדפן)
# פתח: http://localhost:3100
```

---

## 5. איפה רואים משהו

| מה | כתובת |
|----|--------|
| **דאשבורד (UI)** | http://localhost:3100 |
| **API (Swagger)** | http://localhost:8000/docs |
| **M3 Identity (בדאשבורד)** | http://localhost:3100/m3 |
| **Mongo Express** | http://localhost:8081 |

---

## 6. התחברות בדאשבורד (פיתוח)

- ב-`.env.development` יש `DEV_TOKEN=dev-local-token` (וגם ב-docker-compose ל-API).
- בדאשבורד אפשר להגדיר **Token** ב-UI (אם יש שדה) או ב-`localStorage`:  
  `access_token` = `dev-local-token`.
- אם מופעל **SKIP_AUTH** או שהדאשבורד משתמש ב-`NEXT_PUBLIC_DEV_TOKEN` — ייתכן שלא תצטרך לעשות כלום.

אם יש דף לוגין:
- נסה **Token** = `dev-local-token`.
- או חפש ב-README/קוד איך מוגדר `DEFAULT_TENANT_ID` / `DEFAULT_USER_ID` לפיתוח.

---

## 7. M3 — לראות רפלקציות ו-KPIs

1. היכנס ל-**http://localhost:3100/m3**.
2. שלח **Daily reflection** (טקסט + אופציונלי mood) ולחץ Submit.
3. אחרי שליחה — תופיע הרשימה "Recent reflections" ו-KPIs (אם יש נתונים).
4. (אופציונלי) אם הוגדר `OPENAI_API_KEY` או `GEMINI_API_KEY` — הסוכן יסווג רפלקציות (pillar_scores, mood) ויופיעו גם Pillars ברשימה.

---

## 8. אם משהו לא עולה

- **API לא עונה על 8000:**  
  `docker compose ps` — וודא ש-`kirp-api` ב-state **Up** ו-healthy.  
  `docker compose logs kirp-api` — חפש שגיאות (DB, OPA, וכו').

- **דאשבורד 3100 לא נטען:**  
  `docker compose logs kirp-dashboard`.  
  וודא שב-build הוגדר `NEXT_PUBLIC_API_URL=http://localhost:8000` (כמו ב-docker-compose).

- **CORS / לא מצליח לקרוא API מהדאשבורד:**  
  ב-API וודא ש-`FRONTEND_URL` או CORS כוללים `http://localhost:3100`.

- **אין נתונים ב-M3:**  
  M3 memory ברירת מחדל היא in-memory; אחרי restart הנתונים נמחקים.  
  כדי לשמור: ב-`.env.development` הגדר `M3_MEMORY_BACKEND=mongo` (ו-`MONGO_URI` כבר מוגדר ב-docker-compose).

---

## 9. סיכום צעדים (לעין אחת)

```text
1. cd ~/projects/kirp
2. cp .env.example .env.development   # אם חסר
3. docker compose down && docker compose up -d --build
4. חכה 1–2 דקות
5. פתח דפדפן: http://localhost:3100  → דאשבורד
6. גלוש ל־ http://localhost:3100/m3 → שלח רפלקציה וצפה ב-KPIs ורשימה
```

זהו. אחרי זה אמור להיות אפשר "לראות משהו" בדאשבורד וב-M3.
