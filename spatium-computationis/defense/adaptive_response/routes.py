"""
⟲ ADAPTIVE RESPONSE ROUTES — FastAPI endpoints for the defense dashboard

Exposes the adaptive response engine configuration and metrics via REST API.
Integrates with the existing defense dashboard infrastructure.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..organism_charter import ClassificationTier, EntityRole
from ..schemas import ThreatLevel
from .effectiveness import EffectivenessReport, get_tracker
from .engine import AdaptiveResponseEngine, ResponseConfig, ResponseDecision, get_engine
from .escalation import (
    EscalationEngine,
    EscalationEvent,
    EscalationRule,
    EscalationTrigger,
    get_escalation_engine,
)
from .strategies import StrategyType


adaptive_response_router = APIRouter(
    prefix="/adaptive-response",
    tags=["adaptive-response"],
)


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class PostureUpdateRequest(BaseModel):
    """Request to update the defense posture."""
    posture: str = "balanced"  # defensive, balanced, aggressive
    tier_a_strategy: StrategyType | None = None
    tier_b_strategy: StrategyType | None = None
    tier_c_strategy: StrategyType | None = None
    auto_respond_confidence: float | None = None
    enable_ab_testing: bool | None = None
    exploration_rate: float | None = None


class ManualResponseRequest(BaseModel):
    """Request to manually trigger a response against an entity."""
    entity_ip: str
    strategy_type: StrategyType
    fingerprint_id: str | None = None
    reason: str = "manual_override"


class EscalationRuleRequest(BaseModel):
    """Request to add an escalation rule."""
    name: str
    description: str
    trigger: EscalationTrigger
    threshold: int = 3
    window_minutes: int = 60
    from_tier: ClassificationTier | None = None
    to_tier: ClassificationTier
    new_threat_level: ThreatLevel | None = None
    cooldown_minutes: int = 30


class BehaviorSignalRequest(BaseModel):
    """Report a behavior signal for escalation evaluation."""
    entity_ip: str
    trigger: EscalationTrigger
    current_tier: ClassificationTier
    current_threat_level: ThreatLevel
    fingerprint_id: str | None = None


# ---------------------------------------------------------------------------
# Engine Status & Configuration
# ---------------------------------------------------------------------------

@adaptive_response_router.get("/status")
async def get_status() -> dict[str, Any]:
    """Get adaptive response engine status and statistics."""
    engine = get_engine()
    stats = engine.get_stats()
    return {
        "status": "active",
        "engine": "AdaptiveResponseEngine",
        "glyph": "⟲",
        "config": engine.config.model_dump(),
        "stats": stats,
    }


@adaptive_response_router.get("/config")
async def get_config() -> ResponseConfig:
    """Get current engine configuration."""
    return get_engine().config


@adaptive_response_router.put("/config")
async def update_config(request: PostureUpdateRequest) -> dict[str, Any]:
    """
    Update defense posture and strategy configuration.
    Hot-reloads without restart.
    """
    engine = get_engine()
    current = engine.config.model_dump()

    # Apply non-None updates
    updates = request.model_dump(exclude_none=True)
    current.update(updates)

    new_config = ResponseConfig(**current)
    engine.update_config(new_config)

    return {
        "message": f"Defense posture updated to '{new_config.posture}'",
        "config": new_config.model_dump(),
    }


@adaptive_response_router.post("/posture/{posture}")
async def set_posture(posture: str) -> dict[str, Any]:
    """Quick posture switch: defensive, balanced, or aggressive."""
    presets = {
        "defensive": ResponseConfig(
            posture="defensive",
            tier_a_strategy=StrategyType.OBSERVE,
            tier_b_strategy=StrategyType.CHALLENGE,
            tier_c_strategy=StrategyType.OBSERVE,
            auto_respond_confidence=0.85,
            exploration_rate=0.05,
        ),
        "balanced": ResponseConfig(
            posture="balanced",
            tier_a_strategy=StrategyType.OBSERVE,
            tier_b_strategy=StrategyType.BLOCK,
            tier_c_strategy=StrategyType.CHALLENGE,
            auto_respond_confidence=0.7,
            exploration_rate=0.1,
        ),
        "aggressive": ResponseConfig(
            posture="aggressive",
            tier_a_strategy=StrategyType.RATE_LIMIT,
            tier_b_strategy=StrategyType.BLOCK,
            tier_c_strategy=StrategyType.TAR_PIT,
            auto_respond_confidence=0.5,
            exploration_rate=0.15,
        ),
    }

    if posture not in presets:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown posture '{posture}'. Use: defensive, balanced, aggressive",
        )

    engine = get_engine()
    engine.update_config(presets[posture])

    return {
        "message": f"Defense posture set to '{posture}'",
        "config": presets[posture].model_dump(),
    }


# ---------------------------------------------------------------------------
# Response Decisions
# ---------------------------------------------------------------------------

@adaptive_response_router.get("/decisions")
async def get_recent_decisions(
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """Get recent response decisions."""
    return get_engine().get_recent_decisions(limit=limit)


@adaptive_response_router.post("/respond")
async def manual_response(request: ManualResponseRequest) -> dict[str, Any]:
    """Manually trigger a response strategy against an entity."""
    engine = get_engine()

    decision = engine.decide_and_execute(
        entity_ip=request.entity_ip,
        classification_tier=ClassificationTier.TIER_B_HOSTILE,
        entity_role=EntityRole.THREAT,
        threat_level=ThreatLevel.HIGH,
        classification_confidence=1.0,
        fingerprint_id=request.fingerprint_id,
        context={"manual": True, "reason": request.reason},
    )

    return {
        "message": f"Response executed: {decision.selected_strategy.value}",
        "decision": decision.model_dump(mode="json"),
    }


# ---------------------------------------------------------------------------
# Active Blocks
# ---------------------------------------------------------------------------

@adaptive_response_router.get("/blocks")
async def get_active_blocks() -> list[dict[str, Any]]:
    """Get all currently active blocks."""
    return get_engine().get_active_blocks()


# ---------------------------------------------------------------------------
# Escalation
# ---------------------------------------------------------------------------

@adaptive_response_router.get("/escalation/rules")
async def get_escalation_rules() -> list[dict[str, Any]]:
    """Get current escalation rules."""
    engine = get_escalation_engine()
    return [rule.model_dump() for rule in engine.get_rules()]


@adaptive_response_router.post("/escalation/rules")
async def add_escalation_rule(request: EscalationRuleRequest) -> dict[str, Any]:
    """Add a new escalation rule."""
    from .escalation import EscalationDirection

    rule = EscalationRule(
        name=request.name,
        description=request.description,
        trigger=request.trigger,
        threshold=request.threshold,
        window_minutes=request.window_minutes,
        from_tier=request.from_tier,
        to_tier=request.to_tier,
        direction=EscalationDirection.ESCALATE,
        new_threat_level=request.new_threat_level,
        cooldown_minutes=request.cooldown_minutes,
    )

    engine = get_escalation_engine()
    engine.add_rule(rule)

    return {
        "message": f"Escalation rule '{rule.name}' added",
        "rule": rule.model_dump(),
    }


@adaptive_response_router.delete("/escalation/rules/{rule_id}")
async def remove_escalation_rule(rule_id: str) -> dict[str, Any]:
    """Remove an escalation rule."""
    engine = get_escalation_engine()
    removed = engine.remove_rule(rule_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    return {"message": f"Rule '{rule_id}' removed"}


@adaptive_response_router.post("/escalation/signal")
async def report_behavior_signal(
    request: BehaviorSignalRequest,
) -> dict[str, Any]:
    """
    Report a behavior signal for escalation evaluation.
    Returns escalation event if threshold was met.
    """
    engine = get_escalation_engine()
    event = engine.record_behavior(
        entity_ip=request.entity_ip,
        trigger=request.trigger,
        current_tier=request.current_tier,
        current_threat_level=request.current_threat_level,
        fingerprint_id=request.fingerprint_id,
    )

    if event:
        return {
            "escalation_triggered": True,
            "event": event.model_dump(mode="json"),
        }
    return {"escalation_triggered": False}


@adaptive_response_router.get("/escalation/history")
async def get_escalation_history(
    limit: int = Query(default=50, ge=1, le=200),
    entity_ip: str | None = None,
) -> list[dict[str, Any]]:
    """Get escalation event history."""
    engine = get_escalation_engine()
    if entity_ip:
        return engine.get_entity_escalation_history(entity_ip)
    return engine.get_recent_escalations(limit=limit)


# ---------------------------------------------------------------------------
# Effectiveness
# ---------------------------------------------------------------------------

@adaptive_response_router.get("/effectiveness")
async def get_effectiveness_reports(
    period_hours: int = Query(default=24, ge=1, le=720),
) -> list[dict[str, Any]]:
    """Get effectiveness reports for all strategies."""
    tracker = get_tracker()
    reports = tracker.get_all_strategy_reports(period_hours=period_hours)
    return [r.model_dump(mode="json") for r in reports]


@adaptive_response_router.get("/effectiveness/{strategy_type}")
async def get_strategy_effectiveness(
    strategy_type: StrategyType,
    period_hours: int = Query(default=24, ge=1, le=720),
) -> dict[str, Any]:
    """Get effectiveness report for a specific strategy."""
    tracker = get_tracker()
    report = tracker.get_strategy_report(strategy_type, period_hours=period_hours)
    return report.model_dump(mode="json")


@adaptive_response_router.get("/effectiveness/pending")
async def get_pending_evaluations() -> list[dict[str, Any]]:
    """Get responses awaiting effectiveness evaluation."""
    tracker = get_tracker()
    return tracker.get_pending_evaluations()
