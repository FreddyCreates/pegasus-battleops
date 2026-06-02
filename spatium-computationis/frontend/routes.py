"""
Frontend Routes — Spatium Computationis  🌐

FastAPI router serving the customer-facing static site and interactive app.
Provides:
  - Static file serving (CSS/JS assets)
  - Template-rendered HTML pages
  - SSE streaming endpoints for real-time updates
  - Interactive WebSocket app endpoint
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Paths
FRONTEND_DIR = Path(__file__).parent
TEMPLATES_DIR = FRONTEND_DIR / "templates"
STATIC_DIR = FRONTEND_DIR / "static"

# Router
frontend_router = APIRouter(tags=["frontend"])

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ---------------------------------------------------------------------------
# Static Site Pages
# ---------------------------------------------------------------------------

@frontend_router.get("/", response_class=HTMLResponse, tags=["frontend"])
async def homepage(request: Request):
    """
    🌐 Main landing page — Spatium Computationis dashboard.
    """
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Spatium Computationis ⌬",
        "version": "0.5.0",
    })


@frontend_router.get("/app", response_class=HTMLResponse, tags=["frontend"])
async def interactive_app(request: Request):
    """
    🖥️ Interactive application — real-time project management interface.
    """
    return templates.TemplateResponse("app.html", {
        "request": request,
        "title": "Spatium Computationis — Interactive Console",
    })


@frontend_router.get("/projects", response_class=HTMLResponse, tags=["frontend"])
async def projects_page(request: Request):
    """
    📁 Projects overview page.
    """
    return templates.TemplateResponse("projects.html", {
        "request": request,
        "title": "Projects — Spatium Computationis",
    })


@frontend_router.get("/agents/dashboard", response_class=HTMLResponse, tags=["frontend"])
async def agents_dashboard(request: Request):
    """
    ⎈ Agent status dashboard.
    """
    return templates.TemplateResponse("agents.html", {
        "request": request,
        "title": "Agents — Spatium Computationis",
    })


# ---------------------------------------------------------------------------
# Server-Sent Events (SSE) Streaming
# ---------------------------------------------------------------------------

class SSEManager:
    """Manages SSE connections and event broadcasting."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self._subscribers.remove(queue)

    async def broadcast(self, event_type: str, data: dict[str, Any]):
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        for queue in self._subscribers:
            await queue.put(message)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


# Global SSE manager
sse_manager = SSEManager()


async def _event_generator(queue: asyncio.Queue):
    """Generate SSE events from a subscriber queue."""
    try:
        while True:
            message = await asyncio.wait_for(queue.get(), timeout=30.0)
            yield f"event: {message['type']}\ndata: {json.dumps(message)}\n\n"
    except asyncio.TimeoutError:
        # Send keepalive
        yield f": keepalive\n\n"
    except asyncio.CancelledError:
        return


@frontend_router.get("/sse/events", tags=["frontend"])
async def sse_event_stream(request: Request):
    """
    📡 Server-Sent Events stream for real-time platform updates.

    Events include:
    - task_submitted: New task added to queue
    - task_completed: Task finished
    - agent_status: Agent health change
    - pipeline_update: Pipeline stage completion
    - field_update: Field feedback received
    """
    queue = sse_manager.subscribe()

    async def generate():
        try:
            # Send initial connection event
            initial = {
                "type": "connected",
                "data": {"message": "SSE stream active", "glyph": "📡"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            yield f"event: connected\ndata: {json.dumps(initial)}\n\n"

            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"event: {message['type']}\ndata: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    yield f": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            sse_manager.unsubscribe(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@frontend_router.get("/sse/status", tags=["frontend"])
async def sse_status():
    """Get SSE stream status."""
    return {
        "active_subscribers": sse_manager.subscriber_count,
        "status": "active",
    }


# ---------------------------------------------------------------------------
# Interactive WebSocket App
# ---------------------------------------------------------------------------

class AppConnectionManager:
    """Manages interactive app WebSocket connections."""

    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self._connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        disconnected = []
        for conn in self._connections:
            try:
                await conn.send_json(message)
            except Exception:
                disconnected.append(conn)
        for conn in disconnected:
            self._connections.remove(conn)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


app_ws_manager = AppConnectionManager()


@frontend_router.websocket("/ws/app")
async def app_websocket(websocket: WebSocket):
    """
    🖥️ Interactive app WebSocket endpoint.

    Bidirectional communication for:
    - Submitting tasks in real-time
    - Receiving live agent updates
    - Interactive pipeline control
    - Project collaboration

    Commands:
    - {"action": "submit_task", "task_type": "...", "payload": {...}}
    - {"action": "get_status"}
    - {"action": "subscribe", "channels": ["tasks", "agents", "pipeline"]}
    - {"action": "ping"}
    """
    await app_ws_manager.connect(websocket)
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "welcome",
            "glyph": "⌬",
            "message": "Connected to Spatium Computationis Interactive Console",
            "connections": app_ws_manager.connection_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        while True:
            data = await websocket.receive_json()
            action = data.get("action", "")

            if action == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif action == "get_status":
                await websocket.send_json({
                    "type": "status",
                    "data": {
                        "connections": app_ws_manager.connection_count,
                        "sse_subscribers": sse_manager.subscriber_count,
                        "system": "active",
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            elif action == "submit_task":
                # Forward to task queue
                from ..platform import submit_task, TaskPriority
                task = submit_task(
                    task_type=data.get("task_type", "general"),
                    payload=data.get("payload", {}),
                    priority=TaskPriority(data.get("priority", 3)),
                    submitted_by=data.get("submitted_by", "interactive_app"),
                    project_id=data.get("project_id"),
                )
                response = {
                    "type": "task_submitted",
                    "data": task.model_dump(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await websocket.send_json(response)
                # Broadcast to SSE
                await sse_manager.broadcast("task_submitted", task.model_dump())

            elif action == "subscribe":
                channels = data.get("channels", [])
                await websocket.send_json({
                    "type": "subscribed",
                    "channels": channels,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown action: {action}",
                    "available_actions": [
                        "ping", "get_status", "submit_task", "subscribe",
                    ],
                })

    except WebSocketDisconnect:
        app_ws_manager.disconnect(websocket)
    except Exception:
        app_ws_manager.disconnect(websocket)
