"""
Platform Layer — Spatium Computationis  ⎈

The Platform Layer provides infrastructure for agents to operate as a coordinated system:

1. Task Queue (Opus Coda) — Job submission, processing, and status tracking
2. Agent Registry & Discovery — Find agents by capability, check health
3. Inter-agent Delegation (Delegatio) — One agent requesting work from another
4. Bot Layer (Nuntii) — Small, focused task bots for narrow operations

Glyphs:
  ⎈ Platform  — infrastructure coordination
  ⚙ Task      — unit of work
  ⇆ Delegatio — inter-agent request
  ⊡ Nuntius   — task bot
"""

from .task_queue import (
    TaskQueue,
    Task,
    TaskStatus,
    TaskPriority,
    submit_task,
    claim_task,
    complete_task,
    fail_task,
    get_task,
    get_agent_tasks,
    get_queue_stats,
)

from .registry import (
    AgentRegistryAPI,
    AgentInfo,
    discover_agents,
    discover_by_capability,
    get_agent_health,
    get_platform_status,
)

from .delegation import (
    DelegationRequest,
    DelegationResult,
    DelegationStatus,
    delegate_to_agent,
    delegate_to_capability,
    get_delegation_status,
)

from .nuntii import (
    Bot,
    BotRegistry,
    BotResult,
    get_bot,
    list_bots,
    invoke_bot,
)

from .buses import (
    EventBus,
    BusEvent,
    BusTopic,
    BusMetrics,
    EventPriority,
    Subscription,
    publish_event,
    subscribe_to_bus,
    unsubscribe_from_bus,
    get_bus_history,
    get_bus_metrics,
    get_bus_dead_letters,
    list_bus_subscriptions,
)

from .taxis import (
    TaxiDispatcher,
    TaxiRequest,
    TaxiResponse,
    TaxiRoute,
    TaxiMetrics,
    TaxiStatus,
    TaxiPriority,
    register_taxi_route,
    unregister_taxi_route,
    dispatch_taxi,
    dispatch_taxi_async,
    cancel_taxi,
    get_taxi_routes,
    get_taxi_route,
    get_taxi_metrics,
    get_taxi_history,
    get_taxis_in_flight,
)

from .layers import (
    LayerManager,
    Layer,
    LayerLevel,
    LayerRequest,
    LayerResponse,
    LayerMetrics,
    get_layer,
    get_all_layers,
    register_layer_handler,
    route_layer_request,
    get_layer_metrics,
    get_layer_topology,
)

__all__ = [
    # Task Queue
    "TaskQueue",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "submit_task",
    "claim_task",
    "complete_task",
    "fail_task",
    "get_task",
    "get_agent_tasks",
    "get_queue_stats",
    # Registry
    "AgentRegistryAPI",
    "AgentInfo",
    "discover_agents",
    "discover_by_capability",
    "get_agent_health",
    "get_platform_status",
    # Delegation
    "DelegationRequest",
    "DelegationResult",
    "DelegationStatus",
    "delegate_to_agent",
    "delegate_to_capability",
    "get_delegation_status",
    # Nuntii
    "Bot",
    "BotRegistry",
    "BotResult",
    "get_bot",
    "list_bots",
    "invoke_bot",
    # Buses
    "EventBus",
    "BusEvent",
    "BusTopic",
    "BusMetrics",
    "EventPriority",
    "Subscription",
    "publish_event",
    "subscribe_to_bus",
    "unsubscribe_from_bus",
    "get_bus_history",
    "get_bus_metrics",
    "get_bus_dead_letters",
    "list_bus_subscriptions",
    # Taxis
    "TaxiDispatcher",
    "TaxiRequest",
    "TaxiResponse",
    "TaxiRoute",
    "TaxiMetrics",
    "TaxiStatus",
    "TaxiPriority",
    "register_taxi_route",
    "unregister_taxi_route",
    "dispatch_taxi",
    "dispatch_taxi_async",
    "cancel_taxi",
    "get_taxi_routes",
    "get_taxi_route",
    "get_taxi_metrics",
    "get_taxi_history",
    "get_taxis_in_flight",
    # Layers
    "LayerManager",
    "Layer",
    "LayerLevel",
    "LayerRequest",
    "LayerResponse",
    "LayerMetrics",
    "get_layer",
    "get_all_layers",
    "register_layer_handler",
    "route_layer_request",
    "get_layer_metrics",
    "get_layer_topology",
]
