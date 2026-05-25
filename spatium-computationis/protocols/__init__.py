"""
Protocols Package — Spatium Computationis

A comprehensive suite of 50 production-ready protocols organized into categories:

Core Pipeline (6 protocols):
  I.   Ingressus  — raw input normalization
  II.  Compressio — compression into intelligence objects
  III. Ordinatio  — routing decisions
  IV.  Actio      — action execution
  V.   Reductus   — field feedback loop
  VI.  Feedback   — learning and weight adjustment

Security (6 protocols):
  🔐 Authenticatio — identity verification
  🛡️ Auctoritas    — permission checking
  ⚡ Limitatio     — rate control
  🔒 Cryptographia — encryption
  🎫 Token Custos  — token management
  🧹 Sanitatio     — input sanitization

Monitoring (5 protocols):
  💓 Sanitas      — health monitoring
  📊 Metrica      — metrics collection
  🔍 Tractus      — distributed tracing
  🔔 Vigilia      — alerting
  📡 Telemetria   — telemetry

Resilience (5 protocols):
  🔌 Circuitus    — circuit breaker
  🔄 Iteratio     — retry logic
  ⏱️ Tempus       — timeout management
  🛟 Subsidium    — fallback handling
  🚧 Bulkhead     — isolation

Data (5 protocols):
  💾 Repositio    — caching
  🔀 Transformatio — data transformation
  📊 Aggregatio   — aggregation
  ✓ Validatio    — schema validation
  📦 Serializatio — serialization

Communication (4 protocols):
  🪝 Uncus        — webhooks
  📬 Nuntius      — notifications
  📡 Eventus      — server-sent events
  📋 Coda         — queue management

Audit (4 protocols):
  📝 Chronicon    — audit logging
  ✅ Conformitas  — compliance
  🕐 Historia     — version history
  📦 Archivum     — archival

Workflow (4 protocols):
  ⏰ Calendarium  — scheduling
  📦 Fasciculus   — batching
  📋 Ordo         — orchestration
  🔄 Cursus       — flow control

Total: 50 protocols ready for production use.

Glyphs (Core):
  ⊕ Ingressus  — input gate
  ⌬ Compressio — compression
  ≡ Ordinatio  — routing
  ⚡ Actio      — execution
  ↺ Reductus   — field return
  ⟲ Feedback   — learning loop
"""

# Core Pipeline Protocols
from . import ingressus, compressio, ordinatio, actio, reductus, feedback

# Security Protocols
from . import security
from .security import (
    # Authenticatio
    authenticate_request,
    validate_token,
    AuthenticationResult,
    TokenPayload,
    AuthMethod,
    AuthStatus,
    # Auctoritas
    authorize_action,
    check_permission,
    grant_permission,
    revoke_permission,
    AuthorizationResult,
    Permission,
    PermissionLevel,
    ResourceType,
    # Limitatio
    check_rate_limit,
    record_request,
    reset_penalty,
    RateLimitResult,
    RateLimitConfig,
    RateLimitScope,
    # Cryptographia
    encrypt_data,
    decrypt_data,
    hash_sensitive,
    verify_hash,
    rotate_key,
    EncryptionResult,
    DecryptionResult,
    HashResult,
    # Token Custos
    create_token,
    revoke_token,
    refresh_token,
    introspect_token,
    TokenInfo,
    TokenType,
    TokenStatus,
    # Sanitatio
    sanitize_input,
    validate_content,
    SanitizationResult,
    ValidationResult as SanitizationValidationResult,
    SanitizationType,
    ValidationLevel,
)

# Monitoring Protocols
from . import monitoring
from .monitoring import (
    # Sanitas
    health_check,
    liveness_probe,
    readiness_probe,
    HealthStatus,
    HealthCheckResult,
    ComponentHealth,
    # Metrica
    record_metric,
    get_metrics,
    MetricType,
    MetricValue,
    MetricsSnapshot,
    # Tractus
    start_trace,
    end_trace,
    add_span,
    TraceContext,
    Span,
    TraceResult,
    # Vigilia
    create_alert,
    resolve_alert,
    check_alert_rules,
    AlertSeverity,
    Alert,
    AlertRule,
    # Telemetria
    emit_telemetry,
    get_telemetry,
    TelemetryEvent,
    TelemetryConfig,
)

# Resilience Protocols
from . import resilience
from .resilience import (
    # Circuitus
    CircuitBreaker,
    CircuitState,
    circuit_call,
    get_circuit_status,
    # Iteratio
    retry_with_backoff,
    RetryConfig,
    RetryResult,
    # Tempus
    with_timeout,
    TimeoutConfig,
    TimeoutResult,
    # Subsidium
    with_fallback,
    register_fallback,
    FallbackResult,
    # Bulkhead
    Bulkhead,
    acquire_bulkhead,
    BulkheadConfig,
)

# Data Protocols
from . import data
from .data import (
    # Repositio
    cache_get,
    cache_set,
    cache_delete,
    cache_clear,
    CacheConfig,
    CacheEntry,
    # Transformatio
    transform_data,
    register_transformer,
    TransformResult,
    TransformConfig,
    # Aggregatio
    aggregate_data,
    rollup_data,
    AggregateConfig,
    AggregateResult,
    # Validatio
    validate_schema,
    validate_data,
    ValidationConfig,
    ValidationResult,
    # Serializatio
    serialize,
    deserialize,
    SerializationFormat,
)

# Communication Protocols
from . import communication
from .communication import (
    # Uncus
    register_webhook,
    trigger_webhook,
    WebhookConfig,
    WebhookResult,
    # Nuntius
    send_notification,
    get_notifications,
    NotificationChannel,
    Notification,
    # Eventus
    create_event_stream,
    push_event,
    EventStream,
    SSEEvent,
    # Coda
    enqueue,
    dequeue,
    peek,
    QueueConfig,
    QueueMessage,
)

# Audit Protocols
from . import audit
from .audit import (
    # Chronicon
    log_activity,
    get_activity_log,
    AuditEntry,
    AuditAction,
    # Conformitas
    check_compliance,
    register_compliance_rule,
    ComplianceResult,
    ComplianceRule,
    # Historia
    record_version,
    get_version_history,
    VersionEntry,
    # Archivum
    archive_data,
    restore_data,
    ArchiveConfig,
    ArchiveResult,
)

# Workflow Protocols
from . import workflow
from .workflow import (
    # Calendarium
    schedule_task,
    get_scheduled_tasks,
    ScheduledTask,
    ScheduleConfig,
    # Fasciculus
    create_batch,
    process_batch,
    BatchConfig,
    BatchResult,
    # Ordo
    create_workflow,
    execute_workflow,
    WorkflowDefinition,
    WorkflowResult,
    # Cursus
    create_pipeline,
    run_pipeline,
    PipelineConfig,
    PipelineResult,
)

__all__ = [
    # Core pipeline modules
    "ingressus",
    "compressio",
    "ordinatio",
    "actio",
    "reductus",
    "feedback",
    
    # Protocol category modules
    "security",
    "monitoring",
    "resilience",
    "data",
    "communication",
    "audit",
    "workflow",
    
    # Security exports
    "authenticate_request",
    "validate_token",
    "AuthenticationResult",
    "TokenPayload",
    "AuthMethod",
    "AuthStatus",
    "authorize_action",
    "check_permission",
    "grant_permission",
    "revoke_permission",
    "AuthorizationResult",
    "Permission",
    "PermissionLevel",
    "ResourceType",
    "check_rate_limit",
    "record_request",
    "reset_penalty",
    "RateLimitResult",
    "RateLimitConfig",
    "RateLimitScope",
    "encrypt_data",
    "decrypt_data",
    "hash_sensitive",
    "verify_hash",
    "rotate_key",
    "EncryptionResult",
    "DecryptionResult",
    "HashResult",
    "create_token",
    "revoke_token",
    "refresh_token",
    "introspect_token",
    "TokenInfo",
    "TokenType",
    "TokenStatus",
    "sanitize_input",
    "validate_content",
    "SanitizationResult",
    "SanitizationType",
    "ValidationLevel",
    
    # Monitoring exports
    "health_check",
    "liveness_probe",
    "readiness_probe",
    "HealthStatus",
    "HealthCheckResult",
    "ComponentHealth",
    "record_metric",
    "get_metrics",
    "MetricType",
    "MetricValue",
    "MetricsSnapshot",
    "start_trace",
    "end_trace",
    "add_span",
    "TraceContext",
    "Span",
    "TraceResult",
    "create_alert",
    "resolve_alert",
    "check_alert_rules",
    "AlertSeverity",
    "Alert",
    "AlertRule",
    "emit_telemetry",
    "get_telemetry",
    "TelemetryEvent",
    "TelemetryConfig",
    
    # Resilience exports
    "CircuitBreaker",
    "CircuitState",
    "circuit_call",
    "get_circuit_status",
    "retry_with_backoff",
    "RetryConfig",
    "RetryResult",
    "with_timeout",
    "TimeoutConfig",
    "TimeoutResult",
    "with_fallback",
    "register_fallback",
    "FallbackResult",
    "Bulkhead",
    "acquire_bulkhead",
    "BulkheadConfig",
    
    # Data exports
    "cache_get",
    "cache_set",
    "cache_delete",
    "cache_clear",
    "CacheConfig",
    "CacheEntry",
    "transform_data",
    "register_transformer",
    "TransformResult",
    "TransformConfig",
    "aggregate_data",
    "rollup_data",
    "AggregateConfig",
    "AggregateResult",
    "validate_schema",
    "validate_data",
    "ValidationConfig",
    "ValidationResult",
    "serialize",
    "deserialize",
    "SerializationFormat",
    
    # Communication exports
    "register_webhook",
    "trigger_webhook",
    "WebhookConfig",
    "WebhookResult",
    "send_notification",
    "get_notifications",
    "NotificationChannel",
    "Notification",
    "create_event_stream",
    "push_event",
    "EventStream",
    "SSEEvent",
    "enqueue",
    "dequeue",
    "peek",
    "QueueConfig",
    "QueueMessage",
    
    # Audit exports
    "log_activity",
    "get_activity_log",
    "AuditEntry",
    "AuditAction",
    "check_compliance",
    "register_compliance_rule",
    "ComplianceResult",
    "ComplianceRule",
    "record_version",
    "get_version_history",
    "VersionEntry",
    "archive_data",
    "restore_data",
    "ArchiveConfig",
    "ArchiveResult",
    
    # Workflow exports
    "schedule_task",
    "get_scheduled_tasks",
    "ScheduledTask",
    "ScheduleConfig",
    "create_batch",
    "process_batch",
    "BatchConfig",
    "BatchResult",
    "create_workflow",
    "execute_workflow",
    "WorkflowDefinition",
    "WorkflowResult",
    "create_pipeline",
    "run_pipeline",
    "PipelineConfig",
    "PipelineResult",
]
