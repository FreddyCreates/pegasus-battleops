"""
Cloudflare Integration — External Threat Intelligence
◎ Receive and process Cloudflare security events.

This module provides:
1. Webhook endpoint for Cloudflare events
2. Processing of Cloudflare threat scores
3. Integration with the defense system
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from ..schemas import (
    AdaptiveAction,
    BotClassification,
    ThreatIntelligence,
    ThreatLevel,
)


# ---------------------------------------------------------------------------
# Cloudflare Webhook Models
# ---------------------------------------------------------------------------

class CloudflareWebhook(BaseModel):
    """Incoming Cloudflare webhook event."""
    
    # Common fields
    ray_id: str | None = Field(None, alias="rayId")
    client_ip: str = Field(alias="clientIP")
    client_request_host: str | None = Field(None, alias="clientRequestHost")
    client_request_path: str | None = Field(None, alias="clientRequestPath")
    client_request_method: str | None = Field(None, alias="clientRequestMethod")
    
    # Cloudflare security fields
    security_level: str | None = Field(None, alias="securityLevel")
    waf_action: str | None = Field(None, alias="wafAction")
    waf_rule_id: str | None = Field(None, alias="wafRuleId")
    
    # Bot management fields
    bot_score: int | None = Field(None, alias="botScore", ge=1, le=99)
    bot_score_src: str | None = Field(None, alias="botScoreSrc")
    verified_bot: bool = Field(False, alias="verifiedBot")
    ja3_hash: str | None = Field(None, alias="ja3Hash")
    ja4: str | None = None
    
    # Threat intelligence
    threat_score: int | None = Field(None, alias="threatScore", ge=0, le=100)
    
    # Geo/ASN
    client_country: str | None = Field(None, alias="clientCountry")
    client_asn: int | None = Field(None, alias="clientASN")
    client_asn_description: str | None = Field(None, alias="clientASNDescription")
    
    # Request details
    user_agent: str | None = Field(None, alias="userAgent")
    
    # Event type
    action: str | None = None  # "log", "challenge", "block", etc.
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        populate_by_name = True


class CloudflareBotManagementEvent(BaseModel):
    """Cloudflare Bot Management specific event."""
    ray_id: str
    client_ip: str
    bot_score: int = Field(ge=1, le=99)
    verified_bot: bool = False
    bot_score_src: str | None = None
    ja3_hash: str | None = None
    ja4: str | None = None
    action_taken: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CloudflareFirewallEvent(BaseModel):
    """Cloudflare Firewall event."""
    ray_id: str
    client_ip: str
    rule_id: str
    action: str  # "block", "challenge", "js_challenge", "managed_challenge", "log"
    description: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Threat Level Mapping
# ---------------------------------------------------------------------------

def _threat_score_to_level(score: int | None) -> ThreatLevel:
    """Convert Cloudflare threat score (0-100) to ThreatLevel."""
    if score is None:
        return ThreatLevel.NONE
    if score >= 80:
        return ThreatLevel.CRITICAL
    if score >= 60:
        return ThreatLevel.HIGH
    if score >= 40:
        return ThreatLevel.MEDIUM
    if score >= 20:
        return ThreatLevel.LOW
    return ThreatLevel.NONE


def _bot_score_to_classification(
    bot_score: int | None,
    verified_bot: bool,
    threat_score: int | None,
) -> BotClassification:
    """Convert Cloudflare bot score to classification."""
    if verified_bot:
        return BotClassification.LEGITIMATE
    
    if bot_score is None:
        return BotClassification.UNKNOWN
    
    # Bot score: 1 = definitely bot, 99 = definitely human
    if bot_score >= 80:
        return BotClassification.UNKNOWN  # Likely human
    if bot_score >= 50:
        return BotClassification.CRAWLER  # Uncertain, could be bot
    if bot_score >= 30:
        return BotClassification.SCRAPER  # Likely bot
    
    # Very low bot score + high threat = malicious
    if threat_score and threat_score >= 50:
        return BotClassification.EXPLOIT_HUNTER
    
    return BotClassification.SCANNER


def _determine_action(
    threat_level: ThreatLevel,
    classification: BotClassification,
    waf_action: str | None,
) -> AdaptiveAction:
    """Determine recommended action based on Cloudflare data."""
    # If Cloudflare already blocked, we observe
    if waf_action == "block":
        return AdaptiveAction.OBSERVE
    
    # Critical threats get blocked
    if threat_level == ThreatLevel.CRITICAL:
        return AdaptiveAction.BLOCK_PERMANENT
    
    # High threats get temporary block or redirect
    if threat_level == ThreatLevel.HIGH:
        return AdaptiveAction.REDIRECT_HONEYPOT
    
    # Medium threats get challenged
    if threat_level == ThreatLevel.MEDIUM:
        return AdaptiveAction.CHALLENGE
    
    # Suspected bots get rate limited or redirected to honeypot
    if classification in [BotClassification.SCANNER, BotClassification.EXPLOIT_HUNTER]:
        return AdaptiveAction.REDIRECT_HONEYPOT
    
    if classification in [BotClassification.SCRAPER, BotClassification.CRAWLER]:
        return AdaptiveAction.RATE_LIMIT
    
    return AdaptiveAction.OBSERVE


# ---------------------------------------------------------------------------
# Event Processing
# ---------------------------------------------------------------------------

def process_cloudflare_event(event: CloudflareWebhook) -> ThreatIntelligence:
    """
    Process a Cloudflare webhook event into internal threat intelligence.
    
    This transforms Cloudflare's data into our internal format for
    integration with the defense system.
    """
    threat_level = _threat_score_to_level(event.threat_score)
    classification = _bot_score_to_classification(
        event.bot_score,
        event.verified_bot,
        event.threat_score,
    )
    recommended_action = _determine_action(
        threat_level,
        classification,
        event.waf_action,
    )
    
    return ThreatIntelligence(
        intel_id=str(uuid.uuid4()),
        source="cloudflare",
        cf_ray=event.ray_id,
        cf_threat_score=event.threat_score,
        cf_bot_score=event.bot_score,
        cf_verified_bot=event.verified_bot,
        cf_country=event.client_country,
        cf_asn=event.client_asn,
        cf_asn_org=event.client_asn_description,
        ip_address=event.client_ip,
        threat_level=threat_level,
        classification=classification,
        recommended_action=recommended_action,
        received_at=datetime.now(timezone.utc),
    )


def create_cloudflare_rules_template() -> dict[str, Any]:
    """
    Generate a Cloudflare Rules template for integration.
    
    This can be used to configure Cloudflare to:
    1. Send webhook events to our API
    2. Apply custom rules based on our threat intelligence
    3. Redirect suspicious traffic to honeypots
    """
    return {
        "description": "Spatium Computationis Defense Integration",
        "rules": [
            {
                "name": "Log All Suspicious Traffic",
                "description": "Send webhook for suspicious visitors",
                "expression": "(cf.threat_score gt 10) or (cf.bot_management.score lt 50)",
                "action": "log",
                "action_parameters": {
                    "request_headers": ["user-agent", "accept-language"],
                    "response_headers": []
                }
            },
            {
                "name": "Challenge High-Risk Visitors",
                "description": "Challenge visitors with high threat score",
                "expression": "cf.threat_score gt 50",
                "action": "managed_challenge"
            },
            {
                "name": "Block Critical Threats",
                "description": "Block visitors with critical threat score",
                "expression": "cf.threat_score gt 80",
                "action": "block"
            },
            {
                "name": "Redirect Scanners to Honeypot",
                "description": "Send vulnerability scanners to honeypot",
                "expression": """
                    (cf.bot_management.score lt 30) and 
                    (http.request.uri.path contains ".env" or 
                     http.request.uri.path contains "wp-admin" or
                     http.request.uri.path contains "phpmyadmin" or
                     http.request.uri.path contains ".git")
                """,
                "action": "redirect",
                "action_parameters": {
                    "url": "https://your-domain.com/honeypot{http.request.uri.path}"
                }
            }
        ],
        "webhook_config": {
            "url": "https://your-domain.com/api/defense/cloudflare/webhook",
            "events": ["firewall_events", "bot_management_events"],
            "headers": {
                "X-Webhook-Secret": "YOUR_SECRET_HERE"
            }
        }
    }


def create_cloudflare_worker_template() -> str:
    """
    Generate a Cloudflare Worker template for advanced integration.
    
    This worker can:
    1. Intercept requests before they reach origin
    2. Apply custom threat logic
    3. Send real-time data to our API
    4. Route traffic based on our intelligence
    """
    return '''
// Spatium Computationis Defense Worker
// Deploy to Cloudflare Workers for advanced traffic interception

const SPATIUM_API = "https://your-domain.com/api/defense";
const WEBHOOK_SECRET = "YOUR_SECRET_HERE";

addEventListener("fetch", event => {
    event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
    const url = new URL(request.url);
    const clientIP = request.headers.get("CF-Connecting-IP");
    const rayId = request.headers.get("CF-Ray");
    
    // Get Cloudflare bot/threat data
    const botScore = request.cf?.botManagement?.score || 99;
    const verifiedBot = request.cf?.botManagement?.verifiedBot || false;
    const threatScore = request.cf?.threatScore || 0;
    const country = request.cf?.country || "unknown";
    const asn = request.cf?.asn || 0;
    
    // Build threat context
    const threatContext = {
        rayId,
        clientIP,
        path: url.pathname,
        method: request.method,
        userAgent: request.headers.get("User-Agent"),
        botScore,
        verifiedBot,
        threatScore,
        country,
        asn,
        timestamp: new Date().toISOString()
    };
    
    // Check if this is a honeypot path
    const honeypotPaths = [
        "/.env", "/wp-admin", "/wp-login.php", "/phpmyadmin",
        "/.git", "/admin", "/config.php", "/backup.sql"
    ];
    
    const isHoneypotPath = honeypotPaths.some(p => 
        url.pathname.toLowerCase().includes(p)
    );
    
    // Decision logic
    let decision = "allow";
    
    if (threatScore > 80) {
        decision = "block";
    } else if (threatScore > 50 || (botScore < 30 && !verifiedBot)) {
        decision = isHoneypotPath ? "engage" : "challenge";
    } else if (isHoneypotPath && botScore < 50) {
        decision = "engage";  // Let honeypot handle it
    }
    
    // Send to Spatium API (non-blocking)
    sendToSpatium(threatContext, decision);
    
    // Apply decision
    switch (decision) {
        case "block":
            return new Response("Access Denied", { status: 403 });
        
        case "challenge":
            // Return a challenge page
            return generateChallengePage(clientIP, rayId);
        
        case "engage":
            // Let request through to honeypot
            threatContext.honeypotEngaged = true;
            sendToSpatium(threatContext, "honeypot_engaged");
            break;
        
        default:
            // Allow through
            break;
    }
    
    // Pass to origin
    return fetch(request);
}

async function sendToSpatium(context, decision) {
    try {
        await fetch(`${SPATIUM_API}/cloudflare/event`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Webhook-Secret": WEBHOOK_SECRET
            },
            body: JSON.stringify({ ...context, decision })
        });
    } catch (e) {
        // Non-blocking, log and continue
        console.error("Failed to send to Spatium:", e);
    }
}

function generateChallengePage(ip, rayId) {
    const html = `
    <!DOCTYPE html>
    <html>
    <head>
        <title>Security Check</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                height: 100vh; 
                background: #1a1a2e; 
                color: #eee;
                margin: 0;
            }
            .container { 
                text-align: center; 
                padding: 40px;
                background: #16213e;
                border-radius: 10px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            }
            .glyph { font-size: 64px; margin-bottom: 20px; }
            h1 { margin-bottom: 10px; }
            p { color: #888; }
            .spinner {
                width: 40px;
                height: 40px;
                border: 4px solid #333;
                border-top: 4px solid #0f3460;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="glyph">⛨</div>
            <h1>Security Check</h1>
            <p>Verifying your browser...</p>
            <div class="spinner"></div>
            <p style="font-size: 12px; margin-top: 20px;">
                Ray ID: ${rayId}
            </p>
        </div>
        <script>
            // Simulate challenge completion
            setTimeout(() => {
                window.location.reload();
            }, 3000);
        </script>
    </body>
    </html>
    `;
    
    return new Response(html, {
        status: 403,
        headers: { "Content-Type": "text/html" }
    });
}
'''.strip()
