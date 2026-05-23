"""
Protocol: Conformitas  ✅
Meaning: Compliance checking and rule enforcement.

Handles:
- Compliance rule definition
- Automated compliance checks
- Policy enforcement
- Compliance reporting
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field


class ComplianceCategory(str, Enum):
    """Categories of compliance rules."""
    SECURITY = "security"
    PRIVACY = "privacy"
    DATA_QUALITY = "data_quality"
    BUSINESS = "business"
    REGULATORY = "regulatory"
    OPERATIONAL = "operational"


class ComplianceStatus(str, Enum):
    """Status of compliance check."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"
    ERROR = "error"


class ComplianceRule(BaseModel):
    """A compliance rule definition."""
    rule_id: str
    name: str
    description: str
    category: ComplianceCategory
    
    # Rule definition
    resource_type: str
    condition: str  # Expression or rule name
    severity: str = "medium"  # low, medium, high, critical
    
    # Remediation
    remediation_steps: str | None = None
    auto_remediate: bool = False
    
    # Status
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ComplianceResult(BaseModel):
    """Result of a compliance check."""
    check_id: str
    rule_id: str
    rule_name: str
    resource_type: str
    resource_id: str | None = None
    
    # Result
    status: ComplianceStatus
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    
    # Remediation
    remediation_steps: str | None = None
    
    # Timing
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "compliance.db"


def _init_compliance_db() -> None:
    """Initialize the compliance database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS compliance_rules (
                rule_id         TEXT PRIMARY KEY,
                name            TEXT UNIQUE NOT NULL,
                description     TEXT,
                category        TEXT NOT NULL,
                resource_type   TEXT NOT NULL,
                condition       TEXT NOT NULL,
                severity        TEXT DEFAULT 'medium',
                remediation     TEXT,
                auto_remediate  INTEGER DEFAULT 0,
                enabled         INTEGER DEFAULT 1,
                created_at      TEXT NOT NULL
            )
            """
        )
        
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS compliance_checks (
                check_id        TEXT PRIMARY KEY,
                rule_id         TEXT NOT NULL,
                rule_name       TEXT NOT NULL,
                resource_type   TEXT NOT NULL,
                resource_id     TEXT,
                status          TEXT NOT NULL,
                message         TEXT,
                details         TEXT DEFAULT '{}',
                checked_at      TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cc_rule ON compliance_checks(rule_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cc_status ON compliance_checks(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cc_time ON compliance_checks(checked_at)")
        
        conn.commit()


_init_compliance_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Rule Validators
# ---------------------------------------------------------------------------

_rule_validators: dict[str, Callable[[Any, dict], ComplianceStatus]] = {}


def register_compliance_rule(
    name: str,
    validator: Callable[[Any, dict], ComplianceStatus],
) -> None:
    """Register a custom compliance rule validator."""
    _rule_validators[name] = validator


# Built-in validators
def _required_fields_validator(data: Any, params: dict) -> ComplianceStatus:
    """Check that required fields are present."""
    if not isinstance(data, dict):
        return ComplianceStatus.ERROR
    
    required = params.get("fields", [])
    missing = [f for f in required if f not in data or data[f] is None]
    
    if missing:
        return ComplianceStatus.NON_COMPLIANT
    return ComplianceStatus.COMPLIANT


def _max_length_validator(data: Any, params: dict) -> ComplianceStatus:
    """Check field length limits."""
    if not isinstance(data, dict):
        return ComplianceStatus.ERROR
    
    field = params.get("field")
    max_len = params.get("max_length", 0)
    
    if field and field in data:
        value = data[field]
        if hasattr(value, "__len__") and len(value) > max_len:
            return ComplianceStatus.NON_COMPLIANT
    
    return ComplianceStatus.COMPLIANT


def _data_classification_validator(data: Any, params: dict) -> ComplianceStatus:
    """Check data classification rules."""
    if not isinstance(data, dict):
        return ComplianceStatus.ERROR
    
    sensitive_fields = params.get("sensitive_fields", [])
    
    for field in sensitive_fields:
        if field in data and data[field]:
            # Check if encrypted or masked
            value = str(data[field])
            if not (value.startswith("***") or value.startswith("enc:")):
                return ComplianceStatus.NON_COMPLIANT
    
    return ComplianceStatus.COMPLIANT


register_compliance_rule("required_fields", _required_fields_validator)
register_compliance_rule("max_length", _max_length_validator)
register_compliance_rule("data_classification", _data_classification_validator)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def create_compliance_rule(
    name: str,
    description: str,
    category: ComplianceCategory,
    resource_type: str,
    condition: str,
    severity: str = "medium",
    remediation_steps: str | None = None,
    auto_remediate: bool = False,
) -> ComplianceRule:
    """
    Protocol Conformitas: create a compliance rule.
    """
    rule_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    rule = ComplianceRule(
        rule_id=rule_id,
        name=name,
        description=description,
        category=category,
        resource_type=resource_type,
        condition=condition,
        severity=severity,
        remediation_steps=remediation_steps,
        auto_remediate=auto_remediate,
        created_at=now,
    )
    
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO compliance_rules (
                rule_id, name, description, category, resource_type,
                condition, severity, remediation, auto_remediate, enabled, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                rule_id,
                name,
                description,
                category.value,
                resource_type,
                condition,
                severity,
                remediation_steps,
                1 if auto_remediate else 0,
                now.isoformat(),
            )
        )
        conn.commit()
    
    return rule


async def check_compliance(
    data: Any,
    resource_type: str,
    resource_id: str | None = None,
    rule_ids: list[str] | None = None,
) -> list[ComplianceResult]:
    """
    Protocol Conformitas: check data compliance against rules.
    """
    results: list[ComplianceResult] = []
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        # Get applicable rules
        if rule_ids:
            placeholders = ",".join("?" * len(rule_ids))
            rules = conn.execute(
                f"SELECT * FROM compliance_rules WHERE rule_id IN ({placeholders}) AND enabled = 1",
                rule_ids
            ).fetchall()
        else:
            rules = conn.execute(
                "SELECT * FROM compliance_rules WHERE resource_type = ? AND enabled = 1",
                (resource_type,)
            ).fetchall()
        
        for rule in rules:
            check_id = str(uuid.uuid4())
            condition = rule["condition"]
            
            # Parse condition (format: "validator_name:params_json")
            if ":" in condition:
                validator_name, params_str = condition.split(":", 1)
                params = json.loads(params_str)
            else:
                validator_name = condition
                params = {}
            
            # Run validator
            if validator_name in _rule_validators:
                try:
                    status = _rule_validators[validator_name](data, params)
                    message = f"Compliance check: {rule['name']}"
                except Exception as e:
                    status = ComplianceStatus.ERROR
                    message = str(e)
            else:
                status = ComplianceStatus.NOT_APPLICABLE
                message = f"Unknown validator: {validator_name}"
            
            result = ComplianceResult(
                check_id=check_id,
                rule_id=rule["rule_id"],
                rule_name=rule["name"],
                resource_type=resource_type,
                resource_id=resource_id,
                status=status,
                message=message,
                remediation_steps=rule["remediation"],
                checked_at=now,
            )
            results.append(result)
            
            # Store result
            conn.execute(
                """
                INSERT INTO compliance_checks (
                    check_id, rule_id, rule_name, resource_type, resource_id, status, message, checked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    check_id,
                    rule["rule_id"],
                    rule["name"],
                    resource_type,
                    resource_id,
                    status.value,
                    message,
                    now.isoformat(),
                )
            )
        
        conn.commit()
    
    return results


async def get_compliance_summary(
    resource_type: str | None = None,
    hours: int = 24,
) -> dict[str, int]:
    """Get compliance check summary."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    with _db() as conn:
        query = "SELECT status, COUNT(*) as count FROM compliance_checks WHERE checked_at >= ?"
        params: list[Any] = [cutoff.isoformat()]
        
        if resource_type:
            query += " AND resource_type = ?"
            params.append(resource_type)
        
        query += " GROUP BY status"
        
        rows = conn.execute(query, params).fetchall()
        return {row["status"]: row["count"] for row in rows}
