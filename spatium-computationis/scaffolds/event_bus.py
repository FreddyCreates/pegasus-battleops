"""
Event Bus — Inter-Agent Communication  ⟷

The Event Bus provides:
- Publish/subscribe messaging between agents
- Event logging and replay
- Asynchronous communication patterns
- Event filtering and routing

Glyphs:
  ⟷ Exchange  — bidirectional communication
  ⇉ Broadcast — one-to-many emission
  ⇶ Filter    — selective subscription
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Awaitable, TypeVar

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Event Types
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    """Types of events in the system."""
    # Lifecycle events
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"
    AGENT_HEARTBEAT = "agent.heartbeat"
    
    # Protocol events
    INPUT_RECEIVED = "protocol.input_received"
    INPUT_PROCESSED = "protocol.input_processed"
    ROUTING_DECIDED = "protocol.routing_decided"
    ACTION_STARTED = "protocol.action_started"
    ACTION_COMPLETED = "protocol.action_completed"
    ACTION_FAILED = "protocol.action_failed"
    
    # Feedback events
    OUTCOME_RECORDED = "feedback.outcome_recorded"
    WEIGHT_ADJUSTED = "feedback.weight_adjusted"
    LEARNING_SIGNAL = "feedback.learning_signal"
    
    # Defense events
    THREAT_DETECTED = "defense.threat_detected"
    SPECIMEN_CLASSIFIED = "defense.specimen_classified"
    VALUE_CAPTURED = "defense.value_captured"
    ATTACK_BLOCKED = "defense.attack_blocked"
    
    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    CONFIG_CHANGED = "system.config_changed"
    ERROR_LOGGED = "system.error"
    
    # Custom events
    CUSTOM = "custom"


class EventPriority(str, Enum):
    """Priority levels for events."""
    CRITICAL = "critical"   # Must be processed immediately
    HIGH = "high"           # Important, process soon
    NORMAL = "normal"       # Standard priority
    LOW = "low"             # Process when convenient
    BACKGROUND = "background"  # Process in background


# ---------------------------------------------------------------------------
# Event Models
# ---------------------------------------------------------------------------

class Event(BaseModel):
    """A single event in the system."""
    event_id: str
    event_type: EventType
    priority: EventPriority = EventPriority.NORMAL
    
    # Source information
    source_agent: str | None = None
    source_module: str | None = None
    
    # Target (optional, for directed events)
    target_agent: str | None = None
    
    # Payload
    payload: dict[str, Any] = Field(default_factory=dict)
    
    # Context
    project_id: str | None = None
    correlation_id: str | None = None  # For tracking related events
    
    # Metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None


class EventSubscription(BaseModel):
    """A subscription to events."""
    subscription_id: str
    subscriber: str
    event_types: list[EventType]
    
    # Filters
    source_filter: str | None = None  # Regex for source_agent
    priority_filter: list[EventPriority] | None = None
    
    # Handler
    handler_name: str
    is_async: bool = True
    
    # Status
    active: bool = True
    events_received: int = 0
    last_event_at: datetime | None = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent / "field" / "events.db"


def _init_event_db() -> None:
    """Initialize the event database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Event log
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS event_log (
                event_id        TEXT PRIMARY KEY,
                event_type      TEXT NOT NULL,
                priority        TEXT DEFAULT 'normal',
                source_agent    TEXT,
                source_module   TEXT,
                target_agent    TEXT,
                payload         TEXT,
                project_id      TEXT,
                correlation_id  TEXT,
                timestamp       TEXT NOT NULL,
                expires_at      TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_el_type ON event_log(event_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_el_source ON event_log(source_agent)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_el_target ON event_log(target_agent)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_el_corr ON event_log(correlation_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_el_time ON event_log(timestamp)")
        
        # Subscriptions
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS event_subscriptions (
                subscription_id TEXT PRIMARY KEY,
                subscriber      TEXT NOT NULL,
                event_types     TEXT NOT NULL,
                source_filter   TEXT,
                priority_filter TEXT,
                handler_name    TEXT NOT NULL,
                is_async        INTEGER DEFAULT 1,
                active          INTEGER DEFAULT 1,
                events_received INTEGER DEFAULT 0,
                last_event_at   TEXT,
                created_at      TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_es_subscriber ON event_subscriptions(subscriber)")
        
        conn.commit()


_init_event_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Event Bus Implementation
# ---------------------------------------------------------------------------

# Type for event handlers
EventHandler = Callable[[Event], Awaitable[None]]
SyncEventHandler = Callable[[Event], None]


class EventBus:
    """Central event bus for inter-agent communication."""
    
    def __init__(self):
        self._async_handlers: dict[EventType, list[tuple[str, EventHandler]]] = {}
        self._sync_handlers: dict[EventType, list[tuple[str, SyncEventHandler]]] = {}
        self._subscriptions: dict[str, EventSubscription] = {}
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue()
        self._running = False
    
    def subscribe(
        self,
        subscriber: str,
        event_types: list[EventType],
        handler: EventHandler | SyncEventHandler,
        is_async: bool = True,
        source_filter: str | None = None,
        priority_filter: list[EventPriority] | None = None,
    ) -> str:
        """Subscribe to events."""
        subscription_id = str(uuid.uuid4())
        
        subscription = EventSubscription(
            subscription_id=subscription_id,
            subscriber=subscriber,
            event_types=event_types,
            source_filter=source_filter,
            priority_filter=priority_filter,
            handler_name=handler.__name__,
            is_async=is_async,
        )
        
        self._subscriptions[subscription_id] = subscription
        
        # Register handler
        for event_type in event_types:
            if is_async:
                if event_type not in self._async_handlers:
                    self._async_handlers[event_type] = []
                self._async_handlers[event_type].append((subscription_id, handler))  # type: ignore
            else:
                if event_type not in self._sync_handlers:
                    self._sync_handlers[event_type] = []
                self._sync_handlers[event_type].append((subscription_id, handler))  # type: ignore
        
        # Persist subscription
        with _db() as conn:
            conn.execute(
                """
                INSERT INTO event_subscriptions (
                    subscription_id, subscriber, event_types, source_filter,
                    priority_filter, handler_name, is_async, active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    subscription_id,
                    subscriber,
                    json.dumps([et.value for et in event_types]),
                    source_filter,
                    json.dumps([p.value for p in priority_filter]) if priority_filter else None,
                    handler.__name__,
                    1 if is_async else 0,
                    1,
                    datetime.now(timezone.utc).isoformat()
                )
            )
            conn.commit()
        
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from events."""
        if subscription_id not in self._subscriptions:
            return
        
        subscription = self._subscriptions[subscription_id]
        
        # Remove handlers
        for event_type in subscription.event_types:
            if subscription.is_async and event_type in self._async_handlers:
                self._async_handlers[event_type] = [
                    (sid, h) for sid, h in self._async_handlers[event_type]
                    if sid != subscription_id
                ]
            elif not subscription.is_async and event_type in self._sync_handlers:
                self._sync_handlers[event_type] = [
                    (sid, h) for sid, h in self._sync_handlers[event_type]
                    if sid != subscription_id
                ]
        
        del self._subscriptions[subscription_id]
        
        # Update database
        with _db() as conn:
            conn.execute(
                "UPDATE event_subscriptions SET active = 0 WHERE subscription_id = ?",
                (subscription_id,)
            )
            conn.commit()
    
    async def emit(self, event: Event) -> None:
        """Emit an event to all subscribers."""
        # Log the event
        self._log_event(event)
        
        # Call sync handlers immediately
        if event.event_type in self._sync_handlers:
            for sub_id, handler in self._sync_handlers[event.event_type]:
                if self._should_deliver(event, sub_id):
                    try:
                        handler(event)
                        self._record_delivery(sub_id)
                    except Exception as e:
                        self._log_handler_error(sub_id, event, e)
        
        # Call async handlers
        if event.event_type in self._async_handlers:
            tasks = []
            for sub_id, handler in self._async_handlers[event.event_type]:
                if self._should_deliver(event, sub_id):
                    tasks.append(self._call_async_handler(sub_id, handler, event))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _call_async_handler(
        self,
        subscription_id: str,
        handler: EventHandler,
        event: Event,
    ) -> None:
        """Call an async handler and record the result."""
        try:
            await handler(event)
            self._record_delivery(subscription_id)
        except Exception as e:
            self._log_handler_error(subscription_id, event, e)
    
    def _should_deliver(self, event: Event, subscription_id: str) -> bool:
        """Check if event should be delivered to this subscription."""
        if subscription_id not in self._subscriptions:
            return False
        
        sub = self._subscriptions[subscription_id]
        
        if not sub.active:
            return False
        
        # Check source filter
        if sub.source_filter and event.source_agent:
            import re
            if not re.match(sub.source_filter, event.source_agent):
                return False
        
        # Check priority filter
        if sub.priority_filter and event.priority not in sub.priority_filter:
            return False
        
        return True
    
    def _record_delivery(self, subscription_id: str) -> None:
        """Record event delivery to subscription."""
        now = datetime.now(timezone.utc)
        
        if subscription_id in self._subscriptions:
            self._subscriptions[subscription_id].events_received += 1
            self._subscriptions[subscription_id].last_event_at = now
        
        with _db() as conn:
            conn.execute(
                "UPDATE event_subscriptions SET events_received = events_received + 1, last_event_at = ? WHERE subscription_id = ?",
                (now.isoformat(), subscription_id)
            )
            conn.commit()
    
    def _log_event(self, event: Event) -> None:
        """Log event to database."""
        with _db() as conn:
            conn.execute(
                """
                INSERT INTO event_log (
                    event_id, event_type, priority, source_agent, source_module,
                    target_agent, payload, project_id, correlation_id,
                    timestamp, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_type.value,
                    event.priority.value,
                    event.source_agent,
                    event.source_module,
                    event.target_agent,
                    json.dumps(event.payload),
                    event.project_id,
                    event.correlation_id,
                    event.timestamp.isoformat(),
                    event.expires_at.isoformat() if event.expires_at else None
                )
            )
            conn.commit()
    
    def _log_handler_error(
        self,
        subscription_id: str,
        event: Event,
        error: Exception,
    ) -> None:
        """Log handler error."""
        # In production, this would log to a proper error tracking system
        print(f"Event handler error: subscription={subscription_id}, event={event.event_id}, error={error}")
    
    def get_event_history(
        self,
        event_types: list[EventType] | None = None,
        source_agent: str | None = None,
        correlation_id: str | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Get historical events matching criteria."""
        with _db() as conn:
            query = "SELECT * FROM event_log WHERE 1=1"
            params: list[Any] = []
            
            if event_types:
                placeholders = ",".join("?" * len(event_types))
                query += f" AND event_type IN ({placeholders})"
                params.extend(et.value for et in event_types)
            
            if source_agent:
                query += " AND source_agent = ?"
                params.append(source_agent)
            
            if correlation_id:
                query += " AND correlation_id = ?"
                params.append(correlation_id)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            return [
                Event(
                    event_id=row["event_id"],
                    event_type=EventType(row["event_type"]),
                    priority=EventPriority(row["priority"]),
                    source_agent=row["source_agent"],
                    source_module=row["source_module"],
                    target_agent=row["target_agent"],
                    payload=json.loads(row["payload"]) if row["payload"] else {},
                    project_id=row["project_id"],
                    correlation_id=row["correlation_id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                )
                for row in rows
            ]


# ---------------------------------------------------------------------------
# Global Event Bus
# ---------------------------------------------------------------------------

# Singleton event bus
_global_event_bus: EventBus | None = None


def global_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


async def emit_event(
    event_type: EventType,
    payload: dict[str, Any] | None = None,
    source_agent: str | None = None,
    source_module: str | None = None,
    target_agent: str | None = None,
    priority: EventPriority = EventPriority.NORMAL,
    project_id: str | None = None,
    correlation_id: str | None = None,
) -> Event:
    """Convenience function to emit an event."""
    event = Event(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        priority=priority,
        source_agent=source_agent,
        source_module=source_module,
        target_agent=target_agent,
        payload=payload or {},
        project_id=project_id,
        correlation_id=correlation_id,
    )
    
    await global_event_bus().emit(event)
    return event


def subscribe(
    subscriber: str,
    event_types: list[EventType],
    handler: EventHandler | SyncEventHandler,
    is_async: bool = True,
    source_filter: str | None = None,
    priority_filter: list[EventPriority] | None = None,
) -> str:
    """Convenience function to subscribe to events."""
    return global_event_bus().subscribe(
        subscriber=subscriber,
        event_types=event_types,
        handler=handler,
        is_async=is_async,
        source_filter=source_filter,
        priority_filter=priority_filter,
    )
