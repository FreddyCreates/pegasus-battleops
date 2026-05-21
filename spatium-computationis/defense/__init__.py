"""
Defense Module — AI Battleground Infrastructure
⛨ The immune system of Spatium Computationis.

This module transforms the domain into a live-fire AI battleground with:
- Honeypot traps that attract and capture adversarial behavior
- Bot fingerprinting through behavioral analysis
- Cloudflare integration for threat intelligence
- Real-time defense dashboard
- Adaptive learning from attack patterns
- Organism Charter classification and routing
- Value extraction and monetization

Glyphs:
  ⛨ Defensor  — active defense
  ◎ Vigil     — constant monitoring
  ⟲ Adaptio   — adaptive response
  ⚠ Minacium  — threat detection
  🜏 Deceptio  — deceptive trap
  💰 Extractio — value extraction
"""

from .schemas import (
    ThreatLevel,
    BotClassification,
    ThreatRecord,
    BotFingerprint,
    HoneypotEvent,
    ThreatIntelligence,
    AdaptiveResponse,
    DefenseMetrics,
    RequestEnvelope,
    RouteDestination,
    AISourceType,
    DecryptionResult,
    RepairResult,
    GatekeeperDecision,
    AdversaryDissection,
)

from .organism_charter import (
    ClassificationTier,
    EntityRole,
    OrganismClassifier,
    SpecimenProfile,
    SpecimenProfiler,
    get_organism_stats,
    KNOWN_ATTACKER_IPS,
    WORDPRESS_PROBE_PATHS,
    EXPLOIT_PROBE_PATHS,
)

from .value_extraction import (
    ValueType,
    MonetizationStatus,
    ValueEvent,
    ValueSummary,
    capture_content_value,
    capture_task_completion,
    capture_knowledge_access,
    capture_research_output,
    capture_behavioral_data,
    get_value_summary,
    get_top_value_sources,
    get_knowledge_shard_stats,
    issue_task,
    complete_task,
)

from .organism_stats import organism_router

__all__ = [
    # Schemas
    "ThreatLevel",
    "BotClassification",
    "ThreatRecord",
    "BotFingerprint",
    "HoneypotEvent",
    "ThreatIntelligence",
    "AdaptiveResponse",
    "DefenseMetrics",
    "RequestEnvelope",
    "RouteDestination",
    "AISourceType",
    "DecryptionResult",
    "RepairResult",
    "GatekeeperDecision",
    "AdversaryDissection",
    # Organism Charter
    "ClassificationTier",
    "EntityRole",
    "OrganismClassifier",
    "SpecimenProfile",
    "SpecimenProfiler",
    "get_organism_stats",
    "KNOWN_ATTACKER_IPS",
    "WORDPRESS_PROBE_PATHS",
    "EXPLOIT_PROBE_PATHS",
    # Value Extraction
    "ValueType",
    "MonetizationStatus",
    "ValueEvent",
    "ValueSummary",
    "capture_content_value",
    "capture_task_completion",
    "capture_knowledge_access",
    "capture_research_output",
    "capture_behavioral_data",
    "get_value_summary",
    "get_top_value_sources",
    "get_knowledge_shard_stats",
    "issue_task",
    "complete_task",
    # Organism Stats Router
    "organism_router",
]
