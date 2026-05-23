"""
Protocol: Ordo  📋
Meaning: Workflow orchestration.

Handles:
- Workflow definition
- Step execution
- Conditional branching
- Workflow state management
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class StepType(str, Enum):
    """Types of workflow steps."""
    ACTION = "action"
    CONDITION = "condition"
    PARALLEL = "parallel"
    WAIT = "wait"
    SUBPROCESS = "subprocess"


class WorkflowStep(BaseModel):
    """A step in a workflow."""
    step_id: str
    name: str
    step_type: StepType = StepType.ACTION
    handler: str
    
    # Step configuration
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: list[str] = Field(default_factory=list)
    
    # Control flow
    next_step: str | None = None
    on_failure: str | None = None
    condition: str | None = None  # For conditional steps
    
    # Options
    timeout_seconds: int = 60
    retry_count: int = 0


class WorkflowDefinition(BaseModel):
    """Definition of a workflow."""
    workflow_id: str
    name: str
    description: str = ""
    
    # Steps
    steps: list[WorkflowStep] = Field(default_factory=list)
    start_step: str | None = None
    
    # Configuration
    timeout_seconds: int = 3600
    max_retries: int = 3
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0.0"


class WorkflowExecution(BaseModel):
    """A workflow execution instance."""
    execution_id: str
    workflow_id: str
    
    # State
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    
    # History
    step_history: list[dict[str, Any]] = Field(default_factory=list)
    
    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    # Error
    error: str | None = None


class WorkflowResult(BaseModel):
    """Result of workflow execution."""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    
    # Outputs
    outputs: dict[str, Any] = Field(default_factory=dict)
    
    # Statistics
    steps_executed: int = 0
    steps_successful: int = 0
    steps_failed: int = 0
    
    # Timing
    duration_ms: float | None = None
    
    # Error
    error: str | None = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "workflows.db"


def _init_workflows_db() -> None:
    """Initialize the workflows database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_definitions (
                workflow_id     TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                description     TEXT,
                definition      TEXT NOT NULL,
                version         TEXT DEFAULT '1.0.0',
                created_at      TEXT NOT NULL
            )
            """
        )
        
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_executions (
                execution_id    TEXT PRIMARY KEY,
                workflow_id     TEXT NOT NULL,
                status          TEXT DEFAULT 'pending',
                current_step    TEXT,
                context         TEXT DEFAULT '{}',
                step_history    TEXT DEFAULT '[]',
                started_at      TEXT,
                completed_at    TEXT,
                error           TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_we_workflow ON workflow_executions(workflow_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_we_status ON workflow_executions(status)")
        
        conn.commit()


_init_workflows_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Step Handlers Registry
# ---------------------------------------------------------------------------

_step_handlers: dict[str, Callable[[dict, dict], Awaitable[dict]]] = {}


def register_step_handler(name: str, handler: Callable[[dict, dict], Awaitable[dict]]) -> None:
    """Register a workflow step handler."""
    _step_handlers[name] = handler


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def create_workflow(
    name: str,
    steps: list[WorkflowStep],
    description: str = "",
    start_step: str | None = None,
) -> WorkflowDefinition:
    """
    Protocol Ordo: create a workflow definition.
    """
    workflow_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    workflow = WorkflowDefinition(
        workflow_id=workflow_id,
        name=name,
        description=description,
        steps=steps,
        start_step=start_step or (steps[0].step_id if steps else None),
        created_at=now,
    )
    
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO workflow_definitions (workflow_id, name, description, definition, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (workflow_id, name, description, workflow.model_dump_json(), now.isoformat())
        )
        conn.commit()
    
    return workflow


async def execute_workflow(
    workflow_id: str,
    inputs: dict[str, Any] | None = None,
) -> WorkflowResult:
    """
    Protocol Ordo: execute a workflow.
    """
    execution_id = str(uuid.uuid4())
    start_time = time.perf_counter()
    now = datetime.now(timezone.utc)
    
    # Load workflow definition
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM workflow_definitions WHERE workflow_id = ?",
            (workflow_id,)
        ).fetchone()
        
        if not row:
            return WorkflowResult(
                execution_id=execution_id,
                workflow_id=workflow_id,
                status=WorkflowStatus.FAILED,
                error="Workflow not found",
            )
        
        workflow = WorkflowDefinition.model_validate_json(row["definition"])
    
    # Initialize execution
    context = inputs or {}
    step_history: list[dict] = []
    current_step = workflow.start_step
    steps_executed = 0
    steps_successful = 0
    steps_failed = 0
    error = None
    
    # Create execution record
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO workflow_executions (
                execution_id, workflow_id, status, current_step, context, started_at
            ) VALUES (?, ?, 'running', ?, ?, ?)
            """,
            (execution_id, workflow_id, current_step, json.dumps(context), now.isoformat())
        )
        conn.commit()
    
    # Execute steps
    steps_map = {step.step_id: step for step in workflow.steps}
    
    while current_step and current_step in steps_map:
        step = steps_map[current_step]
        step_start = time.perf_counter()
        
        try:
            # Get handler
            handler = _step_handlers.get(step.handler)
            if not handler:
                raise ValueError(f"Handler not found: {step.handler}")
            
            # Prepare inputs
            step_inputs = {}
            for key, value in step.inputs.items():
                if isinstance(value, str) and value.startswith("$"):
                    # Variable reference
                    var_name = value[1:]
                    step_inputs[key] = context.get(var_name)
                else:
                    step_inputs[key] = value
            
            # Execute step
            result = await handler(step_inputs, context)
            
            # Store outputs in context
            for output_key in step.outputs:
                if output_key in result:
                    context[output_key] = result[output_key]
            
            step_duration = (time.perf_counter() - step_start) * 1000
            step_history.append({
                "step_id": step.step_id,
                "status": "completed",
                "duration_ms": step_duration,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            
            steps_executed += 1
            steps_successful += 1
            current_step = step.next_step
            
        except Exception as e:
            step_duration = (time.perf_counter() - step_start) * 1000
            step_history.append({
                "step_id": step.step_id,
                "status": "failed",
                "error": str(e),
                "duration_ms": step_duration,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            
            steps_executed += 1
            steps_failed += 1
            
            if step.on_failure:
                current_step = step.on_failure
            else:
                error = str(e)
                break
    
    # Determine final status
    duration_ms = (time.perf_counter() - start_time) * 1000
    completed_at = datetime.now(timezone.utc)
    
    if error:
        status = WorkflowStatus.FAILED
    elif steps_failed > 0:
        status = WorkflowStatus.FAILED
    else:
        status = WorkflowStatus.COMPLETED
    
    # Update execution record
    with _db() as conn:
        conn.execute(
            """
            UPDATE workflow_executions SET
                status = ?, current_step = ?, context = ?, step_history = ?,
                completed_at = ?, error = ?
            WHERE execution_id = ?
            """,
            (
                status.value,
                current_step,
                json.dumps(context),
                json.dumps(step_history),
                completed_at.isoformat(),
                error,
                execution_id,
            )
        )
        conn.commit()
    
    return WorkflowResult(
        execution_id=execution_id,
        workflow_id=workflow_id,
        status=status,
        outputs=context,
        steps_executed=steps_executed,
        steps_successful=steps_successful,
        steps_failed=steps_failed,
        duration_ms=duration_ms,
        error=error,
    )


async def get_workflow_execution(execution_id: str) -> WorkflowExecution | None:
    """Get a workflow execution."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM workflow_executions WHERE execution_id = ?",
            (execution_id,)
        ).fetchone()
        
        if not row:
            return None
        
        return WorkflowExecution(
            execution_id=row["execution_id"],
            workflow_id=row["workflow_id"],
            status=WorkflowStatus(row["status"]),
            current_step=row["current_step"],
            context=json.loads(row["context"]) if row["context"] else {},
            step_history=json.loads(row["step_history"]) if row["step_history"] else [],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            error=row["error"],
        )
