"""
ARCHON Cognitive Fusion Engine — Dynamic Weight Computation

Implements the core fusion algorithm:
  FusedDecision = Σ(Signal_i × DynamicWeight_i)

Where dynamic weights shift based on alert level:
  - Under HIGH alert: Hacker and Pilot rise (fast detection, action)
  - Under LOW alert: General and Strategist dominate (discipline, planning)
  - AI Intelligence remains CONSTANT (persistent oversight)

Glyph: ⚡ (fusion energy)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from .minds import MindSignal, MindType


# ---------------------------------------------------------------------------
# Weight Configuration
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
    MindType.HACKER: 0.1,       # Rises with urgency
    MindType.GENERAL: -0.05,    # Falls with urgency
    MindType.STRATEGIST: -0.05, # Falls with urgency
    MindType.PILOT: 0.1,        # Rises with urgency
    MindType.AI_INTELLIGENCE: 0.0,  # Constant
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


class FusedDecision(BaseModel):
    """The result of cognitive fusion across all five minds."""
    decision_value: float = Field(description="Weighted sum of all mind signals")
    weights_used: FusionWeights
    signals: list[MindSignal] = Field(default_factory=list)
    dominant_mind: MindType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Fusion Engine
# ---------------------------------------------------------------------------

def compute_urgency(alert_level: float) -> float:
    """Compute urgency factor from alert level (0.0 to 1.0).

    urgency = alertLevel²
    This creates non-linear escalation: low alerts have minimal effect,
    high alerts create dramatic cognitive shift.
    """
    clamped = max(0.0, min(1.0, alert_level))
    return clamped ** 2


def compute_dynamic_weights(alert_level: float) -> FusionWeights:
    """Compute dynamic weights based on current alert level.

    The algorithm applies urgency-sensitive coefficients to base weights,
    then normalizes to ensure the weights sum to 1.0.
    """
    urgency = compute_urgency(alert_level)

    raw_weights: dict[MindType, float] = {}
    for mind_type in MindType:
        base = BASE_WEIGHTS[mind_type]
        coefficient = URGENCY_COEFFICIENTS[mind_type]
        raw_weights[mind_type] = base + urgency * coefficient

    # Clamp to non-negative
    for mind_type in raw_weights:
        raw_weights[mind_type] = max(0.0, raw_weights[mind_type])

    # Normalize so weights sum to 1.0
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
    )


def fuse_signals(
    signals: list[MindSignal],
    alert_level: float,
) -> FusedDecision:
    """Perform cognitive fusion across mind signals.

    FusedDecision = Σ(Signal_i × DynamicWeight_i)

    Args:
        signals: List of signals from each mind.
        alert_level: Current operational alert level (0.0 to 1.0).

    Returns:
        FusedDecision containing the weighted decision and metadata.
    """
    weights = compute_dynamic_weights(alert_level)
    weight_map = weights.as_dict()

    # Compute weighted sum
    decision_value = 0.0
    weighted_confidence = 0.0

    for signal in signals:
        w = weight_map.get(signal.mind_type, 0.0)
        decision_value += signal.signal_value * w
        weighted_confidence += signal.confidence * w

    # Aggregate reasoning
    reasoning_parts = []
    for signal in signals:
        if signal.reasoning:
            reasoning_parts.append(
                f"[{signal.mind_type.value}] {signal.reasoning}"
            )

    return FusedDecision(
        decision_value=decision_value,
        weights_used=weights,
        signals=signals,
        dominant_mind=weights.dominant_mind,
        confidence=min(1.0, max(0.0, weighted_confidence)),
        reasoning=" | ".join(reasoning_parts) if reasoning_parts else "",
    )
