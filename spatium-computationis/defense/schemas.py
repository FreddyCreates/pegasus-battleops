"""
Defense Schemas — Data models for the AI defense system.
⛨ All threat data flowing through the defense system conforms to these models.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ThreatLevel(str, Enum):
    """Threat severity classification."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BotClassification(str, Enum):
    """Bot type classification."""
    LEGITIMATE = "legitimate"      # Known good bots (Googlebot, etc.)
    UNKNOWN = "unknown"            # Unclassified visitor
    SCRAPER = "scraper"            # Content scraping bot
    SCANNER = "scanner"            # Vulnerability scanner
    CRAWLER = "crawler"            # Aggressive crawler
    CREDENTIAL_STUFFER = "credential_stuffer"  # Login brute-forcer
    EXPLOIT_HUNTER = "exploit_hunter"  # Looking for exploits
    DDOS_PARTICIPANT = "ddos_participant"  # Part of DDoS attack
    RESEARCH = "research"          # Security researcher
    HONEYPOT_CAUGHT = "honeypot_caught"  # Fell for honeypot


class TrapType(str, Enum):
    """Types of honeypot traps."""
    ADMIN_PANEL = "admin_panel"     # Fake admin interfaces
    CONFIG_FILE = "config_file"     # Fake .env, config.php, etc.
    API_ENDPOINT = "api_endpoint"   # Fake API routes
    LOGIN_FORM = "login_form"       # Fake login pages
    DEBUG_INFO = "debug_info"       # Fake debug/status endpoints
    BACKUP_FILE = "backup_file"     # Fake backup files
    GIT_REPO = "git_repo"           # Fake .git exposure
    DATABASE = "database"           # Fake DB endpoints


class AdaptiveAction(str, Enum):
    """Actions the adaptive system can take."""
    OBSERVE = "observe"             # Just watch and learn
    CHALLENGE = "challenge"         # Issue JS/CAPTCHA challenge
    RATE_LIMIT = "rate_limit"       # Slow down requests
    REDIRECT_HONEYPOT = "redirect_honeypot"  # Send to trap
    BLOCK_TEMPORARY = "block_temporary"  # Short-term block
    BLOCK_PERMANENT = "block_permanent"  # Long-term block
    ENGAGE = "engage"               # AI engagement (feed fake data)
    ALERT = "alert"                 # Notify operators


# ---------------------------------------------------------------------------
# Fingerprinting
# ---------------------------------------------------------------------------

class BotFingerprint(BaseModel):
    """Behavioral fingerprint of a visitor. 🜏"""
    fingerprint_id: str
    ip_address: str
    user_agent: str | None = None
    accept_language: str | None = None
    accept_encoding: str | None = None
    
    # Behavioral signals
    request_timing_ms: list[float] = Field(default_factory=list)
    request_paths: list[str] = Field(default_factory=list)
    http_methods: list[str] = Field(default_factory=list)
    response_codes: list[int] = Field(default_factory=list)
    
    # TLS fingerprint (JA3/JA4)
    tls_fingerprint: str | None = None
    
    # Derived metrics
    requests_per_minute: float = 0.0
    unique_paths: int = 0
    error_rate: float = 0.0
    honeypot_triggers: int = 0
    
    # Classification
    classification: BotClassification = BotClassification.UNKNOWN
    threat_level: ThreatLevel = ThreatLevel.NONE
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Metadata
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_requests: int = 1


# ---------------------------------------------------------------------------
# Honeypot Events
# ---------------------------------------------------------------------------

class HoneypotEvent(BaseModel):
    """Record of a honeypot trigger. 🜏"""
    event_id: str
    trap_type: TrapType
    trap_path: str
    fingerprint_id: str
    ip_address: str
    
    # Request details
    method: str
    headers: dict[str, str] = Field(default_factory=dict)
    query_params: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
    
    # Response sent
    response_code: int
    fake_data_served: bool = False
    engagement_type: str | None = None  # What kind of fake response
    
    # Analysis
    attack_pattern: str | None = None
    tools_detected: list[str] = Field(default_factory=list)
    
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Threat Intelligence
# ---------------------------------------------------------------------------

class ThreatRecord(BaseModel):
    """Comprehensive threat record. ⚠"""
    record_id: str
    fingerprint_id: str | None = None
    ip_address: str
    
    # Classification
    threat_level: ThreatLevel
    classification: BotClassification
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Evidence
    honeypot_events: list[str] = Field(default_factory=list)  # Event IDs
    attack_patterns: list[str] = Field(default_factory=list)
    tools_detected: list[str] = Field(default_factory=list)
    
    # Behavioral summary
    total_requests: int = 0
    honeypot_triggers: int = 0
    blocked_attempts: int = 0
    
    # Response
    action_taken: AdaptiveAction = AdaptiveAction.OBSERVE
    
    # Lineage tracking
    related_ips: list[str] = Field(default_factory=list)
    campaign_id: str | None = None  # If part of coordinated attack
    
    # Metadata
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ThreatIntelligence(BaseModel):
    """Cloudflare or external threat feed data. ◎"""
    intel_id: str
    source: str = "cloudflare"  # cloudflare, internal, external
    
    # Cloudflare-specific
    cf_ray: str | None = None
    cf_threat_score: int | None = Field(default=None, ge=0, le=100)
    cf_bot_score: int | None = Field(default=None, ge=1, le=99)
    cf_verified_bot: bool = False
    cf_country: str | None = None
    cf_asn: int | None = None
    cf_asn_org: str | None = None
    
    # Processed intelligence
    ip_address: str
    threat_level: ThreatLevel
    classification: BotClassification
    
    # Actions recommended
    recommended_action: AdaptiveAction = AdaptiveAction.OBSERVE
    
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Adaptive Response
# ---------------------------------------------------------------------------

class AdaptiveResponse(BaseModel):
    """Adaptive system response decision. ⟲"""
    response_id: str
    fingerprint_id: str
    
    # Decision
    action: AdaptiveAction
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Context
    threat_record_id: str | None = None
    triggered_by: str  # What event/condition triggered this
    
    # A/B testing
    strategy_id: str | None = None  # Which defense strategy was used
    control_group: bool = False  # Is this a control (baseline) response?
    
    # Outcome tracking
    outcome_effective: bool | None = None  # Was the response effective?
    outcome_notes: str | None = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evaluated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Metrics & Dashboard
# ---------------------------------------------------------------------------

class DefenseMetrics(BaseModel):
    """Real-time defense metrics snapshot. ◎"""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    window_minutes: int = 5
    
    # Volume metrics
    total_requests: int = 0
    unique_visitors: int = 0
    honeypot_triggers: int = 0
    threats_detected: int = 0
    
    # Classification breakdown
    classification_counts: dict[str, int] = Field(default_factory=dict)
    threat_level_counts: dict[str, int] = Field(default_factory=dict)
    
    # Action metrics
    challenges_issued: int = 0
    blocks_issued: int = 0
    engagements_active: int = 0
    
    # Top threats
    top_threat_ips: list[str] = Field(default_factory=list)
    top_attack_patterns: list[str] = Field(default_factory=list)
    top_trap_types: list[str] = Field(default_factory=list)
    
    # Learning metrics
    new_patterns_learned: int = 0
    strategies_tested: int = 0


class ThreatGenome(BaseModel):
    """Attack pattern stored in the threat genome. ⟲"""
    genome_id: str
    pattern_name: str
    pattern_description: str
    
    # Pattern signature
    path_patterns: list[str] = Field(default_factory=list)
    header_patterns: dict[str, str] = Field(default_factory=dict)
    timing_signature: dict[str, float] = Field(default_factory=dict)
    
    # Classification
    typical_classification: BotClassification
    typical_threat_level: ThreatLevel
    
    # Effective responses
    effective_actions: list[AdaptiveAction] = Field(default_factory=list)
    ineffective_actions: list[AdaptiveAction] = Field(default_factory=list)
    
    # Statistics
    times_observed: int = 0
    first_observed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_observed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# WebSocket Messages
# ---------------------------------------------------------------------------

class ThreatFeedMessage(BaseModel):
    """Real-time threat feed message for WebSocket."""
    message_type: str  # "event", "metric", "alert", "update"
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
