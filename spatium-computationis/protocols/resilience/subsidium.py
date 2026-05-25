"""
Protocol: Subsidium  🛟
Meaning: Fallback handling when primary operations fail.

Handles:
- Fallback function registration
- Graceful degradation
- Default value returns
- Multi-level fallbacks
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable, TypeVar, Generic

from pydantic import BaseModel, Field


T = TypeVar("T")


class FallbackResult(BaseModel):
    """Result of an operation with fallback."""
    success: bool
    result: Any = None
    used_fallback: bool = False
    fallback_level: int = 0  # 0 = primary, 1+ = fallback levels
    primary_error: str | None = None
    fallback_errors: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Fallback Registry
# ---------------------------------------------------------------------------

_fallbacks: dict[str, list[Callable[..., Awaitable[Any]]]] = {}
_default_values: dict[str, Any] = {}


def register_fallback(
    operation_id: str,
    fallback_fn: Callable[..., Awaitable[Any]],
    priority: int = 0,
) -> None:
    """
    Register a fallback function for an operation.
    
    Lower priority values are tried first.
    """
    if operation_id not in _fallbacks:
        _fallbacks[operation_id] = []
    
    # Insert at correct position based on priority
    inserted = False
    for i, (existing_priority, _) in enumerate(_fallbacks[operation_id]):
        if priority < existing_priority:
            _fallbacks[operation_id].insert(i, (priority, fallback_fn))
            inserted = True
            break
    
    if not inserted:
        _fallbacks[operation_id].append((priority, fallback_fn))


def set_default_value(operation_id: str, default: Any) -> None:
    """Set a default value to return when all fallbacks fail."""
    _default_values[operation_id] = default


def clear_fallbacks(operation_id: str) -> None:
    """Clear all fallbacks for an operation."""
    _fallbacks.pop(operation_id, None)
    _default_values.pop(operation_id, None)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def with_fallback(
    operation_id: str,
    primary_fn: Callable[..., Awaitable[T]],
    *args: Any,
    fallback_fns: list[Callable[..., Awaitable[T]]] | None = None,
    default_value: T | None = None,
    **kwargs: Any,
) -> FallbackResult:
    """
    Protocol Subsidium: execute an operation with fallback support.
    """
    import time
    start_time = time.perf_counter()
    
    primary_error: str | None = None
    fallback_errors: list[str] = []
    
    # Try primary function
    try:
        result = await primary_fn(*args, **kwargs)
        duration = (time.perf_counter() - start_time) * 1000
        
        return FallbackResult(
            success=True,
            result=result,
            used_fallback=False,
            fallback_level=0,
            duration_ms=duration,
        )
    except Exception as e:
        primary_error = str(e)
    
    # Try registered fallbacks
    registered = _fallbacks.get(operation_id, [])
    for level, (_, fallback_fn) in enumerate(registered, start=1):
        try:
            result = await fallback_fn(*args, **kwargs)
            duration = (time.perf_counter() - start_time) * 1000
            
            return FallbackResult(
                success=True,
                result=result,
                used_fallback=True,
                fallback_level=level,
                primary_error=primary_error,
                fallback_errors=fallback_errors,
                duration_ms=duration,
            )
        except Exception as e:
            fallback_errors.append(str(e))
    
    # Try provided fallback functions
    if fallback_fns:
        base_level = len(registered)
        for level, fallback_fn in enumerate(fallback_fns, start=base_level + 1):
            try:
                result = await fallback_fn(*args, **kwargs)
                duration = (time.perf_counter() - start_time) * 1000
                
                return FallbackResult(
                    success=True,
                    result=result,
                    used_fallback=True,
                    fallback_level=level,
                    primary_error=primary_error,
                    fallback_errors=fallback_errors,
                    duration_ms=duration,
                )
            except Exception as e:
                fallback_errors.append(str(e))
    
    # Try default value
    final_default = default_value if default_value is not None else _default_values.get(operation_id)
    
    if final_default is not None:
        duration = (time.perf_counter() - start_time) * 1000
        return FallbackResult(
            success=True,
            result=final_default,
            used_fallback=True,
            fallback_level=999,  # Indicates default value
            primary_error=primary_error,
            fallback_errors=fallback_errors,
            duration_ms=duration,
        )
    
    # All fallbacks failed
    duration = (time.perf_counter() - start_time) * 1000
    return FallbackResult(
        success=False,
        used_fallback=True,
        fallback_level=len(registered) + len(fallback_fns or []),
        primary_error=primary_error,
        fallback_errors=fallback_errors,
        duration_ms=duration,
    )


def fallback_decorator(
    operation_id: str,
    default_value: Any = None,
):
    """Decorator to add fallback support to an async function."""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            result = await with_fallback(
                operation_id,
                func,
                *args,
                default_value=default_value,
                **kwargs
            )
            if result.success:
                return result.result
            raise Exception(result.primary_error or "All fallbacks failed")
        return wrapper
    return decorator


class FallbackChain(Generic[T]):
    """
    Builder for creating fallback chains.
    
    Usage:
        result = await (FallbackChain("my-operation")
            .primary(primary_fn)
            .fallback(fallback1_fn)
            .fallback(fallback2_fn)
            .default("default_value")
            .execute(arg1, arg2))
    """
    
    def __init__(self, operation_id: str):
        self.operation_id = operation_id
        self._primary: Callable[..., Awaitable[T]] | None = None
        self._fallbacks: list[Callable[..., Awaitable[T]]] = []
        self._default: T | None = None
    
    def primary(self, fn: Callable[..., Awaitable[T]]) -> "FallbackChain[T]":
        """Set the primary function."""
        self._primary = fn
        return self
    
    def fallback(self, fn: Callable[..., Awaitable[T]]) -> "FallbackChain[T]":
        """Add a fallback function."""
        self._fallbacks.append(fn)
        return self
    
    def default(self, value: T) -> "FallbackChain[T]":
        """Set the default value."""
        self._default = value
        return self
    
    async def execute(self, *args: Any, **kwargs: Any) -> FallbackResult:
        """Execute the fallback chain."""
        if not self._primary:
            raise ValueError("Primary function not set")
        
        return await with_fallback(
            self.operation_id,
            self._primary,
            *args,
            fallback_fns=self._fallbacks,
            default_value=self._default,
            **kwargs
        )
