"""
Open Data Policy — Openness & Transparency Governance  ⚖▣

Requirements for system transparency, audit accessibility,
data openness, and public documentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OpenDataRequirement:
    """A single open data policy requirement."""
    requirement_id: str
    title: str
    description: str
    category: str  # "audit" | "documentation" | "data_sharing" | "anonymisation"
    enforcement: str  # "mandatory" | "recommended"


@dataclass
class OpenDataPolicy:
    """
    Open Data Policy for Spatium Computationis.

    Governs:
    - Audit trail accessibility
    - Public documentation requirements
    - Data sharing standards
    - Anonymisation requirements for external data
    - Open-source architecture transparency
    """

    requirements: list[OpenDataRequirement] = field(default_factory=list)

    def __post_init__(self):
        if not self.requirements:
            self.requirements = _default_requirements()

    def get_by_category(self, category: str) -> list[OpenDataRequirement]:
        """Get requirements by category."""
        return [r for r in self.requirements if r.category == category]

    def get_mandatory(self) -> list[OpenDataRequirement]:
        """Get all mandatory requirements."""
        return [r for r in self.requirements if r.enforcement == "mandatory"]


def _default_requirements() -> list[OpenDataRequirement]:
    """Default open data policy requirements."""
    return [
        # Audit
        OpenDataRequirement(
            requirement_id="ODP-A01",
            title="Decision Log Access",
            description=(
                "Agent decision logs must be accessible for audit by authorised "
                "personnel. Logs include routing decisions, confidence scores, "
                "and action outcomes."
            ),
            category="audit",
            enforcement="mandatory",
        ),
        OpenDataRequirement(
            requirement_id="ODP-A02",
            title="Governance Compliance Audit",
            description=(
                "The governance hierarchy compliance checks must be logged and "
                "auditable. Any override or violation must be recorded."
            ),
            category="audit",
            enforcement="mandatory",
        ),
        # Documentation
        OpenDataRequirement(
            requirement_id="ODP-D01",
            title="Public Architecture Documentation",
            description=(
                "System architecture, protocol charters, and governance hierarchy "
                "must be publicly documented in the repository."
            ),
            category="documentation",
            enforcement="mandatory",
        ),
        OpenDataRequirement(
            requirement_id="ODP-D02",
            title="Protocol Charter Openness",
            description=(
                "All protocol charters (Ingressus, Compressio, Ordinatio, Actio, Reductus) "
                "must be documented with their glyph meanings and operational logic."
            ),
            category="documentation",
            enforcement="mandatory",
        ),
        OpenDataRequirement(
            requirement_id="ODP-D03",
            title="Nova Sovereign Integration Documentation",
            description=(
                "The Nova Sovereign protocol integration must be documented, "
                "including the bridge architecture and fallback behaviour."
            ),
            category="documentation",
            enforcement="mandatory",
        ),
        # Data Sharing
        OpenDataRequirement(
            requirement_id="ODP-S01",
            title="Aggregate Data Sharing",
            description=(
                "Aggregate, anonymised operational metrics may be shared for "
                "system improvement. Individual project data requires consent."
            ),
            category="data_sharing",
            enforcement="recommended",
        ),
        # Anonymisation
        OpenDataRequirement(
            requirement_id="ODP-N01",
            title="Field Data Anonymisation",
            description=(
                "Field data (photos, notes, reports) must be anonymised before "
                "any external sharing. Personal identifiers, addresses, and "
                "client names must be redacted."
            ),
            category="anonymisation",
            enforcement="mandatory",
        ),
        OpenDataRequirement(
            requirement_id="ODP-N02",
            title="Estimate Anonymisation",
            description=(
                "Historical estimate data used for pattern analysis must be "
                "anonymised. Client-specific pricing and vendor relationships "
                "must not be exposed."
            ),
            category="anonymisation",
            enforcement="mandatory",
        ),
    ]
