# איפה להכניס כל טוקן / פרט — .env מול UI

## סיכום מהיר

| מה | איפה | הערה |
|----|------|------|
| **ngrok authtoken** | `.env` בלבד | רק כדי שהסקריפט `run_ngrok.sh` יריץ ngrok |
| **Twilio (Account SID, Auth Token, מספר)** | `.env` (ובמקרה של Auth Token גם ב־UI) | הבקאנד קורא מ־.env ל־webhook ולשליחת הודעות |
| **Recovery code של Sandbox** | לא נכנס לקוד | שמור אצלך אם תצטרך לאפס גישה לסנדבוקס |
| **ב־UI (Connections → WhatsApp)** | Twilio Auth Token | רק כדי שהדשבורד יראה "Connected" |

---

## 1. ngrok

- **מה זה:** טוקן מהחשבון של ngrok (ngrok.com) — מאפשר להריץ `ngrok http 8000` ולחשוף את ה־API באינטרנט.
- **איפה:** **רק ב־`.env`** (הסקריפט קורא משם).

```env
NGROK_AUTHTOKEN=380mRoVMH0iW0qnV3xIRsHW857q_57TufZPEAqXWeRJdG1ZqV
```

- **ב־UI:** לא מכניסים כלום.
- **שימוש:** הרצת `./scripts/run_ngrok.sh` → מקבלים URL (למשל `https://xxxx.ngrok-free.app`). את ה־URL הזה מכניסים ב־Twilio כ־Webhook (לא ב־.env).

---

## 2. Twilio — מה מכניסים ואיפה

### ב־`.env` או `.env.development` (חובה כדי ש־WhatsApp webhook יעבוד)

**אם אתה מריץ עם Docker:** ה־API טוען `env_file: .env.development` — שים שם את Twilio (או וודא ש־.env.development כולל אותם).  
**אם אתה מריץ מקומית:** הבקאנד קורא מ־.env (או מהמשתנים שטענת).

הבקאנד משתמש בזה לאימות חתימת Twilio ולשליחת הודעות:

```env
WHATSAPP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=AC2c12235aba0ab58cca546d366859c595
TWILIO_AUTH_TOKEN=5a76571c1d3382080f79763e747762c7
TWILIO_NUMBER=whatsapp:+14155238886
```

- **TWILIO_AUTH_TOKEN:** העתק מהקונסול (Account → API keys & tokens → Auth Token, או "Show" ליד הטוקן). **חשוב:** חייב להיות **אותו** טוקן בדיוק כמו זה ש־Twilio משתמש בו לחתום על ה־webhook.
- **TWILIO_NUMBER:** מספר ה־WhatsApp Sandbox — בדוגמה `whatsapp:+14155238886`.

אופציונלי (אם אתה שולח הודעות ליעד קבוע):

```env
WHATSAPP_DEFAULT_TO=+972546736767
```

**כדי שהודעות WhatsApp יופיעו ב־Inbox** כשאתה מחובר כ־tenant אחר (לא default):  
הוסף את ה־tenant וה־user שלך (מהדשבורד / JWT):

```env
WHATSAPP_WEBHOOK_TENANT_ID=dce15dfc-ef7d-4c3d-bfcc-4f01f6bd3edd
WHATSAPP_WEBHOOK_USER_ID=c655f431-53a4-4166-b4d7-afdbddb4d64a
```

(החלף ב־tenant_id ו־user_id האמיתיים שלך — אפשר לראות ב־Network כשאתה נכנס ל־Connections, או ב־/api/v1/auth/me.)

**WHATSAPP_VERIFY_TOKEN / WHATSAPP_PHONE_ID / WHATSAPP_TOKEN:** משמשים ספקים אחרים (למשל Meta). עם Twilio אפשר להשאיר ריק או לא להגדיר.

### ב־UI (Connections → WhatsApp → Connect)

בשדה "Token / URL" מכניסים **רק** את **Twilio Auth Token** (אותה מחרוזת כמו `TWILIO_AUTH_TOKEN` ב־.env), כדי שהדשבורד יראה "Connected". הבקאנד לא משתמש במה ששמור ב־Connections ל־webhook — הוא קורא מ־.env.

### ב־Twilio Console (לא ב־.env ולא ב־UI)

- **When a message comes in (Webhook URL):**  
  `https://<ה-URL-של-ngrok>/api/v1/webhooks/whatsapp`  
  (למשל `https://abc123.ngrok-free.app/api/v1/webhooks/whatsapp`).  
  זה ה־URL שטוויליו קורא כש**מישהו שולח הודעה למספר הטוויליו** (+14155238886).

---

## 3. Twilio WhatsApp Sandbox — Recovery code

- **מה זה:** קוד Twilio נותן להצטרפות/איפוס לסנדבוקס (למשל `SGXK2X1DRATVGBLPQK9PPPUN`).
- **איפה:** **לא** נכנס ל־.env ולא ל־UI. שומרים אצלך במקום בטוח אם תצטרך לאפס גישה לסנדבוקס.

---

## 4. השגיאה "Twilio signature validation failed" (403)

אם אתה רואה:

```text
WARNING: WhatsApp webhook Twilio signature validation failed
POST /api/v1/webhooks/whatsapp 403 Forbidden
```

זה קרה כי האימות השתמש ב־URL שונה מזה שטוויליו קרא (למשלבקאנד מאחורי ngrok/Docker).  
**תוקן:** הבקאנד משתמש ב־`X-Forwarded-Host` ו־`X-Forwarded-Proto` כדי לבנות את ה־URL הנכון לאימות.  
וודא ש־**TWILIO_AUTH_TOKEN** ב־.env **זהה** לטוקן האמיתי בקונסול (לא placeholder), והעלה מחדש את ה־API אחרי התיקון.

---

## 5. שאר ההודעות בלוג (OpenAI 400, Groq/Anthropic 404)

```text
HTTP Request: GET https://api.openai.com/v1/usage "HTTP/1.1 400 Bad Request"
HTTP Request: GET https://api.groq.com/dashboard/api/usage "HTTP/1.1 404 Not Found"
```

אלה קריאות של **דשבורד השימוש ב־LLM** (כמה טוקנים נצרכו). הן לא קשורות ל־WhatsApp. 400/404 בדרך כלל אומר ש־API key לא תומך ב־usage או שה־endpoint שונה — לא חוסם את ה־webhook של WhatsApp.

---

## צ'קליסט להרצה

1. **.env:**  
   `NGROK_AUTHTOKEN`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_NUMBER=whatsapp:+14155238886`.
2. **UI → Connections → WhatsApp:**  
   Connect עם **Twilio Auth Token** (אותה מחרוזת).
3. **ngrok:**  
   `./scripts/run_ngrok.sh` → להעתיק את ה־URL.
4. **Twilio Console:**  
   Webhook = `https://<ngrok-URL>/api/v1/webhooks/whatsapp`.
5. **API:**  
   רץ על פורט 8000 (Docker או מקומית), וה־API נבנה/הועלה אחרי התיקון של חתימת Twilio.
