"""
ARCHON Organism Bridge — Integration with the Organism Charter

ARCHON does not exist in isolation. It is the cognitive layer of the Organism.
The Organism Charter classifies incoming entities into:
  - Tier A (Cooperative) → Knowledge Realm
  - Tier B (Hostile) → Adversary Lab
  - Tier C (Shadow) → Quarantine

ARCHON enhances this classification by:
1. Receiving organism classifications as input signals
2. Running the five-mind stack on ambiguous/high-value entities
3. Correlating specimens with the cortex threat map
4. Feeding decisions back to the organism adaptive response system
5. Providing cognitive depth to the fingerprinting pipeline

The bridge converts RequestEnvelopes, SpecimenProfiles, and classification
events into ARCHON input contexts that the minds can reason about.

Glyph: 🦠↔🧠 (organism-brain interface)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .minds import MindType, MindSignal, ThreatVector, PostureMode
from .cortex import (
    SituationalAwareness,
    store_memory,
    register_threat,
    get_situational_awareness,
    update_baseline,
)


# ---------------------------------------------------------------------------
# Threat Vector Mapping
# ---------------------------------------------------------------------------

# Map organism classification reasons to ARCHON threat vectors
CLASSIFICATION_TO_THREAT: dict[str, ThreatVector] = {
    "known_attacker": ThreatVector.RECONNAISSANCE,
    "wordpress_probe": ThreatVector.RECONNAISSANCE,
    "exploit_probe": ThreatVector.TRAVERSAL,
    "cloudflare_probe": ThreatVector.RECONNAISSANCE,
    "cloud_vps_scanner": ThreatVector.RECONNAISSANCE,
    "error_probe": ThreatVector.RECONNAISSANCE,
    "high_threat_score": ThreatVector.UNKNOWN_ANOMALY,
    "medium_threat_score": ThreatVector.UNKNOWN_ANOMALY,
    "low_bot_score": ThreatVector.UNKNOWN_ANOMALY,
    "unknown_user_agent": ThreatVector.UNKNOWN_ANOMALY,
    "shadow_material": ThreatVector.UNKNOWN_ANOMALY,
    "credential_attack": ThreatVector.CREDENTIAL_ATTACK,
    "injection_attempt": ThreatVector.INJECTION,
    "traversal_attempt": ThreatVector.TRAVERSAL,
    "exfiltration_attempt": ThreatVector.EXFILTRATION,
}

# Map threat score ranges to ARCHON severity
def _threat_score_to_severity(score: int | None) -> float:
    """Convert Cloudflare threat score (0-100) to ARCHON severity (0-1)."""
    if score is None:
        return 0.2
    return min(1.0, score / 80.0)  # 80+ = max severity


# ---------------------------------------------------------------------------
# Envelope Processing
# ---------------------------------------------------------------------------

def process_request_envelope(
    envelope_data: dict[str, Any],
    classification_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert a RequestEnvelope + classification into ARCHON input context.

    This is the primary bridge function. It takes raw organism data and
    produces the structured input that ARCHON's minds can reason about.

    Args:
        envelope_data: Serialized RequestEnvelope fields
        classification_result: Optional organism classification (tier, role, route, reason, confidence)

    Returns:
        ARCHON-formatted input context for mind reasoning
    """
    context: dict[str, Any] = {
        "source": "organism_charter",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Network identity
    context["network"] = {
        "source_ip": envelope_data.get("source_ip"),
        "asn": envelope_data.get("cf_asn"),
        "asn_org": envelope_data.get("cf_asn_org"),
        "country": envelope_data.get("cf_country"),
        "threat_score": envelope_data.get("cf_threat_score"),
        "bot_score": envelope_data.get("cf_bot_score"),
        "verified_bot": envelope_data.get("cf_verified_bot", False),
    }

    # Request details
    context["request"] = {
        "method": envelope_data.get("method"),
        "path": envelope_data.get("raw_path"),
        "user_agent": envelope_data.get("raw_headers", {}).get("user-agent"),
        "is_encrypted": envelope_data.get("is_encrypted", False),
        "is_malformed": envelope_data.get("is_malformed", False),
        "has_error": envelope_data.get("has_error", False),
        "error_code": envelope_data.get("error_code"),
    }

    # AI source detection
    context["ai_identity"] = {
        "ai_source_detected": envelope_data.get("ai_source_detected"),
        "is_ai_visitor": envelope_data.get("ai_source_detected") is not None,
    }

    # Classification result
    if classification_result:
        context["organism_classification"] = classification_result
        reason = classification_result.get("reason", "")
        confidence = classification_result.get("confidence", 0.5)

        # Map to threat vector
        threat_vector = None
        for key, vector in CLASSIFICATION_TO_THREAT.items():
            if key in reason:
                threat_vector = vector
                break

        if threat_vector:
            context["detected_threat_vector"] = threat_vector.value
            context["classification_confidence"] = confidence

    # Severity assessment
    threat_score = envelope_data.get("cf_threat_score")
    context["computed_severity"] = _threat_score_to_severity(threat_score)

    return context


def ingest_classification_event(
    envelope_data: dict[str, Any],
    tier: str,
    role: str,
    route: str,
    reason: str,
    confidence: float,
) -> str:
    """Ingest a classification event from the organism into the ARCHON cortex.

    This function:
    1. Stores the observation in working memory
    2. Updates threat map if hostile
    3. Updates baselines for drift detection
    4. Returns memory_id for correlation

    Args:
        envelope_data: Request envelope fields
        tier: Classification tier (tier_a_cooperative, tier_b_hostile, tier_c_shadow)
        role: Entity role (resource, specimen, threat, vip, unknown)
        route: Route destination
        reason: Classification reason string
        confidence: Classification confidence

    Returns:
        Memory ID stored in cortex
    """
    source_ip = envelope_data.get("source_ip", "unknown")

    # Store in working memory
    content = (
        f"Classification: {tier}/{role} → {route} | "
        f"Reason: {reason} | IP: {source_ip} | Confidence: {confidence:.2f}"
    )

    # Determine threat vectors
    threat_vectors = []
    for key, vector in CLASSIFICATION_TO_THREAT.items():
        if key in reason:
            threat_vectors.append(vector)

    memory_id = store_memory(
        memory_type="classification",
        content=content,
        mind_source=MindType.AI_INTELLIGENCE,  # AI Intelligence observes all
        signal_value=confidence if "hostile" in tier else -confidence,
        confidence=confidence,
        threat_vectors=threat_vectors or None,
        ttl_hours=72,
    )

    # Register threat if hostile
    if "hostile" in tier or role == "threat":
        primary_vector = threat_vectors[0] if threat_vectors else ThreatVector.UNKNOWN_ANOMALY
        severity = _threat_score_to_severity(envelope_data.get("cf_threat_score"))
        register_threat(
            vector=primary_vector,
            severity=severity,
            confidence=confidence,
            source_ip=source_ip,
            specimen_id=envelope_data.get("specimen_id"),
            mind_attribution=MindType.AI_INTELLIGENCE,
        )

    # Update baselines
    update_baseline("classification_confidence", confidence)
    if envelope_data.get("cf_threat_score"):
        update_baseline("threat_score", float(envelope_data["cf_threat_score"]))
    if envelope_data.get("cf_bot_score"):
        update_baseline("bot_score", float(envelope_data["cf_bot_score"]))

    return memory_id


def process_specimen_for_archon(
    specimen_data: dict[str, Any],
) -> dict[str, Any]:
    """Convert a SpecimenProfile into ARCHON input context for deep analysis.

    Called when the organism encounters an interesting specimen that
    warrants full five-mind cognitive evaluation.
    """
    context: dict[str, Any] = {
        "source": "specimen_analysis",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    context["specimen"] = {
        "specimen_id": specimen_data.get("specimen_id"),
        "ip_address": specimen_data.get("ip_address"),
        "asn": specimen_data.get("asn"),
        "asn_org": specimen_data.get("asn_org"),
        "country": specimen_data.get("country"),
        "tier": specimen_data.get("tier"),
        "role": specimen_data.get("role"),
        "threat_level": specimen_data.get("threat_level"),
        "total_requests": specimen_data.get("total_requests", 0),
        "honeypot_triggers": specimen_data.get("honeypot_triggers", 0),
        "error_count": specimen_data.get("error_count", 0),
        "behavioral_hash": specimen_data.get("behavioral_hash"),
    }

    # Behavioral patterns
    context["behavior"] = {
        "path_attempts": specimen_data.get("path_attempts", [])[:20],
        "methods_used": specimen_data.get("methods_used", []),
        "error_patterns": specimen_data.get("error_patterns", [])[:10],
        "response_codes": specimen_data.get("response_codes", [])[:20],
    }

    # Temporal analysis
    first_seen = specimen_data.get("first_seen")
    last_seen = specimen_data.get("last_seen")
    if first_seen and last_seen:
        context["temporal"] = {
            "first_seen": first_seen,
            "last_seen": last_seen,
            "total_requests": specimen_data.get("total_requests", 0),
        }

    return context


def compute_organism_alert_level() -> float:
    """Compute the current alert level from organism state.

    This is fed into the fusion engine as the primary urgency driver.
    Alert level is derived from:
    - Active threat count and severity
    - Recent classification patterns
    - Baseline drift signals
    """
    awareness = get_situational_awareness()

    # Base from threat map
    if not awareness.active_threats:
        threat_component = 0.0
    else:
        max_severity = max(t.severity for t in awareness.active_threats)
        avg_severity = sum(t.severity for t in awareness.active_threats) / len(awareness.active_threats)
        # Weight max severity more than average
        threat_component = max_severity * 0.6 + avg_severity * 0.4

    # Drift component
    drift_count = len(awareness.baseline_drift)
    drift_component = min(0.3, drift_count * 0.1)

    # Frequency component (high signal frequency = elevated state)
    total_signals = sum(awareness.signal_frequency.values())
    freq_component = min(0.2, total_signals * 0.01)

    alert_level = min(1.0, threat_component + drift_component + freq_component)
    return alert_level
