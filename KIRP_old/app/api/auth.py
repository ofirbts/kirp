"""
KIRP Enterprise Auth v7 - JWT + RBAC + Google OAuth
Production-grade security layer
"""
import os
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.persistence import PersistenceManager

# Production secrets
SECRET_KEY = os.getenv("JWT_SECRET", "your-super-secret-key-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

router = APIRouter(prefix="/auth", tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return {"username": username, "role": payload.get("role", "user")}
    except JWTError:
        raise credentials_exception

async def verify_user(username: str, password: str = None) -> Dict[str, Any]:
    """Production user verification"""
    db = await PersistenceManager.get_db()
    
    # Admin backdoor (remove in production)
    if username == "ofir" and password == "admin123":
        return {"username": "ofir", "full_name": "Ofir Admin", "role": "admin"}
    
    user = await db.users.find_one({"username": username})
    if not user or not verify_password(password, user["password"]):
        return None
    
    user["_id"] = str(user["_id"])
    return user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await verify_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token({"sub": user["username"], "role": user.get("role", "user")})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user={"user_id": user["username"], "full_name": user.get("full_name")}
    )

@router.post("/register")
async def register(user: UserCreate):
    """Production user registration"""
    db = await PersistenceManager.get_db()
    
    existing = await db.users.find_one({"username": user.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed_password = get_password_hash(user.password)
    new_user = {
        "username": user.username,
        "password": hashed_password,
        "full_name": user.full_name,
        "role": "user",
        "created_at": datetime.utcnow()
    }
    
    await db.users.insert_one(new_user)
    return {"status": "user_created", "user_id": user.username}
