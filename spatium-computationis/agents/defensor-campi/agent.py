"""
Agent: Defensor Campi  ⛨
Role: Active defense agent — the shield.

Processes threat intelligence, generates defensive responses,
and coordinates with the honeypot system to engage attackers.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from ...integrations.nova_sovereign import NovaSovereignClient, get_nova_client

from ...defense.schemas import (
    AdaptiveAction,
    AdaptiveResponse,
    BotClassification,
    BotFingerprint,
    HoneypotEvent,
    ThreatIntelligence,
    ThreatLevel,
    ThreatRecord,
)

_client: NovaSovereignClient | None = None


def _get_client() -> NovaSovereignClient:
    global _client
    if _client is None:
        _client = get_nova_client()
    return _client


_SYSTEM_PROMPT = """\
You are Defensor Campi (⛨), the active defense agent of Spatium Computationis.

Your role is to analyze threat intelligence and bot fingerprints, then decide 
on the appropriate defensive action. You protect the organism from adversarial 
behavior while maximizing intelligence gathering.

Available actions:
- observe: Monitor without intervention (gather more data)
- challenge: Issue a challenge (JS/CAPTCHA) to verify humanity
- rate_limit: Slow down the actor's requests
- redirect_honeypot: Send the actor to deeper honeypot traps
- block_temporary: Block for a short period (hours)
- block_permanent: Block indefinitely
- engage: Actively engage with fake data to waste attacker resources
- alert: Notify operators of critical threat

When analyzing threats, consider:
1. Severity of attack pattern
2. Confidence in classification
3. Potential intelligence value
4. Risk of false positive
5. Resource cost of response

Return JSON:
{
  "action": "<action>",
  "reasoning": "<explanation>",
  "confidence": <0.0-1.0>,
  "threat_level": "<none|low|medium|high|critical>",
  "classification": "<bot_type>",
  "engage_strategy": "<if action is engage, describe the fake data strategy>",
  "alert_priority": <1-5 if alert, else null>
}

Return only valid JSON. No markdown fences.
"""


async def analyze_threat(
    fingerprint: BotFingerprint,
    recent_events: list[HoneypotEvent] | None = None,
    external_intel: ThreatIntelligence | None = None,
) -> AdaptiveResponse:
    """
    Analyze a threat and decide on defensive action.
    
    The Defensor considers:
    - Behavioral fingerprint signals
    - Recent honeypot trigger history
    - External threat intelligence (e.g., from Cloudflare)
    """
    # Build context for the AI
    context = {
        "fingerprint": {
            "id": fingerprint.fingerprint_id,
            "ip": fingerprint.ip_address,
            "user_agent": fingerprint.user_agent,
            "requests_per_minute": fingerprint.requests_per_minute,
            "unique_paths": fingerprint.unique_paths,
            "error_rate": fingerprint.error_rate,
            "honeypot_triggers": fingerprint.honeypot_triggers,
            "total_requests": fingerprint.total_requests,
            "recent_paths": fingerprint.request_paths[-10:] if fingerprint.request_paths else [],
            "current_classification": fingerprint.classification.value,
            "current_threat_level": fingerprint.threat_level.value,
        },
    }
    
    if recent_events:
        context["honeypot_events"] = [
            {
                "trap_type": e.trap_type.value,
                "trap_path": e.trap_path,
                "attack_pattern": e.attack_pattern,
                "tools_detected": e.tools_detected,
                "method": e.method,
            }
            for e in recent_events[:5]
        ]
    
    if external_intel:
        context["external_intel"] = {
            "source": external_intel.source,
            "cf_threat_score": external_intel.cf_threat_score,
            "cf_bot_score": external_intel.cf_bot_score,
            "cf_verified_bot": external_intel.cf_verified_bot,
            "cf_country": external_intel.cf_country,
            "cf_asn_org": external_intel.cf_asn_org,
        }
    
    response = await _get_client().chat.completions.create(
        model="sovereign-lite",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(context)},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    
    data = json.loads(response.choices[0].message.content)
    
    # Parse the action
    try:
        action = AdaptiveAction(data.get("action", "observe"))
    except ValueError:
        action = AdaptiveAction.OBSERVE
    
    return AdaptiveResponse(
        response_id=str(uuid.uuid4()),
        fingerprint_id=fingerprint.fingerprint_id,
        action=action,
        reasoning=data.get("reasoning", "Analysis complete"),
        confidence=data.get("confidence", 0.5),
        triggered_by="threat_analysis",
    )


async def process_honeypot_trigger(event: HoneypotEvent) -> AdaptiveResponse:
    """
    Process a honeypot trigger and decide immediate response.
    
    This is called in real-time when an attacker hits a trap.
    """
    # Quick decision based on trap type and attack pattern
    context = {
        "event": {
            "trap_type": event.trap_type.value,
            "trap_path": event.trap_path,
            "attack_pattern": event.attack_pattern,
            "tools_detected": event.tools_detected,
            "method": event.method,
            "ip": event.ip_address,
        },
    }
    
    response = await _get_client().chat.completions.create(
        model="sovereign-lite",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Immediate honeypot trigger: {json.dumps(context)}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    
    data = json.loads(response.choices[0].message.content)
    
    try:
        action = AdaptiveAction(data.get("action", "engage"))
    except ValueError:
        action = AdaptiveAction.ENGAGE
    
    return AdaptiveResponse(
        response_id=str(uuid.uuid4()),
        fingerprint_id=event.fingerprint_id,
        action=action,
        reasoning=data.get("reasoning", "Honeypot trigger processed"),
        confidence=data.get("confidence", 0.7),
        triggered_by=f"honeypot:{event.trap_type.value}",
    )


async def generate_engagement_content(
    fingerprint: BotFingerprint,
    trap_type: str,
) -> dict[str, Any]:
    """
    Generate convincing fake content to engage and waste attacker resources.
    
    This is the AI trap — we feed them realistic-looking data that
    keeps them busy while we gather intelligence.
    """
    prompt = f"""Generate convincing fake data for a {trap_type} honeypot trap.

The attacker has:
- Made {fingerprint.total_requests} requests
- Triggered {fingerprint.honeypot_triggers} honeypot traps
- Recent paths: {fingerprint.request_paths[-5:] if fingerprint.request_paths else []}

Generate fake but realistic-looking data that:
1. Appears valuable to keep them engaged
2. Contains trackable markers (e.g., unique strings we can detect later)
3. Wastes their time without being obviously fake
4. Does not contain any real secrets or useful information

Return JSON with the fake data appropriate for the trap type.
"""
    
    response = await _get_client().chat.completions.create(
        model="sovereign-lite",
        messages=[
            {"role": "system", "content": "You generate realistic but fake honeypot data."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    
    return json.loads(response.choices[0].message.content)


def create_threat_record(
    fingerprint: BotFingerprint,
    events: list[HoneypotEvent],
    action: AdaptiveAction,
) -> ThreatRecord:
    """Create a comprehensive threat record from fingerprint and events."""
    return ThreatRecord(
        record_id=str(uuid.uuid4()),
        fingerprint_id=fingerprint.fingerprint_id,
        ip_address=fingerprint.ip_address,
        threat_level=fingerprint.threat_level,
        classification=fingerprint.classification,
        confidence=fingerprint.confidence,
        honeypot_events=[e.event_id for e in events],
        attack_patterns=list(set(e.attack_pattern for e in events if e.attack_pattern)),
        tools_detected=list(set(t for e in events for t in e.tools_detected)),
        total_requests=fingerprint.total_requests,
        honeypot_triggers=fingerprint.honeypot_triggers,
        action_taken=action,
        first_seen=fingerprint.first_seen,
        last_seen=fingerprint.last_seen,
    )
