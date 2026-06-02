# Brand OS v3 — מההתחלה ועד הסוף: לראות הכל ולוודא שזה עובד

מדריך צעד־אחר־צעד. עשה לפי הסדר — בסוף תראה את כל המערכת ותוודא שהכל רץ.

---

## דרישות מקדימות

- **Python 3.10+** — `python3 --version`
- **Node.js 18+** (רק ל־UI) — `node --version`
- **מסוף** — טרמינל או IDE

---

## שלב 1 — התקנת Python והרצת בדיקות (חובה)

משורש הפרויקט (`/home/ofir/projects/kirp`):

```bash
cd /home/ofir/projects/kirp
pip install -e .
```

**לוודא:** אין שגיאות. אם יש — תקן תלויות חסרות לפי ההודעות.

**הרצת כל בדיקות E2E:**

```bash
pytest -q tests_e2e/
```

**צפוי:** `X passed, Y skipped` (חלק מהבדיקות מדלגות אם חסרים twilio/apscheduler — זה בסדר).

**אם נכשל:** קרא את שם הקובץ והפונקציה שנכשלה ותקן (למשל חסר חבילה — `pip install ...`).

---

## שלב 2 — API (לראות שהשירות חי)

**טרמינל 1:**

```bash
cd /home/ofir/projects/kirp
uvicorn api.main:app --reload
```

**צפוי:** `Uvicorn running on http://127.0.0.1:8002`

**בדיקה:**

```bash
curl http://127.0.0.1:8002/health
```

**צפוי:** `{"status":"ok","service":"brand-os-v3-api"}`

**בדיקה שנייה — הרצת pipeline:**

```bash
curl -X POST http://127.0.0.1:8002/brand-os/run \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"t1","platform":"linkedin","topic_hint":"API release"}'
```

**צפוי:** JSON עם `trace_id`, `content`, `visual_spec`, `recommendations`, `status`.

**או בדפדפן:**  
פתח: **http://127.0.0.1:8002/docs** — תראה Swagger; נסה GET /health ו־POST /brand-os/run.

השאר את ה־API רץ (טרמינל 1 פתוח).

---

## שלב 3 — CLI (לראות את brandos מהטרמינל)

**טרמינל 2** (API עדיין רץ ב־1):

```bash
cd /home/ofir/projects/kirp
brandos agents
```

**צפוי:** רשימת 8 סוכנים (CONTEXT_SCANNER, STRATEGIC_PLANNER, ...).

```bash
brandos run "API release" --tenant t1 --platform linkedin --api
```

**צפוי:** הדפסה של content, visual_spec, recommendations (מגיע מה־API).

```bash
brandos run "test topic" --tenant t1 --platform linkedin --sdk
```

**צפוי:** אותו דבר אבל רץ ישירות דרך ה־SDK (בלי API).

```bash
brandos signals --tenant t1 --platform linkedin
```

**צפוי:** world_context, trends (פלט של CONTEXT_SCANNER).

עכשיו יש לך: API רץ + CLI עובד מול API ו־SDK.

---

## שלב 4 — UI (לראות הכל בדפדפן)

**טרמינל 2** (או 3 אם סגרת את 2):

```bash
cd /home/ofir/projects/kirp/brand_os_ui
npm install
npm run dev
```

**צפוי:** `Local: http://localhost:3001`

**בדפדפן — מה עושים בכל דף:**

| דף | כתובת | מה עושים | איך זה עובד |
|----|--------|----------|-------------|
| **דף הבית** | http://localhost:3001 | לוחצים על "Dashboard" או "Run" בתפריט | קישורים לדפים האחרים |
| **Dashboard** | /dashboard | בודקים אם ה־API חי (מצב ירוק/אדום) ורואים ריצות אחרונות | ה־UI קורא ל־GET /health ול־API; אם Brand OS API על 8002 — חייבים להגדיר למטה |
| **Run** | /run | ממלאים: Tenant (למשל t1), Platform (linkedin/twitter/whatsapp), Topic (למשל "API release") → לוחצים "Run" | ה־UI שולח POST /brand-os/run ל־API; התשובה מוצגת: כותרת, גוף, hook, CTA + prompt לתמונה |
| **History** | /history | צופים ברשימת ריצות קודמות | קורא מ־API route מקומי (stub) — כרגע לא מחובר ל־content memory log; יכול להיות ריק |
| **Agents** | /agents | צופים ברשימת 8 הסוכנים (CONTEXT_SCANNER, STRATEGIC_PLANNER וכו') | קורא מ־API route מקומי שמחזיר את רשימת הסוכנים |
| **Visuals** | /visuals | צופים ב־visual specs שנוצרו | כרגע stub — יכול להיות ריק עד שמחברים למקור נתונים אמיתי |

**איך לעבוד בפועל (Run):**
1. וודא ש־Brand OS API רץ: `uvicorn api.main:app --reload --port 8002`
2. אם ה־API על 8002, צור קובץ `brand_os_ui/.env.local` עם: `NEXT_PUBLIC_BRAND_OS_API_URL=http://127.0.0.1:8002`
3. הרץ UI: `cd brand_os_ui && npm run dev`
4. פתח http://localhost:3001/run
5. הזן Tenant (t1), Platform (linkedin), Topic (למשל "API release") → Run
6. מתחת יופיעו: Content (כותרת + גוף + hook + CTA) ו־Visual Spec (prompt לתמונה, פורמט)

**חשוב:** ה־API חייב לרוץ (אם על 8000 או 8002). אם ה־API על 8002 (כי KIRP Docker תופס 8000), הגדר ב־brand_os_ui `.env.local`:

```bash
NEXT_PUBLIC_BRAND_OS_API_URL=http://127.0.0.1:8002
```

עכשיו יש לך: API + CLI + UI.

---

## שלב 5 — Monitoring (גרפים ומטריקות)

**טרמינל 3:**

```bash
cd /home/ofir/projects/kirp
uvicorn brand_os_monitoring.app:app --port 8001 --reload
```

**בדפדפן:**

- **http://127.0.0.1:8001/metrics** — JSON: total_runs, approved, rejected_identity, top_hooks וכו'.
- **http://127.0.0.1:8001/dashboard** — דף HTML עם גרפים (Chart.js).

אם אין עדיין ריצות ב־content memory log, המספרים יכולים להיות 0 — זה תקין.

עכשיו יש לך: API + CLI + UI + Monitoring.

---

## שלב 6 — Scheduler (אופציונלי — רק לראות שהוא עולה)

**טרמינל 4:**

```bash
cd /home/ofir/projects/kirp
python run_scheduler.py
```

**צפוי:** הודעות שהמתזמן עלה; job יומי ב־08:00.  
אפשר לסגור אחרי כמה שניות (Ctrl+C) — רק וידוא שהמודול נטען בלי שגיאה.

---

## שלב 7 — SDK ישירות מ־Python (אופציונלי)

**טרמינל או Python REPL:**

```bash
cd /home/ofir/projects/kirp
python -c "
from brand_os_sdk import load_identity, load_voice, list_agents, run_orchestrator
print('Identity keys:', list(load_identity().keys())[:5])
print('Voice keys:', list(load_voice().keys())[:5])
print('Agents:', list_agents())
r = run_orchestrator({'tenant_id':'t1','platform':'linkedin','topic_hint':'test'})
print('Status:', r.get('status'))
print('Headline:', r.get('content',{}).get('headline','')[:50])
"
```

**צפוי:** הדפסת מפתחות identity/voice, רשימת סוכנים, status ו־headline.

---

## שלב 8 — Docker (אופציונלי — לוודא שה־build עובד)

```bash
cd /home/ofir/projects/kirp
docker build -f Dockerfile.brand_os_api -t brand-os-api .
docker run -p 8002:8002 --rm brand-os-api
```

**בטרמינל אחר:** `curl http://localhost:8002/health`  
**צפוי:** `{"status":"ok",...}`.  
אחרי הוידוא — עצור את הקונטיינר (Ctrl+C).

---

## סיכום — מה רואים ואיפה

| מה | איך | איפה לראות |
|----|-----|------------|
| **בדיקות** | `pytest -q tests_e2e/` | פלט: X passed |
| **API** | `uvicorn api.main:app --reload` | http://127.0.0.1:8002/docs, /health, /brand-os/run |
| **CLI** | `brandos agents`, `brandos run "..."`, `brandos signals` | פלט בטרמינל |
| **UI** | `cd brand_os_ui && npm run dev` | http://localhost:3001 — /dashboard, /run, /history, /agents, /visuals |
| **Monitoring** | `uvicorn brand_os_monitoring.app:app --port 8001` | http://127.0.0.1:8001/metrics, /dashboard |
| **Scheduler** | `python run_scheduler.py` | הודעת עלייה; job ב־08:00 |
| **SDK** | `python -c "from brand_os_sdk import ..."` | פלט ב־REPL/טרמינל |
| **Docker** | `docker build ... && docker run ...` | curl localhost:8002/health |

---

## סדר מומלץ ל"ריצה אחת מלאה"

1. `pip install -e .`  
2. `pytest -q tests_e2e/`  
3. טרמינל 1: `uvicorn api.main:app --reload`  
4. טרמינל 2: `cd brand_os_ui && npm install && npm run dev`  
5. דפדפן: http://localhost:3001 → /run → שלח טופס → תראה תוכן + visual.  
6. דפדפן: http://127.0.0.1:8002/docs → נסה POST /brand-os/run.  
7. טרמינל: `brandos run "API release" --tenant t1 --platform linkedin --api`  
8. (אופציונלי) טרמינל 3: `uvicorn brand_os_monitoring.app:app --port 8001` → פתח http://127.0.0.1:8001/dashboard  

אם כל השלבים עוברים — אתה רואה את כל המערכת ומוודא שזה עובד מקצה לקצה.
