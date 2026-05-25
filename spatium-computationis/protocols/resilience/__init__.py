"""
Resilience Protocols Package — Spatium Computationis

Resilience and fault tolerance protocols for:
- Circuit breakers
- Retry logic
- Timeout management
- Fallback handlers

Glyphs:
  🔌 Circuitus  — circuit breaker
  🔄 Iteratio   — retry logic
  ⏱️ Tempus     — timeout management
  🛟 Subsidium  — fallback handling
"""

from .circuitus import (
    CircuitBreaker,
    CircuitState,
    circuit_call,
    get_circuit_status,
)
from .iteratio import (
    retry_with_backoff,
    RetryConfig,
    RetryResult,
)
from .tempus import (
    with_timeout,
    TimeoutConfig,
    TimeoutResult,
)
from .subsidium import (
    with_fallback,
    register_fallback,
    FallbackResult,
)
from .bulkhead import (
    Bulkhead,
    acquire_bulkhead,
    BulkheadConfig,
)

__all__ = [
    # Circuitus
    "CircuitBreaker",
    "CircuitState",
    "circuit_call",
    "get_circuit_status",
    # Iteratio
    "retry_with_backoff",
    "RetryConfig",
    "RetryResult",
    # Tempus
    "with_timeout",
    "TimeoutConfig",
    "TimeoutResult",
    # Subsidium
    "with_fallback",
    "register_fallback",
    "FallbackResult",
    # Bulkhead
    "Bulkhead",
    "acquire_bulkhead",
    "BulkheadConfig",
]
