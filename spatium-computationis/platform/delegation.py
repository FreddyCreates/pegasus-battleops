"""
Inter-Agent Delegation — Delegatio  ⇆

Enables agents to request work from other agents:
- Direct delegation (to a specific agent)
- Capability-based delegation (find best agent for the job)
- Async delegation with status tracking
- Delegation chains (multi-hop workflows)

Glyph: ⇆ — inter-agent request
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

from ..scaffolds.base import (
    CapabilityType,
    LifecycleState,
    get_agent_scaffold,
    get_agents_by_capability,
)
from .task_queue import (
    Task,
    TaskPriority,
    TaskStatus,
    submit_task,
    get_task,
)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DelegationStatus(str, Enum):
    """Status of a delegation request."""
    SUBMITTED = "submitted"        # Request submitted, not yet accepted
    ACCEPTED = "accepted"          # Target agent accepted
    IN_PROGRESS = "in_progress"    # Work is being done
    COMPLETED = "completed"        # Successfully completed
    REJECTED = "rejected"          # Target agent rejected
    FAILED = "failed"              # Delegation failed
    TIMED_OUT = "timed_out"        # No response within timeout


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class DelegationRequest(BaseModel):
    """A request from one agent to another."""
    delegation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Source
    requesting_agent: str
    requesting_reason: str = ""
    
    # Target
    target_agent: str | None = None  # Specific agent
    target_capability: str | None = None  # Or find by capability
    
    # Work definition
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    
    # Context
    project_id: str | None = None
    correlation_id: str | None = None
    priority: TaskPriority = TaskPriority.NORMAL
    
    # Configuration
    timeout_seconds: int = 300
    allow_sub_delegation: bool = True  # Can the target delegate further?
    
    # Status tracking
    status: DelegationStatus = DelegationStatus.SUBMITTED
    task_id: str | None = None  # Linked task in the queue
    
    # Timestamps
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None


class DelegationResult(BaseModel):
    """Result of a delegation."""
    delegation_id: str
    status: DelegationStatus
    
    # Who handled it
    handled_by: str | None = None
    
    # Results
    result: dict[str, Any] | None = None
    error_message: str | None = None
    
    # Chain tracking
    sub_delegations: list[str] = Field(default_factory=list)
    
    # Timing
    submitted_at: datetime
    resolved_at: datetime | None = None
    duration_ms: float | None = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent / "field" / "queues.db"


def _init_delegation_db() -> None:
    """Initialize the delegation tracking table."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS delegations (
                delegation_id     TEXT PRIMARY KEY,
                requesting_agent  TEXT NOT NULL,
                requesting_reason TEXT,
                target_agent      TEXT,
                target_capability TEXT,
                task_type         TEXT NOT NULL,
                payload           TEXT DEFAULT '{}',
                project_id        TEXT,
                correlation_id    TEXT,
                priority          INTEGER DEFAULT 3,
                timeout_seconds   INTEGER DEFAULT 300,
                allow_sub_delegation INTEGER DEFAULT 1,
                status            TEXT DEFAULT 'submitted',
                task_id           TEXT,
                handled_by        TEXT,
                result            TEXT,
                error_message     TEXT,
                sub_delegations   TEXT DEFAULT '[]',
                submitted_at      TEXT NOT NULL,
                resolved_at       TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_del_status ON delegations(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_del_requester ON delegations(requesting_agent)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_del_target ON delegations(target_agent)")
        conn.commit()


_init_delegation_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Delegation Logic
# ---------------------------------------------------------------------------

def delegate_to_agent(
    requesting_agent: str,
    target_agent: str,
    task_type: str,
    payload: dict[str, Any] | None = None,
    project_id: str | None = None,
    priority: TaskPriority = TaskPriority.NORMAL,
    reason: str = "",
    timeout_seconds: int = 300,
    correlation_id: str | None = None,
) -> DelegationRequest:
    """
    Delegate work directly to a specific agent.
    
    Creates a delegation record and submits a task targeted at the agent.
    """
    # Verify target agent exists
    scaffold = get_agent_scaffold(target_agent)
    if not scaffold:
        raise ValueError(f"Target agent '{target_agent}' not found in registry")

    if scaffold.state not in (LifecycleState.READY, LifecycleState.BUSY):
        raise ValueError(f"Target agent '{target_agent}' is not available (state: {scaffold.state.value})")

    delegation = DelegationRequest(
        requesting_agent=requesting_agent,
        requesting_reason=reason,
        target_agent=target_agent,
        task_type=task_type,
        payload=payload or {},
        project_id=project_id,
        correlation_id=correlation_id or str(uuid.uuid4()),
        priority=priority,
        timeout_seconds=timeout_seconds,
    )

    # Submit as a task in the queue
    task = submit_task(
        task_type=task_type,
        payload={
            "delegation_id": delegation.delegation_id,
            "requesting_agent": requesting_agent,
            **(payload or {}),
        },
        target_agent=target_agent,
        priority=priority,
        submitted_by=requesting_agent,
        project_id=project_id,
        correlation_id=delegation.correlation_id,
        timeout_seconds=timeout_seconds,
    )

    delegation.task_id = task.task_id
    delegation.status = DelegationStatus.SUBMITTED

    # Persist delegation record
    _persist_delegation(delegation)

    return delegation


def delegate_to_capability(
    requesting_agent: str,
    capability_type: CapabilityType,
    task_type: str,
    payload: dict[str, Any] | None = None,
    project_id: str | None = None,
    priority: TaskPriority = TaskPriority.NORMAL,
    reason: str = "",
    timeout_seconds: int = 300,
    correlation_id: str | None = None,
) -> DelegationRequest:
    """
    Delegate work to the best available agent with a specific capability.
    
    The system finds the most suitable agent based on:
    - Availability (state, capacity)
    - Quality score for the capability
    - Current load
    """
    agents = get_agents_by_capability(capability_type)

    # Filter to available agents
    available = [
        a for a in agents
        if a.state in (LifecycleState.READY, LifecycleState.BUSY)
        and a.current_tasks < a.config.max_concurrent_tasks
    ]

    if not available:
        raise ValueError(f"No available agents with capability '{capability_type.value}'")

    # Score agents: prefer ready over busy, lower load, higher quality
    def agent_score(scaffold):
        state_score = 1.0 if scaffold.state == LifecycleState.READY else 0.5
        load_ratio = scaffold.current_tasks / max(scaffold.config.max_concurrent_tasks, 1)
        load_score = 1.0 - load_ratio
        
        # Find quality score for this capability
        quality_score = 0.5
        for cap in scaffold.config.capabilities:
            if cap.capability_type == capability_type and cap.enabled:
                quality_score = cap.quality_score
                break

        return state_score * 0.3 + load_score * 0.4 + quality_score * 0.3

    best_agent = max(available, key=agent_score)

    delegation = DelegationRequest(
        requesting_agent=requesting_agent,
        requesting_reason=reason,
        target_agent=best_agent.config.agent_name,
        target_capability=capability_type.value,
        task_type=task_type,
        payload=payload or {},
        project_id=project_id,
        correlation_id=correlation_id or str(uuid.uuid4()),
        priority=priority,
        timeout_seconds=timeout_seconds,
    )

    # Submit as a task
    task = submit_task(
        task_type=task_type,
        payload={
            "delegation_id": delegation.delegation_id,
            "requesting_agent": requesting_agent,
            **(payload or {}),
        },
        target_agent=best_agent.config.agent_name,
        required_capability=capability_type.value,
        priority=priority,
        submitted_by=requesting_agent,
        project_id=project_id,
        correlation_id=delegation.correlation_id,
        timeout_seconds=timeout_seconds,
    )

    delegation.task_id = task.task_id
    delegation.status = DelegationStatus.SUBMITTED

    _persist_delegation(delegation)

    return delegation


def get_delegation_status(delegation_id: str) -> DelegationResult | None:
    """Get the current status of a delegation."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM delegations WHERE delegation_id = ?",
            (delegation_id,),
        ).fetchone()

        if not row:
            return None

        # Also check linked task status
        task_status = None
        if row["task_id"]:
            task = get_task(row["task_id"])
            if task:
                task_status = task.status

        status = DelegationStatus(row["status"])
        
        # Sync status from task if needed
        if task_status == TaskStatus.COMPLETED and status != DelegationStatus.COMPLETED:
            status = DelegationStatus.COMPLETED
        elif task_status == TaskStatus.DEAD_LETTER and status != DelegationStatus.FAILED:
            status = DelegationStatus.FAILED

        submitted_at = datetime.fromisoformat(row["submitted_at"])
        resolved_at = datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None

        duration_ms = None
        if resolved_at:
            duration_ms = (resolved_at - submitted_at).total_seconds() * 1000

        return DelegationResult(
            delegation_id=delegation_id,
            status=status,
            handled_by=row["handled_by"],
            result=json.loads(row["result"]) if row["result"] else None,
            error_message=row["error_message"],
            sub_delegations=json.loads(row["sub_delegations"]) if row["sub_delegations"] else [],
            submitted_at=submitted_at,
            resolved_at=resolved_at,
            duration_ms=duration_ms,
        )


def complete_delegation(delegation_id: str, result: dict[str, Any] | None = None, handled_by: str | None = None) -> None:
    """Mark a delegation as completed."""
    now = datetime.now(timezone.utc)
    with _db() as conn:
        conn.execute(
            "UPDATE delegations SET status = 'completed', result = ?, handled_by = ?, resolved_at = ? WHERE delegation_id = ?",
            (json.dumps(result) if result else None, handled_by, now.isoformat(), delegation_id),
        )
        conn.commit()


def fail_delegation(delegation_id: str, error_message: str) -> None:
    """Mark a delegation as failed."""
    now = datetime.now(timezone.utc)
    with _db() as conn:
        conn.execute(
            "UPDATE delegations SET status = 'failed', error_message = ?, resolved_at = ? WHERE delegation_id = ?",
            (error_message, now.isoformat(), delegation_id),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Persistence Helpers
# ---------------------------------------------------------------------------

def _persist_delegation(delegation: DelegationRequest) -> None:
    """Persist a delegation record to the database."""
    with _db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO delegations (
                delegation_id, requesting_agent, requesting_reason,
                target_agent, target_capability, task_type, payload,
                project_id, correlation_id, priority, timeout_seconds,
                allow_sub_delegation, status, task_id, submitted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                delegation.delegation_id,
                delegation.requesting_agent,
                delegation.requesting_reason,
                delegation.target_agent,
                delegation.target_capability,
                delegation.task_type,
                json.dumps(delegation.payload),
                delegation.project_id,
                delegation.correlation_id,
                delegation.priority.value,
                delegation.timeout_seconds,
                1 if delegation.allow_sub_delegation else 0,
                delegation.status.value,
                delegation.task_id,
                delegation.submitted_at.isoformat(),
            ),
        )
        conn.commit()
