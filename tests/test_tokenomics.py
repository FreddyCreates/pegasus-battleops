"""
Tests for Tokenomics Engine — Measurement and Benchmarking Framework.

Validates:
    - Token Value Function computation
    - Cognitive Return Per Token (CRPT) scoring
    - Salience Allocation equations and budget distribution
    - Compression Efficiency metrics
    - Benchmark framework (tokenomic vs non-tokenomic)
    - Runtime Measurement Loop lifecycle
    - TokenomicsEngine orchestrator
    - Edge cases and validation
"""

import math
import sys
import os
import time

import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spatium_computationis.simulation.engines.tokenomics import (
    TokenWeights,
    TokenScore,
    CognitiveReturnScores,
    SalienceWeights,
    SalienceItem,
    SalienceEngine,
    BudgetAllocation,
    CompressionScores,
    BenchmarkScore,
    BenchmarkTask,
    BenchmarkResult,
    BenchmarkSuite,
    RuntimeMeasurementLoop,
    TokenomicsEngine,
    TokenomicsConfig,
    TaskClass,
    EvaluationCriterion,
    compute_token_value,
    compute_crpt,
    compute_salience_score,
    compute_compression_efficiency,
    compute_compression_ratio,
)


# ===========================================================================
# Token Value Function Tests
# ===========================================================================

class TestTokenValueFunction:
    """Test suite for the Token Value Function: TV(t) = Σw·x - w_n·N."""

    def test_zero_score_yields_zero_value(self):
        """A token with all-zero scores has zero value."""
        score = TokenScore()
        assert compute_token_value(score) == 0.0

    def test_positive_value_from_decision(self):
        """A token contributing decision value should be positive."""
        score = TokenScore(decision_value=4.0)
        tv = compute_token_value(score)
        assert tv == 4.0

    def test_negative_value_from_noise(self):
        """A token that is pure noise should have negative value."""
        score = TokenScore(noise=3.0)
        tv = compute_token_value(score)
        assert tv == -3.0

    def test_full_score_computation(self):
        """Full formula: TV = w_d·D + w_a·A + w_r·R + w_c·C + w_m·M - w_n·N."""
        score = TokenScore(
            decision_value=3.0,
            action_usefulness=2.0,
            risk_reduction=4.0,
            compression_value=1.0,
            memory_value=2.0,
            noise=1.5,
        )
        weights = TokenWeights(w_d=2.0, w_a=1.0, w_r=1.5, w_c=1.0, w_m=1.0, w_n=2.0)
        tv = compute_token_value(score, weights)
        # 2*3 + 1*2 + 1.5*4 + 1*1 + 1*2 - 2*1.5 = 6 + 2 + 6 + 1 + 2 - 3 = 14
        assert abs(tv - 14.0) < 1e-10

    def test_equal_weights_sum_components(self):
        """With equal unit weights, TV = D + A + R + C + M - N."""
        score = TokenScore(
            decision_value=1.0,
            action_usefulness=1.0,
            risk_reduction=1.0,
            compression_value=1.0,
            memory_value=1.0,
            noise=1.0,
        )
        tv = compute_token_value(score)
        assert abs(tv - 4.0) < 1e-10  # 5 - 1 = 4

    def test_custom_weights_amplify(self):
        """Higher weights amplify their component."""
        score = TokenScore(decision_value=1.0)
        w1 = TokenWeights(w_d=1.0)
        w5 = TokenWeights(w_d=5.0)
        assert compute_token_value(score, w5) == 5.0 * compute_token_value(score, w1)

    def test_invalid_weight_raises(self):
        """Negative weights should raise ValueError."""
        weights = TokenWeights(w_d=-1.0)
        score = TokenScore(decision_value=1.0)
        with pytest.raises(ValueError):
            compute_token_value(score, weights)

    def test_invalid_score_raises(self):
        """Scores outside [0, 5] should raise ValueError."""
        score = TokenScore(decision_value=6.0)
        with pytest.raises(ValueError):
            compute_token_value(score)

    def test_score_below_zero_raises(self):
        """Negative score values should raise ValueError."""
        score = TokenScore(noise=-1.0)
        with pytest.raises(ValueError):
            compute_token_value(score)

    def test_batch_scoring(self):
        """Batch of tokens should each be scored independently."""
        engine = TokenomicsEngine()
        scores = [
            TokenScore(decision_value=5.0),
            TokenScore(noise=5.0),
            TokenScore(decision_value=2.0, noise=2.0),
        ]
        values = engine.score_token_batch(scores)
        assert values[0] == 5.0
        assert values[1] == -5.0
        assert values[2] == 0.0


# ===========================================================================
# Cognitive Return Per Token Tests
# ===========================================================================

class TestCognitiveReturn:
    """Test suite for CRPT: (DQ + ACT + RISK + REUSE + LEARN) / TotalTokens."""

    def test_basic_crpt(self):
        """CRPT with known values."""
        scores = CognitiveReturnScores(
            decision_quality=4.0,
            actionability=3.0,
            risk_control=2.0,
            reuse_value=3.0,
            learning_gain=1.0,
        )
        # Total CR = 13, tokens = 100
        crpt = compute_crpt(scores, 100)
        assert abs(crpt - 0.13) < 1e-10

    def test_crpt_penalizes_long_outputs(self):
        """Same cognitive return with more tokens → lower CRPT."""
        scores = CognitiveReturnScores(
            decision_quality=4.0,
            actionability=4.0,
            risk_control=4.0,
            reuse_value=4.0,
            learning_gain=4.0,
        )
        crpt_short = compute_crpt(scores, 50)
        crpt_long = compute_crpt(scores, 500)
        assert crpt_short > crpt_long
        assert crpt_short == 10 * crpt_long

    def test_crpt_rewards_compact_useful(self):
        """High scores with few tokens → high CRPT."""
        scores = CognitiveReturnScores(
            decision_quality=5.0,
            actionability=5.0,
            risk_control=5.0,
            reuse_value=5.0,
            learning_gain=5.0,
        )
        crpt = compute_crpt(scores, 10)
        assert crpt == 2.5  # 25 / 10

    def test_zero_tokens_raises(self):
        """Zero tokens should raise ValueError."""
        scores = CognitiveReturnScores(decision_quality=1.0)
        with pytest.raises(ValueError):
            compute_crpt(scores, 0)

    def test_negative_tokens_raises(self):
        """Negative tokens should raise ValueError."""
        scores = CognitiveReturnScores(decision_quality=1.0)
        with pytest.raises(ValueError):
            compute_crpt(scores, -10)

    def test_total_property(self):
        """CognitiveReturnScores.total sums all five categories."""
        scores = CognitiveReturnScores(
            decision_quality=1.0,
            actionability=2.0,
            risk_control=3.0,
            reuse_value=4.0,
            learning_gain=5.0,
        )
        assert scores.total == 15.0

    def test_invalid_score_raises(self):
        """Scores outside [0, 5] should raise."""
        scores = CognitiveReturnScores(decision_quality=5.1)
        with pytest.raises(ValueError):
            compute_crpt(scores, 100)


# ===========================================================================
# Salience Allocation Tests
# ===========================================================================

class TestSalienceAllocation:
    """Test suite for Salience Scoring and Budget Allocation."""

    def test_basic_salience_score(self):
        """S_i = α·U + β·R + γ·M + δ·T + ε·N - ζ·K."""
        item = SalienceItem(
            urgency=3.0,
            risk=4.0,
            mission_relevance=2.0,
            time_sensitivity=1.0,
            novelty=5.0,
            known_context=2.0,
        )
        # With default weights (all 1.0): 3 + 4 + 2 + 1 + 5 - 2 = 13
        score = compute_salience_score(item)
        assert abs(score - 13.0) < 1e-10

    def test_known_context_reduces_salience(self):
        """Known context should decrease salience score."""
        novel = SalienceItem(urgency=3.0, novelty=5.0, known_context=0.0)
        known = SalienceItem(urgency=3.0, novelty=5.0, known_context=5.0)
        assert compute_salience_score(novel) > compute_salience_score(known)

    def test_custom_weights(self):
        """Custom weights should scale components."""
        item = SalienceItem(urgency=2.0, risk=1.0)
        weights = SalienceWeights(alpha=3.0, beta=2.0, gamma=0, delta=0, epsilon=0, zeta=0)
        score = compute_salience_score(item, weights)
        assert abs(score - 8.0) < 1e-10  # 3*2 + 2*1 = 8

    def test_budget_allocation_proportional(self):
        """Budget should be proportional to salience scores."""
        engine = SalienceEngine()
        engine.add_item(SalienceItem(label="A", urgency=4.0))  # salience = 4
        engine.add_item(SalienceItem(label="B", urgency=2.0))  # salience = 2
        engine.add_item(SalienceItem(label="C", urgency=1.0))  # salience = 1

        allocations = engine.allocate_budget(700)
        total_alloc = sum(a.allocated_tokens for a in allocations)
        assert total_alloc == 700

        # A should get roughly 4/7, B roughly 2/7, C roughly 1/7
        alloc_map = {a.label: a.allocated_tokens for a in allocations}
        assert alloc_map["A"] > alloc_map["B"] > alloc_map["C"]

    def test_negative_salience_gets_zero_budget(self):
        """Items with negative salience should receive no budget."""
        engine = SalienceEngine()
        engine.add_item(SalienceItem(label="Good", urgency=5.0))
        engine.add_item(SalienceItem(label="Bad", known_context=5.0))  # score = -5

        allocations = engine.allocate_budget(100)
        labels = [a.label for a in allocations]
        assert "Good" in labels
        assert "Bad" not in labels

    def test_budget_sums_to_total(self):
        """All allocations should sum to total budget."""
        engine = SalienceEngine()
        for i in range(5):
            engine.add_item(SalienceItem(label=f"Item{i}", urgency=float(i + 1)))
        allocations = engine.allocate_budget(1000)
        total = sum(a.allocated_tokens for a in allocations)
        assert total == 1000

    def test_rank_order(self):
        """Rank should return items from highest to lowest salience."""
        engine = SalienceEngine()
        engine.add_item(SalienceItem(label="Low", urgency=1.0))
        engine.add_item(SalienceItem(label="High", urgency=5.0))
        engine.add_item(SalienceItem(label="Mid", urgency=3.0))

        ranked = engine.rank()
        scores = [s for _, s in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_empty_budget_raises(self):
        """Zero or negative budget should raise ValueError."""
        engine = SalienceEngine()
        engine.add_item(SalienceItem(urgency=3.0))
        with pytest.raises(ValueError):
            engine.allocate_budget(0)

    def test_reset_clears_state(self):
        """Reset should clear all items and scores."""
        engine = SalienceEngine()
        engine.add_item(SalienceItem(urgency=3.0))
        engine.reset()
        assert engine.rank() == []

    def test_invalid_item_raises(self):
        """Item scores outside [0, 5] should raise."""
        item = SalienceItem(urgency=6.0)
        with pytest.raises(ValueError):
            compute_salience_score(item)


# ===========================================================================
# Compression Efficiency Tests
# ===========================================================================

class TestCompressionEfficiency:
    """Test suite for Compression Efficiency metrics."""

    def test_basic_cef(self):
        """CEF = (InfoRetained + ActionClarity + RiskPreserved) / OutputTokens."""
        scores = CompressionScores(
            information_retained=4.0,
            action_clarity=3.0,
            risk_preserved=3.0,
        )
        cef = compute_compression_efficiency(scores, 100)
        assert abs(cef - 0.10) < 1e-10  # 10 / 100

    def test_high_meaning_low_tokens_good(self):
        """High meaning preserved in few tokens → high CEF."""
        scores = CompressionScores(
            information_retained=5.0,
            action_clarity=5.0,
            risk_preserved=5.0,
        )
        cef = compute_compression_efficiency(scores, 10)
        assert cef == 1.5  # 15 / 10

    def test_low_meaning_many_tokens_bad(self):
        """Low meaning in many tokens → low CEF."""
        scores = CompressionScores(
            information_retained=1.0,
            action_clarity=1.0,
            risk_preserved=1.0,
        )
        cef = compute_compression_efficiency(scores, 1000)
        assert cef == 0.003  # 3 / 1000

    def test_compression_ratio(self):
        """Compression ratio = original / compressed."""
        ratio = compute_compression_ratio(1000, 250)
        assert ratio == 4.0

    def test_compression_ratio_invalid_raises(self):
        """Invalid inputs should raise."""
        with pytest.raises(ValueError):
            compute_compression_ratio(0, 100)
        with pytest.raises(ValueError):
            compute_compression_ratio(100, 0)

    def test_zero_output_tokens_raises(self):
        """Zero output tokens should raise."""
        scores = CompressionScores(information_retained=3.0)
        with pytest.raises(ValueError):
            compute_compression_efficiency(scores, 0)

    def test_total_property(self):
        """CompressionScores.total should sum components."""
        scores = CompressionScores(
            information_retained=2.0,
            action_clarity=3.0,
            risk_preserved=4.0,
        )
        assert scores.total == 9.0

    def test_invalid_score_raises(self):
        """Scores outside [0, 5] should raise."""
        scores = CompressionScores(information_retained=5.5)
        with pytest.raises(ValueError):
            compute_compression_efficiency(scores, 100)


# ===========================================================================
# Benchmark Framework Tests
# ===========================================================================

class TestBenchmarkFramework:
    """Test suite for the Tokenomic vs Non-Tokenomic benchmark system."""

    def test_benchmark_score_net(self):
        """Net score = DQ + ACT + RISK + REUSE + ACCURACY - WASTE."""
        score = BenchmarkScore(
            decision_quality=4.0,
            actionability=3.0,
            risk_control=4.0,
            reuse_value=2.0,
            accuracy=5.0,
            waste=1.0,
            total_tokens=100,
        )
        assert abs(score.net_score - 17.0) < 1e-10  # 4+3+4+2+5-1

    def test_score_per_token(self):
        """Score per token = net_score / total_tokens."""
        score = BenchmarkScore(
            decision_quality=5.0,
            actionability=5.0,
            risk_control=5.0,
            reuse_value=5.0,
            accuracy=5.0,
            waste=0.0,
            total_tokens=50,
        )
        assert score.score_per_token == 0.5  # 25 / 50

    def test_tokenomic_gain_positive(self):
        """Tokenomic system should show positive gain when more efficient."""
        task = BenchmarkTask(task_class=TaskClass.ESTIMATING, description="Test")
        score_a = BenchmarkScore(
            decision_quality=3.0, actionability=3.0, risk_control=3.0,
            reuse_value=2.0, accuracy=3.0, waste=2.0, total_tokens=500,
        )
        score_b = BenchmarkScore(
            decision_quality=4.0, actionability=4.0, risk_control=4.0,
            reuse_value=3.0, accuracy=4.0, waste=0.5, total_tokens=200,
        )
        result = BenchmarkResult(task=task, score_a=score_a, score_b=score_b)
        # A: (3+3+3+2+3-2)/500 = 12/500 = 0.024
        # B: (4+4+4+3+4-0.5)/200 = 18.5/200 = 0.0925
        # Gain = 0.0925 - 0.024 = 0.0685
        assert result.tokenomic_gain > 0
        assert abs(result.tokenomic_gain - 0.0685) < 1e-10

    def test_tokenomic_gain_negative_when_baseline_better(self):
        """Negative gain when baseline outperforms tokenomic system."""
        task = BenchmarkTask(task_class=TaskClass.INVOICE_EXECUTION)
        score_a = BenchmarkScore(
            decision_quality=5.0, actionability=5.0, risk_control=5.0,
            reuse_value=5.0, accuracy=5.0, waste=0.0, total_tokens=100,
        )
        score_b = BenchmarkScore(
            decision_quality=2.0, actionability=2.0, risk_control=2.0,
            reuse_value=2.0, accuracy=2.0, waste=3.0, total_tokens=200,
        )
        result = BenchmarkResult(task=task, score_a=score_a, score_b=score_b)
        assert result.tokenomic_gain < 0

    def test_benchmark_suite_aggregation(self):
        """Suite should aggregate results correctly."""
        suite = BenchmarkSuite()
        task1 = BenchmarkTask(task_class=TaskClass.ESTIMATING)
        task2 = BenchmarkTask(task_class=TaskClass.PROPOSAL_GENERATION)

        score_a = BenchmarkScore(
            decision_quality=2.0, actionability=2.0, risk_control=2.0,
            reuse_value=2.0, accuracy=2.0, waste=1.0, total_tokens=200,
        )
        score_b = BenchmarkScore(
            decision_quality=4.0, actionability=4.0, risk_control=4.0,
            reuse_value=4.0, accuracy=4.0, waste=0.5, total_tokens=100,
        )

        suite.record_result(task1, score_a, score_b)
        suite.record_result(task2, score_a, score_b)

        assert len(suite.results) == 2
        assert suite.mean_tokenomic_gain > 0
        assert suite.tokenomic_win_rate == 1.0

    def test_win_rate_mixed(self):
        """Win rate with mixed results."""
        suite = BenchmarkSuite()
        # Win for tokenomic
        suite.record_result(
            BenchmarkTask(),
            BenchmarkScore(decision_quality=2.0, accuracy=2.0, total_tokens=200),
            BenchmarkScore(decision_quality=4.0, accuracy=4.0, total_tokens=100),
        )
        # Loss for tokenomic
        suite.record_result(
            BenchmarkTask(),
            BenchmarkScore(decision_quality=5.0, accuracy=5.0, total_tokens=50),
            BenchmarkScore(decision_quality=1.0, accuracy=1.0, total_tokens=500),
        )
        assert suite.tokenomic_win_rate == 0.5

    def test_results_by_class(self):
        """Should filter results by task class."""
        suite = BenchmarkSuite()
        suite.record_result(
            BenchmarkTask(task_class=TaskClass.ESTIMATING),
            BenchmarkScore(decision_quality=3.0, total_tokens=100),
            BenchmarkScore(decision_quality=4.0, total_tokens=80),
        )
        suite.record_result(
            BenchmarkTask(task_class=TaskClass.RED_TEAM_REVIEW),
            BenchmarkScore(decision_quality=3.0, total_tokens=100),
            BenchmarkScore(decision_quality=4.0, total_tokens=80),
        )
        est_results = suite.get_results_by_class(TaskClass.ESTIMATING)
        assert len(est_results) == 1

    def test_summary(self):
        """Summary should contain expected keys."""
        suite = BenchmarkSuite()
        suite.record_result(
            BenchmarkTask(task_class=TaskClass.CASHFLOW_DECISION),
            BenchmarkScore(decision_quality=3.0, total_tokens=100),
            BenchmarkScore(decision_quality=4.0, total_tokens=80),
        )
        summary = suite.summary()
        assert "total_tasks" in summary
        assert "mean_tokenomic_gain" in summary
        assert "tokenomic_win_rate" in summary
        assert "by_class" in summary

    def test_invalid_score_raises(self):
        """Invalid benchmark scores should raise."""
        with pytest.raises(ValueError):
            BenchmarkScore(decision_quality=6.0, total_tokens=100).validate()
        with pytest.raises(ValueError):
            BenchmarkScore(decision_quality=3.0, total_tokens=0).validate()


# ===========================================================================
# Runtime Measurement Loop Tests
# ===========================================================================

class TestRuntimeMeasurementLoop:
    """Test suite for the 11-step Runtime Measurement Loop."""

    def test_loop_has_11_steps(self):
        """Loop should define exactly 11 steps."""
        loop = RuntimeMeasurementLoop()
        assert len(loop.steps) == 11

    def test_initial_state(self):
        """Fresh loop should be at step 0, not complete."""
        loop = RuntimeMeasurementLoop()
        assert loop.progress == 0.0
        assert not loop.is_complete
        assert loop.current_step is not None
        assert loop.current_step.step_number == 1

    def test_advance_progresses(self):
        """Advancing should move to the next step."""
        loop = RuntimeMeasurementLoop()
        step = loop.advance(result="task_classified")
        assert step.step_number == 1
        assert step.completed
        assert step.result == "task_classified"
        assert loop.current_step.step_number == 2

    def test_full_loop_completion(self):
        """Completing all 11 steps should mark loop complete."""
        loop = RuntimeMeasurementLoop()
        for i in range(11):
            loop.advance(result=f"step_{i+1}_done")
        assert loop.is_complete
        assert loop.progress == 1.0
        assert loop.current_step is None

    def test_advance_past_complete_raises(self):
        """Advancing past completion should raise."""
        loop = RuntimeMeasurementLoop()
        for _ in range(11):
            loop.advance()
        with pytest.raises(RuntimeError):
            loop.advance()

    def test_step_names_correct(self):
        """Step names should match the defined 11-step process."""
        loop = RuntimeMeasurementLoop()
        expected_names = [
            "classify_task", "estimate_risk", "rank_salience",
            "allocate_budget", "recruit_modules", "generate_response",
            "audit_compression", "score_cognitive_return", "detect_waste",
            "extract_reuse", "update_policy",
        ]
        actual_names = [s.name for s in loop.steps]
        assert actual_names == expected_names

    def test_get_state(self):
        """State snapshot should include expected fields."""
        loop = RuntimeMeasurementLoop()
        loop.advance()
        loop.advance()
        state = loop.get_state()
        assert state["current_step"] == 2
        assert state["steps_completed"] == 2
        assert state["steps_total"] == 11

    def test_finalize_returns_all_steps(self):
        """Finalize should return full diagnostic info."""
        loop = RuntimeMeasurementLoop()
        loop.advance(result="classified")
        final = loop.finalize()
        assert "steps" in final
        assert len(final["steps"]) == 11
        assert final["steps"][0]["completed"] is True
        assert final["steps"][1]["completed"] is False

    def test_policy_adjustment_recording(self):
        """Policy adjustments should be recorded."""
        loop = RuntimeMeasurementLoop()
        loop.record_policy_adjustment({"rule": "increase_risk_weight", "factor": 1.5})
        state = loop.get_state()
        assert state["policy_adjustments"] == 1

    def test_progress_fraction(self):
        """Progress should be a fraction from 0 to 1."""
        loop = RuntimeMeasurementLoop()
        assert loop.progress == 0.0
        loop.advance()
        assert abs(loop.progress - 1/11) < 1e-10
        for _ in range(10):
            loop.advance()
        assert loop.progress == 1.0


# ===========================================================================
# TokenomicsEngine Integration Tests
# ===========================================================================

class TestTokenomicsEngine:
    """Integration tests for the TokenomicsEngine orchestrator."""

    def test_creation(self):
        """Engine should be created with defaults."""
        engine = TokenomicsEngine()
        assert engine.engine_id is not None
        assert engine.total_measurements == 0
        assert engine.mean_crpt == 0.0

    def test_custom_config(self):
        """Engine should accept custom configuration."""
        config = TokenomicsConfig(
            default_budget=2000,
            compression_threshold=0.8,
            crpt_target=0.05,
        )
        engine = TokenomicsEngine(config)
        assert engine.config.default_budget == 2000

    def test_score_token(self):
        """Engine should compute token values."""
        engine = TokenomicsEngine()
        tv = engine.score_token(TokenScore(decision_value=4.0, noise=1.0))
        assert tv == 3.0

    def test_compute_cognitive_return_records(self):
        """CRPT computation should be recorded in history."""
        engine = TokenomicsEngine()
        scores = CognitiveReturnScores(
            decision_quality=4.0, actionability=3.0,
            risk_control=3.0, reuse_value=2.0, learning_gain=1.0,
        )
        crpt = engine.compute_cognitive_return(scores, 100)
        assert engine.total_measurements == 1
        assert engine.mean_crpt == crpt

    def test_allocate_budget_through_engine(self):
        """Engine should orchestrate salience-based budget allocation."""
        engine = TokenomicsEngine()
        items = [
            SalienceItem(label="Urgent", urgency=5.0, risk=4.0),
            SalienceItem(label="Routine", urgency=1.0, risk=1.0),
        ]
        allocations = engine.allocate_budget(items, total_budget=500)
        assert len(allocations) == 2
        assert sum(a.allocated_tokens for a in allocations) == 500
        # Urgent item should get more
        alloc_map = {a.label: a.allocated_tokens for a in allocations}
        assert alloc_map["Urgent"] > alloc_map["Routine"]

    def test_audit_compression_pass(self):
        """Compression audit should pass when CEF >= threshold."""
        engine = TokenomicsEngine(TokenomicsConfig(compression_threshold=0.05))
        result = engine.audit_compression(
            CompressionScores(information_retained=4.0, action_clarity=3.0, risk_preserved=3.0),
            output_tokens=100,
        )
        assert result["passed"] is True
        assert result["cef"] == 0.10

    def test_audit_compression_fail(self):
        """Compression audit should fail when CEF < threshold."""
        engine = TokenomicsEngine(TokenomicsConfig(compression_threshold=1.0))
        result = engine.audit_compression(
            CompressionScores(information_retained=1.0),
            output_tokens=100,
        )
        assert result["passed"] is False

    def test_measurement_loop_integration(self):
        """Engine should manage measurement loops."""
        engine = TokenomicsEngine()
        loop = engine.start_measurement_loop()
        assert not loop.is_complete
        for _ in range(11):
            loop.advance()
        assert loop.is_complete

    def test_get_state(self):
        """Engine state should include all metrics."""
        engine = TokenomicsEngine()
        engine.compute_cognitive_return(
            CognitiveReturnScores(decision_quality=3.0),
            total_tokens=50,
        )
        state = engine.get_state()
        assert state["total_measurements"] == 1
        assert state["mean_crpt"] > 0
        assert "config" in state

    def test_evaluation_criteria(self):
        """Should return all 8 evaluation criteria."""
        criteria = TokenomicsEngine.evaluation_criteria()
        assert len(criteria) == 8
        assert "crpt" in criteria
        assert "compression_fidelity" in criteria

    def test_task_classes_enum(self):
        """All 8 task classes should be defined."""
        assert len(TaskClass) == 8
        assert TaskClass.INVOICE_EXECUTION.value == "invoice_execution"
        assert TaskClass.MEMORY_CONSOLIDATION.value == "memory_consolidation"

    def test_full_workflow(self):
        """End-to-end workflow: allocate → generate → audit → score → benchmark."""
        engine = TokenomicsEngine(TokenomicsConfig(
            default_budget=500,
            compression_threshold=0.05,
        ))

        # 1. Allocate budget
        items = [
            SalienceItem(label="Critical", urgency=5.0, risk=5.0, mission_relevance=5.0),
            SalienceItem(label="Nice-to-have", urgency=1.0, risk=0.5),
        ]
        allocations = engine.allocate_budget(items)
        assert allocations[0].label == "Critical" or allocations[0].allocated_tokens > 200

        # 2. Start measurement loop
        loop = engine.start_measurement_loop()
        loop.advance(result=TaskClass.ESTIMATING)
        loop.advance(result={"risk": "high", "complexity": "medium"})
        loop.advance(result=allocations)

        # 3. Simulate response generation and audit
        loop.advance(result={"budget": 300})
        loop.advance(result=["estimator_mobilia"])
        loop.advance(result="Budget estimate: $45,000 for Phase 2")

        # 4. Audit compression
        audit = engine.audit_compression(
            CompressionScores(information_retained=4.5, action_clarity=4.0, risk_preserved=3.5),
            output_tokens=50,
        )
        loop.advance(result=audit)
        assert audit["passed"] is True

        # 5. Score cognitive return
        crpt = engine.compute_cognitive_return(
            CognitiveReturnScores(
                decision_quality=4.0,
                actionability=4.5,
                risk_control=3.5,
                reuse_value=3.0,
                learning_gain=2.0,
            ),
            total_tokens=50,
        )
        loop.advance(result=crpt)

        # 6. Detect waste, extract reuse, update policy
        loop.advance(result={"waste_tokens": 3})
        loop.advance(result={"rule": "Phase 2 budgets average $40-50k"})
        loop.advance(result={"adjustment": "increase_reuse_weight"})

        assert loop.is_complete
        assert engine.mean_crpt > 0
