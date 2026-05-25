"""
Protocol: Iteratio  🔄
Meaning: Retry logic with exponential backoff.

Handles:
- Automatic retries on failure
- Exponential backoff
- Jitter for distributed systems
- Configurable retry conditions
"""

from __future__ import annotations

import asyncio
import random
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable, TypeVar, Type

from pydantic import BaseModel, Field


T = TypeVar("T")


class BackoffStrategy(str, Enum):
    """Backoff strategies."""
    CONSTANT = "constant"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1
    
    # Retry conditions
    retry_exceptions: list[str] = Field(default_factory=lambda: ["Exception"])
    no_retry_exceptions: list[str] = Field(default_factory=list)
    retry_on_result: Callable[[Any], bool] | None = None


class RetryAttempt(BaseModel):
    """Information about a single retry attempt."""
    attempt_number: int
    success: bool
    duration_ms: float
    error: str | None = None
    delay_before_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RetryResult(BaseModel):
    """Result of a retry operation."""
    success: bool
    result: Any = None
    total_attempts: int = 0
    total_duration_ms: float = 0.0
    attempts: list[RetryAttempt] = Field(default_factory=list)
    final_error: str | None = None


# ---------------------------------------------------------------------------
# Backoff Calculations
# ---------------------------------------------------------------------------

def _calculate_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """Calculate delay before next retry."""
    if config.backoff_strategy == BackoffStrategy.CONSTANT:
        delay = config.initial_delay_seconds
    elif config.backoff_strategy == BackoffStrategy.LINEAR:
        delay = config.initial_delay_seconds * attempt
    elif config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
        delay = config.initial_delay_seconds * (config.backoff_multiplier ** (attempt - 1))
    elif config.backoff_strategy == BackoffStrategy.FIBONACCI:
        delay = config.initial_delay_seconds * _fibonacci(attempt)
    else:
        delay = config.initial_delay_seconds
    
    # Apply max delay cap
    delay = min(delay, config.max_delay_seconds)
    
    # Apply jitter
    if config.jitter:
        jitter_range = delay * config.jitter_factor
        delay = delay + random.uniform(-jitter_range, jitter_range)
    
    return max(0, delay)


def _fibonacci(n: int) -> int:
    """Calculate nth Fibonacci number."""
    if n <= 1:
        return 1
    a, b = 1, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b


def _should_retry(
    error: Exception,
    config: RetryConfig,
) -> bool:
    """Determine if we should retry based on the exception."""
    error_type = type(error).__name__
    
    # Check no-retry list first
    for no_retry in config.no_retry_exceptions:
        if error_type == no_retry or no_retry in str(type(error).__mro__):
            return False
    
    # Check retry list
    for retry_exc in config.retry_exceptions:
        if retry_exc == "Exception" or error_type == retry_exc:
            return True
    
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    config: RetryConfig | None = None,
    **kwargs: Any,
) -> RetryResult:
    """
    Protocol Iteratio: execute a function with retry logic.
    """
    cfg = config or RetryConfig()
    attempts: list[RetryAttempt] = []
    start_time = time.perf_counter()
    last_error: str | None = None
    result: Any = None
    
    for attempt in range(1, cfg.max_attempts + 1):
        attempt_start = time.perf_counter()
        delay_before = 0.0
        
        # Apply delay before retry (not on first attempt)
        if attempt > 1:
            delay = _calculate_delay(attempt - 1, cfg)
            delay_before = delay * 1000
            await asyncio.sleep(delay)
        
        try:
            result = await func(*args, **kwargs)
            
            # Check if result should trigger retry
            if cfg.retry_on_result and cfg.retry_on_result(result):
                duration = (time.perf_counter() - attempt_start) * 1000
                attempts.append(RetryAttempt(
                    attempt_number=attempt,
                    success=False,
                    duration_ms=duration,
                    delay_before_ms=delay_before,
                    error="Result triggered retry",
                ))
                last_error = "Result triggered retry"
                continue
            
            # Success
            duration = (time.perf_counter() - attempt_start) * 1000
            attempts.append(RetryAttempt(
                attempt_number=attempt,
                success=True,
                duration_ms=duration,
                delay_before_ms=delay_before,
            ))
            
            total_duration = (time.perf_counter() - start_time) * 1000
            return RetryResult(
                success=True,
                result=result,
                total_attempts=attempt,
                total_duration_ms=total_duration,
                attempts=attempts,
            )
            
        except Exception as e:
            duration = (time.perf_counter() - attempt_start) * 1000
            last_error = str(e)
            
            attempts.append(RetryAttempt(
                attempt_number=attempt,
                success=False,
                duration_ms=duration,
                delay_before_ms=delay_before,
                error=last_error,
            ))
            
            # Check if we should retry
            if attempt < cfg.max_attempts and _should_retry(e, cfg):
                continue
            
            # No more retries
            break
    
    # All attempts failed
    total_duration = (time.perf_counter() - start_time) * 1000
    return RetryResult(
        success=False,
        total_attempts=len(attempts),
        total_duration_ms=total_duration,
        attempts=attempts,
        final_error=last_error,
    )


def retry_decorator(
    config: RetryConfig | None = None,
):
    """Decorator to add retry logic to an async function."""
    cfg = config or RetryConfig()
    
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            result = await retry_with_backoff(func, *args, config=cfg, **kwargs)
            if result.success:
                return result.result
            raise Exception(result.final_error or "Retry failed")
        return wrapper
    return decorator
