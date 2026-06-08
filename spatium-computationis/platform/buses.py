"""
Internal Event Bus — Viae Communes  🚌

Pub/sub event buses for broadcast messaging between agents and platform components.
Buses enable one-to-many communication: a publisher emits an event to a topic,
and all subscribers on that topic receive it.

Use cases:
- Agent state change notifications
- Task lifecycle events (submitted, completed, failed)
- Defense alerts broadcast
- Field update propagation
- System-wide announcements

Glyph: 🚌 — event bus (many riders, shared route)
"""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class BusTopic(str, Enum):
    """Pre-defined event bus topics."""

    # Agent lifecycle
    AGENT_REGISTERED = "agent.registered"
    AGENT_STATE_CHANGED = "agent.state_changed"
    AGENT_HEARTBEAT = "agent.heartbeat"

    # Task lifecycle
    TASK_SUBMITTED = "task.submitted"
    TASK_CLAIMED = "task.claimed"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_RETRIED = "task.retried"

    # Delegation
    DELEGATION_SUBMITTED = "delegation.submitted"
    DELEGATION_COMPLETED = "delegation.completed"
    DELEGATION_FAILED = "delegation.failed"

    # Defense / Security
    DEFENSE_THREAT_DETECTED = "defense.threat_detected"
    DEFENSE_ALERT = "defense.alert"
    DEFENSE_BLOCKED = "defense.blocked"

    # Field
    FIELD_UPDATE_RECEIVED = "field.update_received"
    FIELD_ISSUE_FLAGGED = "field.issue_flagged"

    # Platform
    PLATFORM_HEALTH_CHECK = "platform.health_check"
    PLATFORM_SCALING = "platform.scaling"

    # Custom (wildcard topics)
    CUSTOM = "custom"


class EventPriority(str, Enum):
    """Priority levels for bus events."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class BusEvent(BaseModel):
    """An event published to a bus topic."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    source: str  # Who published this event
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: str | None = None
    published_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Metadata
    tags: list[str] = Field(default_factory=list)
    ttl_seconds: int | None = None  # Event expires after this many seconds


class Subscription(BaseModel):
    """A subscription to a bus topic."""
    subscription_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subscriber: str  # Who is subscribed
    topic_pattern: str  # Topic or pattern (supports * wildcard)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True

    # Filtering
    min_priority: EventPriority = EventPriority.LOW
    source_filter: str | None = None  # Only events from this source


class BusMetrics(BaseModel):
    """Metrics for the event bus system."""
    total_events_published: int = 0
    total_events_delivered: int = 0
    total_subscriptions: int = 0
    active_subscriptions: int = 0
    events_per_topic: dict[str, int] = Field(default_factory=dict)
    dead_letter_count: int = 0
    avg_delivery_time_ms: float = 0.0
    last_event_at: datetime | None = None


# ---------------------------------------------------------------------------
# Event Bus Implementation
# ---------------------------------------------------------------------------

# Subscriber handler type
EventHandler = Callable[[BusEvent], Awaitable[None]]

# Priority ordering
_PRIORITY_ORDER = {
    EventPriority.LOW: 0,
    EventPriority.NORMAL: 1,
    EventPriority.HIGH: 2,
    EventPriority.CRITICAL: 3,
}


class EventBus:
    """
    Internal event bus for pub/sub messaging.

    Supports:
    - Topic-based subscriptions
    - Wildcard patterns (e.g., "task.*" matches "task.submitted", "task.completed")
    - Priority-based filtering
    - Source filtering
    - Event history (ring buffer)
    - Dead letter queue for failed deliveries
    """

    def __init__(self, history_size: int = 1000):
        self._subscriptions: dict[str, list[tuple[Subscription, EventHandler]]] = defaultdict(list)
        self._history: list[BusEvent] = []
        self._history_size = history_size
        self._dead_letter: list[tuple[BusEvent, str]] = []  # (event, error)
        self._metrics = BusMetrics()
        self._lock = asyncio.Lock()

    async def publish(self, event: BusEvent) -> int:
        """
        Publish an event to the bus.

        Returns the number of subscribers that received the event.
        """
        delivered = 0

        # Find matching subscriptions
        handlers = self._match_subscriptions(event)

        for subscription, handler in handlers:
            # Check priority filter
            if _PRIORITY_ORDER[event.priority] < _PRIORITY_ORDER[subscription.min_priority]:
                continue

            # Check source filter
            if subscription.source_filter and event.source != subscription.source_filter:
                continue

            try:
                await handler(event)
                delivered += 1
            except Exception as e:
                self._dead_letter.append((event, f"{subscription.subscriber}: {str(e)}"))
                self._metrics.dead_letter_count += 1

        # Update metrics
        self._metrics.total_events_published += 1
        self._metrics.total_events_delivered += delivered
        self._metrics.last_event_at = event.published_at
        self._metrics.events_per_topic[event.topic] = (
            self._metrics.events_per_topic.get(event.topic, 0) + 1
        )

        # Store in history
        self._history.append(event)
        if len(self._history) > self._history_size:
            self._history = self._history[-self._history_size:]

        return delivered

    def subscribe(
        self,
        subscriber: str,
        topic_pattern: str,
        handler: EventHandler,
        min_priority: EventPriority = EventPriority.LOW,
        source_filter: str | None = None,
    ) -> Subscription:
        """
        Subscribe to events matching a topic pattern.

        Patterns:
        - Exact match: "task.completed"
        - Wildcard: "task.*" matches any task event
        - All: "*" matches everything
        """
        subscription = Subscription(
            subscriber=subscriber,
            topic_pattern=topic_pattern,
            min_priority=min_priority,
            source_filter=source_filter,
        )

        self._subscriptions[topic_pattern].append((subscription, handler))
        self._metrics.total_subscriptions += 1
        self._metrics.active_subscriptions += 1

        return subscription

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription by ID."""
        for pattern, subs in self._subscriptions.items():
            for i, (sub, _handler) in enumerate(subs):
                if sub.subscription_id == subscription_id:
                    subs.pop(i)
                    self._metrics.active_subscriptions -= 1
                    return True
        return False

    def get_history(
        self,
        topic: str | None = None,
        source: str | None = None,
        limit: int = 50,
    ) -> list[BusEvent]:
        """Get recent event history, optionally filtered."""
        events = self._history

        if topic:
            events = [e for e in events if self._topic_matches(e.topic, topic)]
        if source:
            events = [e for e in events if e.source == source]

        return events[-limit:]

    def get_metrics(self) -> BusMetrics:
        """Get bus metrics."""
        return self._metrics

    def get_dead_letter_queue(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get events that failed delivery."""
        return [
            {"event": event.model_dump(), "error": error}
            for event, error in self._dead_letter[-limit:]
        ]

    def list_subscriptions(self, subscriber: str | None = None) -> list[Subscription]:
        """List all active subscriptions, optionally filtered by subscriber."""
        subs = []
        for _pattern, items in self._subscriptions.items():
            for sub, _handler in items:
                if sub.active and (subscriber is None or sub.subscriber == subscriber):
                    subs.append(sub)
        return subs

    def _match_subscriptions(self, event: BusEvent) -> list[tuple[Subscription, EventHandler]]:
        """Find all subscriptions matching an event's topic."""
        matched = []

        for pattern, subs in self._subscriptions.items():
            if self._topic_matches(event.topic, pattern):
                for sub, handler in subs:
                    if sub.active:
                        matched.append((sub, handler))

        return matched

    @staticmethod
    def _topic_matches(topic: str, pattern: str) -> bool:
        """Check if a topic matches a pattern (supports * wildcard)."""
        if pattern == "*":
            return True
        if "*" not in pattern:
            return topic == pattern

        # Split by * and check segments
        parts = pattern.split("*")
        if len(parts) == 2:
            prefix, suffix = parts
            return topic.startswith(prefix) and topic.endswith(suffix)

        # Full segment match: "task.*" matches "task.completed"
        pattern_segments = pattern.split(".")
        topic_segments = topic.split(".")

        if len(pattern_segments) > len(topic_segments):
            return False

        for p_seg, t_seg in zip(pattern_segments, topic_segments):
            if p_seg == "*":
                continue
            if p_seg != t_seg:
                return False

        return True


# ---------------------------------------------------------------------------
# Global Instance & Convenience Functions
# ---------------------------------------------------------------------------

_global_bus: EventBus | None = None


def _get_bus() -> EventBus:
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


async def publish_event(
    topic: str,
    source: str,
    payload: dict[str, Any] | None = None,
    priority: EventPriority = EventPriority.NORMAL,
    correlation_id: str | None = None,
    tags: list[str] | None = None,
    ttl_seconds: int | None = None,
) -> int:
    """Publish an event to the internal bus. Returns delivery count."""
    event = BusEvent(
        topic=topic,
        source=source,
        payload=payload or {},
        priority=priority,
        correlation_id=correlation_id,
        tags=tags or [],
        ttl_seconds=ttl_seconds,
    )
    return await _get_bus().publish(event)


def subscribe_to_bus(
    subscriber: str,
    topic_pattern: str,
    handler: EventHandler,
    min_priority: EventPriority = EventPriority.LOW,
    source_filter: str | None = None,
) -> Subscription:
    """Subscribe to bus events matching a topic pattern."""
    return _get_bus().subscribe(
        subscriber=subscriber,
        topic_pattern=topic_pattern,
        handler=handler,
        min_priority=min_priority,
        source_filter=source_filter,
    )


def unsubscribe_from_bus(subscription_id: str) -> bool:
    """Remove a subscription."""
    return _get_bus().unsubscribe(subscription_id)


def get_bus_history(
    topic: str | None = None,
    source: str | None = None,
    limit: int = 50,
) -> list[BusEvent]:
    """Get recent bus event history."""
    return _get_bus().get_history(topic=topic, source=source, limit=limit)


def get_bus_metrics() -> BusMetrics:
    """Get event bus metrics."""
    return _get_bus().get_metrics()


def get_bus_dead_letters(limit: int = 50) -> list[dict[str, Any]]:
    """Get dead letter queue."""
    return _get_bus().get_dead_letter_queue(limit=limit)


def list_bus_subscriptions(subscriber: str | None = None) -> list[Subscription]:
    """List active bus subscriptions."""
    return _get_bus().list_subscriptions(subscriber=subscriber)
