"""
Task Queue — Opus Coda  ⚙

A persistent task queue for distributing work to agents.
Agents submit tasks, claim tasks from the queue, and report completion.

Features:
- Priority-based ordering
- Agent affinity (tasks can target specific agents)
- Dead letter queue for failed tasks
- TTL and timeout handling
- Task dependencies

Glyph: ⚙ — unit of work
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


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    """Status of a task in the queue."""
    PENDING = "pending"        # Waiting to be claimed
    CLAIMED = "claimed"        # Claimed by an agent, in progress
    COMPLETED = "completed"    # Successfully completed
    FAILED = "failed"          # Failed after all retries
    CANCELLED = "cancelled"    # Cancelled by submitter
    EXPIRED = "expired"        # TTL exceeded
    DEAD_LETTER = "dead_letter"  # Moved to dead letter queue


class TaskPriority(int, Enum):
    """Priority levels for tasks (lower number = higher priority)."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Task(BaseModel):
    """A unit of work in the task queue."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Task definition
    task_type: str = Field(description="Type of work, e.g. 'estimate_furniture', 'generate_document'")
    payload: dict[str, Any] = Field(default_factory=dict)
    
    # Routing
    target_agent: str | None = Field(default=None, description="Specific agent to handle this task")
    required_capability: str | None = Field(default=None, description="Capability type required")
    
    # Priority & scheduling
    priority: TaskPriority = TaskPriority.NORMAL
    
    # Status tracking
    status: TaskStatus = TaskStatus.PENDING
    claimed_by: str | None = None
    claimed_at: datetime | None = None
    
    # Results
    result: dict[str, Any] | None = None
    error_message: str | None = None
    
    # Metadata
    submitted_by: str | None = None
    project_id: str | None = None
    correlation_id: str | None = None
    
    # Retry & TTL
    max_retries: int = 3
    retry_count: int = 0
    timeout_seconds: int = 300
    ttl_seconds: int | None = None  # None = no expiry
    
    # Dependencies
    depends_on: list[str] = Field(default_factory=list)
    
    # Timestamps
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    expires_at: datetime | None = None


class QueueStats(BaseModel):
    """Statistics about the task queue."""
    total_tasks: int = 0
    pending: int = 0
    claimed: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    expired: int = 0
    dead_letter: int = 0
    avg_wait_time_ms: float = 0.0
    avg_processing_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent / "field" / "queues.db"


def _init_queue_db() -> None:
    """Initialize the task queue database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_queue (
                task_id           TEXT PRIMARY KEY,
                task_type         TEXT NOT NULL,
                payload           TEXT NOT NULL DEFAULT '{}',
                target_agent      TEXT,
                required_capability TEXT,
                priority          INTEGER DEFAULT 3,
                status            TEXT DEFAULT 'pending',
                claimed_by        TEXT,
                claimed_at        TEXT,
                result            TEXT,
                error_message     TEXT,
                submitted_by      TEXT,
                project_id        TEXT,
                correlation_id    TEXT,
                max_retries       INTEGER DEFAULT 3,
                retry_count       INTEGER DEFAULT 0,
                timeout_seconds   INTEGER DEFAULT 300,
                ttl_seconds       INTEGER,
                depends_on        TEXT DEFAULT '[]',
                submitted_at      TEXT NOT NULL,
                completed_at      TEXT,
                expires_at        TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tq_status ON task_queue(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tq_priority ON task_queue(priority)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tq_target ON task_queue(target_agent)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tq_project ON task_queue(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tq_submitted ON task_queue(submitted_at)")
        conn.commit()


_init_queue_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Task Queue Implementation
# ---------------------------------------------------------------------------

class TaskQueue:
    """Persistent priority task queue for agent work distribution."""

    def submit(self, task: Task) -> Task:
        """Submit a task to the queue."""
        now = datetime.now(timezone.utc)
        task.submitted_at = now

        if task.ttl_seconds:
            task.expires_at = now + timedelta(seconds=task.ttl_seconds)

        with _db() as conn:
            conn.execute(
                """
                INSERT INTO task_queue (
                    task_id, task_type, payload, target_agent, required_capability,
                    priority, status, submitted_by, project_id, correlation_id,
                    max_retries, retry_count, timeout_seconds, ttl_seconds,
                    depends_on, submitted_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    task.task_type,
                    json.dumps(task.payload),
                    task.target_agent,
                    task.required_capability,
                    task.priority.value,
                    task.status.value,
                    task.submitted_by,
                    task.project_id,
                    task.correlation_id,
                    task.max_retries,
                    task.retry_count,
                    task.timeout_seconds,
                    task.ttl_seconds,
                    json.dumps(task.depends_on),
                    now.isoformat(),
                    task.expires_at.isoformat() if task.expires_at else None,
                ),
            )
            conn.commit()

        return task

    def claim(self, agent_name: str, task_types: list[str] | None = None) -> Task | None:
        """
        Claim the highest-priority pending task for an agent.
        
        Considers: target_agent affinity, required_capability, priority, submission order.
        """
        now = datetime.now(timezone.utc)

        with _db() as conn:
            # Build query: prioritize tasks targeted at this agent, then general tasks
            query = """
                SELECT * FROM task_queue
                WHERE status = 'pending'
                  AND (target_agent IS NULL OR target_agent = ?)
                  AND (expires_at IS NULL OR expires_at > ?)
            """
            params: list[Any] = [agent_name, now.isoformat()]

            if task_types:
                placeholders = ",".join("?" * len(task_types))
                query += f" AND task_type IN ({placeholders})"
                params.extend(task_types)

            # Check dependencies are satisfied
            query += """
                ORDER BY 
                    CASE WHEN target_agent = ? THEN 0 ELSE 1 END,
                    priority ASC,
                    submitted_at ASC
                LIMIT 1
            """
            params.append(agent_name)

            row = conn.execute(query, params).fetchone()

            if not row:
                return None

            # Check dependencies
            depends_on = json.loads(row["depends_on"]) if row["depends_on"] else []
            if depends_on:
                # Verify all dependencies are completed
                placeholders = ",".join("?" * len(depends_on))
                dep_check = conn.execute(
                    f"SELECT COUNT(*) as cnt FROM task_queue WHERE task_id IN ({placeholders}) AND status = 'completed'",
                    depends_on,
                ).fetchone()
                if dep_check["cnt"] < len(depends_on):
                    return None  # Dependencies not met

            # Claim the task
            conn.execute(
                "UPDATE task_queue SET status = 'claimed', claimed_by = ?, claimed_at = ? WHERE task_id = ?",
                (agent_name, now.isoformat(), row["task_id"]),
            )
            conn.commit()

            return self._row_to_task(row, status=TaskStatus.CLAIMED, claimed_by=agent_name, claimed_at=now)

    def complete(self, task_id: str, result: dict[str, Any] | None = None) -> Task | None:
        """Mark a task as completed with optional result."""
        now = datetime.now(timezone.utc)

        with _db() as conn:
            conn.execute(
                "UPDATE task_queue SET status = 'completed', result = ?, completed_at = ? WHERE task_id = ?",
                (json.dumps(result) if result else None, now.isoformat(), task_id),
            )
            conn.commit()

        return self.get(task_id)

    def fail(self, task_id: str, error_message: str) -> Task | None:
        """Mark a task as failed. If retries remain, requeue it."""
        now = datetime.now(timezone.utc)

        with _db() as conn:
            row = conn.execute("SELECT * FROM task_queue WHERE task_id = ?", (task_id,)).fetchone()
            if not row:
                return None

            retry_count = row["retry_count"] + 1
            if retry_count < row["max_retries"]:
                # Requeue with incremented retry
                conn.execute(
                    """
                    UPDATE task_queue 
                    SET status = 'pending', retry_count = ?, claimed_by = NULL, 
                        claimed_at = NULL, error_message = ?
                    WHERE task_id = ?
                    """,
                    (retry_count, error_message, task_id),
                )
            else:
                # Move to dead letter
                conn.execute(
                    """
                    UPDATE task_queue 
                    SET status = 'dead_letter', retry_count = ?, error_message = ?, completed_at = ?
                    WHERE task_id = ?
                    """,
                    (retry_count, error_message, now.isoformat(), task_id),
                )
            conn.commit()

        return self.get(task_id)

    def cancel(self, task_id: str) -> Task | None:
        """Cancel a pending or claimed task."""
        now = datetime.now(timezone.utc)

        with _db() as conn:
            conn.execute(
                "UPDATE task_queue SET status = 'cancelled', completed_at = ? WHERE task_id = ? AND status IN ('pending', 'claimed')",
                (now.isoformat(), task_id),
            )
            conn.commit()

        return self.get(task_id)

    def get(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        with _db() as conn:
            row = conn.execute("SELECT * FROM task_queue WHERE task_id = ?", (task_id,)).fetchone()
            if not row:
                return None
            return self._row_to_task(row)

    def get_agent_tasks(self, agent_name: str, status: TaskStatus | None = None) -> list[Task]:
        """Get all tasks for a specific agent."""
        with _db() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM task_queue WHERE claimed_by = ? AND status = ? ORDER BY priority ASC",
                    (agent_name, status.value),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM task_queue WHERE claimed_by = ? ORDER BY priority ASC, submitted_at DESC",
                    (agent_name,),
                ).fetchall()
            return [self._row_to_task(r) for r in rows]

    def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        with _db() as conn:
            row = conn.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'claimed' THEN 1 ELSE 0 END) as claimed,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                    SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired,
                    SUM(CASE WHEN status = 'dead_letter' THEN 1 ELSE 0 END) as dead_letter
                FROM task_queue
                """
            ).fetchone()

            return QueueStats(
                total_tasks=row["total"] or 0,
                pending=row["pending"] or 0,
                claimed=row["claimed"] or 0,
                completed=row["completed"] or 0,
                failed=row["failed"] or 0,
                cancelled=row["cancelled"] or 0,
                expired=row["expired"] or 0,
                dead_letter=row["dead_letter"] or 0,
            )

    def _row_to_task(
        self,
        row,
        status: TaskStatus | None = None,
        claimed_by: str | None = None,
        claimed_at: datetime | None = None,
    ) -> Task:
        """Convert a database row to a Task model."""
        return Task(
            task_id=row["task_id"],
            task_type=row["task_type"],
            payload=json.loads(row["payload"]) if row["payload"] else {},
            target_agent=row["target_agent"],
            required_capability=row["required_capability"],
            priority=TaskPriority(row["priority"]),
            status=status or TaskStatus(row["status"]),
            claimed_by=claimed_by or row["claimed_by"],
            claimed_at=claimed_at or (datetime.fromisoformat(row["claimed_at"]) if row["claimed_at"] else None),
            result=json.loads(row["result"]) if row["result"] else None,
            error_message=row["error_message"],
            submitted_by=row["submitted_by"],
            project_id=row["project_id"],
            correlation_id=row["correlation_id"],
            max_retries=row["max_retries"],
            retry_count=row["retry_count"],
            timeout_seconds=row["timeout_seconds"],
            ttl_seconds=row["ttl_seconds"],
            depends_on=json.loads(row["depends_on"]) if row["depends_on"] else [],
            submitted_at=datetime.fromisoformat(row["submitted_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
        )


# ---------------------------------------------------------------------------
# Global Instance & Convenience Functions
# ---------------------------------------------------------------------------

_global_queue: TaskQueue | None = None


def _get_queue() -> TaskQueue:
    global _global_queue
    if _global_queue is None:
        _global_queue = TaskQueue()
    return _global_queue


def submit_task(
    task_type: str,
    payload: dict[str, Any] | None = None,
    target_agent: str | None = None,
    required_capability: str | None = None,
    priority: TaskPriority = TaskPriority.NORMAL,
    submitted_by: str | None = None,
    project_id: str | None = None,
    correlation_id: str | None = None,
    max_retries: int = 3,
    timeout_seconds: int = 300,
    ttl_seconds: int | None = None,
    depends_on: list[str] | None = None,
) -> Task:
    """Submit a new task to the queue."""
    task = Task(
        task_type=task_type,
        payload=payload or {},
        target_agent=target_agent,
        required_capability=required_capability,
        priority=priority,
        submitted_by=submitted_by,
        project_id=project_id,
        correlation_id=correlation_id,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
        ttl_seconds=ttl_seconds,
        depends_on=depends_on or [],
    )
    return _get_queue().submit(task)


def claim_task(agent_name: str, task_types: list[str] | None = None) -> Task | None:
    """Claim the next available task for an agent."""
    return _get_queue().claim(agent_name, task_types)


def complete_task(task_id: str, result: dict[str, Any] | None = None) -> Task | None:
    """Mark a task as completed."""
    return _get_queue().complete(task_id, result)


def fail_task(task_id: str, error_message: str) -> Task | None:
    """Mark a task as failed."""
    return _get_queue().fail(task_id, error_message)


def get_task(task_id: str) -> Task | None:
    """Get a task by ID."""
    return _get_queue().get(task_id)


def get_agent_tasks(agent_name: str, status: TaskStatus | None = None) -> list[Task]:
    """Get tasks for a specific agent."""
    return _get_queue().get_agent_tasks(agent_name, status)


def get_queue_stats() -> QueueStats:
    """Get queue statistics."""
    return _get_queue().get_stats()
