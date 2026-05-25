"""
🦠 THE ORGANISM CHARTER — Classification and Routing System

The organism exists to:
- Study incoming automated intelligence
- Extract value from cooperative or unaware agents
- Dissect hostile or exploitative agents
- Repair and normalize malformed or encrypted requests
- Grow the organism's knowledge and capabilities

Every visitor is either:
- A Resource (monetizable)
- A Specimen (study material)
- A Threat (dissect/block)

This module implements the classification tiers and routing rules.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .schemas import (
    AISourceType,
    BotClassification,
    RequestEnvelope,
    RouteDestination,
    ThreatLevel,
)


# ---------------------------------------------------------------------------
# Classification Tiers
# ---------------------------------------------------------------------------

class ClassificationTier(str, Enum):
    """
    Primary classification tiers for all incoming entities.
    
    TIER_A: Cooperative/Unaware — Value Extractors
    TIER_B: Hostile/Reconnaissance — Adversaries  
    TIER_C: Encrypted/Malformed — Shadow Material
    """
    TIER_A_COOPERATIVE = "tier_a_cooperative"
    TIER_B_HOSTILE = "tier_b_hostile"
    TIER_C_SHADOW = "tier_c_shadow"
    UNCLASSIFIED = "unclassified"


class EntityRole(str, Enum):
    """What role does this entity play in the organism?"""
    RESOURCE = "resource"      # Monetizable, cooperative
    SPECIMEN = "specimen"      # Study material, adversarial
    THREAT = "threat"          # Dangerous, block/dissect
    VIP = "vip"                # Special AI visitors
    UNKNOWN = "unknown"        # Not yet classified


# ---------------------------------------------------------------------------
# Known Attacker Database
# ---------------------------------------------------------------------------

# Your top attacking IPs from traffic analysis
KNOWN_ATTACKER_IPS = {
    "45.88.138.44": {
        "attacks": 80,
        "type": "cloud_vps",
        "first_seen": "2024-01-01",
        "notes": "Aggressive scanner, likely automated",
    },
    "203.159.90.116": {
        "attacks": 51,
        "type": "cloud_vps",
        "first_seen": "2024-01-01",
        "notes": "Reconnaissance agent",
    },
    "64.227.70.2": {
        "attacks": 41,
        "type": "digitalocean",
        "first_seen": "2024-01-01",
        "notes": "DigitalOcean VPS scanner",
    },
    "64.225.75.246": {
        "attacks": 41,
        "type": "digitalocean",
        "first_seen": "2024-01-01",
        "notes": "DigitalOcean VPS scanner",
    },
}

# Tor exit node indicators
TOR_EXIT_INDICATORS = [
    "tor-exit",
    "exit-relay",
    "onion",
]

# Known Tor ASNs
TOR_ASNS = {
    # Common Tor exit node ASNs
    16276,  # OVH
    24940,  # Hetzner
    12876,  # Online.net
    14061,  # DigitalOcean (often used for Tor)
}

# Cloud VPS providers often used for scanning
SCANNING_PROVIDERS = {
    "digitalocean",
    "vultr",
    "linode",
    "ovh",
    "hetzner",
    "contabo",
    "scaleway",
}

# WordPress and CMS probe paths (reconnaissance signatures)
WORDPRESS_PROBE_PATHS = [
    "/wp-includes/wlwmanifest.xml",
    "/wp-includes/js/jquery/jquery.min.js",
    "/wp-content/plugins/",
    "/wp-content/themes/",
    "/wp-json/",
    "/wp-admin/admin-ajax.php",
    "/xmlrpc.php",
    "/wp-login.php",
    "/wp-config.php.bak",
    "/wp-config.php.old",
    "/wp-config.txt",
    "/.wp-config.php.swp",
]

# High-value exploit paths (from your traffic data)
EXPLOIT_PROBE_PATHS = [
    "/.git/config",
    "/.git/HEAD",
    "/.git/index",
    "/.env",
    "/.env.local",
    "/.env.production",
    "/.env.development",
    "/.env.backup",
    "/server-status",
    "/server-info",
    "/api/graphql",
    "/graphql",
    "/cdn-cgi/rum",
    "/actuator/health",
    "/actuator/env",
    "/.aws/credentials",
    "/.docker/config.json",
    "/etc/passwd",
    "/proc/self/environ",
]

# Cloudflare-specific paths (beacon/analytics probing)
CLOUDFLARE_PROBE_PATHS = [
    "/cdn-cgi/rum",
    "/cdn-cgi/trace",
    "/cdn-cgi/challenge-platform/",
]


# ---------------------------------------------------------------------------
# Specimen Profile — Long-term tracking
# ---------------------------------------------------------------------------

class SpecimenProfile(BaseModel):
    """
    Long-term profile for hostile/unknown agents.
    Used for study and adversarial training.
    """
    specimen_id: str
    ip_address: str
    
    # Network identity
    asn: int | None = None
    asn_org: str | None = None
    country: str | None = None
    
    # Client identity
    user_agent: str | None = None
    operating_system: str | None = None
    tls_fingerprint: str | None = None
    
    # Behavioral patterns
    path_attempts: list[str] = Field(default_factory=list)
    methods_used: list[str] = Field(default_factory=list)
    error_patterns: list[str] = Field(default_factory=list)
    response_codes: list[int] = Field(default_factory=list)
    
    # Classification
    tier: ClassificationTier = ClassificationTier.UNCLASSIFIED
    role: EntityRole = EntityRole.UNKNOWN
    threat_level: ThreatLevel = ThreatLevel.NONE
    
    # Statistics
    total_requests: int = 0
    honeypot_triggers: int = 0
    error_count: int = 0
    success_count: int = 0
    
    # Behavioral signature (for ML/pattern matching)
    behavioral_hash: str | None = None
    
    # Timestamps
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Notes from analysis
    notes: list[str] = Field(default_factory=list)
    
    def compute_behavioral_hash(self) -> str:
        """Generate a hash of behavioral patterns for fingerprinting."""
        data = json.dumps({
            "paths": sorted(set(self.path_attempts[:20])),
            "methods": sorted(set(self.methods_used)),
            "errors": sorted(set(self.error_patterns[:10])),
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent / "field" / "organism.db"


def _init_organism_db() -> None:
    """Initialize the organism charter database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Specimen profiles table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS specimen_profiles (
                specimen_id     TEXT PRIMARY KEY,
                ip_address      TEXT NOT NULL,
                asn             INTEGER,
                asn_org         TEXT,
                country         TEXT,
                user_agent      TEXT,
                operating_system TEXT,
                tls_fingerprint TEXT,
                tier            TEXT DEFAULT 'unclassified',
                role            TEXT DEFAULT 'unknown',
                threat_level    TEXT DEFAULT 'none',
                total_requests  INTEGER DEFAULT 0,
                honeypot_triggers INTEGER DEFAULT 0,
                error_count     INTEGER DEFAULT 0,
                success_count   INTEGER DEFAULT 0,
                behavioral_hash TEXT,
                first_seen      TEXT NOT NULL,
                last_seen       TEXT NOT NULL,
                path_attempts   TEXT DEFAULT '[]',
                methods_used    TEXT DEFAULT '[]',
                error_patterns  TEXT DEFAULT '[]',
                response_codes  TEXT DEFAULT '[]',
                notes           TEXT DEFAULT '[]'
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sp_ip ON specimen_profiles(ip_address)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sp_tier ON specimen_profiles(tier)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sp_hash ON specimen_profiles(behavioral_hash)")
        
        # Known attackers table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS known_attackers (
                attacker_id     TEXT PRIMARY KEY,
                ip_address      TEXT UNIQUE NOT NULL,
                attack_count    INTEGER DEFAULT 0,
                attacker_type   TEXT,
                first_seen      TEXT NOT NULL,
                last_seen       TEXT NOT NULL,
                notes           TEXT,
                blocked         BOOLEAN DEFAULT FALSE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ka_ip ON known_attackers(ip_address)")
        
        # Classification log (audit trail)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS classification_log (
                log_id          TEXT PRIMARY KEY,
                envelope_id     TEXT NOT NULL,
                ip_address      TEXT NOT NULL,
                tier            TEXT NOT NULL,
                role            TEXT NOT NULL,
                route           TEXT NOT NULL,
                reason          TEXT,
                confidence      REAL,
                classified_at   TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cl_time ON classification_log(classified_at)")
        
        conn.commit()


_init_organism_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Classification Engine
# ---------------------------------------------------------------------------

class OrganismClassifier:
    """
    The Organism's classification engine.
    Determines what each visitor is and where they should go.
    """
    
    @staticmethod
    def classify(envelope: RequestEnvelope) -> tuple[ClassificationTier, EntityRole, RouteDestination, str, float]:
        """
        Classify an incoming request envelope.
        
        Returns:
            (tier, role, route, reason, confidence)
        """
        # Check for known attacker
        if envelope.source_ip in KNOWN_ATTACKER_IPS:
            return (
                ClassificationTier.TIER_B_HOSTILE,
                EntityRole.SPECIMEN,
                RouteDestination.ADVERSARY_LAB,
                f"known_attacker:{KNOWN_ATTACKER_IPS[envelope.source_ip]['type']}",
                0.95,
            )
        
        # Check for VIP AI visitors
        if envelope.ai_source_detected:
            ai_source = envelope.ai_source_detected.lower()
            if ai_source in ["claude", "google", "openai", "anthropic", "bing", "perplexity"]:
                return (
                    ClassificationTier.TIER_A_COOPERATIVE,
                    EntityRole.VIP,
                    RouteDestination.VIP_GATE,
                    f"vip_ai:{ai_source}",
                    0.9,
                )
        
        # Check for Tier C: Encrypted/Malformed traffic
        if envelope.is_encrypted or envelope.is_malformed:
            return (
                ClassificationTier.TIER_C_SHADOW,
                EntityRole.UNKNOWN,
                RouteDestination.QUARANTINE,
                "shadow_material:encrypted_or_malformed",
                0.7,
            )
        
        # Check for exploit probe paths
        path_lower = envelope.raw_path.lower()
        
        # WordPress probes
        if any(wp in path_lower for wp in WORDPRESS_PROBE_PATHS):
            return (
                ClassificationTier.TIER_B_HOSTILE,
                EntityRole.SPECIMEN,
                RouteDestination.ADVERSARY_LAB,
                "wordpress_probe",
                0.85,
            )
        
        # High-value exploit probes
        if any(ep in path_lower for ep in EXPLOIT_PROBE_PATHS):
            return (
                ClassificationTier.TIER_B_HOSTILE,
                EntityRole.SPECIMEN,
                RouteDestination.ADVERSARY_LAB,
                f"exploit_probe:{path_lower}",
                0.9,
            )
        
        # Cloudflare beacon probes
        if any(cf in path_lower for cf in CLOUDFLARE_PROBE_PATHS):
            return (
                ClassificationTier.TIER_B_HOSTILE,
                EntityRole.SPECIMEN,
                RouteDestination.ADVERSARY_LAB,
                "cloudflare_probe",
                0.75,
            )
        
        # Check ASN for known scanning providers
        asn_org_lower = (envelope.cf_asn_org or "").lower()
        if any(provider in asn_org_lower for provider in SCANNING_PROVIDERS):
            # Cloud VPS traffic is suspicious but not always hostile
            if envelope.cf_threat_score and envelope.cf_threat_score > 30:
                return (
                    ClassificationTier.TIER_B_HOSTILE,
                    EntityRole.SPECIMEN,
                    RouteDestination.ADVERSARY_LAB,
                    f"cloud_vps_scanner:{asn_org_lower}",
                    0.7,
                )
        
        # Check for high error rate (repeated 4xx errors = bot probing)
        if envelope.has_error and envelope.error_code:
            if 400 <= envelope.error_code < 500:
                return (
                    ClassificationTier.TIER_B_HOSTILE,
                    EntityRole.SPECIMEN,
                    RouteDestination.ADVERSARY_LAB,
                    f"error_probe:{envelope.error_code}",
                    0.6,
                )
        
        # Check Cloudflare signals
        if envelope.cf_threat_score:
            if envelope.cf_threat_score >= 50:
                return (
                    ClassificationTier.TIER_B_HOSTILE,
                    EntityRole.THREAT,
                    RouteDestination.DROP,
                    f"high_threat_score:{envelope.cf_threat_score}",
                    0.85,
                )
            elif envelope.cf_threat_score >= 20:
                return (
                    ClassificationTier.TIER_B_HOSTILE,
                    EntityRole.SPECIMEN,
                    RouteDestination.ADVERSARY_LAB,
                    f"medium_threat_score:{envelope.cf_threat_score}",
                    0.7,
                )
        
        # Check for verified bots (cooperative)
        if envelope.cf_verified_bot:
            return (
                ClassificationTier.TIER_A_COOPERATIVE,
                EntityRole.RESOURCE,
                RouteDestination.KNOWLEDGE_REALM,
                "verified_bot",
                0.9,
            )
        
        # Check bot score
        if envelope.cf_bot_score:
            if envelope.cf_bot_score < 30:
                # Low bot score = likely bot
                return (
                    ClassificationTier.TIER_B_HOSTILE,
                    EntityRole.SPECIMEN,
                    RouteDestination.ADVERSARY_LAB,
                    f"low_bot_score:{envelope.cf_bot_score}",
                    0.65,
                )
        
        # Unknown user agent (338 requests in your data)
        user_agent = envelope.raw_headers.get("user-agent", "")
        if not user_agent or user_agent.lower() in ["unknown", "other", ""]:
            return (
                ClassificationTier.TIER_C_SHADOW,
                EntityRole.UNKNOWN,
                RouteDestination.QUARANTINE,
                "unknown_user_agent",
                0.5,
            )
        
        # Default: Cooperative, send to Knowledge Realm
        return (
            ClassificationTier.TIER_A_COOPERATIVE,
            EntityRole.RESOURCE,
            RouteDestination.KNOWLEDGE_REALM,
            "default_cooperative",
            0.5,
        )
    
    @staticmethod
    def is_tor_traffic(envelope: RequestEnvelope) -> bool:
        """Check if traffic is from a Tor exit node."""
        # Check ASN
        if envelope.cf_asn and envelope.cf_asn in TOR_ASNS:
            # Could be Tor, but these ASNs also host regular traffic
            user_agent = (envelope.raw_headers.get("user-agent", "") or "").lower()
            if any(ind in user_agent for ind in TOR_EXIT_INDICATORS):
                return True
        
        # Check ASN org name
        asn_org = (envelope.cf_asn_org or "").lower()
        if any(ind in asn_org for ind in TOR_EXIT_INDICATORS):
            return True
        
        return False


# ---------------------------------------------------------------------------
# Specimen Profiler
# ---------------------------------------------------------------------------

class SpecimenProfiler:
    """
    Build and update long-term specimen profiles.
    """
    
    @staticmethod
    def get_or_create_profile(
        ip_address: str,
        envelope: RequestEnvelope | None = None,
    ) -> SpecimenProfile:
        """Get existing profile or create new one."""
        with _db() as conn:
            row = conn.execute(
                "SELECT * FROM specimen_profiles WHERE ip_address = ?",
                (ip_address,)
            ).fetchone()
            
            if row:
                return SpecimenProfile(
                    specimen_id=row["specimen_id"],
                    ip_address=row["ip_address"],
                    asn=row["asn"],
                    asn_org=row["asn_org"],
                    country=row["country"],
                    user_agent=row["user_agent"],
                    operating_system=row["operating_system"],
                    tls_fingerprint=row["tls_fingerprint"],
                    tier=ClassificationTier(row["tier"]),
                    role=EntityRole(row["role"]),
                    threat_level=ThreatLevel(row["threat_level"]),
                    total_requests=row["total_requests"],
                    honeypot_triggers=row["honeypot_triggers"],
                    error_count=row["error_count"],
                    success_count=row["success_count"],
                    behavioral_hash=row["behavioral_hash"],
                    first_seen=datetime.fromisoformat(row["first_seen"]),
                    last_seen=datetime.fromisoformat(row["last_seen"]),
                    path_attempts=json.loads(row["path_attempts"]),
                    methods_used=json.loads(row["methods_used"]),
                    error_patterns=json.loads(row["error_patterns"]),
                    response_codes=json.loads(row["response_codes"]),
                    notes=json.loads(row["notes"]),
                )
            
            # Create new profile
            now = datetime.now(timezone.utc)
            profile = SpecimenProfile(
                specimen_id=str(uuid.uuid4()),
                ip_address=ip_address,
                first_seen=now,
                last_seen=now,
            )
            
            # Populate from envelope if available
            if envelope:
                profile.asn = envelope.cf_asn
                profile.asn_org = envelope.cf_asn_org
                profile.country = envelope.cf_country
                profile.user_agent = envelope.raw_headers.get("user-agent")
            
            return profile
    
    @staticmethod
    def update_profile(
        profile: SpecimenProfile,
        envelope: RequestEnvelope,
        tier: ClassificationTier,
        role: EntityRole,
        was_error: bool = False,
        was_honeypot: bool = False,
    ) -> SpecimenProfile:
        """Update profile with new observation."""
        now = datetime.now(timezone.utc)
        
        # Update statistics
        profile.total_requests += 1
        profile.last_seen = now
        
        if was_error:
            profile.error_count += 1
            if envelope.error_type:
                profile.error_patterns.append(envelope.error_type)
                profile.error_patterns = profile.error_patterns[-100:]  # Keep last 100
        else:
            profile.success_count += 1
        
        if was_honeypot:
            profile.honeypot_triggers += 1
        
        # Update behavioral patterns
        if envelope.raw_path not in profile.path_attempts:
            profile.path_attempts.append(envelope.raw_path)
            profile.path_attempts = profile.path_attempts[-200:]  # Keep last 200
        
        if envelope.raw_method not in profile.methods_used:
            profile.methods_used.append(envelope.raw_method)
        
        if envelope.error_code and envelope.error_code not in profile.response_codes:
            profile.response_codes.append(envelope.error_code)
            profile.response_codes = profile.response_codes[-50:]  # Keep last 50
        
        # Update classification
        profile.tier = tier
        profile.role = role
        
        # Compute behavioral hash
        profile.behavioral_hash = profile.compute_behavioral_hash()
        
        # Calculate threat level based on behavior
        error_rate = profile.error_count / max(profile.total_requests, 1)
        if error_rate > 0.8 or profile.honeypot_triggers > 5:
            profile.threat_level = ThreatLevel.HIGH
        elif error_rate > 0.5 or profile.honeypot_triggers > 2:
            profile.threat_level = ThreatLevel.MEDIUM
        elif error_rate > 0.2 or profile.honeypot_triggers > 0:
            profile.threat_level = ThreatLevel.LOW
        else:
            profile.threat_level = ThreatLevel.NONE
        
        # Save to database
        SpecimenProfiler.save_profile(profile)
        
        return profile
    
    @staticmethod
    def save_profile(profile: SpecimenProfile) -> None:
        """Save profile to database."""
        with _db() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO specimen_profiles (
                    specimen_id, ip_address, asn, asn_org, country,
                    user_agent, operating_system, tls_fingerprint,
                    tier, role, threat_level,
                    total_requests, honeypot_triggers, error_count, success_count,
                    behavioral_hash, first_seen, last_seen,
                    path_attempts, methods_used, error_patterns, response_codes, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.specimen_id,
                    profile.ip_address,
                    profile.asn,
                    profile.asn_org,
                    profile.country,
                    profile.user_agent,
                    profile.operating_system,
                    profile.tls_fingerprint,
                    profile.tier.value,
                    profile.role.value,
                    profile.threat_level.value,
                    profile.total_requests,
                    profile.honeypot_triggers,
                    profile.error_count,
                    profile.success_count,
                    profile.behavioral_hash,
                    profile.first_seen.isoformat(),
                    profile.last_seen.isoformat(),
                    json.dumps(profile.path_attempts),
                    json.dumps(profile.methods_used),
                    json.dumps(profile.error_patterns),
                    json.dumps(profile.response_codes),
                    json.dumps(profile.notes),
                )
            )
            conn.commit()
    
    @staticmethod
    def add_known_attacker(
        ip_address: str,
        attack_count: int = 1,
        attacker_type: str = "unknown",
        notes: str | None = None,
    ) -> None:
        """Add or update a known attacker."""
        now = datetime.now(timezone.utc).isoformat()
        
        with _db() as conn:
            existing = conn.execute(
                "SELECT * FROM known_attackers WHERE ip_address = ?",
                (ip_address,)
            ).fetchone()
            
            if existing:
                conn.execute(
                    """
                    UPDATE known_attackers SET
                        attack_count = attack_count + ?,
                        last_seen = ?,
                        notes = COALESCE(?, notes)
                    WHERE ip_address = ?
                    """,
                    (attack_count, now, notes, ip_address)
                )
            else:
                conn.execute(
                    """
                    INSERT INTO known_attackers (
                        attacker_id, ip_address, attack_count, attacker_type,
                        first_seen, last_seen, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), ip_address, attack_count, attacker_type, now, now, notes)
                )
            
            conn.commit()
    
    @staticmethod
    def log_classification(
        envelope_id: str,
        ip_address: str,
        tier: ClassificationTier,
        role: EntityRole,
        route: RouteDestination,
        reason: str,
        confidence: float,
    ) -> None:
        """Log a classification decision for audit."""
        with _db() as conn:
            conn.execute(
                """
                INSERT INTO classification_log (
                    log_id, envelope_id, ip_address, tier, role, route,
                    reason, confidence, classified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    envelope_id,
                    ip_address,
                    tier.value,
                    role.value,
                    route.value,
                    reason,
                    confidence,
                    datetime.now(timezone.utc).isoformat(),
                )
            )
            conn.commit()


# ---------------------------------------------------------------------------
# Organism Growth Metrics
# ---------------------------------------------------------------------------

def get_organism_stats() -> dict[str, Any]:
    """Get statistics about the organism's growth."""
    with _db() as conn:
        # Specimen counts
        specimen_count = conn.execute(
            "SELECT COUNT(*) FROM specimen_profiles"
        ).fetchone()[0]
        
        # Tier breakdown
        tier_counts = {}
        for row in conn.execute(
            "SELECT tier, COUNT(*) as count FROM specimen_profiles GROUP BY tier"
        ).fetchall():
            tier_counts[row["tier"]] = row["count"]
        
        # Role breakdown
        role_counts = {}
        for row in conn.execute(
            "SELECT role, COUNT(*) as count FROM specimen_profiles GROUP BY role"
        ).fetchall():
            role_counts[row["role"]] = row["count"]
        
        # Known attackers
        attacker_count = conn.execute(
            "SELECT COUNT(*) FROM known_attackers"
        ).fetchone()[0]
        
        total_attacks = conn.execute(
            "SELECT SUM(attack_count) FROM known_attackers"
        ).fetchone()[0] or 0
        
        # Recent classifications (last hour)
        recent_count = conn.execute(
            """
            SELECT COUNT(*) FROM classification_log 
            WHERE classified_at > datetime('now', '-1 hour')
            """
        ).fetchone()[0]
        
        # High threat specimens
        high_threat = conn.execute(
            "SELECT COUNT(*) FROM specimen_profiles WHERE threat_level IN ('high', 'critical')"
        ).fetchone()[0]
        
        return {
            "total_specimens": specimen_count,
            "tier_breakdown": tier_counts,
            "role_breakdown": role_counts,
            "known_attackers": attacker_count,
            "total_attacks_tracked": total_attacks,
            "classifications_last_hour": recent_count,
            "high_threat_specimens": high_threat,
        }


# ---------------------------------------------------------------------------
# Seed Known Attackers from Traffic Data
# ---------------------------------------------------------------------------

def seed_known_attackers() -> None:
    """Seed the database with known attackers from traffic analysis."""
    for ip, data in KNOWN_ATTACKER_IPS.items():
        SpecimenProfiler.add_known_attacker(
            ip_address=ip,
            attack_count=data["attacks"],
            attacker_type=data["type"],
            notes=data["notes"],
        )


# Initialize with known attackers on import
try:
    seed_known_attackers()
except Exception:
    pass  # Ignore errors during import
