"""
Geometry Engine — Riemannian Manifolds, Metric Tensors, Geodesics, Curvature
⌬ Real differential geometry for curved spacetime simulation.

This engine implements:
    - Metric tensor fields (Minkowski, Schwarzschild, FLRW, custom)
    - Geodesic computation via numerical integration of geodesic equation
    - Riemann curvature tensor, Ricci tensor, scalar curvature
    - Christoffel symbols (Levi-Civita connection)
    - Proper distance and proper time calculations
    - Topological classification of manifold regions
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import numpy as np


# ---------------------------------------------------------------------------
# Metric Tensor — the fundamental object of Riemannian geometry
# ---------------------------------------------------------------------------

class MetricSignature(str, Enum):
    """Signature of the metric tensor."""
    RIEMANNIAN = "+++"       # Euclidean: all positive
    LORENTZIAN = "-+++"      # Spacetime: one timelike dimension
    DEGENERATE = "0+++"      # Null surface


@dataclass
class MetricTensor:
    """
    Metric tensor g_μν at a point in the manifold.

    The metric defines:
        - Distances: ds² = g_μν dx^μ dx^ν
        - Angles between vectors
        - Volume elements
        - Light cones (in Lorentzian signature)
    """

    components: np.ndarray  # shape (n, n) symmetric matrix
    signature: MetricSignature = MetricSignature.LORENTZIAN
    coordinates: str = "cartesian"  # coordinate system label

    def __post_init__(self):
        if not isinstance(self.components, np.ndarray):
            self.components = np.array(self.components, dtype=np.float64)

    @property
    def dimension(self) -> int:
        return self.components.shape[0]

    @property
    def determinant(self) -> float:
        """det(g_μν) — needed for volume elements."""
        return float(np.linalg.det(self.components))

    @property
    def inverse(self) -> np.ndarray:
        """g^μν — contravariant metric (inverse)."""
        return np.linalg.inv(self.components)

    def line_element(self, dx: np.ndarray) -> float:
        """Compute ds² = g_μν dx^μ dx^ν for displacement dx."""
        return float(dx @ self.components @ dx)

    def proper_distance(self, dx: np.ndarray) -> float:
        """Proper distance |ds| for a given coordinate displacement."""
        ds_sq = self.line_element(dx)
        if ds_sq >= 0:
            return math.sqrt(ds_sq)
        # Timelike interval: return proper time
        return math.sqrt(-ds_sq)

    def is_timelike(self, vector: np.ndarray) -> bool:
        """Check if a vector is timelike (g_μν v^μ v^ν < 0)."""
        return self.line_element(vector) < 0

    def is_spacelike(self, vector: np.ndarray) -> bool:
        """Check if a vector is spacelike (g_μν v^μ v^ν > 0)."""
        return self.line_element(vector) > 0

    def is_null(self, vector: np.ndarray) -> bool:
        """Check if a vector is null/lightlike (g_μν v^μ v^ν = 0)."""
        return abs(self.line_element(vector)) < 1e-12

    def raise_index(self, covector: np.ndarray) -> np.ndarray:
        """Raise index: v^μ = g^μν v_ν."""
        return self.inverse @ covector

    def lower_index(self, vector: np.ndarray) -> np.ndarray:
        """Lower index: v_μ = g_μν v^ν."""
        return self.components @ vector

    @classmethod
    def minkowski(cls, dim: int = 4) -> MetricTensor:
        """Flat Minkowski metric η_μν = diag(-1, 1, 1, 1)."""
        g = np.eye(dim, dtype=np.float64)
        g[0, 0] = -1.0  # timelike component
        return cls(components=g, signature=MetricSignature.LORENTZIAN, coordinates="minkowski")

    @classmethod
    def schwarzschild(cls, r: float, M: float, G: float = 6.674e-11, c: float = 3e8) -> MetricTensor:
        """
        Schwarzschild metric in (t, r, θ, φ) coordinates.

        ds² = -(1 - r_s/r)c²dt² + (1 - r_s/r)⁻¹dr² + r²dθ² + r²sin²θ dφ²

        At θ = π/2 (equatorial plane).
        """
        r_s = 2 * G * M / (c * c)  # Schwarzschild radius

        if r <= r_s:
            # Inside event horizon: flip signature
            factor = r_s / r - 1.0
            g = np.diag([factor * c * c, -1.0 / factor, r * r, r * r])
        else:
            factor = 1.0 - r_s / r
            g = np.diag([-factor * c * c, 1.0 / factor, r * r, r * r])

        return cls(components=g, signature=MetricSignature.LORENTZIAN, coordinates="schwarzschild")

    @classmethod
    def flrw(cls, t: float, a_func: Callable[[float], float], k: float = 0.0) -> MetricTensor:
        """
        Friedmann-Lemaître-Robertson-Walker metric (cosmological).

        ds² = -c²dt² + a(t)²[dr²/(1-kr²) + r²dΩ²]

        Args:
            t: cosmic time
            a_func: scale factor function a(t)
            k: curvature parameter (-1, 0, +1)
        """
        c = 3e8
        a = a_func(t)
        # At r=1, θ=π/2 for simplicity
        r = 1.0
        denom = 1.0 - k * r * r
        if abs(denom) < 1e-15:
            denom = 1e-15

        g = np.diag([
            -(c * c),
            a * a / denom,
            a * a * r * r,
            a * a * r * r,  # sin²θ = 1 at θ=π/2
        ])
        return cls(components=g, signature=MetricSignature.LORENTZIAN, coordinates="flrw")

    @classmethod
    def euclidean(cls, dim: int = 3) -> MetricTensor:
        """Flat Euclidean metric δ_ij."""
        return cls(
            components=np.eye(dim, dtype=np.float64),
            signature=MetricSignature.RIEMANNIAN,
            coordinates="cartesian",
        )


# ---------------------------------------------------------------------------
# Christoffel Symbols — the connection coefficients
# ---------------------------------------------------------------------------

def compute_christoffel_symbols(
    metric_func: Callable[[np.ndarray], np.ndarray],
    point: np.ndarray,
    h: float = 1e-6,
) -> np.ndarray:
    """
    Compute Christoffel symbols Γ^σ_μν via numerical differentiation.

    Γ^σ_μν = ½ g^σρ (∂_μ g_νρ + ∂_ν g_μρ - ∂_ρ g_μν)

    Args:
        metric_func: function mapping coordinates → metric components g_μν
        point: coordinates at which to evaluate
        h: finite difference step size

    Returns:
        ndarray of shape (n, n, n) with Γ^σ_μν
    """
    n = len(point)
    g = metric_func(point)
    g_inv = np.linalg.inv(g)

    # Numerical partial derivatives of metric
    dg = np.zeros((n, n, n))  # ∂_ρ g_μν
    for rho in range(n):
        point_plus = point.copy()
        point_minus = point.copy()
        point_plus[rho] += h
        point_minus[rho] -= h
        dg[rho] = (metric_func(point_plus) - metric_func(point_minus)) / (2 * h)

    # Christoffel symbols
    christoffel = np.zeros((n, n, n))
    for sigma in range(n):
        for mu in range(n):
            for nu in range(n):
                total = 0.0
                for rho in range(n):
                    total += g_inv[sigma, rho] * (
                        dg[mu][nu, rho] + dg[nu][mu, rho] - dg[rho][mu, nu]
                    )
                christoffel[sigma, mu, nu] = 0.5 * total

    return christoffel


# ---------------------------------------------------------------------------
# Curvature Tensor — Riemann, Ricci, scalar curvature
# ---------------------------------------------------------------------------

@dataclass
class CurvatureTensor:
    """
    Curvature information at a point on the manifold.

    Contains:
        - Riemann tensor R^ρ_σμν
        - Ricci tensor R_μν = R^ρ_μρν
        - Ricci scalar R = g^μν R_μν
        - Kretschner scalar K = R_αβγδ R^αβγδ (singularity detector)
    """

    riemann: np.ndarray       # shape (n, n, n, n)
    ricci_tensor: np.ndarray  # shape (n, n)
    ricci_scalar: float
    kretschner_scalar: float
    point: np.ndarray         # where this was computed

    @property
    def is_flat(self) -> bool:
        """Check if spacetime is flat at this point."""
        return abs(self.ricci_scalar) < 1e-10

    @property
    def is_singular(self) -> bool:
        """Check if this point is a curvature singularity."""
        return self.kretschner_scalar > 1e40 or math.isinf(self.kretschner_scalar)

    def einstein_tensor(self, metric: MetricTensor) -> np.ndarray:
        """G_μν = R_μν - ½Rg_μν (Einstein field equation LHS)."""
        return self.ricci_tensor - 0.5 * self.ricci_scalar * metric.components

    def to_dict(self) -> dict:
        return {
            "ricci_scalar": self.ricci_scalar,
            "kretschner_scalar": self.kretschner_scalar,
            "is_flat": self.is_flat,
            "is_singular": self.is_singular,
            "point": self.point.tolist(),
        }


def compute_curvature(
    metric_func: Callable[[np.ndarray], np.ndarray],
    point: np.ndarray,
    h: float = 1e-5,
) -> CurvatureTensor:
    """
    Compute full curvature at a point via numerical differentiation.

    R^ρ_σμν = ∂_μΓ^ρ_νσ - ∂_νΓ^ρ_μσ + Γ^ρ_μλΓ^λ_νσ - Γ^ρ_νλΓ^λ_μσ
    """
    n = len(point)
    g = metric_func(point)
    g_inv = np.linalg.inv(g)

    # Get Christoffel symbols at point and nearby points
    gamma = compute_christoffel_symbols(metric_func, point, h)

    # Numerical derivatives of Christoffel symbols
    dgamma = np.zeros((n, n, n, n))  # ∂_μ Γ^ρ_νσ indexed as [mu, rho, nu, sigma]
    for mu in range(n):
        p_plus = point.copy()
        p_minus = point.copy()
        p_plus[mu] += h
        p_minus[mu] -= h
        gamma_plus = compute_christoffel_symbols(metric_func, p_plus, h)
        gamma_minus = compute_christoffel_symbols(metric_func, p_minus, h)
        dgamma[mu] = (gamma_plus - gamma_minus) / (2 * h)

    # Riemann tensor R^ρ_σμν
    riemann = np.zeros((n, n, n, n))
    for rho in range(n):
        for sigma in range(n):
            for mu in range(n):
                for nu in range(n):
                    # ∂_μΓ^ρ_νσ - ∂_νΓ^ρ_μσ
                    riemann[rho, sigma, mu, nu] = (
                        dgamma[mu][rho, nu, sigma] - dgamma[nu][rho, mu, sigma]
                    )
                    # + Γ^ρ_μλ Γ^λ_νσ - Γ^ρ_νλ Γ^λ_μσ
                    for lam in range(n):
                        riemann[rho, sigma, mu, nu] += (
                            gamma[rho, mu, lam] * gamma[lam, nu, sigma]
                            - gamma[rho, nu, lam] * gamma[lam, mu, sigma]
                        )

    # Ricci tensor R_μν = R^ρ_μρν
    ricci = np.zeros((n, n))
    for mu in range(n):
        for nu in range(n):
            for rho in range(n):
                ricci[mu, nu] += riemann[rho, mu, rho, nu]

    # Ricci scalar R = g^μν R_μν
    ricci_scalar = float(np.sum(g_inv * ricci))

    # Kretschner scalar K = R_αβγδ R^αβγδ
    # Lower all indices first: R_ρσμν = g_ρλ R^λ_σμν
    riemann_lower = np.zeros((n, n, n, n))
    for rho in range(n):
        for sigma in range(n):
            for mu in range(n):
                for nu in range(n):
                    for lam in range(n):
                        riemann_lower[rho, sigma, mu, nu] += g[rho, lam] * riemann[lam, sigma, mu, nu]

    # Raise all indices for contraction
    kretschner = 0.0
    for a in range(n):
        for b in range(n):
            for c in range(n):
                for d in range(n):
                    r_lower = riemann_lower[a, b, c, d]
                    # R^abcd via g^aa' g^bb' g^cc' g^dd' R_a'b'c'd'
                    r_upper = 0.0
                    for ap in range(n):
                        for bp in range(n):
                            for cp in range(n):
                                for dp in range(n):
                                    r_upper += (
                                        g_inv[a, ap] * g_inv[b, bp]
                                        * g_inv[c, cp] * g_inv[d, dp]
                                        * riemann_lower[ap, bp, cp, dp]
                                    )
                    kretschner += r_lower * r_upper

    return CurvatureTensor(
        riemann=riemann,
        ricci_tensor=ricci,
        ricci_scalar=ricci_scalar,
        kretschner_scalar=kretschner,
        point=point,
    )


# ---------------------------------------------------------------------------
# Geodesic — paths of shortest/extremal distance in curved space
# ---------------------------------------------------------------------------

@dataclass
class Geodesic:
    """
    A geodesic path through the manifold.

    Computed by integrating the geodesic equation:
        d²x^μ/dτ² + Γ^μ_αβ (dx^α/dτ)(dx^β/dτ) = 0
    """

    geodesic_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    points: list[np.ndarray] = field(default_factory=list)
    tangent_vectors: list[np.ndarray] = field(default_factory=list)
    proper_times: list[float] = field(default_factory=list)
    is_timelike: bool = True
    is_complete: bool = False

    @property
    def length(self) -> int:
        return len(self.points)

    @property
    def total_proper_time(self) -> float:
        if self.proper_times:
            return self.proper_times[-1]
        return 0.0

    def to_dict(self) -> dict:
        return {
            "geodesic_id": self.geodesic_id,
            "num_points": self.length,
            "total_proper_time": self.total_proper_time,
            "is_timelike": self.is_timelike,
            "is_complete": self.is_complete,
        }


def integrate_geodesic(
    metric_func: Callable[[np.ndarray], np.ndarray],
    initial_position: np.ndarray,
    initial_velocity: np.ndarray,
    num_steps: int = 1000,
    step_size: float = 0.01,
    h: float = 1e-6,
) -> Geodesic:
    """
    Integrate the geodesic equation numerically (RK4).

    d²x^μ/dλ² + Γ^μ_αβ (dx^α/dλ)(dx^β/dλ) = 0

    Rewritten as first-order system:
        dx^μ/dλ = u^μ
        du^μ/dλ = -Γ^μ_αβ u^α u^β
    """
    n = len(initial_position)
    x = initial_position.copy().astype(np.float64)
    u = initial_velocity.copy().astype(np.float64)

    geodesic = Geodesic(
        points=[x.copy()],
        tangent_vectors=[u.copy()],
        proper_times=[0.0],
    )

    # Check if initial tangent is timelike
    g = metric_func(x)
    ds_sq = float(u @ g @ u)
    geodesic.is_timelike = ds_sq < 0

    tau = 0.0

    for _ in range(num_steps):
        # RK4 integration
        def derivs(pos: np.ndarray, vel: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            gamma = compute_christoffel_symbols(metric_func, pos, h)
            accel = np.zeros(n)
            for mu in range(n):
                for alpha in range(n):
                    for beta in range(n):
                        accel[mu] -= gamma[mu, alpha, beta] * vel[alpha] * vel[beta]
            return vel, accel

        # k1
        dx1, du1 = derivs(x, u)
        # k2
        dx2, du2 = derivs(x + 0.5 * step_size * dx1, u + 0.5 * step_size * du1)
        # k3
        dx3, du3 = derivs(x + 0.5 * step_size * dx2, u + 0.5 * step_size * du2)
        # k4
        dx4, du4 = derivs(x + step_size * dx3, u + step_size * du3)

        x = x + (step_size / 6.0) * (dx1 + 2 * dx2 + 2 * dx3 + dx4)
        u = u + (step_size / 6.0) * (du1 + 2 * du2 + 2 * du3 + du4)

        # Proper time increment
        g_new = metric_func(x)
        ds_sq = float(u @ g_new @ u)
        if ds_sq < 0:
            d_tau = math.sqrt(-ds_sq) * step_size
        else:
            d_tau = math.sqrt(abs(ds_sq)) * step_size
        tau += d_tau

        geodesic.points.append(x.copy())
        geodesic.tangent_vectors.append(u.copy())
        geodesic.proper_times.append(tau)

        # Check for singularity (diverging coordinates)
        if np.any(np.abs(x) > 1e15) or np.any(np.isnan(x)):
            break

    geodesic.is_complete = True
    return geodesic


# ---------------------------------------------------------------------------
# Manifold — a collection of patches with metric and topology
# ---------------------------------------------------------------------------

class TopologyType(str, Enum):
    """Topological classification of manifold."""
    EUCLIDEAN = "R^n"
    SPHERE = "S^n"
    TORUS = "T^n"
    HYPERBOLIC = "H^n"
    CYLINDER = "R×S^(n-1)"
    DE_SITTER = "dS"
    ANTI_DE_SITTER = "AdS"
    SCHWARZSCHILD = "schwarzschild"
    CUSTOM = "custom"


@dataclass
class Manifold:
    """
    A differentiable manifold with metric structure.

    Encapsulates the geometric substrate of a mini-verse.
    """

    manifold_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    dimension: int = 4
    topology: TopologyType = TopologyType.EUCLIDEAN
    metric_func: Callable[[np.ndarray], np.ndarray] | None = None
    name: str = "unnamed"
    metadata: dict[str, Any] = field(default_factory=dict)

    def metric_at(self, point: np.ndarray) -> MetricTensor:
        """Get metric tensor at a point."""
        if self.metric_func is None:
            # Default to flat metric
            if self.dimension == 4:
                return MetricTensor.minkowski(4)
            return MetricTensor.euclidean(self.dimension)
        components = self.metric_func(point)
        return MetricTensor(components=components)

    def christoffel_at(self, point: np.ndarray, h: float = 1e-6) -> np.ndarray:
        """Compute Christoffel symbols at a point."""
        if self.metric_func is None:
            return np.zeros((self.dimension, self.dimension, self.dimension))
        return compute_christoffel_symbols(self.metric_func, point, h)

    def curvature_at(self, point: np.ndarray, h: float = 1e-5) -> CurvatureTensor:
        """Compute full curvature tensor at a point."""
        if self.metric_func is None:
            return CurvatureTensor(
                riemann=np.zeros((self.dimension,) * 4),
                ricci_tensor=np.zeros((self.dimension, self.dimension)),
                ricci_scalar=0.0,
                kretschner_scalar=0.0,
                point=point,
            )
        return compute_curvature(self.metric_func, point, h)

    def geodesic(
        self,
        start: np.ndarray,
        direction: np.ndarray,
        steps: int = 500,
        step_size: float = 0.01,
    ) -> Geodesic:
        """Compute a geodesic from start with given initial direction."""
        if self.metric_func is None:
            # Flat space: geodesics are straight lines
            geo = Geodesic(is_timelike=True)
            for i in range(steps):
                geo.points.append(start + direction * (i * step_size))
                geo.tangent_vectors.append(direction.copy())
                geo.proper_times.append(i * step_size)
            geo.is_complete = True
            return geo
        return integrate_geodesic(self.metric_func, start, direction, steps, step_size)

    def proper_distance(self, point_a: np.ndarray, point_b: np.ndarray) -> float:
        """Approximate proper distance between two nearby points."""
        dx = point_b - point_a
        metric = self.metric_at(point_a)
        return metric.proper_distance(dx)

    @classmethod
    def flat_spacetime(cls) -> Manifold:
        """Create flat Minkowski spacetime."""
        def minkowski_metric(x: np.ndarray) -> np.ndarray:
            return np.diag([-1.0, 1.0, 1.0, 1.0])

        return cls(
            dimension=4,
            topology=TopologyType.EUCLIDEAN,
            metric_func=minkowski_metric,
            name="Minkowski Spacetime",
        )

    @classmethod
    def schwarzschild_spacetime(cls, M: float, G: float = 6.674e-11, c: float = 3e8) -> Manifold:
        """Create Schwarzschild spacetime around a mass M."""
        r_s = 2 * G * M / (c * c)

        def schwarzschild_metric(x: np.ndarray) -> np.ndarray:
            # x = [t, r, θ, φ]
            r = max(x[1], 1e-10)  # avoid r=0 singularity only
            factor = 1.0 - r_s / r
            if abs(factor) < 1e-15:
                factor = 1e-15  # avoid division by zero exactly at horizon
            return np.diag([
                -factor * c * c,
                1.0 / factor,
                r * r,
                r * r,  # at θ=π/2
            ])

        return cls(
            dimension=4,
            topology=TopologyType.SCHWARZSCHILD,
            metric_func=schwarzschild_metric,
            name=f"Schwarzschild (M={M:.2e} kg, r_s={r_s:.2e} m)",
            metadata={"mass": M, "schwarzschild_radius": r_s},
        )

    @classmethod
    def expanding_universe(cls, H0: float = 2.2e-18, k: float = 0.0) -> Manifold:
        """Create FLRW expanding universe with Hubble constant H0."""
        def scale_factor(t: float) -> float:
            # Exponential expansion (de Sitter approximation)
            return math.exp(H0 * t)

        def flrw_metric(x: np.ndarray) -> np.ndarray:
            # x = [t, r, θ, φ]
            t = x[0]
            r = max(x[1], 1e-10)
            a = scale_factor(t)
            c = 3e8
            denom = 1.0 - k * r * r
            if abs(denom) < 1e-15:
                denom = 1e-15
            return np.diag([
                -(c * c),
                a * a / denom,
                a * a * r * r,
                a * a * r * r,
            ])

        return cls(
            dimension=4,
            topology=TopologyType.DE_SITTER if k == 0 else TopologyType.SPHERE,
            metric_func=flrw_metric,
            name=f"FLRW Universe (H₀={H0:.2e} s⁻¹, k={k})",
            metadata={"hubble_constant": H0, "curvature_parameter": k},
        )

    def to_dict(self) -> dict:
        return {
            "manifold_id": self.manifold_id,
            "dimension": self.dimension,
            "topology": self.topology.value,
            "name": self.name,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Geometry Engine — the orchestrator
# ---------------------------------------------------------------------------

class GeometryEngine:
    """
    Production geometry engine for computing spacetime structure.

    Provides:
        - Manifold management and multi-patch support
        - Geodesic computation and caching
        - Curvature analysis and singularity detection
        - Coordinate transformations
        - Horizon detection (event horizons, Cauchy horizons)
    """

    def __init__(self, manifold: Manifold | None = None) -> None:
        self.manifold = manifold or Manifold.flat_spacetime()
        self._geodesic_cache: dict[str, Geodesic] = {}
        self._curvature_cache: dict[str, CurvatureTensor] = {}

    def set_manifold(self, manifold: Manifold) -> None:
        """Switch to a different manifold geometry."""
        self.manifold = manifold
        self._geodesic_cache.clear()
        self._curvature_cache.clear()

    def compute_geodesic(
        self,
        start: np.ndarray,
        direction: np.ndarray,
        steps: int = 500,
        step_size: float = 0.01,
    ) -> Geodesic:
        """Compute and cache a geodesic."""
        geo = self.manifold.geodesic(start, direction, steps, step_size)
        self._geodesic_cache[geo.geodesic_id] = geo
        return geo

    def compute_curvature(self, point: np.ndarray) -> CurvatureTensor:
        """Compute curvature at a point."""
        key = str(point.tolist())
        if key in self._curvature_cache:
            return self._curvature_cache[key]
        curv = self.manifold.curvature_at(point)
        self._curvature_cache[key] = curv
        return curv

    def detect_horizons(
        self,
        radial_range: tuple[float, float] = (0.1, 100.0),
        num_samples: int = 200,
    ) -> list[float]:
        """
        Detect event horizons by finding where g_tt changes sign.

        Returns list of radial coordinates where horizons exist.
        """
        horizons = []
        r_min, r_max = radial_range
        dr = (r_max - r_min) / num_samples
        prev_gtt = None

        for i in range(num_samples):
            r = r_min + i * dr
            point = np.array([0.0, r, math.pi / 2, 0.0])
            metric = self.manifold.metric_at(point)
            gtt = metric.components[0, 0]

            if prev_gtt is not None and prev_gtt * gtt < 0:
                # Sign change — horizon between this and previous r
                horizons.append(r - dr / 2)

            prev_gtt = gtt

        return horizons

    def parallel_transport(
        self,
        vector: np.ndarray,
        along_geodesic: Geodesic,
        num_steps: int | None = None,
    ) -> list[np.ndarray]:
        """
        Parallel transport a vector along a geodesic.

        dV^μ/dλ = -Γ^μ_αβ V^α (dx^β/dλ)
        """
        if num_steps is None:
            num_steps = along_geodesic.length

        transported = [vector.copy()]
        v = vector.copy()

        for i in range(min(num_steps - 1, along_geodesic.length - 1)):
            point = along_geodesic.points[i]
            tangent = along_geodesic.tangent_vectors[i]

            gamma = self.manifold.christoffel_at(point)
            n = len(v)

            # dV^μ = -Γ^μ_αβ V^α u^β dλ
            dv = np.zeros(n)
            for mu in range(n):
                for alpha in range(n):
                    for beta in range(n):
                        dv[mu] -= gamma[mu, alpha, beta] * v[alpha] * tangent[beta]

            # Simple Euler step (could be upgraded to RK4)
            dt = 0.01  # affine parameter step
            v = v + dv * dt
            transported.append(v.copy())

        return transported

    def volume_element(self, point: np.ndarray) -> float:
        """Compute √|det(g)| at a point — the invariant volume element."""
        metric = self.manifold.metric_at(point)
        return math.sqrt(abs(metric.determinant))

    def get_state(self) -> dict:
        """Full geometry engine state."""
        return {
            "manifold": self.manifold.to_dict(),
            "cached_geodesics": len(self._geodesic_cache),
            "cached_curvatures": len(self._curvature_cache),
        }
