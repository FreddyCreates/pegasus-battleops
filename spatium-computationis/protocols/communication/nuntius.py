"""
Protocol: Nuntius  📬
Meaning: Notifications and messaging.

Handles:
- Multi-channel notifications
- Notification templates
- Delivery tracking
- User preferences
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


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    SLACK = "slack"
    WEBHOOK = "webhook"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """Notification status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Notification(BaseModel):
    """A notification message."""
    notification_id: str
    channel: NotificationChannel
    recipient: str
    
    # Content
    title: str
    body: str
    data: dict[str, Any] = Field(default_factory=dict)
    
    # Options
    priority: NotificationPriority = NotificationPriority.NORMAL
    
    # Status
    status: NotificationStatus = NotificationStatus.PENDING
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    read_at: datetime | None = None
    
    # Error handling
    error: str | None = None
    retry_count: int = 0


class NotificationTemplate(BaseModel):
    """A notification template."""
    template_id: str
    name: str
    channel: NotificationChannel
    title_template: str
    body_template: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "notifications.db"


def _init_notifications_db() -> None:
    """Initialize the notifications database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Notifications
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                channel         TEXT NOT NULL,
                recipient       TEXT NOT NULL,
                title           TEXT NOT NULL,
                body            TEXT NOT NULL,
                data            TEXT DEFAULT '{}',
                priority        TEXT DEFAULT 'normal',
                status          TEXT DEFAULT 'pending',
                created_at      TEXT NOT NULL,
                sent_at         TEXT,
                delivered_at    TEXT,
                read_at         TEXT,
                error           TEXT,
                retry_count     INTEGER DEFAULT 0
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notif_recipient ON notifications(recipient)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notif_status ON notifications(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notif_channel ON notifications(channel)")
        
        # Templates
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_templates (
                template_id     TEXT PRIMARY KEY,
                name            TEXT UNIQUE NOT NULL,
                channel         TEXT NOT NULL,
                title_template  TEXT NOT NULL,
                body_template   TEXT NOT NULL,
                created_at      TEXT NOT NULL
            )
            """
        )
        
        # User preferences
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_preferences (
                user_id         TEXT NOT NULL,
                channel         TEXT NOT NULL,
                enabled         INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, channel)
            )
            """
        )
        
        conn.commit()


_init_notifications_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Notification Handlers
# ---------------------------------------------------------------------------

_channel_handlers: dict[NotificationChannel, Any] = {}


def register_channel_handler(channel: NotificationChannel, handler: Any) -> None:
    """Register a handler for a notification channel."""
    _channel_handlers[channel] = handler


# Default in-app handler (just stores in DB)
async def _in_app_handler(notification: Notification) -> bool:
    """Default handler for in-app notifications."""
    return True  # Just stored in DB


register_channel_handler(NotificationChannel.IN_APP, _in_app_handler)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def send_notification(
    channel: NotificationChannel,
    recipient: str,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
    priority: NotificationPriority = NotificationPriority.NORMAL,
) -> Notification:
    """
    Protocol Nuntius: send a notification.
    """
    notification_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    notification = Notification(
        notification_id=notification_id,
        channel=channel,
        recipient=recipient,
        title=title,
        body=body,
        data=data or {},
        priority=priority,
        status=NotificationStatus.PENDING,
        created_at=now,
    )
    
    # Store notification
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO notifications (
                notification_id, channel, recipient, title, body, data,
                priority, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                notification_id,
                channel.value,
                recipient,
                title,
                body,
                json.dumps(data or {}),
                priority.value,
                NotificationStatus.PENDING.value,
                now.isoformat(),
            )
        )
        conn.commit()
    
    # Attempt delivery
    if channel in _channel_handlers:
        try:
            success = await _channel_handlers[channel](notification)
            if success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.now(timezone.utc)
            else:
                notification.status = NotificationStatus.FAILED
        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.error = str(e)
    else:
        # No handler, mark as sent for in-app
        if channel == NotificationChannel.IN_APP:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)
    
    # Update status
    with _db() as conn:
        conn.execute(
            """
            UPDATE notifications 
            SET status = ?, sent_at = ?, error = ?
            WHERE notification_id = ?
            """,
            (
                notification.status.value,
                notification.sent_at.isoformat() if notification.sent_at else None,
                notification.error,
                notification_id,
            )
        )
        conn.commit()
    
    return notification


async def send_notification_from_template(
    template_name: str,
    recipient: str,
    variables: dict[str, Any],
    priority: NotificationPriority = NotificationPriority.NORMAL,
) -> Notification | None:
    """Send a notification using a template."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM notification_templates WHERE name = ?",
            (template_name,)
        ).fetchone()
        
        if not row:
            return None
        
        # Render template
        title = row["title_template"]
        body = row["body_template"]
        
        for key, value in variables.items():
            title = title.replace(f"{{{{{key}}}}}", str(value))
            body = body.replace(f"{{{{{key}}}}}", str(value))
        
        return await send_notification(
            channel=NotificationChannel(row["channel"]),
            recipient=recipient,
            title=title,
            body=body,
            data=variables,
            priority=priority,
        )


async def get_notifications(
    recipient: str,
    channel: NotificationChannel | None = None,
    status: NotificationStatus | None = None,
    limit: int = 50,
) -> list[Notification]:
    """
    Protocol Nuntius: get notifications for a recipient.
    """
    with _db() as conn:
        query = "SELECT * FROM notifications WHERE recipient = ?"
        params: list[Any] = [recipient]
        
        if channel:
            query += " AND channel = ?"
            params.append(channel.value)
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        
        return [
            Notification(
                notification_id=row["notification_id"],
                channel=NotificationChannel(row["channel"]),
                recipient=row["recipient"],
                title=row["title"],
                body=row["body"],
                data=json.loads(row["data"]) if row["data"] else {},
                priority=NotificationPriority(row["priority"]),
                status=NotificationStatus(row["status"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                sent_at=datetime.fromisoformat(row["sent_at"]) if row["sent_at"] else None,
                delivered_at=datetime.fromisoformat(row["delivered_at"]) if row["delivered_at"] else None,
                read_at=datetime.fromisoformat(row["read_at"]) if row["read_at"] else None,
                error=row["error"],
                retry_count=row["retry_count"],
            )
            for row in rows
        ]


async def mark_as_read(notification_id: str) -> bool:
    """Mark a notification as read."""
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        cursor = conn.execute(
            "UPDATE notifications SET status = ?, read_at = ? WHERE notification_id = ?",
            (NotificationStatus.READ.value, now.isoformat(), notification_id)
        )
        conn.commit()
        return cursor.rowcount > 0


async def get_unread_count(recipient: str) -> int:
    """Get count of unread notifications."""
    with _db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as count FROM notifications WHERE recipient = ? AND status != 'read'",
            (recipient,)
        ).fetchone()
        return row["count"]
