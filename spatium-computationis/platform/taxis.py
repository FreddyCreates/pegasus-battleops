"""
Point-to-Point Transport — Taxis  🚕

Direct request/response transport for moving data between specific endpoints.
Unlike buses (one-to-many), taxis deliver payloads point-to-point: one sender,
one receiver, with guaranteed delivery tracking and response routing.

Use cases:
- Agent-to-agent direct requests (bypass queue for low-latency)
- Synchronous request/response between components
- Data shuttle between layers (field → platform → agent)
- Streaming data delivery with receipt confirmation

Glyph: 🚕 — taxi (one passenger, direct route)
"""

from __future__ import annotations

import asyncio
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

class TaxiStatus(str, Enum):
    """Status of a taxi delivery."""
    DISPATCHED = "dispatched"      # Sent, awaiting pickup
    IN_TRANSIT = "in_transit"      # Being processed by receiver
    DELIVERED = "delivered"        # Successfully delivered and acknowledged
    RETURNED = "returned"         # Response sent back to sender
    LOST = "lost"                 # Delivery failed (timeout/error)
    CANCELLED = "cancelled"       # Sender cancelled


class TaxiPriority(str, Enum):
    """Delivery priority."""
    ECONOMY = "economy"           # Best effort, no rush
    STANDARD = "standard"         # Normal priority
    EXPRESS = "express"           # Fast delivery
    URGENT = "urgent"            # Immediate, interrupt if needed


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class TaxiRequest(BaseModel):
    """A point-to-point delivery request."""
    taxi_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Routing
    sender: str
    receiver: str
    route: str  # Logical route name (e.g., "estimate.request", "field.sync")

    # Payload
    payload: dict[str, Any] = Field(default_factory=dict)
    expects_response: bool = True  # Whether sender is waiting for a response

    # Configuration
    priority: TaxiPriority = TaxiPriority.STANDARD
    timeout_seconds: float = 30.0
    retry_count: int = 0
    max_retries: int = 3

    # Tracking
    status: TaxiStatus = TaxiStatus.DISPATCHED
    correlation_id: str | None = None
    dispatched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: datetime | None = None

    # Metadata
    tags: list[str] = Field(default_factory=list)


class TaxiResponse(BaseModel):
    """Response from a taxi delivery."""
    taxi_id: str
    sender: str
    receiver: str
    route: str

    # Response
    success: bool
    response_payload: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

    # Timing
    dispatched_at: datetime
    delivered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    round_trip_ms: float = 0.0


class TaxiMetrics(BaseModel):
    """Metrics for the taxi transport system."""
    total_dispatched: int = 0
    total_delivered: int = 0
    total_lost: int = 0
    total_cancelled: int = 0
    active_in_transit: int = 0

    # Performance
    avg_delivery_ms: float = 0.0
    p95_delivery_ms: float = 0.0
    deliveries_per_route: dict[str, int] = Field(default_factory=dict)

    # Reliability
    delivery_success_rate: float = 1.0
    retry_rate: float = 0.0


class TaxiRoute(BaseModel):
    """A registered taxi route between components."""
    route_name: str
    description: str = ""
    sender_pattern: str = "*"   # Who can send on this route
    receiver: str               # Who receives
    handler_registered: bool = False

    # Stats
    total_trips: int = 0
    avg_response_ms: float = 0.0
    last_used_at: datetime | None = None


# ---------------------------------------------------------------------------
# Taxi Dispatcher Implementation
# ---------------------------------------------------------------------------

# Handler type: receives payload, returns response payload
TaxiHandler = Callable[[dict[str, Any], TaxiRequest], Awaitable[dict[str, Any]]]


class TaxiDispatcher:
    """
    Point-to-point transport dispatcher.

    Manages direct request/response communication between components:
    - Register handlers for specific routes/receivers
    - Dispatch requests with timeout and retry
    - Track delivery metrics
    - Support for synchronous (await response) and fire-and-forget patterns
    """

    def __init__(self):
        self._handlers: dict[str, TaxiHandler] = {}  # route -> handler
        self._receiver_handlers: dict[str, dict[str, TaxiHandler]] = defaultdict(dict)  # receiver -> route -> handler
        self._routes: dict[str, TaxiRoute] = {}
        self._in_flight: dict[str, TaxiRequest] = {}
        self._history: list[TaxiResponse] = []
        self._delivery_times: list[float] = []
        self._metrics = TaxiMetrics()

    def register_route(
        self,
        route_name: str,
        receiver: str,
        handler: TaxiHandler,
        description: str = "",
        sender_pattern: str = "*",
    ) -> TaxiRoute:
        """
        Register a handler for a specific route.

        The handler will be called when a taxi is dispatched to this route/receiver.
        """
        route = TaxiRoute(
            route_name=route_name,
            description=description,
            sender_pattern=sender_pattern,
            receiver=receiver,
            handler_registered=True,
        )
        self._routes[route_name] = route
        self._receiver_handlers[receiver][route_name] = handler
        self._handlers[f"{receiver}:{route_name}"] = handler
        return route

    def unregister_route(self, route_name: str, receiver: str) -> bool:
        """Unregister a route handler."""
        key = f"{receiver}:{route_name}"
        if key in self._handlers:
            del self._handlers[key]
            if receiver in self._receiver_handlers:
                self._receiver_handlers[receiver].pop(route_name, None)
            if route_name in self._routes:
                self._routes[route_name].handler_registered = False
            return True
        return False

    async def dispatch(self, request: TaxiRequest) -> TaxiResponse:
        """
        Dispatch a taxi request and await response.

        Handles routing, timeout, and retry logic.
        """
        self._in_flight[request.taxi_id] = request
        self._metrics.total_dispatched += 1
        self._metrics.active_in_transit += 1

        start_time = time.perf_counter()

        while True:
            try:
                # Find handler
                handler = self._find_handler(request)
                if not handler:
                    raise ValueError(
                        f"No handler registered for route '{request.route}' "
                        f"to receiver '{request.receiver}'"
                    )

                # Check sender authorization
                route = self._routes.get(request.route)
                if route and route.sender_pattern != "*":
                    if not self._sender_authorized(request.sender, route.sender_pattern):
                        raise PermissionError(
                            f"Sender '{request.sender}' not authorized for route '{request.route}'"
                        )

                # Execute with timeout
                request.status = TaxiStatus.IN_TRANSIT
                response_payload = await asyncio.wait_for(
                    handler(request.payload, request),
                    timeout=request.timeout_seconds,
                )

                # Success
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                request.status = TaxiStatus.DELIVERED
                request.delivered_at = datetime.now(timezone.utc)

                response = TaxiResponse(
                    taxi_id=request.taxi_id,
                    sender=request.sender,
                    receiver=request.receiver,
                    route=request.route,
                    success=True,
                    response_payload=response_payload,
                    dispatched_at=request.dispatched_at,
                    round_trip_ms=elapsed_ms,
                )

                self._record_success(request, response, elapsed_ms)
                return response

            except asyncio.TimeoutError:
                return await self._handle_failure(
                    request, start_time, "Delivery timeout exceeded"
                )
            except PermissionError as e:
                return await self._handle_failure(request, start_time, str(e))
            except Exception as e:
                # Retry logic (loop-based to avoid stack growth)
                if request.retry_count < request.max_retries:
                    request.retry_count += 1
                    request.status = TaxiStatus.DISPATCHED
                    continue
                return await self._handle_failure(request, start_time, str(e))
            finally:
                self._in_flight.pop(request.taxi_id, None)

    async def dispatch_fire_and_forget(self, request: TaxiRequest) -> str:
        """
        Dispatch without waiting for response. Returns taxi_id for tracking.
        """
        request.expects_response = False
        asyncio.create_task(self._dispatch_background(request))
        return request.taxi_id

    async def _dispatch_background(self, request: TaxiRequest) -> None:
        """Background dispatch for fire-and-forget."""
        try:
            await self.dispatch(request)
        except Exception:
            pass  # Fire and forget — failures are logged in metrics

    def cancel(self, taxi_id: str) -> bool:
        """Cancel an in-flight taxi request."""
        if taxi_id in self._in_flight:
            self._in_flight[taxi_id].status = TaxiStatus.CANCELLED
            self._metrics.total_cancelled += 1
            self._metrics.active_in_transit = max(0, self._metrics.active_in_transit - 1)
            return True
        return False

    def get_routes(self) -> list[TaxiRoute]:
        """List all registered routes."""
        return list(self._routes.values())

    def get_route(self, route_name: str) -> TaxiRoute | None:
        """Get a specific route."""
        return self._routes.get(route_name)

    def get_metrics(self) -> TaxiMetrics:
        """Get taxi transport metrics."""
        total = self._metrics.total_delivered + self._metrics.total_lost
        if total > 0:
            self._metrics.delivery_success_rate = self._metrics.total_delivered / total
        return self._metrics

    def get_history(self, route: str | None = None, limit: int = 50) -> list[TaxiResponse]:
        """Get recent delivery history."""
        history = self._history
        if route:
            history = [r for r in history if r.route == route]
        return history[-limit:]

    def get_in_flight(self) -> list[TaxiRequest]:
        """Get currently in-flight requests."""
        return list(self._in_flight.values())

    def _find_handler(self, request: TaxiRequest) -> TaxiHandler | None:
        """Find the appropriate handler for a request."""
        # First try exact match: receiver + route
        key = f"{request.receiver}:{request.route}"
        if key in self._handlers:
            return self._handlers[key]

        # Then try just receiver with any route
        if request.receiver in self._receiver_handlers:
            handlers = self._receiver_handlers[request.receiver]
            if request.route in handlers:
                return handlers[request.route]
            # Check wildcard
            if "*" in handlers:
                return handlers["*"]

        return None

    @staticmethod
    def _sender_authorized(sender: str, pattern: str) -> bool:
        """Check if a sender matches the authorization pattern."""
        if pattern == "*":
            return True
        # Support comma-separated list
        allowed = [s.strip() for s in pattern.split(",")]
        return sender in allowed

    def _record_success(self, request: TaxiRequest, response: TaxiResponse, elapsed_ms: float) -> None:
        """Record a successful delivery."""
        self._metrics.total_delivered += 1
        self._metrics.active_in_transit = max(0, self._metrics.active_in_transit - 1)

        # Update timing stats
        self._delivery_times.append(elapsed_ms)
        if len(self._delivery_times) > 1000:
            self._delivery_times = self._delivery_times[-1000:]

        self._metrics.avg_delivery_ms = sum(self._delivery_times) / len(self._delivery_times)
        sorted_times = sorted(self._delivery_times)
        p95_idx = int(len(sorted_times) * 0.95)
        self._metrics.p95_delivery_ms = sorted_times[min(p95_idx, len(sorted_times) - 1)]

        # Update route stats
        route_name = request.route
        self._metrics.deliveries_per_route[route_name] = (
            self._metrics.deliveries_per_route.get(route_name, 0) + 1
        )
        if route_name in self._routes:
            self._routes[route_name].total_trips += 1
            self._routes[route_name].last_used_at = datetime.now(timezone.utc)
            # Running average for route
            route = self._routes[route_name]
            route.avg_response_ms = (
                (route.avg_response_ms * (route.total_trips - 1) + elapsed_ms)
                / route.total_trips
            )

        # Store in history
        self._history.append(response)
        if len(self._history) > 1000:
            self._history = self._history[-1000:]

    async def _handle_failure(
        self, request: TaxiRequest, start_time: float, error: str
    ) -> TaxiResponse:
        """Handle a failed delivery."""
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        request.status = TaxiStatus.LOST
        self._metrics.total_lost += 1
        self._metrics.active_in_transit = max(0, self._metrics.active_in_transit - 1)

        response = TaxiResponse(
            taxi_id=request.taxi_id,
            sender=request.sender,
            receiver=request.receiver,
            route=request.route,
            success=False,
            error=error,
            dispatched_at=request.dispatched_at,
            round_trip_ms=elapsed_ms,
        )

        self._history.append(response)
        if len(self._history) > 1000:
            self._history = self._history[-1000:]

        return response


# ---------------------------------------------------------------------------
# Global Instance & Convenience Functions
# ---------------------------------------------------------------------------

_global_dispatcher: TaxiDispatcher | None = None


def _get_dispatcher() -> TaxiDispatcher:
    global _global_dispatcher
    if _global_dispatcher is None:
        _global_dispatcher = TaxiDispatcher()
    return _global_dispatcher


def register_taxi_route(
    route_name: str,
    receiver: str,
    handler: TaxiHandler,
    description: str = "",
    sender_pattern: str = "*",
) -> TaxiRoute:
    """Register a taxi route handler."""
    return _get_dispatcher().register_route(
        route_name=route_name,
        receiver=receiver,
        handler=handler,
        description=description,
        sender_pattern=sender_pattern,
    )


def unregister_taxi_route(route_name: str, receiver: str) -> bool:
    """Unregister a taxi route."""
    return _get_dispatcher().unregister_route(route_name, receiver)


async def dispatch_taxi(
    sender: str,
    receiver: str,
    route: str,
    payload: dict[str, Any] | None = None,
    priority: TaxiPriority = TaxiPriority.STANDARD,
    timeout_seconds: float = 30.0,
    correlation_id: str | None = None,
    tags: list[str] | None = None,
) -> TaxiResponse:
    """Dispatch a taxi request and await response."""
    request = TaxiRequest(
        sender=sender,
        receiver=receiver,
        route=route,
        payload=payload or {},
        priority=priority,
        timeout_seconds=timeout_seconds,
        correlation_id=correlation_id,
        tags=tags or [],
    )
    return await _get_dispatcher().dispatch(request)


async def dispatch_taxi_async(
    sender: str,
    receiver: str,
    route: str,
    payload: dict[str, Any] | None = None,
    priority: TaxiPriority = TaxiPriority.STANDARD,
    timeout_seconds: float = 30.0,
    correlation_id: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Dispatch a taxi request without waiting (fire-and-forget). Returns taxi_id."""
    request = TaxiRequest(
        sender=sender,
        receiver=receiver,
        route=route,
        payload=payload or {},
        expects_response=False,
        priority=priority,
        timeout_seconds=timeout_seconds,
        correlation_id=correlation_id,
        tags=tags or [],
    )
    return await _get_dispatcher().dispatch_fire_and_forget(request)


def cancel_taxi(taxi_id: str) -> bool:
    """Cancel an in-flight taxi."""
    return _get_dispatcher().cancel(taxi_id)


def get_taxi_routes() -> list[TaxiRoute]:
    """List all registered taxi routes."""
    return _get_dispatcher().get_routes()


def get_taxi_route(route_name: str) -> TaxiRoute | None:
    """Get a specific taxi route."""
    return _get_dispatcher().get_route(route_name)


def get_taxi_metrics() -> TaxiMetrics:
    """Get taxi transport metrics."""
    return _get_dispatcher().get_metrics()


def get_taxi_history(route: str | None = None, limit: int = 50) -> list[TaxiResponse]:
    """Get recent delivery history."""
    return _get_dispatcher().get_history(route=route, limit=limit)


def get_taxis_in_flight() -> list[TaxiRequest]:
    """Get currently in-flight taxi requests."""
    return _get_dispatcher().get_in_flight()
