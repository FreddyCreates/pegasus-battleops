"""
Protocol: Uncus  🪝
Meaning: Webhook management and triggering.

Handles:
- Webhook registration
- Event-triggered callbacks
- Retry logic for failed deliveries
- Signature verification
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class WebhookEvent(str, Enum):
    """Types of webhook events."""
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    ESTIMATE_GENERATED = "estimate.generated"
    DOCUMENT_CREATED = "document.created"
    ALERT_TRIGGERED = "alert.triggered"
    ACTION_COMPLETED = "action.completed"
    CUSTOM = "custom"


class WebhookStatus(str, Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class WebhookConfig(BaseModel):
    """Configuration for a webhook."""
    webhook_id: str
    name: str
    url: str
    events: list[WebhookEvent] = Field(default_factory=list)
    
    # Authentication
    secret: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    
    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: int = 60
    
    # Options
    enabled: bool = True
    verify_ssl: bool = True
    timeout_seconds: int = 30
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WebhookDelivery(BaseModel):
    """Record of a webhook delivery attempt."""
    delivery_id: str
    webhook_id: str
    event: WebhookEvent
    payload: dict[str, Any]
    
    # Status
    status: WebhookStatus = WebhookStatus.PENDING
    attempts: int = 0
    
    # Response
    response_status: int | None = None
    response_body: str | None = None
    error: str | None = None
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: datetime | None = None
    next_retry_at: datetime | None = None


class WebhookResult(BaseModel):
    """Result of triggering a webhook."""
    success: bool
    delivery_id: str | None = None
    webhook_id: str
    event: WebhookEvent
    status: WebhookStatus
    error: str | None = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "webhooks.db"


def _init_webhooks_db() -> None:
    """Initialize the webhooks database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Webhook configurations
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS webhooks (
                webhook_id      TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                url             TEXT NOT NULL,
                events          TEXT DEFAULT '[]',
                secret          TEXT,
                headers         TEXT DEFAULT '{}',
                max_retries     INTEGER DEFAULT 3,
                enabled         INTEGER DEFAULT 1,
                created_at      TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wh_enabled ON webhooks(enabled)")
        
        # Delivery log
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_deliveries (
                delivery_id     TEXT PRIMARY KEY,
                webhook_id      TEXT NOT NULL,
                event           TEXT NOT NULL,
                payload         TEXT NOT NULL,
                status          TEXT DEFAULT 'pending',
                attempts        INTEGER DEFAULT 0,
                response_status INTEGER,
                response_body   TEXT,
                error           TEXT,
                created_at      TEXT NOT NULL,
                delivered_at    TEXT,
                next_retry_at   TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wd_webhook ON webhook_deliveries(webhook_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wd_status ON webhook_deliveries(status)")
        
        conn.commit()


_init_webhooks_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Signature Generation
# ---------------------------------------------------------------------------

def _generate_signature(payload: str, secret: str) -> str:
    """Generate HMAC signature for webhook payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def verify_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify a webhook signature."""
    expected = _generate_signature(payload, secret)
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def register_webhook(
    name: str,
    url: str,
    events: list[WebhookEvent],
    secret: str | None = None,
    headers: dict[str, str] | None = None,
    max_retries: int = 3,
) -> WebhookConfig:
    """
    Protocol Uncus: register a new webhook.
    """
    webhook_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    config = WebhookConfig(
        webhook_id=webhook_id,
        name=name,
        url=url,
        events=events,
        secret=secret,
        headers=headers or {},
        max_retries=max_retries,
        created_at=now,
    )
    
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO webhooks (webhook_id, name, url, events, secret, headers, max_retries, enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                webhook_id,
                name,
                url,
                json.dumps([e.value for e in events]),
                secret,
                json.dumps(headers or {}),
                max_retries,
                now.isoformat(),
            )
        )
        conn.commit()
    
    return config


async def trigger_webhook(
    event: WebhookEvent,
    payload: dict[str, Any],
    webhook_ids: list[str] | None = None,
) -> list[WebhookResult]:
    """
    Protocol Uncus: trigger webhooks for an event.
    """
    results: list[WebhookResult] = []
    
    with _db() as conn:
        # Find matching webhooks
        if webhook_ids:
            placeholders = ",".join("?" * len(webhook_ids))
            rows = conn.execute(
                f"SELECT * FROM webhooks WHERE webhook_id IN ({placeholders}) AND enabled = 1",
                webhook_ids
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM webhooks WHERE enabled = 1"
            ).fetchall()
        
        for row in rows:
            events = json.loads(row["events"]) if row["events"] else []
            
            # Check if webhook is subscribed to this event
            if event.value not in events and WebhookEvent.CUSTOM.value not in events:
                continue
            
            # Create delivery
            result = await _deliver_webhook(
                webhook_id=row["webhook_id"],
                url=row["url"],
                event=event,
                payload=payload,
                secret=row["secret"],
                headers=json.loads(row["headers"]) if row["headers"] else {},
                max_retries=row["max_retries"],
            )
            results.append(result)
    
    return results


async def _deliver_webhook(
    webhook_id: str,
    url: str,
    event: WebhookEvent,
    payload: dict[str, Any],
    secret: str | None,
    headers: dict[str, str],
    max_retries: int,
) -> WebhookResult:
    """Deliver a webhook payload."""
    import urllib.request
    import urllib.error
    
    delivery_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Prepare payload
    payload_str = json.dumps({
        "event": event.value,
        "data": payload,
        "timestamp": now.isoformat(),
        "delivery_id": delivery_id,
    })
    
    # Prepare headers
    request_headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": event.value,
        "X-Webhook-Delivery": delivery_id,
        **headers,
    }
    
    if secret:
        signature = _generate_signature(payload_str, secret)
        request_headers["X-Webhook-Signature"] = signature
    
    # Record delivery attempt
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO webhook_deliveries (delivery_id, webhook_id, event, payload, status, attempts, created_at)
            VALUES (?, ?, ?, ?, 'pending', 1, ?)
            """,
            (delivery_id, webhook_id, event.value, payload_str, now.isoformat())
        )
        conn.commit()
    
    # Attempt delivery
    try:
        req = urllib.request.Request(
            url,
            data=payload_str.encode("utf-8"),
            headers=request_headers,
            method="POST",
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            response_body = response.read().decode("utf-8")[:1000]
            
            with _db() as conn:
                conn.execute(
                    """
                    UPDATE webhook_deliveries 
                    SET status = 'delivered', response_status = ?, response_body = ?, delivered_at = ?
                    WHERE delivery_id = ?
                    """,
                    (response.status, response_body, now.isoformat(), delivery_id)
                )
                conn.commit()
            
            return WebhookResult(
                success=True,
                delivery_id=delivery_id,
                webhook_id=webhook_id,
                event=event,
                status=WebhookStatus.DELIVERED,
            )
            
    except Exception as e:
        error_msg = str(e)
        
        with _db() as conn:
            conn.execute(
                """
                UPDATE webhook_deliveries 
                SET status = 'failed', error = ?, next_retry_at = ?
                WHERE delivery_id = ?
                """,
                (error_msg, (now + timedelta(seconds=60)).isoformat(), delivery_id)
            )
            conn.commit()
        
        return WebhookResult(
            success=False,
            delivery_id=delivery_id,
            webhook_id=webhook_id,
            event=event,
            status=WebhookStatus.FAILED,
            error=error_msg,
        )


async def get_webhook(webhook_id: str) -> WebhookConfig | None:
    """Get a webhook configuration."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM webhooks WHERE webhook_id = ?",
            (webhook_id,)
        ).fetchone()
        
        if not row:
            return None
        
        return WebhookConfig(
            webhook_id=row["webhook_id"],
            name=row["name"],
            url=row["url"],
            events=[WebhookEvent(e) for e in json.loads(row["events"]) if e in [e.value for e in WebhookEvent]],
            secret=row["secret"],
            headers=json.loads(row["headers"]) if row["headers"] else {},
            max_retries=row["max_retries"],
            enabled=bool(row["enabled"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


async def delete_webhook(webhook_id: str) -> bool:
    """Delete a webhook."""
    with _db() as conn:
        cursor = conn.execute(
            "DELETE FROM webhooks WHERE webhook_id = ?",
            (webhook_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
