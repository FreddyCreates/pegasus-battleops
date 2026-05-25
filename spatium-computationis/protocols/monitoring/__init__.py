"""
Monitoring Protocols Package — Spatium Computationis

Monitoring and observability protocols for:
- Health checks and liveness probes
- Metrics collection and aggregation
- Distributed tracing
- Alerting and notifications

Glyphs:
  💓 Sanitas   — health monitoring
  📊 Metrica   — metrics collection
  🔍 Tractus   — distributed tracing
  🔔 Vigilia   — alerting
"""

from .sanitas import (
    health_check,
    liveness_probe,
    readiness_probe,
    HealthStatus,
    HealthCheckResult,
    ComponentHealth,
)
from .metrica import (
    record_metric,
    get_metrics,
    MetricType,
    MetricValue,
    MetricsSnapshot,
)
from .tractus import (
    start_trace,
    end_trace,
    add_span,
    TraceContext,
    Span,
    TraceResult,
)
from .vigilia import (
    create_alert,
    resolve_alert,
    check_alert_rules,
    AlertSeverity,
    Alert,
    AlertRule,
)
from .telemetria import (
    emit_telemetry,
    get_telemetry,
    TelemetryEvent,
    TelemetryConfig,
)

__all__ = [
    # Sanitas
    "health_check",
    "liveness_probe",
    "readiness_probe",
    "HealthStatus",
    "HealthCheckResult",
    "ComponentHealth",
    # Metrica
    "record_metric",
    "get_metrics",
    "MetricType",
    "MetricValue",
    "MetricsSnapshot",
    # Tractus
    "start_trace",
    "end_trace",
    "add_span",
    "TraceContext",
    "Span",
    "TraceResult",
    # Vigilia
    "create_alert",
    "resolve_alert",
    "check_alert_rules",
    "AlertSeverity",
    "Alert",
    "AlertRule",
    # Telemetria
    "emit_telemetry",
    "get_telemetry",
    "TelemetryEvent",
    "TelemetryConfig",
]
