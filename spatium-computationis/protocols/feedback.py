"""
Protocol VI: Feedback  ⟲
Meaning: the system learns from outcomes and adjusts.

The Feedback Protocol implements closed-loop learning:
1. Captures outcomes from actions (success/failure/partial)
2. Correlates outcomes with decisions made
3. Adjusts confidence scores and routing weights
4. Enables agents to learn from experience

Glyphs:
  ⟲ Feedback  — outcome returns to improve future decisions
  ⇡ Amplify   — successful patterns get reinforced
  ⇣ Dampen    — failed patterns get reduced weight
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
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Outcome Types
# ---------------------------------------------------------------------------

class OutcomeType(str, Enum):
    """Classification of action outcomes."""
    SUCCESS = "success"           # Action achieved desired result
    PARTIAL = "partial"           # Partially successful
    FAILURE = "failure"           # Action failed
    TIMEOUT = "timeout"           # Action timed out
    REJECTED = "rejected"         # Output rejected by human
    APPROVED = "approved"         # Output approved by human
    CORRECTED = "corrected"       # Output corrected by human
    UNKNOWN = "unknown"           # Outcome not yet determined


class LearningSignal(str, Enum):
    """Type of learning signal to propagate."""
    REINFORCE = "reinforce"       # This pattern worked, do more
    PENALIZE = "penalize"         # This pattern failed, do less
    NEUTRAL = "neutral"           # No strong signal either way
    EXPLORE = "explore"           # Try alternative approaches


# ---------------------------------------------------------------------------
# Feedback Models
# ---------------------------------------------------------------------------

class OutcomeRecord(BaseModel):
    """Records the outcome of an action."""
    outcome_id: str
    action_id: str
    project_id: str | None = None
    agent: str
    action_type: str
    
    # Outcome classification
    outcome_type: OutcomeType
    quality_score: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Details
    human_feedback: str | None = None
    corrections_made: dict[str, Any] = Field(default_factory=dict)
    time_to_outcome_seconds: float | None = None
    
    # Learning signals
    learning_signal: LearningSignal = LearningSignal.NEUTRAL
    confidence_adjustment: float = 0.0  # -1.0 to +1.0
    
    # Context for learning
    input_features: dict[str, Any] = Field(default_factory=dict)
    decision_features: dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentPerformance(BaseModel):
    """Aggregated performance metrics for an agent."""
    agent: str
    period_hours: int = 24
    
    # Counts
    total_actions: int = 0
    successes: int = 0
    failures: int = 0
    partial: int = 0
    
    # Rates
    success_rate: float = 0.0
    approval_rate: float = 0.0
    correction_rate: float = 0.0
    
    # Quality
    avg_quality_score: float = 0.5
    quality_trend: str = "stable"  # improving, stable, declining
    
    # Timing
    avg_time_to_outcome_seconds: float | None = None
    
    # Learning
    confidence_delta: float = 0.0  # Net change in confidence
    
    # Timestamps
    period_start: datetime
    period_end: datetime


class RoutingWeight(BaseModel):
    """Adaptive weight for routing decisions."""
    agent: str
    action_type: str
    
    # Current weight (0.0 to 2.0, 1.0 = neutral)
    weight: float = 1.0
    
    # History
    initial_weight: float = 1.0
    adjustments: list[tuple[datetime, float]] = Field(default_factory=list)
    
    # Bounds
    min_weight: float = 0.1
    max_weight: float = 2.0
    
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent / "field" / "feedback.db"


def _init_feedback_db() -> None:
    """Initialize the feedback database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Outcome records
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outcome_records (
                outcome_id      TEXT PRIMARY KEY,
                action_id       TEXT NOT NULL,
                project_id      TEXT,
                agent           TEXT NOT NULL,
                action_type     TEXT NOT NULL,
                outcome_type    TEXT NOT NULL,
                quality_score   REAL DEFAULT 0.5,
                human_feedback  TEXT,
                corrections     TEXT,
                time_to_outcome REAL,
                learning_signal TEXT,
                confidence_adj  REAL DEFAULT 0.0,
                input_features  TEXT,
                decision_features TEXT,
                recorded_at     TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_or_agent ON outcome_records(agent)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_or_action ON outcome_records(action_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_or_type ON outcome_records(outcome_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_or_recorded ON outcome_records(recorded_at)")
        
        # Routing weights
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS routing_weights (
                agent           TEXT NOT NULL,
                action_type     TEXT NOT NULL,
                weight          REAL DEFAULT 1.0,
                initial_weight  REAL DEFAULT 1.0,
                adjustments     TEXT,
                last_updated    TEXT NOT NULL,
                PRIMARY KEY (agent, action_type)
            )
            """
        )
        
        # Learning history
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_events (
                event_id        TEXT PRIMARY KEY,
                agent           TEXT NOT NULL,
                signal_type     TEXT NOT NULL,
                magnitude       REAL NOT NULL,
                reason          TEXT,
                features        TEXT,
                created_at      TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_le_agent ON learning_events(agent)")
        
        conn.commit()


_init_feedback_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Outcome Recording
# ---------------------------------------------------------------------------

def record_outcome(
    action_id: str,
    agent: str,
    action_type: str,
    outcome_type: OutcomeType,
    quality_score: float = 0.5,
    project_id: str | None = None,
    human_feedback: str | None = None,
    corrections: dict[str, Any] | None = None,
    time_to_outcome: float | None = None,
    input_features: dict[str, Any] | None = None,
    decision_features: dict[str, Any] | None = None,
) -> OutcomeRecord:
    """Record an action outcome for learning."""
    outcome_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Determine learning signal based on outcome
    if outcome_type == OutcomeType.SUCCESS:
        signal = LearningSignal.REINFORCE
        conf_adj = 0.05 * quality_score
    elif outcome_type == OutcomeType.APPROVED:
        signal = LearningSignal.REINFORCE
        conf_adj = 0.1 * quality_score
    elif outcome_type == OutcomeType.FAILURE:
        signal = LearningSignal.PENALIZE
        conf_adj = -0.1
    elif outcome_type == OutcomeType.REJECTED:
        signal = LearningSignal.PENALIZE
        conf_adj = -0.15
    elif outcome_type == OutcomeType.CORRECTED:
        signal = LearningSignal.EXPLORE
        conf_adj = -0.05 * (1 - quality_score)
    elif outcome_type == OutcomeType.PARTIAL:
        signal = LearningSignal.NEUTRAL
        conf_adj = 0.02 * (quality_score - 0.5)
    else:
        signal = LearningSignal.NEUTRAL
        conf_adj = 0.0
    
    record = OutcomeRecord(
        outcome_id=outcome_id,
        action_id=action_id,
        project_id=project_id,
        agent=agent,
        action_type=action_type,
        outcome_type=outcome_type,
        quality_score=quality_score,
        human_feedback=human_feedback,
        corrections_made=corrections or {},
        time_to_outcome_seconds=time_to_outcome,
        learning_signal=signal,
        confidence_adjustment=conf_adj,
        input_features=input_features or {},
        decision_features=decision_features or {},
        recorded_at=now,
    )
    
    # Store in database
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO outcome_records (
                outcome_id, action_id, project_id, agent, action_type,
                outcome_type, quality_score, human_feedback, corrections,
                time_to_outcome, learning_signal, confidence_adj,
                input_features, decision_features, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                outcome_id, action_id, project_id, agent, action_type,
                outcome_type.value, quality_score, human_feedback,
                json.dumps(corrections or {}), time_to_outcome,
                signal.value, conf_adj,
                json.dumps(input_features or {}),
                json.dumps(decision_features or {}),
                now.isoformat()
            )
        )
        conn.commit()
    
    # Propagate learning signal
    _propagate_learning(record)
    
    return record


def _propagate_learning(outcome: OutcomeRecord) -> None:
    """Propagate learning signal to routing weights."""
    if outcome.learning_signal == LearningSignal.NEUTRAL:
        return
    
    adjustment = outcome.confidence_adjustment
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        # Get current weight
        row = conn.execute(
            "SELECT * FROM routing_weights WHERE agent = ? AND action_type = ?",
            (outcome.agent, outcome.action_type)
        ).fetchone()
        
        if row:
            current_weight = row["weight"]
            new_weight = max(0.1, min(2.0, current_weight + adjustment))
            
            # Load and update adjustments history
            adjustments = json.loads(row["adjustments"] or "[]")
            adjustments.append([now.isoformat(), adjustment])
            adjustments = adjustments[-100:]  # Keep last 100
            
            conn.execute(
                "UPDATE routing_weights SET weight = ?, adjustments = ?, last_updated = ? WHERE agent = ? AND action_type = ?",
                (new_weight, json.dumps(adjustments), now.isoformat(), outcome.agent, outcome.action_type)
            )
        else:
            new_weight = 1.0 + adjustment
            adjustments = [[now.isoformat(), adjustment]]
            
            conn.execute(
                "INSERT INTO routing_weights (agent, action_type, weight, initial_weight, adjustments, last_updated) VALUES (?, ?, ?, ?, ?, ?)",
                (outcome.agent, outcome.action_type, new_weight, 1.0, json.dumps(adjustments), now.isoformat())
            )
        
        # Log learning event
        conn.execute(
            "INSERT INTO learning_events (event_id, agent, signal_type, magnitude, reason, features, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                outcome.agent,
                outcome.learning_signal.value,
                adjustment,
                f"Outcome: {outcome.outcome_type.value}, Quality: {outcome.quality_score}",
                json.dumps(outcome.input_features),
                now.isoformat()
            )
        )
        
        conn.commit()


# ---------------------------------------------------------------------------
# Querying Performance
# ---------------------------------------------------------------------------

def get_agent_performance(agent: str, hours: int = 24) -> AgentPerformance:
    """Get aggregated performance metrics for an agent."""
    from datetime import timedelta
    
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(hours=hours)
    
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM outcome_records WHERE agent = ? AND recorded_at >= ?",
            (agent, period_start.isoformat())
        ).fetchall()
        
        total = len(rows)
        successes = sum(1 for r in rows if r["outcome_type"] in ("success", "approved"))
        failures = sum(1 for r in rows if r["outcome_type"] in ("failure", "rejected"))
        partial = sum(1 for r in rows if r["outcome_type"] == "partial")
        approved = sum(1 for r in rows if r["outcome_type"] == "approved")
        corrected = sum(1 for r in rows if r["outcome_type"] == "corrected")
        
        avg_quality = sum(r["quality_score"] for r in rows) / total if total else 0.5
        avg_time = None
        time_rows = [r["time_to_outcome"] for r in rows if r["time_to_outcome"]]
        if time_rows:
            avg_time = sum(time_rows) / len(time_rows)
        
        confidence_delta = sum(r["confidence_adj"] for r in rows)
        
        # Determine trend
        if total < 10:
            trend = "insufficient_data"
        elif confidence_delta > 0.1:
            trend = "improving"
        elif confidence_delta < -0.1:
            trend = "declining"
        else:
            trend = "stable"
        
        return AgentPerformance(
            agent=agent,
            period_hours=hours,
            total_actions=total,
            successes=successes,
            failures=failures,
            partial=partial,
            success_rate=successes / total if total else 0,
            approval_rate=approved / total if total else 0,
            correction_rate=corrected / total if total else 0,
            avg_quality_score=avg_quality,
            quality_trend=trend,
            avg_time_to_outcome_seconds=avg_time,
            confidence_delta=confidence_delta,
            period_start=period_start,
            period_end=now,
        )


def get_routing_weight(agent: str, action_type: str) -> float:
    """Get the current routing weight for an agent/action pair."""
    with _db() as conn:
        row = conn.execute(
            "SELECT weight FROM routing_weights WHERE agent = ? AND action_type = ?",
            (agent, action_type)
        ).fetchone()
        
        return row["weight"] if row else 1.0


def get_all_routing_weights() -> list[RoutingWeight]:
    """Get all routing weights."""
    with _db() as conn:
        rows = conn.execute("SELECT * FROM routing_weights").fetchall()
        
        return [
            RoutingWeight(
                agent=row["agent"],
                action_type=row["action_type"],
                weight=row["weight"],
                initial_weight=row["initial_weight"],
                adjustments=[
                    (datetime.fromisoformat(a[0]), a[1])
                    for a in json.loads(row["adjustments"] or "[]")
                ],
                last_updated=datetime.fromisoformat(row["last_updated"]),
            )
            for row in rows
        ]


# ---------------------------------------------------------------------------
# Feedback Loop Integration
# ---------------------------------------------------------------------------

@dataclass
class FeedbackLoopResult:
    """Result of running the feedback loop."""
    outcomes_processed: int = 0
    weights_adjusted: int = 0
    learning_events: int = 0
    agents_improved: list[str] = field(default_factory=list)
    agents_degraded: list[str] = field(default_factory=list)


async def run_feedback_loop(hours: int = 1) -> FeedbackLoopResult:
    """
    Run the feedback loop to process recent outcomes and adjust weights.
    
    This should be called periodically (e.g., hourly) to:
    1. Aggregate recent outcomes
    2. Identify patterns
    3. Adjust routing weights
    4. Log learning events
    """
    from datetime import timedelta
    
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(hours=hours)
    
    result = FeedbackLoopResult()
    
    with _db() as conn:
        # Get unique agents with recent outcomes
        agents = conn.execute(
            "SELECT DISTINCT agent FROM outcome_records WHERE recorded_at >= ?",
            (period_start.isoformat(),)
        ).fetchall()
        
        for agent_row in agents:
            agent = agent_row["agent"]
            perf = get_agent_performance(agent, hours=hours)
            
            result.outcomes_processed += perf.total_actions
            
            if perf.quality_trend == "improving":
                result.agents_improved.append(agent)
            elif perf.quality_trend == "declining":
                result.agents_degraded.append(agent)
        
        # Count weight adjustments
        weights = conn.execute(
            "SELECT COUNT(*) as count FROM routing_weights WHERE last_updated >= ?",
            (period_start.isoformat(),)
        ).fetchone()
        result.weights_adjusted = weights["count"]
        
        # Count learning events
        events = conn.execute(
            "SELECT COUNT(*) as count FROM learning_events WHERE created_at >= ?",
            (period_start.isoformat(),)
        ).fetchone()
        result.learning_events = events["count"]
    
    return result
