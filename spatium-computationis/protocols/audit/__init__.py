"""
Audit Protocols Package — Spatium Computationis

Audit and compliance protocols for:
- Activity logging
- Compliance tracking
- Version history
- Data archival

Glyphs:
  📝 Chronicon  — audit logging
  ✅ Conformitas — compliance
  🕐 Historia   — version history
  📦 Archivum   — archival
"""

from .chronicon import (
    log_activity,
    get_activity_log,
    AuditEntry,
    AuditAction,
)
from .conformitas import (
    check_compliance,
    register_compliance_rule,
    ComplianceResult,
    ComplianceRule,
)
from .historia import (
    record_version,
    get_version_history,
    VersionEntry,
)
from .archivum import (
    archive_data,
    restore_data,
    ArchiveConfig,
    ArchiveResult,
)

__all__ = [
    # Chronicon
    "log_activity",
    "get_activity_log",
    "AuditEntry",
    "AuditAction",
    # Conformitas
    "check_compliance",
    "register_compliance_rule",
    "ComplianceResult",
    "ComplianceRule",
    # Historia
    "record_version",
    "get_version_history",
    "VersionEntry",
    # Archivum
    "archive_data",
    "restore_data",
    "ArchiveConfig",
    "ArchiveResult",
]
