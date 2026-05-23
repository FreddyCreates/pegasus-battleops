"""
Protocol: Historia  🕐
Meaning: Version history and change tracking.

Handles:
- Version recording
- Change comparison
- History queries
- Rollback support
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class VersionEntry(BaseModel):
    """A version history entry."""
    version_id: str
    resource_type: str
    resource_id: str
    version_number: int
    
    # Content
    data: dict[str, Any]
    data_hash: str
    
    # Metadata
    change_type: str = "update"  # create, update, delete
    change_summary: str | None = None
    changed_fields: list[str] = Field(default_factory=list)
    
    # Actor
    changed_by: str | None = None
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "versions.db"


def _init_versions_db() -> None:
    """Initialize the versions database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS version_history (
                version_id      TEXT PRIMARY KEY,
                resource_type   TEXT NOT NULL,
                resource_id     TEXT NOT NULL,
                version_number  INTEGER NOT NULL,
                data            TEXT NOT NULL,
                data_hash       TEXT NOT NULL,
                change_type     TEXT DEFAULT 'update',
                change_summary  TEXT,
                changed_fields  TEXT DEFAULT '[]',
                changed_by      TEXT,
                created_at      TEXT NOT NULL,
                UNIQUE(resource_type, resource_id, version_number)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vh_resource ON version_history(resource_type, resource_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vh_time ON version_history(created_at)")
        conn.commit()


_init_versions_db()


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

async def record_version(
    resource_type: str,
    resource_id: str,
    data: dict[str, Any],
    change_type: str = "update",
    change_summary: str | None = None,
    changed_by: str | None = None,
) -> VersionEntry:
    """
    Protocol Historia: record a new version of a resource.
    """
    version_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Calculate data hash
    data_str = json.dumps(data, sort_keys=True)
    data_hash = hashlib.sha256(data_str.encode()).hexdigest()
    
    # Get next version number
    with _db() as conn:
        row = conn.execute(
            "SELECT MAX(version_number) as max_ver FROM version_history WHERE resource_type = ? AND resource_id = ?",
            (resource_type, resource_id)
        ).fetchone()
        
        version_number = (row["max_ver"] or 0) + 1
        
        # Detect changed fields
        changed_fields = []
        if version_number > 1:
            prev = conn.execute(
                """
                SELECT data FROM version_history 
                WHERE resource_type = ? AND resource_id = ? AND version_number = ?
                """,
                (resource_type, resource_id, version_number - 1)
            ).fetchone()
            
            if prev:
                prev_data = json.loads(prev["data"])
                changed_fields = _detect_changes(prev_data, data)
        
        entry = VersionEntry(
            version_id=version_id,
            resource_type=resource_type,
            resource_id=resource_id,
            version_number=version_number,
            data=data,
            data_hash=data_hash,
            change_type=change_type,
            change_summary=change_summary,
            changed_fields=changed_fields,
            changed_by=changed_by,
            created_at=now,
        )
        
        conn.execute(
            """
            INSERT INTO version_history (
                version_id, resource_type, resource_id, version_number,
                data, data_hash, change_type, change_summary, changed_fields,
                changed_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                resource_type,
                resource_id,
                version_number,
                data_str,
                data_hash,
                change_type,
                change_summary,
                json.dumps(changed_fields),
                changed_by,
                now.isoformat(),
            )
        )
        conn.commit()
    
    return entry


async def get_version_history(
    resource_type: str,
    resource_id: str,
    limit: int = 50,
) -> list[VersionEntry]:
    """
    Protocol Historia: get version history for a resource.
    """
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM version_history 
            WHERE resource_type = ? AND resource_id = ?
            ORDER BY version_number DESC
            LIMIT ?
            """,
            (resource_type, resource_id, limit)
        ).fetchall()
        
        return [
            VersionEntry(
                version_id=row["version_id"],
                resource_type=row["resource_type"],
                resource_id=row["resource_id"],
                version_number=row["version_number"],
                data=json.loads(row["data"]),
                data_hash=row["data_hash"],
                change_type=row["change_type"],
                change_summary=row["change_summary"],
                changed_fields=json.loads(row["changed_fields"]) if row["changed_fields"] else [],
                changed_by=row["changed_by"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]


async def get_version(
    resource_type: str,
    resource_id: str,
    version_number: int,
) -> VersionEntry | None:
    """Get a specific version."""
    with _db() as conn:
        row = conn.execute(
            """
            SELECT * FROM version_history 
            WHERE resource_type = ? AND resource_id = ? AND version_number = ?
            """,
            (resource_type, resource_id, version_number)
        ).fetchone()
        
        if not row:
            return None
        
        return VersionEntry(
            version_id=row["version_id"],
            resource_type=row["resource_type"],
            resource_id=row["resource_id"],
            version_number=row["version_number"],
            data=json.loads(row["data"]),
            data_hash=row["data_hash"],
            change_type=row["change_type"],
            change_summary=row["change_summary"],
            changed_fields=json.loads(row["changed_fields"]) if row["changed_fields"] else [],
            changed_by=row["changed_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


async def compare_versions(
    resource_type: str,
    resource_id: str,
    version1: int,
    version2: int,
) -> dict[str, Any]:
    """Compare two versions of a resource."""
    v1 = await get_version(resource_type, resource_id, version1)
    v2 = await get_version(resource_type, resource_id, version2)
    
    if not v1 or not v2:
        return {"error": "Version not found"}
    
    changed = _detect_changes(v1.data, v2.data)
    added = [k for k in v2.data if k not in v1.data]
    removed = [k for k in v1.data if k not in v2.data]
    
    return {
        "version1": version1,
        "version2": version2,
        "changed_fields": changed,
        "added_fields": added,
        "removed_fields": removed,
    }


def _detect_changes(old: dict, new: dict) -> list[str]:
    """Detect which fields changed between two versions."""
    changed = []
    
    all_keys = set(old.keys()) | set(new.keys())
    for key in all_keys:
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val != new_val:
            changed.append(key)
    
    return changed
