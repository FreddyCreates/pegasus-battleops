"""
Protocol: Archivum  📦
Meaning: Data archival and restoration.

Handles:
- Data archival
- Compressed storage
- Retention policies
- Data restoration
"""

from __future__ import annotations

import gzip
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ArchiveStatus(str, Enum):
    """Status of archived data."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    RESTORED = "restored"
    EXPIRED = "expired"
    DELETED = "deleted"


class ArchiveConfig(BaseModel):
    """Configuration for archival."""
    retention_days: int = 365
    compression_enabled: bool = True
    encryption_enabled: bool = False


class ArchiveResult(BaseModel):
    """Result of an archive operation."""
    archive_id: str
    resource_type: str
    resource_id: str
    status: ArchiveStatus
    compressed_size: int | None = None
    original_size: int | None = None
    compression_ratio: float | None = None
    archived_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None


class ArchiveEntry(BaseModel):
    """An archived data entry."""
    archive_id: str
    resource_type: str
    resource_id: str
    
    # Data
    data: dict[str, Any]
    
    # Storage info
    compressed: bool = False
    original_size: int = 0
    compressed_size: int | None = None
    
    # Status
    status: ArchiveStatus = ArchiveStatus.ARCHIVED
    
    # Timing
    archived_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    restored_at: datetime | None = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "archive.db"


def _init_archive_db() -> None:
    """Initialize the archive database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS archives (
                archive_id      TEXT PRIMARY KEY,
                resource_type   TEXT NOT NULL,
                resource_id     TEXT NOT NULL,
                data            BLOB NOT NULL,
                compressed      INTEGER DEFAULT 1,
                original_size   INTEGER NOT NULL,
                compressed_size INTEGER,
                status          TEXT DEFAULT 'archived',
                archived_at     TEXT NOT NULL,
                expires_at      TEXT,
                restored_at     TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ar_resource ON archives(resource_type, resource_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ar_status ON archives(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ar_expires ON archives(expires_at)")
        conn.commit()


_init_archive_db()


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

async def archive_data(
    resource_type: str,
    resource_id: str,
    data: dict[str, Any],
    config: ArchiveConfig | None = None,
) -> ArchiveResult:
    """
    Protocol Archivum: archive data for long-term storage.
    """
    archive_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    cfg = config or ArchiveConfig()
    
    # Serialize data
    data_str = json.dumps(data)
    original_size = len(data_str)
    
    # Optionally compress
    if cfg.compression_enabled:
        data_bytes = gzip.compress(data_str.encode("utf-8"))
        compressed = True
        compressed_size = len(data_bytes)
    else:
        data_bytes = data_str.encode("utf-8")
        compressed = False
        compressed_size = original_size
    
    # Calculate expiration
    expires_at = now + timedelta(days=cfg.retention_days)
    
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO archives (
                archive_id, resource_type, resource_id, data, compressed,
                original_size, compressed_size, status, archived_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'archived', ?, ?)
            """,
            (
                archive_id,
                resource_type,
                resource_id,
                data_bytes,
                1 if compressed else 0,
                original_size,
                compressed_size,
                now.isoformat(),
                expires_at.isoformat(),
            )
        )
        conn.commit()
    
    compression_ratio = 1 - (compressed_size / original_size) if compressed else None
    
    return ArchiveResult(
        archive_id=archive_id,
        resource_type=resource_type,
        resource_id=resource_id,
        status=ArchiveStatus.ARCHIVED,
        compressed_size=compressed_size,
        original_size=original_size,
        compression_ratio=compression_ratio,
        archived_at=now,
        expires_at=expires_at,
    )


async def restore_data(
    archive_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> ArchiveEntry | None:
    """
    Protocol Archivum: restore archived data.
    """
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        if archive_id:
            row = conn.execute(
                "SELECT * FROM archives WHERE archive_id = ? AND status != 'deleted'",
                (archive_id,)
            ).fetchone()
        elif resource_type and resource_id:
            row = conn.execute(
                """
                SELECT * FROM archives 
                WHERE resource_type = ? AND resource_id = ? AND status != 'deleted'
                ORDER BY archived_at DESC LIMIT 1
                """,
                (resource_type, resource_id)
            ).fetchone()
        else:
            return None
        
        if not row:
            return None
        
        # Decompress if needed
        data_bytes = row["data"]
        if row["compressed"]:
            data_str = gzip.decompress(data_bytes).decode("utf-8")
        else:
            data_str = data_bytes.decode("utf-8") if isinstance(data_bytes, bytes) else data_bytes
        
        data = json.loads(data_str)
        
        # Update restored timestamp
        conn.execute(
            "UPDATE archives SET status = 'restored', restored_at = ? WHERE archive_id = ?",
            (now.isoformat(), row["archive_id"])
        )
        conn.commit()
        
        return ArchiveEntry(
            archive_id=row["archive_id"],
            resource_type=row["resource_type"],
            resource_id=row["resource_id"],
            data=data,
            compressed=bool(row["compressed"]),
            original_size=row["original_size"],
            compressed_size=row["compressed_size"],
            status=ArchiveStatus.RESTORED,
            archived_at=datetime.fromisoformat(row["archived_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            restored_at=now,
        )


async def list_archives(
    resource_type: str | None = None,
    status: ArchiveStatus | None = None,
    limit: int = 100,
) -> list[ArchiveResult]:
    """List archived data."""
    with _db() as conn:
        query = "SELECT * FROM archives WHERE 1=1"
        params: list[Any] = []
        
        if resource_type:
            query += " AND resource_type = ?"
            params.append(resource_type)
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        query += " ORDER BY archived_at DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        
        return [
            ArchiveResult(
                archive_id=row["archive_id"],
                resource_type=row["resource_type"],
                resource_id=row["resource_id"],
                status=ArchiveStatus(row["status"]),
                compressed_size=row["compressed_size"],
                original_size=row["original_size"],
                compression_ratio=1 - (row["compressed_size"] / row["original_size"]) if row["compressed"] else None,
                archived_at=datetime.fromisoformat(row["archived_at"]),
                expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            )
            for row in rows
        ]


async def delete_archive(archive_id: str) -> bool:
    """Mark an archive as deleted."""
    with _db() as conn:
        cursor = conn.execute(
            "UPDATE archives SET status = 'deleted' WHERE archive_id = ?",
            (archive_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


async def cleanup_expired_archives() -> int:
    """Remove expired archives."""
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        cursor = conn.execute(
            "UPDATE archives SET status = 'expired' WHERE expires_at < ? AND status = 'archived'",
            (now.isoformat(),)
        )
        conn.commit()
        return cursor.rowcount
