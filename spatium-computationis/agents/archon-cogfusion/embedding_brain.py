"""
ARCHON Embedding Brain — Vector-Space Cognitive Fusion Layer

ARCHON V1 Prototype: The Embedding Brain transforms each mind's signal into
a high-dimensional vector representation, enabling context-driven leadership
shifts through semantic similarity, vector composition, and attention-weighted
fusion rather than static arithmetic weights alone.

Core Architecture:
  - Each mind encodes its signal into an embedding vector
  - Environmental context (alert state, threat vectors, posture) encoded as context embedding
  - Relevance computed via cosine similarity between mind embeddings and context
  - Leadership shifts emerge from embedding proximity:
      Low-alert context → closer to General + Strategist embedding space
      High-alert context → closer to Hacker + Pilot embedding space
      AI Intelligence → constant baseline projection across all contexts
  - Fusion composes a unified decision embedding via attention-weighted sum

Key Advantages Over Single-Mode Systems:
  - Avoids brittleness (pure detector lacking doctrine, fast controller ignoring strategy)
  - Supports "know when to hunt, hold, plan, move, or watch"
  - Modular and embeddable: same fusion brain deploys across heterogeneous platforms
  - Seamless posture shifts without reloading models or changing host system

Implementation Notes (V1 Prototype — Early June 2026):
  - Uses learned embedding vectors per mind (initialized from cognitive profiles)
  - Attention mechanism for mode selection (softmax over cosine similarities)
  - Reinforcement-ready: weights can be updated via feedback protocol
  - Builds on Alpha Mind concept from ItsnotAILabs
  - Sovereign and recursive: no external model dependency for core fusion math

@ItsnotAILabs | Alpha Mind Concept | ARCHON V1
Glyph: 🧠⚡🔮 (embedding brain)
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
    ThreatVector,
    CognitivePriority,
    MIND_PROFILES,
)


# ---------------------------------------------------------------------------
# Embedding Dimensions & Configuration
# ---------------------------------------------------------------------------

# Embedding dimensionality for the cognitive vector space
EMBEDDING_DIM = 64

# Temperature for attention softmax (lower = sharper leadership shifts)
ATTENTION_TEMPERATURE = 0.25

# AI Intelligence constant projection strength (never suppressed)
AI_INTELLIGENCE_FLOOR = 0.15

# Context encoding feature indices
CONTEXT_FEATURES = [
    "alert_level", "urgency", "threat_count", "threat_severity_max",
    "threat_severity_avg", "posture_stability", "signal_frequency",
    "drift_magnitude", "contention_level", "time_pressure",
]


# ---------------------------------------------------------------------------
# Mind Embedding Vectors (Learned Initialization from Cognitive Profiles)
# ---------------------------------------------------------------------------

def _init_mind_embedding(mind_type: MindType) -> list[float]:
    """Initialize a mind's embedding vector from its cognitive profile.

    Each mind occupies a distinct region of the embedding space based on
    its cognitive priority, strengths, and behavioral characteristics.
    The initialization encodes the mind's "cognitive DNA" into vector form.

    In production, these embeddings are refined via the feedback protocol.
    """
    vec = [0.0] * EMBEDDING_DIM
    profile = MIND_PROFILES[mind_type]

    # Seed from mind type ordinal for deterministic initialization
    seed_offset = list(MindType).index(mind_type) * (EMBEDDING_DIM // 5)

    # Priority encoding (first 8 dimensions)
    priority_map = {
        CognitivePriority.EXPLOIT_DETECTION: [0.9, 0.8, 0.2, 0.1, 0.7, 0.6, 0.3, 0.9],
        CognitivePriority.DISCIPLINE: [0.2, 0.3, 0.9, 0.8, 0.1, 0.2, 0.8, 0.1],
        CognitivePriority.LONG_RANGE: [0.1, 0.4, 0.7, 0.9, 0.3, 0.1, 0.9, 0.2],
        CognitivePriority.MANEUVER: [0.8, 0.7, 0.1, 0.2, 0.9, 0.8, 0.2, 0.7],
        CognitivePriority.OVERSIGHT: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    }
    priority_vec = priority_map[profile.priority]
    for i, v in enumerate(priority_vec):
        vec[i] = v

    # Urgency response profile (dimensions 8-15)
    # High-alert minds (Hacker, Pilot) have high values here
    # Low-alert minds (General, Strategist) have low values
    urgency_profiles = {
        MindType.HACKER: [0.9, 0.85, 0.7, 0.8, 0.75, 0.9, 0.6, 0.85],
        MindType.GENERAL: [0.1, 0.2, 0.3, 0.15, 0.2, 0.1, 0.25, 0.15],
        MindType.STRATEGIST: [0.15, 0.25, 0.2, 0.1, 0.3, 0.15, 0.2, 0.1],
        MindType.PILOT: [0.85, 0.9, 0.75, 0.8, 0.85, 0.7, 0.8, 0.9],
        MindType.AI_INTELLIGENCE: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    }
    for i, v in enumerate(urgency_profiles[mind_type]):
        vec[8 + i] = v

    # Stability/patience profile (dimensions 16-23)
    # Low-alert minds (General, Strategist) have high values here
    stability_profiles = {
        MindType.HACKER: [0.2, 0.3, 0.15, 0.25, 0.2, 0.3, 0.1, 0.2],
        MindType.GENERAL: [0.9, 0.85, 0.8, 0.9, 0.85, 0.9, 0.8, 0.85],
        MindType.STRATEGIST: [0.85, 0.9, 0.85, 0.8, 0.9, 0.85, 0.9, 0.8],
        MindType.PILOT: [0.25, 0.2, 0.3, 0.2, 0.15, 0.25, 0.2, 0.15],
        MindType.AI_INTELLIGENCE: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    }
    for i, v in enumerate(stability_profiles[mind_type]):
        vec[16 + i] = v

    # Interaction dynamics encoding (dimensions 24-31)
    # Encodes amplification/dampening relationships
    interaction_vec = [0.0] * 8
    for i, ally in enumerate(profile.amplifies[:4]):
        ally_idx = list(MindType).index(ally)
        interaction_vec[i] = 0.7 + ally_idx * 0.05
    for i, comp in enumerate(profile.dampens[:4]):
        comp_idx = list(MindType).index(comp)
        interaction_vec[4 + i] = -(0.3 + comp_idx * 0.05)
    for i, v in enumerate(interaction_vec):
        vec[24 + i] = v

    # Threat sensitivity profile (dimensions 32-41)
    # How responsive this mind is to each threat vector category
    threat_sensitivity = {
        MindType.HACKER: [0.9, 0.95, 0.85, 0.8, 0.9, 0.85, 0.7, 0.6, 0.8, 0.9],
        MindType.GENERAL: [0.3, 0.4, 0.5, 0.3, 0.4, 0.5, 0.6, 0.3, 0.4, 0.3],
        MindType.STRATEGIST: [0.5, 0.4, 0.3, 0.5, 0.6, 0.4, 0.5, 0.7, 0.8, 0.5],
        MindType.PILOT: [0.6, 0.5, 0.4, 0.7, 0.5, 0.4, 0.8, 0.3, 0.4, 0.6],
        MindType.AI_INTELLIGENCE: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    }
    for i, v in enumerate(threat_sensitivity[mind_type]):
        vec[32 + i] = v

    # Posture affinity encoding (dimensions 42-48)
    # How much this mind "wants" each posture
    posture_affinity = {
        MindType.HACKER: [0.2, 0.5, 0.7, 0.9, 1.0, 0.3, 0.1],
        MindType.GENERAL: [0.6, 0.8, 0.7, 0.5, 0.4, 0.9, 1.0],
        MindType.STRATEGIST: [0.7, 0.8, 0.6, 0.4, 0.3, 0.9, 0.5],
        MindType.PILOT: [0.1, 0.4, 0.6, 0.9, 1.0, 0.2, 0.1],
        MindType.AI_INTELLIGENCE: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    }
    for i, v in enumerate(posture_affinity[mind_type]):
        vec[42 + i] = v

    # Remaining dimensions (49-63): reserved for learned refinement
    # Initialize with mind-specific noise for separation
    for i in range(49, EMBEDDING_DIM):
        # Deterministic pseudo-random based on mind index and dimension
        val = math.sin(seed_offset * 0.1 + i * 0.37) * 0.3 + 0.5
        vec[i] = max(0.0, min(1.0, val))

    # Normalize to unit vector
    magnitude = math.sqrt(sum(v * v for v in vec))
    if magnitude > 1e-10:
        vec = [v / magnitude for v in vec]

    return vec


# Pre-computed mind embeddings
MIND_EMBEDDINGS: dict[MindType, list[float]] = {
    mind_type: _init_mind_embedding(mind_type)
    for mind_type in MindType
}


# ---------------------------------------------------------------------------
# Context Embedding
# ---------------------------------------------------------------------------

def encode_context(
    alert_level: float,
    posture: PostureMode,
    threat_vectors: list[ThreatVector] | None = None,
    threat_count: int = 0,
    threat_severity_max: float = 0.0,
    threat_severity_avg: float = 0.0,
    posture_stability_hours: float = 0.0,
    signal_frequency: float = 0.0,
    drift_magnitude: float = 0.0,
    contention_level: float = 0.0,
    time_pressure: float = 0.0,
) -> list[float]:
    """Encode the current environmental context into an embedding vector.

    The context embedding captures the operational state so that mind
    relevance can be computed via similarity. Under high-alert contexts,
    the context vector naturally moves toward the Hacker/Pilot region
    of embedding space. Under low-alert, it moves toward General/Strategist.

    AI Intelligence's embedding is designed to maintain constant proximity
    to all context regions (centroid position).
    """
    vec = [0.0] * EMBEDDING_DIM
    urgency = alert_level ** 2  # Non-linear urgency escalation

    # Priority encoding (dimensions 0-7): blend based on urgency
    # High urgency → exploit/maneuver priorities; Low urgency → discipline/long-range
    high_alert_priority = [0.85, 0.75, 0.15, 0.15, 0.8, 0.7, 0.25, 0.8]
    low_alert_priority = [0.15, 0.35, 0.85, 0.85, 0.2, 0.15, 0.85, 0.15]
    for i in range(8):
        vec[i] = low_alert_priority[i] * (1 - urgency) + high_alert_priority[i] * urgency

    # Urgency response (dimensions 8-15): direct urgency encoding
    for i in range(8):
        vec[8 + i] = urgency * 0.9 + 0.05

    # Stability (dimensions 16-23): inverse of urgency
    stability = 1.0 - urgency
    for i in range(8):
        vec[16 + i] = stability * 0.85 + 0.05

    # Interaction context (dimensions 24-31): based on contention/cooperation
    cooperation = 1.0 - contention_level
    for i in range(4):
        vec[24 + i] = cooperation * 0.7
    for i in range(4):
        vec[28 + i] = -contention_level * 0.5

    # Threat vector encoding (dimensions 32-41)
    if threat_vectors:
        threat_indices = [list(ThreatVector).index(tv) for tv in threat_vectors]
        for idx in threat_indices:
            if idx < 10:
                vec[32 + idx] = min(1.0, threat_severity_max)
    # Also encode general threat presence
    threat_factor = min(1.0, threat_count * 0.15)
    for i in range(32, 42):
        vec[i] = max(vec[i], threat_factor * 0.5)

    # Posture encoding (dimensions 42-48)
    posture_idx = list(PostureMode).index(posture)
    if posture_idx < 7:
        vec[42 + posture_idx] = 1.0
    # Also spread some activation to adjacent postures
    if posture_idx > 0 and posture_idx < 8:
        vec[42 + posture_idx - 1] = 0.3
    if posture_idx < 6:
        vec[42 + posture_idx + 1] = 0.3

    # Environmental features (dimensions 49-63)
    env_features = [
        alert_level,
        urgency,
        min(1.0, threat_count / 10.0),
        threat_severity_max,
        threat_severity_avg,
        min(1.0, posture_stability_hours / 24.0),
        min(1.0, signal_frequency / 100.0),
        drift_magnitude,
        contention_level,
        time_pressure,
        # Derived features
        alert_level * threat_severity_max,  # Compound threat indicator
        (1.0 - alert_level) * (1.0 - contention_level),  # Stability indicator
        urgency * time_pressure,  # Crisis indicator
        stability * posture_stability_hours / 24.0,  # Calm indicator
        math.tanh(threat_count * threat_severity_avg),  # Threat saturation
    ]
    for i, v in enumerate(env_features[:EMBEDDING_DIM - 49]):
        vec[49 + i] = max(-1.0, min(1.0, v))

    # Normalize
    magnitude = math.sqrt(sum(v * v for v in vec))
    if magnitude > 1e-10:
        vec = [v / magnitude for v in vec]

    return vec


# ---------------------------------------------------------------------------
# Attention Mechanism — Context-Driven Leadership Selection
# ---------------------------------------------------------------------------

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a < 1e-10 or mag_b < 1e-10:
        return 0.0
    return dot / (mag_a * mag_b)


def compute_attention_weights(
    context_embedding: list[float],
    mind_embeddings: dict[MindType, list[float]] | None = None,
    temperature: float = ATTENTION_TEMPERATURE,
) -> dict[MindType, float]:
    """Compute attention weights via softmax over cosine similarities.

    This is the core of the embedding brain: context-driven leadership shifts
    emerge from the geometric relationship between the current context
    embedding and each mind's position in vector space.

    Low-alert contexts produce embeddings closer to General + Strategist.
    High-alert contexts produce embeddings closer to Hacker + Pilot.
    AI Intelligence maintains constant proximity (centroid design).

    The temperature parameter controls sharpness of leadership selection:
    - Low temperature → sharp winner-take-most (decisive leadership)
    - High temperature → distributed attention (collaborative mode)
    """
    if mind_embeddings is None:
        mind_embeddings = MIND_EMBEDDINGS

    # Compute similarities
    similarities: dict[MindType, float] = {}
    for mind_type, embedding in mind_embeddings.items():
        sim = cosine_similarity(context_embedding, embedding)
        similarities[mind_type] = sim

    # Apply temperature-scaled softmax
    # Shift by max for numerical stability
    max_sim = max(similarities.values())
    exp_sims: dict[MindType, float] = {}
    for mind_type, sim in similarities.items():
        exp_sims[mind_type] = math.exp((sim - max_sim) / temperature)

    # Ensure AI Intelligence floor
    total = sum(exp_sims.values())
    weights: dict[MindType, float] = {}
    for mind_type, exp_sim in exp_sims.items():
        weights[mind_type] = exp_sim / total if total > 0 else 0.2

    # Apply AI Intelligence floor guarantee
    if weights[MindType.AI_INTELLIGENCE] < AI_INTELLIGENCE_FLOOR:
        deficit = AI_INTELLIGENCE_FLOOR - weights[MindType.AI_INTELLIGENCE]
        weights[MindType.AI_INTELLIGENCE] = AI_INTELLIGENCE_FLOOR
        # Redistribute deficit proportionally from other minds
        other_total = sum(w for mt, w in weights.items() if mt != MindType.AI_INTELLIGENCE)
        if other_total > 0:
            for mt in weights:
                if mt != MindType.AI_INTELLIGENCE:
                    weights[mt] -= deficit * (weights[mt] / other_total)
                    weights[mt] = max(0.01, weights[mt])

    # Final normalization
    total = sum(weights.values())
    if total > 1e-10:
        weights = {mt: w / total for mt, w in weights.items()}

    return weights


# ---------------------------------------------------------------------------
# Embedding Brain Models
# ---------------------------------------------------------------------------

class EmbeddingFusionState(BaseModel):
    """Complete state of the embedding brain at fusion time."""
    context_embedding: list[float] = Field(default_factory=list)
    mind_embeddings_used: dict[str, list[float]] = Field(default_factory=dict)
    attention_weights: dict[str, float] = Field(default_factory=dict)
    similarities: dict[str, float] = Field(default_factory=dict)
    leadership_mode: str = "distributed"
    dominant_coalition: list[str] = Field(default_factory=list)
    temperature_used: float = ATTENTION_TEMPERATURE
    embedding_dim: int = EMBEDDING_DIM


class EmbeddingBrainOutput(BaseModel):
    """Output of the embedding brain fusion process.

    Contains both the fused decision vector and the full cognitive state
    that produced it, enabling introspection and feedback-driven learning.
    """
    # Fused output
    fused_embedding: list[float] = Field(default_factory=list)
    decision_magnitude: float = 0.0
    decision_direction: str = ""  # "engage", "hold", "observe", "maneuver", "plan"

    # Attention state
    attention_weights: dict[str, float] = Field(default_factory=dict)
    dominant_mind: str = ""
    dominant_coalition: list[str] = Field(default_factory=list)
    leadership_mode: str = "distributed"

    # Context analysis
    alert_regime: str = "low"  # "low", "medium", "high", "critical"
    context_stability: float = 0.0
    regime_confidence: float = 0.0

    # Embedding brain state (for feedback/learning)
    fusion_state: EmbeddingFusionState = Field(default_factory=EmbeddingFusionState)

    # Metadata
    timestamp: str = ""
    version: str = "v1_prototype"


# ---------------------------------------------------------------------------
# Leadership Mode Detection
# ---------------------------------------------------------------------------

def _detect_leadership_mode(
    weights: dict[MindType, float],
) -> tuple[str, list[str]]:
    """Detect the current leadership mode from attention weights.

    Modes:
    - "tactical": Hacker + Pilot dominate (high-alert)
    - "strategic": General + Strategist dominate (low-alert)
    - "balanced": No strong dominance (transition state)
    - "distributed": All minds roughly equal (rare, indicates uncertainty)
    """
    hacker_pilot = weights.get(MindType.HACKER, 0) + weights.get(MindType.PILOT, 0)
    general_strat = weights.get(MindType.GENERAL, 0) + weights.get(MindType.STRATEGIST, 0)

    sorted_minds = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    top_two = [m.value for m, _ in sorted_minds[:2]]

    if hacker_pilot > 0.55:
        return "tactical", top_two
    elif general_strat > 0.55:
        return "strategic", top_two
    elif max(weights.values()) - min(weights.values()) < 0.1:
        return "distributed", top_two
    else:
        return "balanced", top_two


def _detect_alert_regime(alert_level: float) -> tuple[str, float]:
    """Classify the current alert regime with confidence."""
    if alert_level >= 0.8:
        return "critical", min(1.0, (alert_level - 0.8) / 0.2 * 0.5 + 0.5)
    elif alert_level >= 0.5:
        return "high", min(1.0, (alert_level - 0.5) / 0.3 * 0.5 + 0.5)
    elif alert_level >= 0.25:
        return "medium", min(1.0, (alert_level - 0.25) / 0.25 * 0.5 + 0.5)
    else:
        return "low", min(1.0, (0.25 - alert_level) / 0.25 * 0.5 + 0.5)


def _determine_decision_direction(
    fused_embedding: list[float],
    leadership_mode: str,
    alert_regime: str,
) -> str:
    """Determine the overall decision direction from the fused embedding.

    Maps the fused vector back to an actionable intent:
    - "engage": Active response (tactical + high alert)
    - "hold": Disciplined restraint (strategic + medium alert)
    - "observe": Passive monitoring (any + low alert)
    - "maneuver": Positional movement (pilot-dominant)
    - "plan": Long-term positioning (strategist-dominant)
    """
    if not fused_embedding:
        return "observe"

    # Use urgency dimensions (8-15) magnitude as action indicator
    urgency_magnitude = math.sqrt(
        sum(v * v for v in fused_embedding[8:16])
    ) if len(fused_embedding) > 16 else 0.0

    stability_magnitude = math.sqrt(
        sum(v * v for v in fused_embedding[16:24])
    ) if len(fused_embedding) > 24 else 0.0

    if leadership_mode == "tactical" and alert_regime in ("high", "critical"):
        return "engage"
    elif leadership_mode == "tactical" and urgency_magnitude > stability_magnitude:
        return "maneuver"
    elif leadership_mode == "strategic" and alert_regime == "low":
        return "plan"
    elif leadership_mode == "strategic":
        return "hold"
    elif alert_regime in ("high", "critical"):
        return "engage"
    else:
        return "observe"


# ---------------------------------------------------------------------------
# Embedding Brain — Core Fusion Function
# ---------------------------------------------------------------------------

def embedding_fuse(
    signals: list[MindSignal],
    alert_level: float,
    posture: PostureMode = PostureMode.PATROL,
    threat_vectors: list[ThreatVector] | None = None,
    threat_count: int = 0,
    threat_severity_max: float = 0.0,
    threat_severity_avg: float = 0.0,
    posture_stability_hours: float = 0.0,
    signal_frequency: float = 0.0,
    drift_magnitude: float = 0.0,
    contention_level: float = 0.0,
    time_pressure: float = 0.0,
    temperature: float = ATTENTION_TEMPERATURE,
) -> EmbeddingBrainOutput:
    """Perform embedding-based cognitive fusion across mind signals.

    This is the primary function of the ARCHON Embedding Brain. It:

    1. Encodes the environmental context into embedding space
    2. Computes attention weights via cosine similarity (leadership selection)
    3. Fuses mind signal embeddings via attention-weighted composition
    4. Detects leadership mode and alert regime
    5. Determines decision direction from fused vector

    Context-Driven Leadership Shifts:
      - Low-alert states: Context embedding naturally closer to General + Strategist
        → Prioritizes order, patience, doctrine, and long-term planning
      - High-alert states: Context embedding shifts toward Hacker + Pilot
        → Elevates rapid exploit recognition, adaptation, and maneuver
      - AI Intelligence: Centroid embedding maintains constant baseline presence

    Fusion Process:
      - Inputs from environment processed in parallel by specialized minds
      - Fusion layer evaluates relevance via embedding similarity
      - Composes unified output by blending insights weighted by attention
      - Enables seamless posture shifts without reloading models

    Args:
        signals: Mind signals from the five-mind stack
        alert_level: Current alert level (0.0-1.0)
        posture: Current operational posture
        threat_vectors: Active threat vector types
        threat_count: Number of active threats
        threat_severity_max: Maximum threat severity
        threat_severity_avg: Average threat severity
        posture_stability_hours: Hours in current posture
        signal_frequency: Recent signal frequency
        drift_magnitude: Baseline drift magnitude
        contention_level: Inter-mind contention (0.0-1.0)
        time_pressure: Time pressure factor (0.0-1.0)
        temperature: Attention temperature (lower = sharper shifts)

    Returns:
        EmbeddingBrainOutput with full cognitive state and decision
    """
    now = datetime.now(timezone.utc)

    # Step 1: Encode context into embedding space
    context_embedding = encode_context(
        alert_level=alert_level,
        posture=posture,
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

    # Step 2: Compute attention weights (context-driven leadership selection)
    attention_weights = compute_attention_weights(
        context_embedding, temperature=temperature
    )

    # Step 3: Signal-modulated embedding fusion
    # Each mind's contribution = its embedding × attention weight × signal strength
    fused_embedding = [0.0] * EMBEDDING_DIM
    signal_map = {s.mind_type: s for s in signals}

    for mind_type in MindType:
        weight = attention_weights[mind_type]
        mind_emb = MIND_EMBEDDINGS[mind_type]

        # Modulate by signal if available
        signal = signal_map.get(mind_type)
        if signal:
            signal_strength = (1.0 + signal.signal_value) / 2.0  # Normalize to 0-1
            confidence_mod = signal.confidence
            # Urgency override amplifies contribution
            urgency_boost = 1.5 if signal.urgency_override else 1.0
            modulation = signal_strength * confidence_mod * urgency_boost
        else:
            modulation = 0.5  # Neutral contribution for missing signals

        # Accumulate weighted embedding
        for i in range(EMBEDDING_DIM):
            fused_embedding[i] += mind_emb[i] * weight * modulation

    # Normalize fused embedding
    magnitude = math.sqrt(sum(v * v for v in fused_embedding))
    if magnitude > 1e-10:
        fused_embedding = [v / magnitude for v in fused_embedding]

    # Step 4: Detect leadership mode and alert regime
    leadership_mode, dominant_coalition = _detect_leadership_mode(attention_weights)
    alert_regime, regime_confidence = _detect_alert_regime(alert_level)

    # Step 5: Decision direction
    decision_direction = _determine_decision_direction(
        fused_embedding, leadership_mode, alert_regime
    )

    # Compute context stability (how "settled" the context is)
    context_stability = 1.0 - (alert_level * 0.4 + contention_level * 0.3 + drift_magnitude * 0.3)

    # Compute similarities for diagnostics
    similarities = {
        mt.value: cosine_similarity(context_embedding, MIND_EMBEDDINGS[mt])
        for mt in MindType
    }

    # Dominant mind
    dominant_mind = max(attention_weights, key=attention_weights.get)  # type: ignore[arg-type]

    # Build fusion state
    fusion_state = EmbeddingFusionState(
        context_embedding=context_embedding,
        mind_embeddings_used={mt.value: emb for mt, emb in MIND_EMBEDDINGS.items()},
        attention_weights={mt.value: w for mt, w in attention_weights.items()},
        similarities=similarities,
        leadership_mode=leadership_mode,
        dominant_coalition=dominant_coalition,
        temperature_used=temperature,
        embedding_dim=EMBEDDING_DIM,
    )

    return EmbeddingBrainOutput(
        fused_embedding=fused_embedding,
        decision_magnitude=magnitude,
        decision_direction=decision_direction,
        attention_weights={mt.value: w for mt, w in attention_weights.items()},
        dominant_mind=dominant_mind.value,
        dominant_coalition=dominant_coalition,
        leadership_mode=leadership_mode,
        alert_regime=alert_regime,
        context_stability=max(0.0, min(1.0, context_stability)),
        regime_confidence=regime_confidence,
        fusion_state=fusion_state,
        timestamp=now.isoformat(),
    )


# ---------------------------------------------------------------------------
# Embedding Brain Integration with Existing Fusion
# ---------------------------------------------------------------------------

def embedding_enhanced_weights(
    alert_level: float,
    posture: PostureMode = PostureMode.PATROL,
    signals: list[MindSignal] | None = None,
    threat_vectors: list[ThreatVector] | None = None,
    threat_count: int = 0,
    threat_severity_max: float = 0.0,
    blend_factor: float = 0.6,
) -> dict[MindType, float]:
    """Compute fusion weights using embedding brain, blended with traditional weights.

    This provides a drop-in replacement for compute_dynamic_weights that
    uses the embedding brain's attention mechanism while maintaining
    backward compatibility with the existing fusion pipeline.

    Args:
        alert_level: Current alert level
        posture: Current posture
        signals: Optional mind signals for modulation
        threat_vectors: Active threat types
        threat_count: Number of active threats
        threat_severity_max: Max threat severity
        blend_factor: How much to weight embedding vs traditional (0=all traditional, 1=all embedding)

    Returns:
        Dict of MindType → weight (sums to 1.0)
    """
    from .fusion import compute_dynamic_weights

    # Embedding-derived weights
    context_emb = encode_context(
        alert_level=alert_level,
        posture=posture,
        threat_vectors=threat_vectors,
        threat_count=threat_count,
        threat_severity_max=threat_severity_max,
    )
    embedding_weights = compute_attention_weights(context_emb)

    # Traditional weights
    traditional = compute_dynamic_weights(alert_level, posture)
    trad_weights = traditional.as_dict()

    # Blend
    blended: dict[MindType, float] = {}
    for mt in MindType:
        blended[mt] = (
            embedding_weights[mt] * blend_factor
            + trad_weights[mt] * (1.0 - blend_factor)
        )

    # Normalize
    total = sum(blended.values())
    if total > 1e-10:
        blended = {mt: w / total for mt, w in blended.items()}

    return blended


# ---------------------------------------------------------------------------
# Feedback Interface (Reinforcement-Ready)
# ---------------------------------------------------------------------------

def update_mind_embedding(
    mind_type: MindType,
    learning_signal: list[float],
    learning_rate: float = 0.01,
) -> None:
    """Update a mind's embedding based on feedback signal.

    This enables the embedding brain to learn from the feedback protocol.
    When a decision outcome is recorded, the relevant mind embeddings
    can be nudged toward or away from the context that produced that decision.

    Args:
        mind_type: Which mind to update
        learning_signal: Direction to nudge the embedding
        learning_rate: Step size for the update
    """
    current = MIND_EMBEDDINGS[mind_type]
    updated = [
        c + learning_rate * l
        for c, l in zip(current, learning_signal[:EMBEDDING_DIM])
    ]

    # Re-normalize
    magnitude = math.sqrt(sum(v * v for v in updated))
    if magnitude > 1e-10:
        updated = [v / magnitude for v in updated]

    MIND_EMBEDDINGS[mind_type] = updated


def get_embedding_diagnostic() -> dict[str, Any]:
    """Return diagnostic information about the embedding brain state.

    Useful for introspection, debugging, and monitoring embedding drift.
    """
    # Compute pairwise similarities
    pairwise: dict[str, float] = {}
    minds = list(MindType)
    for i, m1 in enumerate(minds):
        for m2 in minds[i + 1:]:
            sim = cosine_similarity(MIND_EMBEDDINGS[m1], MIND_EMBEDDINGS[m2])
            pairwise[f"{m1.value}_x_{m2.value}"] = round(sim, 4)

    return {
        "embedding_dim": EMBEDDING_DIM,
        "attention_temperature": ATTENTION_TEMPERATURE,
        "ai_intelligence_floor": AI_INTELLIGENCE_FLOOR,
        "mind_embedding_norms": {
            mt.value: round(math.sqrt(sum(v * v for v in MIND_EMBEDDINGS[mt])), 4)
            for mt in MindType
        },
        "pairwise_similarities": pairwise,
        "version": "v1_prototype",
        "architecture": "alpha_mind_embedding_brain",
        "lab": "ItsnotAILabs",
    }
