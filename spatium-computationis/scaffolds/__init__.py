"""
Scaffolds Package — Agent Initialization and Lifecycle

Scaffolds provide the structural framework for:
- Agent initialization and configuration
- Capability declarations
- Lifecycle management
- Inter-agent communication patterns

Glyphs:
  ⌂ Scaffold  — structural foundation
  ⚙ Config    — agent configuration
  ⟳ Lifecycle — birth, operation, retirement
"""

from .base import (
    AgentScaffold,
    AgentCapability,
    AgentConfig,
    LifecycleState,
    scaffold_registry,
    get_agent_scaffold,
    register_agent,
)

from .event_bus import (
    Event,
    EventType,
    EventBus,
    global_event_bus,
    emit_event,
    subscribe,
)

from .orchestrator import (
    ProtocolOrchestrator,
    OrchestratorConfig,
    orchestrate_request,
)

__all__ = [
    # Base scaffolds
    "AgentScaffold",
    "AgentCapability", 
    "AgentConfig",
    "LifecycleState",
    "scaffold_registry",
    "get_agent_scaffold",
    "register_agent",
    # Event bus
    "Event",
    "EventType",
    "EventBus",
    "global_event_bus",
    "emit_event",
    "subscribe",
    # Orchestrator
    "ProtocolOrchestrator",
    "OrchestratorConfig",
    "orchestrate_request",
]
