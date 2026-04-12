"""
V1 Auth API — signup, login, me.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from src.core.auth import get_user_store
from src.core.jwt_utils import create_access_token, require_auth
from src.services import tenants_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["V1 Auth"])


class SignupBody(BaseModel):
  email: EmailStr
  password: str = Field(min_length=8)
  name: str = Field(min_length=1)


class LoginBody(BaseModel):
  email: str  # allow dev@localhost for local dev (EmailStr rejects it)
  password: str


class AuthUser(BaseModel):
  id: str
  email: str  # allow dev@localhost for local dev
  name: str
  tenant_id: str
  roles: list[str]


class AuthResponse(BaseModel):
  access_token: str
  user: AuthUser


def _make_password_hash(password: str) -> str:
  pw = password.encode("utf-8")
  salt = bcrypt.gensalt()
  return bcrypt.hashpw(pw, salt).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
  try:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
  except Exception:
    return False


@router.post("/register", response_model=AuthResponse, status_code=201)
@router.post("/signup", response_model=AuthResponse, status_code=201)
async def signup(body: SignupBody) -> AuthResponse:
  """
  Create a user + tenant and return an access token.
  """
  store = get_user_store()
  existing = await store.get_user_by_email(str(body.email))
  if existing:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Email already registered",
    )

  # Create tenant + default space via existing service.
  tenant = await tenants_service.create_tenant(name=body.name or str(body.email))
  tenant_id = tenant.id

  try:
    await tenants_service.seed_saas_trial_for_signup(tenant_id, str(body.email))
  except tenants_service.TenantLifecycleError as e:
    logger.warning("seed_saas_trial_for_signup failed after signup tenant=%s: %s", tenant_id, e)

  # Hash password
  password_hash = _make_password_hash(body.password)

  # First user in tenant is admin by default.
  user = await store.create_user(
    email=str(body.email),
    password_hash=password_hash,
    name=body.name,
    tenant_id=tenant_id,
    roles=["admin"],
  )

  token = create_access_token(
    user_id=user.id,
    tenant_id=user.tenant_id,
    roles=user.roles,
    expires_in_seconds=int(os.getenv("JWT_EXPIRES_IN", "3600")),
  )
  await store.update_last_login(user.id)
  return AuthResponse(
    access_token=token,
    user=AuthUser(
      id=user.id,
      email=user.email,
      name=user.name,
      tenant_id=user.tenant_id,
      roles=user.roles,
    ),
  )


DEV_EMAIL = "dev@localhost"
DEV_PASSWORD = "devdevdev"  # match verify_activation.sh and common dev usage


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginBody) -> AuthResponse:
  """
  Authenticate with email + password. Returns access token and user.
  Real auth: user must exist in DB and password must match.
  """
  store = get_user_store()
  user = await store.get_user_by_email(str(body.email))
  if not user or not _verify_password(body.password, user.password_hash):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Invalid email or password",
    )

  token = create_access_token(
    user_id=user.id,
    tenant_id=user.tenant_id,
    roles=user.roles,
    expires_in_seconds=int(os.getenv("JWT_EXPIRES_IN", "3600")),
  )
  await store.update_last_login(user.id)
  return AuthResponse(
    access_token=token,
    user=AuthUser(
      id=user.id,
      email=user.email,
      name=user.name,
      tenant_id=user.tenant_id,
      roles=user.roles,
    ),
  )


def _default_dev_user() -> AuthUser:
  """Return a consistent dev user when SKIP_AUTH and no/invalid token."""
  return AuthUser(
    id="dev",
    email="dev@localhost",
    name="Dev",
    tenant_id="default",
    roles=["admin"],
  )


@router.get("/me", response_model=AuthUser)
async def me(request: Request) -> AuthUser:
  """
  Return authenticated user info from JWT.
  When SKIP_AUTH=1 and no valid Bearer token, return a default dev user so the UI
  can use tenant_id=default consistently and avoid 403 tenant mismatch.
  """
  skip = os.getenv("SKIP_AUTH", "").lower() in ("1", "true", "yes")
  auth = (request.headers.get("Authorization") or "").strip()
  token = auth[7:].strip() if auth.startswith("Bearer ") else ""

  if skip and not token:
    return _default_dev_user()

  if token:
    try:
      from src.core.jwt_utils import decode_token
      payload = decode_token(token)
      request.state.user = {
        "tenant_id": payload.get("tenant_id") or "default",
        "space_id": payload.get("space_id") or "all",
        "user_id": payload.get("user_id") or "dev",
        "roles": payload.get("roles") or [],
      }
      store = get_user_store()
      user_id = payload.get("user_id")
      if user_id:
        user = await store.get_user_by_id(user_id)
        if user:
          return AuthUser(
              id=user.id,
              email=user.email,
              name=user.name,
              tenant_id=user.tenant_id,
              roles=user.roles,
          )
      return AuthUser(
          id=payload.get("user_id") or "dev",
          email="dev@example.com",
          name="Dev",
          tenant_id=payload.get("tenant_id") or "default",
          roles=payload.get("roles") or ["admin"],
      )
    except HTTPException:
      if skip:
        return _default_dev_user()
      raise

  raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authorization header missing or invalid",
  )


@router.post("/refresh", response_model=AuthResponse)
async def refresh(request: Request) -> AuthResponse:
  """
  Refresh token. Expects Authorization: Bearer <refresh_token> or same access token.
  For minimal compatibility: if valid token present, issue new access token; else 401.
  """
  auth = (request.headers.get("Authorization") or "").strip()
  token = auth[7:].strip() if auth.startswith("Bearer ") else ""
  if not token:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
  try:
    from src.core.jwt_utils import decode_token
    payload = decode_token(token)
    store = get_user_store()
    user_id = payload.get("user_id")
    if user_id:
      user = await store.get_user_by_id(user_id)
      if user:
        new_token = create_access_token(
          user_id=user.id,
          tenant_id=user.tenant_id,
          roles=user.roles,
          expires_in_seconds=int(os.getenv("JWT_EXPIRES_IN", "3600")),
        )
        return AuthResponse(
          access_token=new_token,
          user=AuthUser(
            id=user.id,
            email=user.email,
            name=user.name,
            tenant_id=user.tenant_id,
            roles=user.roles,
          ),
        )
    return AuthResponse(
      access_token=create_access_token(
        user_id=payload.get("user_id") or "dev",
        tenant_id=payload.get("tenant_id") or "default",
        roles=payload.get("roles") or ["admin"],
        expires_in_seconds=int(os.getenv("JWT_EXPIRES_IN", "3600")),
      ),
      user=AuthUser(
        id=payload.get("user_id") or "dev",
        email="dev@example.com",
        name="Dev",
        tenant_id=payload.get("tenant_id") or "default",
        roles=payload.get("roles") or ["admin"],
      ),
    )
  except HTTPException:
    raise
  except Exception:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

