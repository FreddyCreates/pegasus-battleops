"""
Spatium Computationis — Engine Suite
⌬ Production-grade physics, geometry, mini-verse, and tokenomics engines.

Engines:
    - PhysicsEngine: Newtonian + relativistic mechanics, field theory, conservation
    - GeometryEngine: Riemannian manifolds, metric tensors, geodesics, curvature
    - MiniVerse: Self-contained universe with configurable physical constants
    - TokenomicsEngine: Measurement & benchmarking for cognitive resource allocation
"""

from .physics import PhysicsEngine, Force, Field, Particle, PhysicsConstants
from .geometry import (
    GeometryEngine,
    MetricTensor,
    Manifold,
    Geodesic,
    CurvatureTensor,
)
from .miniverse import MiniVerse, MiniVerseConfig, UniverseTopology
from .tokenomics import (
    TokenomicsEngine,
    TokenomicsConfig,
    TokenWeights,
    TokenScore,
    CognitiveReturnScores,
    SalienceEngine,
    SalienceWeights,
    SalienceItem,
    BudgetAllocation,
    CompressionScores,
    BenchmarkSuite,
    BenchmarkTask,
    BenchmarkScore,
    BenchmarkResult,
    RuntimeMeasurementLoop,
    TaskClass,
    EvaluationCriterion,
    compute_token_value,
    compute_crpt,
    compute_salience_score,
    compute_compression_efficiency,
    compute_compression_ratio,
)

__all__ = [
    "PhysicsEngine",
    "Force",
    "Field",
    "Particle",
    "PhysicsConstants",
    "GeometryEngine",
    "MetricTensor",
    "Manifold",
    "Geodesic",
    "CurvatureTensor",
    "MiniVerse",
    "MiniVerseConfig",
    "UniverseTopology",
    "TokenomicsEngine",
    "TokenomicsConfig",
    "TokenWeights",
    "TokenScore",
    "CognitiveReturnScores",
    "SalienceEngine",
    "SalienceWeights",
    "SalienceItem",
    "BudgetAllocation",
    "CompressionScores",
    "BenchmarkSuite",
    "BenchmarkTask",
    "BenchmarkScore",
    "BenchmarkResult",
    "RuntimeMeasurementLoop",
    "TaskClass",
    "EvaluationCriterion",
    "compute_token_value",
    "compute_crpt",
    "compute_salience_score",
    "compute_compression_efficiency",
    "compute_compression_ratio",
]
