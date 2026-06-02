"""
Platform API Router — Spatium Computationis  ⎈

FastAPI router exposing platform layer endpoints:
- /api/platform/agents — Agent discovery & health
- /api/platform/tasks — Task queue management
- /api/platform/delegations — Inter-agent delegation
- /api/platform/bots — Bot layer (Nuntii)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .platform import (
    # Task Queue
    Task,
    TaskPriority,
    TaskStatus,
    submit_task,
    claim_task,
    complete_task,
    fail_task,
    get_task,
    get_agent_tasks,
    get_queue_stats,
    # Registry
    discover_agents,
    discover_by_capability,
    get_agent_health,
    get_platform_status,
    # Delegation
    DelegationStatus,
    delegate_to_agent,
    delegate_to_capability,
    get_delegation_status,
    # Nuntii
    get_bot,
    list_bots,
    invoke_bot,
)
from .scaffolds.base import CapabilityType


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

platform_router = APIRouter(prefix="/platform", tags=["platform"])


# ---------------------------------------------------------------------------
# Agent Discovery & Health
# ---------------------------------------------------------------------------

@platform_router.get("/agents", tags=["platform"])
async def list_agents():
    """
    ⎈ List all registered agents with their status and capabilities.
    """
    agents = discover_agents()
    return {
        "agents": [a.model_dump() for a in agents],
        "total": len(agents),
    }


@platform_router.get("/agents/{agent_name}", tags=["platform"])
async def agent_health(agent_name: str):
    """
    ⎈ Get health and status for a specific agent.
    """
    info = get_agent_health(agent_name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    return info.model_dump()


@platform_router.get("/agents/by-capability/{capability_type}", tags=["platform"])
async def agents_by_capability(capability_type: str):
    """
    ⎈ Find agents that have a specific capability type.
    """
    try:
        cap = CapabilityType(capability_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid capability type. Valid types: {[c.value for c in CapabilityType]}",
        )
    
    agents = discover_by_capability(cap)
    return {
        "capability": capability_type,
        "agents": [a.model_dump() for a in agents],
        "total": len(agents),
    }


@platform_router.get("/status", tags=["platform"])
async def platform_status():
    """
    ⎈ Get overall platform health and status dashboard.
    """
    status = get_platform_status()
    return status.model_dump()


# ---------------------------------------------------------------------------
# Task Queue
# ---------------------------------------------------------------------------

class SubmitTaskRequest(BaseModel):
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    target_agent: str | None = None
    required_capability: str | None = None
    priority: int = 3
    submitted_by: str | None = None
    project_id: str | None = None
    max_retries: int = 3
    timeout_seconds: int = 300
    ttl_seconds: int | None = None
    depends_on: list[str] = Field(default_factory=list)


class ClaimTaskRequest(BaseModel):
    agent_name: str
    task_types: list[str] | None = None


class CompleteTaskRequest(BaseModel):
    result: dict[str, Any] | None = None


class FailTaskRequest(BaseModel):
    error_message: str


@platform_router.post("/tasks", tags=["platform"])
async def submit_new_task(req: SubmitTaskRequest):
    """
    ⚙ Submit a task to the queue.
    """
    task = submit_task(
        task_type=req.task_type,
        payload=req.payload,
        target_agent=req.target_agent,
        required_capability=req.required_capability,
        priority=TaskPriority(req.priority),
        submitted_by=req.submitted_by,
        project_id=req.project_id,
        max_retries=req.max_retries,
        timeout_seconds=req.timeout_seconds,
        ttl_seconds=req.ttl_seconds,
        depends_on=req.depends_on,
    )
    return task.model_dump()


@platform_router.post("/tasks/claim", tags=["platform"])
async def claim_next_task(req: ClaimTaskRequest):
    """
    ⚙ Claim the next available task for an agent.
    """
    task = claim_task(req.agent_name, req.task_types)
    if not task:
        return {"task": None, "message": "No tasks available"}
    return task.model_dump()


@platform_router.get("/tasks/{task_id}", tags=["platform"])
async def get_task_status(task_id: str):
    """
    ⚙ Get status of a specific task.
    """
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task.model_dump()


@platform_router.post("/tasks/{task_id}/complete", tags=["platform"])
async def mark_task_complete(task_id: str, req: CompleteTaskRequest):
    """
    ⚙ Mark a task as completed with optional result.
    """
    task = complete_task(task_id, req.result)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task.model_dump()


@platform_router.post("/tasks/{task_id}/fail", tags=["platform"])
async def mark_task_failed(task_id: str, req: FailTaskRequest):
    """
    ⚙ Mark a task as failed.
    """
    task = fail_task(task_id, req.error_message)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task.model_dump()


@platform_router.get("/tasks/agent/{agent_name}", tags=["platform"])
async def get_tasks_for_agent(agent_name: str, status: str | None = None):
    """
    ⚙ Get all tasks for a specific agent.
    """
    task_status = TaskStatus(status) if status else None
    tasks = get_agent_tasks(agent_name, task_status)
    return {
        "agent": agent_name,
        "tasks": [t.model_dump() for t in tasks],
        "total": len(tasks),
    }


@platform_router.get("/queue/stats", tags=["platform"])
async def queue_statistics():
    """
    ⚙ Get task queue statistics.
    """
    stats = get_queue_stats()
    return stats.model_dump()


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------

class DelegateToAgentRequest(BaseModel):
    requesting_agent: str
    target_agent: str
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None
    priority: int = 3
    reason: str = ""
    timeout_seconds: int = 300


class DelegateToCapabilityRequest(BaseModel):
    requesting_agent: str
    capability_type: str
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = None
    priority: int = 3
    reason: str = ""
    timeout_seconds: int = 300


@platform_router.post("/delegations/to-agent", tags=["platform"])
async def delegate_work_to_agent(req: DelegateToAgentRequest):
    """
    ⇆ Delegate work to a specific agent.
    """
    try:
        delegation = delegate_to_agent(
            requesting_agent=req.requesting_agent,
            target_agent=req.target_agent,
            task_type=req.task_type,
            payload=req.payload,
            project_id=req.project_id,
            priority=TaskPriority(req.priority),
            reason=req.reason,
            timeout_seconds=req.timeout_seconds,
        )
        return delegation.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@platform_router.post("/delegations/to-capability", tags=["platform"])
async def delegate_work_to_capability(req: DelegateToCapabilityRequest):
    """
    ⇆ Delegate work to the best agent with a specific capability.
    """
    try:
        cap = CapabilityType(req.capability_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid capability type. Valid types: {[c.value for c in CapabilityType]}",
        )

    try:
        delegation = delegate_to_capability(
            requesting_agent=req.requesting_agent,
            capability_type=cap,
            task_type=req.task_type,
            payload=req.payload,
            project_id=req.project_id,
            priority=TaskPriority(req.priority),
            reason=req.reason,
            timeout_seconds=req.timeout_seconds,
        )
        return delegation.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@platform_router.get("/delegations/{delegation_id}", tags=["platform"])
async def delegation_status(delegation_id: str):
    """
    ⇆ Get status of a delegation request.
    """
    result = get_delegation_status(delegation_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Delegation '{delegation_id}' not found")
    return result.model_dump()


# ---------------------------------------------------------------------------
# Bot Layer (Nuntii)
# ---------------------------------------------------------------------------

class InvokeBotRequest(BaseModel):
    input_data: dict[str, Any] = Field(default_factory=dict)


@platform_router.get("/bots", tags=["platform"])
async def list_all_bots(category: str | None = None):
    """
    ⊡ List all available task bots.
    """
    bots = list_bots(category)
    return {
        "bots": [b.model_dump() for b in bots],
        "total": len(bots),
    }


@platform_router.get("/bots/{bot_id}", tags=["platform"])
async def get_bot_info(bot_id: str):
    """
    ⊡ Get information about a specific bot.
    """
    bot = get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail=f"Bot '{bot_id}' not found")
    return bot.model_dump()


@platform_router.post("/bots/{bot_id}/invoke", tags=["platform"])
async def invoke_bot_endpoint(bot_id: str, req: InvokeBotRequest):
    """
    ⊡ Invoke a task bot with input data.
    """
    result = await invoke_bot(bot_id, req.input_data)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.model_dump()
