"""
Agent: ARCHON 🧠⚡ — Alpha Mind Warfare SDK
Codename: ARCHON
Role: Embeddable multi-mind cognitive brain for warfare-grade decision support.

Five Minds. One Brain. Infinite Hosts.

ARCHON is the warfare-grade expression of Alpha Mind: an embeddable cognitive
brain that fuses multiple specialized reasoning modes into one deployable
intelligence layer.

The same embedded brain can support:
  - Digital avatar
  - Cyber defense platform
  - Swarm node
  - Infrastructure guardian
  - Autonomous system
  - Orbital asset

The host changes. The cognitive fusion layer remains.

Integration with Spatium Computationis:
  - Uses Nova Sovereign as intelligence backend for mind reasoning
  - Consumes Organism Charter classification data as input signals
  - Respects Governance Hierarchy for all decisions
  - Reports outcomes to Feedback Protocol for closed-loop learning
  - Drives the Defense System adaptive response posture

ITSNOTAILABS | Alpha Mind Concept
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
    PostureTransition,
    compute_dynamic_weights,
    fuse_signals,
)
from .minds import (
    MIND_PROFILES,
    MindProfile,
    MindSignal,
    MindType,
    PostureMode,
    EscalationLevel,
)
from .cortex import (
    CortexState,
    SituationalAwareness,
    get_situational_awareness,
    store_memory,
    register_threat,
    record_posture_transition,
    record_signal_frequency,
    prune_expired,
)
from .doctrine import (
    DoctrineEngine,
    DoctrineGateOutput,
    GateResult,
    ARCHON_DOCTRINE,
)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "archon.db"


def _ensure_db() -> None:
    """Ensure the archon decision tables exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fusion_decisions (
                decision_id     TEXT PRIMARY KEY,
                host_id         TEXT,
                alert_level     REAL NOT NULL,
                urgency         REAL NOT NULL,
                decision_value  REAL NOT NULL,
                dominant_mind   TEXT NOT NULL,
                confidence      REAL NOT NULL,
                posture         TEXT NOT NULL,
                escalation      TEXT NOT NULL,
                has_contention  INTEGER DEFAULT 0,
                requires_human  INTEGER DEFAULT 0,
                doctrine_gate   TEXT,
                weights_json    TEXT NOT NULL,
                signals_json    TEXT NOT NULL,
                reasoning       TEXT,
                created_at      TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fd_host ON fusion_decisions(host_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fd_dominant ON fusion_decisions(dominant_mind)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fd_created ON fusion_decisions(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fd_posture ON fusion_decisions(posture)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fd_escalation ON fusion_decisions(escalation)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS archon_hosts (
                host_id         TEXT PRIMARY KEY,
                host_name       TEXT NOT NULL,
                host_type       TEXT NOT NULL,
                description     TEXT,
                config_json     TEXT DEFAULT '{}',
                registered_at   TEXT NOT NULL,
                last_decision   TEXT,
                decision_count  INTEGER DEFAULT 0,
                current_posture TEXT DEFAULT 'patrol'
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ah_type ON archon_hosts(host_type)")

        conn.commit()


_ensure_db()


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
    """A system that embeds the ARCHON cognitive brain.

    The host changes. The cognitive fusion layer remains.
    Any system can embed ARCHON by registering as a host.
    """
    host_id: str
    host_name: str
    host_type: str  # "avatar", "cyber_defense", "swarm_node", "infrastructure", "orbital_asset"
    description: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_decision: datetime | None = None
    decision_count: int = 0
    current_posture: PostureMode = PostureMode.PATROL


def register_host(
    host_name: str,
    host_type: str,
    description: str = "",
    config: dict[str, Any] | None = None,
) -> ArchonHost:
    """Register a new host system that embeds ARCHON.

    The same ARCHON brain can be embedded in any host:
    - Digital avatar
    - Cyber defense platform
    - Swarm node
    - Infrastructure guardian
    - Autonomous system
    - Orbital asset
    """
    host_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    host = ArchonHost(
        host_id=host_id,
        host_name=host_name,
        host_type=host_type,
        description=description,
        config=config or {},
        registered_at=now,
    )

    with _db() as conn:
        conn.execute("""
            INSERT INTO archon_hosts
            (host_id, host_name, host_type, description, config_json, registered_at, current_posture)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            host_id, host_name, host_type, description,
            json.dumps(config or {}), now.isoformat(), PostureMode.PATROL.value,
        ))
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
                config=json.loads(row["config_json"] or "{}"),
                registered_at=datetime.fromisoformat(row["registered_at"]),
                last_decision=(
                    datetime.fromisoformat(row["last_decision"])
                    if row["last_decision"] else None
                ),
                decision_count=row["decision_count"],
                current_posture=PostureMode(row["current_posture"]),
            )
    return None


# ---------------------------------------------------------------------------
# ARCHON Engine — The Full Cognitive Runtime
# ---------------------------------------------------------------------------

class ArchonEngine:
    """The complete ARCHON cognitive runtime.

    This is the main interface for running ARCHON. It orchestrates:
    1. Situational awareness (cortex state)
    2. Signal generation (five-mind reasoning via Nova Sovereign)
    3. Cognitive fusion (dynamic weighting + interaction dynamics)
    4. Doctrine gate (governance compliance)
    5. Feedback recording (closed-loop learning)
    6. Posture management (state transitions)

    Usage:
        engine = create_engine(host_id="...")
        decision = await engine.think(input_data)
    """

    def __init__(
        self,
        host_id: str | None = None,
        doctrine: DoctrineEngine | None = None,
    ):
        self.host_id = host_id
        self.doctrine = doctrine or DoctrineEngine()
        self._current_posture = PostureMode.PATROL

        # Load host posture if available
        if host_id:
            host = get_host(host_id)
            if host:
                self._current_posture = host.current_posture

    @property
    def posture(self) -> PostureMode:
        return self._current_posture

    async def think(
        self,
        input_data: dict[str, Any],
        alert_level: float | None = None,
    ) -> FusedDecision:
        """Run the full ARCHON cognitive cycle.

        This is the primary entry point. It:
        1. Gets situational awareness from cortex
        2. Runs all five minds on the input (via Nova Sovereign)
        3. Performs cognitive fusion
        4. Passes through doctrine gate
        5. Records decision and updates cortex
        6. Returns the fused decision

        Args:
            input_data: The context/stimulus to reason about
            alert_level: Override alert level (None = compute from organism state)

        Returns:
            FusedDecision with full cognitive artifacts and audit trail
        """
        from .nova_reasoning import run_full_cognition
        from .organism_bridge import compute_organism_alert_level

        # Step 1: Situational awareness
        awareness = get_situational_awareness()

        # Compute alert level
        if alert_level is None:
            alert_level = compute_organism_alert_level()

        # Step 2: Five-mind reasoning
        signals = await run_full_cognition(input_data, awareness)

        # Step 3: Cognitive fusion
        decision = fuse_signals(signals, alert_level, self._current_posture)

        # Step 4: Doctrine gate
        mind_signal_map = {s.mind_type: s.confidence for s in signals}
        max_threat_severity = max(
            (t.severity for t in awareness.active_threats), default=0.0
        )
        doctrine_output = self.doctrine.evaluate_decision(
            decision_id=str(uuid.uuid4()),
            recommended_escalation=decision.recommended_escalation,
            current_posture=self._current_posture,
            confidence=decision.confidence,
            has_contention=decision.has_contention,
            mind_signals=mind_signal_map,
            threat_severity=max_threat_severity,
        )

        # Apply doctrine modifications
        decision.governance_compliant = doctrine_output.gate_result == GateResult.PASS
        decision.governance_notes = doctrine_output.violations
        decision.requires_human_review = doctrine_output.human_review_required

        if doctrine_output.modified_escalation:
            decision.recommended_escalation = doctrine_output.modified_escalation

        # Step 5: Posture management
        if decision.posture_transition:
            new_posture = decision.recommended_posture
            record_posture_transition(
                from_posture=self._current_posture,
                to_posture=new_posture,
                trigger_reason=decision.posture_transition.trigger,
                triggered_by=decision.posture_transition.triggered_by,
                alert_level=alert_level,
            )
            self._current_posture = new_posture

            # Update host
            if self.host_id:
                with _db() as conn:
                    conn.execute(
                        "UPDATE archon_hosts SET current_posture = ? WHERE host_id = ?",
                        (new_posture.value, self.host_id),
                    )
                    conn.commit()

        # Step 6: Record decision
        decision_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        with _db() as conn:
            conn.execute("""
                INSERT INTO fusion_decisions
                (decision_id, host_id, alert_level, urgency, decision_value,
                 dominant_mind, confidence, posture, escalation, has_contention,
                 requires_human, doctrine_gate, weights_json, signals_json,
                 reasoning, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision_id, self.host_id, alert_level,
                decision.weights_used.urgency, decision.decision_value,
                decision.dominant_mind.value, decision.confidence,
                self._current_posture.value,
                decision.recommended_escalation.value,
                1 if decision.has_contention else 0,
                1 if decision.requires_human_review else 0,
                doctrine_output.gate_result.value,
                decision.weights_used.model_dump_json(),
                json.dumps([s.model_dump() for s in decision.signals]),
                decision.reasoning, now.isoformat(),
            ))

            if self.host_id:
                conn.execute("""
                    UPDATE archon_hosts
                    SET last_decision = ?, decision_count = decision_count + 1
                    WHERE host_id = ?
                """, (now.isoformat(), self.host_id))

            conn.commit()

        # Step 7: Record signals to cortex
        for signal in signals:
            record_signal_frequency(
                signal.mind_type, signal.signal_value, signal.confidence,
                has_threat=bool(signal.threat_vectors_detected),
            )
            if signal.threat_vectors_detected:
                for tv in signal.threat_vectors_detected:
                    register_threat(
                        vector=tv,
                        severity=abs(signal.signal_value),
                        confidence=signal.confidence,
                        mind_attribution=signal.mind_type,
                    )

        # Store the decision itself as a memory
        store_memory(
            memory_type="decision",
            content=(
                f"Decision: value={decision.decision_value:.3f}, "
                f"dominant={decision.dominant_mind.value}, "
                f"escalation={decision.recommended_escalation.value}, "
                f"posture={self._current_posture.value}"
            ),
            signal_value=decision.decision_value,
            confidence=decision.confidence,
        )

        decision.metadata["decision_id"] = decision_id
        decision.metadata["timestamp"] = now.isoformat()
        decision.metadata["doctrine_gate"] = doctrine_output.gate_result.value
        decision.metadata["doctrine_audit_id"] = doctrine_output.audit_id

        return decision

    async def evaluate_organism_event(
        self,
        envelope_data: dict[str, Any],
        tier: str,
        role: str,
        route: str,
        reason: str,
        confidence: float,
    ) -> FusedDecision:
        """Evaluate an organism classification event through the full ARCHON cycle.

        This is the primary integration point with the Organism Charter.
        When the organism classifies an entity, it can optionally pass it
        through ARCHON for deep cognitive evaluation.
        """
        from .organism_bridge import (
            process_request_envelope,
            ingest_classification_event,
        )

        # Ingest into cortex
        ingest_classification_event(
            envelope_data, tier, role, route, reason, confidence
        )

        # Build ARCHON context
        input_data = process_request_envelope(
            envelope_data,
            classification_result={
                "tier": tier, "role": role, "route": route,
                "reason": reason, "confidence": confidence,
            },
        )

        # Run full cognitive cycle
        return await self.think(input_data)

    def get_cortex_state(self) -> CortexState:
        """Get the full cortex state for diagnostics."""
        awareness = get_situational_awareness()
        from .cortex import recall_memories
        all_memories = recall_memories(limit=100, include_expired=True)

        return CortexState(
            awareness=awareness,
            threat_map_size=len(awareness.active_threats),
            memory_size=len(all_memories),
            oldest_memory=min((m.created_at for m in all_memories), default=None),
            newest_memory=max((m.created_at for m in all_memories), default=None),
        )

    def maintenance(self) -> dict[str, int]:
        """Run cortex maintenance: prune expired entries."""
        pruned = prune_expired()
        return {"pruned": pruned}


# ---------------------------------------------------------------------------
# Factory and Convenience Functions
# ---------------------------------------------------------------------------

def create_engine(
    host_id: str | None = None,
    doctrine: DoctrineEngine | None = None,
) -> ArchonEngine:
    """Create an ARCHON engine instance.

    Args:
        host_id: Optional host to bind to
        doctrine: Optional custom doctrine engine

    Returns:
        ArchonEngine ready for cognition
    """
    return ArchonEngine(host_id=host_id, doctrine=doctrine)


def evaluate(
    signals: list[MindSignal],
    alert_level: float,
    host_id: str | None = None,
    posture: PostureMode = PostureMode.PATROL,
) -> FusedDecision:
    """Synchronous fusion evaluation (without Nova Sovereign reasoning).

    Use this for direct signal injection when you already have pre-computed
    signals and want to run fusion + doctrine without the full async cycle.
    """
    decision = fuse_signals(signals, alert_level, posture)

    # Run doctrine gate
    doctrine = DoctrineEngine()
    mind_signal_map = {s.mind_type: s.confidence for s in signals}
    doctrine_output = doctrine.evaluate_decision(
        decision_id=str(uuid.uuid4()),
        recommended_escalation=decision.recommended_escalation,
        current_posture=posture,
        confidence=decision.confidence,
        has_contention=decision.has_contention,
        mind_signals=mind_signal_map,
    )

    decision.governance_compliant = doctrine_output.gate_result == GateResult.PASS
    decision.governance_notes = doctrine_output.violations
    decision.requires_human_review = doctrine_output.human_review_required

    if doctrine_output.modified_escalation:
        decision.recommended_escalation = doctrine_output.modified_escalation

    # Persist
    decision_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    with _db() as conn:
        conn.execute("""
            INSERT INTO fusion_decisions
            (decision_id, host_id, alert_level, urgency, decision_value,
             dominant_mind, confidence, posture, escalation, has_contention,
             requires_human, doctrine_gate, weights_json, signals_json,
             reasoning, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision_id, host_id, alert_level,
            decision.weights_used.urgency, decision.decision_value,
            decision.dominant_mind.value, decision.confidence,
            posture.value, decision.recommended_escalation.value,
            1 if decision.has_contention else 0,
            1 if decision.requires_human_review else 0,
            doctrine_output.gate_result.value,
            decision.weights_used.model_dump_json(),
            json.dumps([s.model_dump() for s in decision.signals]),
            decision.reasoning, now.isoformat(),
        ))
        if host_id:
            conn.execute("""
                UPDATE archon_hosts SET last_decision = ?, decision_count = decision_count + 1
                WHERE host_id = ?
            """, (now.isoformat(), host_id))
        conn.commit()

    decision.metadata["decision_id"] = decision_id
    decision.metadata["timestamp"] = now.isoformat()
    decision.metadata["doctrine_gate"] = doctrine_output.gate_result.value

    return decision


def get_cognitive_posture(
    alert_level: float,
    posture: PostureMode = PostureMode.PATROL,
) -> FusionWeights:
    """Get the current cognitive posture (weight distribution).

    Useful for introspection and UI display without producing a decision.
    Shows how the five minds would be weighted at a given alert level.
    """
    return compute_dynamic_weights(alert_level, posture)


def get_decision_history(
    host_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve recent fusion decisions for audit."""
    with _db() as conn:
        if host_id:
            rows = conn.execute(
                "SELECT * FROM fusion_decisions WHERE host_id = ? ORDER BY created_at DESC LIMIT ?",
                (host_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM fusion_decisions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]


def get_mind_profiles() -> dict[MindType, MindProfile]:
    """Return all five mind profiles with full doctrine."""
    return MIND_PROFILES.copy()
