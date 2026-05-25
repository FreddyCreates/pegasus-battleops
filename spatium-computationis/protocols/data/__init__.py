"""
Data Protocols Package — Spatium Computationis

Data management protocols for:
- Caching and memoization
- Data transformation
- Aggregation and rollup
- Data migration

Glyphs:
  💾 Repositio   — caching
  🔀 Transformatio — data transformation
  📊 Aggregatio  — aggregation
  🔄 Migratio    — migration
"""

from .repositio import (
    cache_get,
    cache_set,
    cache_delete,
    cache_clear,
    CacheConfig,
    CacheEntry,
)
from .transformatio import (
    transform_data,
    register_transformer,
    TransformResult,
    TransformConfig,
)
from .aggregatio import (
    aggregate_data,
    rollup_data,
    AggregateConfig,
    AggregateResult,
)
from .validatio import (
    validate_schema,
    validate_data,
    ValidationConfig,
    ValidationResult,
)
from .serializatio import (
    serialize,
    deserialize,
    SerializationFormat,
)

__all__ = [
    # Repositio
    "cache_get",
    "cache_set",
    "cache_delete",
    "cache_clear",
    "CacheConfig",
    "CacheEntry",
    # Transformatio
    "transform_data",
    "register_transformer",
    "TransformResult",
    "TransformConfig",
    # Aggregatio
    "aggregate_data",
    "rollup_data",
    "AggregateConfig",
    "AggregateResult",
    # Validatio
    "validate_schema",
    "validate_data",
    "ValidationConfig",
    "ValidationResult",
    # Serializatio
    "serialize",
    "deserialize",
    "SerializationFormat",
]
