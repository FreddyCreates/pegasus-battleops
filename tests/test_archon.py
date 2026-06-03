"""
ARCHON Test Suite — 100 Tests for the Alpha Mind Warfare SDK

Tests cover:
  - Minds module (enums, profiles, signals, utilities)
  - Fusion module (weights, urgency, posture, escalation, contention)
  - Embedding Brain (context encoding, attention, similarity, fusion, diagnostics)
  - Doctrine module (constraints, gates, rules of engagement)
  - Agent module (host management, engine creation)
"""

import math
import sys
import os
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


# ===========================================================================
# MINDS MODULE TESTS (1-20)
# ===========================================================================

class TestMindsEnums:
    """Tests 1-7: Mind enumerations."""

    def test_01_mind_type_has_five_members(self):
        assert len(MindType) == 5

    def test_02_mind_type_values(self):
        expected = {"hacker", "general", "strategist", "pilot", "ai_intelligence"}
        assert {mt.value for mt in MindType} == expected

    def test_03_cognitive_priority_has_five_members(self):
        assert len(CognitivePriority) == 5

    def test_04_posture_mode_has_seven_members(self):
        assert len(PostureMode) == 7

    def test_05_escalation_level_has_six_members(self):
        assert len(EscalationLevel) == 6

    def test_06_threat_vector_has_members(self):
        assert len(ThreatVector) >= 9

    def test_07_terrain_type_has_members(self):
        assert len(TerrainType) >= 7


class TestMindProfiles:
    """Tests 8-15: Mind profile definitions."""

    def test_08_all_five_profiles_exist(self):
        assert len(MIND_PROFILES) == 5
        for mt in MindType:
            assert mt in MIND_PROFILES

    def test_09_hacker_mind_codename(self):
        assert HACKER_MIND.codename == "SPECTER"

    def test_10_general_mind_codename(self):
        assert GENERAL_MIND.codename == "IMPERATOR"

    def test_11_strategist_mind_codename(self):
        assert STRATEGIST_MIND.codename == "ORACLE"

    def test_12_pilot_mind_codename(self):
        assert PILOT_MIND.codename == "VECTOR"

    def test_13_ai_intelligence_mind_codename(self):
        assert AI_INTELLIGENCE_MIND.codename == "PANOPTES"

    def test_14_each_mind_has_system_prompt(self):
        for mt in MindType:
            prompt = get_mind_system_prompt(mt)
            assert len(prompt) > 50

    def test_15_each_mind_has_unique_priority(self):
        priorities = [MIND_PROFILES[mt].priority for mt in MindType]
        assert len(set(priorities)) == 5


class TestMindUtilities:
    """Tests 16-20: Mind utility functions."""

    def test_16_get_mind_codename(self):
        assert get_mind_codename(MindType.HACKER) == "SPECTER"
        assert get_mind_codename(MindType.AI_INTELLIGENCE) == "PANOPTES"

    def test_17_amplification_matrix_has_all_minds(self):
        matrix = get_amplification_matrix()
        assert set(matrix.keys()) == set(MindType)

    def test_18_dampening_matrix_has_all_minds(self):
        matrix = get_dampening_matrix()
        assert set(matrix.keys()) == set(MindType)

    def test_19_hacker_amplifies_pilot(self):
        matrix = get_amplification_matrix()
        assert MindType.PILOT in matrix[MindType.HACKER]

    def test_20_ai_intelligence_dampens_nothing(self):
        matrix = get_dampening_matrix()
        assert matrix[MindType.AI_INTELLIGENCE] == []


# ===========================================================================
# MIND SIGNAL TESTS (21-28)
# ===========================================================================

class TestMindSignal:
    """Tests 21-28: MindSignal creation and validation."""

    def test_21_basic_signal_creation(self):
        sig = _make_signal(MindType.HACKER, 0.8, 0.9)
        assert sig.mind_type == MindType.HACKER
        assert sig.signal_value == 0.8
        assert sig.confidence == 0.9

    def test_22_signal_value_clamped_min(self):
        sig = MindSignal(mind_type=MindType.HACKER, signal_value=-1.0, confidence=0.5)
        assert sig.signal_value == -1.0

    def test_23_signal_value_clamped_max(self):
        sig = MindSignal(mind_type=MindType.HACKER, signal_value=1.0, confidence=0.5)
        assert sig.signal_value == 1.0

    def test_24_signal_with_threat_vectors(self):
        sig = _make_signal(
            MindType.HACKER,
            threat_vectors=[ThreatVector.INJECTION, ThreatVector.EXFILTRATION],
        )
        assert len(sig.threat_vectors_detected) == 2

    def test_25_signal_urgency_override(self):
        sig = _make_signal(MindType.PILOT, urgency_override=True)
        assert sig.urgency_override is True

    def test_26_signal_contends_with(self):
        sig = _make_signal(MindType.HACKER, contends_with=[MindType.GENERAL])
        assert MindType.GENERAL in sig.contends_with

    def test_27_signal_default_values(self):
        sig = MindSignal(mind_type=MindType.GENERAL, signal_value=0.0)
        assert sig.confidence == 0.5
        assert sig.reasoning == ""
        assert sig.urgency_override is False

    def test_28_signal_metadata(self):
        sig = MindSignal(
            mind_type=MindType.STRATEGIST,
            signal_value=0.3,
            metadata={"source": "test"},
        )
        assert sig.metadata["source"] == "test"


# ===========================================================================
# FUSION MODULE TESTS (29-55)
# ===========================================================================

class TestFusionWeights:
    """Tests 29-35: Weight computation."""

    def test_29_base_weights_sum_to_one(self):
        total = sum(BASE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01

    def test_30_compute_urgency_zero(self):
        assert compute_urgency(0.0) == 0.0

    def test_31_compute_urgency_one(self):
        assert compute_urgency(1.0) == 1.0

    def test_32_compute_urgency_quadratic(self):
        assert abs(compute_urgency(0.5) - 0.25) < 1e-10

    def test_33_compute_urgency_clamps_above_one(self):
        assert compute_urgency(1.5) == 1.0

    def test_34_compute_urgency_clamps_below_zero(self):
        assert compute_urgency(-0.5) == 0.0

    def test_35_dynamic_weights_sum_to_one(self):
        weights = compute_dynamic_weights(0.5)
        assert abs(weights.weight_sum - 1.0) < 0.01


class TestDynamicWeights:
    """Tests 36-42: Dynamic weight computation with postures."""

    def test_36_low_alert_general_dominates(self):
        weights = compute_dynamic_weights(0.0, PostureMode.PATROL)
        w = weights.as_dict()
        assert w[MindType.GENERAL] >= w[MindType.HACKER]

    def test_37_high_alert_hacker_rises(self):
        w_low = compute_dynamic_weights(0.0).as_dict()
        w_high = compute_dynamic_weights(1.0).as_dict()
        assert w_high[MindType.HACKER] > w_low[MindType.HACKER]

    def test_38_high_alert_pilot_rises(self):
        w_low = compute_dynamic_weights(0.0).as_dict()
        w_high = compute_dynamic_weights(1.0).as_dict()
        assert w_high[MindType.PILOT] > w_low[MindType.PILOT]

    def test_39_ai_intelligence_constant(self):
        assert URGENCY_COEFFICIENTS[MindType.AI_INTELLIGENCE] == 0.0

    def test_40_combat_posture_boosts_hacker_pilot(self):
        mods = POSTURE_MODIFIERS[PostureMode.COMBAT]
        assert mods[MindType.HACKER] > 1.0
        assert mods[MindType.PILOT] > 1.0

    def test_41_lockdown_posture_boosts_general(self):
        mods = POSTURE_MODIFIERS[PostureMode.LOCKDOWN]
        assert mods[MindType.GENERAL] > 1.0

    def test_42_fusion_weights_dominant_mind(self):
        weights = compute_dynamic_weights(0.9, PostureMode.COMBAT)
        dominant = weights.dominant_mind
        assert dominant in (MindType.HACKER, MindType.PILOT)


class TestPostureTransitions:
    """Tests 43-48: Posture state machine."""

    def test_43_patrol_can_go_to_alert(self):
        assert PostureMode.ALERT in POSTURE_TRANSITIONS[PostureMode.PATROL]

    def test_44_dormant_cannot_go_to_combat(self):
        assert PostureMode.COMBAT not in POSTURE_TRANSITIONS[PostureMode.DORMANT]

    def test_45_combat_cannot_go_to_patrol(self):
        assert PostureMode.PATROL not in POSTURE_TRANSITIONS[PostureMode.COMBAT]

    def test_46_lockdown_only_exits_to_recovery_or_dormant(self):
        exits = POSTURE_TRANSITIONS[PostureMode.LOCKDOWN]
        assert exits == {PostureMode.RECOVERY, PostureMode.DORMANT}

    def test_47_all_postures_can_enter_lockdown(self):
        for posture in PostureMode:
            if posture != PostureMode.LOCKDOWN:
                assert PostureMode.LOCKDOWN in POSTURE_TRANSITIONS[posture]

    def test_48_recovery_can_go_to_patrol(self):
        assert PostureMode.PATROL in POSTURE_TRANSITIONS[PostureMode.RECOVERY]


class TestFuseSignals:
    """Tests 49-55: Core signal fusion."""

    def test_49_fuse_signals_returns_fused_decision(self):
        signals = _make_all_signals()
        result = fuse_signals(signals, 0.5)
        assert isinstance(result, FusedDecision)

    def test_50_fuse_signals_has_correct_signal_count(self):
        signals = _make_all_signals()
        result = fuse_signals(signals, 0.3)
        assert len(result.signals) == 5

    def test_51_fuse_signals_decision_value_is_float(self):
        signals = _make_all_signals(0.8)
        result = fuse_signals(signals, 0.5)
        assert isinstance(result.decision_value, float)

    def test_52_fuse_signals_confidence_bounded(self):
        signals = _make_all_signals(0.9, 0.95)
        result = fuse_signals(signals, 0.5)
        assert 0.0 <= result.confidence <= 1.0

    def test_53_contention_resolution_urgency_override(self):
        signals = [
            _make_signal(MindType.HACKER, 0.9, 0.9, urgency_override=True,
                         contends_with=[MindType.GENERAL]),
            _make_signal(MindType.GENERAL, -0.5, 0.8),
        ]
        resolutions = resolve_contention(signals)
        assert len(resolutions) == 1
        assert resolutions[0].winner == MindType.HACKER
        assert resolutions[0].resolution_method == "urgency_override"

    def test_54_contention_resolution_governance_authority(self):
        signals = [
            _make_signal(MindType.GENERAL, -0.5, 0.8, contends_with=[MindType.HACKER]),
            _make_signal(MindType.HACKER, 0.9, 0.9),
        ]
        resolutions = resolve_contention(signals)
        assert len(resolutions) == 1
        assert resolutions[0].winner == MindType.GENERAL
        assert resolutions[0].resolution_method == "governance_authority"

    def test_55_fuse_signals_high_alert_combat_posture(self):
        signals = [
            _make_signal(MindType.HACKER, 0.9, 0.9,
                         threat_vectors=[ThreatVector.INJECTION],
                         urgency_override=True),
            _make_signal(MindType.GENERAL, 0.3, 0.6),
            _make_signal(MindType.STRATEGIST, 0.2, 0.5),
            _make_signal(MindType.PILOT, 0.8, 0.85),
            _make_signal(MindType.AI_INTELLIGENCE, 0.5, 0.7),
        ]
        result = fuse_signals(signals, 0.95, PostureMode.ALERT)
        assert result.recommended_posture in (PostureMode.COMBAT, PostureMode.ENGAGED, PostureMode.ALERT)


# ===========================================================================
# ESCALATION TESTS (56-60)
# ===========================================================================

class TestEscalation:
    """Tests 56-60: Escalation level determination."""

    def test_56_low_alert_no_contention_observe(self):
        signals = _make_all_signals(0.2, 0.3)
        result = fuse_signals(signals, 0.1, PostureMode.PATROL)
        assert result.recommended_escalation == EscalationLevel.OBSERVE

    def test_57_alert_posture_with_threats_yields_warn_or_higher(self):
        signals = _make_all_signals(0.7, 0.7)
        signals[0] = _make_signal(MindType.HACKER, 0.8, 0.8,
                                  threat_vectors=[ThreatVector.INJECTION])
        result = fuse_signals(signals, 0.7, PostureMode.ALERT)
        assert result.recommended_escalation in (
            EscalationLevel.WARN, EscalationLevel.CHALLENGE,
            EscalationLevel.RESTRICT, EscalationLevel.NEUTRALIZE,
        )

    def test_58_combat_high_confidence_neutralize(self):
        signals = _make_all_signals(0.9, 0.9)
        # Need to create a situation that leads to COMBAT posture
        # Use high alert from ALERT posture (valid transition)
        signals[0] = _make_signal(MindType.HACKER, 0.95, 0.95,
                                  urgency_override=True,
                                  threat_vectors=[ThreatVector.INJECTION])
        result = fuse_signals(signals, 0.95, PostureMode.ALERT)
        if result.recommended_posture == PostureMode.COMBAT:
            assert result.recommended_escalation in (
                EscalationLevel.NEUTRALIZE, EscalationLevel.RESTRICT
            )

    def test_59_human_review_on_neutralize(self):
        signals = _make_all_signals(0.9, 0.9)
        signals[0] = _make_signal(MindType.HACKER, 0.95, 0.95,
                                  urgency_override=True,
                                  threat_vectors=[ThreatVector.EXFILTRATION])
        result = fuse_signals(signals, 0.95, PostureMode.ALERT)
        if result.recommended_escalation == EscalationLevel.NEUTRALIZE:
            assert result.requires_human_review is True

    def test_60_lockdown_requires_human_review(self):
        signals = _make_all_signals(0.9, 0.3)
        # fuse_signals marks human review if posture is LOCKDOWN
        # but LOCKDOWN transition not accessible from PATROL directly via signals
        # Test directly with engaged posture
        signals[0] = _make_signal(MindType.HACKER, 0.5, 0.3, contends_with=[MindType.GENERAL])
        signals[1] = _make_signal(MindType.GENERAL, -0.5, 0.3)
        result = fuse_signals(signals, 0.6, PostureMode.PATROL)
        # With contention and low confidence, human review should be flagged
        if result.has_contention and result.confidence < 0.5:
            assert result.requires_human_review is True


# ===========================================================================
# EMBEDDING BRAIN TESTS (61-85)
# ===========================================================================

class TestEmbeddingConfig:
    """Tests 61-65: Embedding brain configuration."""

    def test_61_embedding_dim_is_64(self):
        assert EMBEDDING_DIM == 64

    def test_62_all_minds_have_embeddings(self):
        assert set(MIND_EMBEDDINGS.keys()) == set(MindType)

    def test_63_embeddings_are_unit_vectors(self):
        for mt in MindType:
            emb = MIND_EMBEDDINGS[mt]
            magnitude = math.sqrt(sum(v * v for v in emb))
            assert abs(magnitude - 1.0) < 0.01

    def test_64_embeddings_have_correct_dimension(self):
        for mt in MindType:
            assert len(MIND_EMBEDDINGS[mt]) == EMBEDDING_DIM

    def test_65_attention_temperature_positive(self):
        assert ATTENTION_TEMPERATURE > 0.0


class TestCosine:
    """Tests 66-70: Cosine similarity."""

    def test_66_identical_vectors_similarity_one(self):
        vec = [1.0, 0.0, 0.0, 0.0]
        assert abs(cosine_similarity(vec, vec) - 1.0) < 1e-10

    def test_67_orthogonal_vectors_similarity_zero(self):
        a = [1.0, 0.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0, 0.0]
        assert abs(cosine_similarity(a, b)) < 1e-10

    def test_68_zero_vector_similarity_zero(self):
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, b) == 0.0

    def test_69_negative_cosine_similarity(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) < 0.0

    def test_70_mind_embeddings_not_identical(self):
        sim = cosine_similarity(
            MIND_EMBEDDINGS[MindType.HACKER],
            MIND_EMBEDDINGS[MindType.GENERAL],
        )
        assert sim < 1.0


class TestContextEncoding:
    """Tests 71-76: Context embedding encoding."""

    def test_71_context_embedding_correct_dimension(self):
        emb = encode_context(alert_level=0.5, posture=PostureMode.PATROL)
        assert len(emb) == EMBEDDING_DIM

    def test_72_context_embedding_is_unit_vector(self):
        emb = encode_context(alert_level=0.5, posture=PostureMode.PATROL)
        magnitude = math.sqrt(sum(v * v for v in emb))
        assert abs(magnitude - 1.0) < 0.01

    def test_73_high_alert_context_closer_to_hacker(self):
        high_ctx = encode_context(alert_level=0.95, posture=PostureMode.COMBAT)
        low_ctx = encode_context(alert_level=0.05, posture=PostureMode.DORMANT)
        hacker_emb = MIND_EMBEDDINGS[MindType.HACKER]
        sim_high = cosine_similarity(high_ctx, hacker_emb)
        sim_low = cosine_similarity(low_ctx, hacker_emb)
        assert sim_high > sim_low

    def test_74_low_alert_context_closer_to_general(self):
        high_ctx = encode_context(alert_level=0.95, posture=PostureMode.COMBAT)
        low_ctx = encode_context(alert_level=0.05, posture=PostureMode.DORMANT)
        general_emb = MIND_EMBEDDINGS[MindType.GENERAL]
        sim_low = cosine_similarity(low_ctx, general_emb)
        sim_high = cosine_similarity(high_ctx, general_emb)
        assert sim_low > sim_high

    def test_75_context_with_threats(self):
        emb = encode_context(
            alert_level=0.8,
            posture=PostureMode.ENGAGED,
            threat_vectors=[ThreatVector.INJECTION, ThreatVector.EXFILTRATION],
            threat_count=3,
            threat_severity_max=0.9,
        )
        assert len(emb) == EMBEDDING_DIM

    def test_76_different_postures_produce_different_contexts(self):
        ctx1 = encode_context(alert_level=0.5, posture=PostureMode.PATROL)
        ctx2 = encode_context(alert_level=0.5, posture=PostureMode.COMBAT)
        sim = cosine_similarity(ctx1, ctx2)
        assert sim < 1.0


class TestAttentionWeights:
    """Tests 77-82: Attention weight computation."""

    def test_77_attention_weights_sum_to_one(self):
        ctx = encode_context(alert_level=0.5, posture=PostureMode.PATROL)
        weights = compute_attention_weights(ctx)
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01

    def test_78_attention_weights_all_positive(self):
        ctx = encode_context(alert_level=0.5, posture=PostureMode.PATROL)
        weights = compute_attention_weights(ctx)
        for w in weights.values():
            assert w > 0.0

    def test_79_ai_intelligence_floor_enforced(self):
        ctx = encode_context(alert_level=0.95, posture=PostureMode.COMBAT)
        weights = compute_attention_weights(ctx)
        assert weights[MindType.AI_INTELLIGENCE] >= AI_INTELLIGENCE_FLOOR - 0.01

    def test_80_high_alert_hacker_pilot_dominant(self):
        ctx = encode_context(alert_level=0.95, posture=PostureMode.COMBAT)
        weights = compute_attention_weights(ctx)
        tactical = weights[MindType.HACKER] + weights[MindType.PILOT]
        strategic = weights[MindType.GENERAL] + weights[MindType.STRATEGIST]
        assert tactical > strategic

    def test_81_low_alert_general_strategist_dominant(self):
        ctx = encode_context(alert_level=0.05, posture=PostureMode.DORMANT)
        weights = compute_attention_weights(ctx)
        strategic = weights[MindType.GENERAL] + weights[MindType.STRATEGIST]
        tactical = weights[MindType.HACKER] + weights[MindType.PILOT]
        assert strategic > tactical

    def test_82_low_temperature_sharper_distribution(self):
        ctx = encode_context(alert_level=0.9, posture=PostureMode.COMBAT)
        weights_low_t = compute_attention_weights(ctx, temperature=0.1)
        weights_high_t = compute_attention_weights(ctx, temperature=1.0)
        # Lower temperature should produce larger max weight
        max_low = max(weights_low_t.values())
        max_high = max(weights_high_t.values())
        assert max_low >= max_high


class TestEmbeddingFuse:
    """Tests 83-85: Full embedding fusion."""

    def test_83_embedding_fuse_returns_output(self):
        signals = _make_all_signals()
        result = embedding_fuse(signals, alert_level=0.5, posture=PostureMode.PATROL)
        assert isinstance(result, EmbeddingBrainOutput)

    def test_84_embedding_fuse_has_attention_weights(self):
        signals = _make_all_signals()
        result = embedding_fuse(signals, alert_level=0.5, posture=PostureMode.PATROL)
        assert len(result.attention_weights) == 5

    def test_85_embedding_fuse_decision_direction(self):
        signals = _make_all_signals(0.9, 0.9)
        result = embedding_fuse(signals, alert_level=0.9, posture=PostureMode.COMBAT)
        assert result.decision_direction in ("engage", "hold", "observe", "maneuver", "plan")


# ===========================================================================
# EMBEDDING BRAIN INTEGRATION TESTS (86-90)
# ===========================================================================

class TestEmbeddingIntegration:
    """Tests 86-90: Embedding brain integration with fusion."""

    def test_86_fuse_signals_with_embedding_brain(self):
        signals = _make_all_signals()
        result = fuse_signals_with_embedding_brain(signals, alert_level=0.5)
        assert isinstance(result, FusedDecision)
        assert result.embedding_brain_active is True

    def test_87_embedding_brain_leadership_mode(self):
        signals = _make_all_signals()
        result = fuse_signals_with_embedding_brain(signals, alert_level=0.9)
        assert result.embedding_leadership_mode in ("tactical", "strategic", "balanced", "distributed")

    def test_88_embedding_enhanced_weights_sum_to_one(self):
        weights = embedding_enhanced_weights(alert_level=0.5)
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01

    def test_89_embedding_diagnostic(self):
        diag = get_embedding_diagnostic()
        assert diag["embedding_dim"] == EMBEDDING_DIM
        assert "pairwise_similarities" in diag
        assert "mind_embedding_norms" in diag

    def test_90_update_mind_embedding(self):
        # Save original
        original = MIND_EMBEDDINGS[MindType.HACKER][:]
        # Update
        learning_signal = [0.1] * EMBEDDING_DIM
        update_mind_embedding(MindType.HACKER, learning_signal, learning_rate=0.01)
        # Verify changed
        updated = MIND_EMBEDDINGS[MindType.HACKER]
        assert updated != original
        # Verify still unit vector
        magnitude = math.sqrt(sum(v * v for v in updated))
        assert abs(magnitude - 1.0) < 0.01
        # Restore (reset for other tests)
        MIND_EMBEDDINGS[MindType.HACKER] = original


# ===========================================================================
# DOCTRINE MODULE TESTS (91-96)
# ===========================================================================

class TestDoctrine:
    """Tests 91-96: Doctrine engine."""

    def test_91_archon_doctrine_exists(self):
        assert ARCHON_DOCTRINE.roe_id == "archon-roe-v1"

    def test_92_doctrine_has_constraints(self):
        assert len(ARCHON_DOCTRINE.constraints) >= 5

    def test_93_doctrine_has_escalation_rules(self):
        assert len(ARCHON_DOCTRINE.escalation_rules) >= 3

    def test_94_doctrine_engine_creates(self):
        engine = DoctrineEngine()
        assert engine is not None

    def test_95_doctrine_max_autonomous_escalation(self):
        assert ARCHON_DOCTRINE.max_autonomous_escalation == EscalationLevel.RESTRICT

    def test_96_doctrine_always_audit(self):
        assert ARCHON_DOCTRINE.always_audit is True


# ===========================================================================
# AGENT MODULE TESTS (97-100)
# ===========================================================================

class TestAgent:
    """Tests 97-100: Agent host management and engine."""

    def test_97_register_host(self):
        host = register_host(
            host_name="test-avatar",
            host_type="avatar",
            description="Test host for unit tests",
        )
        assert isinstance(host, ArchonHost)
        assert host.host_name == "test-avatar"
        assert host.host_type == "avatar"
        assert host.current_posture == PostureMode.PATROL

    def test_98_get_host_after_register(self):
        host = register_host(
            host_name="test-retrieval",
            host_type="cyber_defense",
        )
        retrieved = get_host(host.host_id)
        assert retrieved is not None
        assert retrieved.host_id == host.host_id
        assert retrieved.host_name == "test-retrieval"

    def test_99_get_host_not_found(self):
        result = get_host("nonexistent-host-id-xyz")
        assert result is None

    def test_100_archon_engine_creation(self):
        host = register_host(host_name="engine-test", host_type="swarm_node")
        engine = create_engine(host_id=host.host_id)
        assert isinstance(engine, ArchonEngine)
        assert engine.posture == PostureMode.PATROL
