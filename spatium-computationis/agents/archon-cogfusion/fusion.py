"""
ARCHON Cognitive Fusion Engine — Dynamic Weight Computation & Posture Management

Core Fusion Algorithm:
  FusedDecision = Σ(Signal_i × DynamicWeight_i × AmplificationFactor_i)

The engine implements:
  1. Dynamic weight computation based on alert level (urgency = alertLevel²)
  2. Amplification/dampening between minds based on their interaction matrix
  3. Contention resolution when minds disagree
  4. Posture state machine with transition logic
  5. Temporal decay on historical signals
  6. Urgency override bypass for critical signals

Glyph: ⚡ (fusion energy)
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from .minds import (
    MindSignal,
    MindType,
    PostureMode,
    EscalationLevel,
    get_amplification_matrix,
    get_dampening_matrix,
)


# ---------------------------------------------------------------------------
# Weight Configuration (from Alpha Mind paper)
# ---------------------------------------------------------------------------

# Base weights (sum = 1.0)
BASE_WEIGHTS: dict[MindType, float] = {
    MindType.HACKER: 0.236,
    MindType.GENERAL: 0.236,
    MindType.STRATEGIST: 0.191,
    MindType.PILOT: 0.146,
    MindType.AI_INTELLIGENCE: 0.191,
}

# Urgency sensitivity coefficients
URGENCY_COEFFICIENTS: dict[MindType, float] = {
    MindType.HACKER: 0.1,        # Rises with urgency
    MindType.GENERAL: -0.05,     # Falls with urgency
    MindType.STRATEGIST: -0.05,  # Falls with urgency
    MindType.PILOT: 0.1,         # Rises with urgency
    MindType.AI_INTELLIGENCE: 0.0,  # Constant — persistent oversight
}

# Posture-based weight modifiers (applied on top of urgency weights)
POSTURE_MODIFIERS: dict[PostureMode, dict[MindType, float]] = {
    PostureMode.DORMANT: {
        MindType.HACKER: 0.5, MindType.GENERAL: 0.8,
        MindType.STRATEGIST: 0.6, MindType.PILOT: 0.3,
        MindType.AI_INTELLIGENCE: 1.0,
    },
    PostureMode.PATROL: {
        MindType.HACKER: 0.8, MindType.GENERAL: 1.0,
        MindType.STRATEGIST: 0.9, MindType.PILOT: 0.6,
        MindType.AI_INTELLIGENCE: 1.0,
    },
    PostureMode.ALERT: {
        MindType.HACKER: 1.1, MindType.GENERAL: 1.0,
        MindType.STRATEGIST: 1.0, MindType.PILOT: 0.9,
        MindType.AI_INTELLIGENCE: 1.0,
    },
    PostureMode.ENGAGED: {
        MindType.HACKER: 1.2, MindType.GENERAL: 0.9,
        MindType.STRATEGIST: 0.8, MindType.PILOT: 1.2,
        MindType.AI_INTELLIGENCE: 1.0,
    },
    PostureMode.COMBAT: {
        MindType.HACKER: 1.4, MindType.GENERAL: 0.7,
        MindType.STRATEGIST: 0.6, MindType.PILOT: 1.4,
        MindType.AI_INTELLIGENCE: 1.0,
    },
    PostureMode.RECOVERY: {
        MindType.HACKER: 0.6, MindType.GENERAL: 1.2,
        MindType.STRATEGIST: 1.3, MindType.PILOT: 0.5,
        MindType.AI_INTELLIGENCE: 1.0,
    },
    PostureMode.LOCKDOWN: {
        MindType.HACKER: 0.3, MindType.GENERAL: 1.5,
        MindType.STRATEGIST: 0.4, MindType.PILOT: 0.2,
        MindType.AI_INTELLIGENCE: 1.0,
    },
}

# Amplification/dampening strength
AMPLIFICATION_FACTOR = 0.15
DAMPENING_FACTOR = 0.10


# ---------------------------------------------------------------------------
# Posture Transition Matrix
# ---------------------------------------------------------------------------

# Valid posture transitions: from_posture -> set of valid next postures
POSTURE_TRANSITIONS: dict[PostureMode, set[PostureMode]] = {
    PostureMode.DORMANT: {PostureMode.PATROL, PostureMode.ALERT, PostureMode.LOCKDOWN},
    PostureMode.PATROL: {PostureMode.DORMANT, PostureMode.ALERT, PostureMode.ENGAGED, PostureMode.LOCKDOWN},
    PostureMode.ALERT: {PostureMode.PATROL, PostureMode.ENGAGED, PostureMode.COMBAT, PostureMode.LOCKDOWN},
    PostureMode.ENGAGED: {PostureMode.ALERT, PostureMode.COMBAT, PostureMode.RECOVERY, PostureMode.LOCKDOWN},
    PostureMode.COMBAT: {PostureMode.ENGAGED, PostureMode.RECOVERY, PostureMode.LOCKDOWN},
    PostureMode.RECOVERY: {PostureMode.PATROL, PostureMode.ALERT, PostureMode.DORMANT, PostureMode.LOCKDOWN},
    PostureMode.LOCKDOWN: {PostureMode.RECOVERY, PostureMode.DORMANT},  # Only governance can exit lockdown
}


# ---------------------------------------------------------------------------
# Fusion Models
# ---------------------------------------------------------------------------

class FusionWeights(BaseModel):
    """Computed dynamic weights for the five minds."""
    hacker: float = Field(ge=0.0)
    general: float = Field(ge=0.0)
    strategist: float = Field(ge=0.0)
    pilot: float = Field(ge=0.0)
    ai_intelligence: float = Field(ge=0.0)
    alert_level: float = Field(ge=0.0, le=1.0)
    urgency: float = Field(ge=0.0, le=1.0)
    posture: PostureMode = PostureMode.PATROL
    posture_applied: bool = False

    def as_dict(self) -> dict[MindType, float]:
        return {
            MindType.HACKER: self.hacker,
            MindType.GENERAL: self.general,
            MindType.STRATEGIST: self.strategist,
            MindType.PILOT: self.pilot,
            MindType.AI_INTELLIGENCE: self.ai_intelligence,
        }

    @property
    def dominant_mind(self) -> MindType:
        """Return the mind with the highest weight."""
        weights = self.as_dict()
        return max(weights, key=weights.get)  # type: ignore[arg-type]

    @property
    def weight_sum(self) -> float:
        """Sum of all weights (should be ~1.0 after normalization)."""
        return self.hacker + self.general + self.strategist + self.pilot + self.ai_intelligence


class ContentionResolution(BaseModel):
    """Records how contention between minds was resolved."""
    contending_minds: list[MindType]
    winner: MindType
    resolution_method: str  # "weight_dominance", "urgency_override", "governance_authority"
    reasoning: str = ""
    overridden_signals: list[MindType] = Field(default_factory=list)


class PostureTransition(BaseModel):
    """Records a posture state transition."""
    from_posture: PostureMode
    to_posture: PostureMode
    trigger: str
    triggered_by: MindType | None = None
    alert_level: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FusedDecision(BaseModel):
    """The result of cognitive fusion across all five minds.

    This is the primary output of ARCHON. It contains:
    - The fused decision value
    - Full weight breakdown
    - All contributing signals with reasoning
    - Contention resolution records
    - Posture recommendation
    - Governance compliance status
    - Embedding brain state (when embedding fusion is active)
    """
    decision_value: float = Field(description="Weighted sum of all mind signals")
    weights_used: FusionWeights
    signals: list[MindSignal] = Field(default_factory=list)
    dominant_mind: MindType
    confidence: float = Field(ge=0.0, le=1.0)

    # Structured output
    reasoning: str = ""
    recommended_action: str = ""
    recommended_escalation: EscalationLevel = EscalationLevel.OBSERVE

    # Contention
    contentions: list[ContentionResolution] = Field(default_factory=list)
    has_contention: bool = False

    # Posture
    recommended_posture: PostureMode = PostureMode.PATROL
    posture_transition: PostureTransition | None = None

    # Governance
    governance_compliant: bool = True
    governance_notes: list[str] = Field(default_factory=list)
    requires_human_review: bool = False

    # Embedding Brain (V1 prototype — context-driven leadership shifts)
    embedding_brain_active: bool = False
    embedding_leadership_mode: str = ""
    embedding_dominant_coalition: list[str] = Field(default_factory=list)
    embedding_decision_direction: str = ""
    embedding_attention_weights: dict[str, float] = Field(default_factory=dict)

    # Audit
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Fusion Engine
# ---------------------------------------------------------------------------

def compute_urgency(alert_level: float) -> float:
    """Compute urgency factor from alert level.

    urgency = alertLevel²
    Non-linear escalation: low alerts have minimal effect,
    high alerts create dramatic cognitive shift.
    """
    clamped = max(0.0, min(1.0, alert_level))
    return clamped ** 2


def compute_dynamic_weights(
    alert_level: float,
    posture: PostureMode = PostureMode.PATROL,
) -> FusionWeights:
    """Compute dynamic weights based on alert level and posture.

    The algorithm:
    1. Compute base weights with urgency coefficients
    2. Apply posture modifiers
    3. Normalize to sum = 1.0
    """
    urgency = compute_urgency(alert_level)

    # Step 1: Base + urgency
    raw_weights: dict[MindType, float] = {}
    for mind_type in MindType:
        base = BASE_WEIGHTS[mind_type]
        coefficient = URGENCY_COEFFICIENTS[mind_type]
        raw_weights[mind_type] = base + urgency * coefficient

    # Step 2: Posture modifier
    posture_mod = POSTURE_MODIFIERS.get(posture, POSTURE_MODIFIERS[PostureMode.PATROL])
    for mind_type in raw_weights:
        raw_weights[mind_type] *= posture_mod[mind_type]

    # Clamp non-negative
    for mind_type in raw_weights:
        raw_weights[mind_type] = max(0.0, raw_weights[mind_type])

    # Step 3: Normalize
    total = sum(raw_weights.values())
    if total > 0:
        for mind_type in raw_weights:
            raw_weights[mind_type] /= total

    return FusionWeights(
        hacker=raw_weights[MindType.HACKER],
        general=raw_weights[MindType.GENERAL],
        strategist=raw_weights[MindType.STRATEGIST],
        pilot=raw_weights[MindType.PILOT],
        ai_intelligence=raw_weights[MindType.AI_INTELLIGENCE],
        alert_level=alert_level,
        urgency=urgency,
        posture=posture,
        posture_applied=True,
    )


def _apply_interaction_dynamics(
    weights: dict[MindType, float],
    signals: list[MindSignal],
) -> dict[MindType, float]:
    """Apply amplification and dampening based on mind interaction matrix.

    When a mind produces a high-confidence signal, it amplifies its allies
    and dampens its competitors.
    """
    amp_matrix = get_amplification_matrix()
    damp_matrix = get_dampening_matrix()
    adjusted = dict(weights)

    for signal in signals:
        if signal.confidence < 0.5:
            continue  # Low-confidence signals don't affect dynamics

        strength = signal.confidence * abs(signal.signal_value)

        # Amplify allies
        for ally in amp_matrix.get(signal.mind_type, []):
            adjusted[ally] += AMPLIFICATION_FACTOR * strength

        # Dampen competitors
        for competitor in damp_matrix.get(signal.mind_type, []):
            adjusted[competitor] -= DAMPENING_FACTOR * strength
            adjusted[competitor] = max(0.01, adjusted[competitor])  # Floor

    # Re-normalize
    total = sum(adjusted.values())
    if total > 0:
        for mt in adjusted:
            adjusted[mt] /= total

    return adjusted


def resolve_contention(signals: list[MindSignal]) -> list[ContentionResolution]:
    """Identify and resolve contentions between minds.

    Contention occurs when one mind's signal explicitly disagrees with another.
    Resolution follows priority: urgency_override > governance > weight.
    """
    resolutions: list[ContentionResolution] = []

    for signal in signals:
        if not signal.contends_with:
            continue

        contending = [s for s in signals if s.mind_type in signal.contends_with]
        if not contending:
            continue

        # Check for urgency override
        if signal.urgency_override:
            resolutions.append(ContentionResolution(
                contending_minds=[signal.mind_type] + signal.contends_with,
                winner=signal.mind_type,
                resolution_method="urgency_override",
                reasoning=f"{signal.mind_type.value} invoked urgency override: {signal.reasoning}",
                overridden_signals=signal.contends_with,
            ))
            continue

        # General Mind always wins governance disputes
        if signal.mind_type == MindType.GENERAL:
            resolutions.append(ContentionResolution(
                contending_minds=[signal.mind_type] + signal.contends_with,
                winner=MindType.GENERAL,
                resolution_method="governance_authority",
                reasoning="General Mind has governance authority over tactical minds",
                overridden_signals=signal.contends_with,
            ))
            continue

        # Default: higher weight wins (resolved in fusion)
        resolutions.append(ContentionResolution(
            contending_minds=[signal.mind_type] + signal.contends_with,
            winner=signal.mind_type,  # Tentative — actual resolution by weight
            resolution_method="weight_dominance",
            reasoning="Resolved by dynamic weight at fusion time",
        ))

    return resolutions


def _determine_posture(
    signals: list[MindSignal],
    alert_level: float,
    current_posture: PostureMode,
) -> tuple[PostureMode, PostureTransition | None]:
    """Determine if posture should change based on signals and alert level."""
    urgency = compute_urgency(alert_level)

    # Compute aggregate threat signal
    threat_signals = [s for s in signals if s.threat_vectors_detected]
    max_confidence = max((s.confidence for s in threat_signals), default=0.0)
    override_present = any(s.urgency_override for s in signals)

    # Determine target posture
    if override_present and urgency > 0.8:
        target = PostureMode.COMBAT
    elif urgency > 0.7 and max_confidence > 0.8:
        target = PostureMode.COMBAT
    elif urgency > 0.5 and max_confidence > 0.6:
        target = PostureMode.ENGAGED
    elif urgency > 0.3 or max_confidence > 0.4:
        target = PostureMode.ALERT
    elif urgency < 0.05 and max_confidence < 0.2:
        target = PostureMode.DORMANT
    else:
        target = PostureMode.PATROL

    # Check if transition is valid
    if target == current_posture:
        return current_posture, None

    valid_transitions = POSTURE_TRANSITIONS.get(current_posture, set())
    if target not in valid_transitions:
        return current_posture, None

    trigger_mind = None
    if threat_signals:
        trigger_mind = max(threat_signals, key=lambda s: s.confidence).mind_type

    transition = PostureTransition(
        from_posture=current_posture,
        to_posture=target,
        trigger=f"urgency={urgency:.3f}, max_confidence={max_confidence:.3f}",
        triggered_by=trigger_mind,
        alert_level=alert_level,
    )
    return target, transition


def _determine_escalation(
    decision_value: float,
    confidence: float,
    has_contention: bool,
    posture: PostureMode,
) -> EscalationLevel:
    """Determine the recommended escalation level."""
    if posture == PostureMode.COMBAT:
        if confidence > 0.8:
            return EscalationLevel.NEUTRALIZE
        return EscalationLevel.RESTRICT
    elif posture == PostureMode.ENGAGED:
        if confidence > 0.7:
            return EscalationLevel.RESTRICT
        return EscalationLevel.CHALLENGE
    elif posture == PostureMode.ALERT:
        if confidence > 0.6:
            return EscalationLevel.CHALLENGE
        return EscalationLevel.WARN
    elif has_contention:
        return EscalationLevel.WARN
    return EscalationLevel.OBSERVE


def fuse_signals(
    signals: list[MindSignal],
    alert_level: float,
    current_posture: PostureMode = PostureMode.PATROL,
) -> FusedDecision:
    """Perform cognitive fusion across mind signals.

    FusedDecision = Σ(Signal_i × DynamicWeight_i × InteractionFactor_i)

    The full fusion pipeline:
    1. Compute dynamic weights (urgency + posture)
    2. Apply interaction dynamics (amplification/dampening)
    3. Resolve contentions
    4. Compute weighted sum
    5. Determine posture transition
    6. Determine escalation level
    """
    # Step 1: Base weights
    weights = compute_dynamic_weights(alert_level, current_posture)
    weight_map = weights.as_dict()

    # Step 2: Interaction dynamics
    adjusted_weights = _apply_interaction_dynamics(weight_map, signals)

    # Step 3: Contention resolution
    contentions = resolve_contention(signals)
    has_contention = len(contentions) > 0

    # Apply overrides from contention resolution
    suppressed_minds: set[MindType] = set()
    for res in contentions:
        if res.resolution_method in ("urgency_override", "governance_authority"):
            suppressed_minds.update(res.overridden_signals)

    # Step 4: Weighted sum
    decision_value = 0.0
    weighted_confidence = 0.0

    for signal in signals:
        w = adjusted_weights.get(signal.mind_type, 0.0)
        # Suppressed minds get heavily discounted
        if signal.mind_type in suppressed_minds:
            w *= 0.1
        # Urgency override gets boosted
        if signal.urgency_override:
            w *= 2.0
        decision_value += signal.signal_value * w
        weighted_confidence += signal.confidence * w

    # Step 5: Posture transition
    new_posture, transition = _determine_posture(signals, alert_level, current_posture)

    # Step 6: Escalation
    escalation = _determine_escalation(
        decision_value, weighted_confidence, has_contention, new_posture
    )

    # Aggregate reasoning
    reasoning_parts = []
    for signal in signals:
        if signal.reasoning:
            reasoning_parts.append(f"[{signal.mind_type.value}] {signal.reasoning}")

    # Determine if human review required
    requires_human = (
        escalation in (EscalationLevel.NEUTRALIZE, EscalationLevel.ESCALATE_HUMAN)
        or (has_contention and weighted_confidence < 0.5)
        or new_posture == PostureMode.LOCKDOWN
    )

    return FusedDecision(
        decision_value=decision_value,
        weights_used=weights,
        signals=signals,
        dominant_mind=weights.dominant_mind,
        confidence=min(1.0, max(0.0, weighted_confidence)),
        reasoning=" | ".join(reasoning_parts) if reasoning_parts else "",
        recommended_escalation=escalation,
        contentions=contentions,
        has_contention=has_contention,
        recommended_posture=new_posture,
        posture_transition=transition,
        requires_human_review=requires_human,
    )


def fuse_signals_with_embedding_brain(
    signals: list[MindSignal],
    alert_level: float,
    current_posture: PostureMode = PostureMode.PATROL,
    threat_vectors: list | None = None,
    threat_count: int = 0,
    threat_severity_max: float = 0.0,
    threat_severity_avg: float = 0.0,
    posture_stability_hours: float = 0.0,
    signal_frequency: float = 0.0,
    drift_magnitude: float = 0.0,
    time_pressure: float = 0.0,
) -> FusedDecision:
    """Perform cognitive fusion using the ARCHON Embedding Brain.

    This is the V1 prototype embedding-enhanced fusion path. It runs the
    standard fusion pipeline but augments it with embedding brain intelligence:

    1. Standard fusion (weighted signals, contention, posture)
    2. Embedding brain parallel analysis (context-driven leadership shifts)
    3. Blended output with embedding state attached

    The embedding brain provides:
    - Context-driven leadership shifts via vector-space attention
    - Seamless posture transitions without model reloading
    - Reinforcement-ready weight updates via feedback protocol

    @ItsnotAILabs | Alpha Mind Concept | ARCHON V1 Prototype
    """
    from .embedding_brain import embedding_fuse, EmbeddingBrainOutput

    # Step 1: Standard fusion
    decision = fuse_signals(signals, alert_level, current_posture)

    # Step 2: Compute contention level for embedding context
    contention_level = 0.0
    if decision.has_contention:
        contention_level = min(1.0, len(decision.contentions) * 0.3)

    # Step 3: Embedding brain analysis
    embedding_output: EmbeddingBrainOutput = embedding_fuse(
        signals=signals,
        alert_level=alert_level,
        posture=current_posture,
        threat_vectors=threat_vectors,
        threat_count=threat_count,
        threat_severity_max=threat_severity_max,
        threat_severity_avg=threat_severity_avg,
        posture_stability_hours=posture_stability_hours,
        signal_frequency=signal_frequency,
        drift_magnitude=drift_magnitude,
        contention_level=contention_level,
        time_pressure=time_pressure,
    )

    # Step 4: Attach embedding brain state to decision
    decision.embedding_brain_active = True
    decision.embedding_leadership_mode = embedding_output.leadership_mode
    decision.embedding_dominant_coalition = embedding_output.dominant_coalition
    decision.embedding_decision_direction = embedding_output.decision_direction
    decision.embedding_attention_weights = embedding_output.attention_weights

    # Enrich metadata
    decision.metadata["embedding_brain"] = {
        "version": embedding_output.version,
        "alert_regime": embedding_output.alert_regime,
        "regime_confidence": embedding_output.regime_confidence,
        "context_stability": embedding_output.context_stability,
        "decision_magnitude": embedding_output.decision_magnitude,
        "dominant_mind_embedding": embedding_output.dominant_mind,
        "timestamp": embedding_output.timestamp,
    }

    return decision
