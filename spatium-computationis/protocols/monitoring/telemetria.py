"""
Protocol: Telemetria  📡
Meaning: Emit and collect telemetry data.

Handles:
- System telemetry emission
- Event collection
- Diagnostic data
- Performance analytics
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


class TelemetryLevel(str, Enum):
    """Telemetry verbosity levels."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    DETAILED = "detailed"
    DEBUG = "debug"


class TelemetryCategory(str, Enum):
    """Categories of telemetry events."""
    PERFORMANCE = "performance"
    ERROR = "error"
    USAGE = "usage"
    SECURITY = "security"
    DIAGNOSTIC = "diagnostic"
    CUSTOM = "custom"


class TelemetryConfig(BaseModel):
    """Configuration for telemetry collection."""
    enabled: bool = True
    level: TelemetryLevel = TelemetryLevel.STANDARD
    
    # Categories to collect
    categories: list[TelemetryCategory] = Field(
        default_factory=lambda: list(TelemetryCategory)
    )
    
    # Sampling
    sample_rate: float = 1.0  # 1.0 = 100%
    
    # Retention
    retention_days: int = 30
    
    # Export
    export_enabled: bool = False
    export_endpoint: str | None = None
    export_interval_seconds: int = 60


class TelemetryEvent(BaseModel):
    """A single telemetry event."""
    event_id: str
    category: TelemetryCategory
    event_name: str
    
    # Data
    properties: dict[str, Any] = Field(default_factory=dict)
    measurements: dict[str, float] = Field(default_factory=dict)
    
    # Context
    session_id: str | None = None
    user_id: str | None = None
    trace_id: str | None = None
    
    # Environment
    environment: str = "production"
    version: str = "1.0.0"
    
    # Timing
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float | None = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "telemetry.db"


def _init_telemetry_db() -> None:
    """Initialize the telemetry database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Telemetry events
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry_events (
                event_id        TEXT PRIMARY KEY,
                category        TEXT NOT NULL,
                event_name      TEXT NOT NULL,
                properties      TEXT DEFAULT '{}',
                measurements    TEXT DEFAULT '{}',
                session_id      TEXT,
                user_id         TEXT,
                trace_id        TEXT,
                environment     TEXT DEFAULT 'production',
                version         TEXT DEFAULT '1.0.0',
                timestamp       TEXT NOT NULL,
                duration_ms     REAL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_te_category ON telemetry_events(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_te_name ON telemetry_events(event_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_te_time ON telemetry_events(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_te_session ON telemetry_events(session_id)")
        
        # Aggregated telemetry
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry_aggregates (
                aggregate_id    TEXT PRIMARY KEY,
                event_name      TEXT NOT NULL,
                period_start    TEXT NOT NULL,
                period_end      TEXT NOT NULL,
                count           INTEGER DEFAULT 0,
                avg_duration    REAL,
                min_duration    REAL,
                max_duration    REAL,
                measurements    TEXT DEFAULT '{}'
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ta_name ON telemetry_aggregates(event_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ta_period ON telemetry_aggregates(period_start)")
        
        conn.commit()


_init_telemetry_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Global Configuration
# ---------------------------------------------------------------------------

_config = TelemetryConfig()


def configure_telemetry(config: TelemetryConfig) -> None:
    """Set the global telemetry configuration."""
    global _config
    _config = config


def get_telemetry_config() -> TelemetryConfig:
    """Get the current telemetry configuration."""
    return _config


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def emit_telemetry(
    event_name: str,
    category: TelemetryCategory = TelemetryCategory.USAGE,
    properties: dict[str, Any] | None = None,
    measurements: dict[str, float] | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    trace_id: str | None = None,
    duration_ms: float | None = None,
) -> TelemetryEvent | None:
    """
    Protocol Telemetria: emit a telemetry event.
    """
    # Check if telemetry is enabled
    if not _config.enabled:
        return None
    
    # Check category filter
    if category not in _config.categories:
        return None
    
    # Apply sampling
    import random
    if random.random() > _config.sample_rate:
        return None
    
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    event = TelemetryEvent(
        event_id=event_id,
        category=category,
        event_name=event_name,
        properties=properties or {},
        measurements=measurements or {},
        session_id=session_id,
        user_id=user_id,
        trace_id=trace_id,
        timestamp=now,
        duration_ms=duration_ms,
    )
    
    # Store event
    _store_event(event)
    
    return event


async def emit_performance(
    operation: str,
    duration_ms: float,
    success: bool = True,
    properties: dict[str, Any] | None = None,
) -> TelemetryEvent | None:
    """Emit a performance telemetry event."""
    props = properties or {}
    props["success"] = success
    
    measurements = {"duration_ms": duration_ms}
    
    return await emit_telemetry(
        event_name=f"performance.{operation}",
        category=TelemetryCategory.PERFORMANCE,
        properties=props,
        measurements=measurements,
        duration_ms=duration_ms,
    )


async def emit_error(
    error_type: str,
    error_message: str,
    stack_trace: str | None = None,
    properties: dict[str, Any] | None = None,
) -> TelemetryEvent | None:
    """Emit an error telemetry event."""
    props = properties or {}
    props["error_type"] = error_type
    props["error_message"] = error_message
    if stack_trace:
        props["stack_trace"] = stack_trace
    
    return await emit_telemetry(
        event_name=f"error.{error_type}",
        category=TelemetryCategory.ERROR,
        properties=props,
    )


async def emit_usage(
    feature: str,
    action: str,
    properties: dict[str, Any] | None = None,
) -> TelemetryEvent | None:
    """Emit a usage telemetry event."""
    return await emit_telemetry(
        event_name=f"usage.{feature}.{action}",
        category=TelemetryCategory.USAGE,
        properties=properties,
    )


async def emit_security(
    event_type: str,
    properties: dict[str, Any] | None = None,
) -> TelemetryEvent | None:
    """Emit a security telemetry event."""
    return await emit_telemetry(
        event_name=f"security.{event_type}",
        category=TelemetryCategory.SECURITY,
        properties=properties,
    )


def _store_event(event: TelemetryEvent) -> None:
    """Store a telemetry event."""
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO telemetry_events (
                event_id, category, event_name, properties, measurements,
                session_id, user_id, trace_id, environment, version,
                timestamp, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.category.value,
                event.event_name,
                json.dumps(event.properties),
                json.dumps(event.measurements),
                event.session_id,
                event.user_id,
                event.trace_id,
                event.environment,
                event.version,
                event.timestamp.isoformat(),
                event.duration_ms,
            )
        )
        conn.commit()


async def get_telemetry(
    event_name: str | None = None,
    category: TelemetryCategory | None = None,
    hours: int = 24,
    limit: int = 1000,
) -> list[TelemetryEvent]:
    """
    Protocol Telemetria: retrieve telemetry events.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    with _db() as conn:
        query = "SELECT * FROM telemetry_events WHERE timestamp >= ?"
        params: list[Any] = [cutoff.isoformat()]
        
        if event_name:
            query += " AND event_name LIKE ?"
            params.append(f"%{event_name}%")
        
        if category:
            query += " AND category = ?"
            params.append(category.value)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        
        return [
            TelemetryEvent(
                event_id=row["event_id"],
                category=TelemetryCategory(row["category"]),
                event_name=row["event_name"],
                properties=json.loads(row["properties"]) if row["properties"] else {},
                measurements=json.loads(row["measurements"]) if row["measurements"] else {},
                session_id=row["session_id"],
                user_id=row["user_id"],
                trace_id=row["trace_id"],
                environment=row["environment"],
                version=row["version"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                duration_ms=row["duration_ms"],
            )
            for row in rows
        ]


async def get_telemetry_summary(
    event_name: str,
    hours: int = 24,
) -> dict[str, Any]:
    """Get summary statistics for a telemetry event."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    with _db() as conn:
        row = conn.execute(
            """
            SELECT 
                COUNT(*) as count,
                AVG(duration_ms) as avg_duration,
                MIN(duration_ms) as min_duration,
                MAX(duration_ms) as max_duration
            FROM telemetry_events 
            WHERE event_name LIKE ? AND timestamp >= ?
            """,
            (f"%{event_name}%", cutoff.isoformat())
        ).fetchone()
        
        return {
            "event_name": event_name,
            "period_hours": hours,
            "count": row["count"],
            "avg_duration_ms": row["avg_duration"],
            "min_duration_ms": row["min_duration"],
            "max_duration_ms": row["max_duration"],
        }


async def cleanup_old_telemetry() -> int:
    """Clean up old telemetry data based on retention policy."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=_config.retention_days)
    
    with _db() as conn:
        cursor = conn.execute(
            "DELETE FROM telemetry_events WHERE timestamp < ?",
            (cutoff.isoformat(),)
        )
        conn.commit()
        return cursor.rowcount
