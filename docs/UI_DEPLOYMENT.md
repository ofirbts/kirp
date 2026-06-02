# הפעלת ה-UI עם ה-API (RunMyDocker / Cloud)

יש לך **שני UIs** שמחוברים ל-API. שניהם יכולים לעבוד – צריך רק להגדיר נכון.

---

## 1. Next.js (Dashboard ב-`app/`)

**איך זה עובד:** הדפדפן קורא ישירות ל-API לפי `NEXT_PUBLIC_API_URL`. אין proxy – הבקשות יוצאות מהמשתמש ל-API.

### מה צריך כדי שזה יעבוד

| שלב | פעולה |
|-----|--------|
| **א. API ב-RunMyDocker** | מעלים את ה-API (Dockerfile.api), פורט 8000. מקבלים כתובת כמו `https://kirp-xxx.runmydocker.com`. |
| **ב. CORS** | ה-API מאפשר רק origins מסוימים. **ב-.env של RunMyDocker** (או בממשק) להוסיף: `CORS_ORIGINS=https://הכתובת-של-ה-UI-שלך` (למשל `https://kirp-ui.vercel.app`). אם יש כמה כתובות – מופרדות בפסיק. |
| **ג. העלאת Next.js** | להעלות את תיקיית `app/` (Next.js) ל-**Vercel** או **Netlify** (או שרת אחר). |
| **ד. משתנה סביבה ב-Vercel/Netlify** | ב-build / Runtime: `NEXT_PUBLIC_API_URL=https://kirp-xxx.runmydocker.com` (בלי סיום `/`). אם יש auth: `NEXT_PUBLIC_DEV_TOKEN=ה-token-שלך`. |
| **ה. Auth** | אם ה-API לא ב-`SKIP_AUTH=1` או `ENV=development`, צריך לשלוח `Authorization: Bearer <token>`. כרגע ה-UI שולח `NEXT_PUBLIC_DEV_TOKEN` אם הוא מוגדר. |

אחרי זה: לפתוח את הכתובת של ה-UI (Vercel/Netlify). הדשבורד יקרא ל-API לפי `NEXT_PUBLIC_API_URL` וה-API יקבל כי ה-origin מותר ב-CORS.

---

## 2. Streamlit (Master Dashboard ב-`src/ui/master_dashboard.py`)

**איך זה עובד:** Streamlit רץ על שרת (מחשב או Streamlit Cloud), וקורא ל-API עם `requests` לפי `API_URL`.

### מה צריך כדי שזה יעבוד

| שלב | פעולה |
|-----|--------|
| **א. API זמין** | ה-API רץ (למשל ב-RunMyDocker) וכתובתו נגישה. |
| **ב. משתנה סביבה** | להגדיר `API_URL=https://kirp-xxx.runmydocker.com` (איפה ש-Streamlit רץ). |
| **ג. הרצת Streamlit** | **מקומית:** `streamlit run src/ui/master_dashboard.py --server.port 8501`. **Streamlit Cloud:** להעלות את הריפו, Main file path: `src/ui/master_dashboard.py`, וה-Secrets / env: `API_URL` = כתובת ה-API. |

אין כאן CORS כי הקריאות יוצאות מהשרת של Streamlit ל-API, לא מהדפדפן.

---

## סיכום

| UI | איפה רץ | מה להגדיר | הערה |
|----|---------|-----------|------|
| **Next.js** | Vercel / Netlify / שרת משלך | `NEXT_PUBLIC_API_URL` + ב-API: `CORS_ORIGINS` | הדפדפן קורא ל-API → חובה CORS. |
| **Streamlit** | Streamlit Cloud / שרת משלך | `API_URL` | השרת קורא ל-API → אין CORS. |

**תשובה קצרה:** כן, ה-UI שבנית יכול לעבוד. צריך: (1) API עולה ב-RunMyDocker, (2) אם משתמשים ב-Next.js – להעלות אותו (למשל ל-Vercel), להגדיר `NEXT_PUBLIC_API_URL` ו-`CORS_ORIGINS` ב-API, (3) אם משתמשים ב-Streamlit – להגדיר `API_URL` ולהריץ את Streamlit (מקומי או Cloud).
