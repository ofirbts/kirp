from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from app.core.persistence import PersistenceManager

templates = Jinja2Templates(directory="app/ui/templates")
router = APIRouter()

@router.get("/sessions")
def sessions(request: Request):
    return templates.TemplateResponse(
        "sessions.html",
        {"request": request, "sessions": PersistenceManager.list_sessions()}
    )
