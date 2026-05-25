"""
Protocol: Coda  📋
Meaning: Message queue management.

Handles:
- Message enqueueing
- Priority-based processing
- Dead letter handling
- Queue statistics
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


class QueuePriority(str, Enum):
    """Message priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageStatus(str, Enum):
    """Message processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class QueueConfig(BaseModel):
    """Configuration for a queue."""
    queue_name: str
    max_retries: int = 3
    visibility_timeout_seconds: int = 30
    retention_days: int = 7
    dead_letter_queue: str | None = None


class QueueMessage(BaseModel):
    """A message in the queue."""
    message_id: str
    queue_name: str
    payload: dict[str, Any]
    
    # Priority and ordering
    priority: QueuePriority = QueuePriority.NORMAL
    
    # Status
    status: MessageStatus = MessageStatus.PENDING
    retry_count: int = 0
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    visible_at: datetime | None = None
    processed_at: datetime | None = None
    
    # Processing
    receipt_handle: str | None = None
    error: str | None = None


class QueueStats(BaseModel):
    """Statistics for a queue."""
    queue_name: str
    pending_count: int = 0
    processing_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    dead_letter_count: int = 0
    avg_processing_time_ms: float | None = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "queues.db"


def _init_queues_db() -> None:
    """Initialize the queues database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Queue configurations
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS queue_configs (
                queue_name      TEXT PRIMARY KEY,
                max_retries     INTEGER DEFAULT 3,
                visibility_timeout INTEGER DEFAULT 30,
                retention_days  INTEGER DEFAULT 7,
                dead_letter_queue TEXT,
                created_at      TEXT NOT NULL
            )
            """
        )
        
        # Messages
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS queue_messages (
                message_id      TEXT PRIMARY KEY,
                queue_name      TEXT NOT NULL,
                payload         TEXT NOT NULL,
                priority        TEXT DEFAULT 'normal',
                status          TEXT DEFAULT 'pending',
                retry_count     INTEGER DEFAULT 0,
                created_at      TEXT NOT NULL,
                visible_at      TEXT,
                processed_at    TEXT,
                receipt_handle  TEXT,
                error           TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qm_queue ON queue_messages(queue_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qm_status ON queue_messages(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qm_visible ON queue_messages(visible_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qm_priority ON queue_messages(priority)")
        
        conn.commit()


_init_queues_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Priority Weights
# ---------------------------------------------------------------------------

PRIORITY_ORDER = {
    QueuePriority.CRITICAL: 0,
    QueuePriority.HIGH: 1,
    QueuePriority.NORMAL: 2,
    QueuePriority.LOW: 3,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def create_queue(
    queue_name: str,
    max_retries: int = 3,
    visibility_timeout_seconds: int = 30,
    dead_letter_queue: str | None = None,
) -> QueueConfig:
    """
    Protocol Coda: create a new queue.
    """
    now = datetime.now(timezone.utc)
    
    config = QueueConfig(
        queue_name=queue_name,
        max_retries=max_retries,
        visibility_timeout_seconds=visibility_timeout_seconds,
        dead_letter_queue=dead_letter_queue,
    )
    
    with _db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO queue_configs (
                queue_name, max_retries, visibility_timeout, dead_letter_queue, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                queue_name,
                max_retries,
                visibility_timeout_seconds,
                dead_letter_queue,
                now.isoformat(),
            )
        )
        conn.commit()
    
    return config


async def enqueue(
    queue_name: str,
    payload: dict[str, Any],
    priority: QueuePriority = QueuePriority.NORMAL,
    delay_seconds: int = 0,
) -> QueueMessage:
    """
    Protocol Coda: add a message to the queue.
    """
    message_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    visible_at = now + timedelta(seconds=delay_seconds) if delay_seconds > 0 else now
    
    message = QueueMessage(
        message_id=message_id,
        queue_name=queue_name,
        payload=payload,
        priority=priority,
        status=MessageStatus.PENDING,
        created_at=now,
        visible_at=visible_at,
    )
    
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO queue_messages (
                message_id, queue_name, payload, priority, status, created_at, visible_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                queue_name,
                json.dumps(payload),
                priority.value,
                MessageStatus.PENDING.value,
                now.isoformat(),
                visible_at.isoformat(),
            )
        )
        conn.commit()
    
    return message


async def dequeue(
    queue_name: str,
    visibility_timeout_seconds: int | None = None,
    count: int = 1,
) -> list[QueueMessage]:
    """
    Protocol Coda: retrieve messages from the queue for processing.
    """
    now = datetime.now(timezone.utc)
    timeout = visibility_timeout_seconds or 30
    
    messages: list[QueueMessage] = []
    
    with _db() as conn:
        # Get queue config
        config_row = conn.execute(
            "SELECT * FROM queue_configs WHERE queue_name = ?",
            (queue_name,)
        ).fetchone()
        
        if config_row:
            timeout = visibility_timeout_seconds or config_row["visibility_timeout"]
        
        # Select messages ordered by priority then created_at
        rows = conn.execute(
            """
            SELECT * FROM queue_messages 
            WHERE queue_name = ? 
                AND status = 'pending' 
                AND (visible_at IS NULL OR visible_at <= ?)
            ORDER BY 
                CASE priority 
                    WHEN 'critical' THEN 0 
                    WHEN 'high' THEN 1 
                    WHEN 'normal' THEN 2 
                    WHEN 'low' THEN 3 
                END,
                created_at
            LIMIT ?
            """,
            (queue_name, now.isoformat(), count)
        ).fetchall()
        
        for row in rows:
            receipt_handle = str(uuid.uuid4())
            new_visible_at = now + timedelta(seconds=timeout)
            
            # Update status and set visibility timeout
            conn.execute(
                """
                UPDATE queue_messages 
                SET status = 'processing', receipt_handle = ?, visible_at = ?
                WHERE message_id = ?
                """,
                (receipt_handle, new_visible_at.isoformat(), row["message_id"])
            )
            
            messages.append(QueueMessage(
                message_id=row["message_id"],
                queue_name=row["queue_name"],
                payload=json.loads(row["payload"]),
                priority=QueuePriority(row["priority"]),
                status=MessageStatus.PROCESSING,
                retry_count=row["retry_count"],
                created_at=datetime.fromisoformat(row["created_at"]),
                visible_at=new_visible_at,
                receipt_handle=receipt_handle,
            ))
        
        conn.commit()
    
    return messages


async def complete(
    queue_name: str,
    receipt_handle: str,
) -> bool:
    """Mark a message as completed."""
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        cursor = conn.execute(
            """
            UPDATE queue_messages 
            SET status = 'completed', processed_at = ?
            WHERE queue_name = ? AND receipt_handle = ? AND status = 'processing'
            """,
            (now.isoformat(), queue_name, receipt_handle)
        )
        conn.commit()
        return cursor.rowcount > 0


async def fail(
    queue_name: str,
    receipt_handle: str,
    error: str | None = None,
) -> bool:
    """Mark a message as failed and potentially retry."""
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        # Get message and config
        row = conn.execute(
            "SELECT * FROM queue_messages WHERE queue_name = ? AND receipt_handle = ?",
            (queue_name, receipt_handle)
        ).fetchone()
        
        if not row:
            return False
        
        config_row = conn.execute(
            "SELECT * FROM queue_configs WHERE queue_name = ?",
            (queue_name,)
        ).fetchone()
        
        max_retries = config_row["max_retries"] if config_row else 3
        retry_count = row["retry_count"] + 1
        
        if retry_count >= max_retries:
            # Move to dead letter or mark as failed
            dlq = config_row["dead_letter_queue"] if config_row else None
            
            if dlq:
                # Move to dead letter queue
                conn.execute(
                    "UPDATE queue_messages SET queue_name = ?, status = 'dead_letter', error = ? WHERE message_id = ?",
                    (dlq, error, row["message_id"])
                )
            else:
                conn.execute(
                    "UPDATE queue_messages SET status = 'failed', error = ? WHERE message_id = ?",
                    (error, row["message_id"])
                )
        else:
            # Retry with exponential backoff
            delay = 2 ** retry_count * 10  # 20s, 40s, 80s, etc.
            new_visible_at = now + timedelta(seconds=delay)
            
            conn.execute(
                """
                UPDATE queue_messages 
                SET status = 'pending', retry_count = ?, visible_at = ?, error = ?, receipt_handle = NULL
                WHERE message_id = ?
                """,
                (retry_count, new_visible_at.isoformat(), error, row["message_id"])
            )
        
        conn.commit()
        return True


async def peek(
    queue_name: str,
    count: int = 10,
) -> list[QueueMessage]:
    """
    Protocol Coda: peek at messages without removing them.
    """
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM queue_messages 
            WHERE queue_name = ? AND status = 'pending'
            ORDER BY 
                CASE priority 
                    WHEN 'critical' THEN 0 
                    WHEN 'high' THEN 1 
                    WHEN 'normal' THEN 2 
                    WHEN 'low' THEN 3 
                END,
                created_at
            LIMIT ?
            """,
            (queue_name, count)
        ).fetchall()
        
        return [
            QueueMessage(
                message_id=row["message_id"],
                queue_name=row["queue_name"],
                payload=json.loads(row["payload"]),
                priority=QueuePriority(row["priority"]),
                status=MessageStatus(row["status"]),
                retry_count=row["retry_count"],
                created_at=datetime.fromisoformat(row["created_at"]),
                visible_at=datetime.fromisoformat(row["visible_at"]) if row["visible_at"] else None,
            )
            for row in rows
        ]


async def get_queue_stats(queue_name: str) -> QueueStats:
    """Get statistics for a queue."""
    with _db() as conn:
        # Count by status
        counts = {}
        for status in MessageStatus:
            row = conn.execute(
                "SELECT COUNT(*) as count FROM queue_messages WHERE queue_name = ? AND status = ?",
                (queue_name, status.value)
            ).fetchone()
            counts[status.value] = row["count"]
        
        return QueueStats(
            queue_name=queue_name,
            pending_count=counts.get("pending", 0),
            processing_count=counts.get("processing", 0),
            completed_count=counts.get("completed", 0),
            failed_count=counts.get("failed", 0),
            dead_letter_count=counts.get("dead_letter", 0),
        )


async def purge_queue(queue_name: str) -> int:
    """Remove all messages from a queue."""
    with _db() as conn:
        cursor = conn.execute(
            "DELETE FROM queue_messages WHERE queue_name = ?",
            (queue_name,)
        )
        conn.commit()
        return cursor.rowcount
