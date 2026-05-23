"""
Protocol: Eventus  📡
Meaning: Server-sent events for real-time updates.

Handles:
- Event stream management
- Real-time event pushing
- Client subscription handling
- Event history
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator

from pydantic import BaseModel, Field


class SSEEventType(str, Enum):
    """Types of SSE events."""
    MESSAGE = "message"
    STATUS = "status"
    PROGRESS = "progress"
    ERROR = "error"
    PING = "ping"
    COMPLETE = "complete"


class SSEEvent(BaseModel):
    """A server-sent event."""
    event_id: str
    event_type: SSEEventType = SSEEventType.MESSAGE
    data: Any = None
    stream_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_sse_format(self) -> str:
        """Format as SSE message."""
        lines = []
        lines.append(f"id: {self.event_id}")
        lines.append(f"event: {self.event_type.value}")
        
        data_str = json.dumps(self.data) if not isinstance(self.data, str) else self.data
        for line in data_str.split("\n"):
            lines.append(f"data: {line}")
        
        return "\n".join(lines) + "\n\n"


class EventStream:
    """Manages an SSE event stream."""
    
    def __init__(self, stream_id: str):
        self.stream_id = stream_id
        self._queue: asyncio.Queue[SSEEvent] = asyncio.Queue()
        self._closed = False
        self._subscribers: int = 0
        self._event_history: list[SSEEvent] = []
        self._max_history = 100
        self.created_at = datetime.now(timezone.utc)
    
    async def push(self, event: SSEEvent) -> None:
        """Push an event to the stream."""
        if self._closed:
            return
        
        event.stream_id = self.stream_id
        
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
        
        await self._queue.put(event)
    
    async def subscribe(self) -> AsyncIterator[SSEEvent]:
        """Subscribe to the event stream."""
        self._subscribers += 1
        try:
            while not self._closed:
                try:
                    event = await asyncio.wait_for(self._queue.get(), timeout=30)
                    yield event
                    
                    if event.event_type == SSEEventType.COMPLETE:
                        break
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    yield SSEEvent(
                        event_id=str(uuid.uuid4()),
                        event_type=SSEEventType.PING,
                        data="ping",
                        stream_id=self.stream_id,
                    )
        finally:
            self._subscribers -= 1
    
    def close(self) -> None:
        """Close the event stream."""
        self._closed = True
    
    @property
    def is_closed(self) -> bool:
        return self._closed
    
    @property
    def subscriber_count(self) -> int:
        return self._subscribers
    
    def get_history(self, since_id: str | None = None) -> list[SSEEvent]:
        """Get event history, optionally from a specific event ID."""
        if not since_id:
            return list(self._event_history)
        
        found_index = -1
        for i, event in enumerate(self._event_history):
            if event.event_id == since_id:
                found_index = i
                break
        
        if found_index >= 0:
            return self._event_history[found_index + 1:]
        return list(self._event_history)


# ---------------------------------------------------------------------------
# Stream Registry
# ---------------------------------------------------------------------------

_streams: dict[str, EventStream] = {}
_topic_subscribers: dict[str, set[str]] = defaultdict(set)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def create_event_stream(
    stream_id: str | None = None,
    topics: list[str] | None = None,
) -> EventStream:
    """
    Protocol Eventus: create a new event stream.
    """
    effective_id = stream_id or str(uuid.uuid4())
    
    stream = EventStream(effective_id)
    _streams[effective_id] = stream
    
    # Subscribe to topics
    if topics:
        for topic in topics:
            _topic_subscribers[topic].add(effective_id)
    
    return stream


async def get_event_stream(stream_id: str) -> EventStream | None:
    """Get an existing event stream."""
    return _streams.get(stream_id)


async def close_event_stream(stream_id: str) -> bool:
    """Close and remove an event stream."""
    if stream_id in _streams:
        _streams[stream_id].close()
        del _streams[stream_id]
        
        # Remove from topic subscriptions
        for topic, subscribers in _topic_subscribers.items():
            subscribers.discard(stream_id)
        
        return True
    return False


async def push_event(
    stream_id: str,
    data: Any,
    event_type: SSEEventType = SSEEventType.MESSAGE,
) -> SSEEvent | None:
    """
    Protocol Eventus: push an event to a stream.
    """
    stream = _streams.get(stream_id)
    if not stream or stream.is_closed:
        return None
    
    event = SSEEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        data=data,
        stream_id=stream_id,
    )
    
    await stream.push(event)
    return event


async def broadcast_to_topic(
    topic: str,
    data: Any,
    event_type: SSEEventType = SSEEventType.MESSAGE,
) -> list[SSEEvent]:
    """Broadcast an event to all streams subscribed to a topic."""
    events: list[SSEEvent] = []
    
    stream_ids = _topic_subscribers.get(topic, set())
    for stream_id in stream_ids:
        event = await push_event(stream_id, data, event_type)
        if event:
            events.append(event)
    
    return events


async def subscribe_to_topic(stream_id: str, topic: str) -> None:
    """Subscribe a stream to a topic."""
    _topic_subscribers[topic].add(stream_id)


async def unsubscribe_from_topic(stream_id: str, topic: str) -> None:
    """Unsubscribe a stream from a topic."""
    _topic_subscribers[topic].discard(stream_id)


def get_all_streams() -> dict[str, dict]:
    """Get info about all active streams."""
    return {
        stream_id: {
            "stream_id": stream_id,
            "subscribers": stream.subscriber_count,
            "is_closed": stream.is_closed,
            "created_at": stream.created_at.isoformat(),
            "history_size": len(stream._event_history),
        }
        for stream_id, stream in _streams.items()
    }


# ---------------------------------------------------------------------------
# SSE Response Generator
# ---------------------------------------------------------------------------

async def sse_response_generator(
    stream: EventStream,
    last_event_id: str | None = None,
) -> AsyncIterator[str]:
    """Generate SSE formatted response strings."""
    # Send any missed events
    if last_event_id:
        history = stream.get_history(last_event_id)
        for event in history:
            yield event.to_sse_format()
    
    # Stream new events
    async for event in stream.subscribe():
        yield event.to_sse_format()
