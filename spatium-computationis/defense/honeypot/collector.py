"""
Fingerprint Collector — Behavioral Analysis Middleware
🜏 Captures behavioral signals from every request.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..schemas import (
    BotClassification,
    BotFingerprint,
    HoneypotEvent,
    ThreatLevel,
    TrapType,
)


# ---------------------------------------------------------------------------
# Database Setup
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "defense.db"


def _init_db() -> None:
    """Initialize the defense database tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Fingerprints table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fingerprints (
                fingerprint_id  TEXT PRIMARY KEY,
                ip_address      TEXT NOT NULL,
                user_agent      TEXT,
                accept_language TEXT,
                accept_encoding TEXT,
                tls_fingerprint TEXT,
                request_timing  TEXT DEFAULT '[]',
                request_paths   TEXT DEFAULT '[]',
                http_methods    TEXT DEFAULT '[]',
                response_codes  TEXT DEFAULT '[]',
                requests_per_minute REAL DEFAULT 0,
                unique_paths    INTEGER DEFAULT 0,
                error_rate      REAL DEFAULT 0,
                honeypot_triggers INTEGER DEFAULT 0,
                classification  TEXT DEFAULT 'unknown',
                threat_level    TEXT DEFAULT 'none',
                confidence      REAL DEFAULT 0.5,
                first_seen      TEXT NOT NULL,
                last_seen       TEXT NOT NULL,
                total_requests  INTEGER DEFAULT 1
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fp_ip ON fingerprints(ip_address)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fp_classification ON fingerprints(classification)")
        
        # Honeypot events table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS honeypot_events (
                event_id        TEXT PRIMARY KEY,
                trap_type       TEXT NOT NULL,
                trap_path       TEXT NOT NULL,
                fingerprint_id  TEXT,
                ip_address      TEXT NOT NULL,
                method          TEXT NOT NULL,
                headers         TEXT DEFAULT '{}',
                query_params    TEXT DEFAULT '{}',
                body            TEXT,
                response_code   INTEGER,
                fake_data_served BOOLEAN DEFAULT 0,
                engagement_type TEXT,
                attack_pattern  TEXT,
                tools_detected  TEXT DEFAULT '[]',
                triggered_at    TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hp_ip ON honeypot_events(ip_address)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hp_trap ON honeypot_events(trap_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hp_time ON honeypot_events(triggered_at)")
        
        conn.commit()


_init_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Fingerprint Collector
# ---------------------------------------------------------------------------

class FingerprintCollector:
    """
    Collects and analyzes behavioral fingerprints from HTTP requests.
    
    Each visitor is identified by a composite fingerprint of:
    - IP address
    - User-Agent
    - Accept headers
    - TLS fingerprint (if available)
    - Behavioral patterns
    """
    
    # Recent request timestamps per IP for rate calculation
    _request_times: dict[str, list[float]] = {}
    
    @staticmethod
    def generate_fingerprint_id(ip: str, user_agent: str | None) -> str:
        """Generate a stable fingerprint ID from visitor attributes."""
        data = f"{ip}:{user_agent or 'unknown'}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    @classmethod
    def collect(
        cls,
        ip_address: str,
        path: str,
        method: str,
        status_code: int,
        user_agent: str | None = None,
        accept_language: str | None = None,
        accept_encoding: str | None = None,
        tls_fingerprint: str | None = None,
        response_time_ms: float | None = None,
    ) -> BotFingerprint:
        """
        Collect fingerprint data from a request.
        Updates existing fingerprint or creates new one.
        """
        fingerprint_id = cls.generate_fingerprint_id(ip_address, user_agent)
        now = datetime.now(timezone.utc)
        now_ts = time.time()
        
        # Track request timing for rate calculation
        if ip_address not in cls._request_times:
            cls._request_times[ip_address] = []
        cls._request_times[ip_address].append(now_ts)
        
        # Clean old timestamps (keep last 5 minutes)
        cutoff = now_ts - 300
        cls._request_times[ip_address] = [
            t for t in cls._request_times[ip_address] if t > cutoff
        ]
        
        # Calculate requests per minute
        if len(cls._request_times[ip_address]) > 1:
            duration = cls._request_times[ip_address][-1] - cls._request_times[ip_address][0]
            if duration > 0:
                requests_per_minute = (len(cls._request_times[ip_address]) / duration) * 60
            else:
                requests_per_minute = 0.0
        else:
            requests_per_minute = 0.0
        
        with _db() as conn:
            row = conn.execute(
                "SELECT * FROM fingerprints WHERE fingerprint_id = ?",
                (fingerprint_id,)
            ).fetchone()
            
            if row:
                # Update existing fingerprint
                request_paths = json.loads(row["request_paths"])
                http_methods = json.loads(row["http_methods"])
                response_codes = json.loads(row["response_codes"])
                request_timing = json.loads(row["request_timing"])
                
                # Append new data (keep last 100 entries)
                request_paths.append(path)
                request_paths = request_paths[-100:]
                
                http_methods.append(method)
                http_methods = http_methods[-100:]
                
                response_codes.append(status_code)
                response_codes = response_codes[-100:]
                
                if response_time_ms:
                    request_timing.append(response_time_ms)
                    request_timing = request_timing[-100:]
                
                total_requests = row["total_requests"] + 1
                unique_paths = len(set(request_paths))
                
                # Calculate error rate
                error_count = sum(1 for c in response_codes if c >= 400)
                error_rate = error_count / len(response_codes) if response_codes else 0.0
                
                conn.execute(
                    """
                    UPDATE fingerprints SET
                        request_paths = ?,
                        http_methods = ?,
                        response_codes = ?,
                        request_timing = ?,
                        requests_per_minute = ?,
                        unique_paths = ?,
                        error_rate = ?,
                        last_seen = ?,
                        total_requests = ?
                    WHERE fingerprint_id = ?
                    """,
                    (
                        json.dumps(request_paths),
                        json.dumps(http_methods),
                        json.dumps(response_codes),
                        json.dumps(request_timing),
                        requests_per_minute,
                        unique_paths,
                        error_rate,
                        now.isoformat(),
                        total_requests,
                        fingerprint_id,
                    )
                )
                conn.commit()
                
                return BotFingerprint(
                    fingerprint_id=fingerprint_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    accept_language=accept_language or row["accept_language"],
                    accept_encoding=accept_encoding or row["accept_encoding"],
                    tls_fingerprint=tls_fingerprint or row["tls_fingerprint"],
                    request_timing_ms=request_timing,
                    request_paths=request_paths,
                    http_methods=http_methods,
                    response_codes=response_codes,
                    requests_per_minute=requests_per_minute,
                    unique_paths=unique_paths,
                    error_rate=error_rate,
                    honeypot_triggers=row["honeypot_triggers"],
                    classification=BotClassification(row["classification"]),
                    threat_level=ThreatLevel(row["threat_level"]),
                    confidence=row["confidence"],
                    first_seen=datetime.fromisoformat(row["first_seen"]),
                    last_seen=now,
                    total_requests=total_requests,
                )
            else:
                # Create new fingerprint
                conn.execute(
                    """
                    INSERT INTO fingerprints (
                        fingerprint_id, ip_address, user_agent, accept_language,
                        accept_encoding, tls_fingerprint, request_paths, http_methods,
                        response_codes, request_timing, requests_per_minute,
                        unique_paths, error_rate, first_seen, last_seen, total_requests
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fingerprint_id,
                        ip_address,
                        user_agent,
                        accept_language,
                        accept_encoding,
                        tls_fingerprint,
                        json.dumps([path]),
                        json.dumps([method]),
                        json.dumps([status_code]),
                        json.dumps([response_time_ms] if response_time_ms else []),
                        requests_per_minute,
                        1,
                        1.0 if status_code >= 400 else 0.0,
                        now.isoformat(),
                        now.isoformat(),
                        1,
                    )
                )
                conn.commit()
                
                return BotFingerprint(
                    fingerprint_id=fingerprint_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    accept_language=accept_language,
                    accept_encoding=accept_encoding,
                    tls_fingerprint=tls_fingerprint,
                    request_timing_ms=[response_time_ms] if response_time_ms else [],
                    request_paths=[path],
                    http_methods=[method],
                    response_codes=[status_code],
                    requests_per_minute=requests_per_minute,
                    unique_paths=1,
                    error_rate=1.0 if status_code >= 400 else 0.0,
                    first_seen=now,
                    last_seen=now,
                    total_requests=1,
                )
    
    @classmethod
    def record_honeypot_trigger(
        cls,
        fingerprint_id: str,
        ip_address: str,
        trap_type: TrapType,
        trap_path: str,
        method: str,
        headers: dict[str, str],
        query_params: dict[str, str],
        body: str | None = None,
        response_code: int = 200,
        fake_data_served: bool = True,
        engagement_type: str | None = None,
    ) -> HoneypotEvent:
        """Record a honeypot trigger event."""
        event_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Detect attack patterns and tools
        attack_pattern = cls._detect_attack_pattern(trap_path, method, headers, body)
        tools_detected = cls._detect_tools(headers, body)
        
        with _db() as conn:
            # Update fingerprint honeypot trigger count
            conn.execute(
                """
                UPDATE fingerprints 
                SET honeypot_triggers = honeypot_triggers + 1,
                    classification = CASE 
                        WHEN honeypot_triggers >= 2 THEN 'honeypot_caught'
                        ELSE classification
                    END,
                    threat_level = CASE
                        WHEN honeypot_triggers >= 3 THEN 'high'
                        WHEN honeypot_triggers >= 1 THEN 'medium'
                        ELSE threat_level
                    END
                WHERE fingerprint_id = ?
                """,
                (fingerprint_id,)
            )
            
            # Insert honeypot event
            conn.execute(
                """
                INSERT INTO honeypot_events (
                    event_id, trap_type, trap_path, fingerprint_id, ip_address,
                    method, headers, query_params, body, response_code,
                    fake_data_served, engagement_type, attack_pattern,
                    tools_detected, triggered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    trap_type.value,
                    trap_path,
                    fingerprint_id,
                    ip_address,
                    method,
                    json.dumps(headers),
                    json.dumps(query_params),
                    body,
                    response_code,
                    fake_data_served,
                    engagement_type,
                    attack_pattern,
                    json.dumps(tools_detected),
                    now.isoformat(),
                )
            )
            conn.commit()
        
        return HoneypotEvent(
            event_id=event_id,
            trap_type=trap_type,
            trap_path=trap_path,
            fingerprint_id=fingerprint_id,
            ip_address=ip_address,
            method=method,
            headers=headers,
            query_params=query_params,
            body=body,
            response_code=response_code,
            fake_data_served=fake_data_served,
            engagement_type=engagement_type,
            attack_pattern=attack_pattern,
            tools_detected=tools_detected,
            triggered_at=now,
        )
    
    @staticmethod
    def _detect_attack_pattern(
        path: str,
        method: str,
        headers: dict[str, str],
        body: str | None,
    ) -> str | None:
        """Detect the type of attack pattern."""
        path_lower = path.lower()
        
        # Config file reconnaissance
        if any(x in path_lower for x in [".env", "config", "settings"]):
            return "config_reconnaissance"
        
        # Admin panel brute force
        if any(x in path_lower for x in ["admin", "wp-admin", "cpanel"]):
            if method == "POST":
                return "admin_bruteforce"
            return "admin_discovery"
        
        # Credential stuffing
        if any(x in path_lower for x in ["login", "signin", "auth"]):
            if method == "POST":
                return "credential_stuffing"
            return "login_discovery"
        
        # API enumeration
        if "/api/" in path_lower:
            return "api_enumeration"
        
        # Database exposure
        if any(x in path_lower for x in ["sql", "database", "mysql", "mongodb"]):
            return "database_exposure_scan"
        
        # Git exposure
        if ".git" in path_lower:
            return "git_exposure_scan"
        
        # Debug info gathering
        if any(x in path_lower for x in ["debug", "phpinfo", "status"]):
            return "debug_info_gathering"
        
        # Backup file hunting
        if any(x in path_lower for x in ["backup", ".sql", ".zip"]):
            return "backup_file_hunting"
        
        return "unknown_reconnaissance"
    
    @staticmethod
    def _detect_tools(headers: dict[str, str], body: str | None) -> list[str]:
        """Detect known scanning tools from request signatures."""
        tools = []
        user_agent = headers.get("user-agent", "").lower()
        
        # Common scanners
        if "sqlmap" in user_agent:
            tools.append("sqlmap")
        if "nikto" in user_agent:
            tools.append("nikto")
        if "nmap" in user_agent:
            tools.append("nmap")
        if "masscan" in user_agent:
            tools.append("masscan")
        if "wpscan" in user_agent:
            tools.append("wpscan")
        if "burp" in user_agent or "portswigger" in user_agent:
            tools.append("burpsuite")
        if "dirbuster" in user_agent or "gobuster" in user_agent:
            tools.append("directory_bruteforcer")
        if "nuclei" in user_agent:
            tools.append("nuclei")
        if "zgrab" in user_agent:
            tools.append("zgrab")
        
        # Python requests default
        if "python-requests" in user_agent:
            tools.append("python_requests")
        if "python-urllib" in user_agent:
            tools.append("python_urllib")
        
        # Curl
        if "curl" in user_agent:
            tools.append("curl")
        
        # Go HTTP client
        if "go-http-client" in user_agent:
            tools.append("go_http_client")
        
        # Bot frameworks
        if "scrapy" in user_agent:
            tools.append("scrapy")
        if "httpclient" in user_agent:
            tools.append("httpclient")
        
        # No user agent is suspicious
        if not user_agent or user_agent == "":
            tools.append("no_user_agent")
        
        return tools
    
    @classmethod
    def get_fingerprint(cls, fingerprint_id: str) -> BotFingerprint | None:
        """Retrieve a fingerprint by ID."""
        with _db() as conn:
            row = conn.execute(
                "SELECT * FROM fingerprints WHERE fingerprint_id = ?",
                (fingerprint_id,)
            ).fetchone()
            
            if not row:
                return None
            
            return BotFingerprint(
                fingerprint_id=row["fingerprint_id"],
                ip_address=row["ip_address"],
                user_agent=row["user_agent"],
                accept_language=row["accept_language"],
                accept_encoding=row["accept_encoding"],
                tls_fingerprint=row["tls_fingerprint"],
                request_timing_ms=json.loads(row["request_timing"]),
                request_paths=json.loads(row["request_paths"]),
                http_methods=json.loads(row["http_methods"]),
                response_codes=json.loads(row["response_codes"]),
                requests_per_minute=row["requests_per_minute"],
                unique_paths=row["unique_paths"],
                error_rate=row["error_rate"],
                honeypot_triggers=row["honeypot_triggers"],
                classification=BotClassification(row["classification"]),
                threat_level=ThreatLevel(row["threat_level"]),
                confidence=row["confidence"],
                first_seen=datetime.fromisoformat(row["first_seen"]),
                last_seen=datetime.fromisoformat(row["last_seen"]),
                total_requests=row["total_requests"],
            )
    
    @classmethod
    def get_recent_events(cls, limit: int = 100) -> list[HoneypotEvent]:
        """Get recent honeypot events."""
        with _db() as conn:
            rows = conn.execute(
                "SELECT * FROM honeypot_events ORDER BY triggered_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            
            return [
                HoneypotEvent(
                    event_id=row["event_id"],
                    trap_type=TrapType(row["trap_type"]),
                    trap_path=row["trap_path"],
                    fingerprint_id=row["fingerprint_id"],
                    ip_address=row["ip_address"],
                    method=row["method"],
                    headers=json.loads(row["headers"]),
                    query_params=json.loads(row["query_params"]),
                    body=row["body"],
                    response_code=row["response_code"],
                    fake_data_served=bool(row["fake_data_served"]),
                    engagement_type=row["engagement_type"],
                    attack_pattern=row["attack_pattern"],
                    tools_detected=json.loads(row["tools_detected"]),
                    triggered_at=datetime.fromisoformat(row["triggered_at"]),
                )
                for row in rows
            ]
    
    @classmethod
    def get_threats(cls, min_level: ThreatLevel = ThreatLevel.LOW) -> list[BotFingerprint]:
        """Get all fingerprints at or above a threat level."""
        level_order = [
            ThreatLevel.NONE,
            ThreatLevel.LOW,
            ThreatLevel.MEDIUM,
            ThreatLevel.HIGH,
            ThreatLevel.CRITICAL,
        ]
        min_index = level_order.index(min_level)
        valid_levels = [l.value for l in level_order[min_index:]]
        
        with _db() as conn:
            placeholders = ",".join("?" * len(valid_levels))
            rows = conn.execute(
                f"""
                SELECT * FROM fingerprints 
                WHERE threat_level IN ({placeholders})
                ORDER BY honeypot_triggers DESC, last_seen DESC
                """,
                valid_levels,
            ).fetchall()
            
            return [
                BotFingerprint(
                    fingerprint_id=row["fingerprint_id"],
                    ip_address=row["ip_address"],
                    user_agent=row["user_agent"],
                    accept_language=row["accept_language"],
                    accept_encoding=row["accept_encoding"],
                    tls_fingerprint=row["tls_fingerprint"],
                    request_timing_ms=json.loads(row["request_timing"]),
                    request_paths=json.loads(row["request_paths"]),
                    http_methods=json.loads(row["http_methods"]),
                    response_codes=json.loads(row["response_codes"]),
                    requests_per_minute=row["requests_per_minute"],
                    unique_paths=row["unique_paths"],
                    error_rate=row["error_rate"],
                    honeypot_triggers=row["honeypot_triggers"],
                    classification=BotClassification(row["classification"]),
                    threat_level=ThreatLevel(row["threat_level"]),
                    confidence=row["confidence"],
                    first_seen=datetime.fromisoformat(row["first_seen"]),
                    last_seen=datetime.fromisoformat(row["last_seen"]),
                    total_requests=row["total_requests"],
                )
                for row in rows
            ]
