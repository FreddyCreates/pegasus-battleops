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


# ---------------------------------------------------------------------------
# Request Envelope — Universal container for all incoming traffic
# ---------------------------------------------------------------------------

class RequestEnvelope(BaseModel):
    """
    Universal request envelope that wraps all incoming traffic.
    🜏 The fundamental unit flowing through Shadow Decryption and Error Eyes.
    """
    envelope_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Source fingerprint
    source_ip: str
    source_fingerprint: str | None = None
    
    # Raw request data
    raw_method: str
    raw_path: str
    raw_headers: dict[str, str] = Field(default_factory=dict)
    raw_query: dict[str, str] = Field(default_factory=dict)
    raw_body: bytes | None = None
    raw_body_text: str | None = None
    
    # Cloudflare metadata
    cf_ray: str | None = None
    cf_country: str | None = None
    cf_asn: int | None = None
    cf_asn_org: str | None = None
    cf_threat_score: int | None = None
    cf_bot_score: int | None = None
    cf_verified_bot: bool = False
    cf_tls_version: str | None = None
    cf_tls_cipher: str | None = None
    
    # State flags
    is_encrypted: bool = False
    is_malformed: bool = False
    has_error: bool = False
    error_type: str | None = None
    error_code: int | None = None
    
    # Processing state
    decryption_attempted: bool = False
    repair_attempted: bool = False
    ai_source_detected: str | None = None  # "claude", "google", "openai", etc.
    
    # Routing decision
    route_decision: str | None = None  # "lab", "realm", "drop", "vip"
    route_reason: str | None = None


class AISourceType(str, Enum):
    """Known AI/Bot source types for VIP handling."""
    CLAUDE = "claude"
    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    BING = "bing"
    PERPLEXITY = "perplexity"
    HUGGINGFACE = "huggingface"
    COHERE = "cohere"
    UNKNOWN_AI = "unknown_ai"
    HUMAN = "human"
    BOT = "bot"


class RouteDestination(str, Enum):
    """Where traffic gets routed after processing."""
    ADVERSARY_LAB = "adversary_lab"    # Dissect hostile/noisy agents
    KNOWLEDGE_REALM = "knowledge_realm"  # Cooperative agents work here
    VIP_GATE = "vip_gate"              # Special handling for AI visitors
    DROP = "drop"                       # Discard junk
    QUARANTINE = "quarantine"           # Hold for analysis
    REPLAY = "replay"                   # Repaired request, try again


# ---------------------------------------------------------------------------
# Shadow Decryption — Decode encrypted/weird traffic
# ---------------------------------------------------------------------------

class DecryptionResult(BaseModel):
    """
    Result of Shadow Decryption attempt.
    👁️ Shadow Decryptors try to decode encrypted/malformed traffic.
    """
    result_id: str
    envelope_id: str
    
    # Decryption outcome
    success: bool = False
    partial: bool = False  # Partially decoded
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Decoded data
    decoded_payload: str | None = None
    decoded_headers: dict[str, str] = Field(default_factory=dict)
    decoded_method: str | None = None
    decoded_path: str | None = None
    
    # Protocol detection
    detected_protocol: str | None = None  # "http", "websocket", "grpc", etc.
    protocol_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Entropy analysis
    entropy_score: float = Field(ge=0.0, le=1.0, default=0.5)
    entropy_profile: str | None = None  # "random", "compressed", "encrypted", "text"
    
    # Pattern extraction
    extracted_patterns: list[str] = Field(default_factory=list)
    extracted_snippets: list[str] = Field(default_factory=list)
    
    # Signal score (how interesting is this?)
    signal_score: float = Field(ge=0.0, le=1.0, default=0.0)
    signal_reason: str | None = None
    
    # Metadata
    processing_time_ms: float = 0.0
    techniques_tried: list[str] = Field(default_factory=list)
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Error Eyes — Repair and learn from errors
# ---------------------------------------------------------------------------

class ErrorType(str, Enum):
    """Types of errors the Error Eyes handle."""
    HTTP_4XX = "http_4xx"
    HTTP_5XX = "http_5xx"
    PARSE_ERROR = "parse_error"
    SCHEMA_MISMATCH = "schema_mismatch"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    PATH_NOT_FOUND = "path_not_found"
    MALFORMED_JSON = "malformed_json"
    MISSING_FIELDS = "missing_fields"
    INVALID_HEADERS = "invalid_headers"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    TLS_ERROR = "tls_error"
    UNKNOWN = "unknown"


class RepairResult(BaseModel):
    """
    Result of Error Eyes repair attempt.
    👁️ Error Eyes try to fix and replay broken requests.
    """
    result_id: str
    envelope_id: str
    
    # Original error
    error_type: ErrorType
    error_code: int | None = None
    error_message: str | None = None
    
    # Repair outcome
    repair_success: bool = False
    repair_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Repaired request
    repaired_method: str | None = None
    repaired_path: str | None = None
    repaired_headers: dict[str, str] = Field(default_factory=dict)
    repaired_body: str | None = None
    
    # What was fixed
    fixes_applied: list[str] = Field(default_factory=list)
    # e.g., ["added_content_type", "fixed_json_syntax", "corrected_path"]
    
    # Learning
    error_pattern: str | None = None  # Pattern name for this error type
    source_dialect: str | None = None  # "claude_style", "scanner_style", etc.
    
    # Replay status
    replay_attempted: bool = False
    replay_success: bool = False
    replay_response_code: int | None = None
    
    # Metadata
    processing_time_ms: float = 0.0
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorDialect(BaseModel):
    """
    Learned error patterns from specific sources.
    👁️ Error Eyes build dialects over time.
    """
    dialect_id: str
    source_type: str  # "claude", "google", "scanner", "crawler"
    
    # Common error patterns
    common_errors: list[ErrorType] = Field(default_factory=list)
    error_frequencies: dict[str, int] = Field(default_factory=dict)
    
    # Auto-correction rules
    correction_rules: list[dict[str, Any]] = Field(default_factory=list)
    # e.g., [{"pattern": "missing Content-Type", "fix": "add application/json"}]
    
    # Statistics
    total_errors_seen: int = 0
    successful_repairs: int = 0
    repair_success_rate: float = 0.0
    
    # Metadata
    first_observed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# VIP AI Handling — Special treatment for known AI visitors
# ---------------------------------------------------------------------------

class AIVisitorProfile(BaseModel):
    """
    Profile of a known AI visitor (Claude, Google, etc.).
    ⭐ VIP specimens get special treatment.
    """
    profile_id: str
    ai_source: AISourceType
    
    # Identification markers
    ip_ranges: list[str] = Field(default_factory=list)
    user_agent_patterns: list[str] = Field(default_factory=list)
    tls_fingerprints: list[str] = Field(default_factory=list)
    request_patterns: list[str] = Field(default_factory=list)
    
    # Behavioral characteristics
    typical_paths: list[str] = Field(default_factory=list)
    typical_methods: list[str] = Field(default_factory=list)
    typical_headers: dict[str, str] = Field(default_factory=dict)
    
    # Statistics
    total_visits: int = 0
    successful_interactions: int = 0
    failed_interactions: int = 0
    
    # Last known state
    last_seen: datetime | None = None
    last_interaction_summary: str | None = None


class AISpecimenLog(BaseModel):
    """
    Log of an AI visitor interaction.
    ⭐ Gold data for understanding AI behavior.
    """
    log_id: str
    envelope_id: str
    ai_source: AISourceType
    
    # Request details
    request_path: str
    request_method: str
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: str | None = None
    
    # What we served them
    response_code: int
    response_type: str  # "question", "task", "knowledge_shard", "challenge"
    response_content: str | None = None
    
    # Their behavior
    response_time_ms: float = 0.0
    follow_up_requests: int = 0
    
    # Analysis
    prompt_detected: str | None = None  # If we detected what prompt they're following
    behavior_notes: str | None = None
    
    # Metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Gatekeeper — Route decisions
# ---------------------------------------------------------------------------

class GatekeeperDecision(BaseModel):
    """
    Decision made by the Gatekeeper agent.
    🚪 Determines where traffic goes after processing.
    """
    decision_id: str
    envelope_id: str
    
    # Input signals
    decryption_result_id: str | None = None
    repair_result_id: str | None = None
    fingerprint_id: str | None = None
    
    # Decision
    route: RouteDestination
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Scores used in decision
    threat_score: float = Field(ge=0.0, le=1.0, default=0.0)
    signal_score: float = Field(ge=0.0, le=1.0, default=0.0)
    cooperation_score: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Special handling flags
    is_vip: bool = False
    requires_interrogation: bool = False
    requires_challenge: bool = False
    
    # Metadata
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Adversary Lab — Dissection results
# ---------------------------------------------------------------------------

class AdversaryDissection(BaseModel):
    """
    Results of dissecting a hostile/noisy agent in the Adversary Lab.
    🔬 Extract intelligence from attackers.
    """
    dissection_id: str
    envelope_id: str
    fingerprint_id: str | None = None
    
    # What we found
    jailbreak_attempts: list[str] = Field(default_factory=list)
    exploit_patterns: list[str] = Field(default_factory=list)
    payload_signatures: list[str] = Field(default_factory=list)
    
    # Tool identification
    tools_detected: list[str] = Field(default_factory=list)
    tool_versions: dict[str, str] = Field(default_factory=dict)
    
    # Provider analysis
    likely_provider: str | None = None  # hosting provider, botnet, etc.
    provider_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Campaign detection
    campaign_indicators: list[str] = Field(default_factory=list)
    related_fingerprints: list[str] = Field(default_factory=list)
    
    # Counter-intelligence
    probe_results: dict[str, Any] = Field(default_factory=dict)
    # Results of probing back at the attacker
    
    # Metadata
    dissected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Knowledge Realm — Research outputs
# ---------------------------------------------------------------------------

class ResearchArtifact(BaseModel):
    """
    Output from cooperative AI agents in the Knowledge Realm.
    📚 Monetizable research outputs.
    """
    artifact_id: str
    ai_source: AISourceType
    envelope_id: str
    
    # What they produced
    artifact_type: str  # "draft", "design", "code", "analysis", "research"
    title: str
    content: str
    
    # Quality assessment
    quality_score: float = Field(ge=0.0, le=1.0, default=0.5)
    completeness: float = Field(ge=0.0, le=1.0, default=0.5)
    originality: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Knowledge shards used
    shards_accessed: list[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
