import json
import os
from google_auth_oauthlib.flow import InstalledAppFlow

# ההרשאות הדרושות
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly'
]

def get_token():
    # טעינת המפתח החדש שיצרת (Desktop App)
    if not os.path.exists('google_credentials2.json'):
        print("Error: קובץ google_credentials2.json לא נמצא בתיקייה!")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        'google_credentials2.json', SCOPES)
    
    # הפקודה הזו תנסה לפתוח דפדפן. 
    # אם אתה ב-WSL וזה נכשל, היא תדפיס לינק בטרמינל.
    creds = flow.run_local_server(port=0)
    
    # שמירת הטוקן
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    
    print("\n" + "="*30)
    print("הצלחה! קובץ token.json נוצר.")
    print("="*30)

if __name__ == '__main__':
    get_token()