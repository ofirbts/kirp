from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
# ייבוא פונקציית יצירת הטוקן מהקובץ הקודם
from app.core.security import create_access_token 

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(request: LoginRequest):
    # הבדיקה של אופיר
    if request.username == "ofir" and request.password == "admin123":
        # יצירת טוקן חתום ותקין (JWT)
        token = create_access_token(data={"sub": "ofir", "role": "admin"})
        
        return {
            "status": "success",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "user_id": "ofir",
                "full_name": "Ofir Admin"
            }
        }
    
    raise HTTPException(status_code=401, detail="Invalid credentials")