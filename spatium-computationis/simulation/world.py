"""
3D World State — The spatial substrate of Spatium Computationis.

Defines the coordinate system, entities, and zones that comprise the
simulated 3D battlespace.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Vector3 — fundamental spatial unit
# ---------------------------------------------------------------------------

@dataclass
class Vector3:
    """3D coordinate in the simulation space."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def distance_to(self, other: Vector3) -> float:
        """Euclidean distance to another point."""
        return math.sqrt(
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
        )

    def lerp(self, target: Vector3, t: float) -> Vector3:
        """Linear interpolation toward target by factor t (0-1)."""
        return Vector3(
            x=self.x + (target.x - self.x) * t,
            y=self.y + (target.y - self.y) * t,
            z=self.z + (target.z - self.z) * t,
        )

    def normalized(self) -> Vector3:
        """Return unit vector in the same direction."""
        mag = math.sqrt(self.x**2 + self.y**2 + self.z**2)
        if mag == 0:
            return Vector3(0, 0, 0)
        return Vector3(self.x / mag, self.y / mag, self.z / mag)

    def scale(self, factor: float) -> Vector3:
        """Scale vector by a factor."""
        return Vector3(self.x * factor, self.y * factor, self.z * factor)

    def add(self, other: Vector3) -> Vector3:
        """Add two vectors."""
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def to_dict(self) -> dict:
        return {"x": round(self.x, 3), "y": round(self.y, 3), "z": round(self.z, 3)}


# ---------------------------------------------------------------------------
# Entity types and states
# ---------------------------------------------------------------------------

class EntityType(str, Enum):
    """Types of entities that exist in the 3D space."""
    AGENT = "agent"
    THREAT = "threat"
    SIGNAL = "signal"
    HONEYPOT = "honeypot"
    DATA_PACKET = "data_packet"
    DEFENSIVE_NODE = "defensive_node"
    GATEWAY = "gateway"


class EntityState(str, Enum):
    """Current lifecycle state of an entity."""
    SPAWNING = "spawning"
    ACTIVE = "active"
    MOVING = "moving"
    ENGAGING = "engaging"
    INTERCEPTED = "intercepted"
    DESPAWNING = "despawning"


class ZoneType(str, Enum):
    """Spatial zones in the battlespace."""
    KNOWLEDGE_REALM = "knowledge_realm"
    ADVERSARY_LAB = "adversary_lab"
    QUARANTINE = "quarantine"
    HONEYPOT_GRID = "honeypot_grid"
    GATEWAY_PERIMETER = "gateway_perimeter"
    CORE_NEXUS = "core_nexus"
    SHADOW_LAYER = "shadow_layer"


# ---------------------------------------------------------------------------
# Zone — a bounded region of 3D space
# ---------------------------------------------------------------------------

@dataclass
class Zone:
    """A bounded region in the 3D battlespace."""
    zone_id: str
    zone_type: ZoneType
    center: Vector3
    radius: float
    color: str  # hex color for rendering
    label: str

    def contains(self, point: Vector3) -> bool:
        """Check if a point is within this zone."""
        return self.center.distance_to(point) <= self.radius

    def to_dict(self) -> dict:
        return {
            "zone_id": self.zone_id,
            "zone_type": self.zone_type.value,
            "center": self.center.to_dict(),
            "radius": self.radius,
            "color": self.color,
            "label": self.label,
        }


# ---------------------------------------------------------------------------
# Entity — anything that exists in the 3D space
# ---------------------------------------------------------------------------

@dataclass
class Entity:
    """A discrete object in the simulated 3D space."""
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    entity_type: EntityType = EntityType.SIGNAL
    state: EntityState = EntityState.ACTIVE
    position: Vector3 = field(default_factory=Vector3)
    velocity: Vector3 = field(default_factory=Vector3)
    target_position: Vector3 | None = None
    speed: float = 1.0
    size: float = 1.0
    color: str = "#00ff88"
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    spawned_at: float = field(default_factory=time.time)
    ttl: float | None = None  # time-to-live in seconds, None = immortal

    @property
    def age(self) -> float:
        """Seconds since this entity spawned."""
        return time.time() - self.spawned_at

    @property
    def expired(self) -> bool:
        """Whether this entity has exceeded its TTL."""
        if self.ttl is None:
            return False
        return self.age > self.ttl

    def move_toward_target(self, dt: float) -> None:
        """Move entity toward its target position based on speed and dt."""
        if self.target_position is None:
            return

        direction = Vector3(
            self.target_position.x - self.position.x,
            self.target_position.y - self.position.y,
            self.target_position.z - self.position.z,
        )
        dist = self.position.distance_to(self.target_position)

        if dist < 0.1:
            self.position = Vector3(
                self.target_position.x,
                self.target_position.y,
                self.target_position.z,
            )
            self.target_position = None
            self.state = EntityState.ACTIVE
            return

        step = min(self.speed * dt, dist)
        norm = direction.normalized()
        self.position = self.position.add(norm.scale(step))
        self.state = EntityState.MOVING

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "state": self.state.value,
            "position": self.position.to_dict(),
            "velocity": self.velocity.to_dict(),
            "target_position": self.target_position.to_dict() if self.target_position else None,
            "speed": self.speed,
            "size": self.size,
            "color": self.color,
            "label": self.label,
            "metadata": self.metadata,
            "age": round(self.age, 2),
        }


# ---------------------------------------------------------------------------
# SimulationWorld — the complete 3D world state
# ---------------------------------------------------------------------------

# Default zone layout
DEFAULT_ZONES = [
    Zone(
        zone_id="core",
        zone_type=ZoneType.CORE_NEXUS,
        center=Vector3(0, 0, 0),
        radius=8.0,
        color="#6c5ce7",
        label="Core Nexus",
    ),
    Zone(
        zone_id="knowledge",
        zone_type=ZoneType.KNOWLEDGE_REALM,
        center=Vector3(30, 5, 0),
        radius=15.0,
        color="#00cec9",
        label="Knowledge Realm",
    ),
    Zone(
        zone_id="adversary",
        zone_type=ZoneType.ADVERSARY_LAB,
        center=Vector3(-30, 5, 20),
        radius=12.0,
        color="#d63031",
        label="Adversary Lab",
    ),
    Zone(
        zone_id="quarantine",
        zone_type=ZoneType.QUARANTINE,
        center=Vector3(-30, 5, -20),
        radius=10.0,
        color="#fdcb6e",
        label="Quarantine",
    ),
    Zone(
        zone_id="honeypot",
        zone_type=ZoneType.HONEYPOT_GRID,
        center=Vector3(0, 5, 35),
        radius=14.0,
        color="#e17055",
        label="Honeypot Grid",
    ),
    Zone(
        zone_id="gateway",
        zone_type=ZoneType.GATEWAY_PERIMETER,
        center=Vector3(0, 0, -35),
        radius=18.0,
        color="#0984e3",
        label="Gateway Perimeter",
    ),
    Zone(
        zone_id="shadow",
        zone_type=ZoneType.SHADOW_LAYER,
        center=Vector3(0, -15, 0),
        radius=20.0,
        color="#2d3436",
        label="Shadow Layer",
    ),
]


class SimulationWorld:
    """
    The complete 3D world state of Spatium Computationis.

    Maintains all entities, zones, and world clock.
    """

    def __init__(self) -> None:
        self.entities: dict[str, Entity] = {}
        self.zones: list[Zone] = list(DEFAULT_ZONES)
        self.tick_count: int = 0
        self.world_time: float = 0.0
        self.created_at: float = time.time()
        self._event_log: list[dict] = []

    @property
    def entity_count(self) -> int:
        return len(self.entities)

    def spawn_entity(self, entity: Entity) -> Entity:
        """Add an entity to the world."""
        entity.state = EntityState.SPAWNING
        self.entities[entity.entity_id] = entity
        self._log_event("spawn", entity)
        return entity

    def despawn_entity(self, entity_id: str) -> bool:
        """Remove an entity from the world."""
        if entity_id in self.entities:
            entity = self.entities.pop(entity_id)
            entity.state = EntityState.DESPAWNING
            self._log_event("despawn", entity)
            return True
        return False

    def get_entity(self, entity_id: str) -> Entity | None:
        return self.entities.get(entity_id)

    def get_entities_in_zone(self, zone_id: str) -> list[Entity]:
        """Get all entities within a specific zone."""
        zone = next((z for z in self.zones if z.zone_id == zone_id), None)
        if zone is None:
            return []
        return [e for e in self.entities.values() if zone.contains(e.position)]

    def get_entities_by_type(self, entity_type: EntityType) -> list[Entity]:
        return [e for e in self.entities.values() if e.entity_type == entity_type]

    def get_nearby_entities(self, position: Vector3, radius: float) -> list[Entity]:
        """Get all entities within radius of a position."""
        return [
            e for e in self.entities.values()
            if position.distance_to(e.position) <= radius
        ]

    def update(self, dt: float) -> None:
        """Advance world state by dt seconds."""
        self.tick_count += 1
        self.world_time += dt

        # Update all entities
        expired_ids = []
        for entity in self.entities.values():
            if entity.expired:
                expired_ids.append(entity.entity_id)
                continue

            # Transition spawning → active
            if entity.state == EntityState.SPAWNING and entity.age > 0.5:
                entity.state = EntityState.ACTIVE

            # Move toward targets
            entity.move_toward_target(dt)

        # Remove expired entities
        for eid in expired_ids:
            self.despawn_entity(eid)

    def get_state(self) -> dict:
        """Serialize entire world state for transmission."""
        return {
            "tick": self.tick_count,
            "world_time": round(self.world_time, 2),
            "entity_count": self.entity_count,
            "entities": [e.to_dict() for e in self.entities.values()],
            "zones": [z.to_dict() for z in self.zones],
        }

    def get_state_delta(self) -> dict:
        """Lightweight state for frequent updates (entities only)."""
        return {
            "tick": self.tick_count,
            "world_time": round(self.world_time, 2),
            "entities": [
                {
                    "entity_id": e.entity_id,
                    "position": e.position.to_dict(),
                    "state": e.state.value,
                    "color": e.color,
                    "size": e.size,
                }
                for e in self.entities.values()
            ],
        }

    def _log_event(self, event_type: str, entity: Entity) -> None:
        self._event_log.append({
            "type": event_type,
            "entity_id": entity.entity_id,
            "entity_type": entity.entity_type.value,
            "position": entity.position.to_dict(),
            "tick": self.tick_count,
            "time": time.time(),
        })
        # Keep only last 200 events
        if len(self._event_log) > 200:
            self._event_log = self._event_log[-200:]

    def get_recent_events(self, limit: int = 50) -> list[dict]:
        return self._event_log[-limit:]
