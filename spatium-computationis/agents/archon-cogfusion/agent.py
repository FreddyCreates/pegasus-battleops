"""
Agent: ARCHON Cognitive Fusion 🧠⚡
Role: Embeddable multi-mind cognitive brain for warfare-grade decision support.

ARCHON binds five specialized reasoning modes into one adaptive decision
substrate using dynamic cognitive fusion:
  - Hacker Mind:     Exploits, anomalies, asymmetric movement
  - General Mind:    Discipline, doctrine, escalation control
  - Strategist Mind: Long-range positioning, consequence evaluation
  - Pilot Mind:      Spatial awareness, real-time maneuver
  - AI Intelligence: Continuous oversight, pattern tracking

Glyph: 🧠⚡ (cognitive fusion)
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .fusion import (
    FusedDecision,
    FusionWeights,
    compute_dynamic_weights,
    fuse_signals,
)
from .minds import (
    MIND_PROFILES,
    MindProfile,
    MindSignal,
    MindType,
)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "archon.db"


def _init_archon_db() -> None:
    """Initialize the ARCHON decision log database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fusion_decisions (
                decision_id     TEXT PRIMARY KEY,
                host_id         TEXT,
                alert_level     REAL NOT NULL,
                urgency         REAL NOT NULL,
                decision_value  REAL NOT NULL,
                dominant_mind   TEXT NOT NULL,
                confidence      REAL NOT NULL,
                weights_json    TEXT NOT NULL,
                signals_json    TEXT NOT NULL,
                reasoning       TEXT,
                created_at      TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_fd_host ON fusion_decisions(host_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_fd_dominant ON fusion_decisions(dominant_mind)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_fd_created ON fusion_decisions(created_at)"
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS archon_hosts (
                host_id         TEXT PRIMARY KEY,
                host_name       TEXT NOT NULL,
                host_type       TEXT NOT NULL,
                description     TEXT,
                registered_at   TEXT NOT NULL,
                last_decision   TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ah_type ON archon_hosts(host_type)"
        )

        conn.commit()


_init_archon_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Host Management
# ---------------------------------------------------------------------------

class ArchonHost(BaseModel):
    """A system that embeds the ARCHON cognitive brain."""
    host_id: str
    host_name: str
    host_type: str  # e.g., "avatar", "cyber_defense", "swarm_node", "orbital_asset"
    description: str = ""
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_decision: datetime | None = None


def register_host(
    host_name: str,
    host_type: str,
    description: str = "",
) -> ArchonHost:
    """Register a new host system that embeds ARCHON."""
    host_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    host = ArchonHost(
        host_id=host_id,
        host_name=host_name,
        host_type=host_type,
        description=description,
        registered_at=now,
    )

    with _db() as conn:
        conn.execute(
            """
            INSERT INTO archon_hosts (host_id, host_name, host_type, description, registered_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (host_id, host_name, host_type, description, now.isoformat()),
        )
        conn.commit()

    return host


def get_host(host_id: str) -> ArchonHost | None:
    """Retrieve a registered host."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM archon_hosts WHERE host_id = ?", (host_id,)
        ).fetchone()
        if row:
            return ArchonHost(
                host_id=row["host_id"],
                host_name=row["host_name"],
                host_type=row["host_type"],
                description=row["description"] or "",
                registered_at=datetime.fromisoformat(row["registered_at"]),
                last_decision=(
                    datetime.fromisoformat(row["last_decision"])
                    if row["last_decision"]
                    else None
                ),
            )
    return None


# ---------------------------------------------------------------------------
# Core Decision Interface
# ---------------------------------------------------------------------------

def evaluate(
    signals: list[MindSignal],
    alert_level: float,
    host_id: str | None = None,
) -> FusedDecision:
    """Run cognitive fusion and produce a decision.

    This is the primary entry point for ARCHON. Supply signals from each mind
    along with the current alert level, and receive a fused decision.

    Args:
        signals: Signals from one or more minds.
        alert_level: Operational alert level (0.0 = calm, 1.0 = critical).
        host_id: Optional host identifier for audit trail.

    Returns:
        FusedDecision with weighted result and full audit data.
    """
    decision = fuse_signals(signals, alert_level)

    # Persist decision for audit trail
    decision_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    with _db() as conn:
        conn.execute(
            """
            INSERT INTO fusion_decisions (
                decision_id, host_id, alert_level, urgency,
                decision_value, dominant_mind, confidence,
                weights_json, signals_json, reasoning, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                host_id,
                alert_level,
                decision.weights_used.urgency,
                decision.decision_value,
                decision.dominant_mind.value,
                decision.confidence,
                decision.weights_used.model_dump_json(),
                json.dumps([s.model_dump() for s in decision.signals]),
                decision.reasoning,
                now.isoformat(),
            ),
        )

        if host_id:
            conn.execute(
                "UPDATE archon_hosts SET last_decision = ? WHERE host_id = ?",
                (now.isoformat(), host_id),
            )

        conn.commit()

    decision.metadata["decision_id"] = decision_id
    decision.metadata["timestamp"] = now.isoformat()
    return decision


def get_cognitive_posture(alert_level: float) -> FusionWeights:
    """Get the current cognitive posture (weight distribution) for an alert level.

    Useful for introspection and UI display without producing a decision.
    """
    return compute_dynamic_weights(alert_level)


def get_mind_profiles() -> dict[MindType, MindProfile]:
    """Return all five mind profiles."""
    return MIND_PROFILES.copy()


def get_decision_history(
    host_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve recent fusion decisions for audit.

    Args:
        host_id: Filter by host (None for all hosts).
        limit: Maximum number of decisions to return.

    Returns:
        List of decision records ordered by most recent first.
    """
    with _db() as conn:
        if host_id:
            rows = conn.execute(
                """
                SELECT * FROM fusion_decisions
                WHERE host_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (host_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM fusion_decisions
                ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]
