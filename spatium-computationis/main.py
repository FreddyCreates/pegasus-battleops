"""
Spatium Computationis — FastAPI entrypoint
⌬ The activated computing space.

Start with:
  uvicorn spatium-computationis.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .schemas import (
    ActionResult,
    MemoryRecord,
    RawInput,
)

app = FastAPI(
    title="Spatium Computationis ⌬",
    description=(
        "The activated computing ecosystem for furniture, interiors, "
        "and field installation projects. ⌬ = compressed project intelligence."
    ),
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/", tags=["system"])
async def root():
    return {
        "system": "Spatium Computationis",
        "glyph": "⌬",
        "status": "active",
        "meaning": "compressed project intelligence",
    }


# ---------------------------------------------------------------------------
# Primary intelligence pipeline
# POST /ingest → runs Ingressus → Compressio → Ordinatio → Actio
# ---------------------------------------------------------------------------

@app.post("/ingest", response_model=ActionResult, tags=["pipeline"])
async def ingest(raw: RawInput) -> ActionResult:
    """
    Main entry point. Feed any project input and get back an ActionResult.

    Pipeline: →⌬ Ingressus → ⌬ Compressio → ≡ Ordinatio → ⚡ Actio
    """
    from .protocols import ingressus, compressio, ordinatio, actio

    project_input = await ingressus.process(raw)
    intel_obj = await compressio.compress(project_input)
    decision = await ordinatio.route(intel_obj)
    result = await actio.execute(decision, intel_obj)
    return result


# ---------------------------------------------------------------------------
# Field feedback loop
# POST /field-update → runs Reductus (full feedback pipeline)
# ---------------------------------------------------------------------------

@app.post("/field-update", tags=["pipeline"])
async def field_update(raw: RawInput):
    """
    Field feedback endpoint. Re-ingests field reality and cascades updates.

    Pipeline: ↺ Reductus (Ingressus + Compressio + memory update + Actio + optional RFI)
    """
    from .protocols.reductus import process_field_update

    report = await process_field_update(raw)
    return {
        "project_id": report.project_id,
        "field_input_id": report.field_input_id,
        "summary": report.summary,
        "actions_taken": len(report.actions_taken),
        "details": [
            {"agent": a.agent, "summary": a.result_summary}
            for a in report.actions_taken
        ],
        "processed_at": report.processed_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

class MemoryQuery(BaseModel):
    project_id: str | None = None
    query: str | None = None
    limit: int = 20


@app.post("/memory/recall", response_model=list[MemoryRecord], tags=["memory"])
async def memory_recall(req: MemoryQuery) -> list[MemoryRecord]:
    """Retrieve project memory records. ◉"""
    from .agents.custos_memoriae.agent import recall, search_memory

    if req.query:
        return search_memory(req.query, req.project_id, req.limit)
    return recall(req.project_id, req.limit)


# ---------------------------------------------------------------------------
# Direct agent endpoints (bypass pipeline for targeted calls)
# ---------------------------------------------------------------------------

@app.post("/agents/estimate-furniture", tags=["agents"])
async def estimate_furniture(raw: RawInput):
    """Directly invoke Estimator Mobilia (◈$) for a furniture budget."""
    from .protocols import ingressus, compressio
    from .agents.estimator_mobilia.agent import run

    project_input = await ingressus.process(raw)
    intel_obj = await compressio.compress(project_input)
    budget = await run(intel_obj)
    return budget


@app.post("/agents/estimate-labor", tags=["agents"])
async def estimate_labor(raw: RawInput):
    """Directly invoke Estimator Laboris (⚒$) for a labor bid."""
    from .protocols import ingressus, compressio
    from .agents.estimator_laboris.agent import run

    project_input = await ingressus.process(raw)
    intel_obj = await compressio.compress(project_input)
    bid = await run(intel_obj)
    return bid


@app.post("/agents/punch-list", tags=["agents"])
async def punch_list(raw: RawInput):
    """Directly invoke Inspector Campi (⟁✓) for a punch list."""
    from .protocols import ingressus, compressio
    from .agents.inspector_campi.agent import run

    project_input = await ingressus.process(raw)
    intel_obj = await compressio.compress(project_input)
    punch = await run(intel_obj)
    return punch


@app.post("/agents/install-packet", tags=["agents"])
async def install_packet(raw: RawInput):
    """Directly invoke Interpres Designii (✦⇄⚒) for an install packet."""
    from .protocols import ingressus, compressio
    from .agents.interpres_designii.agent import run

    project_input = await ingressus.process(raw)
    intel_obj = await compressio.compress(project_input)
    packet = await run(intel_obj)
    return packet
