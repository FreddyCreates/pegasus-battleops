"""
Agent Registry & Discovery  ⎈

Provides a unified view of all agents in the system:
- List all registered agents with their capabilities and health
- Discover agents by capability type
- Check agent health and readiness
- Platform-wide status dashboard

Glyph: ⎈ — platform coordination
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from pydantic import BaseModel, Field

from ..scaffolds.base import (
    AgentScaffold,
    AgentConfig,
    CapabilityType,
    LifecycleState,
    get_agent_scaffold,
    get_all_agents,
    get_agents_by_capability,
    scaffold_registry,
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AgentInfo(BaseModel):
    """Public information about an agent."""
    agent_name: str
    glyph: str
    description: str
    version: str
    primary_region: str
    state: LifecycleState
    capabilities: list[str] = Field(default_factory=list)
    
    # Health indicators
    is_healthy: bool = True
    tasks_completed: int = 0
    tasks_failed: int = 0
    current_tasks: int = 0
    avg_task_duration_ms: float = 0.0
    last_heartbeat: datetime | None = None
    last_activity: datetime | None = None
    
    # Availability
    is_available: bool = True
    capacity_remaining: int = 0


class PlatformStatus(BaseModel):
    """Overall platform health status."""
    total_agents: int = 0
    agents_ready: int = 0
    agents_busy: int = 0
    agents_degraded: int = 0
    agents_error: int = 0
    
    # Capabilities coverage
    capabilities_available: list[str] = Field(default_factory=list)
    
    # Overall health
    platform_healthy: bool = True
    health_score: float = Field(ge=0.0, le=1.0, default=1.0)
    
    # Timestamp
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Registry API
# ---------------------------------------------------------------------------

class AgentRegistryAPI:
    """API for discovering and querying agents."""

    def discover_all(self) -> list[AgentInfo]:
        """List all registered agents with their status."""
        agents = get_all_agents()
        return [self._scaffold_to_info(a) for a in agents]

    def discover_by_capability(self, capability_type: CapabilityType) -> list[AgentInfo]:
        """Find agents that have a specific capability."""
        agents = get_agents_by_capability(capability_type)
        return [self._scaffold_to_info(a) for a in agents]

    def get_agent_health(self, agent_name: str) -> AgentInfo | None:
        """Get detailed health info for a specific agent."""
        scaffold = get_agent_scaffold(agent_name)
        if not scaffold:
            return None
        return self._scaffold_to_info(scaffold)

    def get_platform_status(self) -> PlatformStatus:
        """Get overall platform health."""
        agents = get_all_agents()
        now = datetime.now(timezone.utc)

        ready = sum(1 for a in agents if a.state == LifecycleState.READY)
        busy = sum(1 for a in agents if a.state == LifecycleState.BUSY)
        degraded = sum(1 for a in agents if a.state == LifecycleState.DEGRADED)
        error = sum(1 for a in agents if a.state == LifecycleState.ERROR)

        # Collect all available capabilities
        capabilities = set()
        for agent in agents:
            if agent.state in (LifecycleState.READY, LifecycleState.BUSY):
                for cap in agent.config.capabilities:
                    if cap.enabled:
                        capabilities.add(cap.capability_type.value)

        total = len(agents)
        health_score = (ready + busy * 0.8) / max(total, 1)

        return PlatformStatus(
            total_agents=total,
            agents_ready=ready,
            agents_busy=busy,
            agents_degraded=degraded,
            agents_error=error,
            capabilities_available=sorted(capabilities),
            platform_healthy=error == 0 and health_score > 0.5,
            health_score=min(health_score, 1.0),
            checked_at=now,
        )

    def get_available_agents(self) -> list[AgentInfo]:
        """Get only agents that are ready to accept work."""
        agents = get_all_agents()
        available = [
            a for a in agents
            if a.state in (LifecycleState.READY, LifecycleState.BUSY)
            and a.current_tasks < a.config.max_concurrent_tasks
        ]
        return [self._scaffold_to_info(a) for a in available]

    def _scaffold_to_info(self, scaffold: AgentScaffold) -> AgentInfo:
        """Convert an AgentScaffold to public AgentInfo."""
        now = datetime.now(timezone.utc)
        
        # Determine health based on state and heartbeat
        is_healthy = scaffold.state in (
            LifecycleState.READY,
            LifecycleState.BUSY,
            LifecycleState.INITIALIZING,
        )
        
        # Check heartbeat staleness (5 minutes)
        if scaffold.last_heartbeat:
            stale = (now - scaffold.last_heartbeat) > timedelta(minutes=5)
            if stale and scaffold.state == LifecycleState.READY:
                is_healthy = False

        is_available = (
            scaffold.state in (LifecycleState.READY, LifecycleState.BUSY)
            and scaffold.current_tasks < scaffold.config.max_concurrent_tasks
        )

        return AgentInfo(
            agent_name=scaffold.config.agent_name,
            glyph=scaffold.config.glyph,
            description=scaffold.config.description,
            version=scaffold.config.version,
            primary_region=scaffold.config.primary_region,
            state=scaffold.state,
            capabilities=[cap.name for cap in scaffold.config.capabilities if cap.enabled],
            is_healthy=is_healthy,
            tasks_completed=scaffold.tasks_completed,
            tasks_failed=scaffold.tasks_failed,
            current_tasks=scaffold.current_tasks,
            avg_task_duration_ms=scaffold.avg_task_duration_ms,
            last_heartbeat=scaffold.last_heartbeat,
            last_activity=scaffold.last_activity,
            is_available=is_available,
            capacity_remaining=max(0, scaffold.config.max_concurrent_tasks - scaffold.current_tasks),
        )


# ---------------------------------------------------------------------------
# Global Instance & Convenience Functions
# ---------------------------------------------------------------------------

_global_registry: AgentRegistryAPI | None = None


def _get_registry() -> AgentRegistryAPI:
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistryAPI()
    return _global_registry


def discover_agents() -> list[AgentInfo]:
    """List all registered agents."""
    return _get_registry().discover_all()


def discover_by_capability(capability_type: CapabilityType) -> list[AgentInfo]:
    """Find agents with a specific capability."""
    return _get_registry().discover_by_capability(capability_type)


def get_agent_health(agent_name: str) -> AgentInfo | None:
    """Get health info for a specific agent."""
    return _get_registry().get_agent_health(agent_name)


def get_platform_status() -> PlatformStatus:
    """Get overall platform health."""
    return _get_registry().get_platform_status()
