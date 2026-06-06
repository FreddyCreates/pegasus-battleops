"""
Spatium Computationis — 3D Simulation Environment
⌬ A real 3D space where agents, threats, and signals exist as physical entities.

The simulation runs a tick-based world with:
- 3D coordinate system (Vector3)
- Entity lifecycle (spawn, move, interact, despawn)
- Spatial zones (Knowledge Realm, Adversary Lab, Quarantine, Honeypot Grid)
- Real-time WebSocket streaming of world state
"""

from .world import SimulationWorld, Vector3, Entity, Zone
from .engine import SimulationEngine

__all__ = [
    "SimulationWorld",
    "SimulationEngine",
    "Vector3",
    "Entity",
    "Zone",
]
