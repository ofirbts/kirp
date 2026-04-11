# תכנית ניקוי מאגר, תיעוד ו-Cursor (אפריל 2026)

מסמך עבודה: מה לאחד, מה למחוק, איך לנסח מחדש, ולמה.  
**לא מחליף** את `UNIFIED_ARCHITECTURE.md` — משלים אותו מבחינת תפעול ומפת דרכים.

---

## חלק א׳ — קבצי `deploy/*.md` (שאלה 3)

| קובץ | תפקיד מוצע | מה לשנות |
|------|------------|----------|
| `deploy/README.md` | **מקור אמת תפעולי**: WSL, Docker, `launch-prod.sh`, `smoke-test.sh`, `curl /health`, פורטים, טבלת משתני סביבה *בלי* ערכים סודיים | להשאיר כראשי; להוסיף קישור ל-`docker-compose.prod.yml` ול-`MONGO_URI`/`mongo` (לא `localhost` מתוך קונטיינר) |
| `deploy/SAAS_REVENUE_GUIDE.md` | **One-pager מוצרי** (מסע לקוח + Stripe) | לקצר; לתקן: `/billing` הוא ב-**Next.js**, לא ב-API על 8080; לקשר ל-`app/(dashboard)/billing` |
| `deploy/VELOCITY.md` | **מטא-שיווק פנימי** (47 יום → MRR) | לאחד לתוך `ROADMAP` אחד ב-`docs/` או למחוק אם לא בשימוש שבועי |
| `deploy/INCIDENT_RUNBOOK.md` | **Runbook אמיתי** | להרחיב בפקודות קונקרטיות (docker compose, rollback, Stripe dashboard) או למזג ל-`docs/production_checklist.md` |

**נימוק:** חפיפה בין README לשורש לבין מדריכי deploy — טבעית; הבעיה היא **כפילות תוכן שיווקי** (MRR, velocity) לעומת **הוראות הרצה**. הפרדה ברורה: `deploy/README` = איך מרימים; `docs/ROADMAP_*` = למה ומתי.

---

## חלק ב׳ — תיקיית `docs/` (שאלה 4)

יש ~32 קבצים. לא כולם נחוצים בכל יום, אבל רובם **יש להם משמעות היסטורית או ארכיטקטונית**.

**עוגן יחיד מומלץ (קריאה לסוכן ולאדם):**
1. `UNIFIED_ARCHITECTURE.md` (בשורש) — ארכיטקטורה חיה  
2. `docs/QUICKSTART.md` — onboarding מפתח  
3. `docs/production_checklist.md` + `deploy/README.md` — prod  

**כפילויות לטיפול עתידי (לא מחיקה אוטומטית):**
- `ARCHITECTURE.md` מול `KIRP_ARCHITECTURE.md` — לאחד או להפנות צולבת בראש הקובץ ("מקור אמת: …").  
- דוחות `*_AUDIT*`, `*_REPORT*`, `*_VERIFICATION*` — לארוז לתיקייה `docs/archive/` או למחוק אחרי שסגור פרויקט הביקורת.  
- `DUPLICATES_AND_CLEANUP.md` — **לשמור**; הוא מתעד החלטות ניקוי.

**נימוק:** `docs/` היא "מחסן ידע"; בלי אינדקס (`docs/README.md` קצר עם מפת קריאה) קשה לראות תכלית. מספיק **קובץ אינדקס אחד** + הפניות, במקום למחוק היסטוריה שעדיין מסבירה החלטות.

---

## חלק ג׳ — קבצים בשורש (שאלה 5) — סיווג

**חייבים (אל תמחק):**  
`package.json`, `package-lock.json`, `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `alembic.ini`, `next.config.js`, `tailwind.config.js`, `postcss.config.js`, `tsconfig.json`, `next-env.d.ts`, `Makefile`, `docker-compose.yml`, `Dockerfile.api`, `Dockerfile.dashboard`, `Dockerfile.agent`, `Dockerfile` (אם בשימוש), `.gitignore`, `.dockerignore`, `.cursorrules`, `README.md`, `UNIFIED_ARCHITECTURE.md`, סקריפטי `deploy/*`, `run-all.sh`, `check_kirp.sh`, וכו'.

**סודות / סיכון — לא ב-git (או למחוק מהמאגר מיד):**  
`.env`, `.env.local`, `.env.prod`, `token.json`, `google_credentials*.json` — גם אם קיימים מקומית, **לא לחבר ל-git**. `.gitignore` אצלכם כבר מכסה חלק; לוודא שאין `git add -f`.

**ארטיפקטים שלא צריכים להיות בגרסה (מומלץ `git rm` + התעלמות):**  
`*.pid`, `tsconfig.tsbuildinfo`, `ngrok-v3-stable-linux-amd64.tgz`, `project_structure.txt` (אם רק דוח חד-פעמי), לוגים.

**תוכן ידע עם שם מבלבל:**  
`inf` — טקסט ראיון ארוך; **להעביר** ל-`docs/interview_prep_llm_layer.md` (או למחוק אם כפול ל-`KIRP_LEARNING_PACK_INTERVIEW_PREP.md`).

**קבצים לבדיקה ידנית לפני מחיקה:**  
`agent.js`, `list_models.js`, `final.yml`, `get_token.py`, `populate_demo.sh`, `seed_kirp_ofir.sh` — אם אין הפניה ב-Makefile/README — ארכיון או מחיקה.

**נימוק:** שורש נקי = פחות עומס על סוכן ועל מפתח; סודות במאגר = סיכון קריטי חמור מזבל תיעוד.

---

## חלק ד׳ — `tests/` (שאלה 6)

מבנה נוכחי: ~20 קבצי `test_*.py` ברמה אחת — **סביר לפרויקט בגודל הזה**.

**שיפור יעיל בלי לשנות הרבה קוד:**
- `pytest.ini`: מרקרים `[pytest] markers = integration, slow, stripe` והוספת `@pytest.mark.integration` לבדיקות שדורשות DB/Redis.  
- תיקייה עתידית אופציונלית: `tests/unit/` ו-`tests/integration/` — רק כשיהיו 40+ קבצים.

**נימוק:** לא למחוק בדיקות עובדות; לארגן לפי זמן ריצה ותלות שירות.

---

## חלק ה׳ — ניסוח מחדש: `.cursorignore`, `.cursorrules`, `BUILD_PROGRESS.md` (שאלה 7)

### `.cursorignore`
**מטרה:** להקטין הקשר מיותר ולהאיץ סריקה.

הצעה: להוסיף (אם לא קיימים)  
`**/.next/`, `**/dist/`, `**/build/`, `**/*.min.js`, `archive/`, `**/node_modules/` (כבר חלקית), דוחות כבדים ב-`docs/*REPORT* אם לא נדרשים לסוכן.

**בשבילך (אופיר):** אם אתה רוצה שהסוכן **יקרא** ארכיון — אל תתעלם מ-`archive/`; אם לא — השאר.

**נימוק:** איזון בין מהירות לבין כיסוי קוד.

### `.cursorrules`
**מטרה:** גבולות ארכיטקטורה וסיכון.

הצעה: לעבור ל-**Project Rules** ב-`.cursor/rules/*.mdc` עם `globs` (למשל חוק נפרד ל-`app/**` ול-`src/**`), ולהשאיר ב-`.cursorrules` רק **10–15 שורות** "חוקי ברזל" + קישור ל-`UNIFIED_ARCHITECTURE.md`.  
תיעוד רשמי: [Cursor Rules](https://cursor.com/docs/rules).

**בשבילך:** חוקים של multi-tenant ו-event-sourcing — **להשאיר תמיד חלים** (`alwaysApply` או גלוב רחב).

**נימוק:** קובץ אחד ענק פחות מתעדכן ממודולריות; הסוכן מיישם טוב יותר חוקים ממוקדי-נתיב.

### `BUILD_PROGRESS.md`
**מטרה:** יומן בנייה של M3 — **לא** תחליף ל-CHANGELOG.

הצעה:  
- לשנות כותרת ל-`docs/modules/M3_BUILD_LOG.md` (או להשאיר בשורש אבל לקשר מ-README),  
- או לקצר ל-"סטטוס נוכחי + 5 שורות אחרונות" והיסטוריה ב-git.

**בשבילך:** אם אתה משתמש בזה רק כדי שאזכור הקשר — **מספיק קובץ קצר + קומיטים ברורים**.

**נימוק:** קובץ של 200+ שורות יומן מנחית את חלון ההקשר מול קבצי קוד.

---

## חלק ו׳ — אינדקס תיקיות (שאלה 8, פיסקה לכל אחת)

- **`.devcontainer`** — הגדרת VS Code/Cursor בקונטיינר; יעיל אם כל הצוות על אותה סביבה; אחרת אופציונלי.  
- **`.github`** — CI, תבניות PR, Dependabot; חיוני לבגרות מול חברות גדולות.  
- **`.pytest_cache`** — מטמון מקומי; לא לקמיט, בדרך כלל ב-gitignore.  
- **`.venv` / `venv`** — סביבה מקומית; לא לקמיט.  
- **`.vscode`** — הגדרות עורך; שימושי לצוות; לעיתים ב-gitignore.  
- **`alembic`** — מיגרציות DB; חיוני אם SQLAlchemy/Alembic בשימוש פעיל.  
- **`app`** — Next.js App Router; חזית המוצר.  
- **`archive`** — קוד/דוקים ישנים ללמידה בלבד; לא לערבב בייצור.  
- **`components`** — רכיבי React משותפים.  
- **`deploy`** — compose prod, סקריפטים, OPA לפריסה; מקור אמת להרמת stack.  
- **`docs`** — תכנון, ביקורות, מדריכים; דורש אינדקס כדי שלא יהיה "בור תיעוד".  
- **`k8s`** — מניפסטים לקוברנטיס; רלוונטי אם פריסה ב-K8s.  
- **`kirp.egg-info`** — מטא־חבילה; לא לקמיט (בדרך כלל).  
- **`lib`** — עזרי TS/שיתוף צד לקוח.  
- **`node_modules`** — תלויות npm; לא לקמיט.  
- **`opa_policies_live`** — מדיניות OPA לסביבה חיה; צריך מקור אמת אחד מול `deploy/opa`.  
- **`public`** — נכסים סטטיים.  
- **`scripts`** — אוטומציה חד-פעמית/תחזוקה.  
- **`seed`** — נתוני זריעה.  
- **`services`** — שירותים (לעיתים גבול מטושטש מול `src` — לתעד במפורש).  
- **`src`** — ליבת FastAPI, אירועים, סוכנים, workers; לב המערכת.  
- **`tests`** — pytest יחידה/אינטגרציה.  
- **`tests_e2e`** — בדיקות קצה-לקצה; יקר יותר להרצה.  
- **`tools`** — כלי פיתוח; שמור רק מה שבשימוש.  
- **`venv`** — כפילות ל-`.venv`; אחד מספיק מקומית.

---

## חלק ז׳ — עצירה: אסטרטגיה, Cursor, ניקוי נוסף, צעדים כמו לילד בן 5

### 1) האם הגישה מעודכנת מול "חברות גדולות"?
הכיוון (אירועים, multi-tenant, governance, שכבת API מסודרת) **תואם** מה שארגונים דורשים; הפער הוא בדרך כלל ב-**SLA, אבטחה, תאימות, צוות SRE, ותיעוד חוזי API** — לא ברעיון הפרויקט. נדרש: CI ירוק, סודות מחוץ למאגר, מדיניות גישה, מסלולי פריסה ברורים, וביקורת עומס.

### 2) מה כבר בוצע במסמך הזה + מחיקות מומלצות
ראה חלקים א׳–ו׳. מחיקות בוצעו ב-git לקבצי ארטיפקט (ראה קומיט אחרון אם הוחל).

### 3) ניקוי נוסף חשוב
- איחוד מדיניות OPA למקור אחד.  
- אינדקס `docs/README.md`.  
- וידוא `MONGO_URI` ב-`.env.prod` תואם docker network (`mongo:27017` לקונטיינר API).  
- הסרת בינארים/pid מהמאגר.

### 4) חידושי Cursor (2025–2026) שכדאי לאמץ
- **Project Rules** ב-`.cursor/rules` עם globs ו-`alwaysApply` ([תיעוד](https://cursor.com/docs/rules)).  
- **AGENTS.md** לפרויקטים פשוטים יותר.  
- **Skills** (כבר אצלך ב-`~/.cursor/skills-cursor/`) לזרימות חוזרות.  
- מצבי **Plan / Agent** לפיצול תכנון מול ביצוע.  
- בלוג Cursor על [שיטות עבודה עם סוכן](https://cursor.com/blog/agent-best-practices).

### 5) בדיוק מה לעשות כדי להרים את הקיים (פשוט)
1. פתח טרמינל בתיקיית הפרויקט.  
2. וודא ש-Docker רץ.  
3. מלא `.env.prod` (מספרים ומפתחות אמיתיים, Mongo לכתובת `mongo` אם API בדוקר).  
4. הרץ: `./deploy/launch-prod.sh` או `./deploy/smoke-test.sh`.  
5. פתח דפדפן: `http://localhost:8080/health` — צריך לראות `healthy`.  
6. אם משהו אדום — `docker compose -f deploy/docker-compose.prod.yml logs kirp-api`.

---

*נוצר כמסמך תכנון; יישום מלא של מחיקות MD כפולות — שלב נפרד אחרי סימון ידני של קבצים "ארכיון".*
