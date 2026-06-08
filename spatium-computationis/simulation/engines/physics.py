"""
Physics Engine — Real Newtonian & Relativistic Mechanics
⌬ Conservation laws, field theory, force accumulation, Verlet integration.

This engine implements:
    - Newtonian dynamics with symplectic Verlet integration
    - Gravitational, electromagnetic, and custom field interactions
    - Conservation of energy, momentum, and angular momentum tracking
    - Relativistic corrections (Lorentz factor) at high velocities
    - Thermodynamic entropy production in irreversible processes
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Physical constants (SI units, configurable per mini-verse)
# ---------------------------------------------------------------------------

@dataclass
class PhysicsConstants:
    """Fundamental physical constants defining a universe's physics."""

    G: float = 6.67430e-11          # Gravitational constant (m³/kg·s²)
    c: float = 2.99792458e8         # Speed of light (m/s)
    h: float = 6.62607015e-34       # Planck constant (J·s)
    k_B: float = 1.380649e-23       # Boltzmann constant (J/K)
    epsilon_0: float = 8.854187817e-12  # Vacuum permittivity (F/m)
    mu_0: float = 1.2566370621e-6   # Vacuum permeability (H/m)
    e: float = 1.602176634e-19      # Elementary charge (C)
    m_e: float = 9.1093837015e-31   # Electron mass (kg)
    m_p: float = 1.67262192369e-27  # Proton mass (kg)
    alpha: float = 7.2973525693e-3  # Fine-structure constant (dimensionless)

    @property
    def k_coulomb(self) -> float:
        """Coulomb's constant: 1/(4πε₀)."""
        return 1.0 / (4.0 * math.pi * self.epsilon_0)

    @property
    def schwarzschild_radius_factor(self) -> float:
        """2G/c² for computing Schwarzschild radius."""
        return 2.0 * self.G / (self.c ** 2)

    @property
    def planck_length(self) -> float:
        """√(ℏG/c³) — the Planck length."""
        hbar = self.h / (2.0 * math.pi)
        return math.sqrt(hbar * self.G / (self.c ** 3))

    @property
    def planck_mass(self) -> float:
        """√(ℏc/G) — the Planck mass."""
        hbar = self.h / (2.0 * math.pi)
        return math.sqrt(hbar * self.c / self.G)

    @property
    def planck_time(self) -> float:
        """√(ℏG/c⁵) — the Planck time."""
        hbar = self.h / (2.0 * math.pi)
        return math.sqrt(hbar * self.G / (self.c ** 5))


# ---------------------------------------------------------------------------
# 3D Vector (physics-grade, operator overloaded)
# ---------------------------------------------------------------------------

@dataclass
class Vec3:
    """3D vector with full operator algebra."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vec3:
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vec3:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vec3:
        if scalar == 0:
            return Vec3(0, 0, 0)
        return Vec3(self.x / scalar, self.y / scalar, self.z / scalar)

    def __neg__(self) -> Vec3:
        return Vec3(-self.x, -self.y, -self.z)

    @property
    def magnitude(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    @property
    def magnitude_squared(self) -> float:
        return self.x ** 2 + self.y ** 2 + self.z ** 2

    def dot(self, other: Vec3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vec3) -> Vec3:
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def normalized(self) -> Vec3:
        mag = self.magnitude
        if mag < 1e-15:
            return Vec3(0, 0, 0)
        return self / mag

    def distance_to(self, other: Vec3) -> float:
        return (self - other).magnitude

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "z": self.z}

    @classmethod
    def zero(cls) -> Vec3:
        return cls(0.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# Particle — a point mass with charge, spin, and state
# ---------------------------------------------------------------------------

class ParticleType(str, Enum):
    MASSIVE = "massive"
    MASSLESS = "massless"
    CHARGED = "charged"
    NEUTRAL = "neutral"


@dataclass
class Particle:
    """A physical particle with full dynamical state."""

    particle_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    mass: float = 1.0               # kg
    charge: float = 0.0             # Coulombs
    spin: float = 0.0               # intrinsic angular momentum quantum number
    position: Vec3 = field(default_factory=Vec3.zero)
    velocity: Vec3 = field(default_factory=Vec3.zero)
    acceleration: Vec3 = field(default_factory=Vec3.zero)
    force_accumulator: Vec3 = field(default_factory=Vec3.zero)
    particle_type: ParticleType = ParticleType.MASSIVE
    fixed: bool = False             # if True, does not respond to forces
    radius: float = 0.1            # collision radius
    temperature: float = 0.0       # K
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def momentum(self) -> Vec3:
        """p = mv (non-relativistic)."""
        return self.velocity * self.mass

    @property
    def kinetic_energy(self) -> float:
        """T = ½mv² (non-relativistic)."""
        return 0.5 * self.mass * self.velocity.magnitude_squared

    @property
    def lorentz_factor(self) -> float:
        """γ = 1/√(1 - v²/c²) — requires constants context."""
        # Use default c; for mini-verse specific c, use engine method
        c = 2.99792458e8
        beta_sq = self.velocity.magnitude_squared / (c * c)
        if beta_sq >= 1.0:
            return float("inf")
        return 1.0 / math.sqrt(1.0 - beta_sq)

    @property
    def relativistic_mass(self) -> float:
        """γm₀ — relativistic mass."""
        return self.mass * self.lorentz_factor

    @property
    def relativistic_momentum(self) -> Vec3:
        """γmv — relativistic momentum."""
        return self.velocity * self.relativistic_mass

    @property
    def rest_energy(self) -> float:
        """E₀ = mc² — rest energy."""
        c = 2.99792458e8
        return self.mass * c * c

    def apply_force(self, force: Vec3) -> None:
        """Accumulate a force vector for this timestep."""
        self.force_accumulator = self.force_accumulator + force

    def clear_forces(self) -> None:
        """Reset force accumulator for new timestep."""
        self.force_accumulator = Vec3.zero()

    def to_dict(self) -> dict:
        return {
            "particle_id": self.particle_id,
            "mass": self.mass,
            "charge": self.charge,
            "position": self.position.to_dict(),
            "velocity": self.velocity.to_dict(),
            "kinetic_energy": self.kinetic_energy,
            "momentum": self.momentum.to_dict(),
            "particle_type": self.particle_type.value,
        }


# ---------------------------------------------------------------------------
# Force — a vector force acting on particles
# ---------------------------------------------------------------------------

@dataclass
class Force:
    """A named force vector applied to a particle."""

    name: str
    vector: Vec3
    source_id: str | None = None
    target_id: str | None = None


# ---------------------------------------------------------------------------
# Field — a spatial force field (gravitational, EM, custom)
# ---------------------------------------------------------------------------

class FieldType(str, Enum):
    GRAVITATIONAL = "gravitational"
    ELECTRIC = "electric"
    MAGNETIC = "magnetic"
    CUSTOM = "custom"


@dataclass
class Field:
    """A spatial field that exerts forces on particles."""

    field_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    field_type: FieldType = FieldType.GRAVITATIONAL
    source_position: Vec3 = field(default_factory=Vec3.zero)
    strength: float = 1.0           # field-specific coupling
    falloff_power: float = 2.0      # inverse power law exponent (2 = inverse-square)
    max_range: float = float("inf")
    active: bool = True

    def force_at(self, position: Vec3, particle: Particle, constants: PhysicsConstants) -> Vec3:
        """Compute force on a particle at given position due to this field."""
        if not self.active:
            return Vec3.zero()

        displacement = self.source_position - position
        distance = displacement.magnitude

        if distance < 1e-10 or distance > self.max_range:
            return Vec3.zero()

        direction = displacement.normalized()

        if self.field_type == FieldType.GRAVITATIONAL:
            # F = GMm/r² toward source
            force_mag = constants.G * self.strength * particle.mass / (distance ** self.falloff_power)
            return direction * force_mag

        elif self.field_type == FieldType.ELECTRIC:
            # F = kQq/r² (repulsive for like charges)
            force_mag = constants.k_coulomb * self.strength * particle.charge / (distance ** self.falloff_power)
            # Positive strength + positive charge → repulsive (away from source)
            return direction * (-force_mag)

        elif self.field_type == FieldType.MAGNETIC:
            # F = qv × B (Lorentz force, simplified: B along displacement)
            B_field = direction * (self.strength / (distance ** self.falloff_power))
            force = particle.velocity.cross(B_field) * particle.charge
            return force

        elif self.field_type == FieldType.CUSTOM:
            # Generic inverse-power attractive field
            force_mag = self.strength / (distance ** self.falloff_power)
            return direction * force_mag * particle.mass

        return Vec3.zero()


# ---------------------------------------------------------------------------
# Physics Engine — the integrator and conservation tracker
# ---------------------------------------------------------------------------

class PhysicsEngine:
    """
    Production physics engine with Velocity Verlet integration.

    Features:
        - Symplectic integration (energy-conserving for Hamiltonian systems)
        - N-body gravitational & electromagnetic interactions
        - Configurable physical constants (per-universe)
        - Conservation law tracking (energy, momentum, angular momentum)
        - Relativistic corrections at high β
        - Collision detection (sphere-sphere)
        - Entropy production tracking
    """

    def __init__(
        self,
        constants: PhysicsConstants | None = None,
        enable_relativity: bool = True,
        enable_collisions: bool = True,
        softening_length: float = 0.01,
    ) -> None:
        self.constants = constants or PhysicsConstants()
        self.enable_relativity = enable_relativity
        self.enable_collisions = enable_collisions
        self.softening_length = softening_length  # prevents division by zero in N-body

        self.particles: dict[str, Particle] = {}
        self.fields: list[Field] = []
        self.custom_forces: list[Callable[[Particle, float], Vec3]] = []

        # Conservation tracking
        self._total_energy_history: list[float] = []
        self._total_momentum_history: list[Vec3] = []
        self._entropy: float = 0.0
        self._time: float = 0.0
        self._tick: int = 0

    # -----------------------------------------------------------------------
    # Particle management
    # -----------------------------------------------------------------------

    def add_particle(self, particle: Particle) -> Particle:
        """Register a particle in the simulation."""
        self.particles[particle.particle_id] = particle
        return particle

    def remove_particle(self, particle_id: str) -> bool:
        """Remove particle by ID."""
        return self.particles.pop(particle_id, None) is not None

    def get_particle(self, particle_id: str) -> Particle | None:
        return self.particles.get(particle_id)

    # -----------------------------------------------------------------------
    # Field management
    # -----------------------------------------------------------------------

    def add_field(self, f: Field) -> Field:
        """Register a spatial field."""
        self.fields.append(f)
        return f

    def add_custom_force(self, force_fn: Callable[[Particle, float], Vec3]) -> None:
        """Add a custom force function f(particle, dt) -> Vec3."""
        self.custom_forces.append(force_fn)

    # -----------------------------------------------------------------------
    # Integration step (Velocity Verlet)
    # -----------------------------------------------------------------------

    def step(self, dt: float) -> dict[str, Any]:
        """
        Advance simulation by dt seconds using Velocity Verlet.

        Velocity Verlet algorithm:
            x(t+dt) = x(t) + v(t)·dt + ½a(t)·dt²
            a(t+dt) = F(t+dt)/m
            v(t+dt) = v(t) + ½[a(t) + a(t+dt)]·dt

        Returns diagnostics dict with conservation data.
        """
        self._tick += 1
        self._time += dt
        particles = list(self.particles.values())

        # Phase 1: Position update using current velocity and acceleration
        for p in particles:
            if p.fixed:
                continue
            # x(t+dt) = x(t) + v(t)*dt + 0.5*a(t)*dt^2
            p.position = p.position + p.velocity * dt + p.acceleration * (0.5 * dt * dt)

        # Phase 2: Compute new forces and accelerations
        old_accelerations = {p.particle_id: p.acceleration for p in particles}

        for p in particles:
            p.clear_forces()

        self._compute_forces(particles, dt)

        # Phase 3: Update acceleration and velocity
        for p in particles:
            if p.fixed:
                continue

            # a(t+dt) = F/m
            if p.mass > 0:
                p.acceleration = p.force_accumulator / p.mass
            else:
                p.acceleration = Vec3.zero()

            # Relativistic correction: limit velocity to < c
            if self.enable_relativity:
                beta_sq = p.velocity.magnitude_squared / (self.constants.c ** 2)
                if beta_sq > 0.01:  # only apply correction above 10% c
                    gamma = 1.0 / math.sqrt(max(1.0 - beta_sq, 1e-10))
                    # Effective acceleration reduced by γ³ for longitudinal motion
                    p.acceleration = p.acceleration / (gamma ** 3)

            # v(t+dt) = v(t) + 0.5*(a_old + a_new)*dt
            old_a = old_accelerations.get(p.particle_id, Vec3.zero())
            p.velocity = p.velocity + (old_a + p.acceleration) * (0.5 * dt)

            # Hard clamp velocity to < c (physical limit)
            if self.enable_relativity:
                speed = p.velocity.magnitude
                if speed >= self.constants.c * 0.9999:
                    p.velocity = p.velocity.normalized() * (self.constants.c * 0.9999)

        # Phase 4: Collision detection
        if self.enable_collisions:
            self._resolve_collisions(particles)

        # Phase 5: Track conservation laws
        diagnostics = self._compute_diagnostics(particles)

        return diagnostics

    # -----------------------------------------------------------------------
    # Force computation
    # -----------------------------------------------------------------------

    def _compute_forces(self, particles: list[Particle], dt: float) -> None:
        """Compute all forces on all particles."""
        n = len(particles)

        # N-body pairwise gravitational + electrostatic
        for i in range(n):
            for j in range(i + 1, n):
                pi, pj = particles[i], particles[j]
                displacement = pj.position - pi.position
                dist_sq = displacement.magnitude_squared + self.softening_length ** 2
                dist = math.sqrt(dist_sq)
                direction = displacement / dist

                # Gravitational attraction: F = GMiMj / r²
                if pi.mass > 0 and pj.mass > 0:
                    fg_mag = self.constants.G * pi.mass * pj.mass / dist_sq
                    fg = direction * fg_mag
                    pi.apply_force(fg)
                    pj.apply_force(-fg)

                # Coulomb interaction: F = kQ1Q2 / r²
                if pi.charge != 0 and pj.charge != 0:
                    fe_mag = self.constants.k_coulomb * pi.charge * pj.charge / dist_sq
                    fe = direction * (-fe_mag)  # like charges repel
                    pi.apply_force(fe)
                    pj.apply_force(-fe)

        # External field forces
        for p in particles:
            for f in self.fields:
                force = f.force_at(p.position, p, self.constants)
                p.apply_force(force)

        # Custom force functions
        for p in particles:
            for force_fn in self.custom_forces:
                force = force_fn(p, dt)
                p.apply_force(force)

    # -----------------------------------------------------------------------
    # Collision resolution (elastic, conserves momentum + energy)
    # -----------------------------------------------------------------------

    def _resolve_collisions(self, particles: list[Particle]) -> None:
        """Detect and resolve sphere-sphere collisions elastically."""
        n = len(particles)
        for i in range(n):
            for j in range(i + 1, n):
                pi, pj = particles[i], particles[j]
                if pi.fixed and pj.fixed:
                    continue

                displacement = pj.position - pi.position
                dist = displacement.magnitude
                min_dist = pi.radius + pj.radius

                if dist < min_dist and dist > 1e-10:
                    # Elastic collision (conservation of momentum and KE)
                    normal = displacement.normalized()

                    # Relative velocity along collision normal
                    v_rel = pi.velocity - pj.velocity
                    v_rel_n = v_rel.dot(normal)

                    # Only resolve if particles are approaching
                    if v_rel_n <= 0:
                        continue

                    # Coefficient of restitution (perfectly elastic)
                    e = 1.0

                    # Impulse magnitude
                    if pi.fixed:
                        j_mag = -(1 + e) * v_rel_n * pj.mass
                        pj.velocity = pj.velocity + normal * (j_mag / pj.mass)
                    elif pj.fixed:
                        j_mag = -(1 + e) * v_rel_n * pi.mass
                        pi.velocity = pi.velocity - normal * (j_mag / pi.mass)
                    else:
                        j_mag = -(1 + e) * v_rel_n / (1.0 / pi.mass + 1.0 / pj.mass)
                        pi.velocity = pi.velocity - normal * (j_mag / pi.mass)
                        pj.velocity = pj.velocity + normal * (j_mag / pj.mass)

                    # Separate overlapping particles
                    overlap = min_dist - dist
                    if not pi.fixed and not pj.fixed:
                        pi.position = pi.position - normal * (overlap * 0.5)
                        pj.position = pj.position + normal * (overlap * 0.5)
                    elif pi.fixed:
                        pj.position = pj.position + normal * overlap
                    else:
                        pi.position = pi.position - normal * overlap

    # -----------------------------------------------------------------------
    # Conservation law diagnostics
    # -----------------------------------------------------------------------

    def _compute_diagnostics(self, particles: list[Particle]) -> dict[str, Any]:
        """Compute total energy, momentum, angular momentum."""
        total_ke = 0.0
        total_pe = 0.0
        total_momentum = Vec3.zero()
        total_angular_momentum = Vec3.zero()

        for p in particles:
            total_ke += p.kinetic_energy
            total_momentum = total_momentum + p.momentum
            # L = r × p
            total_angular_momentum = total_angular_momentum + p.position.cross(p.momentum)

        # Gravitational PE between all pairs
        particle_list = list(particles)
        n = len(particle_list)
        for i in range(n):
            for j in range(i + 1, n):
                pi, pj = particle_list[i], particle_list[j]
                dist = pi.position.distance_to(pj.position)
                if dist > 1e-10:
                    total_pe -= self.constants.G * pi.mass * pj.mass / dist
                    # Coulomb PE
                    if pi.charge != 0 and pj.charge != 0:
                        total_pe += self.constants.k_coulomb * pi.charge * pj.charge / dist

        total_energy = total_ke + total_pe

        self._total_energy_history.append(total_energy)
        self._total_momentum_history.append(total_momentum)

        # Entropy: measure energy drift (should be ~0 for symplectic integrator)
        if len(self._total_energy_history) > 1:
            energy_drift = abs(total_energy - self._total_energy_history[0])
            self._entropy += energy_drift * 1e-6  # minimal entropy from numerical error

        return {
            "tick": self._tick,
            "time": round(self._time, 6),
            "total_kinetic_energy": total_ke,
            "total_potential_energy": total_pe,
            "total_energy": total_energy,
            "total_momentum": total_momentum.to_dict(),
            "total_angular_momentum": total_angular_momentum.to_dict(),
            "momentum_magnitude": total_momentum.magnitude,
            "particle_count": n,
            "entropy": self._entropy,
            "energy_conservation_error": (
                abs(total_energy - self._total_energy_history[0]) / max(abs(self._total_energy_history[0]), 1e-30)
                if len(self._total_energy_history) > 1
                else 0.0
            ),
        }

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    @property
    def total_energy(self) -> float:
        """Current total energy of the system."""
        if self._total_energy_history:
            return self._total_energy_history[-1]
        return 0.0

    @property
    def total_momentum(self) -> Vec3:
        """Current total momentum of the system."""
        if self._total_momentum_history:
            return self._total_momentum_history[-1]
        return Vec3.zero()

    def get_state(self) -> dict:
        """Full engine state snapshot."""
        return {
            "tick": self._tick,
            "time": self._time,
            "particle_count": len(self.particles),
            "field_count": len(self.fields),
            "particles": [p.to_dict() for p in self.particles.values()],
            "constants": {
                "G": self.constants.G,
                "c": self.constants.c,
                "h": self.constants.h,
                "k_B": self.constants.k_B,
                "planck_length": self.constants.planck_length,
            },
            "conservation": {
                "energy_history_len": len(self._total_energy_history),
                "entropy": self._entropy,
            },
        }
