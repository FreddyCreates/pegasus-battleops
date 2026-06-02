"""
Rules of Procedure — Procedural Governance  ⚖

Defines how the system operates: pipeline execution, agent routing,
decision logging, escalation paths, and operational cycles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProcedureRule:
    """A single procedural rule."""
    rule_id: str
    title: str
    description: str
    enforcement: str  # "mandatory" | "advisory" | "conditional"
    scope: list[str] = field(default_factory=list)  # Which agents/protocols this applies to


@dataclass
class RulesOfProcedure:
    """
    Procedural governance for Spatium Computationis.

    Governs:
    - Pipeline execution order
    - Agent routing and escalation
    - Decision logging requirements
    - Operational cycle timing
    - Error handling procedures
    """

    rules: list[ProcedureRule] = field(default_factory=list)

    def __post_init__(self):
        if not self.rules:
            self.rules = _default_rules()

    def get_rules_for_scope(self, scope: str) -> list[ProcedureRule]:
        """Get all rules applicable to a given scope (agent/protocol name)."""
        return [
            r for r in self.rules
            if not r.scope or scope in r.scope or "all" in r.scope
        ]

    def get_mandatory_rules(self) -> list[ProcedureRule]:
        """Get all mandatory rules."""
        return [r for r in self.rules if r.enforcement == "mandatory"]


def _default_rules() -> list[ProcedureRule]:
    """Default procedural rules."""
    return [
        ProcedureRule(
            rule_id="PROC-001",
            title="Pipeline Integrity",
            description=(
                "All inputs must traverse the full pipeline: "
                "Ingressus → Compressio → Ordinatio → Actio. "
                "No stage may be skipped unless operating in direct-agent mode."
            ),
            enforcement="mandatory",
            scope=["all"],
        ),
        ProcedureRule(
            rule_id="PROC-002",
            title="Decision Audit Trail",
            description=(
                "Every routing decision made by Ordinatio or Auctor Operis "
                "must be logged with: timestamp, input_id, decision, reasoning, "
                "and confidence score."
            ),
            enforcement="mandatory",
            scope=["ordinatio", "auctor_operis"],
        ),
        ProcedureRule(
            rule_id="PROC-003",
            title="Field Feedback Cycle",
            description=(
                "Field updates received via Reductus must be processed within "
                "one operational cycle and cascaded to affected agents."
            ),
            enforcement="mandatory",
            scope=["reductus", "inspector_campi"],
        ),
        ProcedureRule(
            rule_id="PROC-004",
            title="Degraded Mode Declaration",
            description=(
                "When the Nova Sovereign runtime is unreachable, the system must "
                "declare degraded mode, log the event, and restrict operations to "
                "read-only and cached responses."
            ),
            enforcement="mandatory",
            scope=["all"],
        ),
        ProcedureRule(
            rule_id="PROC-005",
            title="Escalation Path",
            description=(
                "When a sub-agent cannot resolve a task or confidence < 0.5, "
                "it must escalate to Auctor Operis with full context."
            ),
            enforcement="mandatory",
            scope=["estimator_mobilia", "estimator_laboris", "inspector_campi",
                   "scriptor_documentorum", "interpres_designii"],
        ),
        ProcedureRule(
            rule_id="PROC-006",
            title="Nova Sovereign Routing",
            description=(
                "All intelligence requests must route through the Nova Sovereign "
                "client. Direct external LLM calls are prohibited."
            ),
            enforcement="mandatory",
            scope=["all"],
        ),
        ProcedureRule(
            rule_id="PROC-007",
            title="Concurrent Task Limits",
            description=(
                "Each agent must respect its scaffold-declared max_concurrent_tasks. "
                "Overflow tasks must queue or escalate."
            ),
            enforcement="mandatory",
            scope=["all"],
        ),
    ]
