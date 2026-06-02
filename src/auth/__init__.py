"""
Auth — Multi-tenant, RBAC, encryption.

- Tenants: root org → user private → shared → team → org
- RBAC + ABAC + policies
- Zero leakage; no cross-tenant access unless explicitly granted
"""

from src.auth.tenants import TenantEngine, Tenant, Space, SpaceKind
from src.auth.rbac import RBACEngine, Role, Permission
from src.auth.encryption import EncryptionEngine

__all__ = [
    "TenantEngine",
    "Tenant",
    "Space",
    "SpaceKind",
    "RBACEngine",
    "Role",
    "Permission",
    "EncryptionEngine",
]
