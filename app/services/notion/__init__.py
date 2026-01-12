import os
# שימוש בנתיב מלא במקום יחסי
from app.services.notion.notion_impl import RealNotionService
from app.services.notion.null_impl import NullNotionService

token = os.getenv("NOTION_TOKEN")
if token and token not in ["mock", "YOUR_NOTION_TOKEN"]:
    notion = RealNotionService()
else:
    notion = NullNotionService()