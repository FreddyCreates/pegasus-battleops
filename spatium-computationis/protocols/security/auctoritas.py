"""
Protocol: Auctoritas  🛡️
Meaning: Verify permissions and authorize actions.

Handles:
- Role-based access control (RBAC)
- Permission checking
- Resource-level authorization
- Scope validation
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class PermissionLevel(str, Enum):
    """Permission access levels."""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    OWNER = "owner"


class ResourceType(str, Enum):
    """Types of resources that can be protected."""
    PROJECT = "project"
    DOCUMENT = "document"
    ESTIMATE = "estimate"
    AGENT = "agent"
    SYSTEM = "system"
    USER = "user"
    API = "api"


class AuthorizationStatus(str, Enum):
    """Authorization result status."""
    ALLOWED = "allowed"
    DENIED = "denied"
    INSUFFICIENT_SCOPE = "insufficient_scope"
    RESOURCE_NOT_FOUND = "resource_not_found"
    INVALID_PERMISSION = "invalid_permission"


class Permission(BaseModel):
    """A specific permission grant."""
    permission_id: str
    subject: str  # User or role
    resource_type: ResourceType
    resource_id: str | None = None  # Specific resource or None for all
    level: PermissionLevel
    conditions: dict[str, Any] = Field(default_factory=dict)
    granted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    granted_by: str | None = None


class AuthorizationResult(BaseModel):
    """Result of an authorization check."""
    request_id: str
    subject: str
    action: str
    resource_type: ResourceType
    resource_id: str | None
    status: AuthorizationStatus
    authorized: bool = False
    
    # Details
    matched_permission: Permission | None = None
    required_level: PermissionLevel
    actual_level: PermissionLevel = PermissionLevel.NONE
    
    # Metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str | None = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "authz.db"


def _init_authz_db() -> None:
    """Initialize the authorization database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Permissions
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS permissions (
                permission_id   TEXT PRIMARY KEY,
                subject         TEXT NOT NULL,
                resource_type   TEXT NOT NULL,
                resource_id     TEXT,
                level           TEXT NOT NULL,
                conditions      TEXT DEFAULT '{}',
                granted_at      TEXT NOT NULL,
                expires_at      TEXT,
                granted_by      TEXT,
                active          INTEGER DEFAULT 1
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_perm_subject ON permissions(subject)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_perm_resource ON permissions(resource_type, resource_id)")
        
        # Roles
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS roles (
                role_id         TEXT PRIMARY KEY,
                role_name       TEXT UNIQUE NOT NULL,
                description     TEXT,
                permissions     TEXT DEFAULT '[]',
                created_at      TEXT NOT NULL
            )
            """
        )
        
        # Role assignments
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS role_assignments (
                assignment_id   TEXT PRIMARY KEY,
                subject         TEXT NOT NULL,
                role_id         TEXT NOT NULL,
                assigned_at     TEXT NOT NULL,
                expires_at      TEXT,
                UNIQUE(subject, role_id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ra_subject ON role_assignments(subject)")
        
        # Authorization log
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS authz_log (
                log_id          TEXT PRIMARY KEY,
                request_id      TEXT NOT NULL,
                subject         TEXT NOT NULL,
                action          TEXT NOT NULL,
                resource_type   TEXT NOT NULL,
                resource_id     TEXT,
                status          TEXT NOT NULL,
                timestamp       TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_al_subject ON authz_log(subject)")
        
        # Insert default roles
        default_roles = [
            ("role_admin", "admin", "Full system access", '["admin"]'),
            ("role_user", "user", "Standard user access", '["read", "write"]'),
            ("role_viewer", "viewer", "Read-only access", '["read"]'),
            ("role_agent", "agent", "Agent service access", '["read", "write", "execute"]'),
        ]
        for role_id, name, desc, perms in default_roles:
            conn.execute(
                """
                INSERT OR IGNORE INTO roles (role_id, role_name, description, permissions, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (role_id, name, desc, perms, datetime.now(timezone.utc).isoformat())
            )
        
        conn.commit()


_init_authz_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Permission Level Hierarchy
# ---------------------------------------------------------------------------

PERMISSION_HIERARCHY = {
    PermissionLevel.NONE: 0,
    PermissionLevel.READ: 1,
    PermissionLevel.WRITE: 2,
    PermissionLevel.DELETE: 3,
    PermissionLevel.ADMIN: 4,
    PermissionLevel.OWNER: 5,
}

ACTION_TO_LEVEL = {
    "read": PermissionLevel.READ,
    "view": PermissionLevel.READ,
    "list": PermissionLevel.READ,
    "get": PermissionLevel.READ,
    "write": PermissionLevel.WRITE,
    "create": PermissionLevel.WRITE,
    "update": PermissionLevel.WRITE,
    "delete": PermissionLevel.DELETE,
    "remove": PermissionLevel.DELETE,
    "admin": PermissionLevel.ADMIN,
    "manage": PermissionLevel.ADMIN,
    "configure": PermissionLevel.ADMIN,
    "transfer": PermissionLevel.OWNER,
    "own": PermissionLevel.OWNER,
}


def _level_satisfies(actual: PermissionLevel, required: PermissionLevel) -> bool:
    """Check if actual permission level satisfies required level."""
    return PERMISSION_HIERARCHY.get(actual, 0) >= PERMISSION_HIERARCHY.get(required, 0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def authorize_action(
    subject: str,
    action: str,
    resource_type: ResourceType,
    resource_id: str | None = None,
    scopes: list[str] | None = None,
) -> AuthorizationResult:
    """
    Protocol Auctoritas: check if a subject can perform an action on a resource.
    """
    request_id = str(uuid.uuid4())
    required_level = ACTION_TO_LEVEL.get(action.lower(), PermissionLevel.READ)
    
    # Get subject's effective permissions
    permissions = await _get_subject_permissions(subject, resource_type, resource_id)
    
    # Find highest permission level
    actual_level = PermissionLevel.NONE
    matched_perm = None
    
    for perm in permissions:
        if _level_satisfies(perm.level, required_level):
            if PERMISSION_HIERARCHY.get(perm.level, 0) > PERMISSION_HIERARCHY.get(actual_level, 0):
                actual_level = perm.level
                matched_perm = perm
    
    # Check scope requirements
    if scopes:
        scope_satisfied = any(s in scopes for s in ["admin", action, f"{resource_type.value}:{action}"])
        if not scope_satisfied:
            result = AuthorizationResult(
                request_id=request_id,
                subject=subject,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                status=AuthorizationStatus.INSUFFICIENT_SCOPE,
                authorized=False,
                required_level=required_level,
                actual_level=actual_level,
                reason=f"Required scope for {action} not found",
            )
            _log_authorization(result)
            return result
    
    # Determine authorization
    authorized = _level_satisfies(actual_level, required_level)
    
    result = AuthorizationResult(
        request_id=request_id,
        subject=subject,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=AuthorizationStatus.ALLOWED if authorized else AuthorizationStatus.DENIED,
        authorized=authorized,
        matched_permission=matched_perm,
        required_level=required_level,
        actual_level=actual_level,
        reason=None if authorized else f"Insufficient permission: has {actual_level.value}, needs {required_level.value}",
    )
    
    _log_authorization(result)
    return result


async def check_permission(
    subject: str,
    resource_type: ResourceType,
    resource_id: str | None = None,
) -> PermissionLevel:
    """Get the effective permission level for a subject on a resource."""
    permissions = await _get_subject_permissions(subject, resource_type, resource_id)
    
    highest_level = PermissionLevel.NONE
    for perm in permissions:
        if PERMISSION_HIERARCHY.get(perm.level, 0) > PERMISSION_HIERARCHY.get(highest_level, 0):
            highest_level = perm.level
    
    return highest_level


async def grant_permission(
    subject: str,
    resource_type: ResourceType,
    level: PermissionLevel,
    resource_id: str | None = None,
    granted_by: str | None = None,
    expires_at: datetime | None = None,
    conditions: dict[str, Any] | None = None,
) -> Permission:
    """Grant a permission to a subject."""
    permission_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    permission = Permission(
        permission_id=permission_id,
        subject=subject,
        resource_type=resource_type,
        resource_id=resource_id,
        level=level,
        conditions=conditions or {},
        granted_at=now,
        expires_at=expires_at,
        granted_by=granted_by,
    )
    
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO permissions (
                permission_id, subject, resource_type, resource_id, level,
                conditions, granted_at, expires_at, granted_by, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                permission_id,
                subject,
                resource_type.value,
                resource_id,
                level.value,
                json.dumps(conditions or {}),
                now.isoformat(),
                expires_at.isoformat() if expires_at else None,
                granted_by,
            )
        )
        conn.commit()
    
    return permission


async def revoke_permission(permission_id: str) -> bool:
    """Revoke a permission."""
    with _db() as conn:
        cursor = conn.execute(
            "UPDATE permissions SET active = 0 WHERE permission_id = ?",
            (permission_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


async def _get_subject_permissions(
    subject: str,
    resource_type: ResourceType,
    resource_id: str | None = None,
) -> list[Permission]:
    """Get all effective permissions for a subject."""
    permissions = []
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        # Direct permissions
        query = """
            SELECT * FROM permissions 
            WHERE subject = ? AND resource_type = ? AND active = 1
            AND (expires_at IS NULL OR expires_at > ?)
        """
        params: list = [subject, resource_type.value, now.isoformat()]
        
        if resource_id:
            query += " AND (resource_id IS NULL OR resource_id = ?)"
            params.append(resource_id)
        
        rows = conn.execute(query, params).fetchall()
        
        for row in rows:
            permissions.append(Permission(
                permission_id=row["permission_id"],
                subject=row["subject"],
                resource_type=ResourceType(row["resource_type"]),
                resource_id=row["resource_id"],
                level=PermissionLevel(row["level"]),
                conditions=json.loads(row["conditions"]) if row["conditions"] else {},
                granted_at=datetime.fromisoformat(row["granted_at"]),
                expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                granted_by=row["granted_by"],
            ))
        
        # Role-based permissions
        role_rows = conn.execute(
            """
            SELECT r.permissions FROM roles r
            JOIN role_assignments ra ON r.role_id = ra.role_id
            WHERE ra.subject = ? AND (ra.expires_at IS NULL OR ra.expires_at > ?)
            """,
            (subject, now.isoformat())
        ).fetchall()
        
        for role_row in role_rows:
            role_perms = json.loads(role_row["permissions"]) if role_row["permissions"] else []
            for perm_name in role_perms:
                try:
                    level = PermissionLevel(perm_name)
                except ValueError:
                    level = PermissionLevel.READ
                
                permissions.append(Permission(
                    permission_id=f"role_{subject}_{perm_name}",
                    subject=subject,
                    resource_type=resource_type,
                    level=level,
                ))
    
    return permissions


def _log_authorization(result: AuthorizationResult) -> None:
    """Log an authorization decision."""
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO authz_log (log_id, request_id, subject, action, resource_type, resource_id, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                result.request_id,
                result.subject,
                result.action,
                result.resource_type.value,
                result.resource_id,
                result.status.value,
                result.timestamp.isoformat(),
            )
        )
        conn.commit()
