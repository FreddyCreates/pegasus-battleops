"""
Spatium Computationis — Engine Suite
⌬ Production-grade physics, geometry, and mini-verse simulation engines.

Engines:
    - PhysicsEngine: Newtonian + relativistic mechanics, field theory, conservation
    - GeometryEngine: Riemannian manifolds, metric tensors, geodesics, curvature
    - MiniVerse: Self-contained universe with configurable physical constants
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
]
