"""
API Router: Medina Operating System 🧠
FastAPI router for the core cognitive operating framework.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .agents.medina_operating_system.agent import (
    process,
    extract_doctrine_alignment,
    synthesize,
    perceive,
    get_operating_principles,
)

medina_operating_system_router = APIRouter(
    prefix="/api/medina/operating-system",
    tags=["medina", "operating-system"],
)


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class MedinaProcessRequest(BaseModel):
    """Request to process through full OIS."""
    input_text: str = Field(..., description="Raw input to process through cognitive framework")
    processing_mode: str = Field(
        "full",
        description="Processing mode: full|perception|synthesis|doctrine",
    )
    context_state: dict[str, Any] | None = Field(
        None,
        description="Optional prior context state for session continuity",
    )


class MedinaPerceptionRequest(BaseModel):
    """Request perception layer only."""
    input_text: str = Field(..., description="Input to perceive")


class MedinaSynthesisRequest(BaseModel):
    """Request synthesis layer."""
    input_text: str = Field(..., description="Input to synthesize")
    context_state: dict[str, Any] | None = Field(None, description="Optional context state")


class MedinaDoctrineAlignmentRequest(BaseModel):
    """Request quick doctrine alignment check."""
    input_text: str = Field(..., description="Input to check for doctrine alignment")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@medina_operating_system_router.post("/process", tags=["medina"])
async def api_process(request: MedinaProcessRequest) -> dict[str, Any]:
    """
    Process input through the full Medina Operating System.

    This applies all cognitive layers: perception, reasoning, synthesis, and state tracking.
    """
    try:
        result = await process(
            request.input_text,
            context_state=request.context_state,
            processing_mode=request.processing_mode,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@medina_operating_system_router.post("/perceive", tags=["medina"])
async def api_perceive(request: MedinaPerceptionRequest) -> dict[str, Any]:
    """
    Perception layer only — strip noise, identify signal.
    """
    try:
        result = await perceive(request.input_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Perception failed: {str(e)}")


@medina_operating_system_router.post("/synthesize", tags=["medina"])
async def api_synthesize(request: MedinaSynthesisRequest) -> dict[str, Any]:
    """
    Synthesis layer only — produce actionable output from input.
    """
    try:
        result = await synthesize(request.input_text, context_state=request.context_state)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")


@medina_operating_system_router.post("/doctrine-alignment", tags=["medina"])
async def api_doctrine_alignment(request: MedinaDoctrineAlignmentRequest) -> dict[str, Any]:
    """
    Quick doctrine alignment check without full processing.
    """
    try:
        result = await extract_doctrine_alignment(request.input_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Doctrine alignment check failed: {str(e)}")


@medina_operating_system_router.get("/principles", tags=["medina"])
async def api_get_principles() -> dict[str, Any]:
    """
    Get the core operating principles of the Medina Operating System.
    """
    principles = get_operating_principles()
    return {
        "operating_system": "Medina",
        "principles": principles,
        "count": len(principles),
    }


@medina_operating_system_router.get("/health", tags=["medina"])
async def api_health() -> dict[str, str]:
    """Health check for the Medina Operating System."""
    return {
        "system": "medina-operating-system",
        "status": "operational",
        "glyph": "🧠",
    }
