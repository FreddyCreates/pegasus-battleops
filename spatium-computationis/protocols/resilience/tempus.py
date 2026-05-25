"""
Protocol: Tempus  ⏱️
Meaning: Timeout management for operations.

Handles:
- Operation timeouts
- Deadline propagation
- Graceful cancellation
- Timeout budgets
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Awaitable, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class TimeoutConfig(BaseModel):
    """Configuration for timeout behavior."""
    timeout_seconds: float = 30.0
    soft_timeout_seconds: float | None = None  # Warning before hard timeout
    cancel_on_timeout: bool = True


class TimeoutResult(BaseModel):
    """Result of a timed operation."""
    success: bool
    result: Any = None
    timed_out: bool = False
    duration_ms: float = 0.0
    timeout_seconds: float = 0.0
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TimeoutError(Exception):
    """Exception raised when an operation times out."""
    def __init__(self, message: str, duration_ms: float, timeout_seconds: float):
        super().__init__(message)
        self.duration_ms = duration_ms
        self.timeout_seconds = timeout_seconds


# ---------------------------------------------------------------------------
# Deadline Context
# ---------------------------------------------------------------------------

class DeadlineContext:
    """Context for tracking operation deadlines."""
    
    def __init__(self, deadline: datetime):
        self.deadline = deadline
        self._start_time = datetime.now(timezone.utc)
    
    @property
    def remaining_seconds(self) -> float:
        """Get remaining time until deadline."""
        now = datetime.now(timezone.utc)
        remaining = (self.deadline - now).total_seconds()
        return max(0, remaining)
    
    @property
    def is_expired(self) -> bool:
        """Check if deadline has passed."""
        return datetime.now(timezone.utc) >= self.deadline
    
    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time since context creation."""
        return (datetime.now(timezone.utc) - self._start_time).total_seconds()
    
    def check_deadline(self) -> None:
        """Raise TimeoutError if deadline has passed."""
        if self.is_expired:
            raise TimeoutError(
                "Operation exceeded deadline",
                self.elapsed_seconds * 1000,
                (self.deadline - self._start_time).total_seconds(),
            )


_deadline_context: DeadlineContext | None = None


def get_current_deadline() -> DeadlineContext | None:
    """Get the current deadline context."""
    return _deadline_context


def set_deadline_context(ctx: DeadlineContext | None) -> None:
    """Set the current deadline context."""
    global _deadline_context
    _deadline_context = ctx


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def with_timeout(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    config: TimeoutConfig | None = None,
    **kwargs: Any,
) -> TimeoutResult:
    """
    Protocol Tempus: execute a function with a timeout.
    """
    cfg = config or TimeoutConfig()
    start_time = time.perf_counter()
    
    # Set up deadline context
    deadline = datetime.now(timezone.utc) + timedelta(seconds=cfg.timeout_seconds)
    ctx = DeadlineContext(deadline)
    old_ctx = get_current_deadline()
    set_deadline_context(ctx)
    
    try:
        result = await asyncio.wait_for(
            func(*args, **kwargs),
            timeout=cfg.timeout_seconds,
        )
        
        duration = (time.perf_counter() - start_time) * 1000
        
        return TimeoutResult(
            success=True,
            result=result,
            timed_out=False,
            duration_ms=duration,
            timeout_seconds=cfg.timeout_seconds,
        )
        
    except asyncio.TimeoutError:
        duration = (time.perf_counter() - start_time) * 1000
        
        return TimeoutResult(
            success=False,
            timed_out=True,
            duration_ms=duration,
            timeout_seconds=cfg.timeout_seconds,
            error=f"Operation timed out after {cfg.timeout_seconds}s",
        )
        
    except Exception as e:
        duration = (time.perf_counter() - start_time) * 1000
        
        return TimeoutResult(
            success=False,
            timed_out=False,
            duration_ms=duration,
            timeout_seconds=cfg.timeout_seconds,
            error=str(e),
        )
    
    finally:
        set_deadline_context(old_ctx)


def timeout_decorator(
    timeout_seconds: float = 30.0,
):
    """Decorator to add timeout to an async function."""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            result = await with_timeout(
                func, *args,
                config=TimeoutConfig(timeout_seconds=timeout_seconds),
                **kwargs
            )
            if result.success:
                return result.result
            if result.timed_out:
                raise TimeoutError(
                    result.error or "Timeout",
                    result.duration_ms,
                    result.timeout_seconds,
                )
            raise Exception(result.error or "Unknown error")
        return wrapper
    return decorator


class TimeoutBudget:
    """
    Manage a timeout budget across multiple operations.
    
    Usage:
        budget = TimeoutBudget(total_seconds=30.0)
        await budget.execute(operation1)
        await budget.execute(operation2)  # Uses remaining time
    """
    
    def __init__(self, total_seconds: float):
        self.total_seconds = total_seconds
        self._start_time = time.perf_counter()
        self._operations: list[dict] = []
    
    @property
    def remaining_seconds(self) -> float:
        """Get remaining budget."""
        elapsed = time.perf_counter() - self._start_time
        return max(0, self.total_seconds - elapsed)
    
    @property
    def is_exhausted(self) -> bool:
        """Check if budget is exhausted."""
        return self.remaining_seconds <= 0
    
    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        min_timeout: float = 1.0,
        **kwargs: Any,
    ) -> TimeoutResult:
        """Execute an operation within the remaining budget."""
        timeout = max(min_timeout, self.remaining_seconds)
        
        result = await with_timeout(
            func, *args,
            config=TimeoutConfig(timeout_seconds=timeout),
            **kwargs
        )
        
        self._operations.append({
            "success": result.success,
            "duration_ms": result.duration_ms,
            "timed_out": result.timed_out,
        })
        
        return result
    
    def get_summary(self) -> dict:
        """Get summary of budget usage."""
        elapsed = (time.perf_counter() - self._start_time) * 1000
        return {
            "total_budget_ms": self.total_seconds * 1000,
            "elapsed_ms": elapsed,
            "remaining_ms": self.remaining_seconds * 1000,
            "operations": len(self._operations),
            "successful_operations": sum(1 for op in self._operations if op["success"]),
            "timed_out_operations": sum(1 for op in self._operations if op["timed_out"]),
        }
