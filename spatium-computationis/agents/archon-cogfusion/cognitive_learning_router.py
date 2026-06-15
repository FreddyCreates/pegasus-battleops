"""
🧠⚡ COGNITIVE LEARNING ROUTER — Feedback → Embedding Adapter

Bridges the Feedback Protocol to the Embedding Brain, enabling real adaptive learning.
Translates outcome signals into embedding delta vectors and propagates them to the 
cognitive layer, making the mind embeddings actually evolve based on experience.

This is the critical missing link that transforms ANIMUS from static library to 
living adaptive intelligence.

Glyph: ⟲🧠 (feedback-driven cognitive adaptation)
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ...protocols.feedback import LearningSignal, OutcomeType
from .embedding_brain import update_mind_embedding, MindType, EMBEDDING_DIM
from .minds import MIND_PROFILES


# ---------------------------------------------------------------------------
# Outcome-to-Signal Mapping
# ---------------------------------------------------------------------------

class MindRelevance(str, Enum):
    """How relevant was this mind to the outcome?"""
    PRIMARY = "primary"      # This mind led the decision
    SUPPORTING = "supporting"  # Contributed significantly
    OPPOSING = "opposing"     # Argued against outcome
    NEUTRAL = "neutral"       # Uninvolved


class CognitiveSignal(BaseModel):
    """Describes how an outcome should influence a mind's embedding."""
    mind_type: MindType
    relevance: MindRelevance
    
    # Direction and magnitude of the adjustment
    learning_signal: list[float] = Field(
        description="Direction vector for embedding update (will be normalized)"
    )
    learning_rate: float = Field(
        ge=0.001, le=0.1,
        default=0.01,
        description="How strongly to update the embedding"
    )
    
    # Context
    outcome_type: OutcomeType
    quality_score: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


# ---------------------------------------------------------------------------
# Learning Signal Generator
# ---------------------------------------------------------------------------

def generate_cognitive_signals(
    outcome_agent: str,
    outcome_type: OutcomeType,
    quality_score: float,
    learning_signal: LearningSignal,
    decision_features: dict[str, Any] | None = None,
    input_features: dict[str, Any] | None = None,
) -> list[CognitiveSignal]:
    """
    Convert a feedback outcome into cognitive signals for each mind.
    
    This is the core translation layer: outcome → embedding deltas.
    
    Args:
        outcome_agent: Which agent produced the outcome
        outcome_type: Whether it succeeded, failed, was rejected, etc.
        quality_score: How good the outcome was (0-1)
        learning_signal: REINFORCE, PENALIZE, EXPLORE, or NEUTRAL
        decision_features: Decisions that led to this outcome
        input_features: Inputs the system received
    
    Returns:
        List of cognitive signals to apply to mind embeddings
    """
    signals: list[CognitiveSignal] = []
    
    # Determine outcome sentiment
    is_success = outcome_type in (OutcomeType.SUCCESS, OutcomeType.APPROVED)
    is_failure = outcome_type in (OutcomeType.FAILURE, OutcomeType.REJECTED)
    is_correction = outcome_type == OutcomeType.CORRECTED
    
    # Base learning rate depends on outcome confidence
    base_rate = quality_score * 0.05  # Scale 0-0.05
    
    # Identify which minds were involved (heuristic based on decision features)
    decision_features = decision_features or {}
    input_features = input_features or {}
    
    # Map decision features to mind involvement
    mind_involvement = _infer_mind_involvement(decision_features, input_features)
    
    # Generate signal for each mind based on their involvement and outcome
    for mind_type in MindType:
        relevance = mind_involvement.get(mind_type, MindRelevance.NEUTRAL)
        
        if relevance == MindRelevance.NEUTRAL:
            continue
        
        # Compute learning rate adjustment based on relevance
        relevance_factor = {
            MindRelevance.PRIMARY: 1.0,
            MindRelevance.SUPPORTING: 0.7,
            MindRelevance.OPPOSING: 0.5,
            MindRelevance.NEUTRAL: 0.0,
        }[relevance]
        
        adjusted_rate = base_rate * relevance_factor
        
        # Generate direction vector
        # For successful outcomes with primary minds: move embedding in positive direction
        # For failures: move in negative direction
        # For exploration signals: move toward novelty
        
        if learning_signal == LearningSignal.REINFORCE and is_success:
            # Reinforce this mind's approach
            direction = _generate_positive_signal(mind_type, decision_features)
            signal_reasoning = f"Outcome success → reinforce {mind_type.value} approach"
        
        elif learning_signal == LearningSignal.PENALIZE or is_failure:
            # This mind's approach failed, push away
            direction = _generate_negative_signal(mind_type, decision_features)
            signal_reasoning = f"Outcome failure → penalize {mind_type.value}"
        
        elif learning_signal == LearningSignal.EXPLORE:
            # Explore: inject novelty in this mind's embedding
            direction = _generate_exploration_signal(mind_type)
            signal_reasoning = f"Explore signal → perturb {mind_type.value}"
        
        elif is_correction:
            # Human corrected the output: learn what was wrong
            direction = _generate_correction_signal(mind_type, decision_features)
            signal_reasoning = f"Human correction → adjust {mind_type.value}"
        
        else:
            # Neutral or unknown
            continue
        
        # Create the signal
        signal = CognitiveSignal(
            mind_type=mind_type,
            relevance=relevance,
            learning_signal=direction,
            learning_rate=adjusted_rate,
            outcome_type=outcome_type,
            quality_score=quality_score,
            reasoning=signal_reasoning,
        )
        
        signals.append(signal)
    
    return signals


def _infer_mind_involvement(
    decision_features: dict[str, Any],
    input_features: dict[str, Any],
) -> dict[MindType, MindRelevance]:
    """
    Infer which minds were involved in a decision based on feature analysis.
    
    Heuristic mapping:
    - High threat/urgency → Hacker, Pilot primary
    - Discipline/constraints in decision → General primary
    - Long-range signals → Strategist primary
    - Always → AI Intelligence supporting
    """
    involvement: dict[MindType, MindRelevance] = {}
    
    # Check for threat indicators
    threat_level = input_features.get("threat_level", "").lower()
    urgency = input_features.get("urgency", 0)
    threat_count = input_features.get("threat_count", 0)
    
    if threat_level in ("high", "critical") or urgency > 0.7 or threat_count > 0:
        involvement[MindType.HACKER] = MindRelevance.PRIMARY
        involvement[MindType.PILOT] = MindRelevance.PRIMARY
    
    # Check for escalation/discipline signals
    escalation_level = decision_features.get("escalation_level", "").lower()
    doctrine_basis = decision_features.get("doctrine_basis", "")
    
    if escalation_level or doctrine_basis:
        involvement[MindType.GENERAL] = MindRelevance.PRIMARY
    
    # Check for long-range planning signals
    resource_state = input_features.get("resource_state", {})
    decision_history = decision_features.get("decision_history_length", 0)
    
    if decision_history > 3 or resource_state.get("depleting"):
        involvement[MindType.STRATEGIST] = MindRelevance.PRIMARY
    
    # AI Intelligence always involved
    involvement[MindType.AI_INTELLIGENCE] = MindRelevance.SUPPORTING
    
    return involvement


def _generate_positive_signal(
    mind_type: MindType,
    decision_features: dict[str, Any],
) -> list[float]:
    """Generate a positive reinforcement signal for a mind."""
    profile = MIND_PROFILES[mind_type]
    
    # Start with a base direction in the embedding space
    signal = [0.0] * EMBEDDING_DIM
    
    # Encode the mind's priority into the signal
    priority_dim = {
        "exploit_detection": 0,
        "discipline": 8,
        "long_range": 16,
        "maneuver": 24,
        "oversight": 32,
    }.get(profile.priority.value, 0)
    
    # Set positive values along priority dimensions
    for i in range(priority_dim, min(priority_dim + 8, EMBEDDING_DIM)):
        signal[i] = 0.8
    
    return signal


def _generate_negative_signal(
    mind_type: MindType,
    decision_features: dict[str, Any],
) -> list[float]:
    """Generate a negative (penalizing) signal for a mind."""
    # Opposite of positive signal
    positive = _generate_positive_signal(mind_type, decision_features)
    return [-v for v in positive]


def _generate_exploration_signal(mind_type: MindType) -> list[float]:
    """Generate a novelty/exploration signal to perturb a mind's embedding."""
    import random
    
    # Create a random perturbation
    signal = [random.gauss(0, 0.3) for _ in range(EMBEDDING_DIM)]
    
    # Normalize
    magnitude = math.sqrt(sum(v * v for v in signal))
    if magnitude > 1e-10:
        signal = [v / magnitude for v in signal]
    
    return signal


def _generate_correction_signal(
    mind_type: MindType,
    decision_features: dict[str, Any],
) -> list[float]:
    """Generate a signal based on human corrections."""
    # Similar to negative signal but somewhat gentler
    negative = _generate_negative_signal(mind_type, decision_features)
    return [v * 0.6 for v in negative]


# ---------------------------------------------------------------------------
# Router: Apply Cognitive Signals to Embeddings
# ---------------------------------------------------------------------------

class CognitiveLearningRouter:
    """
    Routes feedback outcomes to mind embeddings, causing real cognitive adaptation.
    
    This closes the loop:
    Outcome → Cognitive Signals → Embedding Updates → Behavioral Changes
    """
    
    def __init__(self):
        self.signal_history: list[dict[str, Any]] = []
        self.max_history = 1000
    
    def route_outcome(
        self,
        outcome_agent: str,
        outcome_type: OutcomeType,
        quality_score: float,
        learning_signal: LearningSignal,
        decision_features: dict[str, Any] | None = None,
        input_features: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Route an outcome through the cognitive learning pipeline.
        
        Returns metadata about the routing and embeddings that were updated.
        """
        now = datetime.now(timezone.utc)
        
        # Generate cognitive signals
        signals = generate_cognitive_signals(
            outcome_agent=outcome_agent,
            outcome_type=outcome_type,
            quality_score=quality_score,
            learning_signal=learning_signal,
            decision_features=decision_features,
            input_features=input_features,
        )
        
        # Apply signals to embeddings
        updates: dict[str, Any] = {
            "timestamp": now.isoformat(),
            "outcome_agent": outcome_agent,
            "outcome_type": outcome_type.value,
            "signals_generated": len(signals),
            "minds_updated": [],
            "details": [],
        }
        
        for signal in signals:
            # Apply the update
            update_mind_embedding(
                mind_type=signal.mind_type,
                learning_signal=signal.learning_signal,
                learning_rate=signal.learning_rate,
            )
            
            updates["minds_updated"].append(signal.mind_type.value)
            updates["details"].append({
                "mind": signal.mind_type.value,
                "relevance": signal.relevance.value,
                "learning_rate": signal.learning_rate,
                "quality_score": signal.quality_score,
                "reasoning": signal.reasoning,
            })
        
        # Store in history
        self._record_routing(updates)
        
        return updates
    
    def _record_routing(self, routing_update: dict[str, Any]) -> None:
        """Keep a local history of routing updates for diagnostics."""
        self.signal_history.append(routing_update)
        if len(self.signal_history) > self.max_history:
            self.signal_history = self.signal_history[-self.max_history:]
    
    def get_routing_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent routing history."""
        return self.signal_history[-limit:]
    
    def get_routing_stats(self) -> dict[str, Any]:
        """Get statistics about cognitive learning routing."""
        if not self.signal_history:
            return {
                "total_routings": 0,
                "minds_updated_count": {},
                "avg_signals_per_routing": 0.0,
            }
        
        minds_updated_count: dict[str, int] = {}
        total_signals = 0
        
        for routing in self.signal_history:
            total_signals += routing["signals_generated"]
            for mind in routing["minds_updated"]:
                minds_updated_count[mind] = minds_updated_count.get(mind, 0) + 1
        
        return {
            "total_routings": len(self.signal_history),
            "minds_updated_count": minds_updated_count,
            "avg_signals_per_routing": (
                total_signals / len(self.signal_history)
                if self.signal_history else 0.0
            ),
        }


# ---------------------------------------------------------------------------
# Singleton Router Instance
# ---------------------------------------------------------------------------

_router_instance: CognitiveLearningRouter | None = None


def get_cognitive_learning_router() -> CognitiveLearningRouter:
    """Get or create the singleton cognitive learning router."""
    global _router_instance
    if _router_instance is None:
        _router_instance = CognitiveLearningRouter()
    return _router_instance
