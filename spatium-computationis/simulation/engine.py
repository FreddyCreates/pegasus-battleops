"""
Simulation Engine — Tick-based 3D world driver.

Runs the simulation loop, spawns procedural entities, manages
agent presence, and drives world dynamics.
"""

from __future__ import annotations

import asyncio
import math
import random
import time
from typing import Any, Callable

from .world import (
    Entity,
    EntityState,
    EntityType,
    SimulationWorld,
    Vector3,
    ZoneType,
)


# ---------------------------------------------------------------------------
# Simulation configuration
# ---------------------------------------------------------------------------

TICK_RATE = 20  # ticks per second
TICK_INTERVAL = 1.0 / TICK_RATE

# Spawn rates (probability per tick)
SIGNAL_SPAWN_RATE = 0.08
THREAT_SPAWN_RATE = 0.03
DATA_PACKET_RATE = 0.12

# Agent colors by name
AGENT_COLORS = {
    "gatekeeper": "#0984e3",
    "adversary_lab": "#d63031",
    "research_realm": "#00cec9",
    "shadow_decryptor": "#636e72",
    "inspector": "#6c5ce7",
    "estimator": "#fdcb6e",
    "honeypot": "#e17055",
    "defensor": "#00b894",
}


class SimulationEngine:
    """
    Drives the 3D simulation with a tick-based update loop.

    Manages:
    - World state progression
    - Procedural entity spawning (signals, threats, data packets)
    - Agent entity placement
    - Subscriber notifications for real-time streaming
    """

    def __init__(self) -> None:
        self.world = SimulationWorld()
        self.running = False
        self._task: asyncio.Task | None = None
        self._subscribers: list[Callable] = []
        self._spawn_resident_agents()

    def _spawn_resident_agents(self) -> None:
        """Place permanent agent entities at their zone positions."""
        agent_placements = [
            ("gatekeeper", Vector3(0, 2, -35), "Gatekeeper Porta"),
            ("defensor", Vector3(5, 2, -30), "Defensor Campi"),
            ("adversary_lab", Vector3(-30, 7, 20), "Adversary Lab"),
            ("research_realm", Vector3(30, 7, 0), "Research Realm"),
            ("shadow_decryptor", Vector3(0, -12, 0), "Shadow Decryptor"),
            ("honeypot", Vector3(5, 7, 35), "Honeypot Controller"),
            ("inspector", Vector3(0, 3, 0), "Inspector Campi"),
            ("estimator", Vector3(-5, 3, 0), "Estimator Mobilia"),
        ]

        for agent_key, position, label in agent_placements:
            entity = Entity(
                entity_id=f"agent_{agent_key}",
                entity_type=EntityType.AGENT,
                state=EntityState.ACTIVE,
                position=position,
                speed=2.0,
                size=2.5,
                color=AGENT_COLORS.get(agent_key, "#dfe6e9"),
                label=label,
                ttl=None,  # immortal
            )
            self.world.spawn_entity(entity)

        # Place honeypot nodes
        for i in range(5):
            angle = (2 * math.pi / 5) * i
            pos = Vector3(
                math.cos(angle) * 10 + 0,
                6,
                math.sin(angle) * 10 + 35,
            )
            self.world.spawn_entity(Entity(
                entity_id=f"honeypot_node_{i}",
                entity_type=EntityType.HONEYPOT,
                state=EntityState.ACTIVE,
                position=pos,
                size=1.5,
                color="#e17055",
                label=f"Trap {i+1}",
                ttl=None,
            ))

        # Place defensive nodes around core
        for i in range(6):
            angle = (2 * math.pi / 6) * i
            pos = Vector3(
                math.cos(angle) * 10,
                1,
                math.sin(angle) * 10,
            )
            self.world.spawn_entity(Entity(
                entity_id=f"defense_node_{i}",
                entity_type=EntityType.DEFENSIVE_NODE,
                state=EntityState.ACTIVE,
                position=pos,
                size=1.2,
                color="#00b894",
                label=f"Shield {i+1}",
                ttl=None,
            ))

    async def start(self) -> None:
        """Start the simulation loop."""
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the simulation loop."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def subscribe(self, callback: Callable) -> None:
        """Subscribe to world state updates."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable) -> None:
        """Unsubscribe from world state updates."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def _run_loop(self) -> None:
        """Main simulation tick loop."""
        last_time = time.time()
        broadcast_counter = 0

        while self.running:
            now = time.time()
            dt = now - last_time
            last_time = now

            # Update world physics
            self.world.update(dt)

            # Procedural spawning
            self._spawn_signals()
            self._spawn_threats()
            self._spawn_data_packets()

            # Broadcast to subscribers every 3 ticks
            broadcast_counter += 1
            if broadcast_counter >= 3:
                broadcast_counter = 0
                await self._broadcast_state()

            await asyncio.sleep(TICK_INTERVAL)

    def _spawn_signals(self) -> None:
        """Randomly spawn incoming signal entities at the gateway."""
        if random.random() > SIGNAL_SPAWN_RATE:
            return

        # Signals enter from the gateway perimeter and route toward zones
        spawn_pos = Vector3(
            random.uniform(-15, 15),
            random.uniform(0, 3),
            -35 + random.uniform(-5, 5),
        )

        # Route to a random zone
        target_zones = [
            Vector3(30, 5, 0),    # Knowledge
            Vector3(-30, 5, 20),  # Adversary
            Vector3(0, 0, 0),     # Core
        ]
        target = random.choice(target_zones)

        entity = Entity(
            entity_type=EntityType.SIGNAL,
            state=EntityState.ACTIVE,
            position=spawn_pos,
            target_position=target,
            speed=random.uniform(3.0, 8.0),
            size=0.6,
            color="#00ff88",
            label="signal",
            ttl=15.0,
        )
        self.world.spawn_entity(entity)

    def _spawn_threats(self) -> None:
        """Spawn threat entities approaching from random directions."""
        if random.random() > THREAT_SPAWN_RATE:
            return

        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(45, 55)
        spawn_pos = Vector3(
            math.cos(angle) * dist,
            random.uniform(0, 10),
            math.sin(angle) * dist,
        )

        # Threats try to reach the core
        target = Vector3(
            random.uniform(-5, 5),
            random.uniform(0, 3),
            random.uniform(-5, 5),
        )

        colors = ["#ff4757", "#ff6348", "#ff3838"]
        entity = Entity(
            entity_type=EntityType.THREAT,
            state=EntityState.ACTIVE,
            position=spawn_pos,
            target_position=target,
            speed=random.uniform(1.5, 4.0),
            size=random.uniform(0.8, 1.8),
            color=random.choice(colors),
            label="threat",
            ttl=20.0,
            metadata={"threat_level": random.choice(["low", "medium", "high"])},
        )
        self.world.spawn_entity(entity)

    def _spawn_data_packets(self) -> None:
        """Spawn data packets moving between zones."""
        if random.random() > DATA_PACKET_RATE:
            return

        # Packets travel between zones
        zone_centers = [
            Vector3(30, 5, 0),
            Vector3(-30, 5, 20),
            Vector3(0, 0, 0),
            Vector3(0, 5, 35),
        ]
        start = random.choice(zone_centers)
        end = random.choice([z for z in zone_centers if z != start])

        spawn_pos = Vector3(
            start.x + random.uniform(-3, 3),
            start.y + random.uniform(-1, 1),
            start.z + random.uniform(-3, 3),
        )

        entity = Entity(
            entity_type=EntityType.DATA_PACKET,
            state=EntityState.ACTIVE,
            position=spawn_pos,
            target_position=end,
            speed=random.uniform(5.0, 12.0),
            size=0.3,
            color="#74b9ff",
            label="",
            ttl=8.0,
        )
        self.world.spawn_entity(entity)

    async def _broadcast_state(self) -> None:
        """Send world state delta to all subscribers."""
        if not self._subscribers:
            return

        state = self.world.get_state_delta()
        dead_subs = []

        for callback in self._subscribers:
            try:
                await callback(state)
            except Exception:
                dead_subs.append(callback)

        for sub in dead_subs:
            self._subscribers.remove(sub)

    # ---------------------------------------------------------------------------
    # Public API for external manipulation
    # ---------------------------------------------------------------------------

    def inject_entity(
        self,
        entity_type: EntityType,
        position: Vector3,
        target: Vector3 | None = None,
        label: str = "",
        color: str = "#ffffff",
        speed: float = 5.0,
        size: float = 1.0,
        ttl: float | None = 10.0,
        metadata: dict[str, Any] | None = None,
    ) -> Entity:
        """Inject a custom entity into the simulation."""
        entity = Entity(
            entity_type=entity_type,
            state=EntityState.ACTIVE,
            position=position,
            target_position=target,
            speed=speed,
            size=size,
            color=color,
            label=label,
            ttl=ttl,
            metadata=metadata or {},
        )
        return self.world.spawn_entity(entity)

    def get_world_state(self) -> dict:
        """Get full world state snapshot."""
        return self.world.get_state()

    def get_stats(self) -> dict:
        """Get simulation statistics."""
        entities = self.world.entities.values()
        return {
            "running": self.running,
            "tick_count": self.world.tick_count,
            "world_time": round(self.world.world_time, 2),
            "total_entities": self.world.entity_count,
            "by_type": {
                t.value: len([e for e in entities if e.entity_type == t])
                for t in EntityType
            },
            "by_state": {
                s.value: len([e for e in entities if e.state == s])
                for s in EntityState
            },
            "subscribers": len(self._subscribers),
        }
