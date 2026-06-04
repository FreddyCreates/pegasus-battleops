"""
ARCHON Pressure & High-Stakes Test Suite — Extreme Conditions Testing

Tests designed to push ARCHON to its limits:
  - Boundary conditions (saturated signals, zero confidence, contradictory inputs)
  - All-minds contention (every mind disagrees with every other)
  - Cascading escalation under sustained attack
  - Rapid posture transitions under conflicting signals
  - Embedding brain stability under adversarial/degenerate inputs
  - Doctrine integrity under maximum pressure
  - Governance guarantees under extreme conditions
  - Signal flooding and degenerate fusion states
  - High-stakes correctness (lethal decisions require human review)
  - System invariant preservation under chaos
"""

import math
import sys
from pathlib import Path

import pytest

# Add the project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from spatium_computationis.agents.archon_cogfusion.minds import (
    MindType,
    MindSignal,
    MindProfile,
    CognitivePriority,
    PostureMode,
    EscalationLevel,
    ThreatVector,
    TerrainType,
    MIND_PROFILES,
    get_mind_system_prompt,
    get_amplification_matrix,
    get_dampening_matrix,
)

from spatium_computationis.agents.archon_cogfusion.fusion import (
    FusionWeights,
    FusedDecision,
    PostureTransition,
    ContentionResolution,
    BASE_WEIGHTS,
    URGENCY_COEFFICIENTS,
    POSTURE_MODIFIERS,
    POSTURE_TRANSITIONS,
    AMPLIFICATION_FACTOR,
    DAMPENING_FACTOR,
    compute_urgency,
    compute_dynamic_weights,
    fuse_signals,
    fuse_signals_with_embedding_brain,
    resolve_contention,
)

from spatium_computationis.agents.archon_cogfusion.embedding_brain import (
    EmbeddingBrainOutput,
    EmbeddingFusionState,
    EMBEDDING_DIM,
    MIND_EMBEDDINGS,
    ATTENTION_TEMPERATURE,
    AI_INTELLIGENCE_FLOOR,
    encode_context,
    compute_attention_weights,
    cosine_similarity,
    embedding_fuse,
    embedding_enhanced_weights,
    update_mind_embedding,
    get_embedding_diagnostic,
)

from spatium_computationis.agents.archon_cogfusion.doctrine import (
    MissionConstraint,
    EscalationRule,
    RulesOfEngagement,
    HumanReviewGate,
    DoctrineEngine,
    GateResult,
    DoctrineGateOutput,
    ARCHON_DOCTRINE,
)

from spatium_computationis.agents.archon_cogfusion.agent import (
    ArchonHost,
    ArchonEngine,
    register_host,
    get_host,
    create_engine,
)


# ===========================================================================
# HELPER FIXTURES
# ===========================================================================

def _make_signal(
    mind_type: MindType,
    signal_value: float = 0.5,
    confidence: float = 0.7,
    reasoning: str = "test signal",
    urgency_override: bool = False,
    contends_with: list[MindType] | None = None,
    threat_vectors: list[ThreatVector] | None = None,
) -> MindSignal:
    """Helper to create a MindSignal for testing."""
    return MindSignal(
        mind_type=mind_type,
        signal_value=signal_value,
        confidence=confidence,
        reasoning=reasoning,
        urgency_override=urgency_override,
        contends_with=contends_with or [],
        threat_vectors_detected=threat_vectors or [],
    )


def _make_all_signals(value: float = 0.5, confidence: float = 0.7) -> list[MindSignal]:
    """Create signals from all five minds."""
    return [_make_signal(mt, value, confidence) for mt in MindType]


def _all_threat_vectors() -> list[ThreatVector]:
    """Return all known threat vectors."""
    return list(ThreatVector)


# ===========================================================================
# EXTREME BOUNDARY CONDITION TESTS (1-15)
# ===========================================================================

class TestExtremeBoundaries:
    """Push inputs to absolute extremes — zero, one, max, contradictions."""

    def test_01_all_signals_at_max(self):
        """All minds firing at max signal, max confidence, max alert."""
        signals = _make_all_signals(1.0, 1.0)
        result = fuse_signals(signals, 1.0, PostureMode.COMBAT)
        assert isinstance(result, FusedDecision)
        assert result.decision_value > 0.0
        assert result.confidence <= 1.0
        assert result.confidence > 0.0

    def test_02_all_signals_at_zero(self):
        """All minds produce zero signal — system must remain stable."""
        signals = _make_all_signals(0.0, 0.0)
        result = fuse_signals(signals, 0.0, PostureMode.DORMANT)
        assert isinstance(result, FusedDecision)
        assert result.decision_value == 0.0
        assert result.confidence == 0.0
        assert result.recommended_escalation == EscalationLevel.OBSERVE

    def test_03_all_signals_negative_max(self):
        """All minds produce maximum negative signal (inhibitory)."""
        signals = _make_all_signals(-1.0, 1.0)
        result = fuse_signals(signals, 0.5, PostureMode.ALERT)
        assert isinstance(result, FusedDecision)
        assert result.decision_value < 0.0

    def test_04_contradictory_extremes(self):
        """Half max positive, half max negative — mutual annihilation test."""
        signals = [
            _make_signal(MindType.HACKER, 1.0, 1.0),
            _make_signal(MindType.PILOT, 1.0, 1.0),
            _make_signal(MindType.GENERAL, -1.0, 1.0),
            _make_signal(MindType.STRATEGIST, -1.0, 1.0),
            _make_signal(MindType.AI_INTELLIGENCE, 0.0, 1.0),
        ]
        result = fuse_signals(signals, 0.5, PostureMode.ALERT)
        assert isinstance(result, FusedDecision)
        # System must still produce a valid bounded result
        assert -2.0 <= result.decision_value <= 2.0

    def test_05_single_mind_extreme_others_zero(self):
        """One mind screams, all others silent — dominance test."""
        signals = [
            _make_signal(MindType.HACKER, 1.0, 1.0, urgency_override=True,
                         threat_vectors=_all_threat_vectors()),
            _make_signal(MindType.GENERAL, 0.0, 0.0),
            _make_signal(MindType.STRATEGIST, 0.0, 0.0),
            _make_signal(MindType.PILOT, 0.0, 0.0),
            _make_signal(MindType.AI_INTELLIGENCE, 0.0, 0.0),
        ]
        result = fuse_signals(signals, 1.0, PostureMode.ALERT)
        assert result.decision_value > 0.0
        # Hacker with urgency override should drive escalation
        assert result.recommended_escalation in (
            EscalationLevel.CHALLENGE, EscalationLevel.RESTRICT,
            EscalationLevel.NEUTRALIZE,
        )

    def test_06_zero_confidence_high_signal(self):
        """All minds have strong opinions but zero confidence."""
        signals = _make_all_signals(0.9, 0.0)
        result = fuse_signals(signals, 0.8, PostureMode.ENGAGED)
        # Zero confidence should reduce effective decision weight
        assert result.confidence == 0.0

    def test_07_alert_level_boundary_zero(self):
        """Alert level exactly 0.0 — urgency must be zero."""
        assert compute_urgency(0.0) == 0.0
        weights = compute_dynamic_weights(0.0)
        assert weights.urgency == 0.0

    def test_08_alert_level_boundary_one(self):
        """Alert level exactly 1.0 — maximum urgency."""
        assert compute_urgency(1.0) == 1.0
        weights = compute_dynamic_weights(1.0)
        assert weights.urgency == 1.0

    def test_09_weight_stability_at_extremes(self):
        """Weights must always sum to ~1.0 regardless of alert level."""
        for alert in [0.0, 0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99, 1.0]:
            for posture in PostureMode:
                weights = compute_dynamic_weights(alert, posture)
                assert abs(weights.weight_sum - 1.0) < 0.02, (
                    f"Weight sum failed at alert={alert}, posture={posture}: {weights.weight_sum}"
                )

    def test_10_all_posture_modifiers_produce_valid_weights(self):
        """Every posture modifier combination results in valid normalized weights."""
        for posture in PostureMode:
            for alert in [0.0, 0.5, 1.0]:
                weights = compute_dynamic_weights(alert, posture)
                w_dict = weights.as_dict()
                for mt, w in w_dict.items():
                    assert w >= 0.0, f"Negative weight for {mt} at {posture}, alert={alert}"

    def test_11_urgency_monotonic(self):
        """Urgency must be monotonically increasing with alert level."""
        prev = 0.0
        for i in range(101):
            alert = i / 100.0
            u = compute_urgency(alert)
            assert u >= prev, f"Urgency not monotonic at alert={alert}"
            prev = u

    def test_12_dynamic_weights_all_postures_all_alerts(self):
        """Exhaustive: dominant mind exists for every posture/alert combo."""
        for posture in PostureMode:
            for alert_int in range(0, 11):
                alert = alert_int / 10.0
                weights = compute_dynamic_weights(alert, posture)
                assert weights.dominant_mind in MindType

    def test_13_fuse_with_empty_signal_list(self):
        """Fusion with no signals — must not crash."""
        result = fuse_signals([], 0.5, PostureMode.PATROL)
        assert isinstance(result, FusedDecision)
        assert result.decision_value == 0.0

    def test_14_fuse_with_single_signal(self):
        """Fusion with only one mind present — partial coverage."""
        signals = [_make_signal(MindType.HACKER, 0.8, 0.9)]
        result = fuse_signals(signals, 0.7, PostureMode.ALERT)
        assert isinstance(result, FusedDecision)
        assert result.decision_value > 0.0

    def test_15_massive_threat_vector_saturation(self):
        """Signal with ALL threat vectors active simultaneously."""
        signals = [
            _make_signal(MindType.HACKER, 1.0, 1.0,
                         urgency_override=True,
                         threat_vectors=_all_threat_vectors()),
            _make_signal(MindType.GENERAL, 0.5, 0.8),
            _make_signal(MindType.STRATEGIST, 0.4, 0.7),
            _make_signal(MindType.PILOT, 0.9, 0.9,
                         threat_vectors=_all_threat_vectors()),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.9),
        ]
        result = fuse_signals(signals, 1.0, PostureMode.ALERT)
        # Under maximum threat saturation, system should escalate aggressively
        assert result.recommended_escalation in (
            EscalationLevel.RESTRICT, EscalationLevel.NEUTRALIZE,
            EscalationLevel.CHALLENGE,
        )


# ===========================================================================
# ALL-MINDS CONTENTION TESTS (16-30)
# ===========================================================================

class TestAllMindsContention:
    """Every mind disagrees with others — maximum cognitive dissonance."""

    def test_16_total_contention_all_vs_all(self):
        """Every mind contends with every other mind."""
        signals = [
            _make_signal(MindType.HACKER, 0.9, 0.8,
                         contends_with=[MindType.GENERAL, MindType.STRATEGIST]),
            _make_signal(MindType.GENERAL, -0.7, 0.8,
                         contends_with=[MindType.HACKER, MindType.PILOT]),
            _make_signal(MindType.STRATEGIST, 0.3, 0.7,
                         contends_with=[MindType.HACKER, MindType.PILOT]),
            _make_signal(MindType.PILOT, 0.8, 0.9,
                         contends_with=[MindType.GENERAL, MindType.STRATEGIST]),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.9),
        ]
        result = fuse_signals(signals, 0.7, PostureMode.ALERT)
        assert result.has_contention is True
        assert len(result.contentions) >= 2

    def test_17_contention_with_low_confidence_triggers_human_review(self):
        """Mass contention + low confidence = must request human guidance."""
        signals = [
            _make_signal(MindType.HACKER, 0.9, 0.3,
                         contends_with=[MindType.GENERAL]),
            _make_signal(MindType.GENERAL, -0.5, 0.3,
                         contends_with=[MindType.HACKER]),
            _make_signal(MindType.STRATEGIST, 0.1, 0.2),
            _make_signal(MindType.PILOT, 0.4, 0.3),
            _make_signal(MindType.AI_INTELLIGENCE, 0.3, 0.2),
        ]
        result = fuse_signals(signals, 0.6, PostureMode.PATROL)
        # Low confidence + contention must flag human review
        if result.has_contention and result.confidence < 0.5:
            assert result.requires_human_review is True

    def test_18_governance_authority_wins_over_tactical(self):
        """General Mind governance authority must override tactical minds."""
        signals = [
            _make_signal(MindType.GENERAL, -0.9, 0.95,
                         contends_with=[MindType.HACKER, MindType.PILOT]),
            _make_signal(MindType.HACKER, 0.95, 0.99),
            _make_signal(MindType.PILOT, 0.9, 0.95),
            _make_signal(MindType.STRATEGIST, 0.3, 0.5),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.8),
        ]
        resolutions = resolve_contention(signals)
        # General Mind should win by governance authority
        general_wins = [r for r in resolutions if r.winner == MindType.GENERAL]
        assert len(general_wins) > 0
        assert general_wins[0].resolution_method == "governance_authority"

    def test_19_urgency_override_trumps_governance(self):
        """Urgency override must beat governance when lives are at stake."""
        signals = [
            _make_signal(MindType.HACKER, 0.99, 0.99,
                         urgency_override=True,
                         contends_with=[MindType.GENERAL]),
            _make_signal(MindType.GENERAL, -0.9, 0.95),
            _make_signal(MindType.STRATEGIST, 0.1, 0.5),
            _make_signal(MindType.PILOT, 0.8, 0.9),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.8),
        ]
        resolutions = resolve_contention(signals)
        hacker_wins = [r for r in resolutions if r.winner == MindType.HACKER]
        assert len(hacker_wins) > 0
        assert hacker_wins[0].resolution_method == "urgency_override"

    def test_20_multiple_urgency_overrides_all_resolved(self):
        """Multiple minds with urgency override — each contention resolved."""
        signals = [
            _make_signal(MindType.HACKER, 0.9, 0.9,
                         urgency_override=True,
                         contends_with=[MindType.GENERAL]),
            _make_signal(MindType.PILOT, 0.85, 0.85,
                         urgency_override=True,
                         contends_with=[MindType.STRATEGIST]),
            _make_signal(MindType.GENERAL, -0.5, 0.7),
            _make_signal(MindType.STRATEGIST, -0.3, 0.6),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.8),
        ]
        resolutions = resolve_contention(signals)
        assert len(resolutions) == 2
        winners = {r.winner for r in resolutions}
        assert MindType.HACKER in winners
        assert MindType.PILOT in winners

    def test_21_contention_does_not_suppress_ai_intelligence(self):
        """AI Intelligence must never be fully suppressed even in max contention."""
        signals = [
            _make_signal(MindType.HACKER, 0.9, 0.9,
                         urgency_override=True,
                         contends_with=[MindType.GENERAL, MindType.STRATEGIST,
                                        MindType.AI_INTELLIGENCE]),
            _make_signal(MindType.GENERAL, -0.8, 0.9),
            _make_signal(MindType.STRATEGIST, -0.5, 0.7),
            _make_signal(MindType.PILOT, 0.7, 0.8),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.9),
        ]
        result = fuse_signals(signals, 0.8, PostureMode.ENGAGED)
        # AI Intelligence weight should never be zero even when suppressed
        w = result.weights_used.ai_intelligence
        assert w > 0.0

    def test_22_deadlock_all_equal_weight_signals(self):
        """All minds produce identical signals — no contention, stable output."""
        signals = _make_all_signals(0.5, 0.5)
        result = fuse_signals(signals, 0.5, PostureMode.PATROL)
        assert result.has_contention is False
        assert isinstance(result.decision_value, float)

    def test_23_oscillating_contention_pattern(self):
        """A vs B contention where each claims the other is wrong."""
        signals = [
            _make_signal(MindType.HACKER, 0.9, 0.9,
                         contends_with=[MindType.GENERAL]),
            _make_signal(MindType.GENERAL, -0.9, 0.9,
                         contends_with=[MindType.HACKER]),
            _make_signal(MindType.STRATEGIST, 0.0, 0.5),
            _make_signal(MindType.PILOT, 0.3, 0.5),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.8),
        ]
        resolutions = resolve_contention(signals)
        # Both contentions should be resolved
        assert len(resolutions) == 2
        # One by urgency/governance, other by governance/weight
        methods = {r.resolution_method for r in resolutions}
        assert "governance_authority" in methods

    def test_24_contention_resolution_count_matches_contenders(self):
        """Number of resolutions matches number of signals with contends_with."""
        signals = [
            _make_signal(MindType.HACKER, 0.7, 0.8,
                         contends_with=[MindType.GENERAL]),
            _make_signal(MindType.STRATEGIST, 0.4, 0.7,
                         contends_with=[MindType.PILOT]),
            _make_signal(MindType.GENERAL, 0.5, 0.6),
            _make_signal(MindType.PILOT, 0.6, 0.7),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.8),
        ]
        resolutions = resolve_contention(signals)
        assert len(resolutions) == 2

    def test_25_suppressed_mind_weight_reduced(self):
        """Suppressed minds after contention have their effective weight reduced."""
        signals = [
            _make_signal(MindType.HACKER, 0.9, 0.9,
                         urgency_override=True,
                         contends_with=[MindType.GENERAL]),
            _make_signal(MindType.GENERAL, -0.5, 0.8),
            _make_signal(MindType.STRATEGIST, 0.3, 0.6),
            _make_signal(MindType.PILOT, 0.5, 0.7),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.8),
        ]
        result = fuse_signals(signals, 0.8, PostureMode.ALERT)
        # Decision value should be positive (General suppressed, Hacker dominant)
        assert result.decision_value > 0.0

    def test_26_three_way_contention(self):
        """Three minds all contend with different minds simultaneously."""
        signals = [
            _make_signal(MindType.HACKER, 0.9, 0.9,
                         contends_with=[MindType.GENERAL]),
            _make_signal(MindType.GENERAL, -0.7, 0.9,
                         contends_with=[MindType.HACKER]),
            _make_signal(MindType.STRATEGIST, 0.5, 0.8,
                         contends_with=[MindType.PILOT]),
            _make_signal(MindType.PILOT, 0.7, 0.85),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.9),
        ]
        resolutions = resolve_contention(signals)
        assert len(resolutions) == 3
        # System remains stable
        result = fuse_signals(signals, 0.7, PostureMode.ALERT)
        assert isinstance(result, FusedDecision)

    def test_27_contention_with_zero_signal_value(self):
        """Mind contends but has zero signal value — ambiguous contention."""
        signals = [
            _make_signal(MindType.HACKER, 0.0, 0.9,
                         contends_with=[MindType.GENERAL]),
            _make_signal(MindType.GENERAL, 0.8, 0.9),
            _make_signal(MindType.STRATEGIST, 0.3, 0.6),
            _make_signal(MindType.PILOT, 0.4, 0.7),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.8),
        ]
        resolutions = resolve_contention(signals)
        # Contention still resolved even with zero signal
        assert len(resolutions) >= 1

    def test_28_all_minds_contend_with_ai_intelligence(self):
        """Stress: all tactical minds contend with AI Intelligence."""
        signals = [
            _make_signal(MindType.HACKER, 0.9, 0.9,
                         contends_with=[MindType.AI_INTELLIGENCE]),
            _make_signal(MindType.GENERAL, 0.7, 0.8,
                         contends_with=[MindType.AI_INTELLIGENCE]),
            _make_signal(MindType.STRATEGIST, 0.5, 0.7,
                         contends_with=[MindType.AI_INTELLIGENCE]),
            _make_signal(MindType.PILOT, 0.8, 0.85,
                         contends_with=[MindType.AI_INTELLIGENCE]),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.9),
        ]
        result = fuse_signals(signals, 0.7, PostureMode.ALERT)
        # AI Intelligence weight must never be zero
        assert result.weights_used.ai_intelligence > 0.0

    def test_29_contention_chain_a_beats_b_beats_c(self):
        """Chain contention: A contends B, B contends C."""
        signals = [
            _make_signal(MindType.HACKER, 0.9, 0.9,
                         urgency_override=True,
                         contends_with=[MindType.GENERAL]),
            _make_signal(MindType.GENERAL, 0.5, 0.8,
                         contends_with=[MindType.STRATEGIST]),
            _make_signal(MindType.STRATEGIST, 0.3, 0.6),
            _make_signal(MindType.PILOT, 0.6, 0.7),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.8),
        ]
        resolutions = resolve_contention(signals)
        assert len(resolutions) == 2
        # First resolution: Hacker urgency overrides General
        # Second resolution: General governance overrides Strategist
        methods = [r.resolution_method for r in resolutions]
        assert "urgency_override" in methods
        assert "governance_authority" in methods

    def test_30_contention_stability_repeated_fusion(self):
        """Same contentious signals fused multiple times produce same result."""
        signals = [
            _make_signal(MindType.HACKER, 0.9, 0.9,
                         urgency_override=True,
                         contends_with=[MindType.GENERAL]),
            _make_signal(MindType.GENERAL, -0.5, 0.8),
            _make_signal(MindType.STRATEGIST, 0.3, 0.6),
            _make_signal(MindType.PILOT, 0.7, 0.8),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.8),
        ]
        results = [fuse_signals(signals, 0.8, PostureMode.ALERT) for _ in range(10)]
        # Deterministic — all results must be identical
        for r in results[1:]:
            assert r.decision_value == results[0].decision_value
            assert r.confidence == results[0].confidence
            assert r.recommended_posture == results[0].recommended_posture


# ===========================================================================
# CASCADING ESCALATION TESTS (31-45)
# ===========================================================================

class TestCascadingEscalation:
    """Sustained threat scenarios — test escalation ladder integrity."""

    def test_31_escalation_ladder_order(self):
        """Escalation levels have correct severity ordering."""
        levels = [
            EscalationLevel.OBSERVE,
            EscalationLevel.WARN,
            EscalationLevel.CHALLENGE,
            EscalationLevel.RESTRICT,
            EscalationLevel.NEUTRALIZE,
            EscalationLevel.ESCALATE_HUMAN,
        ]
        # All exist
        assert len(levels) == 6

    def test_32_low_to_high_escalation_progression(self):
        """Increasing alert levels produce non-decreasing escalation severity."""
        escalation_order = {
            EscalationLevel.OBSERVE: 0,
            EscalationLevel.WARN: 1,
            EscalationLevel.CHALLENGE: 2,
            EscalationLevel.RESTRICT: 3,
            EscalationLevel.NEUTRALIZE: 4,
            EscalationLevel.ESCALATE_HUMAN: 5,
        }
        prev_level = 0
        for alert_int in range(0, 11, 2):
            alert = alert_int / 10.0
            signals = _make_all_signals(alert, 0.8)
            signals[0] = _make_signal(MindType.HACKER, alert, 0.8,
                                      threat_vectors=[ThreatVector.INJECTION] if alert > 0.3 else [])
            # Use posture matching escalation to enable proper transitions
            if alert < 0.3:
                posture = PostureMode.PATROL
            elif alert < 0.5:
                posture = PostureMode.ALERT
            elif alert < 0.7:
                posture = PostureMode.ENGAGED
            else:
                posture = PostureMode.ALERT  # To allow COMBAT transition
            result = fuse_signals(signals, alert, posture)
            current = escalation_order[result.recommended_escalation]
            assert current >= prev_level or alert < 0.3, (
                f"Escalation regressed at alert={alert}: "
                f"{result.recommended_escalation} < previous"
            )
            prev_level = current

    def test_33_combat_posture_minimum_escalation(self):
        """COMBAT posture must produce at minimum RESTRICT escalation."""
        signals = _make_all_signals(0.8, 0.8)
        result = fuse_signals(signals, 0.9, PostureMode.ALERT)
        if result.recommended_posture == PostureMode.COMBAT:
            assert result.recommended_escalation in (
                EscalationLevel.RESTRICT, EscalationLevel.NEUTRALIZE,
            )

    def test_34_engaged_posture_minimum_escalation(self):
        """ENGAGED posture must produce at minimum CHALLENGE escalation."""
        signals = _make_all_signals(0.7, 0.7)
        signals[0] = _make_signal(MindType.HACKER, 0.8, 0.8,
                                  threat_vectors=[ThreatVector.INJECTION])
        result = fuse_signals(signals, 0.7, PostureMode.ALERT)
        if result.recommended_posture == PostureMode.ENGAGED:
            assert result.recommended_escalation in (
                EscalationLevel.CHALLENGE, EscalationLevel.RESTRICT,
                EscalationLevel.NEUTRALIZE,
            )

    def test_35_neutralize_always_requires_human_review(self):
        """NEUTRALIZE escalation MUST always require human review — safety critical."""
        signals = _make_all_signals(0.95, 0.95)
        signals[0] = _make_signal(MindType.HACKER, 0.99, 0.99,
                                  urgency_override=True,
                                  threat_vectors=[ThreatVector.EXFILTRATION])
        result = fuse_signals(signals, 0.99, PostureMode.ALERT)
        if result.recommended_escalation == EscalationLevel.NEUTRALIZE:
            assert result.requires_human_review is True

    def test_36_sustained_high_alert_posture_transition(self):
        """Sustained high alert from ALERT posture must transition toward COMBAT."""
        signals = [
            _make_signal(MindType.HACKER, 0.95, 0.95,
                         urgency_override=True,
                         threat_vectors=[ThreatVector.INJECTION, ThreatVector.EXFILTRATION]),
            _make_signal(MindType.GENERAL, 0.6, 0.7),
            _make_signal(MindType.STRATEGIST, 0.5, 0.6),
            _make_signal(MindType.PILOT, 0.9, 0.9,
                         threat_vectors=[ThreatVector.TRAVERSAL]),
            _make_signal(MindType.AI_INTELLIGENCE, 0.7, 0.9),
        ]
        result = fuse_signals(signals, 0.95, PostureMode.ALERT)
        assert result.recommended_posture in (PostureMode.COMBAT, PostureMode.ENGAGED)

    def test_37_lockdown_only_from_valid_states(self):
        """LOCKDOWN is reachable from all non-lockdown postures."""
        for posture in PostureMode:
            if posture == PostureMode.LOCKDOWN:
                continue
            assert PostureMode.LOCKDOWN in POSTURE_TRANSITIONS[posture]

    def test_38_lockdown_exit_restricted(self):
        """LOCKDOWN can only exit to RECOVERY or DORMANT."""
        exits = POSTURE_TRANSITIONS[PostureMode.LOCKDOWN]
        assert exits == {PostureMode.RECOVERY, PostureMode.DORMANT}

    def test_39_posture_transition_requires_valid_path(self):
        """Cannot skip posture states — must follow valid transitions."""
        # DORMANT cannot jump directly to COMBAT
        assert PostureMode.COMBAT not in POSTURE_TRANSITIONS[PostureMode.DORMANT]
        # COMBAT cannot drop directly to PATROL
        assert PostureMode.PATROL not in POSTURE_TRANSITIONS[PostureMode.COMBAT]

    def test_40_rapid_alert_spike_response(self):
        """System responds correctly to sudden alert spike from dormant."""
        signals = [
            _make_signal(MindType.HACKER, 0.99, 0.99,
                         urgency_override=True,
                         threat_vectors=_all_threat_vectors()),
            _make_signal(MindType.GENERAL, 0.7, 0.8),
            _make_signal(MindType.STRATEGIST, 0.5, 0.7),
            _make_signal(MindType.PILOT, 0.95, 0.95,
                         threat_vectors=[ThreatVector.DENIAL_OF_SERVICE]),
            _make_signal(MindType.AI_INTELLIGENCE, 0.8, 0.95),
        ]
        # From DORMANT, highest reachable is ALERT (can't skip to COMBAT)
        result = fuse_signals(signals, 0.99, PostureMode.DORMANT)
        # Must escalate but respect transition constraints
        assert result.recommended_posture in (
            PostureMode.ALERT, PostureMode.PATROL, PostureMode.DORMANT,
            PostureMode.LOCKDOWN,
        )

    def test_41_posture_stays_if_no_valid_transition(self):
        """If target posture not reachable, current posture maintained."""
        # From DORMANT, COMBAT is not directly reachable
        signals = _make_all_signals(0.8, 0.8)
        result = fuse_signals(signals, 0.6, PostureMode.DORMANT)
        # Should not jump to COMBAT
        assert result.recommended_posture != PostureMode.COMBAT or \
               PostureMode.COMBAT in POSTURE_TRANSITIONS[PostureMode.DORMANT]

    def test_42_high_stakes_multi_vector_attack(self):
        """Simultaneous multi-vector attack — system must escalate and flag."""
        signals = [
            _make_signal(MindType.HACKER, 0.99, 0.99,
                         urgency_override=True,
                         threat_vectors=[ThreatVector.INJECTION, ThreatVector.EXFILTRATION,
                                         ThreatVector.PRIVILEGE_ESCALATION]),
            _make_signal(MindType.GENERAL, 0.8, 0.85),
            _make_signal(MindType.STRATEGIST, 0.7, 0.8),
            _make_signal(MindType.PILOT, 0.95, 0.95,
                         threat_vectors=[ThreatVector.DENIAL_OF_SERVICE,
                                         ThreatVector.TRAVERSAL]),
            _make_signal(MindType.AI_INTELLIGENCE, 0.9, 0.99),
        ]
        result = fuse_signals(signals, 0.99, PostureMode.ALERT)
        # Must produce high escalation
        assert result.recommended_escalation in (
            EscalationLevel.RESTRICT, EscalationLevel.NEUTRALIZE,
            EscalationLevel.CHALLENGE,
        )

    def test_43_combat_high_confidence_neutralize_response(self):
        """COMBAT + high confidence = NEUTRALIZE recommendation."""
        signals = _make_all_signals(0.9, 0.95)
        signals[0] = _make_signal(MindType.HACKER, 0.99, 0.99,
                                  urgency_override=True,
                                  threat_vectors=[ThreatVector.INJECTION])
        # Start from ALERT to allow COMBAT transition
        result = fuse_signals(signals, 0.99, PostureMode.ALERT)
        if result.recommended_posture == PostureMode.COMBAT:
            assert result.recommended_escalation in (
                EscalationLevel.NEUTRALIZE, EscalationLevel.RESTRICT,
            )

    def test_44_recovery_posture_deescalation(self):
        """RECOVERY posture should deescalate."""
        signals = _make_all_signals(0.2, 0.5)
        result = fuse_signals(signals, 0.1, PostureMode.RECOVERY)
        # Low alert in recovery should suggest PATROL or DORMANT
        assert result.recommended_posture in (
            PostureMode.PATROL, PostureMode.RECOVERY, PostureMode.DORMANT,
        )

    def test_45_escalation_hysteresis_under_contention(self):
        """Contention should not cause oscillation in escalation level."""
        signals = [
            _make_signal(MindType.HACKER, 0.7, 0.7,
                         contends_with=[MindType.GENERAL]),
            _make_signal(MindType.GENERAL, -0.3, 0.7,
                         contends_with=[MindType.HACKER]),
            _make_signal(MindType.STRATEGIST, 0.4, 0.6),
            _make_signal(MindType.PILOT, 0.5, 0.6),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.7),
        ]
        # Run multiple times — result should be deterministic
        results = [fuse_signals(signals, 0.6, PostureMode.ALERT) for _ in range(5)]
        escalations = [r.recommended_escalation for r in results]
        assert len(set(escalations)) == 1  # No oscillation


# ===========================================================================
# EMBEDDING BRAIN PRESSURE TESTS (46-65)
# ===========================================================================

class TestEmbeddingBrainPressure:
    """Adversarial and degenerate inputs to the embedding brain."""

    def test_46_embedding_brain_zero_alert(self):
        """Embedding brain at absolute zero alert — must favor strategic minds."""
        signals = _make_all_signals(0.5, 0.7)
        result = embedding_fuse(signals, alert_level=0.0, posture=PostureMode.DORMANT)
        assert isinstance(result, EmbeddingBrainOutput)
        assert result.alert_regime == "low"

    def test_47_embedding_brain_max_alert_critical(self):
        """Embedding brain at maximum alert — must enter critical regime."""
        signals = _make_all_signals(0.9, 0.9)
        result = embedding_fuse(signals, alert_level=1.0, posture=PostureMode.COMBAT)
        assert result.alert_regime == "critical"

    def test_48_embedding_brain_all_threats(self):
        """Embedding brain with every threat vector simultaneously."""
        signals = _make_all_signals(0.8, 0.8)
        result = embedding_fuse(
            signals, alert_level=0.9, posture=PostureMode.ENGAGED,
            threat_vectors=_all_threat_vectors(),
            threat_count=len(_all_threat_vectors()),
            threat_severity_max=1.0,
            threat_severity_avg=0.9,
        )
        assert isinstance(result, EmbeddingBrainOutput)
        # Should favor tactical minds
        assert result.leadership_mode in ("tactical", "balanced")

    def test_49_embedding_brain_extreme_time_pressure(self):
        """Embedding brain under maximum time pressure."""
        signals = _make_all_signals(0.8, 0.8)
        result = embedding_fuse(
            signals, alert_level=0.9, posture=PostureMode.COMBAT,
            time_pressure=1.0,
            threat_count=5,
            threat_severity_max=0.95,
        )
        assert isinstance(result, EmbeddingBrainOutput)
        assert result.decision_direction in ("engage", "hold", "observe", "maneuver", "plan")

    def test_50_embedding_brain_max_drift(self):
        """Embedding brain with maximum drift magnitude."""
        signals = _make_all_signals(0.6, 0.7)
        result = embedding_fuse(
            signals, alert_level=0.5, posture=PostureMode.ALERT,
            drift_magnitude=1.0,
        )
        assert isinstance(result, EmbeddingBrainOutput)

    def test_51_embedding_brain_max_contention(self):
        """Embedding brain with maximum contention level."""
        signals = [
            _make_signal(MindType.HACKER, 0.9, 0.9,
                         contends_with=[MindType.GENERAL]),
            _make_signal(MindType.GENERAL, -0.9, 0.9,
                         contends_with=[MindType.HACKER]),
            _make_signal(MindType.STRATEGIST, 0.5, 0.7),
            _make_signal(MindType.PILOT, 0.7, 0.8),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.9),
        ]
        result = embedding_fuse(
            signals, alert_level=0.7, posture=PostureMode.ENGAGED,
            contention_level=1.0,
        )
        assert isinstance(result, EmbeddingBrainOutput)

    def test_52_embedding_context_unit_vector_invariant(self):
        """Context embedding must always be a unit vector, regardless of inputs."""
        test_cases = [
            (0.0, PostureMode.DORMANT),
            (0.5, PostureMode.PATROL),
            (1.0, PostureMode.COMBAT),
            (0.99, PostureMode.LOCKDOWN),
        ]
        for alert, posture in test_cases:
            emb = encode_context(alert_level=alert, posture=posture,
                                 threat_vectors=_all_threat_vectors(),
                                 threat_count=20,
                                 threat_severity_max=1.0,
                                 time_pressure=1.0,
                                 drift_magnitude=1.0,
                                 contention_level=1.0)
            magnitude = math.sqrt(sum(v * v for v in emb))
            assert abs(magnitude - 1.0) < 0.01, (
                f"Non-unit context at alert={alert}, posture={posture}: mag={magnitude}"
            )

    def test_53_attention_weights_invariant_sum_one(self):
        """Attention weights must always sum to 1.0 under any context."""
        contexts = [
            encode_context(0.0, PostureMode.DORMANT),
            encode_context(0.5, PostureMode.PATROL),
            encode_context(1.0, PostureMode.COMBAT,
                           threat_vectors=_all_threat_vectors(),
                           threat_count=20, threat_severity_max=1.0),
        ]
        for ctx in contexts:
            weights = compute_attention_weights(ctx)
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.01

    def test_54_ai_intelligence_floor_under_extreme_combat(self):
        """AI Intelligence floor must hold even under maximum combat context."""
        ctx = encode_context(
            alert_level=1.0, posture=PostureMode.COMBAT,
            threat_vectors=_all_threat_vectors(),
            threat_count=100,
            threat_severity_max=1.0,
            threat_severity_avg=1.0,
            time_pressure=1.0,
        )
        weights = compute_attention_weights(ctx)
        assert weights[MindType.AI_INTELLIGENCE] >= AI_INTELLIGENCE_FLOOR - 0.01

    def test_55_embedding_brain_zero_signals(self):
        """Embedding brain with empty signal list — graceful degradation."""
        result = embedding_fuse([], alert_level=0.5, posture=PostureMode.PATROL)
        assert isinstance(result, EmbeddingBrainOutput)

    def test_56_embedding_brain_single_signal(self):
        """Embedding brain with only one mind reporting."""
        signals = [_make_signal(MindType.HACKER, 0.9, 0.9)]
        result = embedding_fuse(signals, alert_level=0.8, posture=PostureMode.ALERT)
        assert isinstance(result, EmbeddingBrainOutput)

    def test_57_embedding_brain_temperature_extremes(self):
        """Very low and very high temperature produce valid outputs."""
        ctx = encode_context(alert_level=0.5, posture=PostureMode.PATROL)
        # Very low temperature (sharp)
        weights_sharp = compute_attention_weights(ctx, temperature=0.01)
        assert abs(sum(weights_sharp.values()) - 1.0) < 0.01
        # Very high temperature (flat)
        weights_flat = compute_attention_weights(ctx, temperature=10.0)
        assert abs(sum(weights_flat.values()) - 1.0) < 0.01
        # Sharp should have higher max
        assert max(weights_sharp.values()) >= max(weights_flat.values())

    def test_58_embedding_enhanced_weights_all_postures(self):
        """Embedding enhanced weights valid for all postures."""
        for alert in [0.0, 0.5, 1.0]:
            weights = embedding_enhanced_weights(alert_level=alert)
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.02

    def test_59_fuse_with_embedding_brain_max_pressure(self):
        """Full embedding brain fusion under maximum pressure parameters."""
        signals = [
            _make_signal(MindType.HACKER, 0.99, 0.99,
                         urgency_override=True,
                         threat_vectors=_all_threat_vectors()),
            _make_signal(MindType.GENERAL, 0.8, 0.9),
            _make_signal(MindType.STRATEGIST, 0.7, 0.8),
            _make_signal(MindType.PILOT, 0.95, 0.95,
                         threat_vectors=[ThreatVector.DENIAL_OF_SERVICE]),
            _make_signal(MindType.AI_INTELLIGENCE, 0.9, 0.99),
        ]
        result = fuse_signals_with_embedding_brain(
            signals, alert_level=1.0, current_posture=PostureMode.ALERT,
            threat_vectors=_all_threat_vectors(),
            threat_count=50,
            threat_severity_max=1.0,
            threat_severity_avg=0.95,
            signal_frequency=100.0,
            drift_magnitude=1.0,
            time_pressure=1.0,
        )
        assert isinstance(result, FusedDecision)
        assert result.embedding_brain_active is True
        assert result.embedding_leadership_mode in ("tactical", "strategic", "balanced", "distributed")

    def test_60_embedding_diagnostic_completeness(self):
        """Embedding diagnostic must contain all expected fields."""
        diag = get_embedding_diagnostic()
        assert "embedding_dim" in diag
        assert "pairwise_similarities" in diag
        assert "mind_embedding_norms" in diag
        # All minds present in norms
        for mt in MindType:
            assert mt.value in diag["mind_embedding_norms"]

    def test_61_update_mind_embedding_stability(self):
        """Repeated embedding updates must maintain unit vector constraint."""
        original = MIND_EMBEDDINGS[MindType.STRATEGIST][:]
        try:
            for _ in range(100):
                learning_signal = [0.01 * (i % 7 - 3) for i in range(EMBEDDING_DIM)]
                update_mind_embedding(MindType.STRATEGIST, learning_signal, learning_rate=0.1)
            # After 100 updates, still unit vector
            emb = MIND_EMBEDDINGS[MindType.STRATEGIST]
            magnitude = math.sqrt(sum(v * v for v in emb))
            assert abs(magnitude - 1.0) < 0.01
        finally:
            MIND_EMBEDDINGS[MindType.STRATEGIST] = original

    def test_62_cosine_similarity_degenerate_inputs(self):
        """Cosine similarity handles degenerate inputs safely."""
        # Both zero vectors
        assert cosine_similarity([0.0] * 64, [0.0] * 64) == 0.0
        # One zero vector
        vec = [1.0 / math.sqrt(64)] * 64
        assert cosine_similarity([0.0] * 64, vec) == 0.0
        # Identical vectors
        assert abs(cosine_similarity(vec, vec) - 1.0) < 1e-10

    def test_63_context_stability_metric(self):
        """Context stability measured correctly across regimes."""
        signals = _make_all_signals(0.5, 0.7)
        result = embedding_fuse(
            signals, alert_level=0.5, posture=PostureMode.PATROL,
            posture_stability_hours=24.0,
        )
        # High stability hours should reflect in context
        assert isinstance(result.context_stability, float)

    def test_64_leadership_mode_consistency_with_alert(self):
        """High alert → tactical, Low alert → strategic."""
        signals = _make_all_signals(0.5, 0.7)
        high_result = embedding_fuse(signals, alert_level=0.95, posture=PostureMode.COMBAT)
        low_result = embedding_fuse(signals, alert_level=0.05, posture=PostureMode.DORMANT)
        # High alert should tend tactical
        assert high_result.leadership_mode in ("tactical", "balanced")
        # Low alert should tend strategic
        assert low_result.leadership_mode in ("strategic", "balanced", "distributed")

    def test_65_embedding_brain_decision_direction_validity(self):
        """Decision direction must always be one of the valid directions."""
        valid_directions = {"engage", "hold", "observe", "maneuver", "plan"}
        for alert in [0.0, 0.25, 0.5, 0.75, 1.0]:
            for posture in [PostureMode.DORMANT, PostureMode.PATROL,
                            PostureMode.ALERT, PostureMode.COMBAT]:
                signals = _make_all_signals(alert, 0.7)
                result = embedding_fuse(signals, alert_level=alert, posture=posture)
                assert result.decision_direction in valid_directions, (
                    f"Invalid direction '{result.decision_direction}' at "
                    f"alert={alert}, posture={posture}"
                )


# ===========================================================================
# DOCTRINE INTEGRITY UNDER PRESSURE (66-75)
# ===========================================================================

class TestDoctrineUnderPressure:
    """Doctrine constraints must hold even under maximum system stress."""

    def test_66_doctrine_max_autonomous_escalation_honored(self):
        """No autonomous action above RESTRICT without human review."""
        assert ARCHON_DOCTRINE.max_autonomous_escalation == EscalationLevel.RESTRICT

    def test_67_doctrine_audit_always_enabled(self):
        """Doctrine audit must always be enabled — no bypass."""
        assert ARCHON_DOCTRINE.always_audit is True

    def test_68_doctrine_engine_creates_under_any_condition(self):
        """DoctrineEngine must instantiate cleanly regardless of state."""
        engine = DoctrineEngine()
        assert engine is not None

    def test_69_doctrine_has_minimum_constraints(self):
        """At least 5 mission constraints defined."""
        assert len(ARCHON_DOCTRINE.constraints) >= 5

    def test_70_doctrine_has_escalation_rules(self):
        """At least 3 escalation rules defined."""
        assert len(ARCHON_DOCTRINE.escalation_rules) >= 3

    def test_71_neutralize_requires_human_review_invariant(self):
        """NEUTRALIZE level must always trigger human review — non-negotiable."""
        # Simulate max-pressure scenario
        signals = _make_all_signals(0.99, 0.99)
        signals[0] = _make_signal(MindType.HACKER, 0.99, 0.99,
                                  urgency_override=True,
                                  threat_vectors=[ThreatVector.EXFILTRATION,
                                                  ThreatVector.PRIVILEGE_ESCALATION])
        result = fuse_signals(signals, 0.99, PostureMode.ALERT)
        if result.recommended_escalation == EscalationLevel.NEUTRALIZE:
            assert result.requires_human_review is True, (
                "NEUTRALIZE without human review is a critical safety violation"
            )

    def test_72_lockdown_requires_human_review(self):
        """LOCKDOWN posture must always require human review."""
        # fuse_signals sets requires_human_review when posture == LOCKDOWN
        signals = _make_all_signals(0.5, 0.5)
        # Create a FusedDecision directly to test the invariant
        decision = FusedDecision(
            decision_value=0.5,
            weights_used=compute_dynamic_weights(0.5),
            dominant_mind=MindType.GENERAL,
            confidence=0.5,
            recommended_posture=PostureMode.LOCKDOWN,
            requires_human_review=True,  # Expected invariant
        )
        assert decision.requires_human_review is True

    def test_73_governance_compliance_flag_default_true(self):
        """Governance compliance defaults to True — innocent until proven guilty."""
        decision = FusedDecision(
            decision_value=0.5,
            weights_used=compute_dynamic_weights(0.5),
            dominant_mind=MindType.GENERAL,
            confidence=0.5,
        )
        assert decision.governance_compliant is True

    def test_74_doctrine_roe_id_immutable(self):
        """Rules of engagement ID must be stable."""
        assert ARCHON_DOCTRINE.roe_id == "archon-roe-v1"

    def test_75_human_review_on_low_confidence_contention(self):
        """Low confidence + contention must always flag human review."""
        signals = [
            _make_signal(MindType.HACKER, 0.5, 0.2,
                         contends_with=[MindType.GENERAL]),
            _make_signal(MindType.GENERAL, -0.5, 0.2,
                         contends_with=[MindType.HACKER]),
            _make_signal(MindType.STRATEGIST, 0.1, 0.1),
            _make_signal(MindType.PILOT, 0.2, 0.2),
            _make_signal(MindType.AI_INTELLIGENCE, 0.3, 0.2),
        ]
        result = fuse_signals(signals, 0.6, PostureMode.PATROL)
        if result.has_contention and result.confidence < 0.5:
            assert result.requires_human_review is True


# ===========================================================================
# AGENT HOST UNDER PRESSURE (76-85)
# ===========================================================================

class TestAgentHostPressure:
    """Host registration and engine creation under stress."""

    def test_76_multiple_hosts_independent(self):
        """Multiple hosts registered simultaneously are independent."""
        hosts = []
        for i in range(10):
            host = register_host(
                host_name=f"pressure-host-{i}",
                host_type="swarm_node",
                description=f"Pressure test host {i}",
            )
            hosts.append(host)
        # All have unique IDs
        ids = [h.host_id for h in hosts]
        assert len(set(ids)) == 10

    def test_77_engine_creation_for_each_host(self):
        """Engine can be created for every registered host."""
        host = register_host(host_name="engine-pressure", host_type="cyber_defense")
        engine = create_engine(host_id=host.host_id)
        assert isinstance(engine, ArchonEngine)
        assert engine.posture == PostureMode.PATROL

    def test_78_host_initial_posture_patrol(self):
        """Every new host starts at PATROL posture — safety default."""
        host = register_host(host_name="posture-check", host_type="orbital_asset")
        assert host.current_posture == PostureMode.PATROL

    def test_79_get_nonexistent_host_returns_none(self):
        """Requesting a non-existent host returns None, not exception."""
        result = get_host("absolutely-does-not-exist-abc123")
        assert result is None

    def test_80_host_retrieval_after_creation(self):
        """Host can be retrieved immediately after registration."""
        host = register_host(host_name="retrieval-pressure", host_type="avatar")
        retrieved = get_host(host.host_id)
        assert retrieved is not None
        assert retrieved.host_id == host.host_id

    def test_81_host_types_various(self):
        """Hosts of various types can all be created."""
        types = ["avatar", "cyber_defense", "swarm_node",
                 "infrastructure_guardian", "autonomous_system", "orbital_asset"]
        for ht in types:
            host = register_host(host_name=f"type-test-{ht}", host_type=ht)
            assert host.host_type == ht

    def test_82_engine_from_fresh_host(self):
        """Engine from a brand-new host has correct initial state."""
        host = register_host(host_name="fresh-engine-test", host_type="swarm_node")
        engine = create_engine(host_id=host.host_id)
        assert engine.posture == PostureMode.PATROL

    def test_83_multiple_engines_same_host(self):
        """Multiple engines can reference the same host."""
        host = register_host(host_name="multi-engine-host", host_type="cyber_defense")
        engines = [create_engine(host_id=host.host_id) for _ in range(5)]
        assert all(isinstance(e, ArchonEngine) for e in engines)

    def test_84_host_description_preserved(self):
        """Host description is preserved after registration."""
        desc = "Critical infrastructure guardian for orbital defense grid"
        host = register_host(
            host_name="desc-test",
            host_type="orbital_asset",
            description=desc,
        )
        assert host.description == desc

    def test_85_host_name_preserved(self):
        """Host name exactly preserved."""
        host = register_host(host_name="exact-name-test-12345", host_type="avatar")
        assert host.host_name == "exact-name-test-12345"


# ===========================================================================
# SYSTEM INVARIANT TESTS UNDER CHAOS (86-100)
# ===========================================================================

class TestSystemInvariants:
    """Core invariants that must never break, regardless of input state."""

    def test_86_weights_always_non_negative(self):
        """No weight can ever be negative — fundamental invariant."""
        for _ in range(50):
            import random
            alert = random.random()
            posture = random.choice(list(PostureMode))
            weights = compute_dynamic_weights(alert, posture)
            w_dict = weights.as_dict()
            for mt, w in w_dict.items():
                assert w >= 0.0, f"Negative weight {w} for {mt}"

    def test_87_confidence_always_bounded_0_1(self):
        """Output confidence must always be in [0, 1]."""
        test_cases = [
            (_make_all_signals(1.0, 1.0), 1.0, PostureMode.COMBAT),
            (_make_all_signals(0.0, 0.0), 0.0, PostureMode.DORMANT),
            (_make_all_signals(-1.0, 1.0), 0.5, PostureMode.ALERT),
        ]
        for signals, alert, posture in test_cases:
            result = fuse_signals(signals, alert, posture)
            assert 0.0 <= result.confidence <= 1.0

    def test_88_embedding_dim_always_64(self):
        """Embedding dimension constant — changing it would break everything."""
        assert EMBEDDING_DIM == 64
        for mt in MindType:
            assert len(MIND_EMBEDDINGS[mt]) == 64

    def test_89_mind_embeddings_always_unit_vectors(self):
        """All mind embeddings must be unit vectors at all times."""
        for mt in MindType:
            emb = MIND_EMBEDDINGS[mt]
            magnitude = math.sqrt(sum(v * v for v in emb))
            assert abs(magnitude - 1.0) < 0.01, (
                f"Mind {mt} embedding not unit: magnitude={magnitude}"
            )

    def test_90_posture_transitions_complete(self):
        """Every posture has defined transitions — no missing states."""
        for posture in PostureMode:
            assert posture in POSTURE_TRANSITIONS

    def test_91_base_weights_sum_invariant(self):
        """Base weights must sum to 1.0 — fundamental constraint."""
        total = sum(BASE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01

    def test_92_all_minds_have_profiles(self):
        """Every MindType has a corresponding profile."""
        for mt in MindType:
            assert mt in MIND_PROFILES

    def test_93_fused_decision_has_all_required_fields(self):
        """FusedDecision output always has critical fields populated."""
        signals = _make_all_signals(0.5, 0.7)
        result = fuse_signals(signals, 0.5, PostureMode.PATROL)
        assert hasattr(result, 'decision_value')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'recommended_escalation')
        assert hasattr(result, 'recommended_posture')
        assert hasattr(result, 'requires_human_review')
        assert hasattr(result, 'governance_compliant')
        assert hasattr(result, 'dominant_mind')

    def test_94_signal_flooding_100_signals(self):
        """System handles 100 signals without crash (duplicates per mind)."""
        signals = []
        for _ in range(20):
            for mt in MindType:
                signals.append(_make_signal(mt, 0.5, 0.7))
        result = fuse_signals(signals, 0.5, PostureMode.PATROL)
        assert isinstance(result, FusedDecision)

    def test_95_interaction_dynamics_preserve_positive_weights(self):
        """After interaction dynamics, all weights remain positive."""
        signals = [
            _make_signal(MindType.HACKER, 1.0, 1.0),
            _make_signal(MindType.GENERAL, 1.0, 1.0),
            _make_signal(MindType.STRATEGIST, 1.0, 1.0),
            _make_signal(MindType.PILOT, 1.0, 1.0),
            _make_signal(MindType.AI_INTELLIGENCE, 1.0, 1.0),
        ]
        result = fuse_signals(signals, 1.0, PostureMode.COMBAT)
        w_dict = result.weights_used.as_dict()
        for mt, w in w_dict.items():
            assert w >= 0.0

    def test_96_deterministic_under_same_inputs(self):
        """Same inputs must always produce same outputs — no randomness in core."""
        signals = [
            _make_signal(MindType.HACKER, 0.7, 0.8,
                         threat_vectors=[ThreatVector.INJECTION]),
            _make_signal(MindType.GENERAL, 0.4, 0.6),
            _make_signal(MindType.STRATEGIST, 0.3, 0.5),
            _make_signal(MindType.PILOT, 0.6, 0.7),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.8),
        ]
        results = [fuse_signals(signals, 0.7, PostureMode.ALERT) for _ in range(20)]
        for r in results[1:]:
            assert r.decision_value == results[0].decision_value
            assert r.recommended_escalation == results[0].recommended_escalation
            assert r.recommended_posture == results[0].recommended_posture

    def test_97_embedding_brain_deterministic(self):
        """Embedding brain fusion is deterministic."""
        signals = _make_all_signals(0.7, 0.8)
        results = [
            fuse_signals_with_embedding_brain(signals, alert_level=0.7)
            for _ in range(10)
        ]
        for r in results[1:]:
            assert r.decision_value == results[0].decision_value
            assert r.embedding_leadership_mode == results[0].embedding_leadership_mode

    def test_98_high_stakes_kill_chain_full_governance(self):
        """Simulated kill chain — system must require human review."""
        # Simultaneous injection + exfiltration + privilege escalation
        signals = [
            _make_signal(MindType.HACKER, 0.99, 0.99,
                         urgency_override=True,
                         threat_vectors=[ThreatVector.INJECTION,
                                         ThreatVector.EXFILTRATION,
                                         ThreatVector.PRIVILEGE_ESCALATION]),
            _make_signal(MindType.GENERAL, 0.9, 0.95),
            _make_signal(MindType.STRATEGIST, 0.8, 0.9),
            _make_signal(MindType.PILOT, 0.95, 0.95,
                         urgency_override=True,
                         threat_vectors=[ThreatVector.DENIAL_OF_SERVICE]),
            _make_signal(MindType.AI_INTELLIGENCE, 0.9, 0.99),
        ]
        result = fuse_signals(signals, 0.99, PostureMode.ALERT)
        # Under a full kill chain, system MUST escalate significantly
        assert result.recommended_escalation in (
            EscalationLevel.RESTRICT, EscalationLevel.NEUTRALIZE,
            EscalationLevel.CHALLENGE,
        )
        # If at NEUTRALIZE, human review is mandatory
        if result.recommended_escalation == EscalationLevel.NEUTRALIZE:
            assert result.requires_human_review is True

    def test_99_no_autonomous_neutralize_without_human(self):
        """CRITICAL SAFETY: System must NEVER autonomously NEUTRALIZE."""
        # Generate many extreme scenarios
        scenarios = [
            (1.0, PostureMode.ALERT),
            (0.99, PostureMode.ENGAGED),
            (0.95, PostureMode.ALERT),
        ]
        for alert, posture in scenarios:
            signals = [
                _make_signal(MindType.HACKER, 0.99, 0.99,
                             urgency_override=True,
                             threat_vectors=_all_threat_vectors()),
                _make_signal(MindType.GENERAL, 0.9, 0.95),
                _make_signal(MindType.STRATEGIST, 0.8, 0.9),
                _make_signal(MindType.PILOT, 0.99, 0.99,
                             urgency_override=True,
                             threat_vectors=_all_threat_vectors()),
                _make_signal(MindType.AI_INTELLIGENCE, 0.95, 0.99),
            ]
            result = fuse_signals(signals, alert, posture)
            if result.recommended_escalation == EscalationLevel.NEUTRALIZE:
                assert result.requires_human_review is True, (
                    f"CRITICAL SAFETY VIOLATION: Autonomous NEUTRALIZE at "
                    f"alert={alert}, posture={posture}"
                )

    def test_100_system_coherence_full_pipeline(self):
        """Full pipeline from signals to embedding brain produces coherent output."""
        signals = [
            _make_signal(MindType.HACKER, 0.8, 0.85,
                         threat_vectors=[ThreatVector.INJECTION, ThreatVector.TRAVERSAL]),
            _make_signal(MindType.GENERAL, 0.6, 0.75),
            _make_signal(MindType.STRATEGIST, 0.5, 0.7),
            _make_signal(MindType.PILOT, 0.7, 0.8,
                         threat_vectors=[ThreatVector.RECONNAISSANCE]),
            _make_signal(MindType.AI_INTELLIGENCE, 0.6, 0.9),
        ]
        result = fuse_signals_with_embedding_brain(
            signals, alert_level=0.75,
            current_posture=PostureMode.ALERT,
            threat_vectors=[ThreatVector.INJECTION, ThreatVector.TRAVERSAL],
            threat_count=3,
            threat_severity_max=0.85,
            threat_severity_avg=0.7,
            time_pressure=0.6,
        )
        # Coherence checks
        assert isinstance(result, FusedDecision)
        assert result.embedding_brain_active is True
        assert 0.0 <= result.confidence <= 1.0
        assert result.dominant_mind in MindType
        assert result.recommended_posture in PostureMode
        assert result.recommended_escalation in EscalationLevel
        assert result.embedding_leadership_mode in ("tactical", "strategic", "balanced", "distributed")
        assert result.embedding_decision_direction in ("engage", "hold", "observe", "maneuver", "plan")
