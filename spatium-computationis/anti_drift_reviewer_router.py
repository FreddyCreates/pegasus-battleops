"""
API Router: Anti-Drift Reviewer 🔍
FastAPI router for drift auditing and validation.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .agents.anti_drift_reviewer.agent import (
    audit,
    comparative_audit,
    quick_check,
    get_drift_categories,
)

anti_drift_reviewer_router = APIRouter(
    prefix="/api/medina/anti-drift-reviewer",
    tags=["medina", "anti-drift"],
)


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class DriftAuditRequest(BaseModel):
    """Request a drift audit."""
    content: str = Field(..., description="Content to audit for drift")
    content_type: str = Field(
        "general",
        description="Type of content: output|architecture|conversation|document|general",
    )
    doctrine_context: str | None = Field(
        None,
        description="Optional doctrine context to check alignment against",
    )


class ComparativeDriftAuditRequest(BaseModel):
    """Request a comparative drift audit."""
    current_content: str = Field(..., description="Current output to evaluate")
    baseline_content: str = Field(..., description="Prior baseline to compare against")
    content_type: str = Field(
        "general",
        description="Type of content being compared",
    )


class QuickCheckRequest(BaseModel):
    """Request a quick pass/warn/fail check."""
    content: str = Field(..., description="Content to quickly check")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@anti_drift_reviewer_router.post("/audit", tags=["medina"])
async def api_audit(request: DriftAuditRequest) -> dict[str, Any]:
    """
    Perform a full drift audit on content.

    Checks for:
    - Depth drift (becoming shallow/performative)
    - Doctrine drift (departure from principles)
    - Structure drift (loss of coherence)
    - Red-team weakness (exploitable gaps)
    - State/context loss (broken continuity)
    """
    try:
        result = await audit(
            request.content,
            content_type=request.content_type,
            doctrine_context=request.doctrine_context,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")


@anti_drift_reviewer_router.post("/comparative-audit", tags=["medina"])
async def api_comparative_audit(request: ComparativeDriftAuditRequest) -> dict[str, Any]:
    """
    Compare current content against a baseline to detect drift over time.

    Returns drift trajectory and alignment scores.
    """
    try:
        result = await comparative_audit(
            request.current_content,
            request.baseline_content,
            content_type=request.content_type,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparative audit failed: {str(e)}")


@anti_drift_reviewer_router.post("/quick-check", tags=["medina"])
async def api_quick_check(request: QuickCheckRequest) -> dict[str, Any]:
    """
    Quick pass/warn/fail check without full detailed audit.

    Returns only verdict and overall score.
    """
    try:
        result = await quick_check(request.content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick check failed: {str(e)}")


@anti_drift_reviewer_router.get("/categories", tags=["medina"])
async def api_get_categories() -> dict[str, Any]:
    """
    Get the drift categories this reviewer checks for.
    """
    categories = get_drift_categories()
    return {
        "reviewer": "anti-drift-reviewer",
        "categories": categories,
        "count": len(categories),
    }


@anti_drift_reviewer_router.get("/health", tags=["medina"])
async def api_health() -> dict[str, str]:
    """Health check for the Anti-Drift Reviewer."""
    return {
        "system": "anti-drift-reviewer",
        "status": "operational",
        "glyph": "🔍",
    }
