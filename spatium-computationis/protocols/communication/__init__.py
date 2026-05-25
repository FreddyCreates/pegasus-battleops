"""
Communication Protocols Package — Spatium Computationis

Communication and messaging protocols for:
- Webhooks and callbacks
- Notifications and messaging
- Server-sent events
- Queue management

Glyphs:
  🪝 Uncus       — webhooks
  📬 Nuntius     — notifications
  📡 Eventus     — server-sent events
  📋 Coda        — queue management
"""

from .uncus import (
    register_webhook,
    trigger_webhook,
    WebhookConfig,
    WebhookResult,
)
from .nuntius import (
    send_notification,
    get_notifications,
    NotificationChannel,
    Notification,
)
from .eventus import (
    create_event_stream,
    push_event,
    EventStream,
    SSEEvent,
)
from .coda import (
    enqueue,
    dequeue,
    peek,
    QueueConfig,
    QueueMessage,
)

__all__ = [
    # Uncus
    "register_webhook",
    "trigger_webhook",
    "WebhookConfig",
    "WebhookResult",
    # Nuntius
    "send_notification",
    "get_notifications",
    "NotificationChannel",
    "Notification",
    # Eventus
    "create_event_stream",
    "push_event",
    "EventStream",
    "SSEEvent",
    # Coda
    "enqueue",
    "dequeue",
    "peek",
    "QueueConfig",
    "QueueMessage",
]
