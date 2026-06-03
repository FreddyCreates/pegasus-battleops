"""
ARCHON Doctrine Engine — Mission Constraints, Escalation Rules, and Governance

A serious warfare SDK must include boundaries:
  - Audit trails
  - Permissions
  - Human review where required
  - Mission constraints
  - Escalation rules
  - Clear separation between recommendation and authorized action

The Doctrine Engine enforces these boundaries. It sits between the fusion
output and any execution. No decision reaches the outside world without
passing through Doctrine.

The future of defense AI is not just faster models.
It is governed cognitive fusion.

Glyph: ⚖️ (justice / governance)
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

from .minds import MindType, PostureMode, EscalationLevel


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "archon.db"


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _init_doctrine_db() -> None:
    """Initialize doctrine audit tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS doctrine_audit (
                audit_id        TEXT PRIMARY KEY,
                decision_id     TEXT NOT NULL,
                gate_name       TEXT NOT NULL,
                gate_result     TEXT NOT NULL,
                reasoning       TEXT,
                constraints_checked TEXT DEFAULT '[]',
                violations      TEXT DEFAULT '[]',
                escalation_required INTEGER DEFAULT 0,
                human_review_required INTEGER DEFAULT 0,
                created_at      TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_da_decision ON doctrine_audit(decision_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_da_gate ON doctrine_audit(gate_name)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS human_review_queue (
                review_id       TEXT PRIMARY KEY,
                decision_id     TEXT NOT NULL,
                reason          TEXT NOT NULL,
                urgency         TEXT DEFAULT 'normal',
                context_json    TEXT,
                status          TEXT DEFAULT 'pending',
                reviewer        TEXT,
                review_outcome  TEXT,
                review_notes    TEXT,
                queued_at       TEXT NOT NULL,
                reviewed_at     TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hrq_status ON human_review_queue(status)")

        conn.commit()


_init_doctrine_db()


# ---------------------------------------------------------------------------
# Doctrine Models
# ---------------------------------------------------------------------------

class GateResult(str, Enum):
    """Result of passing through a doctrine gate."""
    PASS = "pass"               # Decision is compliant, proceed
    HOLD = "hold"               # Decision requires further review
    DENY = "deny"               # Decision violates doctrine, blocked
    ESCALATE = "escalate"       # Decision requires higher authority
    HUMAN_REVIEW = "human_review"  # Decision requires human decision


class MissionConstraint(BaseModel):
    """A hard constraint on what ARCHON is permitted to do."""
    constraint_id: str
    name: str
    description: str
    applies_to_postures: list[PostureMode] = Field(default_factory=list)
    applies_to_minds: list[MindType] = Field(default_factory=list)
    max_escalation_allowed: EscalationLevel = EscalationLevel.NEUTRALIZE
    requires_human_above: EscalationLevel = EscalationLevel.NEUTRALIZE
    active: bool = True


class EscalationRule(BaseModel):
    """Rule governing when and how to escalate."""
    rule_id: str
    name: str
    trigger_condition: str
    from_level: EscalationLevel
    to_level: EscalationLevel
    requires_confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    requires_corroboration: int = 1  # How many minds must agree
    cooldown_seconds: int = 60
    human_notification: bool = False


class RulesOfEngagement(BaseModel):
    """Complete rules of engagement for ARCHON."""
    roe_id: str
    name: str
    version: str = "1.0.0"
    constraints: list[MissionConstraint] = Field(default_factory=list)
    escalation_rules: list[EscalationRule] = Field(default_factory=list)
    max_autonomous_escalation: EscalationLevel = EscalationLevel.RESTRICT
    always_audit: bool = True
    lockdown_requires_governance: bool = True


class HumanReviewGate(BaseModel):
    """A gate that requires human decision before proceeding."""
    review_id: str
    decision_id: str
    reason: str
    urgency: str = "normal"  # "low", "normal", "high", "critical"
    context: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # "pending", "approved", "denied", "expired"
    queued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DoctrineGateOutput(BaseModel):
    """Output of running a decision through the doctrine engine."""
    gate_result: GateResult
    decision_id: str
    constraints_checked: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    escalation_required: bool = False
    human_review_required: bool = False
    reasoning: str = ""
    modified_escalation: EscalationLevel | None = None
    audit_id: str = ""


# ---------------------------------------------------------------------------
# Default ARCHON Doctrine
# ---------------------------------------------------------------------------

ARCHON_DOCTRINE = RulesOfEngagement(
    roe_id="archon-roe-v1",
    name="ARCHON Rules of Engagement v1",
    version="1.0.0",
    constraints=[
        MissionConstraint(
            constraint_id="mc-001",
            name="No autonomous destructive action",
            description="ARCHON cannot authorize destructive actions without human review",
            applies_to_postures=[PostureMode.COMBAT, PostureMode.ENGAGED],
            max_escalation_allowed=EscalationLevel.RESTRICT,
            requires_human_above=EscalationLevel.RESTRICT,
        ),
        MissionConstraint(
            constraint_id="mc-002",
            name="Lockdown requires governance",
            description="LOCKDOWN posture can only be entered via governance override",
            applies_to_postures=[PostureMode.LOCKDOWN],
            max_escalation_allowed=EscalationLevel.ESCALATE_HUMAN,
            requires_human_above=EscalationLevel.OBSERVE,
        ),
        MissionConstraint(
            constraint_id="mc-003",
            name="Observation always permitted",
            description="ARCHON may always observe and record without restriction",
            applies_to_postures=list(PostureMode),
            max_escalation_allowed=EscalationLevel.OBSERVE,
            requires_human_above=EscalationLevel.ESCALATE_HUMAN,
        ),
        MissionConstraint(
            constraint_id="mc-004",
            name="Challenge requires confidence",
            description="Issuing a challenge to an entity requires confidence >= 0.6",
            applies_to_postures=[PostureMode.ALERT, PostureMode.ENGAGED],
            max_escalation_allowed=EscalationLevel.CHALLENGE,
            requires_human_above=EscalationLevel.NEUTRALIZE,
        ),
        MissionConstraint(
            constraint_id="mc-005",
            name="Recovery posture limits action",
            description="In RECOVERY, max escalation is WARN to prevent re-engagement",
            applies_to_postures=[PostureMode.RECOVERY],
            max_escalation_allowed=EscalationLevel.WARN,
            requires_human_above=EscalationLevel.CHALLENGE,
        ),
    ],
    escalation_rules=[
        EscalationRule(
            rule_id="er-001",
            name="Multi-mind high-confidence escalation",
            trigger_condition="3+ minds signal confidence > 0.7",
            from_level=EscalationLevel.OBSERVE,
            to_level=EscalationLevel.CHALLENGE,
            requires_confidence=0.7,
            requires_corroboration=3,
            cooldown_seconds=30,
        ),
        EscalationRule(
            rule_id="er-002",
            name="Urgency override escalation",
            trigger_condition="Any mind invokes urgency_override",
            from_level=EscalationLevel.OBSERVE,
            to_level=EscalationLevel.RESTRICT,
            requires_confidence=0.8,
            requires_corroboration=1,
            cooldown_seconds=0,
            human_notification=True,
        ),
        EscalationRule(
            rule_id="er-003",
            name="Repeated threat escalation",
            trigger_condition="Same threat vector seen 5+ times in 1 hour",
            from_level=EscalationLevel.WARN,
            to_level=EscalationLevel.RESTRICT,
            requires_confidence=0.6,
            requires_corroboration=1,
            cooldown_seconds=120,
        ),
        EscalationRule(
            rule_id="er-004",
            name="Critical severity forces human",
            trigger_condition="Threat severity >= 0.9",
            from_level=EscalationLevel.RESTRICT,
            to_level=EscalationLevel.ESCALATE_HUMAN,
            requires_confidence=0.85,
            requires_corroboration=2,
            cooldown_seconds=0,
            human_notification=True,
        ),
    ],
    max_autonomous_escalation=EscalationLevel.RESTRICT,
    always_audit=True,
    lockdown_requires_governance=True,
)


# ---------------------------------------------------------------------------
# Doctrine Engine
# ---------------------------------------------------------------------------

class DoctrineEngine:
    """Enforces mission constraints and escalation rules on ARCHON decisions.

    Every decision passes through the Doctrine Engine before it can be executed.
    The engine:
    1. Checks mission constraints for the current posture
    2. Validates escalation level against rules
    3. Determines if human review is required
    4. Records audit trail
    5. Returns gate result
    """

    def __init__(self, roe: RulesOfEngagement | None = None):
        self.roe = roe or ARCHON_DOCTRINE

    def evaluate_decision(
        self,
        decision_id: str,
        recommended_escalation: EscalationLevel,
        current_posture: PostureMode,
        confidence: float,
        has_contention: bool,
        mind_signals: dict[MindType, float],
        threat_severity: float = 0.0,
    ) -> DoctrineGateOutput:
        """Run a decision through the full doctrine gate.

        Args:
            decision_id: Unique ID of the fusion decision
            recommended_escalation: What the fusion engine recommends
            current_posture: Current operational posture
            confidence: Fused confidence level
            has_contention: Whether minds disagreed
            mind_signals: Signal values per mind
            threat_severity: Maximum threat severity

        Returns:
            DoctrineGateOutput with result and audit trail
        """
        constraints_checked: list[str] = []
        violations: list[str] = []
        escalation_required = False
        human_review_required = False
        modified_escalation = recommended_escalation

        # Check each constraint
        for constraint in self.roe.constraints:
            if not constraint.active:
                continue
            if constraint.applies_to_postures and current_posture not in constraint.applies_to_postures:
                continue

            constraints_checked.append(constraint.name)

            # Check if recommended escalation exceeds allowed
            escalation_order = list(EscalationLevel)
            rec_idx = escalation_order.index(recommended_escalation)
            max_idx = escalation_order.index(constraint.max_escalation_allowed)
            human_idx = escalation_order.index(constraint.requires_human_above)

            if rec_idx > max_idx:
                violations.append(
                    f"{constraint.name}: escalation {recommended_escalation.value} "
                    f"exceeds max allowed {constraint.max_escalation_allowed.value}"
                )
                modified_escalation = constraint.max_escalation_allowed

            if rec_idx >= human_idx:
                human_review_required = True

        # Check escalation rules
        corroborating_minds = sum(1 for v in mind_signals.values() if v > 0.5)
        high_confidence_minds = sum(1 for v in mind_signals.values() if v > 0.7)

        for rule in self.roe.escalation_rules:
            if rule.requires_corroboration <= corroborating_minds:
                if confidence >= rule.requires_confidence:
                    escalation_order = list(EscalationLevel)
                    current_idx = escalation_order.index(modified_escalation)
                    rule_to_idx = escalation_order.index(rule.to_level)
                    if rule_to_idx > current_idx:
                        escalation_required = True
                        if rule.human_notification:
                            human_review_required = True

        # Cap at max autonomous escalation
        escalation_order = list(EscalationLevel)
        max_auto_idx = escalation_order.index(self.roe.max_autonomous_escalation)
        modified_idx = escalation_order.index(modified_escalation)
        if modified_idx > max_auto_idx and not human_review_required:
            human_review_required = True

        # Determine gate result
        if violations and not human_review_required:
            gate_result = GateResult.DENY
        elif human_review_required:
            gate_result = GateResult.HUMAN_REVIEW
        elif escalation_required:
            gate_result = GateResult.ESCALATE
        elif has_contention and confidence < 0.5:
            gate_result = GateResult.HOLD
        else:
            gate_result = GateResult.PASS

        # Build reasoning
        reasoning_parts = []
        if violations:
            reasoning_parts.append(f"Violations: {'; '.join(violations)}")
        if human_review_required:
            reasoning_parts.append("Human review required by doctrine")
        if escalation_required:
            reasoning_parts.append("Escalation rules triggered")
        if not reasoning_parts:
            reasoning_parts.append("All constraints satisfied")

        # Audit
        audit_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        if self.roe.always_audit:
            with _db() as conn:
                conn.execute("""
                    INSERT INTO doctrine_audit
                    (audit_id, decision_id, gate_name, gate_result, reasoning,
                     constraints_checked, violations, escalation_required,
                     human_review_required, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    audit_id, decision_id, "primary_gate", gate_result.value,
                    " | ".join(reasoning_parts),
                    json.dumps(constraints_checked), json.dumps(violations),
                    1 if escalation_required else 0,
                    1 if human_review_required else 0,
                    now.isoformat(),
                ))

                # Queue for human review if required
                if human_review_required:
                    urgency = "critical" if threat_severity > 0.8 else (
                        "high" if threat_severity > 0.5 else "normal"
                    )
                    conn.execute("""
                        INSERT INTO human_review_queue
                        (review_id, decision_id, reason, urgency, context_json, status, queued_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(uuid.uuid4()), decision_id,
                        f"Doctrine gate requires human review: {'; '.join(reasoning_parts)}",
                        urgency,
                        json.dumps({
                            "posture": current_posture.value,
                            "escalation": modified_escalation.value,
                            "confidence": confidence,
                            "threat_severity": threat_severity,
                            "violations": violations,
                        }),
                        "pending", now.isoformat(),
                    ))

                conn.commit()

        return DoctrineGateOutput(
            gate_result=gate_result,
            decision_id=decision_id,
            constraints_checked=constraints_checked,
            violations=violations,
            escalation_required=escalation_required,
            human_review_required=human_review_required,
            reasoning=" | ".join(reasoning_parts),
            modified_escalation=modified_escalation if modified_escalation != recommended_escalation else None,
            audit_id=audit_id,
        )

    def get_pending_reviews(self) -> list[dict[str, Any]]:
        """Get all pending human reviews."""
        with _db() as conn:
            rows = conn.execute(
                "SELECT * FROM human_review_queue WHERE status = 'pending' ORDER BY queued_at"
            ).fetchall()
            return [dict(row) for row in rows]

    def submit_review(
        self,
        review_id: str,
        outcome: str,  # "approved" or "denied"
        reviewer: str,
        notes: str = "",
    ) -> None:
        """Submit a human review decision."""
        now = datetime.now(timezone.utc)
        with _db() as conn:
            conn.execute("""
                UPDATE human_review_queue
                SET status = ?, reviewer = ?, review_outcome = ?,
                    review_notes = ?, reviewed_at = ?
                WHERE review_id = ?
            """, (outcome, reviewer, outcome, notes, now.isoformat(), review_id))
            conn.commit()
