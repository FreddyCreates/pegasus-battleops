"""
Base Scaffold — Agent Structural Foundation  ⌂

Provides the core scaffolding for all agents:
- Capability declarations (what can this agent do?)
- Configuration management
- Lifecycle state tracking
- Registry for agent discovery

Every agent in Spatium Computationis is built on this scaffold.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class LifecycleState(str, Enum):
    """Agent lifecycle states."""
    INITIALIZING = "initializing"  # Agent is starting up
    READY = "ready"                # Agent is ready to accept work
    BUSY = "busy"                  # Agent is processing
    PAUSED = "paused"              # Agent is temporarily paused
    DEGRADED = "degraded"          # Agent has reduced capability
    ERROR = "error"                # Agent encountered an error
    SHUTTING_DOWN = "shutting_down"  # Agent is cleaning up
    RETIRED = "retired"            # Agent is no longer available


class CapabilityType(str, Enum):
    """Types of agent capabilities."""
    GENERATION = "generation"      # Can generate content/documents
    ANALYSIS = "analysis"          # Can analyze input
    TRANSFORMATION = "transformation"  # Can transform data
    STORAGE = "storage"            # Can store/retrieve data
    COMMUNICATION = "communication"  # Can communicate with external systems
    DECISION = "decision"          # Can make routing/action decisions
    LEARNING = "learning"          # Can learn from feedback


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AgentCapability(BaseModel):
    """Declares a specific capability of an agent."""
    capability_id: str
    capability_type: CapabilityType
    name: str
    description: str
    
    # Input/output types
    input_types: list[str] = Field(default_factory=list)
    output_types: list[str] = Field(default_factory=list)
    
    # Performance characteristics
    avg_latency_ms: float | None = None
    throughput_per_minute: float | None = None
    
    # Quality metrics
    quality_score: float = Field(ge=0.0, le=1.0, default=0.5)
    reliability_score: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Dependencies
    requires_capabilities: list[str] = Field(default_factory=list)
    
    # Cost
    cost_per_invocation_cents: float = 0.0
    
    # Enabled
    enabled: bool = True


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    agent_name: str
    agent_class: str
    version: str = "1.0.0"
    
    # Glyph and description
    glyph: str = "⚙"
    description: str = ""
    
    # Region/domain
    primary_region: str = "core"
    secondary_regions: list[str] = Field(default_factory=list)
    
    # Capabilities
    capabilities: list[AgentCapability] = Field(default_factory=list)
    
    # Resource limits
    max_concurrent_tasks: int = 10
    timeout_seconds: int = 60
    retry_count: int = 3
    
    # Feature flags
    features: dict[str, bool] = Field(default_factory=dict)
    
    # External dependencies
    requires_nova_sovereign: bool = False
    requires_database: bool = False
    requires_external_api: bool = False
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentScaffold(BaseModel):
    """Complete scaffold for an agent instance."""
    scaffold_id: str
    config: AgentConfig
    
    # Current state
    state: LifecycleState = LifecycleState.INITIALIZING
    
    # Runtime metrics
    tasks_completed: int = 0
    tasks_failed: int = 0
    current_tasks: int = 0
    
    # Health
    last_heartbeat: datetime | None = None
    error_count: int = 0
    last_error: str | None = None
    
    # Performance
    avg_task_duration_ms: float = 0.0
    
    # Timestamps
    initialized_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent / "field" / "scaffolds.db"


def _init_scaffold_db() -> None:
    """Initialize the scaffold database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Agent scaffolds
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_scaffolds (
                scaffold_id     TEXT PRIMARY KEY,
                agent_name      TEXT NOT NULL UNIQUE,
                config          TEXT NOT NULL,
                state           TEXT DEFAULT 'initializing',
                tasks_completed INTEGER DEFAULT 0,
                tasks_failed    INTEGER DEFAULT 0,
                current_tasks   INTEGER DEFAULT 0,
                last_heartbeat  TEXT,
                error_count     INTEGER DEFAULT 0,
                last_error      TEXT,
                avg_task_duration REAL DEFAULT 0.0,
                initialized_at  TEXT NOT NULL,
                last_activity   TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_as_name ON agent_scaffolds(agent_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_as_state ON agent_scaffolds(state)")
        
        # Capability registry
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS capability_registry (
                capability_id   TEXT PRIMARY KEY,
                agent_name      TEXT NOT NULL,
                capability_type TEXT NOT NULL,
                name            TEXT NOT NULL,
                description     TEXT,
                input_types     TEXT,
                output_types    TEXT,
                quality_score   REAL DEFAULT 0.5,
                enabled         INTEGER DEFAULT 1,
                created_at      TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cr_agent ON capability_registry(agent_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cr_type ON capability_registry(capability_type)")
        
        conn.commit()


_init_scaffold_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

# In-memory registry for fast lookup
_scaffold_registry: dict[str, AgentScaffold] = {}


def scaffold_registry() -> dict[str, AgentScaffold]:
    """Get the current scaffold registry."""
    return _scaffold_registry.copy()


def register_agent(config: AgentConfig) -> AgentScaffold:
    """Register a new agent with the system."""
    scaffold_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    scaffold = AgentScaffold(
        scaffold_id=scaffold_id,
        config=config,
        state=LifecycleState.READY,
        initialized_at=now,
        last_activity=now,
    )
    
    # Store in memory
    _scaffold_registry[config.agent_name] = scaffold
    
    # Persist to database
    with _db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO agent_scaffolds (
                scaffold_id, agent_name, config, state,
                tasks_completed, tasks_failed, current_tasks,
                error_count, initialized_at, last_activity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scaffold_id,
                config.agent_name,
                config.model_dump_json(),
                scaffold.state.value,
                0, 0, 0, 0,
                now.isoformat(),
                now.isoformat()
            )
        )
        
        # Register capabilities
        for cap in config.capabilities:
            conn.execute(
                """
                INSERT OR REPLACE INTO capability_registry (
                    capability_id, agent_name, capability_type, name,
                    description, input_types, output_types, quality_score,
                    enabled, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cap.capability_id,
                    config.agent_name,
                    cap.capability_type.value,
                    cap.name,
                    cap.description,
                    json.dumps(cap.input_types),
                    json.dumps(cap.output_types),
                    cap.quality_score,
                    1 if cap.enabled else 0,
                    now.isoformat()
                )
            )
        
        conn.commit()
    
    return scaffold


def get_agent_scaffold(agent_name: str) -> AgentScaffold | None:
    """Get the scaffold for a specific agent."""
    # Check in-memory first
    if agent_name in _scaffold_registry:
        return _scaffold_registry[agent_name]
    
    # Try loading from database
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM agent_scaffolds WHERE agent_name = ?",
            (agent_name,)
        ).fetchone()
        
        if row:
            config = AgentConfig.model_validate_json(row["config"])
            scaffold = AgentScaffold(
                scaffold_id=row["scaffold_id"],
                config=config,
                state=LifecycleState(row["state"]),
                tasks_completed=row["tasks_completed"],
                tasks_failed=row["tasks_failed"],
                current_tasks=row["current_tasks"],
                error_count=row["error_count"],
                last_error=row["last_error"],
                avg_task_duration_ms=row["avg_task_duration"],
                initialized_at=datetime.fromisoformat(row["initialized_at"]),
                last_activity=datetime.fromisoformat(row["last_activity"]),
            )
            if row["last_heartbeat"]:
                scaffold.last_heartbeat = datetime.fromisoformat(row["last_heartbeat"])
            
            _scaffold_registry[agent_name] = scaffold
            return scaffold
    
    return None


def update_scaffold_state(agent_name: str, state: LifecycleState) -> None:
    """Update the lifecycle state of an agent."""
    now = datetime.now(timezone.utc)
    
    if agent_name in _scaffold_registry:
        _scaffold_registry[agent_name].state = state
        _scaffold_registry[agent_name].last_activity = now
    
    with _db() as conn:
        conn.execute(
            "UPDATE agent_scaffolds SET state = ?, last_activity = ? WHERE agent_name = ?",
            (state.value, now.isoformat(), agent_name)
        )
        conn.commit()


def record_task_completion(agent_name: str, success: bool, duration_ms: float) -> None:
    """Record a task completion for an agent."""
    now = datetime.now(timezone.utc)
    
    scaffold = get_agent_scaffold(agent_name)
    if scaffold:
        if success:
            scaffold.tasks_completed += 1
        else:
            scaffold.tasks_failed += 1
        
        # Update average duration
        total = scaffold.tasks_completed + scaffold.tasks_failed
        scaffold.avg_task_duration_ms = (
            (scaffold.avg_task_duration_ms * (total - 1) + duration_ms) / total
        )
        scaffold.last_activity = now
        scaffold.current_tasks = max(0, scaffold.current_tasks - 1)
    
    with _db() as conn:
        if success:
            conn.execute(
                """
                UPDATE agent_scaffolds 
                SET tasks_completed = tasks_completed + 1,
                    current_tasks = MAX(0, current_tasks - 1),
                    avg_task_duration = ?,
                    last_activity = ?
                WHERE agent_name = ?
                """,
                (scaffold.avg_task_duration_ms if scaffold else duration_ms, now.isoformat(), agent_name)
            )
        else:
            conn.execute(
                """
                UPDATE agent_scaffolds 
                SET tasks_failed = tasks_failed + 1,
                    current_tasks = MAX(0, current_tasks - 1),
                    error_count = error_count + 1,
                    last_activity = ?
                WHERE agent_name = ?
                """,
                (now.isoformat(), agent_name)
            )
        conn.commit()


def get_all_agents() -> list[AgentScaffold]:
    """Get all registered agents."""
    with _db() as conn:
        rows = conn.execute("SELECT agent_name FROM agent_scaffolds").fetchall()
        
        agents = []
        for row in rows:
            scaffold = get_agent_scaffold(row["agent_name"])
            if scaffold:
                agents.append(scaffold)
        
        return agents


def get_agents_by_capability(capability_type: CapabilityType) -> list[AgentScaffold]:
    """Get all agents that have a specific capability type."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT agent_name FROM capability_registry WHERE capability_type = ? AND enabled = 1",
            (capability_type.value,)
        ).fetchall()
        
        agents = []
        for row in rows:
            scaffold = get_agent_scaffold(row["agent_name"])
            if scaffold:
                agents.append(scaffold)
        
        return agents


def heartbeat(agent_name: str) -> None:
    """Record a heartbeat for an agent."""
    now = datetime.now(timezone.utc)
    
    if agent_name in _scaffold_registry:
        _scaffold_registry[agent_name].last_heartbeat = now
    
    with _db() as conn:
        conn.execute(
            "UPDATE agent_scaffolds SET last_heartbeat = ? WHERE agent_name = ?",
            (now.isoformat(), agent_name)
        )
        conn.commit()
