import os
from app.services.notion.null_impl import NullNotionService
from app.services.notion.notion_impl import NotionClient

token = os.getenv("NOTION_TOKEN")
db_id = os.getenv("NOTION_DATABASE_ID")

# רק אם שני המשתנים קיימים ולא על "mock", נפעיל את השירות האמיתי
if token and db_id and token not in ["mock", "YOUR_NOTION_TOKEN"]:
    # שים לב: הורדנו את ה-auth=token כי ה-Client מושך אותו לבד מה-env
    notion = NotionClient() 
else:
    notion = NullNotionService()