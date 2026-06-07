"""
Simulation API Routes — REST + WebSocket endpoints for the 3D space.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .engine import SimulationEngine
from .world import EntityType, Vector3

# ---------------------------------------------------------------------------
# Singleton simulation engine
# ---------------------------------------------------------------------------

_engine: SimulationEngine | None = None


def get_engine() -> SimulationEngine:
    """Get or create the simulation engine singleton."""
    global _engine
    if _engine is None:
        _engine = SimulationEngine()
    return _engine


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

simulation_router = APIRouter(prefix="/simulation", tags=["simulation"])


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------

@simulation_router.get("/state")
async def get_world_state():
    """Get the full 3D world state snapshot."""
    engine = get_engine()
    return engine.get_world_state()


@simulation_router.get("/stats")
async def get_simulation_stats():
    """Get simulation statistics and entity counts."""
    engine = get_engine()
    return engine.get_stats()


@simulation_router.post("/start")
async def start_simulation():
    """Start the simulation engine."""
    engine = get_engine()
    await engine.start()
    return {"status": "running", "message": "Simulation started"}


@simulation_router.post("/stop")
async def stop_simulation():
    """Stop the simulation engine."""
    engine = get_engine()
    await engine.stop()
    return {"status": "stopped", "message": "Simulation stopped"}


@simulation_router.get("/events")
async def get_recent_events(limit: int = 50):
    """Get recent simulation events."""
    engine = get_engine()
    return engine.world.get_recent_events(limit)


@simulation_router.get("/zones")
async def get_zones():
    """Get all zones in the 3D space."""
    engine = get_engine()
    return [z.to_dict() for z in engine.world.zones]


@simulation_router.get("/entities/{entity_id}")
async def get_entity(entity_id: str):
    """Get a specific entity by ID."""
    engine = get_engine()
    entity = engine.world.get_entity(entity_id)
    if entity is None:
        return {"error": "Entity not found"}
    return entity.to_dict()


class InjectEntityRequest(BaseModel):
    entity_type: str = "signal"
    position: dict = {"x": 0, "y": 0, "z": -35}
    target: dict | None = {"x": 0, "y": 0, "z": 0}
    label: str = "injected"
    color: str = "#ffffff"
    speed: float = 5.0
    size: float = 1.0
    ttl: float | None = 10.0


@simulation_router.post("/inject")
async def inject_entity(req: InjectEntityRequest):
    """Inject a custom entity into the 3D space."""
    engine = get_engine()

    try:
        etype = EntityType(req.entity_type)
    except ValueError:
        etype = EntityType.SIGNAL

    pos = Vector3(req.position.get("x", 0), req.position.get("y", 0), req.position.get("z", 0))
    target = None
    if req.target:
        target = Vector3(req.target.get("x", 0), req.target.get("y", 0), req.target.get("z", 0))

    entity = engine.inject_entity(
        entity_type=etype,
        position=pos,
        target=target,
        label=req.label,
        color=req.color,
        speed=req.speed,
        size=req.size,
        ttl=req.ttl,
    )
    return {"status": "injected", "entity": entity.to_dict()}


# ---------------------------------------------------------------------------
# WebSocket — Real-time 3D state streaming
# ---------------------------------------------------------------------------

@simulation_router.websocket("/ws")
async def simulation_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time 3D simulation streaming.

    Streams world state deltas at ~7 FPS for smooth 3D rendering.
    
    Client can send commands:
    - {"cmd": "inject", "entity_type": "threat", "position": {...}, ...}
    - {"cmd": "despawn", "entity_id": "..."}
    - {"cmd": "get_state"}
    """
    await websocket.accept()
    engine = get_engine()

    # Auto-start simulation on first connection
    if not engine.running:
        await engine.start()

    # Create subscriber callback
    async def send_state(state: dict):
        try:
            await websocket.send_json({"type": "state_delta", "data": state})
        except Exception:
            raise

    engine.subscribe(send_state)

    # Send initial full state
    await websocket.send_json({
        "type": "full_state",
        "data": engine.get_world_state(),
    })

    try:
        while True:
            # Listen for client commands
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                cmd = msg.get("cmd")

                if cmd == "get_state":
                    await websocket.send_json({
                        "type": "full_state",
                        "data": engine.get_world_state(),
                    })
                elif cmd == "inject":
                    etype = EntityType(msg.get("entity_type", "signal"))
                    pos_data = msg.get("position", {"x": 0, "y": 0, "z": -35})
                    pos = Vector3(pos_data.get("x", 0), pos_data.get("y", 0), pos_data.get("z", 0))
                    target_data = msg.get("target")
                    target = Vector3(target_data["x"], target_data["y"], target_data["z"]) if target_data else None

                    entity = engine.inject_entity(
                        entity_type=etype,
                        position=pos,
                        target=target,
                        label=msg.get("label", ""),
                        color=msg.get("color", "#ffffff"),
                        speed=msg.get("speed", 5.0),
                        size=msg.get("size", 1.0),
                        ttl=msg.get("ttl", 10.0),
                    )
                    await websocket.send_json({
                        "type": "inject_ack",
                        "entity": entity.to_dict(),
                    })
                elif cmd == "despawn":
                    eid = msg.get("entity_id", "")
                    success = engine.world.despawn_entity(eid)
                    await websocket.send_json({
                        "type": "despawn_ack",
                        "entity_id": eid,
                        "success": success,
                    })
                elif cmd == "stats":
                    await websocket.send_json({
                        "type": "stats",
                        "data": engine.get_stats(),
                    })

            except (json.JSONDecodeError, KeyError, ValueError):
                await websocket.send_json({"type": "error", "message": "Invalid command"})

    except WebSocketDisconnect:
        pass
    finally:
        engine.unsubscribe(send_state)
