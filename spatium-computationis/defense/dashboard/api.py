"""
Defense Dashboard API — REST Endpoints for Dashboard
◎ Metrics, threats, and defense management.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..schemas import (
    AdaptiveAction,
    BotFingerprint,
    DefenseMetrics,
    HoneypotEvent,
    ThreatGenome,
    ThreatLevel,
    ThreatRecord,
)


dashboard_router = APIRouter(prefix="/defense", tags=["defense-dashboard"])


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class MetricsRequest(BaseModel):
    window_minutes: int = 5


class ThreatActionRequest(BaseModel):
    fingerprint_id: str
    action: AdaptiveAction
    reason: str | None = None


class OutcomeRecordRequest(BaseModel):
    response_id: str
    effective: bool
    notes: str | None = None


# ---------------------------------------------------------------------------
# Metrics Endpoints
# ---------------------------------------------------------------------------

@dashboard_router.get("/metrics", response_model=DefenseMetrics)
async def get_metrics(window_minutes: int = Query(5, ge=1, le=60)):
    """
    Get real-time defense metrics.
    
    ◎ Returns aggregated threat data for the specified time window.
    """
    from ...agents.vigil_operis.agent import compute_metrics
    return compute_metrics(window_minutes=window_minutes)


@dashboard_router.get("/metrics/anomalies")
async def get_anomalies(window_minutes: int = Query(5, ge=1, le=60)):
    """
    Detect anomalies in current traffic patterns.
    
    ◎ Returns list of detected anomalies with severity.
    """
    from ...agents.vigil_operis.agent import compute_metrics, detect_anomalies
    metrics = compute_metrics(window_minutes=window_minutes)
    anomalies = await detect_anomalies(metrics)
    return {"anomalies": anomalies, "metrics_window": window_minutes}


# ---------------------------------------------------------------------------
# Threat Endpoints
# ---------------------------------------------------------------------------

@dashboard_router.get("/threats")
async def list_threats(
    min_level: ThreatLevel = Query(ThreatLevel.LOW),
    limit: int = Query(50, ge=1, le=200),
):
    """
    List current threats above a minimum level.
    
    ⚠ Returns fingerprints classified as threats.
    """
    from ..honeypot.collector import FingerprintCollector
    threats = FingerprintCollector.get_threats(min_level)
    return {
        "threats": [t.model_dump(mode="json") for t in threats[:limit]],
        "total": len(threats),
        "min_level": min_level.value,
    }


@dashboard_router.get("/threats/{fingerprint_id}")
async def get_threat_detail(fingerprint_id: str):
    """
    Get detailed information about a specific threat.
    
    ⚠ Returns full fingerprint and associated events.
    """
    from ..honeypot.collector import FingerprintCollector
    
    fingerprint = FingerprintCollector.get_fingerprint(fingerprint_id)
    if not fingerprint:
        raise HTTPException(status_code=404, detail="Fingerprint not found")
    
    # Get associated events
    events = FingerprintCollector.get_recent_events(limit=500)
    threat_events = [e for e in events if e.fingerprint_id == fingerprint_id]
    
    return {
        "fingerprint": fingerprint.model_dump(mode="json"),
        "events": [e.model_dump(mode="json") for e in threat_events[:50]],
    }


@dashboard_router.post("/threats/{fingerprint_id}/action")
async def take_threat_action(fingerprint_id: str, request: ThreatActionRequest):
    """
    Take action against a threat.
    
    ⛨ Manually trigger a defensive action against a fingerprint.
    """
    from ..honeypot.collector import FingerprintCollector
    from ...agents.defensor_campi.agent import analyze_threat
    from ...agents.adaptio_mentis.agent import save_adaptive_response
    
    fingerprint = FingerprintCollector.get_fingerprint(fingerprint_id)
    if not fingerprint:
        raise HTTPException(status_code=404, detail="Fingerprint not found")
    
    # Create adaptive response record
    from ..schemas import AdaptiveResponse
    import uuid
    
    response = AdaptiveResponse(
        response_id=str(uuid.uuid4()),
        fingerprint_id=fingerprint_id,
        action=request.action,
        reasoning=request.reason or f"Manual action: {request.action.value}",
        confidence=1.0,
        triggered_by="manual_dashboard",
    )
    
    save_adaptive_response(response)
    
    return {
        "status": "action_recorded",
        "response_id": response.response_id,
        "action": request.action.value,
        "fingerprint_id": fingerprint_id,
    }


# ---------------------------------------------------------------------------
# Honeypot Event Endpoints
# ---------------------------------------------------------------------------

@dashboard_router.get("/events")
async def list_honeypot_events(
    limit: int = Query(50, ge=1, le=500),
    trap_type: str | None = None,
):
    """
    List recent honeypot events.
    
    🜏 Returns traps that have been triggered.
    """
    from ..honeypot.collector import FingerprintCollector
    
    events = FingerprintCollector.get_recent_events(limit=limit)
    
    if trap_type:
        events = [e for e in events if e.trap_type.value == trap_type]
    
    return {
        "events": [e.model_dump(mode="json") for e in events],
        "total": len(events),
    }


@dashboard_router.get("/events/{event_id}")
async def get_event_detail(event_id: str):
    """
    Get detailed information about a honeypot event.
    
    🜏 Returns full event data including headers and body.
    """
    from ..honeypot.collector import FingerprintCollector
    
    events = FingerprintCollector.get_recent_events(limit=1000)
    event = next((e for e in events if e.event_id == event_id), None)
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return event.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Genome Endpoints (Threat Patterns)
# ---------------------------------------------------------------------------

@dashboard_router.get("/genome")
async def list_genome_patterns(limit: int = Query(50, ge=1, le=200)):
    """
    List threat patterns in the genome.
    
    ⟲ Returns learned attack patterns from the adaptive system.
    """
    from ...agents.adaptio_mentis.agent import get_genome_patterns
    patterns = get_genome_patterns(limit=limit)
    return {
        "patterns": [p.model_dump(mode="json") for p in patterns],
        "total": len(patterns),
    }


@dashboard_router.get("/genome/{genome_id}")
async def get_genome_pattern(genome_id: str):
    """
    Get detailed information about a threat pattern.
    
    ⟲ Returns full pattern signature and effectiveness data.
    """
    from ...agents.adaptio_mentis.agent import get_genome_patterns
    
    patterns = get_genome_patterns(limit=1000)
    pattern = next((p for p in patterns if p.genome_id == genome_id), None)
    
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    return pattern.model_dump(mode="json")


@dashboard_router.post("/genome/learn")
async def trigger_learning():
    """
    Trigger learning from recent honeypot events.
    
    ⟲ Analyzes recent events and extracts new patterns for the genome.
    """
    from ..honeypot.collector import FingerprintCollector
    from ...agents.adaptio_mentis.agent import learn_from_events
    
    events = FingerprintCollector.get_recent_events(limit=100)
    
    if not events:
        return {"status": "no_events", "message": "No recent events to learn from"}
    
    pattern = await learn_from_events(events)
    
    if pattern:
        return {
            "status": "learned",
            "pattern": pattern.model_dump(mode="json"),
        }
    else:
        return {"status": "no_pattern", "message": "Could not extract pattern"}


# ---------------------------------------------------------------------------
# Strategy Endpoints
# ---------------------------------------------------------------------------

@dashboard_router.post("/strategy/evolve")
async def evolve_strategies():
    """
    Trigger strategy evolution.
    
    ⟲ Analyzes response effectiveness and suggests improvements.
    """
    from ...agents.adaptio_mentis.agent import evolve_strategies
    
    improvements = await evolve_strategies()
    return {
        "status": "evolved",
        "improvements": improvements,
    }


@dashboard_router.post("/outcomes/record")
async def record_outcome(request: OutcomeRecordRequest):
    """
    Record the outcome of an adaptive response.
    
    ⟲ Feedback for learning - was the response effective?
    """
    from ...agents.adaptio_mentis.agent import record_response_outcome
    
    record_response_outcome(
        response_id=request.response_id,
        effective=request.effective,
        notes=request.notes,
    )
    
    return {
        "status": "recorded",
        "response_id": request.response_id,
        "effective": request.effective,
    }


# ---------------------------------------------------------------------------
# System Status
# ---------------------------------------------------------------------------

@dashboard_router.get("/status")
async def get_defense_status():
    """
    Get overall defense system status.
    
    ⛨ Returns health and configuration of the defense system.
    """
    from ...agents.vigil_operis.agent import compute_metrics
    from ...agents.adaptio_mentis.agent import get_genome_patterns
    from ..honeypot.traps import TRAP_REGISTRY
    
    metrics = compute_metrics(window_minutes=60)
    patterns = get_genome_patterns(limit=1000)
    
    return {
        "status": "active",
        "glyph": "⛨",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "honeypot": {
            "active_traps": len(TRAP_REGISTRY),
            "triggers_last_hour": metrics.honeypot_triggers,
        },
        "threats": {
            "detected_last_hour": metrics.threats_detected,
            "top_ips": metrics.top_threat_ips[:5],
        },
        "genome": {
            "known_patterns": len(patterns),
            "top_patterns": metrics.top_attack_patterns[:5],
        },
        "monitoring": {
            "unique_visitors_last_hour": metrics.unique_visitors,
            "classification_breakdown": metrics.classification_counts,
        },
    }
