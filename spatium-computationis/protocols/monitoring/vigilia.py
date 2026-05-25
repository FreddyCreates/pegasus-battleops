"""
Protocol: Vigilia  🔔
Meaning: Monitor and alert on system conditions.

Handles:
- Alert rule definition
- Threshold monitoring
- Alert creation and resolution
- Notification dispatch
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertRule(BaseModel):
    """Definition of an alert rule."""
    rule_id: str
    name: str
    description: str
    
    # Condition
    metric_name: str
    condition: str  # e.g., "> 90", "== 0", "< 10"
    threshold: float
    
    # Timing
    duration_seconds: int = 60  # Condition must persist for this long
    evaluation_interval_seconds: int = 30
    
    # Alert settings
    severity: AlertSeverity = AlertSeverity.MEDIUM
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    
    # Status
    enabled: bool = True
    last_evaluated: datetime | None = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Alert(BaseModel):
    """An active or historical alert."""
    alert_id: str
    rule_id: str
    rule_name: str
    
    # Status
    status: AlertStatus = AlertStatus.ACTIVE
    severity: AlertSeverity
    
    # Details
    message: str
    value: float | None = None
    threshold: float | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    
    # Timing
    fired_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    
    # Resolution
    resolved_by: str | None = None
    resolution_notes: str | None = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "alerts.db"


def _init_alerts_db() -> None:
    """Initialize the alerts database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Alert rules
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_rules (
                rule_id         TEXT PRIMARY KEY,
                name            TEXT UNIQUE NOT NULL,
                description     TEXT,
                metric_name     TEXT NOT NULL,
                condition       TEXT NOT NULL,
                threshold       REAL NOT NULL,
                duration_secs   INTEGER DEFAULT 60,
                eval_interval   INTEGER DEFAULT 30,
                severity        TEXT DEFAULT 'medium',
                labels          TEXT DEFAULT '{}',
                annotations     TEXT DEFAULT '{}',
                enabled         INTEGER DEFAULT 1,
                last_evaluated  TEXT,
                created_at      TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ar_name ON alert_rules(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ar_metric ON alert_rules(metric_name)")
        
        # Alerts
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id        TEXT PRIMARY KEY,
                rule_id         TEXT NOT NULL,
                rule_name       TEXT NOT NULL,
                status          TEXT DEFAULT 'active',
                severity        TEXT NOT NULL,
                message         TEXT NOT NULL,
                value           REAL,
                threshold       REAL,
                labels          TEXT DEFAULT '{}',
                annotations     TEXT DEFAULT '{}',
                fired_at        TEXT NOT NULL,
                acknowledged_at TEXT,
                resolved_at     TEXT,
                resolved_by     TEXT,
                resolution_notes TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_al_status ON alerts(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_al_severity ON alerts(severity)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_al_rule ON alerts(rule_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_al_fired ON alerts(fired_at)")
        
        # Notification history
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                alert_id        TEXT NOT NULL,
                channel         TEXT NOT NULL,
                status          TEXT DEFAULT 'sent',
                sent_at         TEXT NOT NULL,
                error           TEXT
            )
            """
        )
        
        conn.commit()


_init_alerts_db()


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

_notification_handlers: dict[str, Callable[[Alert], None]] = {}


def register_notification_handler(channel: str, handler: Callable[[Alert], None]) -> None:
    """Register a notification handler for a channel."""
    _notification_handlers[channel] = handler


# Default console handler
def _console_handler(alert: Alert) -> None:
    """Default console notification handler."""
    print(f"[ALERT] [{alert.severity.value.upper()}] {alert.rule_name}: {alert.message}")


register_notification_handler("console", _console_handler)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def create_alert_rule(
    name: str,
    metric_name: str,
    condition: str,
    threshold: float,
    description: str = "",
    severity: AlertSeverity = AlertSeverity.MEDIUM,
    duration_seconds: int = 60,
    labels: dict[str, str] | None = None,
    annotations: dict[str, str] | None = None,
) -> AlertRule:
    """
    Protocol Vigilia: create an alert rule.
    """
    rule_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    rule = AlertRule(
        rule_id=rule_id,
        name=name,
        description=description,
        metric_name=metric_name,
        condition=condition,
        threshold=threshold,
        duration_seconds=duration_seconds,
        severity=severity,
        labels=labels or {},
        annotations=annotations or {},
        created_at=now,
    )
    
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO alert_rules (
                rule_id, name, description, metric_name, condition, threshold,
                duration_secs, severity, labels, annotations, enabled, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                rule_id,
                name,
                description,
                metric_name,
                condition,
                threshold,
                duration_seconds,
                severity.value,
                json.dumps(labels or {}),
                json.dumps(annotations or {}),
                now.isoformat(),
            )
        )
        conn.commit()
    
    return rule


async def create_alert(
    rule_id: str,
    message: str,
    value: float | None = None,
    labels: dict[str, str] | None = None,
    annotations: dict[str, str] | None = None,
    notify: bool = True,
) -> Alert:
    """
    Protocol Vigilia: create and fire an alert.
    """
    alert_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Get rule details
    with _db() as conn:
        rule_row = conn.execute(
            "SELECT * FROM alert_rules WHERE rule_id = ?",
            (rule_id,)
        ).fetchone()
        
        if not rule_row:
            raise ValueError(f"Alert rule not found: {rule_id}")
        
        rule_labels = json.loads(rule_row["labels"]) if rule_row["labels"] else {}
        rule_annotations = json.loads(rule_row["annotations"]) if rule_row["annotations"] else {}
        
        # Merge labels and annotations
        merged_labels = {**rule_labels, **(labels or {})}
        merged_annotations = {**rule_annotations, **(annotations or {})}
        
        alert = Alert(
            alert_id=alert_id,
            rule_id=rule_id,
            rule_name=rule_row["name"],
            status=AlertStatus.ACTIVE,
            severity=AlertSeverity(rule_row["severity"]),
            message=message,
            value=value,
            threshold=rule_row["threshold"],
            labels=merged_labels,
            annotations=merged_annotations,
            fired_at=now,
        )
        
        # Store alert
        conn.execute(
            """
            INSERT INTO alerts (
                alert_id, rule_id, rule_name, status, severity, message,
                value, threshold, labels, annotations, fired_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id,
                rule_id,
                rule_row["name"],
                AlertStatus.ACTIVE.value,
                alert.severity.value,
                message,
                value,
                rule_row["threshold"],
                json.dumps(merged_labels),
                json.dumps(merged_annotations),
                now.isoformat(),
            )
        )
        conn.commit()
    
    # Send notifications
    if notify:
        await _send_notifications(alert)
    
    return alert


async def resolve_alert(
    alert_id: str,
    resolved_by: str | None = None,
    resolution_notes: str | None = None,
) -> Alert | None:
    """
    Protocol Vigilia: resolve an alert.
    """
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM alerts WHERE alert_id = ?",
            (alert_id,)
        ).fetchone()
        
        if not row:
            return None
        
        conn.execute(
            """
            UPDATE alerts 
            SET status = ?, resolved_at = ?, resolved_by = ?, resolution_notes = ?
            WHERE alert_id = ?
            """,
            (
                AlertStatus.RESOLVED.value,
                now.isoformat(),
                resolved_by,
                resolution_notes,
                alert_id,
            )
        )
        conn.commit()
        
        return Alert(
            alert_id=row["alert_id"],
            rule_id=row["rule_id"],
            rule_name=row["rule_name"],
            status=AlertStatus.RESOLVED,
            severity=AlertSeverity(row["severity"]),
            message=row["message"],
            value=row["value"],
            threshold=row["threshold"],
            labels=json.loads(row["labels"]) if row["labels"] else {},
            annotations=json.loads(row["annotations"]) if row["annotations"] else {},
            fired_at=datetime.fromisoformat(row["fired_at"]),
            resolved_at=now,
            resolved_by=resolved_by,
            resolution_notes=resolution_notes,
        )


async def acknowledge_alert(
    alert_id: str,
    acknowledged_by: str | None = None,
) -> bool:
    """Acknowledge an alert."""
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        cursor = conn.execute(
            """
            UPDATE alerts 
            SET status = ?, acknowledged_at = ?
            WHERE alert_id = ? AND status = ?
            """,
            (
                AlertStatus.ACKNOWLEDGED.value,
                now.isoformat(),
                alert_id,
                AlertStatus.ACTIVE.value,
            )
        )
        conn.commit()
        return cursor.rowcount > 0


async def check_alert_rules(
    metrics: dict[str, float],
) -> list[Alert]:
    """
    Protocol Vigilia: check all alert rules against current metrics.
    """
    alerts: list[Alert] = []
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        rules = conn.execute(
            "SELECT * FROM alert_rules WHERE enabled = 1"
        ).fetchall()
        
        for rule_row in rules:
            metric_name = rule_row["metric_name"]
            
            if metric_name not in metrics:
                continue
            
            value = metrics[metric_name]
            threshold = rule_row["threshold"]
            condition = rule_row["condition"]
            
            # Evaluate condition
            triggered = _evaluate_condition(value, condition, threshold)
            
            if triggered:
                # Check if alert already exists
                existing = conn.execute(
                    """
                    SELECT alert_id FROM alerts 
                    WHERE rule_id = ? AND status IN ('active', 'acknowledged')
                    """,
                    (rule_row["rule_id"],)
                ).fetchone()
                
                if not existing:
                    # Create new alert
                    alert = await create_alert(
                        rule_id=rule_row["rule_id"],
                        message=f"{metric_name} {condition} {threshold} (current: {value})",
                        value=value,
                    )
                    alerts.append(alert)
            
            # Update last evaluated
            conn.execute(
                "UPDATE alert_rules SET last_evaluated = ? WHERE rule_id = ?",
                (now.isoformat(), rule_row["rule_id"])
            )
        
        conn.commit()
    
    return alerts


def _evaluate_condition(value: float, condition: str, threshold: float) -> bool:
    """Evaluate an alert condition."""
    condition = condition.strip()
    
    if condition.startswith(">="):
        return value >= threshold
    elif condition.startswith("<="):
        return value <= threshold
    elif condition.startswith(">"):
        return value > threshold
    elif condition.startswith("<"):
        return value < threshold
    elif condition.startswith("==") or condition.startswith("="):
        return abs(value - threshold) < 0.0001
    elif condition.startswith("!="):
        return abs(value - threshold) >= 0.0001
    
    return False


async def _send_notifications(alert: Alert) -> None:
    """Send notifications for an alert."""
    for channel, handler in _notification_handlers.items():
        try:
            handler(alert)
            _log_notification(alert.alert_id, channel, "sent")
        except Exception as e:
            _log_notification(alert.alert_id, channel, "failed", str(e))


def _log_notification(
    alert_id: str,
    channel: str,
    status: str,
    error: str | None = None,
) -> None:
    """Log a notification attempt."""
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO notifications (notification_id, alert_id, channel, status, sent_at, error)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                alert_id,
                channel,
                status,
                datetime.now(timezone.utc).isoformat(),
                error,
            )
        )
        conn.commit()


async def get_active_alerts(
    severity: AlertSeverity | None = None,
    limit: int = 100,
) -> list[Alert]:
    """Get all active alerts."""
    with _db() as conn:
        if severity:
            rows = conn.execute(
                """
                SELECT * FROM alerts 
                WHERE status IN ('active', 'acknowledged') AND severity = ?
                ORDER BY fired_at DESC LIMIT ?
                """,
                (severity.value, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM alerts 
                WHERE status IN ('active', 'acknowledged')
                ORDER BY fired_at DESC LIMIT ?
                """,
                (limit,)
            ).fetchall()
        
        return [
            Alert(
                alert_id=row["alert_id"],
                rule_id=row["rule_id"],
                rule_name=row["rule_name"],
                status=AlertStatus(row["status"]),
                severity=AlertSeverity(row["severity"]),
                message=row["message"],
                value=row["value"],
                threshold=row["threshold"],
                labels=json.loads(row["labels"]) if row["labels"] else {},
                annotations=json.loads(row["annotations"]) if row["annotations"] else {},
                fired_at=datetime.fromisoformat(row["fired_at"]),
                acknowledged_at=datetime.fromisoformat(row["acknowledged_at"]) if row["acknowledged_at"] else None,
            )
            for row in rows
        ]
