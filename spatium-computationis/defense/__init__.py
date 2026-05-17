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

Glyphs:
  ⛨ Defensor  — active defense
  ◎ Vigil     — constant monitoring
  ⟲ Adaptio   — adaptive response
  ⚠ Minacium  — threat detection
  🜏 Deceptio  — deceptive trap
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
]
