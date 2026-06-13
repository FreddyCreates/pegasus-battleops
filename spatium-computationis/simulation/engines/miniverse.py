"""
Mini-Verse Engine — Self-Contained Universes with Configurable Physics
⌬ Each mini-verse is an isolated universe with its own physical constants,
  geometry, topology, and particle populations.

This engine implements:
    - Universe creation with configurable fundamental constants
    - Multiple topology options (flat, spherical, toroidal, hyperbolic)
    - Time evolution with proper physics integration
    - Inter-verse communication channels (wormholes, entanglement)
    - Thermodynamic arrow of time and entropy tracking
    - Cosmological evolution (expansion, contraction, bounce)
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import numpy as np

from .physics import Force, Particle, PhysicsConstants, PhysicsEngine, Vec3
from .geometry import (
    CurvatureTensor,
    GeometryEngine,
    Geodesic,
    Manifold,
    MetricTensor,
    TopologyType,
)


# ---------------------------------------------------------------------------
# Universe Topology — shape of the spatial dimensions
# ---------------------------------------------------------------------------

class UniverseTopology(str, Enum):
    """Spatial topology of a mini-verse."""
    FLAT_INFINITE = "flat_infinite"         # R³ — standard flat infinite
    FLAT_PERIODIC = "flat_periodic"         # T³ — flat torus (periodic BCs)
    SPHERICAL = "spherical"                 # S³ — closed, positive curvature
    HYPERBOLIC = "hyperbolic"               # H³ — open, negative curvature
    CYLINDRICAL = "cylindrical"             # R×S² — one infinite + compact
    DE_SITTER = "de_sitter"                 # Exponential expansion
    ANTI_DE_SITTER = "anti_de_sitter"       # Negative cosmological constant


# ---------------------------------------------------------------------------
# Mini-Verse Configuration
# ---------------------------------------------------------------------------

@dataclass
class MiniVerseConfig:
    """
    Configuration for creating a new mini-verse.

    Every parameter maps to a real physical or cosmological quantity.
    """

    # Identity
    name: str = "Universe-α"
    seed: int = 42

    # Topology and geometry
    topology: UniverseTopology = UniverseTopology.FLAT_INFINITE
    spatial_dimensions: int = 3
    total_dimensions: int = 4  # including time

    # Physical constants (ratios relative to our universe)
    constants: PhysicsConstants = field(default_factory=PhysicsConstants)

    # Cosmological parameters
    hubble_constant: float = 2.2e-18        # H₀ in s⁻¹ (≈67.4 km/s/Mpc)
    cosmological_constant: float = 1.1e-52  # Λ in m⁻² (dark energy)
    matter_density: float = 9.9e-27         # ρ_m in kg/m³
    radiation_density: float = 4.6e-31      # ρ_r in kg/m³
    dark_energy_fraction: float = 0.683     # Ω_Λ
    matter_fraction: float = 0.317          # Ω_m
    curvature_parameter: float = 0.0        # k: -1, 0, +1

    # Bounds
    spatial_extent: float = 1e26            # meters (observable universe ~4.4e26 m)
    age: float = 0.0                        # initial age in seconds
    max_age: float = 1e18                   # ~31.7 billion years

    # Simulation parameters
    time_scale: float = 1.0                 # simulation time multiplier
    particle_limit: int = 10000

    def validate(self) -> list[str]:
        """Validate configuration, return list of issues."""
        issues = []
        if self.constants.G <= 0:
            issues.append("G must be positive")
        if self.constants.c <= 0:
            issues.append("c must be positive")
        if self.spatial_dimensions < 1:
            issues.append("Need at least 1 spatial dimension")
        if self.total_dimensions <= self.spatial_dimensions:
            issues.append("Total dimensions must exceed spatial dimensions")
        if self.matter_fraction + self.dark_energy_fraction > 1.01:
            issues.append("Density fractions exceed unity (non-physical unless k≠0)")
        return issues


# ---------------------------------------------------------------------------
# Cosmological Evolution
# ---------------------------------------------------------------------------

class CosmologicalPhase(str, Enum):
    """Phase of cosmological evolution."""
    RADIATION_DOMINATED = "radiation_dominated"
    MATTER_DOMINATED = "matter_dominated"
    DARK_ENERGY_DOMINATED = "dark_energy_dominated"
    CONTRACTING = "contracting"
    BOUNCING = "bouncing"
    STATIC = "static"


@dataclass
class CosmologicalState:
    """Current cosmological state of the mini-verse."""

    scale_factor: float = 1.0           # a(t) — dimensionless
    hubble_parameter: float = 2.2e-18   # H(t) = ȧ/a
    deceleration_parameter: float = 0.0  # q = -aä/ȧ²
    age: float = 0.0                     # cosmic time in seconds
    temperature: float = 2.725           # CMB temperature in K
    phase: CosmologicalPhase = CosmologicalPhase.DARK_ENERGY_DOMINATED
    entropy: float = 0.0

    @property
    def expansion_rate(self) -> float:
        """ȧ = H·a — rate of scale factor change."""
        return self.hubble_parameter * self.scale_factor

    @property
    def is_expanding(self) -> bool:
        return self.hubble_parameter > 0

    @property
    def is_accelerating(self) -> bool:
        return self.deceleration_parameter < 0

    def to_dict(self) -> dict:
        return {
            "scale_factor": self.scale_factor,
            "hubble_parameter": self.hubble_parameter,
            "deceleration_parameter": self.deceleration_parameter,
            "age": self.age,
            "temperature": self.temperature,
            "phase": self.phase.value,
            "entropy": self.entropy,
            "is_expanding": self.is_expanding,
            "is_accelerating": self.is_accelerating,
        }


# ---------------------------------------------------------------------------
# Mini-Verse — the self-contained universe
# ---------------------------------------------------------------------------

class MiniVerse:
    """
    A self-contained universe with its own physics, geometry, and evolution.

    Each MiniVerse encapsulates:
        - Its own physical constants (G, c, ℏ, etc.)
        - Spacetime geometry (metric, curvature, topology)
        - Particle population with full N-body dynamics
        - Cosmological expansion/contraction
        - Thermodynamic entropy evolution
        - Conservation law tracking

    Mini-verses can be connected via wormholes or entanglement channels
    to exchange particles/information with other mini-verses.
    """

    def __init__(self, config: MiniVerseConfig | None = None) -> None:
        self.config = config or MiniVerseConfig()
        self.verse_id = str(uuid.uuid4())[:12]

        # Validate configuration
        issues = self.config.validate()
        if issues:
            raise ValueError(f"Invalid MiniVerse config: {', '.join(issues)}")

        # Initialize engines
        self.physics = PhysicsEngine(
            constants=self.config.constants,
            enable_relativity=True,
            enable_collisions=True,
        )

        # Set up geometry based on topology
        self.geometry = GeometryEngine(self._create_manifold())

        # Cosmological state
        self.cosmo = CosmologicalState(
            hubble_parameter=self.config.hubble_constant,
            age=self.config.age,
        )

        # Internal state
        self._tick = 0
        self._wall_time_start = time.time()
        self._events: list[dict] = []
        self._connections: dict[str, MiniVerseConnection] = {}

        # Thermodynamics
        self._entropy_production_rate = 0.0

    def _create_manifold(self) -> Manifold:
        """Create spacetime manifold matching topology config."""
        topology = self.config.topology
        G = self.config.constants.G
        c = self.config.constants.c

        if topology == UniverseTopology.FLAT_INFINITE:
            return Manifold.flat_spacetime()

        elif topology == UniverseTopology.DE_SITTER:
            return Manifold.expanding_universe(
                H0=self.config.hubble_constant,
                k=0,
            )

        elif topology == UniverseTopology.SPHERICAL:
            return Manifold.expanding_universe(
                H0=self.config.hubble_constant,
                k=1,
            )

        elif topology == UniverseTopology.HYPERBOLIC:
            return Manifold.expanding_universe(
                H0=self.config.hubble_constant,
                k=-1,
            )

        elif topology == UniverseTopology.FLAT_PERIODIC:
            # Flat torus: same metric as flat, but with periodic identification
            L = self.config.spatial_extent

            def torus_metric(x: np.ndarray) -> np.ndarray:
                return np.diag([-c * c, 1.0, 1.0, 1.0])

            m = Manifold(
                dimension=4,
                topology=TopologyType.TORUS,
                metric_func=torus_metric,
                name=f"T³ Torus (L={L:.2e} m)",
                metadata={"period": L},
            )
            return m

        elif topology == UniverseTopology.ANTI_DE_SITTER:
            # AdS: negative cosmological constant
            Lambda = -abs(self.config.cosmological_constant)
            L_ads = math.sqrt(-3.0 / Lambda) if Lambda < 0 else 1e26

            def ads_metric(x: np.ndarray) -> np.ndarray:
                r = max(x[1], 1e-10)
                factor = 1.0 + (r / L_ads) ** 2
                return np.diag([
                    -factor * c * c,
                    1.0 / factor,
                    r * r,
                    r * r,
                ])

            return Manifold(
                dimension=4,
                topology=TopologyType.ANTI_DE_SITTER,
                metric_func=ads_metric,
                name=f"Anti-de Sitter (L_AdS={L_ads:.2e} m)",
                metadata={"ads_radius": L_ads},
            )

        # Default fallback
        return Manifold.flat_spacetime()

    # -----------------------------------------------------------------------
    # Time evolution
    # -----------------------------------------------------------------------

    def step(self, dt: float) -> dict[str, Any]:
        """
        Evolve the mini-verse by dt seconds.

        Performs:
            1. Cosmological scale factor evolution (Friedmann equation)
            2. Physics integration (particles, forces)
            3. Entropy production
            4. Event logging
        """
        self._tick += 1
        scaled_dt = dt * self.config.time_scale

        # 1. Cosmological evolution
        self._evolve_cosmology(scaled_dt)

        # 2. Physics step
        physics_diag = self.physics.step(scaled_dt)

        # 3. Apply periodic boundary conditions if topology requires
        if self.config.topology == UniverseTopology.FLAT_PERIODIC:
            self._apply_periodic_boundaries()

        # 4. Entropy evolution (second law of thermodynamics)
        self._evolve_entropy(scaled_dt, physics_diag)

        # 5. Build diagnostics
        diagnostics = {
            "verse_id": self.verse_id,
            "tick": self._tick,
            "cosmic_age": self.cosmo.age,
            "scale_factor": self.cosmo.scale_factor,
            "hubble_parameter": self.cosmo.hubble_parameter,
            "cosmological_phase": self.cosmo.phase.value,
            "temperature": self.cosmo.temperature,
            "entropy": self.cosmo.entropy,
            "physics": physics_diag,
            "particle_count": len(self.physics.particles),
        }

        self._log_event("step", diagnostics)
        return diagnostics

    def _evolve_cosmology(self, dt: float) -> None:
        """
        Evolve scale factor using Friedmann equations.

        H² = (8πG/3)ρ - kc²/a² + Λc²/3
        ä/a = -(4πG/3)(ρ + 3p/c²) + Λc²/3
        """
        G = self.config.constants.G
        c = self.config.constants.c
        k = self.config.curvature_parameter
        Lambda = self.config.cosmological_constant

        a = self.cosmo.scale_factor
        H = self.cosmo.hubble_parameter

        # Matter density dilutes as a⁻³, radiation as a⁻⁴
        rho_m = self.config.matter_density / (a ** 3)
        rho_r = self.config.radiation_density / (a ** 4)
        rho_total = rho_m + rho_r

        # Friedmann equation: H² = (8πG/3)ρ - kc²/a² + Λc²/3
        H_squared = (8.0 * math.pi * G / 3.0) * rho_total - k * c * c / (a * a) + Lambda * c * c / 3.0

        if H_squared > 0:
            H_new = math.sqrt(H_squared)
        elif H_squared < 0:
            # Contracting phase
            H_new = -math.sqrt(abs(H_squared))
        else:
            H_new = 0.0

        # Acceleration equation: ä/a = -(4πG/3)(ρ + 3p/c²) + Λc²/3
        # For matter: p=0, for radiation: p=ρc²/3
        pressure = rho_r * c * c / 3.0
        a_double_dot_over_a = (
            -(4.0 * math.pi * G / 3.0) * (rho_total + 3.0 * pressure / (c * c))
            + Lambda * c * c / 3.0
        )

        # Deceleration parameter q = -aä/(ȧ²)
        if abs(H_new) > 1e-30:
            q = -a_double_dot_over_a / (H_new * H_new)
        else:
            q = 0.0

        # Evolve scale factor: ȧ = Ha, so a(t+dt) ≈ a(t) + H·a·dt
        a_new = a + H_new * a * dt
        if a_new < 1e-10:
            a_new = 1e-10  # prevent collapse singularity

        # Temperature scales as T ∝ 1/a
        T_new = 2.725 / a_new  # CMB temperature reference

        # Determine cosmological phase
        if rho_r > rho_m and rho_r > Lambda * c * c / (8 * math.pi * G):
            phase = CosmologicalPhase.RADIATION_DOMINATED
        elif rho_m > Lambda * c * c / (8 * math.pi * G):
            phase = CosmologicalPhase.MATTER_DOMINATED
        elif H_new < 0:
            phase = CosmologicalPhase.CONTRACTING
        else:
            phase = CosmologicalPhase.DARK_ENERGY_DOMINATED

        # Update state
        self.cosmo.scale_factor = a_new
        self.cosmo.hubble_parameter = H_new
        self.cosmo.deceleration_parameter = q
        self.cosmo.age += dt
        self.cosmo.temperature = T_new
        self.cosmo.phase = phase

    def _apply_periodic_boundaries(self) -> None:
        """Wrap particle positions for toroidal topology."""
        L = self.config.spatial_extent
        half_L = L / 2.0

        for p in self.physics.particles.values():
            # Wrap each spatial coordinate to [-L/2, L/2]
            p.position = Vec3(
                ((p.position.x + half_L) % L) - half_L,
                ((p.position.y + half_L) % L) - half_L,
                ((p.position.z + half_L) % L) - half_L,
            )

    def _evolve_entropy(self, dt: float, physics_diag: dict) -> None:
        """
        Track entropy evolution (second law of thermodynamics).

        dS/dt ≥ 0 for isolated systems
        S = k_B ln(Ω) — Boltzmann entropy
        """
        k_B = self.config.constants.k_B
        n = len(self.physics.particles)

        if n == 0:
            return

        # Entropy from particle phase space volume
        # S ≈ Nk_B [5/2 + ln(V/N (4πmE/3Nh²)^(3/2))] — Sackur-Tetrode
        total_ke = physics_diag.get("total_kinetic_energy", 0)
        if total_ke > 0:
            avg_energy = total_ke / n
            # Simplified entropy production from energy dissipation
            energy_error = physics_diag.get("energy_conservation_error", 0)
            ds = k_B * n * energy_error * dt  # irreversible entropy production
            self.cosmo.entropy += abs(ds)

        # Cosmological entropy (horizon entropy grows with expansion)
        if self.cosmo.is_expanding:
            # Bekenstein-Hawking: S_horizon ∝ A/4 ∝ (c/H)²
            if self.cosmo.hubble_parameter > 0:
                horizon_area = 4 * math.pi * (self.config.constants.c / self.cosmo.hubble_parameter) ** 2
                ds_cosmo = k_B * horizon_area * 1e-70 * dt  # normalized
                self.cosmo.entropy += ds_cosmo

    # -----------------------------------------------------------------------
    # Particle creation and manipulation
    # -----------------------------------------------------------------------

    def spawn_particle(
        self,
        mass: float = 1.0,
        charge: float = 0.0,
        position: Vec3 | None = None,
        velocity: Vec3 | None = None,
        **kwargs: Any,
    ) -> Particle:
        """Spawn a new particle in this mini-verse."""
        if len(self.physics.particles) >= self.config.particle_limit:
            raise RuntimeError(f"Particle limit ({self.config.particle_limit}) reached")

        p = Particle(
            mass=mass,
            charge=charge,
            position=position or Vec3.zero(),
            velocity=velocity or Vec3.zero(),
            **kwargs,
        )
        return self.physics.add_particle(p)

    def spawn_particles_random(
        self,
        count: int,
        mass_range: tuple[float, float] = (1.0, 10.0),
        position_range: float = 100.0,
        velocity_range: float = 10.0,
    ) -> list[Particle]:
        """Spawn multiple particles with random initial conditions."""
        import random

        rng = random.Random(self.config.seed + self._tick)
        particles = []

        for _ in range(count):
            p = self.spawn_particle(
                mass=rng.uniform(*mass_range),
                charge=rng.uniform(-1, 1) * self.config.constants.e,
                position=Vec3(
                    rng.uniform(-position_range, position_range),
                    rng.uniform(-position_range, position_range),
                    rng.uniform(-position_range, position_range),
                ),
                velocity=Vec3(
                    rng.uniform(-velocity_range, velocity_range),
                    rng.uniform(-velocity_range, velocity_range),
                    rng.uniform(-velocity_range, velocity_range),
                ),
            )
            particles.append(p)

        return particles

    # -----------------------------------------------------------------------
    # Inter-verse connections
    # -----------------------------------------------------------------------

    def connect_to(
        self,
        other: MiniVerse,
        channel_type: str = "wormhole",
        bandwidth: float = 1.0,
    ) -> MiniVerseConnection:
        """
        Establish a connection to another mini-verse.

        Connection types:
            - wormhole: bidirectional particle transfer
            - entanglement: information-only quantum channel
            - membrane: one-way energy/information leak
        """
        conn = MiniVerseConnection(
            connection_id=str(uuid.uuid4())[:8],
            source_id=self.verse_id,
            target_id=other.verse_id,
            channel_type=channel_type,
            bandwidth=bandwidth,
        )
        self._connections[conn.connection_id] = conn
        other._connections[conn.connection_id] = conn
        return conn

    def transfer_particle(
        self,
        particle_id: str,
        target_verse: MiniVerse,
        connection_id: str,
    ) -> bool:
        """Transfer a particle to another mini-verse via connection."""
        conn = self._connections.get(connection_id)
        if conn is None or conn.channel_type != "wormhole":
            return False

        particle = self.physics.get_particle(particle_id)
        if particle is None:
            return False

        # Remove from source
        self.physics.remove_particle(particle_id)

        # Adjust for different physics constants if needed
        # (mass is invariant, but charge coupling may differ)
        target_verse.physics.add_particle(particle)

        self._log_event("transfer_out", {
            "particle_id": particle_id,
            "target": target_verse.verse_id,
        })
        target_verse._log_event("transfer_in", {
            "particle_id": particle_id,
            "source": self.verse_id,
        })

        return True

    # -----------------------------------------------------------------------
    # Analysis and state
    # -----------------------------------------------------------------------

    def compute_geodesic(
        self,
        start: np.ndarray,
        direction: np.ndarray,
        steps: int = 500,
    ) -> Geodesic:
        """Compute a geodesic in this mini-verse's spacetime."""
        return self.geometry.compute_geodesic(start, direction, steps)

    def curvature_at(self, point: np.ndarray) -> CurvatureTensor:
        """Compute spacetime curvature at a point."""
        return self.geometry.compute_curvature(point)

    def get_state(self) -> dict:
        """Complete mini-verse state snapshot."""
        return {
            "verse_id": self.verse_id,
            "name": self.config.name,
            "tick": self._tick,
            "topology": self.config.topology.value,
            "dimensions": self.config.total_dimensions,
            "cosmology": self.cosmo.to_dict(),
            "physics": self.physics.get_state(),
            "geometry": self.geometry.get_state(),
            "connections": [c.to_dict() for c in self._connections.values()],
            "event_count": len(self._events),
            "constants": {
                "G": self.config.constants.G,
                "c": self.config.constants.c,
                "h": self.config.constants.h,
                "k_B": self.config.constants.k_B,
                "alpha": self.config.constants.alpha,
                "planck_length": self.config.constants.planck_length,
            },
        }

    def summary(self) -> str:
        """Human-readable summary of the mini-verse."""
        return (
            f"MiniVerse '{self.config.name}' [{self.verse_id}]\n"
            f"  Topology: {self.config.topology.value}\n"
            f"  Dimensions: {self.config.total_dimensions}D ({self.config.spatial_dimensions}+1)\n"
            f"  Age: {self.cosmo.age:.2e} s\n"
            f"  Scale factor: {self.cosmo.scale_factor:.6f}\n"
            f"  Hubble: {self.cosmo.hubble_parameter:.2e} s⁻¹\n"
            f"  Temperature: {self.cosmo.temperature:.2f} K\n"
            f"  Phase: {self.cosmo.phase.value}\n"
            f"  Particles: {len(self.physics.particles)}\n"
            f"  Entropy: {self.cosmo.entropy:.2e}\n"
            f"  Connections: {len(self._connections)}\n"
        )

    def _log_event(self, event_type: str, data: dict) -> None:
        self._events.append({
            "type": event_type,
            "tick": self._tick,
            "time": time.time(),
            "data": data,
        })
        if len(self._events) > 500:
            self._events = self._events[-500:]


# ---------------------------------------------------------------------------
# Inter-Verse Connection
# ---------------------------------------------------------------------------

@dataclass
class MiniVerseConnection:
    """A connection between two mini-verses."""

    connection_id: str
    source_id: str
    target_id: str
    channel_type: str = "wormhole"      # wormhole | entanglement | membrane
    bandwidth: float = 1.0              # particles/second capacity
    active: bool = True
    transfer_count: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "connection_id": self.connection_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "channel_type": self.channel_type,
            "bandwidth": self.bandwidth,
            "active": self.active,
            "transfer_count": self.transfer_count,
        }
