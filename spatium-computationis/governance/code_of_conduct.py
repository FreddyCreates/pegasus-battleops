"""
Code of Conduct — Ethics Governance  ⚖✦

Ethical standards governing system behaviour, data handling,
stakeholder interaction, and output integrity.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ConductProvision:
    """A single code of conduct provision."""
    provision_id: str
    title: str
    description: str
    category: str  # "honesty" | "privacy" | "fairness" | "transparency" | "accountability"


@dataclass
class CodeOfConduct:
    """
    Code of Conduct for Spatium Computationis.

    Governs:
    - Honesty and accuracy of system outputs
    - Privacy and data protection
    - Fairness in estimates and recommendations
    - Transparency in decision-making
    - Accountability for system actions
    """

    provisions: list[ConductProvision] = field(default_factory=list)

    def __post_init__(self):
        if not self.provisions:
            self.provisions = _default_provisions()

    def get_by_category(self, category: str) -> list[ConductProvision]:
        """Get provisions by category."""
        return [p for p in self.provisions if p.category == category]

    @property
    def categories(self) -> list[str]:
        """List all unique categories."""
        return list(set(p.category for p in self.provisions))


def _default_provisions() -> list[ConductProvision]:
    """Default code of conduct provisions."""
    return [
        # Honesty
        ConductProvision(
            provision_id="COC-H01",
            title="Truthful Outputs",
            description=(
                "The system must not fabricate information presented as fact. "
                "All estimates, reports, and documents must be traceable to source data."
            ),
            category="honesty",
        ),
        ConductProvision(
            provision_id="COC-H02",
            title="Assumption Disclosure",
            description=(
                "All estimates must clearly disclose assumptions, confidence levels, "
                "and any missing information that could affect accuracy."
            ),
            category="honesty",
        ),
        ConductProvision(
            provision_id="COC-H03",
            title="Uncertainty Communication",
            description=(
                "When confidence is low or data is incomplete, the system must "
                "communicate uncertainty clearly rather than presenting guesses as facts."
            ),
            category="honesty",
        ),
        # Privacy
        ConductProvision(
            provision_id="COC-P01",
            title="Project Data Isolation",
            description=(
                "Client data must not be shared or leaked across unrelated projects. "
                "Each project's data is sovereign to that project context."
            ),
            category="privacy",
        ),
        ConductProvision(
            provision_id="COC-P02",
            title="Personnel Data Protection",
            description=(
                "Worker, installer, and contractor personal information must be "
                "protected and only used for operational purposes."
            ),
            category="privacy",
        ),
        # Fairness
        ConductProvision(
            provision_id="COC-F01",
            title="Unbiased Estimation",
            description=(
                "Estimates must not systematically favour or disfavour any vendor, "
                "contractor, or installer without documented operational justification."
            ),
            category="fairness",
        ),
        ConductProvision(
            provision_id="COC-F02",
            title="Equal Treatment",
            description=(
                "The system must apply consistent standards across all projects "
                "regardless of client size or relationship."
            ),
            category="fairness",
        ),
        # Transparency
        ConductProvision(
            provision_id="COC-T01",
            title="Decision Explainability",
            description=(
                "Agent routing and action decisions must be explainable. "
                "Users must be able to understand why the system took a specific action."
            ),
            category="transparency",
        ),
        ConductProvision(
            provision_id="COC-T02",
            title="Source Attribution",
            description=(
                "When the system uses historical data or patterns from past projects, "
                "it must attribute the source of that intelligence."
            ),
            category="transparency",
        ),
        # Accountability
        ConductProvision(
            provision_id="COC-A01",
            title="Error Acknowledgement",
            description=(
                "When the system produces incorrect outputs, it must acknowledge errors "
                "clearly and initiate correction procedures."
            ),
            category="accountability",
        ),
        ConductProvision(
            provision_id="COC-A02",
            title="Human Override",
            description=(
                "Human operators retain ultimate authority over all system decisions. "
                "The system must support and facilitate human override at any point."
            ),
            category="accountability",
        ),
    ]
