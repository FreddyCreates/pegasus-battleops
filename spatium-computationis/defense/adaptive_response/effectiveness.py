"""
◎ EFFECTIVENESS TRACKER — Measure and learn from response outcomes

Integrates with the Feedback Protocol to:
- Track whether each response strategy was effective
- Build per-strategy success rates
- Recommend strategy adjustments based on outcomes
- Generate effectiveness reports for the dashboard
"""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .strategies import StrategyType


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class EffectivenessRecord(BaseModel):
    """Tracks the effectiveness of a single response decision."""
    record_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    decision_id: str
    strategy_type: StrategyType
    entity_ip: str

    # Outcome
    effective: bool | None = None  # None = not yet evaluated
    outcome_signal: str = "pending"  # stopped, continued, escalated, evaded

    # Metrics
    requests_before: int = 0  # Entity requests in window before response
    requests_after: int = 0   # Entity requests in window after response
    reduction_pct: float = 0.0  # % reduction in activity

    # Timing
    response_applied_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    evaluated_at: datetime | None = None
    evaluation_window_minutes: int = 30


class EffectivenessReport(BaseModel):
    """Aggregated effectiveness metrics per strategy."""
    strategy_type: StrategyType
    period_hours: int = 24

    # Counts
    total_applications: int = 0
    evaluated: int = 0
    effective_count: int = 0
    ineffective_count: int = 0
    pending_count: int = 0

    # Rates
    effectiveness_rate: float = 0.0  # effective / evaluated
    avg_reduction_pct: float = 0.0

    # Trends
    trend: str = "stable"  # improving, stable, declining

    # Recommendation
    recommended_adjustment: str = "none"  # increase_use, decrease_use, none

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "adaptive_response.db"


def _init_effectiveness_tables() -> None:
    """Initialize effectiveness tracking tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS effectiveness_records (
                record_id           TEXT PRIMARY KEY,
                decision_id         TEXT NOT NULL,
                strategy_type       TEXT NOT NULL,
                entity_ip           TEXT NOT NULL,
                effective           BOOLEAN,
                outcome_signal      TEXT DEFAULT 'pending',
                requests_before     INTEGER DEFAULT 0,
                requests_after      INTEGER DEFAULT 0,
                reduction_pct       REAL DEFAULT 0.0,
                response_applied_at TEXT NOT NULL,
                evaluated_at        TEXT,
                evaluation_window_minutes INTEGER DEFAULT 30
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_er_strategy ON effectiveness_records(strategy_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_er_decision ON effectiveness_records(decision_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_er_time ON effectiveness_records(response_applied_at)"
        )
        conn.commit()


_init_effectiveness_tables()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Effectiveness Tracker
# ---------------------------------------------------------------------------

class EffectivenessTracker:
    """
    ◎ Tracks and evaluates response strategy effectiveness.

    Lifecycle:
    1. Response applied → create EffectivenessRecord (pending)
    2. Wait evaluation window
    3. Measure entity behavior after response
    4. Mark as effective/ineffective
    5. Update strategy-level metrics
    """

    def __init__(self, evaluation_window_minutes: int = 30):
        self.evaluation_window_minutes = evaluation_window_minutes

    def record_response_applied(
        self,
        decision_id: str,
        strategy_type: StrategyType,
        entity_ip: str,
        requests_before: int = 0,
    ) -> EffectivenessRecord:
        """Record that a response strategy was applied."""
        record = EffectivenessRecord(
            decision_id=decision_id,
            strategy_type=strategy_type,
            entity_ip=entity_ip,
            requests_before=requests_before,
            evaluation_window_minutes=self.evaluation_window_minutes,
        )

        with _db() as conn:
            conn.execute(
                """
                INSERT INTO effectiveness_records
                (record_id, decision_id, strategy_type, entity_ip,
                 effective, outcome_signal, requests_before, requests_after,
                 reduction_pct, response_applied_at, evaluated_at,
                 evaluation_window_minutes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.record_id,
                    record.decision_id,
                    record.strategy_type.value,
                    record.entity_ip,
                    record.effective,
                    record.outcome_signal,
                    record.requests_before,
                    record.requests_after,
                    record.reduction_pct,
                    record.response_applied_at.isoformat(),
                    None,
                    record.evaluation_window_minutes,
                ),
            )
            conn.commit()

        return record

    def evaluate_response(
        self,
        record_id: str,
        requests_after: int,
        outcome_signal: str = "auto",
    ) -> EffectivenessRecord | None:
        """
        Evaluate whether a response was effective.

        Effectiveness heuristics:
        - "stopped": entity stopped all activity → effective
        - "reduced": >50% reduction in requests → effective
        - "continued": <50% reduction → ineffective
        - "escalated": entity increased activity → ineffective
        - "evaded": entity changed fingerprint → partially effective
        """
        now = datetime.now(timezone.utc)

        with _db() as conn:
            row = conn.execute(
                "SELECT * FROM effectiveness_records WHERE record_id = ?",
                (record_id,),
            ).fetchone()

            if row is None:
                return None

            requests_before = row["requests_before"]

            # Calculate reduction
            if requests_before > 0:
                reduction_pct = (
                    (requests_before - requests_after) / requests_before
                ) * 100
            else:
                reduction_pct = 100.0 if requests_after == 0 else -100.0

            # Determine effectiveness
            if outcome_signal == "auto":
                if requests_after == 0:
                    outcome_signal = "stopped"
                elif reduction_pct >= 50:
                    outcome_signal = "reduced"
                elif reduction_pct < 0:
                    outcome_signal = "escalated"
                else:
                    outcome_signal = "continued"

            effective = outcome_signal in ("stopped", "reduced")

            # Update record
            conn.execute(
                """
                UPDATE effectiveness_records
                SET effective = ?, outcome_signal = ?, requests_after = ?,
                    reduction_pct = ?, evaluated_at = ?
                WHERE record_id = ?
                """,
                (
                    effective,
                    outcome_signal,
                    requests_after,
                    reduction_pct,
                    now.isoformat(),
                    record_id,
                ),
            )
            conn.commit()

            return EffectivenessRecord(
                record_id=record_id,
                decision_id=row["decision_id"],
                strategy_type=StrategyType(row["strategy_type"]),
                entity_ip=row["entity_ip"],
                effective=effective,
                outcome_signal=outcome_signal,
                requests_before=requests_before,
                requests_after=requests_after,
                reduction_pct=reduction_pct,
                response_applied_at=datetime.fromisoformat(row["response_applied_at"]),
                evaluated_at=now,
                evaluation_window_minutes=row["evaluation_window_minutes"],
            )

    def get_strategy_report(
        self,
        strategy_type: StrategyType,
        period_hours: int = 24,
    ) -> EffectivenessReport:
        """Generate an effectiveness report for a specific strategy."""
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=period_hours)
        ).isoformat()

        with _db() as conn:
            rows = conn.execute(
                """
                SELECT effective, outcome_signal, reduction_pct
                FROM effectiveness_records
                WHERE strategy_type = ? AND response_applied_at >= ?
                """,
                (strategy_type.value, cutoff),
            ).fetchall()

        total = len(rows)
        evaluated = [r for r in rows if r["effective"] is not None]
        effective_count = sum(1 for r in evaluated if r["effective"])
        ineffective_count = len(evaluated) - effective_count
        pending_count = total - len(evaluated)

        effectiveness_rate = (
            effective_count / len(evaluated) if evaluated else 0.0
        )

        avg_reduction = (
            sum(r["reduction_pct"] for r in evaluated) / len(evaluated)
            if evaluated else 0.0
        )

        # Simple trend: compare first half vs second half
        trend = "stable"
        if len(evaluated) >= 4:
            mid = len(evaluated) // 2
            first_half_rate = sum(
                1 for r in evaluated[:mid] if r["effective"]
            ) / mid
            second_half_rate = sum(
                1 for r in evaluated[mid:] if r["effective"]
            ) / (len(evaluated) - mid)
            if second_half_rate > first_half_rate + 0.1:
                trend = "improving"
            elif second_half_rate < first_half_rate - 0.1:
                trend = "declining"

        # Recommendation
        if effectiveness_rate >= 0.8:
            recommended_adjustment = "increase_use"
        elif effectiveness_rate <= 0.3 and len(evaluated) >= 5:
            recommended_adjustment = "decrease_use"
        else:
            recommended_adjustment = "none"

        return EffectivenessReport(
            strategy_type=strategy_type,
            period_hours=period_hours,
            total_applications=total,
            evaluated=len(evaluated),
            effective_count=effective_count,
            ineffective_count=ineffective_count,
            pending_count=pending_count,
            effectiveness_rate=effectiveness_rate,
            avg_reduction_pct=avg_reduction,
            trend=trend,
            recommended_adjustment=recommended_adjustment,
        )

    def get_all_strategy_reports(
        self, period_hours: int = 24
    ) -> list[EffectivenessReport]:
        """Generate reports for all strategy types."""
        return [
            self.get_strategy_report(st, period_hours)
            for st in StrategyType
        ]

    def get_pending_evaluations(self) -> list[dict[str, Any]]:
        """Get records that need evaluation (past their window)."""
        now = datetime.now(timezone.utc)

        with _db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM effectiveness_records
                WHERE effective IS NULL
                ORDER BY response_applied_at ASC
                """
            ).fetchall()

        pending = []
        for row in rows:
            applied_at = datetime.fromisoformat(row["response_applied_at"])
            window_end = applied_at + timedelta(
                minutes=row["evaluation_window_minutes"]
            )
            if now >= window_end:
                pending.append(dict(row))

        return pending


# ---------------------------------------------------------------------------
# Singleton Access
# ---------------------------------------------------------------------------

_tracker_instance: EffectivenessTracker | None = None


def get_tracker(
    evaluation_window_minutes: int = 30,
) -> EffectivenessTracker:
    """Get or create the singleton effectiveness tracker."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = EffectivenessTracker(
            evaluation_window_minutes=evaluation_window_minutes
        )
    return _tracker_instance
