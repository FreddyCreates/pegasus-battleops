"""
⟲ ADAPTIVE RESPONSE ENGINE — Core decision-making logic

Receives classification results from the Organism Charter and selects
the optimal response strategy based on:
- Entity tier (Cooperative / Hostile / Shadow)
- Threat level
- Historical effectiveness data
- Current defense posture configuration
"""

from __future__ import annotations

import random
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ..organism_charter import ClassificationTier, EntityRole
from ..schemas import AdaptiveAction, ThreatLevel
from .strategies import (
    StrategyParams,
    StrategyResult,
    StrategyType,
    get_strategy,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class ResponseConfig(BaseModel):
    """
    Defense posture configuration.
    Controls how aggressive the adaptive response engine behaves.
    """
    # Posture: defensive, balanced, aggressive
    posture: str = "balanced"

    # Per-tier default strategies
    tier_a_strategy: StrategyType = StrategyType.OBSERVE
    tier_b_strategy: StrategyType = StrategyType.BLOCK
    tier_c_strategy: StrategyType = StrategyType.CHALLENGE

    # Threat level overrides
    critical_strategy: StrategyType = StrategyType.BLOCK
    high_strategy: StrategyType = StrategyType.TAR_PIT
    medium_strategy: StrategyType = StrategyType.CHALLENGE
    low_strategy: StrategyType = StrategyType.RATE_LIMIT

    # Confidence thresholds
    auto_respond_confidence: float = 0.7  # Auto-respond above this
    escalate_confidence: float = 0.5  # Escalate for review below this

    # Strategy parameters
    strategy_params: StrategyParams = Field(default_factory=StrategyParams)

    # Learning
    enable_ab_testing: bool = True
    exploration_rate: float = 0.1  # 10% of decisions try alternatives


# ---------------------------------------------------------------------------
# Response Decision
# ---------------------------------------------------------------------------

class ResponseDecision(BaseModel):
    """A decision made by the adaptive response engine."""
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])

    # Input context
    entity_ip: str
    entity_fingerprint: str | None = None
    classification_tier: ClassificationTier
    entity_role: EntityRole
    threat_level: ThreatLevel
    classification_confidence: float

    # Decision output
    selected_strategy: StrategyType
    action: AdaptiveAction
    reasoning: str
    decision_confidence: float

    # Execution result
    result: StrategyResult | None = None
    executed: bool = False

    # Metadata
    posture: str = "balanced"
    is_exploration: bool = False  # A/B test exploration decision
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "adaptive_response.db"


def _init_db() -> None:
    """Initialize the adaptive response database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS response_decisions (
                decision_id         TEXT PRIMARY KEY,
                entity_ip           TEXT NOT NULL,
                entity_fingerprint  TEXT,
                classification_tier TEXT NOT NULL,
                entity_role         TEXT NOT NULL,
                threat_level        TEXT NOT NULL,
                classification_confidence REAL,
                selected_strategy   TEXT NOT NULL,
                action              TEXT NOT NULL,
                reasoning           TEXT,
                decision_confidence REAL,
                posture             TEXT,
                is_exploration      BOOLEAN DEFAULT FALSE,
                executed            BOOLEAN DEFAULT FALSE,
                decided_at          TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rd_ip ON response_decisions(entity_ip)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rd_tier ON response_decisions(classification_tier)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rd_time ON response_decisions(decided_at)"
        )

        # Active blocks table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS active_blocks (
                block_id        TEXT PRIMARY KEY,
                entity_ip       TEXT NOT NULL,
                fingerprint     TEXT,
                strategy_type   TEXT NOT NULL,
                reason          TEXT,
                expires_at      TEXT,
                created_at      TEXT NOT NULL,
                is_active       BOOLEAN DEFAULT TRUE
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ab_ip ON active_blocks(entity_ip)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ab_active ON active_blocks(is_active)"
        )

        conn.commit()


_init_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Adaptive Response Engine
# ---------------------------------------------------------------------------

class AdaptiveResponseEngine:
    """
    ⟲ The Adaptive Response Engine.

    Core responsibilities:
    1. Select optimal strategy based on classification + threat level
    2. Execute the selected strategy
    3. Record decisions for effectiveness tracking
    4. Support A/B testing of response strategies
    """

    def __init__(self, config: ResponseConfig | None = None):
        self.config = config or ResponseConfig()

    def decide(
        self,
        entity_ip: str,
        classification_tier: ClassificationTier,
        entity_role: EntityRole,
        threat_level: ThreatLevel,
        classification_confidence: float,
        fingerprint_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> ResponseDecision:
        """
        Make a response decision based on classification results.

        Decision priority:
        1. Threat level override (critical/high overrides tier strategy)
        2. Tier-based default strategy
        3. Confidence gating (low confidence → observe)
        4. A/B exploration (small % try alternative strategies)
        """

        # Low confidence → fall back to observation
        if classification_confidence < self.config.escalate_confidence:
            strategy_type = StrategyType.OBSERVE
            reasoning = (
                f"Low classification confidence ({classification_confidence:.2f} "
                f"< {self.config.escalate_confidence}), defaulting to observation"
            )
            decision_confidence = 0.5
        # Threat level overrides
        elif threat_level == ThreatLevel.CRITICAL:
            strategy_type = self.config.critical_strategy
            reasoning = f"Critical threat level → {strategy_type.value}"
            decision_confidence = 0.95
        elif threat_level == ThreatLevel.HIGH:
            strategy_type = self.config.high_strategy
            reasoning = f"High threat level → {strategy_type.value}"
            decision_confidence = 0.85
        # Tier-based strategy
        elif classification_tier == ClassificationTier.TIER_A_COOPERATIVE:
            strategy_type = self.config.tier_a_strategy
            reasoning = f"Cooperative entity (Tier A) → {strategy_type.value}"
            decision_confidence = 0.8
        elif classification_tier == ClassificationTier.TIER_B_HOSTILE:
            strategy_type = self.config.tier_b_strategy
            reasoning = f"Hostile entity (Tier B) → {strategy_type.value}"
            decision_confidence = 0.85
        elif classification_tier == ClassificationTier.TIER_C_SHADOW:
            strategy_type = self.config.tier_c_strategy
            reasoning = f"Shadow entity (Tier C) → {strategy_type.value}"
            decision_confidence = 0.7
        else:
            # Unclassified
            strategy_type = StrategyType.OBSERVE
            reasoning = "Unclassified entity → observe"
            decision_confidence = 0.4

        # A/B exploration: occasionally try alternative strategies
        is_exploration = False
        if (
            self.config.enable_ab_testing
            and random.random() < self.config.exploration_rate
            and strategy_type != StrategyType.OBSERVE
        ):
            alternatives = [
                s for s in StrategyType
                if s != strategy_type and s != StrategyType.OBSERVE
            ]
            if alternatives:
                strategy_type = random.choice(alternatives)
                reasoning += f" [EXPLORATION: trying {strategy_type.value}]"
                is_exploration = True
                decision_confidence *= 0.7

        # Build strategy and get action
        strategy = get_strategy(strategy_type, self.config.strategy_params)

        decision = ResponseDecision(
            entity_ip=entity_ip,
            entity_fingerprint=fingerprint_id,
            classification_tier=classification_tier,
            entity_role=entity_role,
            threat_level=threat_level,
            classification_confidence=classification_confidence,
            selected_strategy=strategy_type,
            action=strategy.get_adaptive_action(),
            reasoning=reasoning,
            decision_confidence=decision_confidence,
            posture=self.config.posture,
            is_exploration=is_exploration,
        )

        return decision

    def execute_decision(
        self,
        decision: ResponseDecision,
        context: dict[str, Any] | None = None,
    ) -> ResponseDecision:
        """Execute a response decision and record the result."""
        strategy = get_strategy(
            decision.selected_strategy,
            self.config.strategy_params,
        )

        result = strategy.execute(
            ip_address=decision.entity_ip,
            fingerprint_id=decision.entity_fingerprint,
            context=context,
        )

        decision.result = result
        decision.executed = True

        # Persist the decision
        self._record_decision(decision)

        return decision

    def decide_and_execute(
        self,
        entity_ip: str,
        classification_tier: ClassificationTier,
        entity_role: EntityRole,
        threat_level: ThreatLevel,
        classification_confidence: float,
        fingerprint_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> ResponseDecision:
        """Convenience: make a decision and immediately execute it."""
        decision = self.decide(
            entity_ip=entity_ip,
            classification_tier=classification_tier,
            entity_role=entity_role,
            threat_level=threat_level,
            classification_confidence=classification_confidence,
            fingerprint_id=fingerprint_id,
            context=context,
        )
        return self.execute_decision(decision, context=context)

    def update_config(self, new_config: ResponseConfig) -> None:
        """Hot-reload configuration (e.g., change defense posture)."""
        self.config = new_config

    def get_active_blocks(self) -> list[dict[str, Any]]:
        """Return currently active blocks."""
        with _db() as conn:
            rows = conn.execute(
                "SELECT * FROM active_blocks WHERE is_active = TRUE"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_recent_decisions(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent response decisions."""
        with _db() as conn:
            rows = conn.execute(
                "SELECT * FROM response_decisions ORDER BY decided_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_stats(self) -> dict[str, Any]:
        """Get engine statistics."""
        with _db() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM response_decisions"
            ).fetchone()[0]
            by_strategy = conn.execute(
                """
                SELECT selected_strategy, COUNT(*) as count
                FROM response_decisions
                GROUP BY selected_strategy
                """
            ).fetchall()
            explorations = conn.execute(
                "SELECT COUNT(*) FROM response_decisions WHERE is_exploration = TRUE"
            ).fetchone()[0]

            return {
                "total_decisions": total,
                "by_strategy": {row[0]: row[1] for row in by_strategy},
                "exploration_count": explorations,
                "exploration_rate_actual": (
                    explorations / total if total > 0 else 0.0
                ),
                "current_posture": self.config.posture,
                "active_blocks": len(self.get_active_blocks()),
            }

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    def _record_decision(self, decision: ResponseDecision) -> None:
        """Persist a decision to the database."""
        with _db() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO response_decisions
                (decision_id, entity_ip, entity_fingerprint, classification_tier,
                 entity_role, threat_level, classification_confidence,
                 selected_strategy, action, reasoning, decision_confidence,
                 posture, is_exploration, executed, decided_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.decision_id,
                    decision.entity_ip,
                    decision.entity_fingerprint,
                    decision.classification_tier.value,
                    decision.entity_role.value,
                    decision.threat_level.value,
                    decision.classification_confidence,
                    decision.selected_strategy.value,
                    decision.action.value,
                    decision.reasoning,
                    decision.decision_confidence,
                    decision.posture,
                    decision.is_exploration,
                    decision.executed,
                    decision.decided_at.isoformat(),
                ),
            )
            conn.commit()


# ---------------------------------------------------------------------------
# Singleton Access
# ---------------------------------------------------------------------------

_engine_instance: AdaptiveResponseEngine | None = None


def get_engine(config: ResponseConfig | None = None) -> AdaptiveResponseEngine:
    """Get or create the singleton adaptive response engine."""
    global _engine_instance
    if _engine_instance is None or config is not None:
        _engine_instance = AdaptiveResponseEngine(config=config)
    return _engine_instance
