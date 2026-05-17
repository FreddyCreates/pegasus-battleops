"""
Defense Dashboard WebSocket — Real-Time Threat Feed
◎ Stream live threat events to connected clients.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from ..schemas import DefenseMetrics, ThreatFeedMessage


class ConnectionManager:
    """Manage WebSocket connections for the threat feed."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict[str, Any]):
        """Send message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_to(self, websocket: WebSocket, message: dict[str, Any]):
        """Send message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)


# Global connection manager
manager = ConnectionManager()


async def defense_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time threat feed.
    
    Clients connect to receive:
    - Live honeypot events
    - Threat alerts
    - Metrics updates
    - Anomaly notifications
    """
    await manager.connect(websocket)
    
    # Send initial state
    from ...agents.vigil_operis.agent import compute_metrics, get_recent_threat_feed
    
    try:
        # Send current metrics
        metrics = compute_metrics(window_minutes=5)
        await manager.send_to(websocket, {
            "type": "metrics",
            "data": metrics.model_dump(mode="json"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        # Send recent events
        recent = get_recent_threat_feed(limit=20)
        for msg in recent:
            await manager.send_to(websocket, {
                "type": msg.message_type,
                "data": msg.data,
                "timestamp": msg.timestamp.isoformat(),
            })
        
        # Keep connection alive and listen for commands
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Handle client commands
                try:
                    command = json.loads(data)
                    await handle_client_command(websocket, command)
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await manager.send_to(websocket, {
                    "type": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


async def handle_client_command(websocket: WebSocket, command: dict[str, Any]):
    """Handle commands from WebSocket clients."""
    cmd_type = command.get("type", "")
    
    if cmd_type == "get_metrics":
        from ...agents.vigil_operis.agent import compute_metrics
        window = command.get("window_minutes", 5)
        metrics = compute_metrics(window_minutes=window)
        await manager.send_to(websocket, {
            "type": "metrics",
            "data": metrics.model_dump(mode="json"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    elif cmd_type == "get_threats":
        from ..honeypot.collector import FingerprintCollector
        from ..schemas import ThreatLevel
        min_level = command.get("min_level", "low")
        threats = FingerprintCollector.get_threats(ThreatLevel(min_level))
        await manager.send_to(websocket, {
            "type": "threats",
            "data": [t.model_dump(mode="json") for t in threats[:50]],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    elif cmd_type == "get_events":
        from ..honeypot.collector import FingerprintCollector
        limit = command.get("limit", 50)
        events = FingerprintCollector.get_recent_events(limit)
        await manager.send_to(websocket, {
            "type": "events",
            "data": [e.model_dump(mode="json") for e in events],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    elif cmd_type == "get_genome":
        from ...agents.adaptio_mentis.agent import get_genome_patterns
        limit = command.get("limit", 20)
        patterns = get_genome_patterns(limit)
        await manager.send_to(websocket, {
            "type": "genome",
            "data": [p.model_dump(mode="json") for p in patterns],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


async def broadcast_event(event_type: str, data: dict[str, Any]):
    """Broadcast an event to all connected dashboard clients."""
    await manager.broadcast({
        "type": event_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def broadcast_honeypot_event(event):
    """Broadcast a honeypot trigger to all connected clients."""
    await broadcast_event("honeypot_event", {
        "event_id": event.event_id,
        "trap_type": event.trap_type.value,
        "trap_path": event.trap_path,
        "ip_address": event.ip_address,
        "attack_pattern": event.attack_pattern,
        "tools_detected": event.tools_detected,
    })


async def broadcast_threat_alert(fingerprint):
    """Broadcast a threat alert to all connected clients."""
    await broadcast_event("threat_alert", {
        "fingerprint_id": fingerprint.fingerprint_id,
        "ip_address": fingerprint.ip_address,
        "classification": fingerprint.classification.value,
        "threat_level": fingerprint.threat_level.value,
        "honeypot_triggers": fingerprint.honeypot_triggers,
    })


async def broadcast_metrics_update(metrics: DefenseMetrics):
    """Broadcast updated metrics to all connected clients."""
    await broadcast_event("metrics_update", metrics.model_dump(mode="json"))
