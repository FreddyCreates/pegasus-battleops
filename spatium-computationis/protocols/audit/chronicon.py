"""
Protocol: Chronicon  📝
Meaning: Audit logging for all system activities.

Handles:
- Activity logging
- User action tracking
- System event recording
- Audit trail queries
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    """Types of auditable actions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"
    EXECUTE = "execute"
    CONFIGURE = "configure"
    SYSTEM = "system"


class AuditEntry(BaseModel):
    """An audit log entry."""
    entry_id: str
    action: AuditAction
    resource_type: str
    resource_id: str | None = None
    
    # Actor
    actor_id: str | None = None
    actor_type: str = "user"  # user, system, agent
    
    # Details
    description: str
    old_value: Any = None
    new_value: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    # Context
    ip_address: str | None = None
    user_agent: str | None = None
    trace_id: str | None = None
    
    # Timing
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Status
    success: bool = True
    error: str | None = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "audit.db"


def _init_audit_db() -> None:
    """Initialize the audit database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                entry_id        TEXT PRIMARY KEY,
                action          TEXT NOT NULL,
                resource_type   TEXT NOT NULL,
                resource_id     TEXT,
                actor_id        TEXT,
                actor_type      TEXT DEFAULT 'user',
                description     TEXT NOT NULL,
                old_value       TEXT,
                new_value       TEXT,
                metadata        TEXT DEFAULT '{}',
                ip_address      TEXT,
                user_agent      TEXT,
                trace_id        TEXT,
                timestamp       TEXT NOT NULL,
                success         INTEGER DEFAULT 1,
                error           TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_al_action ON audit_log(action)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_al_resource ON audit_log(resource_type, resource_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_al_actor ON audit_log(actor_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_al_timestamp ON audit_log(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_al_trace ON audit_log(trace_id)")
        conn.commit()


_init_audit_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def log_activity(
    action: AuditAction,
    resource_type: str,
    description: str,
    resource_id: str | None = None,
    actor_id: str | None = None,
    actor_type: str = "user",
    old_value: Any = None,
    new_value: Any = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    trace_id: str | None = None,
    success: bool = True,
    error: str | None = None,
) -> AuditEntry:
    """
    Protocol Chronicon: log an activity to the audit trail.
    """
    entry_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    entry = AuditEntry(
        entry_id=entry_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_id=actor_id,
        actor_type=actor_type,
        description=description,
        old_value=old_value,
        new_value=new_value,
        metadata=metadata or {},
        ip_address=ip_address,
        user_agent=user_agent,
        trace_id=trace_id,
        timestamp=now,
        success=success,
        error=error,
    )
    
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO audit_log (
                entry_id, action, resource_type, resource_id, actor_id, actor_type,
                description, old_value, new_value, metadata, ip_address, user_agent,
                trace_id, timestamp, success, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_id,
                action.value,
                resource_type,
                resource_id,
                actor_id,
                actor_type,
                description,
                json.dumps(old_value) if old_value is not None else None,
                json.dumps(new_value) if new_value is not None else None,
                json.dumps(metadata or {}),
                ip_address,
                user_agent,
                trace_id,
                now.isoformat(),
                1 if success else 0,
                error,
            )
        )
        conn.commit()
    
    return entry


async def get_activity_log(
    resource_type: str | None = None,
    resource_id: str | None = None,
    actor_id: str | None = None,
    action: AuditAction | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 100,
) -> list[AuditEntry]:
    """
    Protocol Chronicon: query the audit log.
    """
    with _db() as conn:
        query = "SELECT * FROM audit_log WHERE 1=1"
        params: list[Any] = []
        
        if resource_type:
            query += " AND resource_type = ?"
            params.append(resource_type)
        
        if resource_id:
            query += " AND resource_id = ?"
            params.append(resource_id)
        
        if actor_id:
            query += " AND actor_id = ?"
            params.append(actor_id)
        
        if action:
            query += " AND action = ?"
            params.append(action.value)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        
        return [
            AuditEntry(
                entry_id=row["entry_id"],
                action=AuditAction(row["action"]),
                resource_type=row["resource_type"],
                resource_id=row["resource_id"],
                actor_id=row["actor_id"],
                actor_type=row["actor_type"],
                description=row["description"],
                old_value=json.loads(row["old_value"]) if row["old_value"] else None,
                new_value=json.loads(row["new_value"]) if row["new_value"] else None,
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                ip_address=row["ip_address"],
                user_agent=row["user_agent"],
                trace_id=row["trace_id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                success=bool(row["success"]),
                error=row["error"],
            )
            for row in rows
        ]


async def get_resource_history(
    resource_type: str,
    resource_id: str,
    limit: int = 50,
) -> list[AuditEntry]:
    """Get complete history for a specific resource."""
    return await get_activity_log(
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
    )


async def get_user_activity(
    actor_id: str,
    hours: int = 24,
    limit: int = 100,
) -> list[AuditEntry]:
    """Get recent activity for a user."""
    start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    return await get_activity_log(
        actor_id=actor_id,
        start_time=start_time,
        limit=limit,
    )
