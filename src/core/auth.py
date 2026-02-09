"""
Authentication core — User model and MongoDB-backed UserStore.

This is intentionally small and framework-agnostic. FastAPI routers should
import and use it for sign-up / login flows.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    name: str
    created_at: datetime
    last_login_at: Optional[datetime]
    roles: list[str]
    tenant_id: str
    meta: dict[str, Any]

    def to_doc(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "password_hash": self.password_hash,
            "name": self.name,
            "created_at": self.created_at,
            "last_login_at": self.last_login_at,
            "roles": self.roles,
            "tenant_id": self.tenant_id,
            "meta": self.meta or {},
        }

    @classmethod
    def from_doc(cls, doc: dict[str, Any]) -> "User":
        return cls(
            id=doc.get("id", ""),
            email=doc.get("email", ""),
            password_hash=doc.get("password_hash", ""),
            name=doc.get("name", ""),
            created_at=doc.get("created_at") or datetime.now(timezone.utc),
            last_login_at=doc.get("last_login_at"),
            roles=list(doc.get("roles") or []),
            tenant_id=doc.get("tenant_id", ""),
            meta=doc.get("meta") or {},
        )


class UserStore:
    """MongoDB store for users. Collection: users."""

    def __init__(self, mongo_uri: str, db_name: str = "kirp") -> None:
        self._mongo_uri = mongo_uri
        self._db_name = db_name
        self._client: Any = None
        self._db: Any = None

    async def connect(self) -> None:
        if self._db is not None:
            return
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            self._client = AsyncIOMotorClient(self._mongo_uri)
            self._db = self._client[self._db_name]
            await self._db.command("ping")
            # Index: users by email (unique) and tenant_id
            await self._db.users.create_index("email", unique=True)
            await self._db.users.create_index([("tenant_id", 1), ("created_at", -1)])
            logger.info("UserStore connected to MongoDB")
        except Exception as e:
            logger.error("UserStore connect failed: %s", e)
            raise

    @property
    def _coll(self):
        if self._db is None:
            return None
        return self._db.users

    async def create_user(self, email: str, password_hash: str, name: str, tenant_id: str, roles: Optional[list[str]] = None) -> User:
        await self.connect()
        now = datetime.now(timezone.utc)
        user = User(
            id=str(uuid4()),
            email=email.lower().strip(),
            password_hash=password_hash,
            name=name.strip() or email,
            created_at=now,
            last_login_at=None,
            roles=roles or ["user"],
            tenant_id=tenant_id,
            meta={},
        )
        await self._coll.insert_one(user.to_doc())
        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        await self.connect()
        doc = await self._coll.find_one({"email": email.lower().strip()})
        return User.from_doc(doc) if doc else None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        await self.connect()
        doc = await self._coll.find_one({"id": user_id})
        return User.from_doc(doc) if doc else None

    async def update_last_login(self, user_id: str) -> None:
        await self.connect()
        await self._coll.update_one(
            {"id": user_id},
            {"$set": {"last_login_at": datetime.now(timezone.utc)}},
        )

    async def list_users(self, tenant_id: str) -> list[User]:
        await self.connect()
        cursor = self._coll.find({"tenant_id": tenant_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=1000)
        return [User.from_doc(d) for d in docs]


_user_store: Optional[UserStore] = None


def get_user_store(mongo_uri: Optional[str] = None) -> UserStore:
    global _user_store
    if _user_store is None:
        import os
        _user_store = UserStore(
            mongo_uri or os.getenv("MONGO_URI", "mongodb://root:example@localhost:27017/kirp?authSource=admin")
        )
    return _user_store
