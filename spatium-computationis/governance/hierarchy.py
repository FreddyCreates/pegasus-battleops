"""
Governance Hierarchy — Authority ordering for Spatium Computationis.

The hierarchy of instruments ensures that higher-level rules always
take precedence. Any agent decision, protocol action, or system output
must respect this ordering.

Authority flows downward:
  Constitutional → Procedural → Committee → Personnel → Ethics → Openness → Safety
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class InstrumentLevel(IntEnum):
    """Authority levels, highest = most authoritative."""
    CONSTITUTIONAL = 7
    PROCEDURAL = 6
    COMMITTEE = 5
    PERSONNEL = 4
    ETHICS = 3
    OPENNESS = 2
    SAFETY = 1  # Safety has override power at execution time


@dataclass
class GovernanceInstrument:
    """A single governance instrument."""
    name: str
    level: InstrumentLevel
    description: str
    provisions: list[str] = field(default_factory=list)
    override_authority: bool = False  # Safety instruments can override lower levels


@dataclass
class GovernanceHierarchy:
    """
    Complete governance hierarchy for the system.

    Provides:
    - Authority ordering and precedence checks
    - Instrument lookup
    - Compliance validation for agent decisions
    """

    instruments: list[GovernanceInstrument] = field(default_factory=list)

    def __post_init__(self):
        if not self.instruments:
            self.instruments = _default_instruments()

    def get_by_level(self, level: InstrumentLevel) -> list[GovernanceInstrument]:
        """Get all instruments at a given authority level."""
        return [i for i in self.instruments if i.level == level]

    def check_compliance(self, action: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Check whether a proposed action complies with the governance hierarchy.

        Returns a compliance report with any violations.
        """
        violations: list[dict[str, str]] = []

        # Safety rules have execution-time override
        for instrument in self.get_by_level(InstrumentLevel.SAFETY):
            if instrument.override_authority:
                for provision in instrument.provisions:
                    if _violates_provision(action, provision, context):
                        violations.append({
                            "instrument": instrument.name,
                            "level": "SAFETY (OVERRIDE)",
                            "provision": provision,
                        })

        # Check all levels from highest to lowest
        for level in sorted(InstrumentLevel, reverse=True):
            for instrument in self.get_by_level(level):
                for provision in instrument.provisions:
                    if _violates_provision(action, provision, context):
                        violations.append({
                            "instrument": instrument.name,
                            "level": level.name,
                            "provision": provision,
                        })

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "checked_instruments": len(self.instruments),
        }

    @property
    def authority_chain(self) -> list[str]:
        """Return instrument names ordered by authority (highest first)."""
        sorted_instruments = sorted(
            self.instruments, key=lambda i: i.level, reverse=True
        )
        return [i.name for i in sorted_instruments]


def _violates_provision(action: str, provision: str, context: dict[str, Any]) -> bool:
    """
    Check if an action violates a specific provision.

    This is a structural check — the Nova Sovereign organism runtime
    performs deeper semantic compliance analysis.
    """
    # Keyword-based structural check
    action_lower = action.lower()
    provision_lower = provision.lower()

    # Safety-critical provisions
    if "must not" in provision_lower or "prohibited" in provision_lower:
        # Extract the prohibited concept
        prohibited_terms = [
            term.strip()
            for term in provision_lower.split("must not")[-1].split(",")
        ] if "must not" in provision_lower else []
        for term in prohibited_terms:
            if term and term in action_lower:
                return True

    return False


def _default_instruments() -> list[GovernanceInstrument]:
    """Build the default governance hierarchy instruments."""
    return [
        GovernanceInstrument(
            name="Constitutional Charter",
            level=InstrumentLevel.CONSTITUTIONAL,
            description=(
                "Foundational principles of Spatium Computationis. "
                "Establishes the system as an activated computing ecosystem "
                "governed by the Nova Sovereign Protocol."
            ),
            provisions=[
                "The system serves the Casa de Medina operational ecosystem",
                "All intelligence flows through Nova Sovereign organisms",
                "No external LLM dependency shall bypass sovereign computation",
                "The φ-derived mathematical primitives are the computational foundation",
            ],
        ),
        GovernanceInstrument(
            name="Rules of Procedure",
            level=InstrumentLevel.PROCEDURAL,
            description=(
                "Procedural governance for system operations, agent routing, "
                "and protocol execution."
            ),
            provisions=[
                "All inputs must traverse the Ingressus → Compressio → Ordinatio → Actio pipeline",
                "Agent routing decisions must be logged and auditable",
                "Field feedback must be processed through Reductus within one operational cycle",
                "Degraded mode must be declared when Nova runtime is unreachable",
            ],
        ),
        GovernanceInstrument(
            name="Committee Instruments",
            level=InstrumentLevel.COMMITTEE,
            description=(
                "Defines committee structures for multi-agent decision-making "
                "and cross-region coordination."
            ),
            provisions=[
                "Multi-region decisions require consensus from affected region agents",
                "Escalation to Auctor Operis when sub-agents disagree",
                "Budget decisions above threshold require Estimator committee review",
            ],
        ),
        GovernanceInstrument(
            name="Personnel Instruments",
            level=InstrumentLevel.PERSONNEL,
            description=(
                "Governance of agent lifecycle, registration, capabilities, "
                "and operational authority."
            ),
            provisions=[
                "All agents must register via scaffold before accepting work",
                "Agent capabilities must be declared and verified",
                "Retired agents must not receive new tasks",
            ],
        ),
        GovernanceInstrument(
            name="Code of Conduct",
            level=InstrumentLevel.ETHICS,
            description=(
                "Ethical standards for system behaviour, data handling, "
                "and stakeholder interaction."
            ),
            provisions=[
                "System outputs must be honest and traceable",
                "Client data must not be shared across unrelated projects",
                "Estimates must disclose assumptions and confidence levels",
                "The system must not fabricate information presented as fact",
            ],
        ),
        GovernanceInstrument(
            name="Open Data Policy",
            level=InstrumentLevel.OPENNESS,
            description=(
                "Transparency and openness requirements for system operations, "
                "audit trails, and data accessibility."
            ),
            provisions=[
                "Agent decision logs must be accessible for audit",
                "Governance hierarchy must be publicly documented",
                "System architecture and protocol charters are open-source",
                "Field data anonymisation must be applied before external sharing",
            ],
        ),
        GovernanceInstrument(
            name="Safety Rules",
            level=InstrumentLevel.SAFETY,
            description=(
                "Operational safety constraints with execution-time override "
                "authority. Safety provisions can halt any action regardless "
                "of other instrument permissions."
            ),
            provisions=[
                "Must not generate outputs that endanger physical safety on jobsites",
                "Must not approve install plans without verified site conditions",
                "Must halt operations when data integrity is compromised",
                "Must not exceed authorized financial thresholds without human approval",
                "Defense system must quarantine hostile traffic immediately",
            ],
            override_authority=True,
        ),
    ]
