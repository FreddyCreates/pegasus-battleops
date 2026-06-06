"""
⇡ ESCALATION ENGINE — Tier transition and reclassification logic

Monitors entity behavior over time and triggers reclassification when:
- A Tier C (Shadow) entity exhibits Tier B (Hostile) patterns
- A Tier A (Cooperative) entity starts probing restricted paths
- Threat level increases due to repeated violations

Escalation is bidirectional:
- ESCALATE: move entity to a more hostile classification
- DE-ESCALATE: relax classification after sustained good behavior
"""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ..organism_charter import ClassificationTier, EntityRole
from ..schemas import ThreatLevel


# ---------------------------------------------------------------------------
# Escalation Types
# ---------------------------------------------------------------------------

class EscalationDirection(str, Enum):
    """Direction of tier transition."""
    ESCALATE = "escalate"          # Move to higher threat tier
    DE_ESCALATE = "de_escalate"    # Move to lower threat tier
    HOLD = "hold"                  # No change


class EscalationTrigger(str, Enum):
    """What triggered the escalation decision."""
    REPEATED_PROBES = "repeated_probes"
    HONEYPOT_TRIGGER = "honeypot_trigger"
    EXPLOIT_ATTEMPT = "exploit_attempt"
    RATE_EXCEEDED = "rate_exceeded"
    CHALLENGE_FAILED = "challenge_failed"
    BEHAVIORAL_SHIFT = "behavioral_shift"
    TIME_DECAY = "time_decay"           # Good behavior over time
    MANUAL_OVERRIDE = "manual_override"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class EscalationRule(BaseModel):
    """A rule that defines when escalation should occur."""
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: str

    # Trigger conditions
    trigger: EscalationTrigger
    threshold: int = 3  # How many events before triggering
    window_minutes: int = 60  # Time window to count events

    # Transition
    from_tier: ClassificationTier | None = None  # None = any tier
    to_tier: ClassificationTier
    direction: EscalationDirection

    # Threat level change
    new_threat_level: ThreatLevel | None = None

    # Controls
    enabled: bool = True
    cooldown_minutes: int = 30  # Min time between escalations for same entity


class EscalationEvent(BaseModel):
    """Record of an escalation that occurred."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    entity_ip: str
    entity_fingerprint: str | None = None

    # Transition
    rule_id: str
    rule_name: str
    trigger: EscalationTrigger
    direction: EscalationDirection

    # Before/After
    previous_tier: ClassificationTier
    new_tier: ClassificationTier
    previous_threat_level: ThreatLevel
    new_threat_level: ThreatLevel

    # Context
    trigger_count: int = 0  # How many events triggered this
    reasoning: str = ""

    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "adaptive_response.db"


def _init_escalation_tables() -> None:
    """Initialize escalation tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS escalation_events (
                event_id            TEXT PRIMARY KEY,
                entity_ip           TEXT NOT NULL,
                entity_fingerprint  TEXT,
                rule_id             TEXT NOT NULL,
                rule_name           TEXT,
                trigger_type        TEXT NOT NULL,
                direction           TEXT NOT NULL,
                previous_tier       TEXT NOT NULL,
                new_tier            TEXT NOT NULL,
                previous_threat_level TEXT NOT NULL,
                new_threat_level    TEXT NOT NULL,
                trigger_count       INTEGER DEFAULT 0,
                reasoning           TEXT,
                occurred_at         TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ee_ip ON escalation_events(entity_ip)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ee_time ON escalation_events(occurred_at)"
        )

        # Entity behavior counters (sliding window tracking)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS behavior_counters (
                entity_ip       TEXT NOT NULL,
                trigger_type    TEXT NOT NULL,
                count           INTEGER DEFAULT 0,
                window_start    TEXT NOT NULL,
                last_updated    TEXT NOT NULL,
                PRIMARY KEY (entity_ip, trigger_type)
            )
            """
        )

        conn.commit()


_init_escalation_tables()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Default Escalation Rules
# ---------------------------------------------------------------------------

DEFAULT_RULES: list[EscalationRule] = [
    EscalationRule(
        name="shadow_to_hostile_probes",
        description="Shadow entity (Tier C) escalates to Hostile (Tier B) after repeated exploit probes",
        trigger=EscalationTrigger.REPEATED_PROBES,
        threshold=5,
        window_minutes=30,
        from_tier=ClassificationTier.TIER_C_SHADOW,
        to_tier=ClassificationTier.TIER_B_HOSTILE,
        direction=EscalationDirection.ESCALATE,
        new_threat_level=ThreatLevel.HIGH,
    ),
    EscalationRule(
        name="shadow_to_hostile_honeypot",
        description="Shadow entity triggers honeypot → immediately escalate to Hostile",
        trigger=EscalationTrigger.HONEYPOT_TRIGGER,
        threshold=1,
        window_minutes=60,
        from_tier=ClassificationTier.TIER_C_SHADOW,
        to_tier=ClassificationTier.TIER_B_HOSTILE,
        direction=EscalationDirection.ESCALATE,
        new_threat_level=ThreatLevel.HIGH,
    ),
    EscalationRule(
        name="cooperative_to_shadow_probes",
        description="Cooperative entity (Tier A) starts probing → reclassify as Shadow",
        trigger=EscalationTrigger.REPEATED_PROBES,
        threshold=3,
        window_minutes=60,
        from_tier=ClassificationTier.TIER_A_COOPERATIVE,
        to_tier=ClassificationTier.TIER_C_SHADOW,
        direction=EscalationDirection.ESCALATE,
        new_threat_level=ThreatLevel.MEDIUM,
    ),
    EscalationRule(
        name="hostile_rate_exceeded",
        description="Hostile entity exceeds rate limits → escalate threat to Critical",
        trigger=EscalationTrigger.RATE_EXCEEDED,
        threshold=10,
        window_minutes=5,
        from_tier=ClassificationTier.TIER_B_HOSTILE,
        to_tier=ClassificationTier.TIER_B_HOSTILE,
        direction=EscalationDirection.ESCALATE,
        new_threat_level=ThreatLevel.CRITICAL,
    ),
    EscalationRule(
        name="challenge_failure_escalate",
        description="Entity fails challenge → escalate from Shadow to Hostile",
        trigger=EscalationTrigger.CHALLENGE_FAILED,
        threshold=2,
        window_minutes=30,
        from_tier=ClassificationTier.TIER_C_SHADOW,
        to_tier=ClassificationTier.TIER_B_HOSTILE,
        direction=EscalationDirection.ESCALATE,
        new_threat_level=ThreatLevel.HIGH,
    ),
    EscalationRule(
        name="time_decay_de_escalate",
        description="No hostile behavior for extended period → de-escalate",
        trigger=EscalationTrigger.TIME_DECAY,
        threshold=1,
        window_minutes=1440,  # 24 hours of quiet
        from_tier=None,  # Any tier
        to_tier=ClassificationTier.TIER_A_COOPERATIVE,
        direction=EscalationDirection.DE_ESCALATE,
        new_threat_level=ThreatLevel.LOW,
    ),
]


# ---------------------------------------------------------------------------
# Escalation Engine
# ---------------------------------------------------------------------------

class EscalationEngine:
    """
    ⇡ Monitors entity behavior and triggers tier transitions.

    Flow:
    1. Receive behavior signals (probes, honeypot triggers, rate violations)
    2. Increment counters within sliding time windows
    3. Check counters against escalation rules
    4. If threshold met → emit EscalationEvent → reclassify entity
    """

    def __init__(self, rules: list[EscalationRule] | None = None):
        self.rules = rules or DEFAULT_RULES

    def record_behavior(
        self,
        entity_ip: str,
        trigger: EscalationTrigger,
        current_tier: ClassificationTier,
        current_threat_level: ThreatLevel,
        fingerprint_id: str | None = None,
    ) -> EscalationEvent | None:
        """
        Record a behavior signal and check if escalation is triggered.

        Returns an EscalationEvent if a rule threshold is met, else None.
        """
        now = datetime.now(timezone.utc)

        # Update behavior counter
        count = self._increment_counter(entity_ip, trigger, now)

        # Check rules
        for rule in self.rules:
            if not rule.enabled:
                continue

            # Check if rule applies to this trigger
            if rule.trigger != trigger:
                continue

            # Check if rule applies to current tier
            if rule.from_tier is not None and rule.from_tier != current_tier:
                continue

            # Check cooldown
            if self._in_cooldown(entity_ip, rule, now):
                continue

            # Check threshold within window
            window_count = self._get_count_in_window(
                entity_ip, trigger, rule.window_minutes, now
            )

            if window_count >= rule.threshold:
                # Escalation triggered!
                event = EscalationEvent(
                    entity_ip=entity_ip,
                    entity_fingerprint=fingerprint_id,
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    trigger=trigger,
                    direction=rule.direction,
                    previous_tier=current_tier,
                    new_tier=rule.to_tier,
                    previous_threat_level=current_threat_level,
                    new_threat_level=rule.new_threat_level or current_threat_level,
                    trigger_count=window_count,
                    reasoning=(
                        f"Rule '{rule.name}': {window_count} {trigger.value} events "
                        f"in {rule.window_minutes}min (threshold={rule.threshold})"
                    ),
                )

                self._record_escalation(event)
                self._reset_counter(entity_ip, trigger)
                return event

        return None

    def get_recent_escalations(
        self, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get recent escalation events."""
        with _db() as conn:
            rows = conn.execute(
                "SELECT * FROM escalation_events ORDER BY occurred_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_entity_escalation_history(
        self, entity_ip: str
    ) -> list[dict[str, Any]]:
        """Get escalation history for a specific entity."""
        with _db() as conn:
            rows = conn.execute(
                "SELECT * FROM escalation_events WHERE entity_ip = ? ORDER BY occurred_at DESC",
                (entity_ip,),
            ).fetchall()
            return [dict(row) for row in rows]

    def add_rule(self, rule: EscalationRule) -> None:
        """Add a new escalation rule at runtime."""
        self.rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an escalation rule by ID."""
        original_len = len(self.rules)
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        return len(self.rules) < original_len

    def get_rules(self) -> list[EscalationRule]:
        """Return current escalation rules."""
        return self.rules

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    def _increment_counter(
        self, entity_ip: str, trigger: EscalationTrigger, now: datetime
    ) -> int:
        """Increment behavior counter, return new count."""
        with _db() as conn:
            row = conn.execute(
                """
                SELECT count, window_start FROM behavior_counters
                WHERE entity_ip = ? AND trigger_type = ?
                """,
                (entity_ip, trigger.value),
            ).fetchone()

            if row is None:
                conn.execute(
                    """
                    INSERT INTO behavior_counters
                    (entity_ip, trigger_type, count, window_start, last_updated)
                    VALUES (?, ?, 1, ?, ?)
                    """,
                    (entity_ip, trigger.value, now.isoformat(), now.isoformat()),
                )
                conn.commit()
                return 1
            else:
                new_count = row["count"] + 1
                conn.execute(
                    """
                    UPDATE behavior_counters
                    SET count = ?, last_updated = ?
                    WHERE entity_ip = ? AND trigger_type = ?
                    """,
                    (new_count, now.isoformat(), entity_ip, trigger.value),
                )
                conn.commit()
                return new_count

    def _get_count_in_window(
        self,
        entity_ip: str,
        trigger: EscalationTrigger,
        window_minutes: int,
        now: datetime,
    ) -> int:
        """Get count within the specified time window."""
        with _db() as conn:
            row = conn.execute(
                """
                SELECT count, window_start FROM behavior_counters
                WHERE entity_ip = ? AND trigger_type = ?
                """,
                (entity_ip, trigger.value),
            ).fetchone()

            if row is None:
                return 0

            window_start = datetime.fromisoformat(row["window_start"])
            window_elapsed = (now - window_start).total_seconds() / 60

            # If window has expired, reset
            if window_elapsed > window_minutes:
                conn.execute(
                    """
                    UPDATE behavior_counters
                    SET count = 0, window_start = ?
                    WHERE entity_ip = ? AND trigger_type = ?
                    """,
                    (now.isoformat(), entity_ip, trigger.value),
                )
                conn.commit()
                return 0

            return row["count"]

    def _in_cooldown(
        self, entity_ip: str, rule: EscalationRule, now: datetime
    ) -> bool:
        """Check if entity is in cooldown for this rule."""
        with _db() as conn:
            row = conn.execute(
                """
                SELECT occurred_at FROM escalation_events
                WHERE entity_ip = ? AND rule_id = ?
                ORDER BY occurred_at DESC LIMIT 1
                """,
                (entity_ip, rule.rule_id),
            ).fetchone()

            if row is None:
                return False

            last_escalation = datetime.fromisoformat(row["occurred_at"])
            cooldown_end = last_escalation + timedelta(minutes=rule.cooldown_minutes)
            return now < cooldown_end

    def _record_escalation(self, event: EscalationEvent) -> None:
        """Persist an escalation event."""
        with _db() as conn:
            conn.execute(
                """
                INSERT INTO escalation_events
                (event_id, entity_ip, entity_fingerprint, rule_id, rule_name,
                 trigger_type, direction, previous_tier, new_tier,
                 previous_threat_level, new_threat_level, trigger_count,
                 reasoning, occurred_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.entity_ip,
                    event.entity_fingerprint,
                    event.rule_id,
                    event.rule_name,
                    event.trigger.value,
                    event.direction.value,
                    event.previous_tier.value,
                    event.new_tier.value,
                    event.previous_threat_level.value,
                    event.new_threat_level.value,
                    event.trigger_count,
                    event.reasoning,
                    event.occurred_at.isoformat(),
                ),
            )
            conn.commit()

    def _reset_counter(self, entity_ip: str, trigger: EscalationTrigger) -> None:
        """Reset counter after escalation."""
        with _db() as conn:
            conn.execute(
                """
                UPDATE behavior_counters SET count = 0, window_start = ?
                WHERE entity_ip = ? AND trigger_type = ?
                """,
                (datetime.now(timezone.utc).isoformat(), entity_ip, trigger.value),
            )
            conn.commit()


# ---------------------------------------------------------------------------
# Singleton Access
# ---------------------------------------------------------------------------

_escalation_instance: EscalationEngine | None = None


def get_escalation_engine(
    rules: list[EscalationRule] | None = None,
) -> EscalationEngine:
    """Get or create the singleton escalation engine."""
    global _escalation_instance
    if _escalation_instance is None or rules is not None:
        _escalation_instance = EscalationEngine(rules=rules)
    return _escalation_instance
