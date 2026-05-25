"""
Protocol: Transformatio  🔀
Meaning: Data transformation and mapping.

Handles:
- Schema transformation
- Field mapping
- Data enrichment
- Format conversion
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class TransformOperation(str, Enum):
    """Types of transform operations."""
    MAP = "map"           # Map fields
    FILTER = "filter"     # Filter records
    FLATTEN = "flatten"   # Flatten nested data
    GROUP = "group"       # Group by field
    SORT = "sort"         # Sort records
    ENRICH = "enrich"     # Add computed fields
    RENAME = "rename"     # Rename fields
    CONVERT = "convert"   # Convert types


class TransformConfig(BaseModel):
    """Configuration for a transformation."""
    operation: TransformOperation
    source_fields: list[str] = Field(default_factory=list)
    target_field: str | None = None
    
    # For mapping
    field_mapping: dict[str, str] = Field(default_factory=dict)
    
    # For filtering
    filter_condition: str | None = None
    
    # For type conversion
    type_conversions: dict[str, str] = Field(default_factory=dict)
    
    # For enrichment
    enrichment_fn: str | None = None
    
    # Options
    preserve_original: bool = True
    fail_on_error: bool = False


class TransformResult(BaseModel):
    """Result of a transformation."""
    success: bool
    data: Any = None
    records_processed: int = 0
    records_transformed: int = 0
    records_filtered: int = 0
    errors: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Transformer Registry
# ---------------------------------------------------------------------------

_transformers: dict[str, Callable[[Any, TransformConfig], Any]] = {}


def register_transformer(
    name: str,
    transformer_fn: Callable[[Any, TransformConfig], Any],
) -> None:
    """Register a custom transformer."""
    _transformers[name] = transformer_fn


# ---------------------------------------------------------------------------
# Built-in Transformers
# ---------------------------------------------------------------------------

def _map_fields(data: list[dict], config: TransformConfig) -> list[dict]:
    """Map fields from source to target names."""
    result = []
    for record in data:
        new_record = {} if not config.preserve_original else dict(record)
        for source, target in config.field_mapping.items():
            if source in record:
                new_record[target] = record[source]
                if not config.preserve_original and source != target:
                    new_record.pop(source, None)
        result.append(new_record)
    return result


def _filter_records(data: list[dict], config: TransformConfig) -> list[dict]:
    """Filter records based on condition."""
    if not config.filter_condition:
        return data
    
    result = []
    for record in data:
        try:
            # Simple condition evaluation (field == value, field > value, etc.)
            condition = config.filter_condition
            for key, value in record.items():
                condition = condition.replace(f"${key}", repr(value))
            
            if eval(condition):  # Note: In production, use a safe evaluator
                result.append(record)
        except Exception:
            if config.fail_on_error:
                raise
    return result


def _flatten_data(data: list[dict], config: TransformConfig) -> list[dict]:
    """Flatten nested dictionary structures."""
    def flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key, sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    return [flatten_dict(record) for record in data]


def _rename_fields(data: list[dict], config: TransformConfig) -> list[dict]:
    """Rename fields in records."""
    result = []
    for record in data:
        new_record = dict(record)
        for old_name, new_name in config.field_mapping.items():
            if old_name in new_record:
                new_record[new_name] = new_record.pop(old_name)
        result.append(new_record)
    return result


def _convert_types(data: list[dict], config: TransformConfig) -> list[dict]:
    """Convert field types."""
    type_converters = {
        "str": str,
        "int": int,
        "float": float,
        "bool": lambda x: x.lower() in ("true", "1", "yes") if isinstance(x, str) else bool(x),
        "list": lambda x: json.loads(x) if isinstance(x, str) else list(x),
        "dict": lambda x: json.loads(x) if isinstance(x, str) else dict(x),
    }
    
    result = []
    for record in data:
        new_record = dict(record)
        for field, target_type in config.type_conversions.items():
            if field in new_record and target_type in type_converters:
                try:
                    new_record[field] = type_converters[target_type](new_record[field])
                except Exception:
                    if config.fail_on_error:
                        raise
        result.append(new_record)
    return result


def _sort_records(data: list[dict], config: TransformConfig) -> list[dict]:
    """Sort records by specified fields."""
    if not config.source_fields:
        return data
    
    return sorted(data, key=lambda x: tuple(x.get(f, "") for f in config.source_fields))


def _group_records(data: list[dict], config: TransformConfig) -> dict[str, list[dict]]:
    """Group records by field value."""
    if not config.source_fields:
        return {"all": data}
    
    groups: dict[str, list[dict]] = {}
    group_field = config.source_fields[0]
    
    for record in data:
        key = str(record.get(group_field, "unknown"))
        if key not in groups:
            groups[key] = []
        groups[key].append(record)
    
    return groups


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def transform_data(
    data: Any,
    config: TransformConfig | list[TransformConfig],
) -> TransformResult:
    """
    Protocol Transformatio: transform data according to configuration.
    """
    import time
    start_time = time.perf_counter()
    
    configs = config if isinstance(config, list) else [config]
    current_data = data
    total_processed = 0
    total_transformed = 0
    total_filtered = 0
    errors: list[str] = []
    
    try:
        for cfg in configs:
            # Ensure data is a list for most operations
            if isinstance(current_data, dict) and cfg.operation != TransformOperation.FLATTEN:
                current_data = [current_data]
            
            input_count = len(current_data) if isinstance(current_data, list) else 1
            total_processed += input_count
            
            # Apply transformation
            if cfg.operation == TransformOperation.MAP:
                current_data = _map_fields(current_data, cfg)
            elif cfg.operation == TransformOperation.FILTER:
                current_data = _filter_records(current_data, cfg)
                total_filtered += input_count - len(current_data)
            elif cfg.operation == TransformOperation.FLATTEN:
                current_data = _flatten_data(current_data, cfg)
            elif cfg.operation == TransformOperation.RENAME:
                current_data = _rename_fields(current_data, cfg)
            elif cfg.operation == TransformOperation.CONVERT:
                current_data = _convert_types(current_data, cfg)
            elif cfg.operation == TransformOperation.SORT:
                current_data = _sort_records(current_data, cfg)
            elif cfg.operation == TransformOperation.GROUP:
                current_data = _group_records(current_data, cfg)
            elif cfg.operation == TransformOperation.ENRICH:
                if cfg.enrichment_fn and cfg.enrichment_fn in _transformers:
                    current_data = _transformers[cfg.enrichment_fn](current_data, cfg)
            
            output_count = len(current_data) if isinstance(current_data, (list, dict)) else 1
            total_transformed += output_count
        
        duration = (time.perf_counter() - start_time) * 1000
        
        return TransformResult(
            success=True,
            data=current_data,
            records_processed=total_processed,
            records_transformed=total_transformed,
            records_filtered=total_filtered,
            errors=errors,
            duration_ms=duration,
        )
        
    except Exception as e:
        duration = (time.perf_counter() - start_time) * 1000
        errors.append(str(e))
        
        return TransformResult(
            success=False,
            data=current_data,
            records_processed=total_processed,
            records_transformed=total_transformed,
            records_filtered=total_filtered,
            errors=errors,
            duration_ms=duration,
        )


# ---------------------------------------------------------------------------
# Pipeline Builder
# ---------------------------------------------------------------------------

class TransformPipeline:
    """Builder for creating transformation pipelines."""
    
    def __init__(self):
        self._steps: list[TransformConfig] = []
    
    def map(self, field_mapping: dict[str, str]) -> "TransformPipeline":
        """Add a field mapping step."""
        self._steps.append(TransformConfig(
            operation=TransformOperation.MAP,
            field_mapping=field_mapping,
        ))
        return self
    
    def filter(self, condition: str) -> "TransformPipeline":
        """Add a filter step."""
        self._steps.append(TransformConfig(
            operation=TransformOperation.FILTER,
            filter_condition=condition,
        ))
        return self
    
    def flatten(self) -> "TransformPipeline":
        """Add a flatten step."""
        self._steps.append(TransformConfig(
            operation=TransformOperation.FLATTEN,
        ))
        return self
    
    def rename(self, field_mapping: dict[str, str]) -> "TransformPipeline":
        """Add a rename step."""
        self._steps.append(TransformConfig(
            operation=TransformOperation.RENAME,
            field_mapping=field_mapping,
        ))
        return self
    
    def convert(self, type_conversions: dict[str, str]) -> "TransformPipeline":
        """Add a type conversion step."""
        self._steps.append(TransformConfig(
            operation=TransformOperation.CONVERT,
            type_conversions=type_conversions,
        ))
        return self
    
    def sort(self, *fields: str) -> "TransformPipeline":
        """Add a sort step."""
        self._steps.append(TransformConfig(
            operation=TransformOperation.SORT,
            source_fields=list(fields),
        ))
        return self
    
    def group(self, field: str) -> "TransformPipeline":
        """Add a group step."""
        self._steps.append(TransformConfig(
            operation=TransformOperation.GROUP,
            source_fields=[field],
        ))
        return self
    
    async def execute(self, data: Any) -> TransformResult:
        """Execute the transformation pipeline."""
        return await transform_data(data, self._steps)
