"""
Tokenomics Engine — Measurement and Benchmarking Framework
⌬ Cognitive resource allocation, token value scoring, salience budgeting,
  compression auditing, and benchmark evaluation for AI systems.

This engine implements:
    - Token Value Function: TV(t) = w_d·D + w_a·A + w_r·R + w_c·C + w_m·M - w_n·N
    - Cognitive Return Per Token (CRPT) scoring across 5 categories
    - Salience Allocation with urgency/risk/mission/time/novelty ranking
    - Compression Efficiency metrics preserving meaning, action, and risk
    - Benchmark framework comparing tokenomic vs non-tokenomic systems
    - Runtime Measurement Loop with adaptive feedback

Doctrine:
    Do not optimize for fewer tokens. Optimize for higher-value tokens.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Task Classification — what kind of cognitive work is being measured
# ---------------------------------------------------------------------------

class TaskClass(str, Enum):
    """Classification of benchmark task types."""
    INVOICE_EXECUTION = "invoice_execution"
    ESTIMATING = "estimating"
    CASHFLOW_DECISION = "cashflow_decision"
    PROPOSAL_GENERATION = "proposal_generation"
    RESEARCH_SYNTHESIS = "research_synthesis"
    ARCHITECTURE_DESIGN = "architecture_design"
    RED_TEAM_REVIEW = "red_team_review"
    MEMORY_CONSOLIDATION = "memory_consolidation"


class EvaluationCriterion(str, Enum):
    """System-level evaluation criteria for mature tokenomic systems."""
    COGNITIVE_RETURN_PER_TOKEN = "crpt"
    COMPRESSION_FIDELITY = "compression_fidelity"
    ACTION_CONVERSION_RATE = "action_conversion_rate"
    RISK_PRESERVATION = "risk_preservation"
    REUSE_EXTRACTION_RATE = "reuse_extraction_rate"
    CONTEXT_HYGIENE = "context_hygiene"
    ADAPTIVE_DEPTH_ACCURACY = "adaptive_depth_accuracy"
    ERROR_AVOIDANCE = "error_avoidance"


# ---------------------------------------------------------------------------
# Token Value Function
# TV(t) = w_d·D_t + w_a·A_t + w_r·R_t + w_c·C_t + w_m·M_t - w_n·N_t
# ---------------------------------------------------------------------------

@dataclass
class TokenWeights:
    """Task-specific weighting coefficients for the Token Value Function.

    Each weight controls how much influence a component has on total token value.
    All weights should be non-negative. Default: equal weighting.
    """
    w_d: float = 1.0   # Decision value weight
    w_a: float = 1.0   # Action usefulness weight
    w_r: float = 1.0   # Risk reduction weight
    w_c: float = 1.0   # Compression contribution weight
    w_m: float = 1.0   # Memory/reuse value weight
    w_n: float = 1.0   # Noise/waste penalty weight

    def validate(self) -> None:
        """Ensure all weights are non-negative."""
        for name in ("w_d", "w_a", "w_r", "w_c", "w_m", "w_n"):
            val = getattr(self, name)
            if val < 0:
                raise ValueError(f"Weight {name} must be non-negative, got {val}")


@dataclass
class TokenScore:
    """Score components for a single token or token group.

    Positive contributors: decision, action, risk, compression, memory.
    Negative contributor: noise (redundancy, filler, attention waste).
    All scores range 0.0–5.0.
    """
    decision_value: float = 0.0      # D_t: decision quality contributed
    action_usefulness: float = 0.0   # A_t: action enablement
    risk_reduction: float = 0.0      # R_t: risk/uncertainty reduction
    compression_value: float = 0.0   # C_t: compression contribution
    memory_value: float = 0.0        # M_t: reuse/memory value
    noise: float = 0.0               # N_t: redundancy, filler, waste

    def validate(self) -> None:
        """Ensure all scores are within [0, 5]."""
        for attr in ("decision_value", "action_usefulness", "risk_reduction",
                     "compression_value", "memory_value", "noise"):
            val = getattr(self, attr)
            if not (0.0 <= val <= 5.0):
                raise ValueError(f"{attr} must be in [0, 5], got {val}")


def compute_token_value(score: TokenScore, weights: TokenWeights | None = None) -> float:
    """Compute Token Value: TV(t) = w_d·D + w_a·A + w_r·R + w_c·C + w_m·M - w_n·N.

    A token has positive value when it improves decision quality, enables action,
    reduces risk, compresses useful knowledge, or creates reusable memory.
    A token has negative value when it repeats known context, adds generic language,
    increases ambiguity, or consumes attention without improving the outcome.
    """
    if weights is None:
        weights = TokenWeights()
    weights.validate()
    score.validate()

    return (
        weights.w_d * score.decision_value
        + weights.w_a * score.action_usefulness
        + weights.w_r * score.risk_reduction
        + weights.w_c * score.compression_value
        + weights.w_m * score.memory_value
        - weights.w_n * score.noise
    )


# ---------------------------------------------------------------------------
# Cognitive Return Metrics
# CRPT = (DQ + ACT + RISK + REUSE + LEARN) / TotalTokens
# ---------------------------------------------------------------------------

@dataclass
class CognitiveReturnScores:
    """Five-category cognitive return scoring (each 0.0–5.0).

    DQ:    Did the response improve the actual decision?
    ACT:   Can the user or system act immediately?
    RISK:  Did the response identify or reduce meaningful failure modes?
    REUSE: Did the response create a reusable rule/template/memory/artifact?
    LEARN: Did the interaction improve future system behavior?
    """
    decision_quality: float = 0.0    # DQ
    actionability: float = 0.0       # ACT
    risk_control: float = 0.0        # RISK
    reuse_value: float = 0.0         # REUSE
    learning_gain: float = 0.0       # LEARN

    def validate(self) -> None:
        """Ensure all scores are within [0, 5]."""
        for attr in ("decision_quality", "actionability", "risk_control",
                     "reuse_value", "learning_gain"):
            val = getattr(self, attr)
            if not (0.0 <= val <= 5.0):
                raise ValueError(f"{attr} must be in [0, 5], got {val}")

    @property
    def total(self) -> float:
        """Total cognitive return: CR = DQ + ACT + RISK + REUSE + LEARN."""
        return (
            self.decision_quality
            + self.actionability
            + self.risk_control
            + self.reuse_value
            + self.learning_gain
        )


def compute_crpt(scores: CognitiveReturnScores, total_tokens: int) -> float:
    """Compute Cognitive Return Per Token.

    CRPT = (DQ + ACT + RISK + REUSE + LEARN) / TotalTokens

    Rewards systems that produce compact but useful outputs.
    Penalizes long outputs that do not improve action, judgment, risk, or reuse.
    """
    scores.validate()
    if total_tokens <= 0:
        raise ValueError(f"total_tokens must be positive, got {total_tokens}")
    return scores.total / total_tokens


# ---------------------------------------------------------------------------
# Salience Allocation Equations
# S_i = α·U + β·R + γ·M + δ·T + ε·N - ζ·K
# B_i = B_total · (S_i / ΣS)
# ---------------------------------------------------------------------------

@dataclass
class SalienceWeights:
    """Task-specific salience weighting coefficients.

    α = urgency weight
    β = risk/consequence weight
    γ = mission relevance weight
    δ = time sensitivity weight
    ε = novelty/uncertainty weight
    ζ = known-context penalty weight
    """
    alpha: float = 1.0   # Urgency
    beta: float = 1.0    # Risk/consequence
    gamma: float = 1.0   # Mission relevance
    delta: float = 1.0   # Time sensitivity
    epsilon: float = 1.0  # Novelty/uncertainty
    zeta: float = 1.0    # Known-context penalty

    def validate(self) -> None:
        """Ensure all weights are non-negative."""
        for name in ("alpha", "beta", "gamma", "delta", "epsilon", "zeta"):
            val = getattr(self, name)
            if val < 0:
                raise ValueError(f"Weight {name} must be non-negative, got {val}")


@dataclass
class SalienceItem:
    """An information unit to be scored for token budget allocation.

    Each item represents something the system *could* spend tokens on.
    The salience score determines how much budget it deserves.
    """
    item_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    label: str = ""
    urgency: float = 0.0           # U_i: how urgent
    risk: float = 0.0              # R_i: risk/consequence if ignored
    mission_relevance: float = 0.0  # M_i: alignment with primary mission
    time_sensitivity: float = 0.0   # T_i: decays in value over time
    novelty: float = 0.0           # N_i: new/uncertain information
    known_context: float = 0.0     # K_i: already settled/known (penalty)

    def validate(self) -> None:
        """Ensure all scores are within [0, 5]."""
        for attr in ("urgency", "risk", "mission_relevance",
                     "time_sensitivity", "novelty", "known_context"):
            val = getattr(self, attr)
            if not (0.0 <= val <= 5.0):
                raise ValueError(f"{attr} must be in [0, 5], got {val}")


def compute_salience_score(item: SalienceItem,
                           weights: SalienceWeights | None = None) -> float:
    """Compute salience score for an information unit.

    S_i = α·U + β·R + γ·M + δ·T + ε·N - ζ·K

    High salience items deserve more token budget. Known/settled context
    is penalized to prevent low-value repetition.
    """
    if weights is None:
        weights = SalienceWeights()
    weights.validate()
    item.validate()

    return (
        weights.alpha * item.urgency
        + weights.beta * item.risk
        + weights.gamma * item.mission_relevance
        + weights.delta * item.time_sensitivity
        + weights.epsilon * item.novelty
        - weights.zeta * item.known_context
    )


@dataclass
class BudgetAllocation:
    """Result of salience-based token budget allocation."""
    item_id: str
    label: str
    salience_score: float
    allocated_tokens: int
    budget_fraction: float


class SalienceEngine:
    """Allocates token budget proportionally based on salience scoring.

    B_i = B_total · (S_i / ΣS)

    Prevents low-value context from consuming high-value token space.
    Spends tokens on what is urgent, risky, mission-relevant, time-sensitive,
    uncertain, and not already known.
    """

    def __init__(self, weights: SalienceWeights | None = None):
        self.weights = weights or SalienceWeights()
        self._items: list[SalienceItem] = []
        self._scores: dict[str, float] = {}

    def add_item(self, item: SalienceItem) -> None:
        """Register an information unit for salience scoring."""
        self._items.append(item)
        self._scores[item.item_id] = compute_salience_score(item, self.weights)

    def rank(self) -> list[tuple[str, float]]:
        """Return items ranked by salience score (highest first)."""
        return sorted(self._scores.items(), key=lambda x: x[1], reverse=True)

    def allocate_budget(self, total_budget: int) -> list[BudgetAllocation]:
        """Allocate token budget proportionally to salience scores.

        Items with negative salience receive zero budget.
        Budget is distributed proportionally among positive-salience items.
        """
        if total_budget <= 0:
            raise ValueError(f"total_budget must be positive, got {total_budget}")

        # Only consider items with positive salience
        positive_items = [
            (item, self._scores[item.item_id])
            for item in self._items
            if self._scores[item.item_id] > 0
        ]

        if not positive_items:
            return []

        total_salience = sum(score for _, score in positive_items)

        allocations = []
        allocated_so_far = 0

        for i, (item, score) in enumerate(positive_items):
            fraction = score / total_salience
            if i == len(positive_items) - 1:
                # Last item gets remainder to avoid rounding loss
                tokens = total_budget - allocated_so_far
            else:
                tokens = int(round(total_budget * fraction))
                allocated_so_far += tokens

            allocations.append(BudgetAllocation(
                item_id=item.item_id,
                label=item.label,
                salience_score=score,
                allocated_tokens=tokens,
                budget_fraction=fraction,
            ))

        return allocations

    def reset(self) -> None:
        """Clear all items and scores."""
        self._items.clear()
        self._scores.clear()


# ---------------------------------------------------------------------------
# Compression Efficiency Metrics
# CE = MeaningPreserved / TokensUsed
# CEF = (InformationRetained + ActionClarity + RiskPreserved) / OutputTokens
# ---------------------------------------------------------------------------

@dataclass
class CompressionScores:
    """Scores for evaluating compression quality (each 0.0–5.0).

    Good compression reduces surface length while preserving correct action.
    Bad compression merely deletes context and increases operational risk.

    A compressed output passes the tokenomic test only if the user or
    downstream system can still act correctly.
    """
    information_retained: float = 0.0   # Preservation of task-relevant content
    action_clarity: float = 0.0         # Clarity of next step or decision
    risk_preserved: float = 0.0         # Preservation of caution/uncertainty/constraints

    def validate(self) -> None:
        """Ensure all scores are within [0, 5]."""
        for attr in ("information_retained", "action_clarity", "risk_preserved"):
            val = getattr(self, attr)
            if not (0.0 <= val <= 5.0):
                raise ValueError(f"{attr} must be in [0, 5], got {val}")

    @property
    def total(self) -> float:
        """Total meaning preserved."""
        return self.information_retained + self.action_clarity + self.risk_preserved


def compute_compression_efficiency(scores: CompressionScores,
                                   output_tokens: int) -> float:
    """Compute Compression Efficiency Factor.

    CEF = (InformationRetained + ActionClarity + RiskPreserved) / OutputTokens

    Higher values indicate better compression — more meaning per token.
    """
    scores.validate()
    if output_tokens <= 0:
        raise ValueError(f"output_tokens must be positive, got {output_tokens}")
    return scores.total / output_tokens


def compute_compression_ratio(original_tokens: int, compressed_tokens: int) -> float:
    """Compute raw compression ratio (original / compressed).

    A ratio of 2.0 means the output is half the length of the original.
    This does NOT measure quality — use CEF for meaning preservation.
    """
    if original_tokens <= 0:
        raise ValueError(f"original_tokens must be positive, got {original_tokens}")
    if compressed_tokens <= 0:
        raise ValueError(f"compressed_tokens must be positive, got {compressed_tokens}")
    return original_tokens / compressed_tokens


# ---------------------------------------------------------------------------
# Benchmark Framework — Tokenomic vs Non-Tokenomic comparison
# Score = DQ + ACT + RISK + REUSE + ACCURACY - WASTE
# TokenomicGain = (Score_B / Tokens_B) - (Score_A / Tokens_A)
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkScore:
    """Benchmark task score for a single system run.

    Score = DQ + ACT + RISK + REUSE + ACCURACY - WASTE

    A tokenomic system is superior when it produces equal or higher task score
    with fewer tokens, or significantly higher task score with justified tokens.
    """
    decision_quality: float = 0.0    # DQ
    actionability: float = 0.0       # ACT
    risk_control: float = 0.0        # RISK
    reuse_value: float = 0.0         # REUSE
    accuracy: float = 0.0            # ACCURACY: factual/math/procedural correctness
    waste: float = 0.0               # WASTE: unnecessary token expenditure
    total_tokens: int = 0            # Total tokens used (prompt + output)

    def validate(self) -> None:
        """Ensure scores are within [0, 5] and tokens positive."""
        for attr in ("decision_quality", "actionability", "risk_control",
                     "reuse_value", "accuracy", "waste"):
            val = getattr(self, attr)
            if not (0.0 <= val <= 5.0):
                raise ValueError(f"{attr} must be in [0, 5], got {val}")
        if self.total_tokens <= 0:
            raise ValueError(f"total_tokens must be positive, got {self.total_tokens}")

    @property
    def net_score(self) -> float:
        """Net benchmark score: DQ + ACT + RISK + REUSE + ACCURACY - WASTE."""
        return (
            self.decision_quality
            + self.actionability
            + self.risk_control
            + self.reuse_value
            + self.accuracy
            - self.waste
        )

    @property
    def score_per_token(self) -> float:
        """Score efficiency: net_score / total_tokens."""
        if self.total_tokens <= 0:
            return 0.0
        return self.net_score / self.total_tokens


@dataclass
class BenchmarkTask:
    """A single benchmark task for comparing systems."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_class: TaskClass = TaskClass.ESTIMATING
    description: str = ""
    input_text: str = ""


@dataclass
class BenchmarkResult:
    """Result comparing a tokenomic system (B) against a baseline (A)."""
    task: BenchmarkTask
    score_a: BenchmarkScore  # Non-tokenomic baseline
    score_b: BenchmarkScore  # Tokenomic system
    tokenomic_gain: float = 0.0

    def __post_init__(self):
        self.tokenomic_gain = self.compute_gain()

    def compute_gain(self) -> float:
        """TokenomicGain = (Score_B / Tokens_B) - (Score_A / Tokens_A).

        Positive gain means the tokenomic system is superior.
        """
        return self.score_b.score_per_token - self.score_a.score_per_token


class BenchmarkSuite:
    """Suite for running tokenomic vs non-tokenomic comparisons.

    Manages tasks, collects results, and computes aggregate metrics.
    """

    def __init__(self):
        self._tasks: list[BenchmarkTask] = []
        self._results: list[BenchmarkResult] = []

    def add_task(self, task: BenchmarkTask) -> None:
        """Register a benchmark task."""
        self._tasks.append(task)

    def record_result(self, task: BenchmarkTask,
                      score_a: BenchmarkScore,
                      score_b: BenchmarkScore) -> BenchmarkResult:
        """Record benchmark scores for both systems on a task."""
        score_a.validate()
        score_b.validate()
        result = BenchmarkResult(task=task, score_a=score_a, score_b=score_b)
        self._results.append(result)
        return result

    @property
    def results(self) -> list[BenchmarkResult]:
        """All recorded benchmark results."""
        return list(self._results)

    @property
    def mean_tokenomic_gain(self) -> float:
        """Average tokenomic gain across all tasks."""
        if not self._results:
            return 0.0
        return sum(r.tokenomic_gain for r in self._results) / len(self._results)

    @property
    def tokenomic_win_rate(self) -> float:
        """Fraction of tasks where the tokenomic system outperformed baseline."""
        if not self._results:
            return 0.0
        wins = sum(1 for r in self._results if r.tokenomic_gain > 0)
        return wins / len(self._results)

    def get_results_by_class(self, task_class: TaskClass) -> list[BenchmarkResult]:
        """Filter results by task class."""
        return [r for r in self._results if r.task.task_class == task_class]

    def summary(self) -> dict[str, Any]:
        """Aggregate benchmark summary."""
        return {
            "total_tasks": len(self._results),
            "mean_tokenomic_gain": self.mean_tokenomic_gain,
            "tokenomic_win_rate": self.tokenomic_win_rate,
            "by_class": {
                tc.value: {
                    "count": len(self.get_results_by_class(tc)),
                    "mean_gain": (
                        sum(r.tokenomic_gain for r in self.get_results_by_class(tc))
                        / max(1, len(self.get_results_by_class(tc)))
                    ),
                }
                for tc in TaskClass
                if self.get_results_by_class(tc)
            },
        }


# ---------------------------------------------------------------------------
# Runtime Measurement Loop
# The 11-step feedback loop that makes Tokenomics deployable
# ---------------------------------------------------------------------------

@dataclass
class MeasurementStep:
    """A single step in the runtime measurement loop."""
    step_number: int
    name: str
    description: str
    completed: bool = False
    result: Any = None
    timestamp: float = 0.0


class RuntimeMeasurementLoop:
    """The 11-step runtime measurement loop for tokenomic AI systems.

    Steps:
        1. Classify the task
        2. Estimate task risk and complexity
        3. Rank salience targets
        4. Allocate token budget
        5. Recruit only necessary modules or agents
        6. Generate the response or artifact
        7. Audit compression quality
        8. Score cognitive return
        9. Detect wasted tokens
        10. Extract reusable rules or memory
        11. Update future token allocation policy

    Creates a feedback loop where every interaction improves future efficiency.
    A successful interaction should not only solve the current task, but reduce
    the cost of solving similar tasks later.
    """

    STEP_DEFINITIONS = [
        (1, "classify_task", "Classify the task type and domain"),
        (2, "estimate_risk", "Estimate task risk and complexity"),
        (3, "rank_salience", "Rank salience targets for token allocation"),
        (4, "allocate_budget", "Allocate token budget based on salience"),
        (5, "recruit_modules", "Recruit only necessary modules or agents"),
        (6, "generate_response", "Generate the response or artifact"),
        (7, "audit_compression", "Audit compression quality"),
        (8, "score_cognitive_return", "Score cognitive return (CRPT)"),
        (9, "detect_waste", "Detect wasted tokens"),
        (10, "extract_reuse", "Extract reusable rules or memory"),
        (11, "update_policy", "Update future token allocation policy"),
    ]

    def __init__(self):
        self.loop_id: str = str(uuid.uuid4())[:8]
        self.steps: list[MeasurementStep] = [
            MeasurementStep(step_number=num, name=name, description=desc)
            for num, name, desc in self.STEP_DEFINITIONS
        ]
        self._current_step: int = 0
        self._history: list[dict[str, Any]] = []
        self._policy_adjustments: list[dict[str, Any]] = []

    @property
    def current_step(self) -> MeasurementStep | None:
        """The next step to be executed."""
        if self._current_step >= len(self.steps):
            return None
        return self.steps[self._current_step]

    @property
    def is_complete(self) -> bool:
        """Whether all 11 steps have been completed."""
        return self._current_step >= len(self.steps)

    @property
    def progress(self) -> float:
        """Fraction of loop completed (0.0 to 1.0)."""
        return self._current_step / len(self.steps)

    def advance(self, result: Any = None) -> MeasurementStep:
        """Complete the current step and advance to the next.

        Returns the completed step.
        """
        if self.is_complete:
            raise RuntimeError("Measurement loop already complete")

        step = self.steps[self._current_step]
        step.completed = True
        step.result = result
        step.timestamp = time.time()
        self._current_step += 1
        return step

    def record_policy_adjustment(self, adjustment: dict[str, Any]) -> None:
        """Record a policy adjustment from step 11 (update_policy)."""
        self._policy_adjustments.append({
            "loop_id": self.loop_id,
            "timestamp": time.time(),
            **adjustment,
        })

    def get_completed_steps(self) -> list[MeasurementStep]:
        """Return all completed steps."""
        return [s for s in self.steps if s.completed]

    def get_state(self) -> dict[str, Any]:
        """Snapshot of current loop state."""
        return {
            "loop_id": self.loop_id,
            "current_step": self._current_step,
            "is_complete": self.is_complete,
            "progress": self.progress,
            "steps_completed": len(self.get_completed_steps()),
            "steps_total": len(self.steps),
            "policy_adjustments": len(self._policy_adjustments),
        }

    def finalize(self) -> dict[str, Any]:
        """Finalize the loop and return full diagnostics."""
        return {
            "loop_id": self.loop_id,
            "completed": self.is_complete,
            "steps": [
                {
                    "step": s.step_number,
                    "name": s.name,
                    "completed": s.completed,
                    "result": s.result,
                }
                for s in self.steps
            ],
            "policy_adjustments": self._policy_adjustments,
        }


# ---------------------------------------------------------------------------
# Tokenomics Engine — Orchestrator combining all measurement components
# ---------------------------------------------------------------------------

@dataclass
class TokenomicsConfig:
    """Configuration for the Tokenomics Engine."""
    token_weights: TokenWeights = field(default_factory=TokenWeights)
    salience_weights: SalienceWeights = field(default_factory=SalienceWeights)
    default_budget: int = 1000
    compression_threshold: float = 0.5  # Minimum CEF to pass audit
    crpt_target: float = 0.01           # Target CRPT score


class TokenomicsEngine:
    """Tokenomics Measurement and Benchmarking Engine.

    Orchestrates all measurement components:
        - Token Value computation
        - Cognitive Return scoring
        - Salience-based budget allocation
        - Compression quality auditing
        - Benchmark comparisons
        - Runtime measurement loops

    Central hypothesis:
        AI systems governed by Tokenomic allocation will produce higher cognitive
        return per token than non-tokenomic systems, especially in operational,
        financial, research, and multi-step reasoning tasks.
    """

    def __init__(self, config: TokenomicsConfig | None = None):
        self.config = config or TokenomicsConfig()
        self.engine_id: str = str(uuid.uuid4())[:8]
        self._salience_engine = SalienceEngine(self.config.salience_weights)
        self._benchmark_suite = BenchmarkSuite()
        self._measurement_loops: list[RuntimeMeasurementLoop] = []
        self._token_history: list[dict[str, Any]] = []

    # --- Token Value ---

    def score_token(self, score: TokenScore) -> float:
        """Compute value of a token using configured weights."""
        return compute_token_value(score, self.config.token_weights)

    def score_token_batch(self, scores: list[TokenScore]) -> list[float]:
        """Score multiple tokens/groups."""
        return [self.score_token(s) for s in scores]

    # --- Cognitive Return ---

    def compute_cognitive_return(self, scores: CognitiveReturnScores,
                                 total_tokens: int) -> float:
        """Compute CRPT for an interaction."""
        crpt = compute_crpt(scores, total_tokens)
        self._token_history.append({
            "type": "crpt",
            "value": crpt,
            "tokens": total_tokens,
            "cr_total": scores.total,
            "timestamp": time.time(),
        })
        return crpt

    # --- Salience Allocation ---

    @property
    def salience_engine(self) -> SalienceEngine:
        """Access the salience allocation engine."""
        return self._salience_engine

    def allocate_budget(self, items: list[SalienceItem],
                        total_budget: int | None = None) -> list[BudgetAllocation]:
        """Score salience items and allocate token budget."""
        self._salience_engine.reset()
        for item in items:
            self._salience_engine.add_item(item)
        budget = total_budget or self.config.default_budget
        return self._salience_engine.allocate_budget(budget)

    # --- Compression Audit ---

    def audit_compression(self, scores: CompressionScores,
                          output_tokens: int) -> dict[str, Any]:
        """Audit compression quality and determine pass/fail.

        A compressed output passes only if CEF >= configured threshold.
        """
        cef = compute_compression_efficiency(scores, output_tokens)
        passed = cef >= self.config.compression_threshold
        return {
            "cef": cef,
            "passed": passed,
            "threshold": self.config.compression_threshold,
            "output_tokens": output_tokens,
            "meaning_preserved": scores.total,
        }

    # --- Benchmarking ---

    @property
    def benchmark_suite(self) -> BenchmarkSuite:
        """Access the benchmark comparison suite."""
        return self._benchmark_suite

    # --- Runtime Measurement Loop ---

    def start_measurement_loop(self) -> RuntimeMeasurementLoop:
        """Start a new 11-step runtime measurement loop."""
        loop = RuntimeMeasurementLoop()
        self._measurement_loops.append(loop)
        return loop

    # --- Diagnostics ---

    @property
    def total_measurements(self) -> int:
        """Total measurement interactions recorded."""
        return len(self._token_history)

    @property
    def mean_crpt(self) -> float:
        """Mean CRPT across all measured interactions."""
        crpt_entries = [e for e in self._token_history if e["type"] == "crpt"]
        if not crpt_entries:
            return 0.0
        return sum(e["value"] for e in crpt_entries) / len(crpt_entries)

    def get_state(self) -> dict[str, Any]:
        """Full engine state snapshot."""
        return {
            "engine_id": self.engine_id,
            "config": {
                "default_budget": self.config.default_budget,
                "compression_threshold": self.config.compression_threshold,
                "crpt_target": self.config.crpt_target,
            },
            "total_measurements": self.total_measurements,
            "mean_crpt": self.mean_crpt,
            "measurement_loops": len(self._measurement_loops),
            "benchmark_results": len(self._benchmark_suite.results),
        }

    # --- Evaluation Criteria ---

    @staticmethod
    def evaluation_criteria() -> dict[str, str]:
        """Return the 8 evaluation criteria for mature tokenomic systems."""
        return {
            EvaluationCriterion.COGNITIVE_RETURN_PER_TOKEN.value:
                "Useful cognition generated per total token spent",
            EvaluationCriterion.COMPRESSION_FIDELITY.value:
                "Degree to which compressed output preserves meaning",
            EvaluationCriterion.ACTION_CONVERSION_RATE.value:
                "Percentage of outputs that lead directly to correct action",
            EvaluationCriterion.RISK_PRESERVATION.value:
                "Ability to stay concise without hiding important uncertainty",
            EvaluationCriterion.REUSE_EXTRACTION_RATE.value:
                "Frequency of converting interactions into reusable rules/templates/memory",
            EvaluationCriterion.CONTEXT_HYGIENE.value:
                "Ability to avoid polluting context with irrelevant information",
            EvaluationCriterion.ADAPTIVE_DEPTH_ACCURACY.value:
                "Ability to expand or compress based on task stakes",
            EvaluationCriterion.ERROR_AVOIDANCE.value:
                "Ability to prevent math, scope, logic, or operational mistakes",
        }
