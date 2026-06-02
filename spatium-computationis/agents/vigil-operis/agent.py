"""
Agent: Vigil Operis  ◎
Role: Continuous monitoring agent — the sensor.

Watches all traffic, classifies visitors, detects anomalies,
and feeds real-time data to the defense dashboard.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ...integrations.nova_sovereign import NovaSovereignClient, get_nova_client

from ...defense.schemas import (
    BotClassification,
    BotFingerprint,
    DefenseMetrics,
    HoneypotEvent,
    ThreatFeedMessage,
    ThreatLevel,
)

_client: NovaSovereignClient | None = None


def _get_client() -> NovaSovereignClient:
    global _client
    if _client is None:
        _client = get_nova_client()
    return _client


DB_PATH = Path(__file__).parent.parent.parent / "field" / "defense.db"


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


_CLASSIFICATION_PROMPT = """\
You are Vigil Operis (◎), the monitoring agent of Spatium Computationis.

Analyze the visitor fingerprint and classify the bot type.

Classifications:
- legitimate: Known good bots (search engines, monitoring services)
- unknown: Cannot determine, needs more data
- scraper: Content scraping bot
- scanner: Vulnerability or security scanner
- crawler: Aggressive web crawler
- credential_stuffer: Login brute-forcer
- exploit_hunter: Looking for specific exploits
- ddos_participant: Part of DDoS attack
- research: Security researcher (ethical)
- honeypot_caught: Already triggered honeypot traps

Consider:
1. User-agent patterns (search engine bots, known tools)
2. Request patterns (paths, methods, timing)
3. Error rates (high error rate = likely scanner)
4. Request frequency (very high = potential DDoS)
5. Honeypot triggers (any triggers = suspicious)

Return JSON:
{
  "classification": "<bot_type>",
  "threat_level": "<none|low|medium|high|critical>",
  "confidence": <0.0-1.0>,
  "reasoning": "<brief explanation>",
  "indicators": ["<indicator1>", "<indicator2>", ...]
}

Return only valid JSON.
"""


async def classify_visitor(fingerprint: BotFingerprint) -> dict[str, Any]:
    """
    Classify a visitor based on their behavioral fingerprint.
    
    Uses AI to analyze patterns and determine bot type.
    """
    context = {
        "user_agent": fingerprint.user_agent,
        "requests_per_minute": fingerprint.requests_per_minute,
        "unique_paths": fingerprint.unique_paths,
        "error_rate": fingerprint.error_rate,
        "honeypot_triggers": fingerprint.honeypot_triggers,
        "total_requests": fingerprint.total_requests,
        "recent_paths": fingerprint.request_paths[-20:] if fingerprint.request_paths else [],
        "methods_used": list(set(fingerprint.http_methods)) if fingerprint.http_methods else [],
        "response_codes": list(set(fingerprint.response_codes)) if fingerprint.response_codes else [],
    }
    
    response = await _get_client().chat.completions.create(
        model="sovereign-lite",
        messages=[
            {"role": "system", "content": _CLASSIFICATION_PROMPT},
            {"role": "user", "content": json.dumps(context)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    
    return json.loads(response.choices[0].message.content)


async def detect_anomalies(
    current_metrics: DefenseMetrics,
    historical_baseline: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """
    Detect anomalies in current traffic patterns.
    
    Compares current metrics against historical baseline
    to identify unusual activity.
    """
    anomalies = []
    
    if historical_baseline is None:
        # Use default baseline
        historical_baseline = {
            "requests_per_minute": 100.0,
            "unique_visitors_per_minute": 20.0,
            "honeypot_triggers_per_hour": 5.0,
            "error_rate": 0.05,
        }
    
    # Check request volume
    rpm = current_metrics.total_requests / max(current_metrics.window_minutes, 1)
    baseline_rpm = historical_baseline.get("requests_per_minute", 100)
    if rpm > baseline_rpm * 3:
        anomalies.append({
            "type": "high_request_volume",
            "severity": "high" if rpm > baseline_rpm * 5 else "medium",
            "current_value": rpm,
            "baseline_value": baseline_rpm,
            "message": f"Request volume {rpm:.1f}/min is {rpm/baseline_rpm:.1f}x above baseline",
        })
    
    # Check honeypot triggers
    hpt = current_metrics.honeypot_triggers
    baseline_hpt = historical_baseline.get("honeypot_triggers_per_hour", 5) * (current_metrics.window_minutes / 60)
    if hpt > baseline_hpt * 2:
        anomalies.append({
            "type": "high_honeypot_triggers",
            "severity": "high",
            "current_value": hpt,
            "baseline_value": baseline_hpt,
            "message": f"Honeypot triggers {hpt} is {hpt/max(baseline_hpt,1):.1f}x above baseline",
        })
    
    # Check threat distribution
    high_threats = current_metrics.threat_level_counts.get("high", 0) + \
                   current_metrics.threat_level_counts.get("critical", 0)
    if high_threats > 5:
        anomalies.append({
            "type": "high_threat_concentration",
            "severity": "critical",
            "current_value": high_threats,
            "message": f"Detected {high_threats} high/critical threats in window",
        })
    
    return anomalies


def compute_metrics(window_minutes: int = 5) -> DefenseMetrics:
    """
    Compute real-time defense metrics for the specified time window.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=window_minutes)
    window_start_str = window_start.isoformat()
    
    with _db() as conn:
        # Total requests (approximated by fingerprint updates)
        total_requests = conn.execute(
            "SELECT SUM(total_requests) FROM fingerprints WHERE last_seen >= ?",
            (window_start_str,)
        ).fetchone()[0] or 0
        
        # Unique visitors
        unique_visitors = conn.execute(
            "SELECT COUNT(DISTINCT ip_address) FROM fingerprints WHERE last_seen >= ?",
            (window_start_str,)
        ).fetchone()[0] or 0
        
        # Honeypot triggers
        honeypot_triggers = conn.execute(
            "SELECT COUNT(*) FROM honeypot_events WHERE triggered_at >= ?",
            (window_start_str,)
        ).fetchone()[0] or 0
        
        # Classification breakdown
        classification_rows = conn.execute(
            "SELECT classification, COUNT(*) as cnt FROM fingerprints WHERE last_seen >= ? GROUP BY classification",
            (window_start_str,)
        ).fetchall()
        classification_counts = {row["classification"]: row["cnt"] for row in classification_rows}
        
        # Threat level breakdown
        threat_rows = conn.execute(
            "SELECT threat_level, COUNT(*) as cnt FROM fingerprints WHERE last_seen >= ? GROUP BY threat_level",
            (window_start_str,)
        ).fetchall()
        threat_level_counts = {row["threat_level"]: row["cnt"] for row in threat_rows}
        
        # Threats detected (non-none threat levels)
        threats_detected = sum(
            cnt for level, cnt in threat_level_counts.items()
            if level != "none"
        )
        
        # Top threat IPs
        top_threat_rows = conn.execute(
            """
            SELECT ip_address FROM fingerprints 
            WHERE last_seen >= ? AND threat_level != 'none'
            ORDER BY honeypot_triggers DESC, threat_level DESC
            LIMIT 10
            """,
            (window_start_str,)
        ).fetchall()
        top_threat_ips = [row["ip_address"] for row in top_threat_rows]
        
        # Top attack patterns
        pattern_rows = conn.execute(
            """
            SELECT attack_pattern, COUNT(*) as cnt FROM honeypot_events
            WHERE triggered_at >= ? AND attack_pattern IS NOT NULL
            GROUP BY attack_pattern
            ORDER BY cnt DESC
            LIMIT 10
            """,
            (window_start_str,)
        ).fetchall()
        top_attack_patterns = [row["attack_pattern"] for row in pattern_rows]
        
        # Top trap types
        trap_rows = conn.execute(
            """
            SELECT trap_type, COUNT(*) as cnt FROM honeypot_events
            WHERE triggered_at >= ?
            GROUP BY trap_type
            ORDER BY cnt DESC
            LIMIT 10
            """,
            (window_start_str,)
        ).fetchall()
        top_trap_types = [row["trap_type"] for row in trap_rows]
    
    return DefenseMetrics(
        timestamp=now,
        window_minutes=window_minutes,
        total_requests=total_requests,
        unique_visitors=unique_visitors,
        honeypot_triggers=honeypot_triggers,
        threats_detected=threats_detected,
        classification_counts=classification_counts,
        threat_level_counts=threat_level_counts,
        top_threat_ips=top_threat_ips,
        top_attack_patterns=top_attack_patterns,
        top_trap_types=top_trap_types,
    )


def create_feed_message(
    message_type: str,
    data: dict[str, Any],
) -> ThreatFeedMessage:
    """Create a WebSocket feed message."""
    return ThreatFeedMessage(
        message_type=message_type,
        data=data,
        timestamp=datetime.now(timezone.utc),
    )


def get_recent_threat_feed(limit: int = 50) -> list[ThreatFeedMessage]:
    """
    Get recent events for the threat feed.
    
    Returns a mix of honeypot events and threat alerts.
    """
    messages = []
    
    with _db() as conn:
        # Recent honeypot events
        events = conn.execute(
            """
            SELECT * FROM honeypot_events 
            ORDER BY triggered_at DESC 
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        
        for row in events:
            messages.append(ThreatFeedMessage(
                message_type="honeypot_event",
                data={
                    "event_id": row["event_id"],
                    "trap_type": row["trap_type"],
                    "trap_path": row["trap_path"],
                    "ip_address": row["ip_address"],
                    "attack_pattern": row["attack_pattern"],
                    "tools_detected": json.loads(row["tools_detected"]),
                },
                timestamp=datetime.fromisoformat(row["triggered_at"]),
            ))
        
        # Recent high-threat fingerprints
        threats = conn.execute(
            """
            SELECT * FROM fingerprints 
            WHERE threat_level IN ('high', 'critical')
            ORDER BY last_seen DESC 
            LIMIT ?
            """,
            (limit // 2,)
        ).fetchall()
        
        for row in threats:
            messages.append(ThreatFeedMessage(
                message_type="threat_alert",
                data={
                    "fingerprint_id": row["fingerprint_id"],
                    "ip_address": row["ip_address"],
                    "classification": row["classification"],
                    "threat_level": row["threat_level"],
                    "honeypot_triggers": row["honeypot_triggers"],
                },
                timestamp=datetime.fromisoformat(row["last_seen"]),
            ))
    
    # Sort by timestamp
    messages.sort(key=lambda m: m.timestamp, reverse=True)
    return messages[:limit]


async def run_continuous_monitoring() -> DefenseMetrics:
    """
    Run a continuous monitoring cycle.
    
    This is called periodically to update metrics and detect anomalies.
    """
    metrics = compute_metrics(window_minutes=5)
    anomalies = await detect_anomalies(metrics)
    
    if anomalies:
        metrics.new_patterns_learned = len(anomalies)
    
    return metrics
