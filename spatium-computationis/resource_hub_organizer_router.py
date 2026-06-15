"""
API Router: Resource Hub Organizer 📂
FastAPI router for organizing and managing intellectual resources.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .agents.resource_hub_organizer.agent import (
    organize,
    add_to_organization,
    generate_release_path,
    suggest_collections,
    get_organization_principles,
)

resource_hub_organizer_router = APIRouter(
    prefix="/api/medina/resource-hub",
    tags=["medina", "resource-hub"],
)


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class OrganizationRequest(BaseModel):
    """Request material organization."""
    material: str = Field(..., description="Intellectual material to organize")
    material_type: str = Field(
        "mixed",
        description="Type of material: ideas|documents|doctrine|projects|mixed",
    )
    existing_organization: dict[str, Any] | None = Field(
        None,
        description="Optional existing organization to integrate into",
    )


class AddToOrganizationRequest(BaseModel):
    """Request to add material to existing organization."""
    new_material: str = Field(..., description="New material to add")
    existing_organization: dict[str, Any] = Field(..., description="Existing organization")


class ReleasePathRequest(BaseModel):
    """Request release path generation."""
    organization: dict[str, Any] = Field(..., description="Organized material")
    target_audience: str = Field(..., description="Target audience for release")
    format_type: str = Field(
        "series",
        description="Format: article|whitepaper|series|course|reference",
    )


class CollectionSuggestionRequest(BaseModel):
    """Request collection suggestions."""
    material: str = Field(..., description="Material to suggest collections for")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@resource_hub_organizer_router.post("/organize", tags=["medina"])
async def api_organize(request: OrganizationRequest) -> dict[str, Any]:
    """
    Organize material into a structured resource hierarchy.

    Produces topics, subtopics, sub-subtopics, collections, and release paths.
    """
    try:
        result = await organize(
            request.material,
            material_type=request.material_type,
            existing_organization=request.existing_organization,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Organization failed: {str(e)}")


@resource_hub_organizer_router.post("/add", tags=["medina"])
async def api_add_to_organization(request: AddToOrganizationRequest) -> dict[str, Any]:
    """
    Add new material to an existing organization structure.

    Maintains consistency while integrating new content.
    """
    try:
        result = await add_to_organization(request.new_material, request.existing_organization)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Adding to organization failed: {str(e)}")


@resource_hub_organizer_router.post("/release-path", tags=["medina"])
async def api_generate_release_path(request: ReleasePathRequest) -> dict[str, Any]:
    """
    Generate a release path for organized material.

    Creates optimal sequencing for publishing/sharing to target audience.
    """
    try:
        result = await generate_release_path(
            request.organization,
            target_audience=request.target_audience,
            format_type=request.format_type,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Release path generation failed: {str(e)}")


@resource_hub_organizer_router.post("/suggest-collections", tags=["medina"])
async def api_suggest_collections(request: CollectionSuggestionRequest) -> dict[str, Any]:
    """
    Suggest collections for material without full organization.

    Quick collection recommendations for release packaging.
    """
    try:
        result = await suggest_collections(request.material)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Collection suggestion failed: {str(e)}")


@resource_hub_organizer_router.get("/principles", tags=["medina"])
async def api_get_principles() -> dict[str, Any]:
    """
    Get the organizing principles used by this agent.

    Returns the 7 principles for information organization.
    """
    principles = get_organization_principles()
    return {
        "organizer": "resource-hub-organizer",
        "principles": principles,
        "count": len(principles),
    }


@resource_hub_organizer_router.get("/health", tags=["medina"])
async def api_health() -> dict[str, str]:
    """Health check for the Resource Hub Organizer."""
    return {
        "system": "resource-hub-organizer",
        "status": "operational",
        "glyph": "📂",
    }
