import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.persistence import PersistenceManager
from app.core.security import create_access_token

router = APIRouter(prefix="/auth/google", tags=["auth"])

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

class GoogleCallbackRequest(BaseModel):
    code: str

@router.post("/callback")
async def google_callback(payload: GoogleCallbackRequest):
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    # וודא שזה תואם ל-EXTERNAL_URL ב-UI
    redirect_uri = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8501")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Exchange Code for Token
        token_res = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": payload.code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Google Error: {token_res.text}")

        access_token = token_res.json().get("access_token")

        # 2. Get User Info
        userinfo_res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        user_data = userinfo_res.json()
        email = user_data.get("email")

        # 3. Upsert User in DB
        await PersistenceManager.create_google_user(
            email=email,
            full_name=user_data.get("name"),
            avatar_url=user_data.get("picture")
        )

        # 4. Create internal JWT
        internal_token = create_access_token({"sub": email, "email": email})

        return {
            "access_token": internal_token,
            "user": {
                "user_id": email,
                "full_name": user_data.get("name")
            }
        }