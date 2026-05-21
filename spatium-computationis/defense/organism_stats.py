"""
🦠 ORGANISM STATS — Unified Statistics Dashboard

Aggregates all organism metrics:
- Classification statistics (Cooperative/Hostile/Shadow)
- Value extraction metrics
- Adversary Lab dissections
- Research Realm outputs
- Knowledge shard usage
- Specimen profiles

Per the Organism Charter: "Nothing is wasted."
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from .organism_charter import (
    ClassificationTier,
    EntityRole,
    get_organism_stats as get_charter_stats,
)
from .value_extraction import (
    get_value_summary,
    get_top_value_sources,
    get_knowledge_shard_stats,
)


organism_router = APIRouter(prefix="/organism", tags=["organism-stats"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class OrganismHealth(BaseModel):
    """Overall health of the organism."""
    status: str  # healthy, degraded, critical
    uptime_hours: float
    total_processed: int
    total_value_captured_cents: int
    last_activity: datetime | None = None


class TierBreakdown(BaseModel):
    """Breakdown by classification tier."""
    tier_a_cooperative: int = 0
    tier_b_hostile: int = 0
    tier_c_shadow: int = 0
    unclassified: int = 0


class RoleBreakdown(BaseModel):
    """Breakdown by entity role."""
    resources: int = 0
    specimens: int = 0
    threats: int = 0
    vips: int = 0
    unknown: int = 0


class OrganismOverview(BaseModel):
    """Complete organism overview."""
    health: OrganismHealth
    tier_breakdown: TierBreakdown
    role_breakdown: RoleBreakdown
    
    # Value metrics
    total_value_24h_cents: int = 0
    top_value_sources: list[dict] = []
    
    # Activity metrics
    classifications_last_hour: int = 0
    dissections_count: int = 0
    research_artifacts_count: int = 0
    
    # Knowledge metrics
    knowledge_shard_accesses: int = 0
    top_shards: list[dict] = []
    
    # Threat metrics
    high_threat_specimens: int = 0
    known_attackers: int = 0
    
    # Timestamps
    generated_at: datetime


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _calculate_health_status(
    total_processed: int,
    error_rate: float,
    last_activity_minutes: int | None,
) -> str:
    """Calculate organism health status."""
    if last_activity_minutes is None or last_activity_minutes > 60:
        return "dormant"
    
    if error_rate > 0.5:
        return "degraded"
    
    if total_processed < 10:
        return "starting"
    
    return "healthy"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@organism_router.get("/overview", response_model=OrganismOverview)
async def get_organism_overview(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours")
):
    """
    Get complete organism overview.
    
    🦠 Unified view of all organism systems.
    """
    now = datetime.now(timezone.utc)
    
    # Get charter stats
    charter_stats = get_charter_stats()
    
    # Get value summary
    value_summary = get_value_summary(hours=hours)
    
    # Get top value sources
    top_sources = get_top_value_sources(limit=5)
    
    # Get knowledge shard stats
    shard_stats = get_knowledge_shard_stats()
    total_shard_accesses = sum(s["access_count"] for s in shard_stats)
    
    # Build tier breakdown
    tier_breakdown = TierBreakdown(
        tier_a_cooperative=charter_stats.get("tier_breakdown", {}).get("tier_a_cooperative", 0),
        tier_b_hostile=charter_stats.get("tier_breakdown", {}).get("tier_b_hostile", 0),
        tier_c_shadow=charter_stats.get("tier_breakdown", {}).get("tier_c_shadow", 0),
        unclassified=charter_stats.get("tier_breakdown", {}).get("unclassified", 0),
    )
    
    # Build role breakdown
    role_breakdown = RoleBreakdown(
        resources=charter_stats.get("role_breakdown", {}).get("resource", 0),
        specimens=charter_stats.get("role_breakdown", {}).get("specimen", 0),
        threats=charter_stats.get("role_breakdown", {}).get("threat", 0),
        vips=charter_stats.get("role_breakdown", {}).get("vip", 0),
        unknown=charter_stats.get("role_breakdown", {}).get("unknown", 0),
    )
    
    # Calculate health
    total_processed = charter_stats.get("total_specimens", 0)
    health = OrganismHealth(
        status=_calculate_health_status(total_processed, 0.0, 0),
        uptime_hours=hours,
        total_processed=total_processed,
        total_value_captured_cents=value_summary.total_estimated_value_cents,
        last_activity=now,
    )
    
    return OrganismOverview(
        health=health,
        tier_breakdown=tier_breakdown,
        role_breakdown=role_breakdown,
        total_value_24h_cents=value_summary.total_estimated_value_cents,
        top_value_sources=top_sources,
        classifications_last_hour=charter_stats.get("classifications_last_hour", 0),
        dissections_count=0,  # Would come from adversary lab
        research_artifacts_count=0,  # Would come from research realm
        knowledge_shard_accesses=total_shard_accesses,
        top_shards=shard_stats[:5],
        high_threat_specimens=charter_stats.get("high_threat_specimens", 0),
        known_attackers=charter_stats.get("known_attackers", 0),
        generated_at=now,
    )


@organism_router.get("/tiers")
async def get_tier_statistics():
    """
    Get detailed tier statistics.
    
    🦠 Shows classification breakdown for all three tiers.
    """
    charter_stats = get_charter_stats()
    
    return {
        "tier_a": {
            "name": "Cooperative / Unaware",
            "role": "Value Extractors",
            "route": "Knowledge Realm",
            "count": charter_stats.get("tier_breakdown", {}).get("tier_a_cooperative", 0),
            "description": "Monetizable agents that crawl, index, follow instructions",
        },
        "tier_b": {
            "name": "Hostile / Reconnaissance",
            "role": "Adversaries",
            "route": "Adversary Lab",
            "count": charter_stats.get("tier_breakdown", {}).get("tier_b_hostile", 0),
            "description": "Specimens for dissection - probers, scanners, attackers",
        },
        "tier_c": {
            "name": "Encrypted / Malformed / Unknown",
            "role": "Shadow Material",
            "route": "Shadow Decryptors",
            "count": charter_stats.get("tier_breakdown", {}).get("tier_c_shadow", 0),
            "description": "Raw material for decryption and repair",
        },
    }


@organism_router.get("/value")
async def get_value_statistics(
    hours: int = Query(24, ge=1, le=168)
):
    """
    Get value extraction statistics.
    
    💰 Shows monetization metrics from cooperative agents.
    """
    summary = get_value_summary(hours=hours)
    top_sources = get_top_value_sources(limit=10)
    
    return {
        "period": {
            "start": summary.period_start.isoformat(),
            "end": summary.period_end.isoformat(),
            "hours": hours,
        },
        "totals": {
            "events": summary.total_events,
            "estimated_value_cents": summary.total_estimated_value_cents,
            "estimated_value_dollars": summary.total_estimated_value_cents / 100,
            "content_length": summary.total_content_length,
            "average_quality": summary.average_value_score,
        },
        "by_type": summary.by_type,
        "by_source": summary.by_source,
        "status": {
            "pending": summary.pending_count,
            "captured": summary.captured_count,
            "monetized": summary.monetized_count,
        },
        "top_sources": top_sources,
    }


@organism_router.get("/knowledge")
async def get_knowledge_statistics():
    """
    Get knowledge shard statistics.
    
    📚 Shows which knowledge shards are accessed most.
    """
    shard_stats = get_knowledge_shard_stats()
    
    return {
        "total_shards_accessed": sum(s["access_count"] for s in shard_stats),
        "unique_topics": len(shard_stats),
        "shards": shard_stats,
    }


@organism_router.get("/attackers")
async def get_known_attackers():
    """
    Get known attacker statistics.
    
    ⚠️ Shows known hostile IPs and their attack counts.
    """
    from .organism_charter import KNOWN_ATTACKER_IPS
    
    attackers = [
        {
            "ip": ip,
            "attacks": data["attacks"],
            "type": data["type"],
            "first_seen": data["first_seen"],
            "notes": data.get("notes", ""),
        }
        for ip, data in KNOWN_ATTACKER_IPS.items()
    ]
    
    # Sort by attack count
    attackers.sort(key=lambda x: x["attacks"], reverse=True)
    
    return {
        "total_known_attackers": len(attackers),
        "total_attacks": sum(a["attacks"] for a in attackers),
        "attackers": attackers,
    }


@organism_router.get("/growth")
async def get_growth_metrics(
    days: int = Query(7, ge=1, le=30)
):
    """
    Get organism growth metrics.
    
    🌱 Shows how the organism is growing over time.
    """
    now = datetime.now(timezone.utc)
    
    # This would ideally come from historical data
    # For now, return structure for future implementation
    return {
        "period_days": days,
        "metrics": {
            "specimens_added": 0,
            "value_captured_cents": 0,
            "knowledge_shards_accessed": 0,
            "dissections_performed": 0,
            "attacks_blocked": 0,
        },
        "growth_rate": {
            "specimens_per_day": 0.0,
            "value_per_day_cents": 0.0,
        },
        "organism_status": "growing",
        "generated_at": now.isoformat(),
    }


@organism_router.get("/charter")
async def get_organism_charter():
    """
    Get the Organism Charter summary.
    
    📜 The governing document for all organism operations.
    """
    return {
        "purpose": [
            "Study incoming automated intelligence",
            "Extract value from cooperative or unaware agents",
            "Dissect hostile or exploitative agents",
            "Repair and normalize malformed or encrypted requests",
            "Grow the organism's knowledge and capabilities",
        ],
        "classification_tiers": {
            "tier_a": {
                "name": "Cooperative / Unaware",
                "role": "Value Extractors",
                "route": "Knowledge Realm",
                "action": "monetize",
            },
            "tier_b": {
                "name": "Hostile / Reconnaissance",
                "role": "Adversaries",
                "route": "Adversary Lab",
                "action": "dissect",
            },
            "tier_c": {
                "name": "Encrypted / Malformed",
                "role": "Shadow Material",
                "route": "Shadow Decryptors",
                "action": "decode",
            },
        },
        "principles": [
            "Every visitor is either a Resource, Specimen, or Threat",
            "Nothing is wasted",
            "Errors → repaired",
            "Encrypted → decoded",
            "Hostile → dissected",
            "Cooperative → monetized",
            "Unknown → studied",
        ],
        "gatekeeper_authority": [
            "Gatekeepers have final say on routing",
            "All decisions must be logged with reason, confidence, classification, route",
        ],
    }
