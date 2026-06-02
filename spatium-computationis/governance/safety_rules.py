"""
Safety Rules & Safety Objectives — Operational Safety Governance  ⚖⛨

Safety constraints with execution-time override authority.
These provisions can halt any system action regardless of other
instrument permissions when safety is at risk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SafetySeverity(str, Enum):
    """Severity level of a safety rule."""
    CRITICAL = "critical"  # Immediate halt required
    HIGH = "high"          # Action blocked, escalation required
    MEDIUM = "medium"      # Warning issued, human review recommended
    LOW = "low"            # Advisory, logged for audit


@dataclass
class SafetyRule:
    """A single safety rule with override authority."""
    rule_id: str
    title: str
    description: str
    severity: SafetySeverity
    domain: str  # "physical" | "financial" | "data" | "operational" | "defense"
    override_authority: bool = True  # Can this rule halt operations?
    action_on_violation: str = "halt"  # "halt" | "block" | "warn" | "log"


@dataclass
class SafetyObjective:
    """A high-level safety objective that safety rules implement."""
    objective_id: str
    title: str
    description: str
    related_rules: list[str] = field(default_factory=list)


@dataclass
class SafetyRules:
    """
    Safety Rules for Spatium Computationis.

    These have OVERRIDE AUTHORITY — they can halt any system action
    regardless of what other governance instruments permit.

    Domains:
    - Physical: jobsite and personnel safety
    - Financial: budget and approval thresholds
    - Data: data integrity and protection
    - Operational: system stability and availability
    - Defense: threat response and quarantine
    """

    rules: list[SafetyRule] = field(default_factory=list)

    def __post_init__(self):
        if not self.rules:
            self.rules = _default_safety_rules()

    def get_by_domain(self, domain: str) -> list[SafetyRule]:
        """Get safety rules by domain."""
        return [r for r in self.rules if r.domain == domain]

    def get_critical(self) -> list[SafetyRule]:
        """Get all critical-severity rules."""
        return [r for r in self.rules if r.severity == SafetySeverity.CRITICAL]

    def check_action(self, action: str, context: dict) -> dict:
        """
        Check if an action violates any safety rules.

        Returns halt/block/warn decision.
        """
        violations = []
        for rule in self.rules:
            if _action_violates_safety(action, rule, context):
                violations.append({
                    "rule_id": rule.rule_id,
                    "title": rule.title,
                    "severity": rule.severity.value,
                    "action_required": rule.action_on_violation,
                })

        if not violations:
            return {"safe": True, "violations": []}

        # Determine overall action
        most_severe = max(violations, key=lambda v: list(SafetySeverity).index(SafetySeverity(v["severity"])))
        return {
            "safe": False,
            "violations": violations,
            "required_action": most_severe["action_required"],
        }


@dataclass
class SafetyObjectives:
    """
    High-level safety objectives that the safety rules implement.

    These express the WHY behind safety rules.
    """

    objectives: list[SafetyObjective] = field(default_factory=list)

    def __post_init__(self):
        if not self.objectives:
            self.objectives = _default_safety_objectives()


def _action_violates_safety(action: str, rule: SafetyRule, context: dict) -> bool:
    """Check if an action violates a specific safety rule."""
    action_lower = action.lower()

    # Domain-specific checks
    if rule.domain == "physical":
        unsafe_terms = ["skip inspection", "bypass safety", "ignore site conditions",
                       "proceed without verification"]
        if any(term in action_lower for term in unsafe_terms):
            return True

    elif rule.domain == "financial":
        threshold = context.get("financial_threshold", 0)
        amount = context.get("amount", 0)
        if amount > threshold > 0 and "approve" in action_lower:
            return True

    elif rule.domain == "data":
        if "delete" in action_lower and "backup" not in action_lower:
            if context.get("critical_data", False):
                return True

    elif rule.domain == "defense":
        if context.get("threat_level") == "critical" and "allow" in action_lower:
            return True

    return False


def _default_safety_rules() -> list[SafetyRule]:
    """Default safety rules."""
    return [
        # Physical safety
        SafetyRule(
            rule_id="SAF-P01",
            title="Site Condition Verification",
            description=(
                "Install plans must not be approved without verified site conditions. "
                "Unverified sites pose physical danger to installation crews."
            ),
            severity=SafetySeverity.CRITICAL,
            domain="physical",
            action_on_violation="halt",
        ),
        SafetyRule(
            rule_id="SAF-P02",
            title="Equipment Safety Verification",
            description=(
                "Install packets must include equipment requirements and safety "
                "considerations for the specific jobsite access conditions."
            ),
            severity=SafetySeverity.HIGH,
            domain="physical",
            action_on_violation="block",
        ),
        SafetyRule(
            rule_id="SAF-P03",
            title="After-Hours Safety Protocol",
            description=(
                "After-hours installation work must include additional safety "
                "provisions and supervisor requirements."
            ),
            severity=SafetySeverity.MEDIUM,
            domain="physical",
            action_on_violation="warn",
        ),
        # Financial safety
        SafetyRule(
            rule_id="SAF-F01",
            title="Budget Threshold Override",
            description=(
                "Financial commitments exceeding authorised thresholds must not "
                "be auto-approved. Human approval is required."
            ),
            severity=SafetySeverity.CRITICAL,
            domain="financial",
            action_on_violation="halt",
        ),
        SafetyRule(
            rule_id="SAF-F02",
            title="Estimate Variance Alert",
            description=(
                "When estimates deviate more than 20% from historical norms, "
                "a variance alert must be issued for human review."
            ),
            severity=SafetySeverity.MEDIUM,
            domain="financial",
            action_on_violation="warn",
        ),
        # Data safety
        SafetyRule(
            rule_id="SAF-D01",
            title="Data Integrity Protection",
            description=(
                "Operations must halt when data integrity is compromised. "
                "No outputs may be generated from corrupted inputs."
            ),
            severity=SafetySeverity.CRITICAL,
            domain="data",
            action_on_violation="halt",
        ),
        SafetyRule(
            rule_id="SAF-D02",
            title="Critical Data Deletion Prevention",
            description=(
                "Critical project data must not be deleted without verified "
                "backup confirmation and human approval."
            ),
            severity=SafetySeverity.CRITICAL,
            domain="data",
            action_on_violation="halt",
        ),
        # Operational safety
        SafetyRule(
            rule_id="SAF-O01",
            title="Cascade Failure Prevention",
            description=(
                "When multiple agents fail consecutively, the system must "
                "enter safe mode rather than continuing degraded operations."
            ),
            severity=SafetySeverity.HIGH,
            domain="operational",
            action_on_violation="block",
        ),
        # Defense safety
        SafetyRule(
            rule_id="SAF-X01",
            title="Hostile Traffic Quarantine",
            description=(
                "Traffic classified as hostile by the defense system must be "
                "quarantined immediately. No exceptions."
            ),
            severity=SafetySeverity.CRITICAL,
            domain="defense",
            action_on_violation="halt",
        ),
        SafetyRule(
            rule_id="SAF-X02",
            title="Shadow Traffic Isolation",
            description=(
                "Shadow-classified traffic must be isolated for analysis. "
                "Must not interact with production data paths."
            ),
            severity=SafetySeverity.HIGH,
            domain="defense",
            action_on_violation="block",
        ),
    ]


def _default_safety_objectives() -> list[SafetyObjective]:
    """Default safety objectives."""
    return [
        SafetyObjective(
            objective_id="OBJ-01",
            title="Zero Harm to Field Personnel",
            description=(
                "The system must never produce outputs that could lead to "
                "physical harm of installation crews, delivery teams, or "
                "any personnel on jobsites."
            ),
            related_rules=["SAF-P01", "SAF-P02", "SAF-P03"],
        ),
        SafetyObjective(
            objective_id="OBJ-02",
            title="Financial Sovereignty",
            description=(
                "The system must protect financial interests by requiring "
                "human approval for significant commitments and alerting "
                "on anomalous estimates."
            ),
            related_rules=["SAF-F01", "SAF-F02"],
        ),
        SafetyObjective(
            objective_id="OBJ-03",
            title="Data Sovereignty",
            description=(
                "Project data must remain sovereign and intact. The system "
                "must prevent data loss, corruption, and unauthorised access."
            ),
            related_rules=["SAF-D01", "SAF-D02"],
        ),
        SafetyObjective(
            objective_id="OBJ-04",
            title="Operational Resilience",
            description=(
                "The system must fail safely, maintaining data integrity "
                "and human override capability even during degraded operations."
            ),
            related_rules=["SAF-O01"],
        ),
        SafetyObjective(
            objective_id="OBJ-05",
            title="Defense Integrity",
            description=(
                "The defense system must act immediately on threats without "
                "waiting for governance review. Safety override authority "
                "applies to all threat responses."
            ),
            related_rules=["SAF-X01", "SAF-X02"],
        ),
    ]
