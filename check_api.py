import openai
import os

# הדרך הכי בטוחה לבדוק - תכניס את המפתח ישירות כאן (רק לבדיקה!)
client = openai.OpenAI(
    api_key="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" # שים פה את המפתח המלא
)

try:
    print("בודק חיבור ל-OpenAI...")
    # ניסיון לבצע קריאה פשוטה מאוד
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "test"}],
        max_tokens=5
    )
    print("הצלחה! הנה התגובה מה-AI:")
    print(response.choices[0].message.content)

except openai.AuthenticationError:
    print("שגיאה: המפתח עדיין לא מזוהה (Authentication Error).")
    print("ודא שהעתקת את המפתח המלא כולל ה-sk-proj- והסיומת.")
except openai.RateLimitError:
    print("שגיאה: נגמר הכסף או שעדיין לא התעדכן (Rate Limit).")
except Exception as e:
    print(f"קרתה שגיאה אחרת: {e}")