"""
Protocol: Cursus  🔄
Meaning: Data pipeline and flow control.

Handles:
- Pipeline definition
- Stage-based processing
- Data flow management
- Pipeline monitoring
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field


class PipelineStatus(str, Enum):
    """Pipeline execution status."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class StageStatus(str, Enum):
    """Stage execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStage(BaseModel):
    """A stage in a pipeline."""
    stage_id: str
    name: str
    processor: str
    
    # Configuration
    config: dict[str, Any] = Field(default_factory=dict)
    
    # Options
    parallel: bool = False
    continue_on_failure: bool = False
    timeout_seconds: int = 300


class PipelineConfig(BaseModel):
    """Configuration for a pipeline."""
    pipeline_id: str
    name: str
    description: str = ""
    
    # Stages
    stages: list[PipelineStage] = Field(default_factory=list)
    
    # Options
    fail_fast: bool = True
    max_concurrent_stages: int = 5
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StageResult(BaseModel):
    """Result of a pipeline stage."""
    stage_id: str
    name: str
    status: StageStatus
    
    # Input/Output
    input_records: int = 0
    output_records: int = 0
    
    # Data
    data: Any = None
    
    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None
    
    # Error
    error: str | None = None


class PipelineResult(BaseModel):
    """Result of pipeline execution."""
    execution_id: str
    pipeline_id: str
    name: str
    status: PipelineStatus
    
    # Stage results
    stage_results: list[StageResult] = Field(default_factory=list)
    
    # Statistics
    total_stages: int = 0
    completed_stages: int = 0
    failed_stages: int = 0
    
    # Output
    final_output: Any = None
    
    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None
    
    # Error
    error: str | None = None


# ---------------------------------------------------------------------------
# Processor Registry
# ---------------------------------------------------------------------------

_stage_processors: dict[str, Callable[[Any, dict], Awaitable[Any]]] = {}


def register_stage_processor(name: str, processor: Callable[[Any, dict], Awaitable[Any]]) -> None:
    """Register a pipeline stage processor."""
    _stage_processors[name] = processor


# Built-in processors
async def _passthrough_processor(data: Any, config: dict) -> Any:
    """Pass data through unchanged."""
    return data


async def _filter_processor(data: Any, config: dict) -> Any:
    """Filter records based on condition."""
    if not isinstance(data, list):
        return data
    
    field = config.get("field")
    value = config.get("value")
    operator = config.get("operator", "eq")
    
    if not field:
        return data
    
    result = []
    for record in data:
        if isinstance(record, dict) and field in record:
            record_value = record[field]
            if operator == "eq" and record_value == value:
                result.append(record)
            elif operator == "ne" and record_value != value:
                result.append(record)
            elif operator == "gt" and record_value > value:
                result.append(record)
            elif operator == "lt" and record_value < value:
                result.append(record)
            elif operator == "contains" and value in str(record_value):
                result.append(record)
    
    return result


async def _map_processor(data: Any, config: dict) -> Any:
    """Map fields in records."""
    if not isinstance(data, list):
        return data
    
    field_mapping = config.get("mapping", {})
    
    result = []
    for record in data:
        if isinstance(record, dict):
            new_record = {}
            for old_key, new_key in field_mapping.items():
                if old_key in record:
                    new_record[new_key] = record[old_key]
            result.append(new_record)
        else:
            result.append(record)
    
    return result


async def _aggregate_processor(data: Any, config: dict) -> Any:
    """Aggregate records."""
    if not isinstance(data, list):
        return data
    
    group_by = config.get("group_by")
    agg_field = config.get("field")
    agg_func = config.get("function", "count")
    
    if not group_by or not agg_field:
        return {"count": len(data)}
    
    groups: dict[str, list] = {}
    for record in data:
        if isinstance(record, dict):
            key = str(record.get(group_by, "unknown"))
            if key not in groups:
                groups[key] = []
            groups[key].append(record.get(agg_field))
    
    result = []
    for key, values in groups.items():
        values = [v for v in values if v is not None]
        if agg_func == "count":
            agg_value = len(values)
        elif agg_func == "sum":
            agg_value = sum(values) if values else 0
        elif agg_func == "avg":
            agg_value = sum(values) / len(values) if values else 0
        elif agg_func == "min":
            agg_value = min(values) if values else None
        elif agg_func == "max":
            agg_value = max(values) if values else None
        else:
            agg_value = len(values)
        
        result.append({group_by: key, f"{agg_field}_{agg_func}": agg_value})
    
    return result


register_stage_processor("passthrough", _passthrough_processor)
register_stage_processor("filter", _filter_processor)
register_stage_processor("map", _map_processor)
register_stage_processor("aggregate", _aggregate_processor)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def create_pipeline(
    name: str,
    stages: list[PipelineStage],
    description: str = "",
) -> PipelineConfig:
    """
    Protocol Cursus: create a data pipeline.
    """
    pipeline_id = str(uuid.uuid4())
    
    return PipelineConfig(
        pipeline_id=pipeline_id,
        name=name,
        description=description,
        stages=stages,
    )


async def run_pipeline(
    pipeline: PipelineConfig,
    input_data: Any,
) -> PipelineResult:
    """
    Protocol Cursus: run a data pipeline.
    """
    execution_id = str(uuid.uuid4())
    start_time = time.perf_counter()
    now = datetime.now(timezone.utc)
    
    stage_results: list[StageResult] = []
    current_data = input_data
    error = None
    
    for stage in pipeline.stages:
        stage_start = time.perf_counter()
        stage_started_at = datetime.now(timezone.utc)
        
        try:
            processor = _stage_processors.get(stage.processor)
            if not processor:
                raise ValueError(f"Processor not found: {stage.processor}")
            
            # Determine input records count
            input_records = len(current_data) if isinstance(current_data, list) else 1
            
            # Execute stage with timeout
            output_data = await asyncio.wait_for(
                processor(current_data, stage.config),
                timeout=stage.timeout_seconds,
            )
            
            # Determine output records count
            output_records = len(output_data) if isinstance(output_data, list) else 1
            
            stage_duration = (time.perf_counter() - stage_start) * 1000
            
            stage_results.append(StageResult(
                stage_id=stage.stage_id,
                name=stage.name,
                status=StageStatus.COMPLETED,
                input_records=input_records,
                output_records=output_records,
                data=output_data,
                started_at=stage_started_at,
                completed_at=datetime.now(timezone.utc),
                duration_ms=stage_duration,
            ))
            
            current_data = output_data
            
        except Exception as e:
            stage_duration = (time.perf_counter() - stage_start) * 1000
            
            stage_results.append(StageResult(
                stage_id=stage.stage_id,
                name=stage.name,
                status=StageStatus.FAILED,
                started_at=stage_started_at,
                completed_at=datetime.now(timezone.utc),
                duration_ms=stage_duration,
                error=str(e),
            ))
            
            if not stage.continue_on_failure and pipeline.fail_fast:
                error = f"Stage '{stage.name}' failed: {str(e)}"
                break
    
    # Calculate summary
    duration_ms = (time.perf_counter() - start_time) * 1000
    completed_stages = sum(1 for r in stage_results if r.status == StageStatus.COMPLETED)
    failed_stages = sum(1 for r in stage_results if r.status == StageStatus.FAILED)
    
    if error:
        status = PipelineStatus.FAILED
    elif failed_stages > 0:
        status = PipelineStatus.FAILED
    else:
        status = PipelineStatus.COMPLETED
    
    return PipelineResult(
        execution_id=execution_id,
        pipeline_id=pipeline.pipeline_id,
        name=pipeline.name,
        status=status,
        stage_results=stage_results,
        total_stages=len(pipeline.stages),
        completed_stages=completed_stages,
        failed_stages=failed_stages,
        final_output=current_data,
        started_at=now,
        completed_at=datetime.now(timezone.utc),
        duration_ms=duration_ms,
        error=error,
    )


# ---------------------------------------------------------------------------
# Pipeline Builder
# ---------------------------------------------------------------------------

class PipelineBuilder:
    """Builder for creating pipelines."""
    
    def __init__(self, name: str, description: str = ""):
        self._name = name
        self._description = description
        self._stages: list[PipelineStage] = []
        self._stage_counter = 0
    
    def add_stage(
        self,
        name: str,
        processor: str,
        config: dict[str, Any] | None = None,
        continue_on_failure: bool = False,
    ) -> "PipelineBuilder":
        """Add a stage to the pipeline."""
        self._stage_counter += 1
        self._stages.append(PipelineStage(
            stage_id=f"stage_{self._stage_counter}",
            name=name,
            processor=processor,
            config=config or {},
            continue_on_failure=continue_on_failure,
        ))
        return self
    
    def filter(self, field: str, operator: str, value: Any) -> "PipelineBuilder":
        """Add a filter stage."""
        return self.add_stage(
            f"filter_{field}",
            "filter",
            {"field": field, "operator": operator, "value": value},
        )
    
    def map(self, mapping: dict[str, str]) -> "PipelineBuilder":
        """Add a map stage."""
        return self.add_stage("map_fields", "map", {"mapping": mapping})
    
    def aggregate(
        self,
        group_by: str,
        field: str,
        function: str = "count",
    ) -> "PipelineBuilder":
        """Add an aggregate stage."""
        return self.add_stage(
            f"aggregate_{function}",
            "aggregate",
            {"group_by": group_by, "field": field, "function": function},
        )
    
    async def build(self) -> PipelineConfig:
        """Build the pipeline."""
        return await create_pipeline(self._name, self._stages, self._description)
    
    async def run(self, input_data: Any) -> PipelineResult:
        """Build and run the pipeline."""
        pipeline = await self.build()
        return await run_pipeline(pipeline, input_data)
