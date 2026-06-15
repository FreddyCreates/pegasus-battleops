"""
API Router: Mission Roadmap Orchestrator 🗺️
FastAPI router for project roadmapping and execution planning.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .agents.mission_roadmap_orchestrator.agent import (
    generate_roadmap,
    update_roadmap,
    extract_next_actions,
    get_roadmap_structure,
)

mission_roadmap_router = APIRouter(
    prefix="/api/medina/mission-roadmap",
    tags=["medina", "roadmap"],
)


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class RoadmapGenerationRequest(BaseModel):
    """Request roadmap generation."""
    project_input: str = Field(..., description="Project description, vision, or initiative")
    constraints: dict[str, Any] | None = Field(
        None,
        description="Optional constraints: timeline, resources, dependencies",
    )


class RoadmapUpdateRequest(BaseModel):
    """Request roadmap update."""
    current_roadmap: dict[str, Any] = Field(..., description="Current roadmap state")
    update_input: str = Field(..., description="Status update or change request")


class NextActionsRequest(BaseModel):
    """Request immediate next actions."""
    project_input: str = Field(..., description="Project to extract actions from")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@mission_roadmap_router.post("/generate", tags=["medina"])
async def api_generate_roadmap(request: RoadmapGenerationRequest) -> dict[str, Any]:
    """
    Generate a structured roadmap from a project description.

    Produces phases, gates, branches, risks, dependencies, and compounding execution path.
    """
    try:
        result = await generate_roadmap(request.project_input, constraints=request.constraints)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Roadmap generation failed: {str(e)}")


@mission_roadmap_router.post("/update", tags=["medina"])
async def api_update_roadmap(request: RoadmapUpdateRequest) -> dict[str, Any]:
    """
    Update an existing roadmap with new status or changes.

    Tracks changes, gates passed, new risks, and adjusted critical path.
    """
    try:
        result = await update_roadmap(request.current_roadmap, request.update_input)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Roadmap update failed: {str(e)}")


@mission_roadmap_router.post("/next-actions", tags=["medina"])
async def api_extract_next_actions(request: NextActionsRequest) -> dict[str, Any]:
    """
    Extract immediate next actions from a project without full roadmap.

    Quick planning focused on what comes first.
    """
    try:
        result = await extract_next_actions(request.project_input)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Next actions extraction failed: {str(e)}")


@mission_roadmap_router.get("/structure", tags=["medina"])
async def api_get_structure() -> dict[str, Any]:
    """
    Get the roadmap architecture components.

    Returns the structure of phases, gates, branches, risks, dependencies, and compounding path.
    """
    structure = get_roadmap_structure()
    return {
        "orchestrator": "mission-roadmap",
        "architecture": structure,
    }


@mission_roadmap_router.get("/health", tags=["medina"])
async def api_health() -> dict[str, str]:
    """Health check for the Mission Roadmap Orchestrator."""
    return {
        "system": "mission-roadmap-orchestrator",
        "status": "operational",
        "glyph": "🗺️",
    }
