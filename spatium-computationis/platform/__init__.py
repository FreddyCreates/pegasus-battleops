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
]
