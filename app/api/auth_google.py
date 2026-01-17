
import os
import httpx
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.persistence import PersistenceManager, get_user
from typing import Dict, Any

REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8501")
router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)

class GoogleCallbackRequest(BaseModel):
    code: str

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/google/callback")
async def google_callback(payload: GoogleCallbackRequest):
    """OAuth callback - מחזיר user מלא מ‑Persistence"""
    code = payload.code
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not all([google_client_id, google_client_secret]):
        logger.error("Missing Google OAuth config")
        raise HTTPException(500, "Google OAuth not configured")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Token exchange
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": google_client_id,
                "client_secret": google_client_secret,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            }
        )

        if token_res.status_code != 200:
            logger.error(f"Token exchange failed: {token_res.text}")
            raise HTTPException(400, f"Token exchange failed: {token_res.status_code}")

        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(400, "No access token received")

        # User info
        user_info_res = await client.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if user_info_res.status_code != 200:
            logger.error(f"User info failed: {user_info_res.text}")
            raise HTTPException(400, "Failed to fetch user info")

        user_info = user_info_res.json()
        email = user_info.get("email")
        name = user_info.get("name", email)
        picture = user_info.get("picture")

        if not email:
            raise HTTPException(400, "Google user has no email")

        # Create/update user
        PersistenceManager.create_google_user(email=email, full_name=name, avatar_url=picture)
        
        # Log event
        PersistenceManager.append_event(
            user_id=email,
            event_type="google_login_success",
            data={"name": name, "picture": picture}
        )

        # Return full user data
        user = PersistenceManager.get_user(email)
        if not user:
            raise HTTPException(500, "User created but not found")

        logger.info(f"✅ Google login success: {email}")
        return {
            "status": "success",
            "user_id": user["username"],
            "full_name": user.get("full_name", email),
            "avatar_url": user.get("avatar_url"),
            "email": user.get("email")
        }

@router.post("/login")
async def local_login(request: LoginRequest):
    """Local username/password login"""
    user = PersistenceManager.verify_user(request.username, request.password)
    
    if not user:
        logger.warning(f"❌ Failed login attempt: {request.username}")
        PersistenceManager.append_event(
            user_id=request.username,
            event_type="login_failed",
            data={"username": request.username}
        )
        raise HTTPException(401, "Invalid credentials")
    
    # Log success
    PersistenceManager.append_event(
        user_id=user["username"],
        event_type="local_login_success",
        data={"username": user["username"]}
    )
    
    logger.info(f"✅ Local login success: {user['username']}")
    return {
        "status": "success",
        "user_id": user["username"],
        "full_name": user.get("full_name", user["username"]),
        "avatar_url": user.get("avatar_url"),
        "email": user.get("email")
    }

@router.get("/status/{user_id}")
async def get_user_status(user_id: str):
    """בדיקת מצב משתמש לפי ID"""
    user = PersistenceManager.get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    recent_events = PersistenceManager.get_user_events(user_id, limit=5)
    return {
        "user": user,
        "recent_activity": recent_events,
        "status": "active"
    }
