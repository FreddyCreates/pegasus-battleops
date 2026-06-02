"""
Protocol: Discoveritas — Service & Agent Discovery  🔭

Dynamic discovery protocol for finding agents, services, capabilities, and resources
across the Spatium Computationis ecosystem.

Glyph: 🔭
Latin: Discoveritas
Meaning: the act of uncovering what is available

Features:
  - Service registry with health checks
  - Capability-based discovery
  - Tag-based search
  - Auto-registration with TTL
  - Dependency graph resolution
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceType(str, Enum):
    AGENT = "agent"
    BOT = "bot"
    PROTOCOL = "protocol"
    INTEGRATION = "integration"
    EXTERNAL = "external"


class ServiceEntry(BaseModel):
    """A discoverable service in the platform."""
    service_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    service_type: ServiceType
    version: str = "1.0.0"
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    endpoint: str | None = None
    status: ServiceStatus = ServiceStatus.UNKNOWN
    metadata: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int = 300  # 5 minutes default


class DiscoveryQuery(BaseModel):
    """Query for discovering services."""
    service_type: ServiceType | None = None
    capabilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    status: ServiceStatus | None = None
    name_pattern: str | None = None


class DiscoveryResult(BaseModel):
    """Result of a discovery query."""
    services: list[ServiceEntry]
    total: int
    query_time_ms: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DependencyNode(BaseModel):
    """Node in a dependency graph."""
    service_id: str
    name: str
    dependencies: list[str] = Field(default_factory=list)
    dependents: list[str] = Field(default_factory=list)
    depth: int = 0


# ---------------------------------------------------------------------------
# Registry Store
# ---------------------------------------------------------------------------

_registry: dict[str, ServiceEntry] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register_service(
    name: str,
    service_type: ServiceType,
    capabilities: list[str] | None = None,
    tags: list[str] | None = None,
    endpoint: str | None = None,
    version: str = "1.0.0",
    description: str = "",
    dependencies: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    ttl_seconds: int = 300,
) -> ServiceEntry:
    """Register a service for discovery."""
    entry = ServiceEntry(
        name=name,
        service_type=service_type,
        version=version,
        description=description,
        capabilities=capabilities or [],
        tags=tags or [],
        endpoint=endpoint,
        dependencies=dependencies or [],
        metadata=metadata or {},
        ttl_seconds=ttl_seconds,
        status=ServiceStatus.HEALTHY,
    )
    _registry[entry.service_id] = entry
    return entry


def deregister_service(service_id: str) -> bool:
    """Remove a service from the registry."""
    return _registry.pop(service_id, None) is not None


def heartbeat(service_id: str, status: ServiceStatus = ServiceStatus.HEALTHY) -> bool:
    """Update service heartbeat and status."""
    entry = _registry.get(service_id)
    if not entry:
        return False
    entry.last_heartbeat = datetime.now(timezone.utc)
    entry.status = status
    return True


def discover(query: DiscoveryQuery | None = None) -> DiscoveryResult:
    """Discover services matching a query."""
    import time
    start = time.time()

    # Prune expired services
    _prune_expired()

    services = list(_registry.values())

    if query:
        if query.service_type:
            services = [s for s in services if s.service_type == query.service_type]

        if query.capabilities:
            services = [
                s for s in services
                if all(cap in s.capabilities for cap in query.capabilities)
            ]

        if query.tags:
            services = [
                s for s in services
                if any(tag in s.tags for tag in query.tags)
            ]

        if query.status:
            services = [s for s in services if s.status == query.status]

        if query.name_pattern:
            pattern = query.name_pattern.lower()
            services = [s for s in services if pattern in s.name.lower()]

    elapsed = (time.time() - start) * 1000

    return DiscoveryResult(
        services=services,
        total=len(services),
        query_time_ms=round(elapsed, 2),
    )


def discover_by_capability(capability: str) -> list[ServiceEntry]:
    """Find all services with a specific capability."""
    _prune_expired()
    return [s for s in _registry.values() if capability in s.capabilities]


def discover_by_tag(tag: str) -> list[ServiceEntry]:
    """Find all services with a specific tag."""
    _prune_expired()
    return [s for s in _registry.values() if tag in s.tags]


def get_service(service_id: str) -> ServiceEntry | None:
    """Get a specific service by ID."""
    return _registry.get(service_id)


def get_service_by_name(name: str) -> ServiceEntry | None:
    """Get a service by exact name."""
    for entry in _registry.values():
        if entry.name == name:
            return entry
    return None


def resolve_dependencies(service_id: str) -> list[DependencyNode]:
    """Resolve the full dependency graph for a service."""
    entry = _registry.get(service_id)
    if not entry:
        return []

    visited: set[str] = set()
    result: list[DependencyNode] = []

    def _resolve(sid: str, depth: int):
        if sid in visited:
            return
        visited.add(sid)
        svc = _registry.get(sid) or get_service_by_name(sid)
        if not svc:
            return

        # Find dependents
        dependents = [
            s.name for s in _registry.values()
            if svc.name in s.dependencies
        ]

        node = DependencyNode(
            service_id=svc.service_id,
            name=svc.name,
            dependencies=svc.dependencies,
            dependents=dependents,
            depth=depth,
        )
        result.append(node)

        for dep in svc.dependencies:
            dep_entry = get_service_by_name(dep)
            if dep_entry:
                _resolve(dep_entry.service_id, depth + 1)

    _resolve(service_id, 0)
    return result


def get_registry_stats() -> dict[str, Any]:
    """Get registry statistics."""
    _prune_expired()
    services = list(_registry.values())
    by_type = {}
    by_status = {}
    for s in services:
        by_type[s.service_type.value] = by_type.get(s.service_type.value, 0) + 1
        by_status[s.status.value] = by_status.get(s.status.value, 0) + 1

    return {
        "total_services": len(services),
        "by_type": by_type,
        "by_status": by_status,
        "capabilities": list(set(
            cap for s in services for cap in s.capabilities
        )),
    }


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _prune_expired():
    """Remove services that haven't sent a heartbeat within their TTL."""
    now = datetime.now(timezone.utc)
    expired = [
        sid for sid, entry in _registry.items()
        if (now - entry.last_heartbeat) > timedelta(seconds=entry.ttl_seconds)
    ]
    for sid in expired:
        _registry.pop(sid, None)
