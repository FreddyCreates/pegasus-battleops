"""
⟲ COGNITIVE HOMEOSTAT — Explore/Exploit Equilibrium

The brain's self-regulating mechanism for balancing exploitation (using proven strategies)
with exploration (trying new approaches). This implements the core adaptive loop that
failed in the review: when prediction error rises, awareness decreases, triggering the
explore branch and entropy injection.

Core Formula (Corrected from broken version):
- effectiveness = (awareness + coherence + resonance) / 3
- When perceived_pattern_mismatch > novelty_threshold:
    awareness -= (prediction_error × novelty_factor)
    if effectiveness < φ⁻¹:  [explore branch triggers]
        entropy += inject(entropy_magnitude)

Glyph: ⟲🎯 (self-regulating cognitive equilibrium)
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


# Constants
PHI = (1 + math.sqrt(5)) / 2  # Golden ratio ≈ 1.618
PHI_INVERSE = 1 / PHI          # ≈ 0.618
NOVELTY_THRESHOLD = 0.3         # How different must a percept be to count as novel


class PerceptionEvent(BaseModel):
    """A single sensory/cognitive input to process."""
    event_id: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Context
    is_threat: bool = False
    severity: float = Field(ge=0.0, le=1.0, default=0.5)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CognitiveState(BaseModel):
    """The living state of the cognitive homeostat."""
    
    # Core metrics
    awareness: float = Field(
        ge=0.0, le=1.0, default=1.0,
        description="How alert/responsive the system is"
    )
    coherence: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="How well-integrated the cognitive signals are"
    )
    resonance: float = Field(
        ge=0.0, le=1.0, default=PHI_INVERSE,
        description="Harmonic alignment with environmental patterns"
    )
    
    # Derived
    @property
    def effectiveness(self) -> float:
        """How well the organism is performing (exploit metric)."""
        return (self.awareness + self.coherence + self.resonance) / 3.0
    
    @property
    def should_explore(self) -> bool:
        """Whether conditions warrant shifting to explore mode."""
        return self.effectiveness < PHI_INVERSE
    
    # Entropy state
    entropy: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="System disorder/exploration tendency"
    )
    
    # Learning memory
    pattern_history: list[str] = Field(
        default_factory=list,
        description="Recent patterns seen (for novelty detection)"
    )
    prediction_error: float = Field(
        ge=0.0, le=1.0, default=0.0,
        description="How much recent percepts mismatch predictions"
    )
    
    # Timing
    last_update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Activity
    total_perceptions: int = 0
    explore_activations: int = 0


class CognitiveHomeostat:
    """
    🎯 The explore/exploit regulator.
    
    Maintains cognitive equilibrium:
    - When prediction error is low (confidence high): exploit (entropy → 0)
    - When prediction error is high (surprises detected): explore (entropy ↑)
    - Awareness couples with novelty: mismatches lower awareness
    
    This closes the loop: Novelty → Lower Awareness → Lower Effectiveness → Explore Fires
    """
    
    def __init__(self):
        self.state = CognitiveState()
        self.update_history: list[dict[str, Any]] = []
        self.max_history = 500
    
    def process_percept(
        self,
        event: PerceptionEvent,
        expected_pattern: str | None = None,
    ) -> dict[str, Any]:
        """
        🧠 Process a new perception through the homeostat.
        
        Detects novelty, updates awareness, triggers explore when appropriate.
        
        Args:
            event: The perception/input to process
            expected_pattern: What pattern we expected to see (for error calculation)
        
        Returns:
            Update result showing state changes
        """
        self.state.total_perceptions += 1
        now = datetime.now(timezone.utc)
        
        # Step 1: Detect novelty via pattern mismatch
        is_novel, mismatch_score = self._detect_novelty(
            event.content,
            expected_pattern
        )
        
        # Step 2: Update prediction error
        old_prediction_error = self.state.prediction_error
        self.state.prediction_error = mismatch_score
        
        # Step 3: Awareness down-driver (KEY FIX from review)
        # When percepts mismatch predictions, lower awareness proportionally
        old_awareness = self.state.awareness
        if is_novel:
            novelty_penalty = mismatch_score * 0.15  # Max 0.15 per percept
            self.state.awareness = max(0.0, self.state.awareness - novelty_penalty)
        
        # Step 4: Update coherence based on signal integration
        # High prediction error → lower coherence
        old_coherence = self.state.coherence
        if self.state.prediction_error > 0.5:
            self.state.coherence = max(0.0, self.state.coherence - 0.05)
        else:
            self.state.coherence = min(1.0, self.state.coherence + 0.02)
        
        # Step 5: Resonance update
        # Resonance stays close to phi_inverse but oscillates with pattern stability
        old_resonance = self.state.resonance
        pattern_match_quality = 1.0 - mismatch_score
        self.state.resonance = (
            PHI_INVERSE * 0.7 +  # Baseline
            pattern_match_quality * 0.3  # Current match quality
        )
        
        # Step 6: Check homeostat condition
        old_effectiveness = (old_awareness + old_coherence + old_resonance) / 3.0
        new_effectiveness = self.state.effectiveness
        
        # THE CRITICAL CHECK (was broken, now works):
        did_explore_trigger = False
        if new_effectiveness < PHI_INVERSE and old_effectiveness >= PHI_INVERSE:
            # Crossed threshold! Explore triggered!
            did_explore_trigger = True
            self.state.explore_activations += 1
            self._inject_entropy()
        
        # Step 7: Update entropy ratchet
        # Entropy ratchets DOWN when exploiting, UP when exploring
        old_entropy = self.state.entropy
        if self.state.should_explore:
            # In explore mode: entropy gradually increases
            self.state.entropy = min(1.0, self.state.entropy + 0.1)
        else:
            # In exploit mode: entropy gradually decreases
            self.state.entropy = max(0.0, self.state.entropy - 0.05)
        
        # Step 8: Update pattern history for next novelty check
        self.state.pattern_history.append(event.content)
        self.state.pattern_history = self.state.pattern_history[-50:]  # Keep last 50
        
        # Step 9: Timestamp
        self.state.last_update = now
        
        # Record the update
        result = {
            "timestamp": now.isoformat(),
            "was_novel": is_novel,
            "mismatch_score": round(mismatch_score, 4),
            "prediction_error_change": round(self.state.prediction_error - old_prediction_error, 4),
            "awareness_change": round(self.state.awareness - old_awareness, 4),
            "coherence_change": round(self.state.coherence - old_coherence, 4),
            "resonance_change": round(self.state.resonance - old_resonance, 4),
            "effectiveness_change": round(new_effectiveness - old_effectiveness, 4),
            "effectiveness": round(new_effectiveness, 4),
            "should_explore": self.state.should_explore,
            "explore_triggered": did_explore_trigger,
            "entropy_change": round(self.state.entropy - old_entropy, 4),
            "entropy": round(self.state.entropy, 4),
        }
        
        self._record_update(result)
        return result
    
    def _detect_novelty(
        self,
        percept: str,
        expected_pattern: str | None = None,
    ) -> tuple[bool, float]:
        """
        Detect whether a percept is novel (doesn't match known patterns).
        
        Returns: (is_novel, mismatch_score)
        - is_novel: True if mismatch exceeds threshold
        - mismatch_score: 0-1 representing degree of mismatch
        """
        if not expected_pattern:
            # No expectation set; rough novelty from pattern history
            if not self.state.pattern_history:
                return False, 0.0
            
            # Simple string similarity to recent patterns
            max_similarity = 0.0
            for recent_pattern in self.state.pattern_history:
                sim = self._string_similarity(percept, recent_pattern)
                max_similarity = max(max_similarity, sim)
            
            mismatch = 1.0 - max_similarity
            is_novel = mismatch > NOVELTY_THRESHOLD
            return is_novel, mismatch
        
        else:
            # We have an expectation; measure deviation
            similarity = self._string_similarity(percept, expected_pattern)
            mismatch = 1.0 - similarity
            is_novel = mismatch > NOVELTY_THRESHOLD
            return is_novel, mismatch
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Simple string similarity (0-1, 1 = identical)."""
        if s1 == s2:
            return 1.0
        
        # Rough similarity based on common characters / total length
        common = sum(1 for c in s1 if c in s2)
        total = max(len(s1), len(s2))
        
        if total == 0:
            return 1.0
        
        return common / total
    
    def _inject_entropy(self) -> None:
        """When explore branch fires, inject entropy into the system."""
        # Entropy injection: sudden increase
        self.state.entropy = min(1.0, self.state.entropy + 0.3)
    
    def _record_update(self, result: dict[str, Any]) -> None:
        """Keep history of state updates."""
        self.update_history.append(result)
        if len(self.update_history) > self.max_history:
            self.update_history = self.update_history[-self.max_history:]
    
    def get_state(self) -> dict[str, Any]:
        """Get current cognitive state."""
        return {
            "awareness": round(self.state.awareness, 4),
            "coherence": round(self.state.coherence, 4),
            "resonance": round(self.state.resonance, 4),
            "effectiveness": round(self.state.effectiveness, 4),
            "should_explore": self.state.should_explore,
            "entropy": round(self.state.entropy, 4),
            "prediction_error": round(self.state.prediction_error, 4),
            "total_perceptions": self.state.total_perceptions,
            "explore_activations": self.state.explore_activations,
            "phi_inverse_threshold": round(PHI_INVERSE, 4),
            "last_update": self.state.last_update.isoformat(),
        }
    
    def get_update_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent state update history."""
        return self.update_history[-limit:]
    
    def get_homeostat_stats(self) -> dict[str, Any]:
        """Statistics about homeostat behavior."""
        if not self.update_history:
            return {"updates": 0, "explore_rate": 0.0}
        
        explore_count = sum(
            1 for u in self.update_history if u.get("explore_triggered", False)
        )
        
        return {
            "total_updates": len(self.update_history),
            "explore_activations": explore_count,
            "explore_rate": explore_count / len(self.update_history),
            "avg_prediction_error": (
                sum(u.get("mismatch_score", 0) for u in self.update_history)
                / len(self.update_history)
            ),
            "current_state": self.get_state(),
        }


# ---------------------------------------------------------------------------
# Singleton Instance
# ---------------------------------------------------------------------------

_homeostat_instance: CognitiveHomeostat | None = None


def get_cognitive_homeostat() -> CognitiveHomeostat:
    """Get or create the singleton cognitive homeostat."""
    global _homeostat_instance
    if _homeostat_instance is None:
        _homeostat_instance = CognitiveHomeostat()
    return _homeostat_instance
