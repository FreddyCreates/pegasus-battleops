"""
Protocol: Metrica  📊
Meaning: Collect and aggregate metrics.

Handles:
- Counter metrics (monotonically increasing)
- Gauge metrics (point-in-time values)
- Histogram metrics (distribution of values)
- Timer metrics (duration measurements)
"""

from __future__ import annotations

import json
import sqlite3
import statistics
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"      # Monotonically increasing count
    GAUGE = "gauge"          # Point-in-time value
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"          # Duration measurements
    SUMMARY = "summary"      # Summary statistics


class MetricValue(BaseModel):
    """A single metric value."""
    metric_id: str
    name: str
    metric_type: MetricType
    value: float
    labels: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    unit: str | None = None


class MetricsSnapshot(BaseModel):
    """Snapshot of all current metrics."""
    snapshot_id: str
    metrics: list[MetricValue] = Field(default_factory=list)
    
    # Aggregations
    counters: dict[str, float] = Field(default_factory=dict)
    gauges: dict[str, float] = Field(default_factory=dict)
    histograms: dict[str, dict[str, float]] = Field(default_factory=dict)
    
    # Metadata
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    collection_duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "metrics.db"


def _init_metrics_db() -> None:
    """Initialize the metrics database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Metrics values
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metric_values (
                metric_id       TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                metric_type     TEXT NOT NULL,
                value           REAL NOT NULL,
                labels          TEXT DEFAULT '{}',
                timestamp       TEXT NOT NULL,
                unit            TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mv_name ON metric_values(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mv_type ON metric_values(metric_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mv_time ON metric_values(timestamp)")
        
        # Counters (accumulated values)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS counters (
                name            TEXT NOT NULL,
                labels_hash     TEXT NOT NULL,
                labels          TEXT DEFAULT '{}',
                value           REAL DEFAULT 0,
                updated_at      TEXT NOT NULL,
                PRIMARY KEY (name, labels_hash)
            )
            """
        )
        
        # Histogram buckets
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS histogram_values (
                name            TEXT NOT NULL,
                labels_hash     TEXT NOT NULL,
                bucket          REAL NOT NULL,
                count           INTEGER DEFAULT 0,
                updated_at      TEXT NOT NULL,
                PRIMARY KEY (name, labels_hash, bucket)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hv_name ON histogram_values(name)")
        
        conn.commit()


_init_metrics_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# In-memory Metrics (for high-frequency recording)
# ---------------------------------------------------------------------------

_counters: dict[str, float] = defaultdict(float)
_gauges: dict[str, float] = {}
_histograms: dict[str, list[float]] = defaultdict(list)
_timers: dict[str, list[float]] = defaultdict(list)


def _labels_to_key(name: str, labels: dict[str, str]) -> str:
    """Convert name + labels to a unique key."""
    if labels:
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    return name


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def record_metric(
    name: str,
    value: float,
    metric_type: MetricType = MetricType.GAUGE,
    labels: dict[str, str] | None = None,
    unit: str | None = None,
    persist: bool = False,
) -> MetricValue:
    """
    Protocol Metrica: record a metric value.
    """
    metric_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    effective_labels = labels or {}
    key = _labels_to_key(name, effective_labels)
    
    # Update in-memory storage
    if metric_type == MetricType.COUNTER:
        _counters[key] += value
        actual_value = _counters[key]
    elif metric_type == MetricType.GAUGE:
        _gauges[key] = value
        actual_value = value
    elif metric_type == MetricType.HISTOGRAM:
        _histograms[key].append(value)
        # Keep last 1000 values
        if len(_histograms[key]) > 1000:
            _histograms[key] = _histograms[key][-1000:]
        actual_value = value
    elif metric_type == MetricType.TIMER:
        _timers[key].append(value)
        if len(_timers[key]) > 1000:
            _timers[key] = _timers[key][-1000:]
        actual_value = value
    else:
        actual_value = value
    
    metric = MetricValue(
        metric_id=metric_id,
        name=name,
        metric_type=metric_type,
        value=actual_value,
        labels=effective_labels,
        timestamp=now,
        unit=unit,
    )
    
    # Optionally persist to database
    if persist:
        _persist_metric(metric)
    
    return metric


async def increment_counter(
    name: str,
    value: float = 1.0,
    labels: dict[str, str] | None = None,
) -> float:
    """Increment a counter metric."""
    metric = await record_metric(name, value, MetricType.COUNTER, labels)
    return metric.value


async def set_gauge(
    name: str,
    value: float,
    labels: dict[str, str] | None = None,
) -> float:
    """Set a gauge metric."""
    metric = await record_metric(name, value, MetricType.GAUGE, labels)
    return metric.value


async def record_histogram(
    name: str,
    value: float,
    labels: dict[str, str] | None = None,
) -> None:
    """Record a histogram value."""
    await record_metric(name, value, MetricType.HISTOGRAM, labels)


async def record_timer(
    name: str,
    duration_ms: float,
    labels: dict[str, str] | None = None,
) -> None:
    """Record a timer value in milliseconds."""
    await record_metric(name, duration_ms, MetricType.TIMER, labels, unit="ms")


class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, name: str, labels: dict[str, str] | None = None):
        self.name = name
        self.labels = labels
        self.start_time: float | None = None
        self.duration_ms: float | None = None
    
    async def __aenter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.start_time:
            self.duration_ms = (time.perf_counter() - self.start_time) * 1000
            await record_timer(self.name, self.duration_ms, self.labels)


async def get_metrics(
    names: list[str] | None = None,
    metric_type: MetricType | None = None,
) -> MetricsSnapshot:
    """
    Protocol Metrica: get current metrics.
    """
    start = time.perf_counter()
    snapshot_id = str(uuid.uuid4())
    metrics: list[MetricValue] = []
    now = datetime.now(timezone.utc)
    
    # Collect counters
    counters_dict = {}
    for key, value in _counters.items():
        if names is None or any(key.startswith(n) for n in names):
            if metric_type is None or metric_type == MetricType.COUNTER:
                counters_dict[key] = value
                metrics.append(MetricValue(
                    metric_id=str(uuid.uuid4()),
                    name=key,
                    metric_type=MetricType.COUNTER,
                    value=value,
                    timestamp=now,
                ))
    
    # Collect gauges
    gauges_dict = {}
    for key, value in _gauges.items():
        if names is None or any(key.startswith(n) for n in names):
            if metric_type is None or metric_type == MetricType.GAUGE:
                gauges_dict[key] = value
                metrics.append(MetricValue(
                    metric_id=str(uuid.uuid4()),
                    name=key,
                    metric_type=MetricType.GAUGE,
                    value=value,
                    timestamp=now,
                ))
    
    # Collect histogram statistics
    histograms_dict = {}
    for key, values in _histograms.items():
        if names is None or any(key.startswith(n) for n in names):
            if metric_type is None or metric_type == MetricType.HISTOGRAM:
                if values:
                    stats = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "mean": statistics.mean(values),
                        "median": statistics.median(values),
                        "p95": values[int(len(values) * 0.95)] if len(values) > 20 else max(values),
                        "p99": values[int(len(values) * 0.99)] if len(values) > 100 else max(values),
                    }
                    if len(values) > 1:
                        stats["stdev"] = statistics.stdev(values)
                    histograms_dict[key] = stats
    
    # Collect timer statistics (same as histogram)
    for key, values in _timers.items():
        if names is None or any(key.startswith(n) for n in names):
            if metric_type is None or metric_type == MetricType.TIMER:
                if values:
                    stats = {
                        "count": len(values),
                        "min_ms": min(values),
                        "max_ms": max(values),
                        "mean_ms": statistics.mean(values),
                        "median_ms": statistics.median(values),
                        "p95_ms": values[int(len(values) * 0.95)] if len(values) > 20 else max(values),
                        "p99_ms": values[int(len(values) * 0.99)] if len(values) > 100 else max(values),
                    }
                    if len(values) > 1:
                        stats["stdev_ms"] = statistics.stdev(values)
                    histograms_dict[key] = stats
    
    duration = (time.perf_counter() - start) * 1000
    
    return MetricsSnapshot(
        snapshot_id=snapshot_id,
        metrics=metrics,
        counters=counters_dict,
        gauges=gauges_dict,
        histograms=histograms_dict,
        collected_at=now,
        collection_duration_ms=duration,
    )


def _persist_metric(metric: MetricValue) -> None:
    """Persist a metric to the database."""
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO metric_values (metric_id, name, metric_type, value, labels, timestamp, unit)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metric.metric_id,
                metric.name,
                metric.metric_type.value,
                metric.value,
                json.dumps(metric.labels),
                metric.timestamp.isoformat(),
                metric.unit,
            )
        )
        conn.commit()


async def get_metric_history(
    name: str,
    hours: int = 24,
    limit: int = 1000,
) -> list[MetricValue]:
    """Get historical values for a metric."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM metric_values 
            WHERE name = ? AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (name, cutoff.isoformat(), limit)
        ).fetchall()
        
        return [
            MetricValue(
                metric_id=row["metric_id"],
                name=row["name"],
                metric_type=MetricType(row["metric_type"]),
                value=row["value"],
                labels=json.loads(row["labels"]) if row["labels"] else {},
                timestamp=datetime.fromisoformat(row["timestamp"]),
                unit=row["unit"],
            )
            for row in rows
        ]


async def reset_metrics() -> None:
    """Reset all in-memory metrics."""
    _counters.clear()
    _gauges.clear()
    _histograms.clear()
    _timers.clear()
