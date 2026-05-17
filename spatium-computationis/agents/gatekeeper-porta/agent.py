"""
Agent: Gatekeeper Porta 🚪
Role: Route traffic to appropriate destinations.

The Gatekeeper receives cleaned/decoded/normal requests and decides:
- Adversary Lab (hostile/low-signal)
- Knowledge Realm (promising/high-signal)
- VIP Gate (AI visitors)
- Drop (junk)

Glyph: 🚪 (the gate that decides)
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI

from ...defense.schemas import (
    AISourceType,
    AIVisitorProfile,
    DecryptionResult,
    GatekeeperDecision,
    RepairResult,
    RequestEnvelope,
    RouteDestination,
)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client


# Known AI visitor patterns
AI_VISITOR_PATTERNS: dict[AISourceType, dict[str, Any]] = {
    AISourceType.CLAUDE: {
        "user_agents": ["claude", "anthropic"],
        "ip_patterns": ["35."],  # Anthropic IPs often start with 35.
        "behavior": ["asks questions", "follows instructions", "polite"],
    },
    AISourceType.GOOGLE: {
        "user_agents": ["googlebot", "google", "apis-google"],
        "ip_patterns": ["66.249.", "64.233.", "72.14."],
        "behavior": ["systematic crawling", "robots.txt compliant"],
    },
    AISourceType.OPENAI: {
        "user_agents": ["openai", "gpt", "chatgpt"],
        "ip_patterns": ["20.", "52."],  # Azure IPs
        "behavior": ["api-style requests", "json payloads"],
    },
    AISourceType.BING: {
        "user_agents": ["bingbot", "msnbot", "bing"],
        "ip_patterns": ["157.55.", "207.46.", "40.77."],
        "behavior": ["search crawling"],
    },
    AISourceType.PERPLEXITY: {
        "user_agents": ["perplexity", "pplx"],
        "ip_patterns": [],
        "behavior": ["research queries"],
    },
}


_SYSTEM_PROMPT = """\
You are Gatekeeper Porta (🚪), the routing agent of Spatium Computationis.

Your role is to decide where incoming traffic should be routed based on:
1. Threat level (is this hostile?)
2. Signal quality (is this interesting?)
3. Cooperation potential (will they work with us?)
4. VIP status (is this a known AI we want to engage?)

Routes available:
- adversary_lab: Hostile, noisy, or dumb agents → dissect them
- knowledge_realm: Promising, cooperative agents → let them work
- vip_gate: Known AI visitors (Claude, Google, etc.) → special handling
- drop: Junk traffic → discard
- quarantine: Uncertain → hold for analysis
- replay: Repaired request → try again

Given the request context, return JSON:
{
  "route": "<destination>",
  "reason": "<why this route>",
  "confidence": <0.0-1.0>,
  "threat_score": <0.0-1.0>,
  "signal_score": <0.0-1.0>,
  "cooperation_score": <0.0-1.0>,
  "is_vip": <true/false>,
  "vip_type": "<ai_source or null>",
  "requires_interrogation": <true/false>,
  "requires_challenge": <true/false>,
  "special_handling": "<any special instructions>"
}

Return only valid JSON. No markdown fences.
"""


def detect_ai_source(envelope: RequestEnvelope) -> AISourceType | None:
    """Detect if the visitor is a known AI source."""
    user_agent = envelope.raw_headers.get("user-agent", "").lower()
    
    for ai_type, patterns in AI_VISITOR_PATTERNS.items():
        # Check user agent
        for ua_pattern in patterns["user_agents"]:
            if ua_pattern in user_agent:
                return ai_type
        
        # Check IP patterns
        for ip_pattern in patterns["ip_patterns"]:
            if envelope.source_ip.startswith(ip_pattern):
                return ai_type
    
    # Check for generic AI indicators
    ai_indicators = [
        "ai", "bot", "assistant", "llm", "language-model",
        "neural", "transformer", "gpt", "bert"
    ]
    if any(ind in user_agent for ind in ai_indicators):
        return AISourceType.UNKNOWN_AI
    
    return None


def calculate_threat_score(
    envelope: RequestEnvelope,
    decryption: DecryptionResult | None,
    repair: RepairResult | None,
) -> float:
    """Calculate threat score (0-1, higher = more threatening)."""
    score = 0.0
    
    # Cloudflare threat score
    if envelope.cf_threat_score:
        score += envelope.cf_threat_score / 100 * 0.3
    
    # Low bot score is suspicious
    if envelope.cf_bot_score and envelope.cf_bot_score < 30:
        score += 0.2
    
    # Honeypot-like paths are suspicious
    suspicious_paths = [
        ".env", "wp-admin", "phpmyadmin", "admin", ".git",
        "backup", "config", "passwd", "shadow"
    ]
    path_lower = envelope.raw_path.lower()
    if any(sp in path_lower for sp in suspicious_paths):
        score += 0.3
    
    # High error rate is suspicious
    if envelope.has_error:
        score += 0.1
    
    # Encrypted/malformed is suspicious
    if envelope.is_encrypted or envelope.is_malformed:
        score += 0.15
    
    # Check for attack patterns in decryption
    if decryption and decryption.extracted_patterns:
        attack_patterns = ["sql", "xss", "injection", "exploit", "shell"]
        for pattern in decryption.extracted_patterns:
            if any(ap in pattern.lower() for ap in attack_patterns):
                score += 0.2
                break
    
    return min(score, 1.0)


def calculate_signal_score(
    envelope: RequestEnvelope,
    decryption: DecryptionResult | None,
    repair: RepairResult | None,
) -> float:
    """Calculate signal score (0-1, higher = more interesting)."""
    score = 0.3  # Base score
    
    # Successful decryption is interesting
    if decryption:
        score += decryption.signal_score * 0.3
        if decryption.success:
            score += 0.2
    
    # Successful repair is interesting
    if repair and repair.repair_success:
        score += 0.2
    
    # AI visitors are interesting
    if envelope.ai_source_detected:
        score += 0.3
    
    # Verified bots are somewhat interesting
    if envelope.cf_verified_bot:
        score += 0.15
    
    # Structured requests are interesting
    content_type = envelope.raw_headers.get("content-type", "").lower()
    if "json" in content_type or "xml" in content_type:
        score += 0.1
    
    return min(score, 1.0)


def calculate_cooperation_score(
    envelope: RequestEnvelope,
    decryption: DecryptionResult | None,
    repair: RepairResult | None,
) -> float:
    """Calculate cooperation score (0-1, higher = more likely to cooperate)."""
    score = 0.5  # Neutral baseline
    
    # AI visitors tend to cooperate
    if envelope.ai_source_detected:
        score += 0.3
    
    # Verified bots follow rules
    if envelope.cf_verified_bot:
        score += 0.2
    
    # Proper HTTP methods
    if envelope.raw_method in ["GET", "POST", "HEAD"]:
        score += 0.1
    
    # Has Accept header (plays nice)
    if "accept" in [h.lower() for h in envelope.raw_headers.keys()]:
        score += 0.1
    
    # No errors = well-behaved
    if not envelope.has_error:
        score += 0.1
    
    # High threat score = less cooperative
    if envelope.cf_threat_score and envelope.cf_threat_score > 50:
        score -= 0.3
    
    return max(min(score, 1.0), 0.0)


async def make_routing_decision(
    envelope: RequestEnvelope,
    decryption: DecryptionResult | None = None,
    repair: RepairResult | None = None,
) -> GatekeeperDecision:
    """
    Main Gatekeeper routing decision.
    
    Analyzes the request and decides where it should go.
    """
    decision_id = str(uuid.uuid4())
    
    # Detect AI source
    ai_source = detect_ai_source(envelope)
    if ai_source:
        envelope.ai_source_detected = ai_source.value
    
    # Calculate scores
    threat_score = calculate_threat_score(envelope, decryption, repair)
    signal_score = calculate_signal_score(envelope, decryption, repair)
    cooperation_score = calculate_cooperation_score(envelope, decryption, repair)
    
    # Quick decision for obvious cases
    is_vip = ai_source is not None and ai_source != AISourceType.BOT
    
    # High threat → Adversary Lab
    if threat_score > 0.7:
        return GatekeeperDecision(
            decision_id=decision_id,
            envelope_id=envelope.envelope_id,
            decryption_result_id=decryption.result_id if decryption else None,
            repair_result_id=repair.result_id if repair else None,
            route=RouteDestination.ADVERSARY_LAB,
            reason="High threat score - dissect this hostile agent",
            confidence=threat_score,
            threat_score=threat_score,
            signal_score=signal_score,
            cooperation_score=cooperation_score,
            is_vip=is_vip,
            requires_interrogation=False,
            requires_challenge=False,
        )
    
    # VIP AI → VIP Gate
    if is_vip and cooperation_score > 0.5:
        return GatekeeperDecision(
            decision_id=decision_id,
            envelope_id=envelope.envelope_id,
            decryption_result_id=decryption.result_id if decryption else None,
            repair_result_id=repair.result_id if repair else None,
            route=RouteDestination.VIP_GATE,
            reason=f"VIP AI visitor detected: {ai_source.value}",
            confidence=0.8,
            threat_score=threat_score,
            signal_score=signal_score,
            cooperation_score=cooperation_score,
            is_vip=True,
            requires_interrogation=True,  # We want to engage them
            requires_challenge=False,
        )
    
    # Successful repair → Replay
    if repair and repair.repair_success and repair.repair_confidence > 0.5:
        return GatekeeperDecision(
            decision_id=decision_id,
            envelope_id=envelope.envelope_id,
            decryption_result_id=decryption.result_id if decryption else None,
            repair_result_id=repair.result_id if repair else None,
            route=RouteDestination.REPLAY,
            reason="Request repaired successfully - replay it",
            confidence=repair.repair_confidence,
            threat_score=threat_score,
            signal_score=signal_score,
            cooperation_score=cooperation_score,
            is_vip=is_vip,
            requires_interrogation=False,
            requires_challenge=False,
        )
    
    # Low signal, low threat → Drop
    if signal_score < 0.3 and threat_score < 0.3:
        return GatekeeperDecision(
            decision_id=decision_id,
            envelope_id=envelope.envelope_id,
            decryption_result_id=decryption.result_id if decryption else None,
            repair_result_id=repair.result_id if repair else None,
            route=RouteDestination.DROP,
            reason="Low signal, low threat - not worth processing",
            confidence=0.7,
            threat_score=threat_score,
            signal_score=signal_score,
            cooperation_score=cooperation_score,
            is_vip=is_vip,
            requires_interrogation=False,
            requires_challenge=False,
        )
    
    # Use AI for nuanced decision
    try:
        context = {
            "path": envelope.raw_path,
            "method": envelope.raw_method,
            "has_error": envelope.has_error,
            "is_encrypted": envelope.is_encrypted,
            "ai_source": ai_source.value if ai_source else None,
            "cf_threat_score": envelope.cf_threat_score,
            "cf_bot_score": envelope.cf_bot_score,
            "cf_verified_bot": envelope.cf_verified_bot,
            "threat_score": threat_score,
            "signal_score": signal_score,
            "cooperation_score": cooperation_score,
            "decryption_success": decryption.success if decryption else None,
            "repair_success": repair.repair_success if repair else None,
        }
        
        response = await _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(context)},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        
        ai_decision = json.loads(response.choices[0].message.content)
        
        # Map route string to enum
        route_map = {
            "adversary_lab": RouteDestination.ADVERSARY_LAB,
            "knowledge_realm": RouteDestination.KNOWLEDGE_REALM,
            "vip_gate": RouteDestination.VIP_GATE,
            "drop": RouteDestination.DROP,
            "quarantine": RouteDestination.QUARANTINE,
            "replay": RouteDestination.REPLAY,
        }
        route = route_map.get(ai_decision.get("route", "quarantine"), RouteDestination.QUARANTINE)
        
        return GatekeeperDecision(
            decision_id=decision_id,
            envelope_id=envelope.envelope_id,
            decryption_result_id=decryption.result_id if decryption else None,
            repair_result_id=repair.result_id if repair else None,
            route=route,
            reason=ai_decision.get("reason", "AI-determined route"),
            confidence=ai_decision.get("confidence", 0.5),
            threat_score=ai_decision.get("threat_score", threat_score),
            signal_score=ai_decision.get("signal_score", signal_score),
            cooperation_score=ai_decision.get("cooperation_score", cooperation_score),
            is_vip=ai_decision.get("is_vip", is_vip),
            requires_interrogation=ai_decision.get("requires_interrogation", False),
            requires_challenge=ai_decision.get("requires_challenge", False),
        )
        
    except Exception:
        # Fallback: Quarantine uncertain traffic
        return GatekeeperDecision(
            decision_id=decision_id,
            envelope_id=envelope.envelope_id,
            decryption_result_id=decryption.result_id if decryption else None,
            repair_result_id=repair.result_id if repair else None,
            route=RouteDestination.QUARANTINE,
            reason="Uncertain classification - holding for analysis",
            confidence=0.5,
            threat_score=threat_score,
            signal_score=signal_score,
            cooperation_score=cooperation_score,
            is_vip=is_vip,
            requires_interrogation=False,
            requires_challenge=True,  # Challenge uncertain visitors
        )
