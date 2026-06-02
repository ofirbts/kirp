# כפילויות וניקוי (Duplicates & cleanup)

## מה טופל

### 1. קבצי Rego
- **היה:** 3 עותקים של `kirp.rego` (deploy/opa/policies, opa_policies_live, opa_policies_live/policies).
- **עכשיו:** מקור אמת יחיד — **`deploy/opa/policies/kirp.rego`**. ה־docker-compose ממפה את התיקייה הזו. שני העותקים ב־`opa_policies_live` הוסרו; יש שם רק README שמפנה ל־deploy.

### 2. קבצי env
- **היה:** `.env.example` (API), `docs/env.local.example` (UI), `docs/env.production.example` (רק טקסט "deprecated").
- **עכשיו:** `docs/env.production.example` נמחק. Production משתמש באותו `.env.example` עם ערכי production. ה־UI ממשיך להשתמש ב־`docs/env.local.example` → `.env.local` (מפורט ב־.env.example).

### 3. קבצי ג'אנק בשורש הפרויקט
- **הוסרו:** `=`, `CACHED`, `resolve`, `[internal]`, `[qdrant`, `Host:` (קבצים ריקים שנוצרו כנראה בטעות).
- אין צורך בהם; לא משמשים בקוד.

## מה נשאר במכוון (לא כפילות)

| פריט | הסבר |
|------|--------|
| **api/** vs **src/main.py** | לא כפילות. `api/main.py` = Brand OS v3 API (מיני־שירות); `src/main.py` = אפליקציית KIRP הראשית. |
| **.env.example** vs **docs/env.local.example** | משלימים: הראשון ל־API (.env), השני ל־Next.js (.env.local). |
| **backup_pre_runmydocker/** | גיבוי מכוון (מתועד ב־docs/RUNMYDOCKER.md). אם לא צריך — אפשר למחוק את כל התיקייה. |
| **Dockerfile* בשורש** | כל אחד לשירות אחר (api, dashboard, agent, worker, brand_os). לא כפילויות. |

## המלצה להמשך

- אם אין צורך בגיבוי: `rm -rf backup_pre_runmydocker`.
- אם יש תיקיות/קבצים נוספים שנראים כפולים — לבדוק אם משהו מייבא אותם (grep / docker-compose) ואז לאחד או למחוק.
