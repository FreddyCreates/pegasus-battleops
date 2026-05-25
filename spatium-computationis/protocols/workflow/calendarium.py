"""
Protocol: Calendarium  ⏰
Meaning: Task scheduling and cron management.

Handles:
- Scheduled task registration
- Cron-like scheduling
- One-time scheduled tasks
- Task execution tracking
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field


class ScheduleType(str, Enum):
    """Types of schedules."""
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"
    DAILY = "daily"
    WEEKLY = "weekly"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduleConfig(BaseModel):
    """Configuration for a scheduled task."""
    schedule_type: ScheduleType
    run_at: datetime | None = None  # For ONCE
    interval_seconds: int | None = None  # For INTERVAL
    cron_expression: str | None = None  # For CRON
    time_of_day: str | None = None  # For DAILY (HH:MM)
    day_of_week: int | None = None  # For WEEKLY (0=Monday)
    max_retries: int = 3
    timeout_seconds: int = 300


class ScheduledTask(BaseModel):
    """A scheduled task."""
    task_id: str
    name: str
    handler: str  # Function/handler name
    payload: dict[str, Any] = Field(default_factory=dict)
    
    # Schedule
    schedule: ScheduleConfig
    
    # Status
    status: TaskStatus = TaskStatus.PENDING
    enabled: bool = True
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    
    # Execution tracking
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_error: str | None = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "schedules.db"


def _init_schedules_db() -> None:
    """Initialize the schedules database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                task_id         TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                handler         TEXT NOT NULL,
                payload         TEXT DEFAULT '{}',
                schedule_type   TEXT NOT NULL,
                schedule_config TEXT NOT NULL,
                status          TEXT DEFAULT 'pending',
                enabled         INTEGER DEFAULT 1,
                created_at      TEXT NOT NULL,
                next_run_at     TEXT,
                last_run_at     TEXT,
                run_count       INTEGER DEFAULT 0,
                success_count   INTEGER DEFAULT 0,
                failure_count   INTEGER DEFAULT 0,
                last_error      TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_st_status ON scheduled_tasks(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_st_next ON scheduled_tasks(next_run_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_st_enabled ON scheduled_tasks(enabled)")
        
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_executions (
                execution_id    TEXT PRIMARY KEY,
                task_id         TEXT NOT NULL,
                status          TEXT NOT NULL,
                started_at      TEXT NOT NULL,
                completed_at    TEXT,
                duration_ms     REAL,
                error           TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_te_task ON task_executions(task_id)")
        
        conn.commit()


_init_schedules_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Handler Registry
# ---------------------------------------------------------------------------

_task_handlers: dict[str, Callable[[dict], Awaitable[Any]]] = {}


def register_task_handler(name: str, handler: Callable[[dict], Awaitable[Any]]) -> None:
    """Register a task handler function."""
    _task_handlers[name] = handler


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def schedule_task(
    name: str,
    handler: str,
    schedule: ScheduleConfig,
    payload: dict[str, Any] | None = None,
) -> ScheduledTask:
    """
    Protocol Calendarium: schedule a task for execution.
    """
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Calculate next run time
    next_run_at = _calculate_next_run(schedule, now)
    
    task = ScheduledTask(
        task_id=task_id,
        name=name,
        handler=handler,
        payload=payload or {},
        schedule=schedule,
        status=TaskStatus.PENDING,
        created_at=now,
        next_run_at=next_run_at,
    )
    
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO scheduled_tasks (
                task_id, name, handler, payload, schedule_type, schedule_config,
                status, enabled, created_at, next_run_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', 1, ?, ?)
            """,
            (
                task_id,
                name,
                handler,
                json.dumps(payload or {}),
                schedule.schedule_type.value,
                schedule.model_dump_json(),
                now.isoformat(),
                next_run_at.isoformat() if next_run_at else None,
            )
        )
        conn.commit()
    
    return task


async def get_scheduled_tasks(
    status: TaskStatus | None = None,
    enabled_only: bool = True,
    limit: int = 100,
) -> list[ScheduledTask]:
    """
    Protocol Calendarium: get scheduled tasks.
    """
    with _db() as conn:
        query = "SELECT * FROM scheduled_tasks WHERE 1=1"
        params: list[Any] = []
        
        if enabled_only:
            query += " AND enabled = 1"
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        query += " ORDER BY next_run_at LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        
        return [
            ScheduledTask(
                task_id=row["task_id"],
                name=row["name"],
                handler=row["handler"],
                payload=json.loads(row["payload"]) if row["payload"] else {},
                schedule=ScheduleConfig.model_validate_json(row["schedule_config"]),
                status=TaskStatus(row["status"]),
                enabled=bool(row["enabled"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                next_run_at=datetime.fromisoformat(row["next_run_at"]) if row["next_run_at"] else None,
                last_run_at=datetime.fromisoformat(row["last_run_at"]) if row["last_run_at"] else None,
                run_count=row["run_count"],
                success_count=row["success_count"],
                failure_count=row["failure_count"],
                last_error=row["last_error"],
            )
            for row in rows
        ]


async def get_due_tasks() -> list[ScheduledTask]:
    """Get tasks that are due for execution."""
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM scheduled_tasks 
            WHERE enabled = 1 AND status = 'pending' AND next_run_at <= ?
            ORDER BY next_run_at
            """,
            (now.isoformat(),)
        ).fetchall()
        
        return [
            ScheduledTask(
                task_id=row["task_id"],
                name=row["name"],
                handler=row["handler"],
                payload=json.loads(row["payload"]) if row["payload"] else {},
                schedule=ScheduleConfig.model_validate_json(row["schedule_config"]),
                status=TaskStatus(row["status"]),
                enabled=bool(row["enabled"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                next_run_at=datetime.fromisoformat(row["next_run_at"]) if row["next_run_at"] else None,
            )
            for row in rows
        ]


async def execute_task(task_id: str) -> bool:
    """Execute a scheduled task."""
    import time
    
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM scheduled_tasks WHERE task_id = ?",
            (task_id,)
        ).fetchone()
        
        if not row:
            return False
        
        handler_name = row["handler"]
        payload = json.loads(row["payload"]) if row["payload"] else {}
        schedule = ScheduleConfig.model_validate_json(row["schedule_config"])
        
        # Mark as running
        now = datetime.now(timezone.utc)
        execution_id = str(uuid.uuid4())
        
        conn.execute(
            "UPDATE scheduled_tasks SET status = 'running' WHERE task_id = ?",
            (task_id,)
        )
        conn.execute(
            "INSERT INTO task_executions (execution_id, task_id, status, started_at) VALUES (?, ?, 'running', ?)",
            (execution_id, task_id, now.isoformat())
        )
        conn.commit()
    
    # Execute handler
    start_time = time.perf_counter()
    success = False
    error = None
    
    try:
        if handler_name in _task_handlers:
            await _task_handlers[handler_name](payload)
            success = True
        else:
            error = f"Handler not found: {handler_name}"
    except Exception as e:
        error = str(e)
    
    duration_ms = (time.perf_counter() - start_time) * 1000
    completed_at = datetime.now(timezone.utc)
    
    # Update task and execution
    with _db() as conn:
        next_run_at = _calculate_next_run(schedule, completed_at) if schedule.schedule_type != ScheduleType.ONCE else None
        
        if success:
            conn.execute(
                """
                UPDATE scheduled_tasks SET 
                    status = 'pending', last_run_at = ?, next_run_at = ?,
                    run_count = run_count + 1, success_count = success_count + 1
                WHERE task_id = ?
                """,
                (completed_at.isoformat(), next_run_at.isoformat() if next_run_at else None, task_id)
            )
        else:
            conn.execute(
                """
                UPDATE scheduled_tasks SET 
                    status = 'pending', last_run_at = ?, next_run_at = ?,
                    run_count = run_count + 1, failure_count = failure_count + 1, last_error = ?
                WHERE task_id = ?
                """,
                (completed_at.isoformat(), next_run_at.isoformat() if next_run_at else None, error, task_id)
            )
        
        conn.execute(
            """
            UPDATE task_executions SET status = ?, completed_at = ?, duration_ms = ?, error = ?
            WHERE execution_id = ?
            """,
            ('completed' if success else 'failed', completed_at.isoformat(), duration_ms, error, execution_id)
        )
        conn.commit()
    
    return success


def _calculate_next_run(schedule: ScheduleConfig, from_time: datetime) -> datetime | None:
    """Calculate the next run time based on schedule."""
    if schedule.schedule_type == ScheduleType.ONCE:
        return schedule.run_at
    
    elif schedule.schedule_type == ScheduleType.INTERVAL:
        if schedule.interval_seconds:
            return from_time + timedelta(seconds=schedule.interval_seconds)
    
    elif schedule.schedule_type == ScheduleType.DAILY:
        if schedule.time_of_day:
            hour, minute = map(int, schedule.time_of_day.split(":"))
            next_run = from_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= from_time:
                next_run += timedelta(days=1)
            return next_run
    
    elif schedule.schedule_type == ScheduleType.WEEKLY:
        if schedule.day_of_week is not None:
            days_ahead = schedule.day_of_week - from_time.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return from_time + timedelta(days=days_ahead)
    
    return from_time + timedelta(hours=1)  # Default fallback


async def cancel_task(task_id: str) -> bool:
    """Cancel a scheduled task."""
    with _db() as conn:
        cursor = conn.execute(
            "UPDATE scheduled_tasks SET status = 'cancelled', enabled = 0 WHERE task_id = ?",
            (task_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
