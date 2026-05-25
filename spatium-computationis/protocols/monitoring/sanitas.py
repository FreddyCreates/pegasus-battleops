"""
Protocol: Sanitas  💓
Meaning: Monitor system health.

Handles:
- Liveness probes (is the system running?)
- Readiness probes (is the system ready to serve?)
- Component health checks
- Dependency verification
"""

from __future__ import annotations

import asyncio
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentType(str, Enum):
    """Types of components to check."""
    DATABASE = "database"
    CACHE = "cache"
    EXTERNAL_API = "external_api"
    MESSAGE_QUEUE = "message_queue"
    FILE_SYSTEM = "file_system"
    AGENT = "agent"
    MEMORY = "memory"
    CPU = "cpu"
    DISK = "disk"


class ComponentHealth(BaseModel):
    """Health status of a single component."""
    component_name: str
    component_type: ComponentType
    status: HealthStatus
    latency_ms: float | None = None
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthCheckResult(BaseModel):
    """Complete health check result."""
    check_id: str
    overall_status: HealthStatus
    components: list[ComponentHealth] = Field(default_factory=list)
    
    # Summary
    healthy_count: int = 0
    degraded_count: int = 0
    unhealthy_count: int = 0
    
    # Timing
    total_latency_ms: float = 0.0
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Version info
    version: str = "1.0.0"
    environment: str = "production"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "health.db"


def _init_health_db() -> None:
    """Initialize the health database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Health check history
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS health_checks (
                check_id        TEXT PRIMARY KEY,
                overall_status  TEXT NOT NULL,
                healthy_count   INTEGER DEFAULT 0,
                degraded_count  INTEGER DEFAULT 0,
                unhealthy_count INTEGER DEFAULT 0,
                total_latency   REAL DEFAULT 0.0,
                checked_at      TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hc_time ON health_checks(checked_at)")
        
        # Component health history
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS component_health (
                record_id       TEXT PRIMARY KEY,
                check_id        TEXT NOT NULL,
                component_name  TEXT NOT NULL,
                component_type  TEXT NOT NULL,
                status          TEXT NOT NULL,
                latency_ms      REAL,
                message         TEXT,
                checked_at      TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ch_component ON component_health(component_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ch_check ON component_health(check_id)")
        
        conn.commit()


_init_health_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Health Check Registry
# ---------------------------------------------------------------------------

_health_checks: dict[str, Callable[[], Awaitable[ComponentHealth]]] = {}


def register_health_check(
    component_name: str,
    component_type: ComponentType,
    check_fn: Callable[[], Awaitable[ComponentHealth]],
) -> None:
    """Register a health check function."""
    _health_checks[component_name] = check_fn


# ---------------------------------------------------------------------------
# Built-in Health Checks
# ---------------------------------------------------------------------------

async def _check_database() -> ComponentHealth:
    """Check database connectivity."""
    start = time.perf_counter()
    try:
        with _db() as conn:
            conn.execute("SELECT 1").fetchone()
        latency = (time.perf_counter() - start) * 1000
        
        return ComponentHealth(
            component_name="database",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.HEALTHY if latency < 100 else HealthStatus.DEGRADED,
            latency_ms=latency,
            message="Database connection OK",
        )
    except Exception as e:
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(
            component_name="database",
            component_type=ComponentType.DATABASE,
            status=HealthStatus.UNHEALTHY,
            latency_ms=latency,
            message=str(e),
        )


async def _check_memory() -> ComponentHealth:
    """Check memory usage."""
    try:
        import os
        
        # Simple memory check using /proc/meminfo on Linux
        mem_path = Path("/proc/meminfo")
        if mem_path.exists():
            with open(mem_path) as f:
                lines = f.readlines()
            
            mem_info = {}
            for line in lines:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = int(parts[1].strip().split()[0])
                    mem_info[key] = value
            
            total = mem_info.get("MemTotal", 1)
            available = mem_info.get("MemAvailable", 0)
            used_percent = (1 - available / total) * 100
            
            status = HealthStatus.HEALTHY
            if used_percent > 90:
                status = HealthStatus.UNHEALTHY
            elif used_percent > 80:
                status = HealthStatus.DEGRADED
            
            return ComponentHealth(
                component_name="memory",
                component_type=ComponentType.MEMORY,
                status=status,
                message=f"Memory usage: {used_percent:.1f}%",
                details={"used_percent": used_percent, "total_mb": total // 1024},
            )
        else:
            # Fallback for non-Linux systems
            return ComponentHealth(
                component_name="memory",
                component_type=ComponentType.MEMORY,
                status=HealthStatus.HEALTHY,
                message="Memory check not available on this platform",
            )
    except Exception as e:
        return ComponentHealth(
            component_name="memory",
            component_type=ComponentType.MEMORY,
            status=HealthStatus.UNKNOWN,
            message=str(e),
        )


async def _check_disk() -> ComponentHealth:
    """Check disk usage."""
    try:
        import os
        
        stat = os.statvfs(DB_PATH.parent)
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bavail * stat.f_frsize
        used_percent = (1 - free / total) * 100
        
        status = HealthStatus.HEALTHY
        if used_percent > 95:
            status = HealthStatus.UNHEALTHY
        elif used_percent > 85:
            status = HealthStatus.DEGRADED
        
        return ComponentHealth(
            component_name="disk",
            component_type=ComponentType.DISK,
            status=status,
            message=f"Disk usage: {used_percent:.1f}%",
            details={
                "used_percent": used_percent,
                "free_gb": free / (1024**3),
                "total_gb": total / (1024**3),
            },
        )
    except Exception as e:
        return ComponentHealth(
            component_name="disk",
            component_type=ComponentType.DISK,
            status=HealthStatus.UNKNOWN,
            message=str(e),
        )


# Register built-in checks
register_health_check("database", ComponentType.DATABASE, _check_database)
register_health_check("memory", ComponentType.MEMORY, _check_memory)
register_health_check("disk", ComponentType.DISK, _check_disk)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def health_check(
    include_components: list[str] | None = None,
    timeout_seconds: float = 10.0,
) -> HealthCheckResult:
    """
    Protocol Sanitas: perform a comprehensive health check.
    """
    check_id = str(uuid.uuid4())
    start = time.perf_counter()
    components: list[ComponentHealth] = []
    
    # Determine which checks to run
    checks_to_run = include_components or list(_health_checks.keys())
    
    # Run checks with timeout
    for component_name in checks_to_run:
        if component_name in _health_checks:
            try:
                result = await asyncio.wait_for(
                    _health_checks[component_name](),
                    timeout=timeout_seconds / len(checks_to_run)
                )
                components.append(result)
            except asyncio.TimeoutError:
                components.append(ComponentHealth(
                    component_name=component_name,
                    component_type=ComponentType.AGENT,
                    status=HealthStatus.UNHEALTHY,
                    message="Health check timed out",
                ))
            except Exception as e:
                components.append(ComponentHealth(
                    component_name=component_name,
                    component_type=ComponentType.AGENT,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                ))
    
    total_latency = (time.perf_counter() - start) * 1000
    
    # Calculate summary
    healthy = sum(1 for c in components if c.status == HealthStatus.HEALTHY)
    degraded = sum(1 for c in components if c.status == HealthStatus.DEGRADED)
    unhealthy = sum(1 for c in components if c.status == HealthStatus.UNHEALTHY)
    
    # Determine overall status
    if unhealthy > 0:
        overall = HealthStatus.UNHEALTHY
    elif degraded > 0:
        overall = HealthStatus.DEGRADED
    elif healthy > 0:
        overall = HealthStatus.HEALTHY
    else:
        overall = HealthStatus.UNKNOWN
    
    result = HealthCheckResult(
        check_id=check_id,
        overall_status=overall,
        components=components,
        healthy_count=healthy,
        degraded_count=degraded,
        unhealthy_count=unhealthy,
        total_latency_ms=total_latency,
    )
    
    # Store result
    _store_health_check(result)
    
    return result


async def liveness_probe() -> bool:
    """
    Protocol Sanitas: simple liveness check (is the system running?).
    """
    return True


async def readiness_probe() -> bool:
    """
    Protocol Sanitas: readiness check (is the system ready to serve?).
    """
    try:
        result = await health_check(include_components=["database"])
        return result.overall_status != HealthStatus.UNHEALTHY
    except Exception:
        return False


def _store_health_check(result: HealthCheckResult) -> None:
    """Store health check result."""
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO health_checks (check_id, overall_status, healthy_count, degraded_count, unhealthy_count, total_latency, checked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.check_id,
                result.overall_status.value,
                result.healthy_count,
                result.degraded_count,
                result.unhealthy_count,
                result.total_latency_ms,
                result.checked_at.isoformat(),
            )
        )
        
        for comp in result.components:
            conn.execute(
                """
                INSERT INTO component_health (record_id, check_id, component_name, component_type, status, latency_ms, message, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    result.check_id,
                    comp.component_name,
                    comp.component_type.value,
                    comp.status.value,
                    comp.latency_ms,
                    comp.message,
                    comp.checked_at.isoformat(),
                )
            )
        
        conn.commit()


async def get_health_history(hours: int = 24, limit: int = 100) -> list[HealthCheckResult]:
    """Get health check history."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM health_checks 
            WHERE checked_at >= ? 
            ORDER BY checked_at DESC 
            LIMIT ?
            """,
            (cutoff.isoformat(), limit)
        ).fetchall()
        
        results = []
        for row in rows:
            results.append(HealthCheckResult(
                check_id=row["check_id"],
                overall_status=HealthStatus(row["overall_status"]),
                healthy_count=row["healthy_count"],
                degraded_count=row["degraded_count"],
                unhealthy_count=row["unhealthy_count"],
                total_latency_ms=row["total_latency"],
                checked_at=datetime.fromisoformat(row["checked_at"]),
            ))
        
        return results
