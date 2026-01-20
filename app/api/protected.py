from fastapi import APIRouter, Depends
from app.core.security import get_current_user

router = APIRouter(prefix="/protected", tags=["protected"])

@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user": user}
