"""
Protocol: Tractus  🔍
Meaning: Distributed tracing across the system.

Handles:
- Trace context propagation
- Span creation and management
- Trace sampling
- Correlation across services
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager, asynccontextmanager
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class SpanKind(str, Enum):
    """Types of spans."""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(str, Enum):
    """Status of a span."""
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


class TraceContext(BaseModel):
    """Context for trace propagation."""
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    sampled: bool = True
    baggage: dict[str, str] = Field(default_factory=dict)
    
    def to_header(self) -> str:
        """Convert to W3C traceparent format."""
        flags = "01" if self.sampled else "00"
        return f"00-{self.trace_id}-{self.span_id}-{flags}"
    
    @classmethod
    def from_header(cls, header: str) -> "TraceContext | None":
        """Parse from W3C traceparent format."""
        try:
            parts = header.split("-")
            if len(parts) != 4:
                return None
            version, trace_id, span_id, flags = parts
            return cls(
                trace_id=trace_id,
                span_id=span_id,
                sampled=flags == "01",
            )
        except Exception:
            return None


class Span(BaseModel):
    """A single span in a trace."""
    span_id: str
    trace_id: str
    parent_span_id: str | None = None
    operation_name: str
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.UNSET
    
    # Timing
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    duration_ms: float | None = None
    
    # Attributes
    attributes: dict[str, Any] = Field(default_factory=dict)
    
    # Events within the span
    events: list[dict[str, Any]] = Field(default_factory=list)
    
    # Error info
    error_message: str | None = None
    error_type: str | None = None


class TraceResult(BaseModel):
    """Complete trace result."""
    trace_id: str
    spans: list[Span] = Field(default_factory=list)
    root_span: Span | None = None
    
    # Summary
    total_duration_ms: float = 0.0
    span_count: int = 0
    error_count: int = 0
    
    # Metadata
    started_at: datetime | None = None
    ended_at: datetime | None = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "traces.db"


def _init_traces_db() -> None:
    """Initialize the traces database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Traces
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS traces (
                trace_id        TEXT PRIMARY KEY,
                root_span_id    TEXT,
                started_at      TEXT NOT NULL,
                ended_at        TEXT,
                duration_ms     REAL,
                span_count      INTEGER DEFAULT 0,
                error_count     INTEGER DEFAULT 0,
                sampled         INTEGER DEFAULT 1
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tr_started ON traces(started_at)")
        
        # Spans
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS spans (
                span_id         TEXT PRIMARY KEY,
                trace_id        TEXT NOT NULL,
                parent_span_id  TEXT,
                operation_name  TEXT NOT NULL,
                kind            TEXT DEFAULT 'internal',
                status          TEXT DEFAULT 'unset',
                start_time      TEXT NOT NULL,
                end_time        TEXT,
                duration_ms     REAL,
                attributes      TEXT DEFAULT '{}',
                events          TEXT DEFAULT '[]',
                error_message   TEXT,
                error_type      TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sp_trace ON spans(trace_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sp_parent ON spans(parent_span_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sp_operation ON spans(operation_name)")
        
        conn.commit()


_init_traces_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Active Trace Context
# ---------------------------------------------------------------------------

_active_contexts: dict[str, TraceContext] = {}


def _generate_id(length: int = 16) -> str:
    """Generate a random hex ID."""
    return uuid.uuid4().hex[:length * 2]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def start_trace(
    operation_name: str,
    parent_context: TraceContext | None = None,
    kind: SpanKind = SpanKind.SERVER,
    attributes: dict[str, Any] | None = None,
    sampled: bool = True,
) -> TraceContext:
    """
    Protocol Tractus: start a new trace or continue an existing one.
    """
    now = datetime.now(timezone.utc)
    
    if parent_context:
        # Continue existing trace
        trace_id = parent_context.trace_id
        parent_span_id = parent_context.span_id
    else:
        # Start new trace
        trace_id = _generate_id(16)
        parent_span_id = None
    
    span_id = _generate_id(8)
    
    # Create span
    span = Span(
        span_id=span_id,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        operation_name=operation_name,
        kind=kind,
        start_time=now,
        attributes=attributes or {},
    )
    
    # Store span
    _store_span(span)
    
    # Create and store context
    context = TraceContext(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        sampled=sampled,
    )
    
    _active_contexts[span_id] = context
    
    # Create trace record if new trace
    if not parent_context:
        with _db() as conn:
            conn.execute(
                """
                INSERT INTO traces (trace_id, root_span_id, started_at, sampled)
                VALUES (?, ?, ?, ?)
                """,
                (trace_id, span_id, now.isoformat(), 1 if sampled else 0)
            )
            conn.commit()
    
    return context


async def end_trace(
    context: TraceContext,
    status: SpanStatus = SpanStatus.OK,
    error_message: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Span | None:
    """
    Protocol Tractus: end a trace span.
    """
    now = datetime.now(timezone.utc)
    
    # Get and update the span
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM spans WHERE span_id = ?",
            (context.span_id,)
        ).fetchone()
        
        if not row:
            return None
        
        start_time = datetime.fromisoformat(row["start_time"])
        duration_ms = (now - start_time).total_seconds() * 1000
        
        # Merge attributes
        existing_attrs = json.loads(row["attributes"]) if row["attributes"] else {}
        if attributes:
            existing_attrs.update(attributes)
        
        # Update span
        conn.execute(
            """
            UPDATE spans 
            SET end_time = ?, duration_ms = ?, status = ?, 
                error_message = ?, attributes = ?
            WHERE span_id = ?
            """,
            (
                now.isoformat(),
                duration_ms,
                status.value,
                error_message,
                json.dumps(existing_attrs),
                context.span_id,
            )
        )
        
        # Update trace if this is root span
        if not context.parent_span_id:
            # Count spans and errors
            span_count = conn.execute(
                "SELECT COUNT(*) as count FROM spans WHERE trace_id = ?",
                (context.trace_id,)
            ).fetchone()["count"]
            
            error_count = conn.execute(
                "SELECT COUNT(*) as count FROM spans WHERE trace_id = ? AND status = 'error'",
                (context.trace_id,)
            ).fetchone()["count"]
            
            conn.execute(
                """
                UPDATE traces 
                SET ended_at = ?, duration_ms = ?, span_count = ?, error_count = ?
                WHERE trace_id = ?
                """,
                (now.isoformat(), duration_ms, span_count, error_count, context.trace_id)
            )
        
        conn.commit()
    
    # Remove from active contexts
    _active_contexts.pop(context.span_id, None)
    
    return Span(
        span_id=context.span_id,
        trace_id=context.trace_id,
        parent_span_id=context.parent_span_id,
        operation_name=row["operation_name"],
        kind=SpanKind(row["kind"]),
        status=status,
        start_time=start_time,
        end_time=now,
        duration_ms=duration_ms,
        attributes=existing_attrs,
        error_message=error_message,
    )


async def add_span(
    context: TraceContext,
    operation_name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict[str, Any] | None = None,
) -> TraceContext:
    """
    Protocol Tractus: add a child span to an existing trace.
    """
    return await start_trace(
        operation_name=operation_name,
        parent_context=context,
        kind=kind,
        attributes=attributes,
        sampled=context.sampled,
    )


async def add_event(
    context: TraceContext,
    name: str,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Add an event to the current span."""
    now = datetime.now(timezone.utc)
    event = {
        "name": name,
        "timestamp": now.isoformat(),
        "attributes": attributes or {},
    }
    
    with _db() as conn:
        row = conn.execute(
            "SELECT events FROM spans WHERE span_id = ?",
            (context.span_id,)
        ).fetchone()
        
        if row:
            events = json.loads(row["events"]) if row["events"] else []
            events.append(event)
            
            conn.execute(
                "UPDATE spans SET events = ? WHERE span_id = ?",
                (json.dumps(events), context.span_id)
            )
            conn.commit()


@asynccontextmanager
async def trace_span(
    operation_name: str,
    parent_context: TraceContext | None = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict[str, Any] | None = None,
):
    """Context manager for tracing a span."""
    context = await start_trace(
        operation_name=operation_name,
        parent_context=parent_context,
        kind=kind,
        attributes=attributes,
    )
    
    try:
        yield context
        await end_trace(context, SpanStatus.OK)
    except Exception as e:
        await end_trace(context, SpanStatus.ERROR, str(e))
        raise


def _store_span(span: Span) -> None:
    """Store a span in the database."""
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO spans (
                span_id, trace_id, parent_span_id, operation_name, kind,
                status, start_time, attributes, events
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                span.span_id,
                span.trace_id,
                span.parent_span_id,
                span.operation_name,
                span.kind.value,
                span.status.value,
                span.start_time.isoformat(),
                json.dumps(span.attributes),
                json.dumps(span.events),
            )
        )
        conn.commit()


async def get_trace(trace_id: str) -> TraceResult | None:
    """Get a complete trace by ID."""
    with _db() as conn:
        trace_row = conn.execute(
            "SELECT * FROM traces WHERE trace_id = ?",
            (trace_id,)
        ).fetchone()
        
        if not trace_row:
            return None
        
        span_rows = conn.execute(
            "SELECT * FROM spans WHERE trace_id = ? ORDER BY start_time",
            (trace_id,)
        ).fetchall()
        
        spans = []
        root_span = None
        
        for row in span_rows:
            span = Span(
                span_id=row["span_id"],
                trace_id=row["trace_id"],
                parent_span_id=row["parent_span_id"],
                operation_name=row["operation_name"],
                kind=SpanKind(row["kind"]),
                status=SpanStatus(row["status"]),
                start_time=datetime.fromisoformat(row["start_time"]),
                end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
                duration_ms=row["duration_ms"],
                attributes=json.loads(row["attributes"]) if row["attributes"] else {},
                events=json.loads(row["events"]) if row["events"] else [],
                error_message=row["error_message"],
            )
            spans.append(span)
            
            if row["span_id"] == trace_row["root_span_id"]:
                root_span = span
        
        return TraceResult(
            trace_id=trace_id,
            spans=spans,
            root_span=root_span,
            total_duration_ms=trace_row["duration_ms"] or 0,
            span_count=trace_row["span_count"],
            error_count=trace_row["error_count"],
            started_at=datetime.fromisoformat(trace_row["started_at"]),
            ended_at=datetime.fromisoformat(trace_row["ended_at"]) if trace_row["ended_at"] else None,
        )
