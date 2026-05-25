"""
Workflow Protocols Package — Spatium Computationis

Workflow and orchestration protocols for:
- Task scheduling
- Batch processing
- Job queuing
- Workflow orchestration

Glyphs:
  ⏰ Calendarium — scheduling
  📦 Fasciculus  — batching
  📋 Ordo        — orchestration
  🔄 Cursus      — flow control
"""

from .calendarium import (
    schedule_task,
    get_scheduled_tasks,
    ScheduledTask,
    ScheduleConfig,
)
from .fasciculus import (
    create_batch,
    process_batch,
    BatchConfig,
    BatchResult,
)
from .ordo import (
    create_workflow,
    execute_workflow,
    WorkflowDefinition,
    WorkflowResult,
)
from .cursus import (
    create_pipeline,
    run_pipeline,
    PipelineConfig,
    PipelineResult,
)

__all__ = [
    # Calendarium
    "schedule_task",
    "get_scheduled_tasks",
    "ScheduledTask",
    "ScheduleConfig",
    # Fasciculus
    "create_batch",
    "process_batch",
    "BatchConfig",
    "BatchResult",
    # Ordo
    "create_workflow",
    "execute_workflow",
    "WorkflowDefinition",
    "WorkflowResult",
    # Cursus
    "create_pipeline",
    "run_pipeline",
    "PipelineConfig",
    "PipelineResult",
]
