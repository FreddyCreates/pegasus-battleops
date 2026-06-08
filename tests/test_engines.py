"""
Tests for Mini-Verse Engines — Physics, Geometry, and MiniVerse.

Validates:
    - Conservation laws (energy, momentum)
    - Geodesic correctness in flat space
    - Metric tensor properties
    - Cosmological evolution
    - Particle dynamics
"""

import math
import sys
import os

import numpy as np

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spatium_computationis.simulation.engines.physics import (
    PhysicsConstants,
    PhysicsEngine,
    Particle,
    Vec3,
    Field,
    FieldType,
)
from spatium_computationis.simulation.engines.geometry import (
    GeometryEngine,
    MetricTensor,
    Manifold,
    TopologyType,
)
from spatium_computationis.simulation.engines.miniverse import (
    MiniVerse,
    MiniVerseConfig,
    UniverseTopology,
)


# ===========================================================================
# Physics Engine Tests
# ===========================================================================

class TestPhysicsEngine:
    """Test suite for the physics engine."""

    def test_momentum_conservation_isolated(self):
        """Total momentum must be conserved in an isolated system."""
        engine = PhysicsEngine(enable_collisions=False)

        # Two particles with equal and opposite momenta
        p1 = Particle(mass=1.0, position=Vec3(-10, 0, 0), velocity=Vec3(5, 0, 0))
        p2 = Particle(mass=1.0, position=Vec3(10, 0, 0), velocity=Vec3(-5, 0, 0))
        engine.add_particle(p1)
        engine.add_particle(p2)

        # Initial momentum should be zero
        initial_p = p1.momentum + p2.momentum
        assert abs(initial_p.magnitude) < 1e-10, "Initial momentum should be zero"

        # Run 100 steps
        for _ in range(100):
            diag = engine.step(0.01)

        assert diag["momentum_magnitude"] < 1e-6, (
            f"Momentum not conserved: {diag['momentum_magnitude']}"
        )

    def test_energy_conservation_gravity(self):
        """Energy should be approximately conserved under gravity (Verlet)."""
        engine = PhysicsEngine(enable_relativity=False, enable_collisions=False)

        # Sun-Earth like system (scaled)
        sun = Particle(mass=1e10, position=Vec3.zero(), velocity=Vec3.zero(), fixed=True)
        planet = Particle(mass=1.0, position=Vec3(100, 0, 0), velocity=Vec3(0, 8.16, 0))
        engine.add_particle(sun)
        engine.add_particle(planet)

        # Run for many steps
        for _ in range(1000):
            diag = engine.step(0.1)

        # Verlet should keep energy drift < 1%
        assert diag["energy_conservation_error"] < 0.01, (
            f"Energy drift too large: {diag['energy_conservation_error']}"
        )

    def test_velocity_capped_at_c(self):
        """No particle should exceed the speed of light."""
        constants = PhysicsConstants(c=100.0)  # low c for testing
        engine = PhysicsEngine(constants=constants, enable_relativity=True)

        # Particle with huge initial velocity
        p = Particle(mass=1.0, position=Vec3.zero(), velocity=Vec3(200, 0, 0))
        engine.add_particle(p)

        engine.step(0.01)
        speed = p.velocity.magnitude
        assert speed < constants.c, f"Speed {speed} exceeds c={constants.c}"

    def test_elastic_collision_momentum(self):
        """Elastic collision must conserve total momentum."""
        engine = PhysicsEngine(enable_relativity=False, enable_collisions=True)

        p1 = Particle(mass=2.0, position=Vec3(0, 0, 0), velocity=Vec3(5, 0, 0), radius=1.0)
        p2 = Particle(mass=1.0, position=Vec3(1.5, 0, 0), velocity=Vec3(-3, 0, 0), radius=1.0)
        engine.add_particle(p1)
        engine.add_particle(p2)

        p_initial = (p1.momentum + p2.momentum).magnitude

        engine.step(0.01)

        p_final = (p1.momentum + p2.momentum).magnitude
        assert abs(p_final - p_initial) < 1e-6, (
            f"Momentum changed: {p_initial} -> {p_final}"
        )

    def test_vec3_operations(self):
        """Vector3 algebra correctness."""
        a = Vec3(1, 2, 3)
        b = Vec3(4, 5, 6)

        # Addition
        c = a + b
        assert c.x == 5 and c.y == 7 and c.z == 9

        # Dot product
        assert a.dot(b) == 32  # 1*4 + 2*5 + 3*6

        # Cross product
        cross = a.cross(b)
        assert cross.x == -3 and cross.y == 6 and cross.z == -3

        # Magnitude
        assert abs(Vec3(3, 4, 0).magnitude - 5.0) < 1e-10

    def test_particle_kinetic_energy(self):
        """KE = ½mv² must be correct."""
        p = Particle(mass=2.0, velocity=Vec3(3, 4, 0))  # |v| = 5
        assert abs(p.kinetic_energy - 25.0) < 1e-10  # ½ * 2 * 25 = 25

    def test_planck_units(self):
        """Planck length, mass, time should be approximately correct."""
        c = PhysicsConstants()
        assert 1e-36 < c.planck_length < 1e-34
        assert 1e-9 < c.planck_mass < 1e-7
        assert 1e-45 < c.planck_time < 1e-43


# ===========================================================================
# Geometry Engine Tests
# ===========================================================================

class TestGeometryEngine:
    """Test suite for the geometry engine."""

    def test_minkowski_is_flat(self):
        """Minkowski metric should have zero curvature."""
        manifold = Manifold.flat_spacetime()
        engine = GeometryEngine(manifold)

        point = np.array([0.0, 1.0, 1.0, 1.0])
        curv = engine.compute_curvature(point)

        assert abs(curv.ricci_scalar) < 1e-6, (
            f"Flat space Ricci scalar: {curv.ricci_scalar}"
        )
        assert curv.is_flat

    def test_metric_tensor_inverse(self):
        """g^μν g_νρ = δ^μ_ρ."""
        metric = MetricTensor.minkowski(4)
        product = metric.inverse @ metric.components
        identity = np.eye(4)
        assert np.allclose(product, identity, atol=1e-10)

    def test_schwarzschild_horizon(self):
        """Schwarzschild metric should have horizon at r_s."""
        M = 1e30  # ~solar mass
        G = 6.674e-11
        c = 3e8
        r_s = 2 * G * M / (c * c)

        manifold = Manifold.schwarzschild_spacetime(M, G, c)
        engine = GeometryEngine(manifold)

        horizons = engine.detect_horizons(
            radial_range=(r_s * 0.5, r_s * 3.0),
            num_samples=100,
        )

        assert len(horizons) > 0, "Should detect at least one horizon"
        # Closest horizon should be near r_s
        closest = min(horizons, key=lambda h: abs(h - r_s))
        assert abs(closest - r_s) / r_s < 0.05, (
            f"Horizon at {closest}, expected ~{r_s}"
        )

    def test_geodesic_straight_in_flat_space(self):
        """Geodesics in flat space should be straight lines."""
        manifold = Manifold.flat_spacetime()
        engine = GeometryEngine(manifold)

        start = np.array([0.0, 0.0, 0.0, 0.0])
        direction = np.array([1.0, 1.0, 0.0, 0.0])

        geo = engine.compute_geodesic(start, direction, steps=100, step_size=0.1)

        # In flat space, final position should be start + direction * total_steps * step_size
        final = geo.points[-1]
        expected = start + direction * 100 * 0.1
        assert np.allclose(final, expected, atol=0.01), (
            f"Geodesic deviated: {final} vs {expected}"
        )

    def test_volume_element_flat(self):
        """Volume element in flat space should be 1 (Euclidean) or c (Minkowski)."""
        engine = GeometryEngine(Manifold.flat_spacetime())
        point = np.array([0.0, 1.0, 1.0, 1.0])
        vol = engine.volume_element(point)
        # √|det(η)| = √|-(-1)(1)(1)(1)| = 1
        assert abs(vol - 1.0) < 1e-10

    def test_metric_tensor_signature(self):
        """Minkowski metric should have Lorentzian signature."""
        metric = MetricTensor.minkowski(4)
        eigenvalues = np.linalg.eigvalsh(metric.components)
        # Should have one negative and three positive eigenvalues
        negative_count = sum(1 for ev in eigenvalues if ev < 0)
        assert negative_count == 1


# ===========================================================================
# Mini-Verse Tests
# ===========================================================================

class TestMiniVerse:
    """Test suite for the mini-verse system."""

    def test_creation_flat(self):
        """Create a flat mini-verse."""
        config = MiniVerseConfig(
            name="Test Universe",
            topology=UniverseTopology.FLAT_INFINITE,
        )
        verse = MiniVerse(config)
        assert verse.verse_id is not None
        assert verse.config.name == "Test Universe"

    def test_cosmological_expansion(self):
        """Scale factor should increase in expanding universe."""
        config = MiniVerseConfig(
            topology=UniverseTopology.DE_SITTER,
            hubble_constant=2.2e-18,  # real Hubble constant
            # Use real cosmological parameters (our universe)
        )
        verse = MiniVerse(config)
        initial_a = verse.cosmo.scale_factor

        # With real H₀ ≈ 2.2e-18 s⁻¹, in 1e15 seconds (~31 Myr):
        # Δa/a ≈ H₀ * t = 2.2e-18 * 1e15 = 2.2e-3
        for _ in range(100):
            verse.step(1e13)  # each step = 10 trillion seconds

        assert verse.cosmo.scale_factor > initial_a, (
            f"Scale factor didn't grow: {initial_a} -> {verse.cosmo.scale_factor}"
        )

    def test_entropy_increases(self):
        """Entropy should never decrease (second law)."""
        config = MiniVerseConfig(
            topology=UniverseTopology.DE_SITTER,
            hubble_constant=1e-3,
        )
        verse = MiniVerse(config)

        # Add some particles
        verse.spawn_particles_random(10, position_range=50.0, velocity_range=5.0)

        prev_entropy = verse.cosmo.entropy
        for _ in range(50):
            verse.step(0.1)
            assert verse.cosmo.entropy >= prev_entropy - 1e-30, (
                f"Entropy decreased: {prev_entropy} -> {verse.cosmo.entropy}"
            )
            prev_entropy = verse.cosmo.entropy

    def test_periodic_boundaries(self):
        """Toroidal topology should wrap particle positions."""
        config = MiniVerseConfig(
            topology=UniverseTopology.FLAT_PERIODIC,
            spatial_extent=100.0,
        )
        verse = MiniVerse(config)

        # Place particle near edge with high velocity
        p = verse.spawn_particle(
            mass=1.0,
            position=Vec3(48.0, 0, 0),
            velocity=Vec3(50.0, 0, 0),  # fast enough to cross boundary
        )

        # Step enough for particle to cross boundary
        for _ in range(10):
            verse.step(1.0)

        # Should have wrapped (x should not be > 50 with L=100, half_L=50)
        assert -50.0 <= p.position.x <= 50.0, (
            f"Particle outside bounds: x={p.position.x}"
        )

    def test_particle_limit(self):
        """Should raise error when particle limit is reached."""
        config = MiniVerseConfig(particle_limit=5)
        verse = MiniVerse(config)

        for i in range(5):
            verse.spawn_particle(mass=1.0)

        try:
            verse.spawn_particle(mass=1.0)
            assert False, "Should have raised RuntimeError"
        except RuntimeError:
            pass

    def test_inter_verse_connection(self):
        """Two mini-verses should be connectable."""
        v1 = MiniVerse(MiniVerseConfig(name="Universe A"))
        v2 = MiniVerse(MiniVerseConfig(name="Universe B"))

        conn = v1.connect_to(v2, channel_type="wormhole")
        assert conn.connection_id in v1._connections
        assert conn.connection_id in v2._connections

    def test_particle_transfer(self):
        """Particle should transfer between connected verses."""
        v1 = MiniVerse(MiniVerseConfig(name="Source"))
        v2 = MiniVerse(MiniVerseConfig(name="Target"))

        conn = v1.connect_to(v2, channel_type="wormhole")
        p = v1.spawn_particle(mass=5.0, position=Vec3(1, 2, 3))
        pid = p.particle_id

        assert pid in v1.physics.particles
        assert pid not in v2.physics.particles

        result = v1.transfer_particle(pid, v2, conn.connection_id)
        assert result is True
        assert pid not in v1.physics.particles
        assert pid in v2.physics.particles

    def test_invalid_config(self):
        """Invalid config should raise ValueError."""
        config = MiniVerseConfig()
        config.constants.G = -1.0  # invalid

        try:
            MiniVerse(config)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_state_snapshot(self):
        """get_state should return complete state dict."""
        verse = MiniVerse(MiniVerseConfig(name="Snapshot Test"))
        verse.spawn_particles_random(5)
        verse.step(0.1)

        state = verse.get_state()
        assert "verse_id" in state
        assert "cosmology" in state
        assert "physics" in state
        assert "geometry" in state
        assert state["name"] == "Snapshot Test"


# ===========================================================================
# Run tests
# ===========================================================================

def run_tests():
    """Run all tests and report results."""
    test_classes = [TestPhysicsEngine, TestGeometryEngine, TestMiniVerse]
    total = 0
    passed = 0
    failed = 0
    errors = []

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]

        for method_name in methods:
            total += 1
            try:
                getattr(instance, method_name)()
                passed += 1
                print(f"  ✓ {cls.__name__}.{method_name}")
            except Exception as e:
                failed += 1
                errors.append((f"{cls.__name__}.{method_name}", str(e)))
                print(f"  ✗ {cls.__name__}.{method_name}: {e}")

    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    if errors:
        print(f"\nFailures:")
        for name, err in errors:
            print(f"  - {name}: {err}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
