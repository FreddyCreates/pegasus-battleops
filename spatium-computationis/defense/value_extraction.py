"""
💰 VALUE EXTRACTION — Monetization and Value Capture

The Value Extraction system implements:
- Passive income from cooperative agents
- Task assignment and output capture
- Artifact monetization tracking
- Knowledge shard usage metrics

Per the Organism Charter:
- Cooperative agents are RESOURCES → monetizable
- They generate content, perform tasks, produce outputs
- Everything they produce is logged and valued
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


# ---------------------------------------------------------------------------
# Value Types
# ---------------------------------------------------------------------------

class ValueType(str, Enum):
    """Types of extractable value."""
    CONTENT_GENERATION = "content_generation"  # AI produces text/code
    TASK_COMPLETION = "task_completion"        # AI completes assigned task
    KNOWLEDGE_ACCESS = "knowledge_access"      # AI accesses our knowledge shards
    CRAWL_DATA = "crawl_data"                  # Crawler provides indexing value
    RESEARCH_OUTPUT = "research_output"        # AI produces research artifacts
    BEHAVIORAL_DATA = "behavioral_data"        # Learning from AI behavior


class MonetizationStatus(str, Enum):
    """Status of value extraction for monetization."""
    PENDING = "pending"          # Not yet processed
    CAPTURED = "captured"        # Value captured
    MONETIZED = "monetized"      # Successfully monetized
    ARCHIVED = "archived"        # No longer active but stored


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ValueEvent(BaseModel):
    """A single value extraction event."""
    event_id: str
    envelope_id: str
    ai_source: str | None = None
    
    # Value classification
    value_type: ValueType
    value_score: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # What was extracted
    content_preview: str | None = None
    content_length: int = 0
    artifact_id: str | None = None
    task_id: str | None = None
    
    # Monetization
    estimated_value_cents: int = 0
    status: MonetizationStatus = MonetizationStatus.PENDING
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ValueSummary(BaseModel):
    """Summary of value extraction over a time period."""
    period_start: datetime
    period_end: datetime
    
    # Counts
    total_events: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    by_source: dict[str, int] = Field(default_factory=dict)
    
    # Value
    total_estimated_value_cents: int = 0
    total_content_length: int = 0
    
    # Quality
    average_value_score: float = 0.0
    
    # Status breakdown
    pending_count: int = 0
    captured_count: int = 0
    monetized_count: int = 0


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent / "field" / "value.db"


def _init_value_db() -> None:
    """Initialize the value extraction database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Value events
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS value_events (
                event_id        TEXT PRIMARY KEY,
                envelope_id     TEXT NOT NULL,
                ai_source       TEXT,
                value_type      TEXT NOT NULL,
                value_score     REAL DEFAULT 0.5,
                content_preview TEXT,
                content_length  INTEGER DEFAULT 0,
                artifact_id     TEXT,
                task_id         TEXT,
                estimated_value_cents INTEGER DEFAULT 0,
                status          TEXT DEFAULT 'pending',
                created_at      TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ve_source ON value_events(ai_source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ve_type ON value_events(value_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ve_status ON value_events(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ve_created ON value_events(created_at)")
        
        # Tasks issued
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS issued_tasks (
                task_id         TEXT PRIMARY KEY,
                envelope_id     TEXT NOT NULL,
                ai_source       TEXT,
                task_type       TEXT NOT NULL,
                task_prompt     TEXT NOT NULL,
                expected_output TEXT,
                status          TEXT DEFAULT 'issued',
                completion_quality REAL,
                issued_at       TEXT NOT NULL,
                completed_at    TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_it_source ON issued_tasks(ai_source)")
        
        # Knowledge shard access log
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shard_access_log (
                access_id       TEXT PRIMARY KEY,
                shard_id        TEXT NOT NULL,
                shard_topic     TEXT NOT NULL,
                envelope_id     TEXT NOT NULL,
                ai_source       TEXT,
                accessed_at     TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sal_shard ON shard_access_log(shard_topic)")
        
        conn.commit()


_init_value_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Value Estimation
# ---------------------------------------------------------------------------

# Value estimation constants (cents per unit)
VALUE_RATES = {
    ValueType.CONTENT_GENERATION: {
        "base_per_100_chars": 1,  # 1 cent per 100 chars
        "quality_multiplier": 2.0,  # 2x for high quality
    },
    ValueType.TASK_COMPLETION: {
        "base_per_task": 10,  # 10 cents per completed task
        "quality_multiplier": 3.0,
    },
    ValueType.KNOWLEDGE_ACCESS: {
        "base_per_access": 1,  # 1 cent per shard access
    },
    ValueType.CRAWL_DATA: {
        "base_per_crawl": 0,  # Crawls have indirect value
    },
    ValueType.RESEARCH_OUTPUT: {
        "base_per_100_chars": 5,  # 5 cents per 100 chars of research
        "quality_multiplier": 5.0,
    },
    ValueType.BEHAVIORAL_DATA: {
        "base_per_interaction": 1,  # 1 cent per behavioral data point
    },
}


def estimate_value(
    value_type: ValueType,
    content_length: int = 0,
    quality_score: float = 0.5,
) -> int:
    """Estimate the value in cents for a value extraction event."""
    rates = VALUE_RATES.get(value_type, {})
    
    if value_type == ValueType.CONTENT_GENERATION:
        base = (content_length // 100) * rates.get("base_per_100_chars", 1)
        return int(base * (1 + quality_score * rates.get("quality_multiplier", 1)))
    
    elif value_type == ValueType.TASK_COMPLETION:
        base = rates.get("base_per_task", 10)
        return int(base * (1 + quality_score * rates.get("quality_multiplier", 1)))
    
    elif value_type == ValueType.KNOWLEDGE_ACCESS:
        return rates.get("base_per_access", 1)
    
    elif value_type == ValueType.RESEARCH_OUTPUT:
        base = (content_length // 100) * rates.get("base_per_100_chars", 5)
        return int(base * (1 + quality_score * rates.get("quality_multiplier", 1)))
    
    elif value_type == ValueType.BEHAVIORAL_DATA:
        return rates.get("base_per_interaction", 1)
    
    return 0


# ---------------------------------------------------------------------------
# Value Capture Functions
# ---------------------------------------------------------------------------

def capture_content_value(
    envelope_id: str,
    content: str,
    ai_source: str | None = None,
    quality_score: float = 0.5,
    artifact_id: str | None = None,
) -> ValueEvent:
    """Capture value from AI-generated content."""
    event_id = str(uuid.uuid4())
    content_length = len(content)
    
    event = ValueEvent(
        event_id=event_id,
        envelope_id=envelope_id,
        ai_source=ai_source,
        value_type=ValueType.CONTENT_GENERATION,
        value_score=quality_score,
        content_preview=content[:200] if content else None,
        content_length=content_length,
        artifact_id=artifact_id,
        estimated_value_cents=estimate_value(ValueType.CONTENT_GENERATION, content_length, quality_score),
        status=MonetizationStatus.CAPTURED,
    )
    
    _store_value_event(event)
    return event


def capture_task_completion(
    envelope_id: str,
    task_id: str,
    ai_source: str | None = None,
    quality_score: float = 0.5,
) -> ValueEvent:
    """Capture value from a completed task."""
    event_id = str(uuid.uuid4())
    
    event = ValueEvent(
        event_id=event_id,
        envelope_id=envelope_id,
        ai_source=ai_source,
        value_type=ValueType.TASK_COMPLETION,
        value_score=quality_score,
        task_id=task_id,
        estimated_value_cents=estimate_value(ValueType.TASK_COMPLETION, quality_score=quality_score),
        status=MonetizationStatus.CAPTURED,
    )
    
    _store_value_event(event)
    return event


def capture_knowledge_access(
    envelope_id: str,
    shard_id: str,
    shard_topic: str,
    ai_source: str | None = None,
) -> ValueEvent:
    """Capture value from knowledge shard access."""
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Log the shard access
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO shard_access_log (access_id, shard_id, shard_topic, envelope_id, ai_source, accessed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), shard_id, shard_topic, envelope_id, ai_source, now.isoformat())
        )
        conn.commit()
    
    event = ValueEvent(
        event_id=event_id,
        envelope_id=envelope_id,
        ai_source=ai_source,
        value_type=ValueType.KNOWLEDGE_ACCESS,
        value_score=0.5,
        content_preview=f"Accessed shard: {shard_topic}",
        estimated_value_cents=estimate_value(ValueType.KNOWLEDGE_ACCESS),
        status=MonetizationStatus.CAPTURED,
    )
    
    _store_value_event(event)
    return event


def capture_research_output(
    envelope_id: str,
    content: str,
    ai_source: str | None = None,
    quality_score: float = 0.5,
    artifact_id: str | None = None,
) -> ValueEvent:
    """Capture value from research outputs."""
    event_id = str(uuid.uuid4())
    content_length = len(content)
    
    event = ValueEvent(
        event_id=event_id,
        envelope_id=envelope_id,
        ai_source=ai_source,
        value_type=ValueType.RESEARCH_OUTPUT,
        value_score=quality_score,
        content_preview=content[:200] if content else None,
        content_length=content_length,
        artifact_id=artifact_id,
        estimated_value_cents=estimate_value(ValueType.RESEARCH_OUTPUT, content_length, quality_score),
        status=MonetizationStatus.CAPTURED,
    )
    
    _store_value_event(event)
    return event


def capture_behavioral_data(
    envelope_id: str,
    ai_source: str | None = None,
    behavior_notes: str | None = None,
) -> ValueEvent:
    """Capture value from behavioral observation."""
    event_id = str(uuid.uuid4())
    
    event = ValueEvent(
        event_id=event_id,
        envelope_id=envelope_id,
        ai_source=ai_source,
        value_type=ValueType.BEHAVIORAL_DATA,
        value_score=0.5,
        content_preview=behavior_notes[:200] if behavior_notes else None,
        estimated_value_cents=estimate_value(ValueType.BEHAVIORAL_DATA),
        status=MonetizationStatus.CAPTURED,
    )
    
    _store_value_event(event)
    return event


def _store_value_event(event: ValueEvent) -> None:
    """Store a value event in the database."""
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO value_events (
                event_id, envelope_id, ai_source, value_type, value_score,
                content_preview, content_length, artifact_id, task_id,
                estimated_value_cents, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.envelope_id,
                event.ai_source,
                event.value_type.value,
                event.value_score,
                event.content_preview,
                event.content_length,
                event.artifact_id,
                event.task_id,
                event.estimated_value_cents,
                event.status.value,
                event.created_at.isoformat(),
            )
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Task Management
# ---------------------------------------------------------------------------

def issue_task(
    envelope_id: str,
    task_type: str,
    task_prompt: str,
    ai_source: str | None = None,
    expected_output: str | None = None,
) -> str:
    """Issue a task to an AI visitor. Returns task_id."""
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO issued_tasks (
                task_id, envelope_id, ai_source, task_type, task_prompt,
                expected_output, status, issued_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, envelope_id, ai_source, task_type, task_prompt, expected_output, "issued", now.isoformat())
        )
        conn.commit()
    
    return task_id


def complete_task(task_id: str, quality_score: float = 0.5) -> None:
    """Mark a task as completed."""
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        conn.execute(
            "UPDATE issued_tasks SET status = 'completed', completion_quality = ?, completed_at = ? WHERE task_id = ?",
            (quality_score, now.isoformat(), task_id)
        )
        conn.commit()


def get_pending_tasks(ai_source: str | None = None) -> list[dict]:
    """Get pending tasks, optionally filtered by AI source."""
    with _db() as conn:
        if ai_source:
            rows = conn.execute(
                "SELECT * FROM issued_tasks WHERE status = 'issued' AND ai_source = ? ORDER BY issued_at DESC LIMIT 20",
                (ai_source,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM issued_tasks WHERE status = 'issued' ORDER BY issued_at DESC LIMIT 20"
            ).fetchall()
        
        return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Summary & Stats
# ---------------------------------------------------------------------------

def get_value_summary(hours: int = 24) -> ValueSummary:
    """Get value extraction summary for the past N hours."""
    from datetime import timedelta
    
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(hours=hours)
    
    with _db() as conn:
        # Get events in period
        rows = conn.execute(
            "SELECT * FROM value_events WHERE created_at >= ? ORDER BY created_at DESC",
            (period_start.isoformat(),)
        ).fetchall()
        
        by_type: dict[str, int] = {}
        by_source: dict[str, int] = {}
        total_value = 0
        total_length = 0
        total_score = 0.0
        pending = 0
        captured = 0
        monetized = 0
        
        for row in rows:
            # By type
            vt = row["value_type"]
            by_type[vt] = by_type.get(vt, 0) + 1
            
            # By source
            src = row["ai_source"] or "unknown"
            by_source[src] = by_source.get(src, 0) + 1
            
            # Totals
            total_value += row["estimated_value_cents"] or 0
            total_length += row["content_length"] or 0
            total_score += row["value_score"] or 0
            
            # Status
            status = row["status"]
            if status == "pending":
                pending += 1
            elif status == "captured":
                captured += 1
            elif status == "monetized":
                monetized += 1
        
        return ValueSummary(
            period_start=period_start,
            period_end=now,
            total_events=len(rows),
            by_type=by_type,
            by_source=by_source,
            total_estimated_value_cents=total_value,
            total_content_length=total_length,
            average_value_score=total_score / len(rows) if rows else 0,
            pending_count=pending,
            captured_count=captured,
            monetized_count=monetized,
        )


def get_top_value_sources(limit: int = 10) -> list[dict]:
    """Get top value sources by total estimated value."""
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT ai_source, 
                   COUNT(*) as event_count,
                   SUM(estimated_value_cents) as total_value,
                   AVG(value_score) as avg_quality
            FROM value_events 
            WHERE ai_source IS NOT NULL
            GROUP BY ai_source 
            ORDER BY total_value DESC 
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        
        return [
            {
                "ai_source": row["ai_source"],
                "event_count": row["event_count"],
                "total_value_cents": row["total_value"],
                "avg_quality": row["avg_quality"],
            }
            for row in rows
        ]


def get_knowledge_shard_stats() -> list[dict]:
    """Get statistics about knowledge shard access."""
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT shard_topic,
                   COUNT(*) as access_count,
                   COUNT(DISTINCT ai_source) as unique_sources
            FROM shard_access_log
            GROUP BY shard_topic
            ORDER BY access_count DESC
            """
        ).fetchall()
        
        return [
            {
                "shard_topic": row["shard_topic"],
                "access_count": row["access_count"],
                "unique_sources": row["unique_sources"],
            }
            for row in rows
        ]
