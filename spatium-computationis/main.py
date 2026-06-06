"""
Spatium Computationis — FastAPI entrypoint
⌬ The activated computing space.
⛨ With integrated AI defense system.
🌐 Customer-facing static site & interactive app.

Start with:
  uvicorn spatium_computationis.main:app --reload
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .schemas import (
    ActionResult,
    MemoryRecord,
    RawInput,
)

# Import defense components
from .defense.honeypot.routes import honeypot_router
from .defense.dashboard.api import dashboard_router
from .defense.dashboard.websocket import defense_websocket_endpoint
from .defense.adaptive_response.routes import adaptive_response_router

# Import marketing components
from .marketing_router import marketing_router

# Import platform components
from .platform_router import platform_router

# Import frontend components
from .frontend.routes import frontend_router

app = FastAPI(
    title="Spatium Computationis ⌬",
    description=(
        "The activated computing ecosystem for furniture, interiors, "
        "and field installation projects. ⌬ = compressed project intelligence.\n\n"
        "**Defense System (⛨)**\n"
        "Integrated AI battleground with honeypots, bot fingerprinting, "
        "Cloudflare integration, and adaptive threat response.\n\n"
        "**Marketing Platform (🌐)**\n"
        "GoDaddy-focused marketing agents for website management, content creation, "
        "SEO optimization, social media, and analytics.\n\n"
        "**Agent Platform (⎈)**\n"
        "Task queue, agent discovery, inter-agent delegation, and task bots (Nuntii).\n\n"
        "**Interactive App (🖥️)**\n"
        "Customer-facing dashboard, real-time console, SSE streaming, "
        "and WebSocket-powered interactive application."
    ),
    version="0.5.0",
)

# ---------------------------------------------------------------------------
# Include Defense Routers
# ---------------------------------------------------------------------------

# Mount static files
_static_dir = Path(__file__).parent / "frontend" / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

app.include_router(honeypot_router)
app.include_router(dashboard_router, prefix="/api")
app.include_router(adaptive_response_router, prefix="/api")
app.include_router(marketing_router)
app.include_router(platform_router, prefix="/api")
app.include_router(frontend_router)


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


# ---------------------------------------------------------------------------
# Defense System Endpoints
# ---------------------------------------------------------------------------

@app.websocket("/ws/defense")
async def defense_feed(websocket: WebSocket):
    """
    WebSocket endpoint for real-time defense feed.
    
    ◎ Stream live threat events, honeypot triggers, and metrics.
    
    Commands:
    - {"type": "get_metrics", "window_minutes": 5}
    - {"type": "get_threats", "min_level": "low"}
    - {"type": "get_events", "limit": 50}
    - {"type": "get_genome", "limit": 20}
    """
    await defense_websocket_endpoint(websocket)


@app.post("/api/defense/cloudflare/event", tags=["defense"])
async def cloudflare_event(event: dict):
    """
    Webhook endpoint for Cloudflare Worker events.
    
    ⛨ Receives threat intelligence from the edge.
    """
    from .defense.threat_intel.cloudflare import CloudflareWebhook, process_cloudflare_event
    from .defense.honeypot.collector import FingerprintCollector
    
    try:
        # Parse Cloudflare event
        cf_event = CloudflareWebhook(**event)
        intel = process_cloudflare_event(cf_event)
        
        # Collect fingerprint
        FingerprintCollector.collect(
            ip_address=intel.ip_address,
            path=event.get("path", "/"),
            method=event.get("method", "GET"),
            status_code=200,
            user_agent=event.get("userAgent"),
        )
        
        return {
            "status": "received",
            "intel_id": intel.intel_id,
            "threat_level": intel.threat_level.value,
            "recommended_action": intel.recommended_action.value,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/defense/cloudflare/rules", tags=["defense"])
async def get_cloudflare_rules():
    """
    Get Cloudflare rules template for integration.
    
    ⛨ Returns configuration for Cloudflare firewall rules.
    """
    from .defense.threat_intel.cloudflare import create_cloudflare_rules_template
    return create_cloudflare_rules_template()


@app.get("/api/defense/cloudflare/worker", tags=["defense"])
async def get_cloudflare_worker():
    """
    Get Cloudflare Worker template.
    
    ⛨ Returns JavaScript code for deploying to Cloudflare Workers.
    """
    from .defense.threat_intel.cloudflare import create_cloudflare_worker_template
    return {"worker_code": create_cloudflare_worker_template()}

