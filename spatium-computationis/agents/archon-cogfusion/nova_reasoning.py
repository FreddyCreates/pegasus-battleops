"""
ARCHON Nova Reasoning — Mind Signal Generation via Nova Sovereign

Each mind reasons through the Nova Sovereign intelligence backend.
This module implements the actual cognitive process:

1. Build context from cortex state + organism data
2. Construct mind-specific prompt with doctrine
3. Call Nova Sovereign for reasoning
4. Parse structured signal output
5. Return MindSignal with full cognitive artifact

This is where ARCHON thinks. Not weights. Not math. Actual reasoning.

Glyph: 💭 (thought process)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .minds import (
    MindType,
    MindSignal,
    ThreatVector,
    PostureMode,
    MIND_PROFILES,
)
from .cortex import (
    SituationalAwareness,
    WorkingMemory,
    ThreatMapEntry,
    recall_memories,
    get_active_threats,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Context Building
# ---------------------------------------------------------------------------

def _build_mind_context(
    mind_type: MindType,
    input_data: dict[str, Any],
    awareness: SituationalAwareness,
) -> str:
    """Build the full context string for a mind's reasoning call.

    Includes:
    - Current situational awareness
    - Active threats relevant to this mind
    - Recent memories from this mind
    - The input data to evaluate
    """
    profile = MIND_PROFILES[mind_type]
    parts: list[str] = []

    # Current state
    parts.append(f"CURRENT POSTURE: {awareness.current_posture.value}")
    parts.append(f"ALERT LEVEL: {awareness.alert_level:.3f}")
    parts.append(f"POSTURE STABILITY: {awareness.posture_stability_hours:.1f} hours")

    # Active threats
    if awareness.active_threats:
        parts.append(f"\nACTIVE THREATS ({len(awareness.active_threats)}):")
        for threat in awareness.active_threats[:5]:
            parts.append(
                f"  - {threat.vector.value}: severity={threat.severity:.2f}, "
                f"confidence={threat.confidence:.2f}, seen={threat.occurrence_count}x"
            )

    # Recent memories from this mind
    recent = recall_memories(mind_source=mind_type, limit=5)
    if recent:
        parts.append(f"\nRECENT {mind_type.value.upper()} OBSERVATIONS:")
        for mem in recent:
            parts.append(
                f"  - [{mem.memory_type}] {mem.content[:100]} "
                f"(decay={mem.decay_factor:.2f})"
            )

    # Baseline drift alerts
    if awareness.baseline_drift:
        parts.append("\nBASELINE DRIFT ALERTS:")
        for metric, sigma in awareness.baseline_drift.items():
            parts.append(f"  - {metric}: {sigma:.1f}σ from mean")

    # Input data to evaluate
    parts.append("\nINPUT TO EVALUATE:")
    parts.append(json.dumps(input_data, indent=2, default=str)[:2000])

    return "\n".join(parts)


def _build_signal_instruction() -> str:
    """Instructions for Nova Sovereign to produce a structured signal."""
    return """
Respond with a JSON object containing your cognitive signal:
{
    "signal_value": <float -1.0 to 1.0, negative=suppress action, positive=recommend action>,
    "confidence": <float 0.0 to 1.0>,
    "reasoning": "<one paragraph explaining your assessment>",
    "doctrine_basis": "<which rule/principle supports this signal>",
    "recommendation": "<specific recommended action>",
    "threat_vectors": [<list of detected threat vector strings>],
    "opportunity_detected": <boolean>,
    "contends_with": [<list of mind types this signal disagrees with>],
    "urgency_override": <boolean - only true for immediate critical threats>,
    "needs_more_data": [<list of data that would increase confidence>]
}

Valid threat_vectors: reconnaissance, credential_attack, injection, traversal,
exfiltration, privilege_escalation, denial_of_service, social_engineering,
supply_chain, unknown_anomaly

Valid mind types for contention: hacker, general, strategist, pilot, ai_intelligence

Return ONLY valid JSON. No markdown. No explanation outside the JSON.
"""


# ---------------------------------------------------------------------------
# Signal Generation
# ---------------------------------------------------------------------------

async def generate_mind_signal(
    mind_type: MindType,
    input_data: dict[str, Any],
    awareness: SituationalAwareness,
) -> MindSignal:
    """Generate a signal from a specific mind using Nova Sovereign.

    This is the core reasoning function. It:
    1. Gets the mind's system prompt
    2. Builds context from cortex state
    3. Calls Nova Sovereign for reasoning
    4. Parses the structured output
    5. Returns a fully-formed MindSignal
    """
    # Lazy import to avoid circular dependencies
    from ...integrations.nova_sovereign import get_nova_client

    profile = MIND_PROFILES[mind_type]
    client = get_nova_client()

    # Build messages
    system_prompt = (
        f"{profile.system_prompt_fragment}\n\n"
        f"RULES OF ENGAGEMENT:\n"
        + "\n".join(f"- {r}" for r in profile.rules_of_engagement)
        + f"\n\nESCALATION TRIGGERS:\n"
        + "\n".join(f"- {t}" for t in profile.escalation_triggers)
        + f"\n\nSUPPRESSION TRIGGERS:\n"
        + "\n".join(f"- {t}" for t in profile.suppression_triggers)
        + f"\n\n{_build_signal_instruction()}"
    )

    context = _build_mind_context(mind_type, input_data, awareness)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]

    try:
        response = await client.chat.completions.create(
            model="sovereign",
            messages=messages,
            temperature=0.1,  # Low temperature for consistent tactical reasoning
        )
        raw_output = response.content

        # Parse structured output
        signal_data = json.loads(raw_output)
        return _parse_signal_response(mind_type, signal_data, context)

    except json.JSONDecodeError as e:
        logger.warning(f"[ARCHON/{mind_type.value}] Failed to parse Nova response: {e}")
        return _fallback_signal(mind_type, input_data, awareness)
    except Exception as e:
        logger.error(f"[ARCHON/{mind_type.value}] Nova Sovereign call failed: {e}")
        return _fallback_signal(mind_type, input_data, awareness)


def _parse_signal_response(
    mind_type: MindType,
    data: dict[str, Any],
    context: str,
) -> MindSignal:
    """Parse Nova Sovereign response into a MindSignal."""
    # Parse threat vectors
    threat_vectors: list[ThreatVector] = []
    for tv_str in data.get("threat_vectors", []):
        try:
            threat_vectors.append(ThreatVector(tv_str))
        except ValueError:
            continue

    # Parse contention
    contends: list[MindType] = []
    for mt_str in data.get("contends_with", []):
        try:
            contends.append(MindType(mt_str))
        except ValueError:
            continue

    import hashlib
    input_digest = hashlib.sha256(context.encode()).hexdigest()[:16]

    return MindSignal(
        mind_type=mind_type,
        signal_value=max(-1.0, min(1.0, float(data.get("signal_value", 0.0)))),
        confidence=max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
        reasoning=str(data.get("reasoning", "")),
        doctrine_basis=str(data.get("doctrine_basis", "")),
        recommendation=str(data.get("recommendation", "")),
        threat_vectors_detected=threat_vectors,
        opportunity_detected=bool(data.get("opportunity_detected", False)),
        contends_with=contends,
        urgency_override=bool(data.get("urgency_override", False)),
        needs_more_data=data.get("needs_more_data", []),
        input_digest=input_digest,
    )


def _fallback_signal(
    mind_type: MindType,
    input_data: dict[str, Any],
    awareness: SituationalAwareness,
) -> MindSignal:
    """Generate a heuristic fallback signal when Nova Sovereign is unavailable.

    This implements the baseline heuristic logic so ARCHON can still function
    (degraded) without the intelligence backend.
    """
    import hashlib
    input_digest = hashlib.sha256(
        json.dumps(input_data, default=str).encode()
    ).hexdigest()[:16]

    alert = awareness.alert_level
    threat_count = len(awareness.active_threats)

    if mind_type == MindType.HACKER:
        # Hacker mind is sensitive to threat count and alert level
        signal_value = min(1.0, alert * 0.5 + threat_count * 0.1)
        confidence = 0.3 + alert * 0.2
        reasoning = f"Heuristic: {threat_count} active threats, alert={alert:.2f}"

    elif mind_type == MindType.GENERAL:
        # General mind pushes back against high urgency (discipline)
        signal_value = 0.3 - alert * 0.2  # More restrained as alert rises
        confidence = 0.5
        reasoning = "Heuristic: maintaining discipline, recommending restraint"

    elif mind_type == MindType.STRATEGIST:
        # Strategist evaluates long-term cost
        signal_value = 0.2 if alert < 0.5 else -0.1
        confidence = 0.4
        reasoning = "Heuristic: evaluating cost of action vs inaction"

    elif mind_type == MindType.PILOT:
        # Pilot ready to maneuver when alert is high
        signal_value = alert * 0.6
        confidence = 0.3 + alert * 0.3
        reasoning = f"Heuristic: maneuver readiness proportional to alert={alert:.2f}"

    else:  # AI_INTELLIGENCE
        # AI Intelligence always observes
        signal_value = 0.1  # Slight positive — always gather more data
        confidence = 0.6
        reasoning = "Heuristic: continuous observation, baseline monitoring"

    return MindSignal(
        mind_type=mind_type,
        signal_value=signal_value,
        confidence=confidence,
        reasoning=reasoning,
        doctrine_basis="Fallback heuristic — Nova Sovereign unavailable",
        recommendation="Operate in degraded mode, rely on heuristic signals",
        input_digest=input_digest,
    )


# ---------------------------------------------------------------------------
# Full Five-Mind Reasoning Cycle
# ---------------------------------------------------------------------------

async def run_full_cognition(
    input_data: dict[str, Any],
    awareness: SituationalAwareness | None = None,
) -> list[MindSignal]:
    """Run all five minds on the given input and return their signals.

    This is the complete cognitive cycle: each mind evaluates the same
    input context through its own lens and produces a structured signal.
    """
    if awareness is None:
        from .cortex import get_situational_awareness
        awareness = get_situational_awareness()

    import asyncio

    # Run all five minds concurrently
    tasks = [
        generate_mind_signal(mind_type, input_data, awareness)
        for mind_type in MindType
    ]
    signals = await asyncio.gather(*tasks)
    return list(signals)
