"""
API Layers — Strata  📐

Defines the architectural layers of the internal API and provides
middleware, routing tiers, and layer-aware request processing.

The layer system organizes the platform into clear tiers:

    ┌─────────────────────────────────────────────┐
    │  Layer 4: Interface (API endpoints, UI)     │
    ├─────────────────────────────────────────────┤
    │  Layer 3: Orchestration (pipelines, flows)  │
    ├─────────────────────────────────────────────┤
    │  Layer 2: Service (agents, bots)            │
    ├─────────────────────────────────────────────┤
    │  Layer 1: Transport (buses, taxis)          │
    ├─────────────────────────────────────────────┤
    │  Layer 0: Foundation (storage, config)      │
    └─────────────────────────────────────────────┘

Each layer has defined responsibilities, access rules, and communication patterns.

Glyph: 📐 — layers (structured tiers)
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class LayerLevel(int, Enum):
    """Platform layer levels."""
    FOUNDATION = 0     # Storage, config, secrets, environment
    TRANSPORT = 1      # Buses, taxis, message queues
    SERVICE = 2        # Agents, bots, capabilities
    ORCHESTRATION = 3  # Pipelines, workflows, delegation
    INTERFACE = 4      # API endpoints, WebSocket, UI


class LayerAccessRule(str, Enum):
    """Rules for cross-layer communication."""
    ALLOW = "allow"               # Communication permitted
    ALLOW_DOWN = "allow_down"     # Can call layers below
    ALLOW_UP_EVENT = "allow_up_event"  # Can send events upward (bus only)
    DENY = "deny"                 # Communication blocked
    AUDIT = "audit"               # Allowed but logged for review


class RequestPhase(str, Enum):
    """Phase of request processing through layers."""
    INGRESS = "ingress"           # Entering the layer
    PROCESSING = "processing"    # Being processed in the layer
    EGRESS = "egress"            # Leaving the layer
    COMPLETE = "complete"        # Finished


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Layer(BaseModel):
    """Definition of a platform layer."""
    level: LayerLevel
    name: str
    glyph: str
    description: str
    
    # Components in this layer
    components: list[str] = Field(default_factory=list)
    
    # Access rules: which layers this one can communicate with
    can_access: list[int] = Field(default_factory=list)  # Layer levels
    
    # Middleware stack for this layer
    middleware: list[str] = Field(default_factory=list)
    
    # Metrics
    requests_processed: int = 0
    avg_latency_ms: float = 0.0
    error_count: int = 0
    last_activity: datetime | None = None


class LayerRequest(BaseModel):
    """A request traversing through layers."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Routing
    source_layer: LayerLevel
    target_layer: LayerLevel
    source_component: str
    target_component: str
    
    # Payload
    operation: str
    payload: dict[str, Any] = Field(default_factory=dict)
    
    # Tracking
    phase: RequestPhase = RequestPhase.INGRESS
    correlation_id: str | None = None
    trace: list[dict[str, Any]] = Field(default_factory=list)
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class LayerResponse(BaseModel):
    """Response from layer processing."""
    request_id: str
    success: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    
    # Trace of layers traversed
    layers_traversed: list[str] = Field(default_factory=list)
    total_latency_ms: float = 0.0


class LayerMetrics(BaseModel):
    """Metrics for the layer system."""
    layers: dict[str, dict[str, Any]] = Field(default_factory=dict)
    total_requests: int = 0
    cross_layer_calls: int = 0
    access_violations: int = 0
    avg_request_latency_ms: float = 0.0
    layer_health: dict[str, bool] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# Middleware type: takes request and next handler, returns response
MiddlewareHandler = Callable[[LayerRequest, Callable], Awaitable[LayerResponse]]


class LayerMiddleware:
    """Base class for layer middleware."""

    def __init__(self, name: str):
        self.name = name

    async def process(
        self, request: LayerRequest, next_handler: Callable
    ) -> LayerResponse:
        """Process request through this middleware, then call next."""
        return await next_handler(request)


class AccessControlMiddleware(LayerMiddleware):
    """Enforces cross-layer access rules."""

    def __init__(self):
        super().__init__("access_control")
        self._violations: list[dict[str, Any]] = []

    async def process(
        self, request: LayerRequest, next_handler: Callable
    ) -> LayerResponse:
        # Rule: layers can access their own level or below (except via bus events)
        if request.target_layer.value > request.source_layer.value:
            # Upward call — only allowed for specific patterns
            violation = {
                "request_id": request.request_id,
                "source": f"{request.source_layer.name}:{request.source_component}",
                "target": f"{request.target_layer.name}:{request.target_component}",
                "operation": request.operation,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._violations.append(violation)

            return LayerResponse(
                request_id=request.request_id,
                success=False,
                error=(
                    f"Access denied: {request.source_layer.name} (L{request.source_layer.value}) "
                    f"cannot directly call {request.target_layer.name} (L{request.target_layer.value}). "
                    f"Use event bus for upward communication."
                ),
            )

        return await next_handler(request)

    def get_violations(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._violations[-limit:]


class TracingMiddleware(LayerMiddleware):
    """Adds trace information to requests."""

    def __init__(self):
        super().__init__("tracing")

    async def process(
        self, request: LayerRequest, next_handler: Callable
    ) -> LayerResponse:
        # Add trace entry
        trace_entry = {
            "layer": request.target_layer.name,
            "component": request.target_component,
            "operation": request.operation,
            "phase": "enter",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        request.trace.append(trace_entry)

        response = await next_handler(request)

        # Add exit trace
        request.trace.append({
            **trace_entry,
            "phase": "exit",
            "success": response.success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return response


class RateLimitMiddleware(LayerMiddleware):
    """Rate limits requests per source component."""

    def __init__(self, max_requests_per_second: int = 100):
        super().__init__("rate_limit")
        self._max_rps = max_requests_per_second
        self._counters: dict[str, list[float]] = defaultdict(list)

    async def process(
        self, request: LayerRequest, next_handler: Callable
    ) -> LayerResponse:
        now = time.time()
        key = request.source_component

        # Clean old entries (older than 1 second)
        self._counters[key] = [t for t in self._counters[key] if now - t < 1.0]

        if len(self._counters[key]) >= self._max_rps:
            return LayerResponse(
                request_id=request.request_id,
                success=False,
                error=f"Rate limit exceeded for '{key}': {self._max_rps} req/s",
            )

        self._counters[key].append(now)
        return await next_handler(request)


# ---------------------------------------------------------------------------
# Layer Registry & Manager
# ---------------------------------------------------------------------------

class LayerManager:
    """
    Manages the layer architecture.

    Responsibilities:
    - Define and track layers
    - Enforce access rules between layers
    - Apply middleware stacks
    - Route requests between layers
    - Collect metrics per layer
    """

    def __init__(self):
        self._layers: dict[LayerLevel, Layer] = {}
        self._middleware_stack: list[LayerMiddleware] = []
        self._handlers: dict[str, Callable] = {}  # component -> handler
        self._metrics = LayerMetrics()
        self._request_times: list[float] = []
        self._initialize_default_layers()
        self._initialize_default_middleware()

    def _initialize_default_layers(self) -> None:
        """Set up the default layer architecture."""
        self._layers[LayerLevel.FOUNDATION] = Layer(
            level=LayerLevel.FOUNDATION,
            name="Foundation",
            glyph="⬡",
            description="Storage, configuration, secrets, and environment management",
            components=["sqlite_store", "config_manager", "secrets_vault", "env_loader"],
            can_access=[0],  # Can only access itself
            middleware=["tracing"],
        )

        self._layers[LayerLevel.TRANSPORT] = Layer(
            level=LayerLevel.TRANSPORT,
            name="Transport",
            glyph="⇌",
            description="Event buses, taxi dispatch, message queues, and data routing",
            components=["event_bus", "taxi_dispatcher", "task_queue", "message_router"],
            can_access=[0, 1],  # Foundation + self
            middleware=["tracing", "rate_limit"],
        )

        self._layers[LayerLevel.SERVICE] = Layer(
            level=LayerLevel.SERVICE,
            name="Service",
            glyph="⎈",
            description="Agent execution, bot layer, capability registry, and delegation",
            components=["agent_registry", "bot_layer", "delegation_engine", "scaffold_manager"],
            can_access=[0, 1, 2],  # Foundation + Transport + self
            middleware=["access_control", "tracing", "rate_limit"],
        )

        self._layers[LayerLevel.ORCHESTRATION] = Layer(
            level=LayerLevel.ORCHESTRATION,
            name="Orchestration",
            glyph="⌬",
            description="Intelligence pipeline, protocol execution, workflow coordination",
            components=["pipeline_engine", "protocol_runner", "workflow_coordinator", "feedback_loop"],
            can_access=[0, 1, 2, 3],  # All below + self
            middleware=["access_control", "tracing"],
        )

        self._layers[LayerLevel.INTERFACE] = Layer(
            level=LayerLevel.INTERFACE,
            name="Interface",
            glyph="◈",
            description="HTTP API, WebSocket, SSE streams, frontend, and external integrations",
            components=["rest_api", "websocket_server", "sse_stream", "frontend_app", "webhook_handler"],
            can_access=[0, 1, 2, 3, 4],  # All layers
            middleware=["tracing", "rate_limit"],
        )

    def _initialize_default_middleware(self) -> None:
        """Set up the default middleware stack."""
        self._middleware_stack = [
            TracingMiddleware(),
            AccessControlMiddleware(),
            RateLimitMiddleware(max_requests_per_second=200),
        ]

    def get_layer(self, level: LayerLevel) -> Layer:
        """Get a layer by level."""
        return self._layers[level]

    def get_all_layers(self) -> list[Layer]:
        """Get all layers ordered by level."""
        return [self._layers[level] for level in sorted(self._layers.keys(), key=lambda l: l.value)]

    def register_handler(self, component: str, handler: Callable) -> None:
        """Register a request handler for a component."""
        self._handlers[component] = handler

    async def route_request(self, request: LayerRequest) -> LayerResponse:
        """
        Route a request through the layer system.

        Applies middleware stack and delivers to the target component.
        """
        start_time = time.perf_counter()
        self._metrics.total_requests += 1

        if request.source_layer != request.target_layer:
            self._metrics.cross_layer_calls += 1

        # Build middleware chain
        async def final_handler(req: LayerRequest) -> LayerResponse:
            handler = self._handlers.get(req.target_component)
            if handler:
                try:
                    result = await handler(req.payload)
                    return LayerResponse(
                        request_id=req.request_id,
                        success=True,
                        result=result if isinstance(result, dict) else {"result": result},
                        layers_traversed=[req.target_layer.name],
                    )
                except Exception as e:
                    return LayerResponse(
                        request_id=req.request_id,
                        success=False,
                        error=str(e),
                        layers_traversed=[req.target_layer.name],
                    )
            else:
                return LayerResponse(
                    request_id=req.request_id,
                    success=False,
                    error=f"No handler registered for component '{req.target_component}'",
                    layers_traversed=[req.target_layer.name],
                )

        # Apply middleware (reverse order so first in list runs first)
        chain = final_handler
        for mw in reversed(self._middleware_stack):
            def _wrap(middleware, next_h):
                async def handler(req):
                    return await middleware.process(req, next_h)
                return handler
            chain = _wrap(mw, chain)

        # Execute
        response = await chain(request)

        # Update metrics
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        response.total_latency_ms = elapsed_ms

        self._request_times.append(elapsed_ms)
        if len(self._request_times) > 1000:
            self._request_times = self._request_times[-1000:]
        self._metrics.avg_request_latency_ms = sum(self._request_times) / len(self._request_times)

        # Update layer stats
        target_layer = self._layers.get(request.target_layer)
        if target_layer:
            target_layer.requests_processed += 1
            target_layer.last_activity = datetime.now(timezone.utc)
            if not response.success:
                target_layer.error_count += 1

        if not response.success and "Access denied" in (response.error or ""):
            self._metrics.access_violations += 1

        return response

    def get_metrics(self) -> LayerMetrics:
        """Get comprehensive layer metrics."""
        layer_data = {}
        health = {}

        for level, layer in self._layers.items():
            layer_data[layer.name] = {
                "level": level.value,
                "glyph": layer.glyph,
                "components": layer.components,
                "requests_processed": layer.requests_processed,
                "avg_latency_ms": layer.avg_latency_ms,
                "error_count": layer.error_count,
                "last_activity": layer.last_activity.isoformat() if layer.last_activity else None,
            }
            # Layer is healthy if error rate is below 10%
            total = layer.requests_processed
            error_rate = layer.error_count / max(total, 1)
            health[layer.name] = error_rate < 0.1

        self._metrics.layers = layer_data
        self._metrics.layer_health = health
        return self._metrics

    def get_layer_topology(self) -> dict[str, Any]:
        """Get the layer topology for visualization."""
        topology = {
            "layers": [],
            "connections": [],
        }

        for level in sorted(self._layers.keys(), key=lambda l: l.value, reverse=True):
            layer = self._layers[level]
            topology["layers"].append({
                "level": level.value,
                "name": layer.name,
                "glyph": layer.glyph,
                "description": layer.description,
                "components": layer.components,
            })

            # Add connections
            for target_level in layer.can_access:
                if target_level != level.value:
                    topology["connections"].append({
                        "from_layer": layer.name,
                        "from_level": level.value,
                        "to_layer": self._layers[LayerLevel(target_level)].name,
                        "to_level": target_level,
                        "direction": "down" if target_level < level.value else "lateral",
                    })

        return topology


# ---------------------------------------------------------------------------
# Global Instance & Convenience Functions
# ---------------------------------------------------------------------------

_global_manager: LayerManager | None = None


def _get_manager() -> LayerManager:
    global _global_manager
    if _global_manager is None:
        _global_manager = LayerManager()
    return _global_manager


def get_layer(level: LayerLevel) -> Layer:
    """Get a layer by level."""
    return _get_manager().get_layer(level)


def get_all_layers() -> list[Layer]:
    """Get all layers ordered by level."""
    return _get_manager().get_all_layers()


def register_layer_handler(component: str, handler: Callable) -> None:
    """Register a handler for a component."""
    _get_manager().register_handler(component, handler)


async def route_layer_request(
    source_layer: LayerLevel,
    target_layer: LayerLevel,
    source_component: str,
    target_component: str,
    operation: str,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> LayerResponse:
    """Route a request through the layer system."""
    request = LayerRequest(
        source_layer=source_layer,
        target_layer=target_layer,
        source_component=source_component,
        target_component=target_component,
        operation=operation,
        payload=payload or {},
        correlation_id=correlation_id,
    )
    return await _get_manager().route_request(request)


def get_layer_metrics() -> LayerMetrics:
    """Get layer system metrics."""
    return _get_manager().get_metrics()


def get_layer_topology() -> dict[str, Any]:
    """Get layer topology for visualization."""
    return _get_manager().get_layer_topology()
