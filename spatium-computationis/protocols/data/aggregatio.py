"""
Protocol: Aggregatio  📊
Meaning: Data aggregation and rollup.

Handles:
- Statistical aggregations
- Time-based rollups
- Grouping and summarization
- Windowed computations
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field


class AggregateFunction(str, Enum):
    """Aggregate functions."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    FIRST = "first"
    LAST = "last"
    MEDIAN = "median"
    STDEV = "stdev"
    VARIANCE = "variance"
    PERCENTILE_90 = "p90"
    PERCENTILE_95 = "p95"
    PERCENTILE_99 = "p99"


class RollupPeriod(str, Enum):
    """Time-based rollup periods."""
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class AggregateConfig(BaseModel):
    """Configuration for aggregation."""
    group_by: list[str] = Field(default_factory=list)
    aggregations: dict[str, AggregateFunction] = Field(default_factory=dict)
    
    # Time-based rollup
    time_field: str | None = None
    rollup_period: RollupPeriod | None = None
    
    # Options
    include_count: bool = True
    null_handling: str = "ignore"  # ignore, zero, error


class AggregateResult(BaseModel):
    """Result of an aggregation."""
    success: bool
    data: Any = None
    groups: int = 0
    records_processed: int = 0
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Aggregate Functions
# ---------------------------------------------------------------------------

def _compute_aggregate(values: list[Any], func: AggregateFunction) -> Any:
    """Compute an aggregate value."""
    if not values:
        return None
    
    # Filter out None values
    numeric_values = [v for v in values if v is not None and isinstance(v, (int, float))]
    
    if not numeric_values and func not in (AggregateFunction.COUNT, AggregateFunction.FIRST, AggregateFunction.LAST):
        return None
    
    if func == AggregateFunction.SUM:
        return sum(numeric_values)
    elif func == AggregateFunction.AVG:
        return statistics.mean(numeric_values) if numeric_values else None
    elif func == AggregateFunction.MIN:
        return min(numeric_values) if numeric_values else None
    elif func == AggregateFunction.MAX:
        return max(numeric_values) if numeric_values else None
    elif func == AggregateFunction.COUNT:
        return len(values)
    elif func == AggregateFunction.FIRST:
        return values[0] if values else None
    elif func == AggregateFunction.LAST:
        return values[-1] if values else None
    elif func == AggregateFunction.MEDIAN:
        return statistics.median(numeric_values) if numeric_values else None
    elif func == AggregateFunction.STDEV:
        return statistics.stdev(numeric_values) if len(numeric_values) > 1 else None
    elif func == AggregateFunction.VARIANCE:
        return statistics.variance(numeric_values) if len(numeric_values) > 1 else None
    elif func == AggregateFunction.PERCENTILE_90:
        return _percentile(numeric_values, 0.90)
    elif func == AggregateFunction.PERCENTILE_95:
        return _percentile(numeric_values, 0.95)
    elif func == AggregateFunction.PERCENTILE_99:
        return _percentile(numeric_values, 0.99)
    
    return None


def _percentile(values: list[float], p: float) -> float | None:
    """Calculate percentile of values."""
    if not values:
        return None
    sorted_values = sorted(values)
    index = int(len(sorted_values) * p)
    return sorted_values[min(index, len(sorted_values) - 1)]


def _truncate_timestamp(ts: datetime, period: RollupPeriod) -> datetime:
    """Truncate a timestamp to a period boundary."""
    if period == RollupPeriod.MINUTE:
        return ts.replace(second=0, microsecond=0)
    elif period == RollupPeriod.HOUR:
        return ts.replace(minute=0, second=0, microsecond=0)
    elif period == RollupPeriod.DAY:
        return ts.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == RollupPeriod.WEEK:
        # Start of week (Monday)
        days_since_monday = ts.weekday()
        start_of_week = ts - timedelta(days=days_since_monday)
        return start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == RollupPeriod.MONTH:
        return ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return ts


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def aggregate_data(
    data: list[dict],
    config: AggregateConfig,
) -> AggregateResult:
    """
    Protocol Aggregatio: aggregate data according to configuration.
    """
    import time
    start_time = time.perf_counter()
    
    try:
        # Group data
        groups: dict[tuple, list[dict]] = defaultdict(list)
        
        for record in data:
            # Build group key
            if config.group_by:
                key = tuple(record.get(f, None) for f in config.group_by)
            else:
                key = ("__all__",)
            
            groups[key].append(record)
        
        # Compute aggregations
        result_data = []
        
        for group_key, records in groups.items():
            result_record = {}
            
            # Add group key fields
            if config.group_by:
                for i, field in enumerate(config.group_by):
                    result_record[field] = group_key[i]
            
            # Compute aggregations
            for field, func in config.aggregations.items():
                values = [r.get(field) for r in records]
                result_record[f"{field}_{func.value}"] = _compute_aggregate(values, func)
            
            # Add count if requested
            if config.include_count:
                result_record["count"] = len(records)
            
            result_data.append(result_record)
        
        duration = (time.perf_counter() - start_time) * 1000
        
        return AggregateResult(
            success=True,
            data=result_data,
            groups=len(groups),
            records_processed=len(data),
            duration_ms=duration,
        )
        
    except Exception as e:
        duration = (time.perf_counter() - start_time) * 1000
        return AggregateResult(
            success=False,
            duration_ms=duration,
        )


async def rollup_data(
    data: list[dict],
    time_field: str,
    period: RollupPeriod,
    aggregations: dict[str, AggregateFunction],
    group_by: list[str] | None = None,
) -> AggregateResult:
    """
    Protocol Aggregatio: rollup time-series data.
    """
    import time
    start_time = time.perf_counter()
    
    try:
        # Group by time period
        groups: dict[tuple, list[dict]] = defaultdict(list)
        
        for record in data:
            # Get and truncate timestamp
            ts_value = record.get(time_field)
            if ts_value is None:
                continue
            
            if isinstance(ts_value, str):
                ts = datetime.fromisoformat(ts_value.replace("Z", "+00:00"))
            elif isinstance(ts_value, datetime):
                ts = ts_value
            else:
                continue
            
            truncated_ts = _truncate_timestamp(ts, period)
            
            # Build group key
            key_parts = [truncated_ts.isoformat()]
            if group_by:
                key_parts.extend(str(record.get(f, "")) for f in group_by)
            
            groups[tuple(key_parts)].append(record)
        
        # Compute aggregations
        result_data = []
        
        for group_key, records in groups.items():
            result_record = {
                time_field: group_key[0],
            }
            
            # Add group by fields
            if group_by:
                for i, field in enumerate(group_by):
                    result_record[field] = group_key[i + 1]
            
            # Compute aggregations
            for field, func in aggregations.items():
                values = [r.get(field) for r in records]
                result_record[f"{field}_{func.value}"] = _compute_aggregate(values, func)
            
            result_record["count"] = len(records)
            result_data.append(result_record)
        
        # Sort by time
        result_data.sort(key=lambda x: x[time_field])
        
        duration = (time.perf_counter() - start_time) * 1000
        
        return AggregateResult(
            success=True,
            data=result_data,
            groups=len(groups),
            records_processed=len(data),
            duration_ms=duration,
        )
        
    except Exception as e:
        duration = (time.perf_counter() - start_time) * 1000
        return AggregateResult(
            success=False,
            duration_ms=duration,
        )


# ---------------------------------------------------------------------------
# Aggregation Builder
# ---------------------------------------------------------------------------

class AggregationBuilder:
    """Builder for creating aggregations."""
    
    def __init__(self, data: list[dict]):
        self._data = data
        self._group_by: list[str] = []
        self._aggregations: dict[str, AggregateFunction] = {}
        self._time_field: str | None = None
        self._rollup_period: RollupPeriod | None = None
    
    def group_by(self, *fields: str) -> "AggregationBuilder":
        """Group by specified fields."""
        self._group_by.extend(fields)
        return self
    
    def sum(self, field: str) -> "AggregationBuilder":
        """Add sum aggregation."""
        self._aggregations[field] = AggregateFunction.SUM
        return self
    
    def avg(self, field: str) -> "AggregationBuilder":
        """Add average aggregation."""
        self._aggregations[field] = AggregateFunction.AVG
        return self
    
    def min(self, field: str) -> "AggregationBuilder":
        """Add min aggregation."""
        self._aggregations[field] = AggregateFunction.MIN
        return self
    
    def max(self, field: str) -> "AggregationBuilder":
        """Add max aggregation."""
        self._aggregations[field] = AggregateFunction.MAX
        return self
    
    def count(self, field: str) -> "AggregationBuilder":
        """Add count aggregation."""
        self._aggregations[field] = AggregateFunction.COUNT
        return self
    
    def rollup(self, time_field: str, period: RollupPeriod) -> "AggregationBuilder":
        """Set time-based rollup."""
        self._time_field = time_field
        self._rollup_period = period
        return self
    
    async def execute(self) -> AggregateResult:
        """Execute the aggregation."""
        if self._time_field and self._rollup_period:
            return await rollup_data(
                self._data,
                self._time_field,
                self._rollup_period,
                self._aggregations,
                self._group_by if self._group_by else None,
            )
        else:
            return await aggregate_data(
                self._data,
                AggregateConfig(
                    group_by=self._group_by,
                    aggregations=self._aggregations,
                )
            )
