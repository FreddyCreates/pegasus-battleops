"""
ARCHON Mind Definitions — The Five-Mind Stack

Each mind represents a distinct cognitive posture:
  🔓 Hacker Mind     — exploits, pressure points, asymmetric movement
  🎖️ General Mind    — discipline, escalation, doctrine, restraint
  🗺️ Strategist Mind — second-order consequences, long-range positioning
  🛩️ Pilot Mind      — motion, orientation, terrain, real-time maneuver
  👁️ AI Intelligence — continuous observation, pattern tracking, context

Glyph: 🧠 (cognitive fusion)
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MindType(str, Enum):
    """The five cognitive modes of ARCHON."""
    HACKER = "hacker"
    GENERAL = "general"
    STRATEGIST = "strategist"
    PILOT = "pilot"
    AI_INTELLIGENCE = "ai_intelligence"


class MindSignal(BaseModel):
    """A signal produced by a single mind in response to an input context."""
    mind_type: MindType
    signal_value: float = Field(ge=-1.0, le=1.0, description="Normalized signal strength")
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    reasoning: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class MindProfile(BaseModel):
    """Static profile describing a mind's characteristics."""
    mind_type: MindType
    name: str
    glyph: str
    description: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# The Five Mind Profiles
# ---------------------------------------------------------------------------

HACKER_MIND = MindProfile(
    mind_type=MindType.HACKER,
    name="Hacker Mind",
    glyph="🔓",
    description="Detects weak points, anomalies, adversarial paths, and hidden openings. "
                "Thinks in exploits, pressure points, and asymmetric movement.",
    strengths=["anomaly detection", "exploit identification", "lateral thinking", "rapid adaptation"],
    weaknesses=["may over-prioritize offense", "can neglect doctrine"],
)

GENERAL_MIND = MindProfile(
    mind_type=MindType.GENERAL,
    name="General Mind",
    glyph="🎖️",
    description="Imposes discipline. Manages escalation, rules, boundaries, "
                "mission order, and operational restraint.",
    strengths=["discipline", "escalation control", "mission order", "boundary enforcement"],
    weaknesses=["may be too conservative", "can slow response under high urgency"],
)

STRATEGIST_MIND = MindProfile(
    mind_type=MindType.STRATEGIST,
    name="Strategist Mind",
    glyph="🗺️",
    description="Looks beyond the immediate signal. Evaluates second-order consequences, "
                "long-range positioning, and the cost of action over time.",
    strengths=["long-range planning", "consequence evaluation", "resource optimization"],
    weaknesses=["may overthink immediate threats", "can delay time-critical actions"],
)

PILOT_MIND = MindProfile(
    mind_type=MindType.PILOT,
    name="Pilot Mind",
    glyph="🛩️",
    description="Handles motion, orientation, terrain, routing, spatial awareness, "
                "and real-time maneuver logic.",
    strengths=["spatial awareness", "real-time maneuvering", "terrain routing", "fast reaction"],
    weaknesses=["may lack strategic context", "can over-focus on immediate movement"],
)

AI_INTELLIGENCE_MIND = MindProfile(
    mind_type=MindType.AI_INTELLIGENCE,
    name="AI Intelligence Mind",
    glyph="👁️",
    description="Watches continuously. Tracks patterns, compares states, monitors context, "
                "and keeps the broader field under observation.",
    strengths=["persistent oversight", "pattern recognition", "context maintenance", "state tracking"],
    weaknesses=["passive role", "may not initiate action independently"],
)

MIND_PROFILES: dict[MindType, MindProfile] = {
    MindType.HACKER: HACKER_MIND,
    MindType.GENERAL: GENERAL_MIND,
    MindType.STRATEGIST: STRATEGIST_MIND,
    MindType.PILOT: PILOT_MIND,
    MindType.AI_INTELLIGENCE: AI_INTELLIGENCE_MIND,
}
