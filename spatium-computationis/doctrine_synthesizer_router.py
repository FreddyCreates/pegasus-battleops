"""
API Router: Doctrine Synthesizer ⚗️
FastAPI router for converting raw ideas into structured doctrine.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .agents.doctrine_synthesizer.agent import (
    synthesize,
    extract_laws,
    expand_doctrine,
    synthesize_framework,
    get_doctrine_hierarchy,
)

doctrine_synthesizer_router = APIRouter(
    prefix="/api/medina/doctrine-synthesizer",
    tags=["medina", "doctrine"],
)


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class DoctrineSynthesisRequest(BaseModel):
    """Request doctrine synthesis."""
    raw_input: str = Field(..., description="Raw intellectual material to synthesize")
    synthesis_type: str = Field(
        "full",
        description="Type: full (complete doctrine)|laws (extract laws only)|expand (expand existing)",
    )
    existing_doctrine: dict[str, Any] | None = Field(
        None,
        description="Optional existing doctrine to expand upon",
    )


class LawExtractionRequest(BaseModel):
    """Request law extraction from raw material."""
    raw_input: str = Field(..., description="Raw material to extract laws from")


class DoctrineExpansionRequest(BaseModel):
    """Request expansion of existing doctrine."""
    raw_input: str = Field(..., description="New material to integrate")
    existing_doctrine: dict[str, Any] = Field(..., description="Existing doctrine to expand")


class FrameworkSynthesisRequest(BaseModel):
    """Request framework synthesis."""
    raw_input: str = Field(..., description="Raw material to synthesize into framework")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@doctrine_synthesizer_router.post("/synthesize", tags=["medina"])
async def api_synthesize(request: DoctrineSynthesisRequest) -> dict[str, Any]:
    """
    Convert raw ideas into structured doctrine.

    Extracts laws, principles, frameworks, maps, and taxonomies from unstructured input.
    """
    try:
        result = await synthesize(
            request.raw_input,
            synthesis_type=request.synthesis_type,
            existing_doctrine=request.existing_doctrine,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")


@doctrine_synthesizer_router.post("/extract-laws", tags=["medina"])
async def api_extract_laws(request: LawExtractionRequest) -> dict[str, Any]:
    """
    Extract only immutable laws from raw material.

    Laws are things that are always true regardless of context or time.
    """
    try:
        result = await extract_laws(request.raw_input)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Law extraction failed: {str(e)}")


@doctrine_synthesizer_router.post("/expand", tags=["medina"])
async def api_expand_doctrine(request: DoctrineExpansionRequest) -> dict[str, Any]:
    """
    Expand existing doctrine with new material.

    Integrates new input while maintaining internal consistency.
    """
    try:
        result = await expand_doctrine(request.raw_input, request.existing_doctrine)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Doctrine expansion failed: {str(e)}")


@doctrine_synthesizer_router.post("/synthesize-framework", tags=["medina"])
async def api_synthesize_framework(request: FrameworkSynthesisRequest) -> dict[str, Any]:
    """
    Synthesize a complete framework from raw input.

    Focuses on the framework map — structural models for applying principles.
    """
    try:
        result = await synthesize_framework(request.raw_input)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Framework synthesis failed: {str(e)}")


@doctrine_synthesizer_router.get("/hierarchy", tags=["medina"])
async def api_get_hierarchy() -> dict[str, Any]:
    """
    Get the doctrine hierarchy levels.

    Returns the 5 levels of doctrine organization.
    """
    hierarchy = get_doctrine_hierarchy()
    return {
        "synthesizer": "doctrine-synthesizer",
        "hierarchy": hierarchy,
        "levels": len(hierarchy),
    }


@doctrine_synthesizer_router.get("/health", tags=["medina"])
async def api_health() -> dict[str, str]:
    """Health check for the Doctrine Synthesizer."""
    return {
        "system": "doctrine-synthesizer",
        "status": "operational",
        "glyph": "⚗️",
    }
