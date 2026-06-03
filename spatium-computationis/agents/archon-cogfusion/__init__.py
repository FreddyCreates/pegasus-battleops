"""
🧠⚡ ARCHON — Codename ARCHON — Alpha Mind Warfare SDK

Five Minds. One Brain. Infinite Hosts.

ARCHON is the warfare-grade expression of Alpha Mind: an embeddable cognitive
brain designed to fuse multiple specialized reasoning modes into one deployable
intelligence layer.

Not one model. Not one agent. Not one personality. A fusion engine.

The Five-Mind Stack:
  🔓 SPECTER  — Hacker Mind: exploits, pressure points, asymmetric movement
  🎖️ IMPERATOR — General Mind: discipline, escalation, doctrine, restraint
  🗺️ ORACLE   — Strategist Mind: second-order consequences, long-range positioning
  🛩️ VECTOR   — Pilot Mind: motion, orientation, terrain, real-time maneuver
  👁️ PANOPTES — AI Intelligence: continuous observation, pattern tracking, context

The Cognitive Fusion Layer:
  Under low alert → General and Strategist dominate (discipline, planning)
  Under high alert → Hacker and Pilot rise (detection, action)
  AI Intelligence remains constant — persistent oversight across every mode.

Integration Points:
  - Nova Sovereign: Intelligence backend for mind reasoning
  - Organism Charter: Classification pipeline feeds ARCHON signals
  - Governance Hierarchy: Constrains ARCHON decisions
  - Feedback Protocol: ARCHON learns from outcomes
  - Defense System: ARCHON drives adaptive response posture

ITSNOTAILABS | Alpha Mind Concept
"""

from .minds import (
    MindType,
    MindSignal,
    MindProfile,
    CognitivePriority,
    PostureMode,
    EscalationLevel,
    ThreatVector,
    TerrainType,
    MIND_PROFILES,
    HACKER_MIND,
    GENERAL_MIND,
    STRATEGIST_MIND,
    PILOT_MIND,
    AI_INTELLIGENCE_MIND,
    get_mind_system_prompt,
    get_mind_codename,
    get_amplification_matrix,
    get_dampening_matrix,
)

from .fusion import (
    FusionWeights,
    FusedDecision,
    PostureTransition,
    ContentionResolution,
    BASE_WEIGHTS,
    URGENCY_COEFFICIENTS,
    compute_urgency,
    compute_dynamic_weights,
    fuse_signals,
    resolve_contention,
)

from .cortex import (
    CortexState,
    SituationalAwareness,
    WorkingMemory,
    ThreatMapEntry,
)

from .doctrine import (
    MissionConstraint,
    EscalationRule,
    RulesOfEngagement,
    HumanReviewGate,
    DoctrineEngine,
    ARCHON_DOCTRINE,
)

from .agent import (
    ArchonHost,
    ArchonEngine,
    register_host,
    get_host,
    create_engine,
    evaluate,
    get_cognitive_posture,
    get_decision_history,
)

__all__ = [
    # Minds
    "MindType",
    "MindSignal",
    "MindProfile",
    "CognitivePriority",
    "PostureMode",
    "EscalationLevel",
    "ThreatVector",
    "TerrainType",
    "MIND_PROFILES",
    "HACKER_MIND",
    "GENERAL_MIND",
    "STRATEGIST_MIND",
    "PILOT_MIND",
    "AI_INTELLIGENCE_MIND",
    "get_mind_system_prompt",
    "get_mind_codename",
    "get_amplification_matrix",
    "get_dampening_matrix",
    # Fusion
    "FusionWeights",
    "FusedDecision",
    "PostureTransition",
    "ContentionResolution",
    "BASE_WEIGHTS",
    "URGENCY_COEFFICIENTS",
    "compute_urgency",
    "compute_dynamic_weights",
    "fuse_signals",
    "resolve_contention",
    # Cortex
    "CortexState",
    "SituationalAwareness",
    "WorkingMemory",
    "ThreatMapEntry",
    # Doctrine
    "MissionConstraint",
    "EscalationRule",
    "RulesOfEngagement",
    "HumanReviewGate",
    "DoctrineEngine",
    "ARCHON_DOCTRINE",
    # Agent
    "ArchonHost",
    "ArchonEngine",
    "register_host",
    "get_host",
    "create_engine",
    "evaluate",
    "get_cognitive_posture",
    "get_decision_history",
]
