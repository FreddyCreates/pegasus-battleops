"""
Protocol: Circuitus  🔌
Meaning: Circuit breaker for fault isolation.

Implements the circuit breaker pattern:
- CLOSED: Normal operation, requests flow through
- OPEN: Failures detected, requests fail fast
- HALF_OPEN: Testing if service has recovered
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Awaitable, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing fast
    HALF_OPEN = "half_open" # Testing recovery


class CircuitConfig(BaseModel):
    """Configuration for a circuit breaker."""
    failure_threshold: int = 5       # Failures before opening
    success_threshold: int = 3       # Successes to close from half-open
    timeout_seconds: float = 30.0    # Time to wait before half-open
    half_open_max_calls: int = 3     # Max calls in half-open state


class CircuitStatus(BaseModel):
    """Current status of a circuit breaker."""
    circuit_id: str
    state: CircuitState
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: datetime | None = None
    last_state_change: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class CircuitBreaker:
    """
    Circuit breaker implementation.
    
    Usage:
        cb = CircuitBreaker("my-service")
        result = await cb.call(my_async_function, arg1, arg2)
    """
    
    def __init__(
        self,
        circuit_id: str,
        config: CircuitConfig | None = None,
    ):
        self.circuit_id = circuit_id
        self.config = config or CircuitConfig()
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: datetime | None = None
        self._last_state_change = datetime.now(timezone.utc)
        self._half_open_calls = 0
        
        # Statistics
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current state, checking for timeout transition."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                elapsed = (datetime.now(timezone.utc) - self._last_failure_time).total_seconds()
                if elapsed >= self.config.timeout_seconds:
                    return CircuitState.HALF_OPEN
        return self._state
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self.state == CircuitState.OPEN
    
    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute a function through the circuit breaker."""
        async with self._lock:
            current_state = self.state
            
            # If open, fail fast
            if current_state == CircuitState.OPEN:
                raise CircuitOpenError(f"Circuit {self.circuit_id} is open")
            
            # If half-open, limit calls
            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitOpenError(f"Circuit {self.circuit_id} is half-open, max calls reached")
                self._half_open_calls += 1
        
        self._total_calls += 1
        
        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            raise
    
    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self._total_successes += 1
            self._failure_count = 0
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
    
    async def _record_failure(self) -> None:
        """Record a failed call."""
        async with self._lock:
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = datetime.now(timezone.utc)
            
            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open opens the circuit
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        self._state = new_state
        self._last_state_change = datetime.now(timezone.utc)
        
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._success_count = 0
            self._half_open_calls = 0
    
    def get_status(self) -> CircuitStatus:
        """Get current circuit status."""
        return CircuitStatus(
            circuit_id=self.circuit_id,
            state=self.state,
            failure_count=self._failure_count,
            success_count=self._success_count,
            last_failure_time=self._last_failure_time,
            last_state_change=self._last_state_change,
            total_calls=self._total_calls,
            total_failures=self._total_failures,
            total_successes=self._total_successes,
        )
    
    def reset(self) -> None:
        """Manually reset the circuit to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_state_change = datetime.now(timezone.utc)


class CircuitOpenError(Exception):
    """Exception raised when circuit is open."""
    pass


# ---------------------------------------------------------------------------
# Global Circuit Registry
# ---------------------------------------------------------------------------

_circuits: dict[str, CircuitBreaker] = {}


def get_or_create_circuit(
    circuit_id: str,
    config: CircuitConfig | None = None,
) -> CircuitBreaker:
    """Get or create a circuit breaker."""
    if circuit_id not in _circuits:
        _circuits[circuit_id] = CircuitBreaker(circuit_id, config)
    return _circuits[circuit_id]


async def circuit_call(
    circuit_id: str,
    func: Callable[..., Awaitable[T]],
    *args: Any,
    config: CircuitConfig | None = None,
    **kwargs: Any,
) -> T:
    """
    Protocol Circuitus: execute a function through a circuit breaker.
    """
    circuit = get_or_create_circuit(circuit_id, config)
    return await circuit.call(func, *args, **kwargs)


def get_circuit_status(circuit_id: str) -> CircuitStatus | None:
    """Get status of a circuit breaker."""
    if circuit_id in _circuits:
        return _circuits[circuit_id].get_status()
    return None


def get_all_circuits() -> dict[str, CircuitStatus]:
    """Get status of all circuit breakers."""
    return {cid: cb.get_status() for cid, cb in _circuits.items()}


def reset_circuit(circuit_id: str) -> bool:
    """Reset a circuit breaker."""
    if circuit_id in _circuits:
        _circuits[circuit_id].reset()
        return True
    return False
