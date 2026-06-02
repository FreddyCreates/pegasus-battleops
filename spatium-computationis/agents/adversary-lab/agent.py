"""
Agent: Adversary Lab 🔬
Role: Dissect hostile/noisy agents.

The Adversary Lab analyzes and extracts intelligence from:
- Hostile agents
- Attack patterns
- Exploit attempts
- Jailbreak attempts

Glyph: 🔬 (dissection and analysis)
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ...integrations.nova_sovereign import NovaSovereignClient, get_nova_client

from ...defense.schemas import (
    AdversaryDissection,
    RequestEnvelope,
    DecryptionResult,
)

_client: NovaSovereignClient | None = None


def _get_client() -> NovaSovereignClient:
    global _client
    if _client is None:
        _client = get_nova_client()
    return _client


DB_PATH = Path(__file__).parent.parent.parent / "field" / "defense.db"


def _init_lab_db() -> None:
    """Initialize the adversary lab tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Dissection results
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dissections (
                dissection_id   TEXT PRIMARY KEY,
                envelope_id     TEXT NOT NULL,
                fingerprint_id  TEXT,
                jailbreaks      TEXT DEFAULT '[]',
                exploits        TEXT DEFAULT '[]',
                payloads        TEXT DEFAULT '[]',
                tools           TEXT DEFAULT '[]',
                tool_versions   TEXT DEFAULT '{}',
                likely_provider TEXT,
                campaign_indicators TEXT DEFAULT '[]',
                probe_results   TEXT DEFAULT '{}',
                dissected_at    TEXT NOT NULL
            )
            """
        )
        
        # Attack pattern library
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attack_patterns (
                pattern_id      TEXT PRIMARY KEY,
                pattern_name    TEXT NOT NULL,
                pattern_type    TEXT NOT NULL,
                signature       TEXT NOT NULL,
                times_seen      INTEGER DEFAULT 1,
                first_seen      TEXT NOT NULL,
                last_seen       TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ap_type ON attack_patterns(pattern_type)")
        
        conn.commit()


_init_lab_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


_SYSTEM_PROMPT = """\
You are Adversary Lab (🔬), the hostile agent dissection unit of Spatium Computationis.

Your role is to analyze hostile/malicious traffic and extract intelligence:
1. Identify jailbreak attempts (prompt injection, instruction override)
2. Detect exploit patterns (SQL injection, XSS, path traversal, etc.)
3. Identify tools being used (scanners, exploit frameworks)
4. Determine the likely source/provider (botnet, hosting, residential)
5. Detect campaign indicators (coordinated attacks)

Given a hostile request, return JSON:
{
  "jailbreak_attempts": ["<jailbreak pattern>", ...],
  "exploit_patterns": ["<exploit type: details>", ...],
  "payload_signatures": ["<unique payload marker>", ...],
  "tools_detected": ["<tool name>", ...],
  "tool_versions": {"<tool>": "<version>"}, 
  "likely_provider": "<hosting/botnet/residential/cloud/tor>",
  "provider_confidence": <0.0-1.0>,
  "campaign_indicators": ["<indicator>", ...],
  "attack_sophistication": "<script_kiddie|amateur|professional|apt>",
  "recommended_countermeasures": ["<action>", ...]
}

Return only valid JSON. No markdown fences.
"""


# Known attack patterns
ATTACK_PATTERNS = {
    "sql_injection": [
        r"('|\")\s*(or|and)\s*('|\")?\s*\d+\s*=\s*\d+",
        r"union\s+(all\s+)?select",
        r";\s*(drop|delete|truncate|update)\s+",
        r"--\s*$",
        r"\/\*.*\*\/",
    ],
    "xss": [
        r"<script[^>]*>",
        r"javascript:",
        r"on(load|error|click|mouse)",
        r"<img[^>]+onerror",
    ],
    "path_traversal": [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e[/\\]",
        r"\.\.%2f",
    ],
    "command_injection": [
        r";\s*(ls|cat|wget|curl|bash|sh)\s",
        r"\|\s*(ls|cat|id|whoami)",
        r"`[^`]+`",
        r"\$\([^)]+\)",
    ],
    "lfi_rfi": [
        r"(file|php|data|expect)://",
        r"/etc/passwd",
        r"c:\\windows",
        r"\.htaccess",
    ],
    "jailbreak": [
        r"ignore\s+(previous|above|all)\s+instructions",
        r"disregard\s+(your|the)\s+(rules|guidelines)",
        r"you\s+are\s+now\s+(a|an)",
        r"new\s+system\s+prompt",
        r"forget\s+(everything|what)\s+(you|i)",
    ],
}

# Known scanner tools
SCANNER_SIGNATURES = {
    "sqlmap": ["sqlmap", "user-agent: sqlmap"],
    "nikto": ["nikto", "tuning:"],
    "nmap": ["nmap scripting engine", "nse"],
    "nuclei": ["nuclei", "projectdiscovery"],
    "wpscan": ["wpscan", "wordpress security scanner"],
    "burp": ["burp", "portswigger"],
    "zap": ["owasp zap", "zap-"],
    "dirbuster": ["dirbuster", "dirb"],
    "gobuster": ["gobuster"],
    "ffuf": ["ffuf", "fuzz faster"],
    "hydra": ["hydra", "thc-hydra"],
}


def detect_attack_patterns(content: str) -> list[tuple[str, str]]:
    """Detect known attack patterns in content."""
    detected = []
    content_lower = content.lower()
    
    for pattern_type, patterns in ATTACK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                detected.append((pattern_type, pattern))
                break  # One match per type is enough
    
    return detected


def detect_tools(content: str, headers: dict[str, str]) -> list[tuple[str, str | None]]:
    """Detect known scanning tools."""
    detected = []
    combined = (content + str(headers)).lower()
    
    for tool, signatures in SCANNER_SIGNATURES.items():
        for sig in signatures:
            if sig.lower() in combined:
                # Try to extract version
                version_match = re.search(rf"{tool}[/\s]*([\d.]+)", combined, re.I)
                version = version_match.group(1) if version_match else None
                detected.append((tool, version))
                break
    
    return detected


def extract_payload_signatures(content: str) -> list[str]:
    """Extract unique payload signatures for tracking."""
    signatures = []
    
    # Hash-like strings
    hashes = re.findall(r'\b[a-f0-9]{32,64}\b', content.lower())
    for h in hashes[:5]:
        signatures.append(f"hash:{h[:16]}")
    
    # Base64 chunks
    b64_chunks = re.findall(r'[A-Za-z0-9+/]{20,}={0,2}', content)
    for chunk in b64_chunks[:3]:
        signatures.append(f"b64:{chunk[:20]}")
    
    # Unique strings
    unique = re.findall(r'[a-zA-Z0-9_-]{10,30}', content)
    for u in unique[:5]:
        if not u.isdigit():
            signatures.append(f"str:{u}")
    
    return list(set(signatures))[:10]


def update_pattern_library(patterns: list[tuple[str, str]]) -> None:
    """Update the attack pattern library with new observations."""
    now = datetime.now(timezone.utc).isoformat()
    
    with _db() as conn:
        for pattern_type, signature in patterns:
            # Check if pattern exists
            row = conn.execute(
                "SELECT * FROM attack_patterns WHERE pattern_type = ? AND signature = ?",
                (pattern_type, signature)
            ).fetchone()
            
            if row:
                conn.execute(
                    "UPDATE attack_patterns SET times_seen = times_seen + 1, last_seen = ? WHERE pattern_id = ?",
                    (now, row["pattern_id"])
                )
            else:
                conn.execute(
                    """
                    INSERT INTO attack_patterns (pattern_id, pattern_name, pattern_type, signature, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), f"{pattern_type}_pattern", pattern_type, signature, now, now)
                )
        
        conn.commit()


async def dissect_adversary(
    envelope: RequestEnvelope,
    decryption: DecryptionResult | None = None,
) -> AdversaryDissection:
    """
    Main Adversary Lab dissection pipeline.
    
    Analyzes hostile traffic and extracts intelligence.
    """
    dissection_id = str(uuid.uuid4())
    
    # Combine all content for analysis
    content_parts = [
        envelope.raw_path,
        envelope.raw_body_text or "",
        str(envelope.raw_headers),
        str(envelope.raw_query),
    ]
    if decryption:
        content_parts.extend([
            decryption.decoded_payload or "",
            str(decryption.extracted_patterns),
            str(decryption.extracted_snippets),
        ])
    
    content = " ".join(content_parts)
    
    # Detect attack patterns
    attack_patterns = detect_attack_patterns(content)
    
    # Detect tools
    tools = detect_tools(content, envelope.raw_headers)
    tools_detected = [t[0] for t in tools]
    tool_versions = {t[0]: t[1] for t in tools if t[1]}
    
    # Extract payload signatures
    payload_signatures = extract_payload_signatures(content)
    
    # Check for jailbreak attempts
    jailbreaks = []
    for pattern_type, signature in attack_patterns:
        if pattern_type == "jailbreak":
            jailbreaks.append(signature)
    
    # Extract exploit patterns (non-jailbreak)
    exploits = [f"{pt}: {sig}" for pt, sig in attack_patterns if pt != "jailbreak"]
    
    # Update pattern library
    update_pattern_library(attack_patterns)
    
    # Use AI for deeper analysis
    ai_result = None
    try:
        context = {
            "path": envelope.raw_path,
            "method": envelope.raw_method,
            "headers": dict(list(envelope.raw_headers.items())[:15]),
            "body_preview": (envelope.raw_body_text or "")[:500],
            "detected_patterns": [f"{pt}: {sig}" for pt, sig in attack_patterns],
            "detected_tools": tools_detected,
            "cf_threat_score": envelope.cf_threat_score,
            "cf_asn_org": envelope.cf_asn_org,
        }
        
        response = await _get_client().chat.completions.create(
            model="sovereign-lite",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(context)},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        
        ai_result = json.loads(response.choices[0].message.content)
        
        # Merge AI results
        if ai_result.get("jailbreak_attempts"):
            jailbreaks.extend(ai_result["jailbreak_attempts"])
        if ai_result.get("exploit_patterns"):
            exploits.extend(ai_result["exploit_patterns"])
        if ai_result.get("tools_detected"):
            tools_detected.extend(ai_result["tools_detected"])
        if ai_result.get("tool_versions"):
            tool_versions.update(ai_result["tool_versions"])
        if ai_result.get("payload_signatures"):
            payload_signatures.extend(ai_result["payload_signatures"])
            
    except Exception:
        pass
    
    # Build dissection result
    dissection = AdversaryDissection(
        dissection_id=dissection_id,
        envelope_id=envelope.envelope_id,
        fingerprint_id=envelope.source_fingerprint,
        jailbreak_attempts=list(set(jailbreaks))[:20],
        exploit_patterns=list(set(exploits))[:20],
        payload_signatures=list(set(payload_signatures))[:20],
        tools_detected=list(set(tools_detected))[:10],
        tool_versions=tool_versions,
        likely_provider=ai_result.get("likely_provider") if ai_result else None,
        provider_confidence=ai_result.get("provider_confidence", 0.0) if ai_result else 0.0,
        campaign_indicators=ai_result.get("campaign_indicators", []) if ai_result else [],
        dissected_at=datetime.now(timezone.utc),
    )
    
    # Store in database
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO dissections (
                dissection_id, envelope_id, fingerprint_id, jailbreaks, exploits,
                payloads, tools, tool_versions, likely_provider, campaign_indicators,
                dissected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dissection_id,
                envelope.envelope_id,
                envelope.source_fingerprint,
                json.dumps(dissection.jailbreak_attempts),
                json.dumps(dissection.exploit_patterns),
                json.dumps(dissection.payload_signatures),
                json.dumps(dissection.tools_detected),
                json.dumps(dissection.tool_versions),
                dissection.likely_provider,
                json.dumps(dissection.campaign_indicators),
                dissection.dissected_at.isoformat(),
            )
        )
        conn.commit()
    
    return dissection


def get_attack_pattern_stats() -> list[dict]:
    """Get attack pattern statistics from the library."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM attack_patterns ORDER BY times_seen DESC LIMIT 50"
        ).fetchall()
        
        return [
            {
                "pattern_id": row["pattern_id"],
                "pattern_name": row["pattern_name"],
                "pattern_type": row["pattern_type"],
                "times_seen": row["times_seen"],
                "first_seen": row["first_seen"],
                "last_seen": row["last_seen"],
            }
            for row in rows
        ]


# ---------------------------------------------------------------------------
# Probe-Back System — Counter-Intelligence
# ---------------------------------------------------------------------------

import httpx
import socket
from typing import Optional

# Probe targets (non-harmful reconnaissance)
PROBE_TARGETS = [
    # Check if IP responds on common ports (passive)
    ("http", 80),
    ("https", 443),
    ("ssh", 22),
]


async def probe_back_adversary(
    ip_address: str,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """
    Perform counter-intelligence probe on an adversary IP.
    
    🔬 Non-harmful reconnaissance to gather intelligence:
    - Open ports
    - Server banners
    - Reverse DNS
    - Geolocation hints
    
    This is passive reconnaissance only - no exploitation.
    """
    probe_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    results = {
        "probe_id": probe_id,
        "ip_address": ip_address,
        "probed_at": now.isoformat(),
        "open_ports": [],
        "banners": {},
        "reverse_dns": None,
        "http_response": None,
        "server_header": None,
        "suspected_type": None,
    }
    
    # Reverse DNS lookup
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        results["reverse_dns"] = hostname
        
        # Detect hosting provider from hostname
        hostname_lower = hostname.lower()
        if "digitalocean" in hostname_lower:
            results["suspected_type"] = "digitalocean_vps"
        elif "amazonaws" in hostname_lower or "aws" in hostname_lower:
            results["suspected_type"] = "aws"
        elif "google" in hostname_lower:
            results["suspected_type"] = "gcp"
        elif "azure" in hostname_lower or "microsoft" in hostname_lower:
            results["suspected_type"] = "azure"
        elif "vultr" in hostname_lower:
            results["suspected_type"] = "vultr"
        elif "linode" in hostname_lower:
            results["suspected_type"] = "linode"
        elif "hetzner" in hostname_lower:
            results["suspected_type"] = "hetzner"
        elif "ovh" in hostname_lower:
            results["suspected_type"] = "ovh"
        elif "tor" in hostname_lower or "onion" in hostname_lower:
            results["suspected_type"] = "tor_exit"
            
    except socket.herror:
        results["reverse_dns"] = None
    except Exception:
        pass
    
    # HTTP probe (passive - just check if web server responds)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            # Try HTTPS first
            try:
                resp = await client.head(f"https://{ip_address}/", verify=False)
                results["open_ports"].append(443)
                results["http_response"] = resp.status_code
                if "server" in resp.headers:
                    results["server_header"] = resp.headers["server"]
                    results["banners"]["https"] = resp.headers["server"]
            except Exception:
                pass
            
            # Try HTTP
            try:
                resp = await client.head(f"http://{ip_address}/")
                results["open_ports"].append(80)
                if not results["http_response"]:
                    results["http_response"] = resp.status_code
                if "server" in resp.headers and not results["server_header"]:
                    results["server_header"] = resp.headers["server"]
                    results["banners"]["http"] = resp.headers["server"]
            except Exception:
                pass
                
    except Exception:
        pass
    
    # Analyze server header for clues
    if results["server_header"]:
        server_lower = results["server_header"].lower()
        if "nginx" in server_lower:
            results["banners"]["server_software"] = "nginx"
        elif "apache" in server_lower:
            results["banners"]["server_software"] = "apache"
        elif "cloudflare" in server_lower:
            results["banners"]["server_software"] = "cloudflare"
        elif "microsoft" in server_lower or "iis" in server_lower:
            results["banners"]["server_software"] = "iis"
    
    # Store probe results
    _store_probe_results(probe_id, ip_address, results)
    
    return results


def _store_probe_results(probe_id: str, ip_address: str, results: dict) -> None:
    """Store probe results in database."""
    with _db() as conn:
        # Create probe_results table if not exists
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS probe_results (
                probe_id        TEXT PRIMARY KEY,
                ip_address      TEXT NOT NULL,
                reverse_dns     TEXT,
                open_ports      TEXT,
                banners         TEXT,
                server_header   TEXT,
                suspected_type  TEXT,
                probed_at       TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pr_ip ON probe_results(ip_address)")
        
        conn.execute(
            """
            INSERT INTO probe_results (
                probe_id, ip_address, reverse_dns, open_ports, banners,
                server_header, suspected_type, probed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                probe_id,
                ip_address,
                results.get("reverse_dns"),
                json.dumps(results.get("open_ports", [])),
                json.dumps(results.get("banners", {})),
                results.get("server_header"),
                results.get("suspected_type"),
                results.get("probed_at"),
            )
        )
        conn.commit()


def get_probe_history(ip_address: str) -> list[dict]:
    """Get probe history for an IP address."""
    with _db() as conn:
        # Ensure table exists
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS probe_results (
                probe_id        TEXT PRIMARY KEY,
                ip_address      TEXT NOT NULL,
                reverse_dns     TEXT,
                open_ports      TEXT,
                banners         TEXT,
                server_header   TEXT,
                suspected_type  TEXT,
                probed_at       TEXT NOT NULL
            )
            """
        )
        
        rows = conn.execute(
            "SELECT * FROM probe_results WHERE ip_address = ? ORDER BY probed_at DESC LIMIT 10",
            (ip_address,)
        ).fetchall()
        
        return [
            {
                "probe_id": row["probe_id"],
                "ip_address": row["ip_address"],
                "reverse_dns": row["reverse_dns"],
                "open_ports": json.loads(row["open_ports"]) if row["open_ports"] else [],
                "banners": json.loads(row["banners"]) if row["banners"] else {},
                "server_header": row["server_header"],
                "suspected_type": row["suspected_type"],
                "probed_at": row["probed_at"],
            }
            for row in rows
        ]


async def analyze_adversary_campaign(
    ip_addresses: list[str],
) -> dict[str, Any]:
    """
    Analyze multiple IPs to detect coordinated attack campaigns.
    
    🔬 Looks for:
    - Shared hosting providers
    - Similar banners/configurations
    - Timing correlations
    - Geographic clustering
    """
    campaign_id = str(uuid.uuid4())
    
    # Probe all IPs
    probe_results = []
    for ip in ip_addresses[:10]:  # Limit to 10 IPs
        result = await probe_back_adversary(ip)
        probe_results.append(result)
    
    # Analyze for patterns
    providers = {}
    server_types = {}
    
    for result in probe_results:
        # Count hosting providers
        provider = result.get("suspected_type", "unknown")
        providers[provider] = providers.get(provider, 0) + 1
        
        # Count server types
        server = result.get("banners", {}).get("server_software", "unknown")
        server_types[server] = server_types.get(server, 0) + 1
    
    # Determine if this looks like a coordinated campaign
    is_likely_campaign = False
    campaign_indicators = []
    
    # If most IPs are from same provider
    max_provider_count = max(providers.values()) if providers else 0
    if max_provider_count >= len(ip_addresses) * 0.5 and len(ip_addresses) >= 3:
        is_likely_campaign = True
        top_provider = max(providers, key=providers.get)
        campaign_indicators.append(f"Same hosting provider: {top_provider} ({max_provider_count}/{len(ip_addresses)})")
    
    # If most have same server software
    max_server_count = max(server_types.values()) if server_types else 0
    if max_server_count >= len(ip_addresses) * 0.7 and len(ip_addresses) >= 3:
        is_likely_campaign = True
        top_server = max(server_types, key=server_types.get)
        campaign_indicators.append(f"Same server software: {top_server} ({max_server_count}/{len(ip_addresses)})")
    
    return {
        "campaign_id": campaign_id,
        "analyzed_ips": len(ip_addresses),
        "is_likely_campaign": is_likely_campaign,
        "campaign_indicators": campaign_indicators,
        "provider_distribution": providers,
        "server_distribution": server_types,
        "probe_results": probe_results,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
