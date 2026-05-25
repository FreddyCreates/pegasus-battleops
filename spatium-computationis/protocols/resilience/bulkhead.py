"""
Protocol: Bulkhead  🚧
Meaning: Isolate operations to prevent cascade failures.

Handles:
- Concurrent operation limits
- Resource isolation
- Queue management
- Load shedding
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class BulkheadConfig(BaseModel):
    """Configuration for bulkhead isolation."""
    max_concurrent: int = 10       # Max concurrent executions
    max_wait_seconds: float = 30.0  # Max time to wait for slot
    queue_size: int = 100          # Max waiting queue size


class BulkheadStatus(BaseModel):
    """Status of a bulkhead."""
    bulkhead_id: str
    active_count: int = 0
    waiting_count: int = 0
    max_concurrent: int = 10
    queue_size: int = 100
    total_acquired: int = 0
    total_rejected: int = 0
    total_timeouts: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BulkheadRejectedError(Exception):
    """Exception raised when bulkhead rejects a request."""
    pass


class BulkheadTimeoutError(Exception):
    """Exception raised when waiting for bulkhead times out."""
    pass


class Bulkhead:
    """
    Bulkhead for isolating concurrent operations.
    
    Usage:
        bulkhead = Bulkhead("my-service", max_concurrent=10)
        async with bulkhead:
            await my_operation()
    """
    
    def __init__(
        self,
        bulkhead_id: str,
        config: BulkheadConfig | None = None,
    ):
        self.bulkhead_id = bulkhead_id
        self.config = config or BulkheadConfig()
        
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._waiting_count = 0
        self._active_count = 0
        
        # Statistics
        self._total_acquired = 0
        self._total_rejected = 0
        self._total_timeouts = 0
        
        self._lock = asyncio.Lock()
    
    async def acquire(self, timeout: float | None = None) -> bool:
        """Acquire a slot in the bulkhead."""
        effective_timeout = timeout if timeout is not None else self.config.max_wait_seconds
        
        async with self._lock:
            # Check queue size
            if self._waiting_count >= self.config.queue_size:
                self._total_rejected += 1
                raise BulkheadRejectedError(
                    f"Bulkhead {self.bulkhead_id} queue full "
                    f"({self._waiting_count}/{self.config.queue_size})"
                )
            self._waiting_count += 1
        
        try:
            acquired = await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=effective_timeout,
            )
            
            async with self._lock:
                self._waiting_count -= 1
                if acquired:
                    self._active_count += 1
                    self._total_acquired += 1
            
            return acquired
            
        except asyncio.TimeoutError:
            async with self._lock:
                self._waiting_count -= 1
                self._total_timeouts += 1
            raise BulkheadTimeoutError(
                f"Timeout waiting for bulkhead {self.bulkhead_id} "
                f"after {effective_timeout}s"
            )
    
    def release(self) -> None:
        """Release a slot in the bulkhead."""
        self._semaphore.release()
        self._active_count = max(0, self._active_count - 1)
    
    async def __aenter__(self) -> "Bulkhead":
        """Acquire bulkhead on context entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Release bulkhead on context exit."""
        self.release()
    
    def get_status(self) -> BulkheadStatus:
        """Get current bulkhead status."""
        return BulkheadStatus(
            bulkhead_id=self.bulkhead_id,
            active_count=self._active_count,
            waiting_count=self._waiting_count,
            max_concurrent=self.config.max_concurrent,
            queue_size=self.config.queue_size,
            total_acquired=self._total_acquired,
            total_rejected=self._total_rejected,
            total_timeouts=self._total_timeouts,
        )


# ---------------------------------------------------------------------------
# Global Bulkhead Registry
# ---------------------------------------------------------------------------

_bulkheads: dict[str, Bulkhead] = {}


def get_or_create_bulkhead(
    bulkhead_id: str,
    config: BulkheadConfig | None = None,
) -> Bulkhead:
    """Get or create a bulkhead."""
    if bulkhead_id not in _bulkheads:
        _bulkheads[bulkhead_id] = Bulkhead(bulkhead_id, config)
    return _bulkheads[bulkhead_id]


async def acquire_bulkhead(
    bulkhead_id: str,
    config: BulkheadConfig | None = None,
    timeout: float | None = None,
) -> Bulkhead:
    """
    Protocol Bulkhead: acquire a slot in a bulkhead.
    
    Returns the bulkhead for use as a context manager.
    """
    bulkhead = get_or_create_bulkhead(bulkhead_id, config)
    await bulkhead.acquire(timeout)
    return bulkhead


async def execute_in_bulkhead(
    bulkhead_id: str,
    func: Callable[..., Awaitable[T]],
    *args: Any,
    config: BulkheadConfig | None = None,
    **kwargs: Any,
) -> T:
    """Execute a function within a bulkhead."""
    bulkhead = get_or_create_bulkhead(bulkhead_id, config)
    
    async with bulkhead:
        return await func(*args, **kwargs)


def get_bulkhead_status(bulkhead_id: str) -> BulkheadStatus | None:
    """Get status of a bulkhead."""
    if bulkhead_id in _bulkheads:
        return _bulkheads[bulkhead_id].get_status()
    return None


def get_all_bulkheads() -> dict[str, BulkheadStatus]:
    """Get status of all bulkheads."""
    return {bid: b.get_status() for bid, b in _bulkheads.items()}


def bulkhead_decorator(
    bulkhead_id: str,
    config: BulkheadConfig | None = None,
):
    """Decorator to execute a function within a bulkhead."""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await execute_in_bulkhead(
                bulkhead_id, func, *args, config=config, **kwargs
            )
        return wrapper
    return decorator
