# איך לוודא ש־Gmail, לוח שנה ו־WhatsApp עובדים (UI + בקאנד)

במערכת **אין התראות פופאפ** כשמגיע מייל / אירוע לוח שנה / הודעת WhatsApp.  
**כל הקלט מופיע במקום אחד:** **Second Brain → Inbox**.  
הדף מרענן אוטומטית כל 30 שניות; אפשר גם ללחוץ **Refresh**.

---

## 1. מה הזנת ב־UI ומה כל חיבור עושה

| חיבור    | מה הזנת ב־Connections      | איך נתונים נכנסים למערכת                    | איפה רואים ב־UI        |
|----------|----------------------------|-----------------------------------------------|-------------------------|
| **Gmail**   | Connect → OAuth גוגל        | **Sync ידני:** לחיצה על "Sync Now" אחרי חיבור | **Inbox** (עמודת Source: gmail)  |
| **Calendar** | Connect → OAuth גוגל      | **Sync ידני:** "Sync Now" אחרי חיבור          | **Inbox** (Source: calendar)     |
| **WhatsApp** | טוקן/פרטים (או OAuth לפי ספק) | **Webhook:** טוויליו שולח POST ל־API כשמישהו שולח הודעה **למספר הטוויליו** | **Inbox** (Source: whatsapp)     |

- **Gmail / Calendar:** הנתונים נמשכים רק כש**אתה** לוחץ "Sync Now" (או כש־Celery מריץ sync על טיימר).  
- **WhatsApp:** הנתונים נכנסים **רק כשטוויליו קורא ל־Webhook** – כלומר ה־API חייב להיות נגיש מהאינטרנט (למשל דרך ngrok). ב־localhost בלבד טוויליו לא יגיע.

---

## 2. איך לוודא ב־UI

### Gmail (מייל)

1. **Connections** → Gmail אמור להיות **Connected** (חיברת עם OAuth).  
   אם Sync נכשל עם "credentials do not contain... refresh_token": **Disconnect** ואז **Connect** שוב (כדי לקבל `refresh_token` מגוגל).
2. לחץ **Sync Now** על כרטיס Gmail.
3. **Second Brain → Inbox** → תראה שורות עם **Source: gmail** (ואם אין – לחץ Refresh או חכה ~30 שניות).
4. אם יש שגיאה ב־Sync – תופיע הודעת שגיאה ליד הכפתור או ב־last_sync_status.

### לוח שנה (Calendar)

1. **חשוב:** לוח השנה מחובר **בנפרד** מ-Gmail. גם אם חיברת Gmail, צריך ללחוץ **Connect** על **Google Calendar** ולעבור את האישור של גוגל (scope של לוח שנה).
2. **Connections** → **Google Calendar** → **Connect** (אם עדיין לא מחובר) → אחרי החיבור: **Sync Now**.  
   אם Sync נכשל עם "credentials do not contain... refresh_token": **Disconnect** ואז **Connect** שוב.
3. אירועים מ-**7 הימים האחרונים** ועד האירועים הבאים יופיעו ב-Inbox אחרי Sync.
3. **Second Brain → Inbox** → שורות עם **Source: calendar**.
4. אם אין – Refresh / חכה לרענון אוטומטי.

### WhatsApp

1. **ב־Connections → WhatsApp → Connect (token / URL):** הכנס את **Twilio Auth Token** (מהקונסול של טוויליו: Account → API keys & tokens → Auth Token, או העתק מה־curl אחרי ה־`:`)  
   דוגמה: `5a76571c1d3382080f79763e747762c7`. זה מאפשר ל־UI להראות "Connected"; הקבלה של הודעות עובדת דרך Webhook (למטה).
2. **חשוב – קבלת הודעות:** טוויליו שולח הודעות ל־API רק אם ה־**Webhook URL** גלוי באינטרנט.  
   - ה־**ngrok authtoken** מוגדר ב־`.env` (משתנה `NGROK_AUTHTOKEN`).  
   - מהתיקייה של הפרויקט הרץ: **`./scripts/run_ngrok.sh`** (או `./scripts/run_ngrok.sh 8000`). יופיע URL כמו `https://xxxx.ngrok-free.app`.  
   - ב־Twilio Console → Messaging → WhatsApp Sandbox (או המספר שלך) → "When a message comes in" הגדר:  
     **`https://<ה-URL-של-ngrok>/api/v1/webhooks/whatsapp`**  
   - וודא שה־API רץ על פורט 8000 (אותו פורט ש־ngrok מפנה אליו).
3. **שלח הודעה** מהטלפון **אל** המספר של טוויליו (`+14155238886` בסנדבוקס) – לא להפך. אם צריך, הצטרף לסנדבוקס (שלח את הקוד שטוויליו מציג).
4. **Second Brain → Inbox** → שורות עם **Source: whatsapp**.  
   אם לא רואים – Refresh; אם עדיין ריק – עוברים לבדיקה בבקאנד (לוגים + API).

---

## 3. איך לוודא בבקאנד

### התחברות (JWT)

קבל טוקן (אותו טוקן שהדשבורד משתמש בו):

```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@localhost","password":"devdevdev"}' | jq -r '.access_token')
```

(אם אין `jq`: פתח את התשובה והעתק ידנית את `access_token`.)

### רשימת אירועים (Inbox = מה שהדשבורד מציג)

```bash
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/events" | jq '.data[] | {source, topic, payloadPreview: .payloadPreview[0:80]}'
```

- **Gmail:** חפש אובייקטים עם `source: "gmail"`.
- **Calendar:** `source: "calendar"`.
- **WhatsApp:** `source: "whatsapp"`.

אם יש אירועים כאן אבל לא ב־Inbox ב־UI – הבעיה בדשבורד (כתובת API, tenant, וכו').  
אם אין אירועים כאן – הבעיה ב־ingest (Sync לא רץ / Webhook לא מגיע או נכשל).

### לוגים (במיוחד ל־WhatsApp)

אחרי שליחת הודעה למספר הטוויליו:

```bash
docker logs kirp-api 2>&1 | tail -100
```

חפש:

- `POST /api/v1/webhooks/whatsapp` – טוויליו הגיע ל־API.
- שגיאות 4xx/5xx או stack trace – בעיה ב־signature / parsing וכו'.

אם **אין** שום שורת `POST .../webhooks/whatsapp` אחרי שליחת הודעה – טוויליו לא מגיע ל־API (כתובת Webhook לא נכונה או לא גלויה, למשל localhost).

---

## 4. סיכום מהיר

| מה רוצים לוודא | ב־UI | בבקאנד |
|-----------------|------|--------|
| **מייל (Gmail)** | Connections → Gmail → Sync Now, אחר כך Inbox → Source: gmail | `GET /api/events` עם JWT → `source: "gmail"` |
| **לוח שנה**     | Connections → Calendar → Sync Now, אחר כך Inbox → Source: calendar | `GET /api/events` → `source: "calendar"` |
| **WhatsApp**     | Inbox → Source: whatsapp (אחרי שליחת הודעה למספר הטוויליו ו־Webhook גלוי) | לוגים: `POST .../webhooks/whatsapp`; `GET /api/events` → `source: "whatsapp"` |

**"התראות"** במערכת = לראות את האירועים ב־**Inbox** (ולרענן אם צריך). אין כרגע התראת פופאפ על מייל / לוח שנה / ווצאטסאפ – רק רשימה ב־Second Brain → Inbox.
