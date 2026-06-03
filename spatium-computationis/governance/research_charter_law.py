"""
Research Charter Law — Governance Embedding  ⚖⊛

Embeds the Research Charter Protocol into the governance hierarchy
as a COMMITTEE-level instrument (Authority Level 5).

This law:
1. Establishes research as a governed activity within the ecosystem
2. Defines the legal authority for research charter creation and approval
3. Specifies compliance requirements and enforcement mechanisms
4. Links research governance to Constitutional, Procedural, Ethics,
   and Safety instruments

Authority Chain:
  Constitutional (7) → constrains research scope and sovereignty
  Procedural (6)    → requires audit trails and pipeline compliance
  Committee (5)     → THIS LAW: governs research charter lifecycle
  Ethics (3)        → applies ethical standards to all research
  Safety (1)        → override authority on research activities

Source authority: Casa de Medina — Architectos de Architectura Inteligente
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Research Governance Enums
# ---------------------------------------------------------------------------

class ResearchAuthority(str, Enum):
    """Who can authorize research activities at each level."""
    CONSTITUTIONAL = "constitutional_authority"  # System-level changes
    COMMITTEE = "committee_authority"            # Domain research
    PRINCIPAL = "principal_authority"            # Day-to-day research ops
    DELEGATED = "delegated_authority"            # Agent-level exploration


class ResearchReviewOutcome(str, Enum):
    """Possible outcomes of a research governance review."""
    APPROVED = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    REQUIRES_ESCALATION = "requires_escalation"


# ---------------------------------------------------------------------------
# Research Law Articles
# ---------------------------------------------------------------------------

@dataclass
class LawArticle:
    """A single article within the Research Charter Law."""
    article_id: str
    title: str
    text: str
    enforcement: str           # "mandatory" | "advisory" | "conditional"
    authority_required: ResearchAuthority
    penalties: list[str] = field(default_factory=list)
    related_instruments: list[str] = field(default_factory=list)


@dataclass
class ResearchCharterLaw:
    """
    THE RESEARCH CHARTER LAW

    Instrument Level: COMMITTEE (5)
    Authority: Casa de Medina — Architectos de Architectura Inteligente
    Effective: Upon integration into Spatium Computationis governance

    This law establishes the legal framework for all research activities
    within the Spatium Computationis ecosystem. It is embedded within
    the governance hierarchy and enforceable at runtime.

    ═══════════════════════════════════════════════════════════════════
    PREAMBLE

    WHEREAS the Spatium Computationis ecosystem is a living computational
    organism that must grow, adapt, and evolve through disciplined inquiry;

    WHEREAS research activities carry inherent risks to data integrity,
    operational stability, and system sovereignty;

    WHEREAS the advancement of the ecosystem requires a formalized
    framework that balances innovation with governance;

    NOW THEREFORE, the following articles are enacted as binding law
    within the governance hierarchy of Spatium Computationis.
    ═══════════════════════════════════════════════════════════════════
    """

    articles: list[LawArticle] = field(default_factory=list)

    def __post_init__(self):
        if not self.articles:
            self.articles = _default_articles()

    @property
    def preamble(self) -> str:
        """The legal preamble of this instrument."""
        return (
            "WHEREAS the Spatium Computationis ecosystem is a living "
            "computational organism that must grow, adapt, and evolve "
            "through disciplined inquiry;\n\n"
            "WHEREAS research activities carry inherent risks to data "
            "integrity, operational stability, and system sovereignty;\n\n"
            "WHEREAS the advancement of the ecosystem requires a formalized "
            "framework that balances innovation with governance;\n\n"
            "NOW THEREFORE, the following articles are enacted as binding law "
            "within the governance hierarchy of Spatium Computationis."
        )

    def get_article(self, article_id: str) -> LawArticle | None:
        """Retrieve a specific article by ID."""
        for article in self.articles:
            if article.article_id == article_id:
                return article
        return None

    def get_mandatory_articles(self) -> list[LawArticle]:
        """Get all mandatory articles."""
        return [a for a in self.articles if a.enforcement == "mandatory"]

    def get_articles_by_authority(
        self, authority: ResearchAuthority
    ) -> list[LawArticle]:
        """Get articles requiring a specific authority level."""
        return [a for a in self.articles if a.authority_required == authority]

    def check_research_compliance(
        self, action: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Check whether a research action complies with this law.

        Returns compliance report with any violations and required remedies.
        """
        violations: list[dict[str, Any]] = []

        for article in self.get_mandatory_articles():
            if _violates_article(action, article, context):
                violations.append({
                    "article_id": article.article_id,
                    "title": article.title,
                    "enforcement": article.enforcement,
                    "authority_required": article.authority_required.value,
                    "penalties": article.penalties,
                })

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "articles_checked": len(self.articles),
            "mandatory_articles_checked": len(self.get_mandatory_articles()),
            "required_action": (
                "NONE" if not violations
                else violations[0]["penalties"][0] if violations[0]["penalties"]
                else "HALT_AND_REVIEW"
            ),
        }

    def review_charter_proposal(
        self, charter_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Perform governance review of a proposed research charter.

        Returns review outcome with binding conditions.
        """
        issues: list[str] = []
        conditions: list[str] = []

        # Article RCL-01: Must have defined scope
        if not charter_data.get("abstract") or len(charter_data.get("abstract", "")) < 20:
            issues.append("RCL-01: Research scope (abstract) is insufficient")

        # Article RCL-02: Must have ethical classification
        if not charter_data.get("ethical_classification"):
            issues.append("RCL-02: Ethical classification is missing")

        # Article RCL-03: Must name principal investigator
        if not charter_data.get("principal_investigator"):
            issues.append("RCL-03: No principal investigator designated")

        # Article RCL-04: Must have objectives with measurable criteria
        objectives = charter_data.get("objectives", [])
        if not objectives:
            issues.append("RCL-04: No research objectives defined")
        else:
            for obj in objectives:
                if not obj.get("measurable_criteria"):
                    conditions.append(
                        f"RCL-04: Objective '{obj.get('title', '?')}' "
                        f"needs measurable criteria"
                    )

        # Article RCL-05: High/Restricted ethics require escalation
        ethics_level = charter_data.get("ethical_classification", "low")
        if ethics_level in ("high", "restricted"):
            conditions.append(
                "RCL-05: High/Restricted ethical classification requires "
                "escalation to Constitutional authority"
            )

        # Article RCL-07: Must declare methodology
        if not charter_data.get("methodology"):
            conditions.append("RCL-07: Methodology must be declared before activation")

        # Determine outcome
        if issues:
            outcome = ResearchReviewOutcome.REJECTED
        elif conditions and ethics_level in ("high", "restricted"):
            outcome = ResearchReviewOutcome.REQUIRES_ESCALATION
        elif conditions:
            outcome = ResearchReviewOutcome.APPROVED_WITH_CONDITIONS
        else:
            outcome = ResearchReviewOutcome.APPROVED

        return {
            "outcome": outcome.value,
            "issues": issues,
            "conditions": conditions,
            "reviewable": len(issues) == 0,
            "law_instrument": "Research Charter Law (Committee Level 5)",
        }


# ---------------------------------------------------------------------------
# Article Violation Checking
# ---------------------------------------------------------------------------

def _violates_article(
    action: str, article: LawArticle, context: dict[str, Any]
) -> bool:
    """Check if an action violates a specific law article."""
    action_lower = action.lower()

    # RCL-01: Scope definition
    if article.article_id == "RCL-01":
        if "begin research" in action_lower and not context.get("scope_defined"):
            return True

    # RCL-02: Ethical review
    if article.article_id == "RCL-02":
        if "execute" in action_lower and not context.get("ethics_reviewed"):
            return True

    # RCL-03: Authority chain
    if article.article_id == "RCL-03":
        authority = context.get("authority_level")
        if authority and authority != article.authority_required.value:
            # Check if the provided authority is sufficient
            authority_order = [
                "delegated_authority",
                "principal_authority",
                "committee_authority",
                "constitutional_authority",
            ]
            if authority not in authority_order:
                return True  # Unrecognized authority cannot satisfy requirement
            required_idx = authority_order.index(article.authority_required.value)
            provided_idx = authority_order.index(authority)
            if provided_idx < required_idx:
                return True

    # RCL-06: Sovereignty protection
    if article.article_id == "RCL-06":
        external_deps = ["openai", "anthropic", "cohere", "external llm"]
        if any(dep in action_lower for dep in external_deps):
            return True

    # RCL-08: Safety override
    if article.article_id == "RCL-08":
        if context.get("safety_violation") or context.get("data_integrity_compromised"):
            return True

    return False


# ---------------------------------------------------------------------------
# Default Law Articles
# ---------------------------------------------------------------------------

def _default_articles() -> list[LawArticle]:
    """The complete articles of the Research Charter Law."""
    return [
        LawArticle(
            article_id="RCL-01",
            title="Mandatory Scope Definition",
            text=(
                "No research activity may commence without a formally defined "
                "scope documented in a Research Charter. The charter must include: "
                "(a) research domain, (b) abstract describing the inquiry, "
                "(c) objectives with measurable criteria, and (d) methodology."
            ),
            enforcement="mandatory",
            authority_required=ResearchAuthority.PRINCIPAL,
            penalties=["charter_rejection", "activity_suspension"],
            related_instruments=["Constitutional Charter", "Rules of Procedure"],
        ),
        LawArticle(
            article_id="RCL-02",
            title="Ethical Classification Requirement",
            text=(
                "Every research charter must carry an ethical classification "
                "(minimal, low, moderate, high, restricted). Classification "
                "determines the level of oversight required:\n"
                "  - Minimal/Low: Principal authority sufficient\n"
                "  - Moderate: Committee review required\n"
                "  - High: Full governance review + human approval\n"
                "  - Restricted: Constitutional-level authorization required"
            ),
            enforcement="mandatory",
            authority_required=ResearchAuthority.COMMITTEE,
            penalties=["charter_rejection", "escalation_to_ethics_board"],
            related_instruments=["Code of Conduct", "Safety Rules"],
        ),
        LawArticle(
            article_id="RCL-03",
            title="Authority Chain for Research Approval",
            text=(
                "Research charters must be approved through the governance "
                "authority chain. The required authority level is determined by:\n"
                "  - Domain scope (cross-domain requires higher authority)\n"
                "  - Ethical classification level\n"
                "  - Resource requirements (compute, data, personnel)\n"
                "  - Potential impact on production operations"
            ),
            enforcement="mandatory",
            authority_required=ResearchAuthority.COMMITTEE,
            penalties=["charter_suspension", "authority_review"],
            related_instruments=["Committee Instruments", "Personnel Instruments"],
        ),
        LawArticle(
            article_id="RCL-04",
            title="Measurable Objectives and Deliverables",
            text=(
                "Research charters must define objectives with measurable "
                "success criteria. Each objective must specify:\n"
                "  - What will be measured\n"
                "  - How success is determined\n"
                "  - Expected deliverable type(s)\n"
                "Charters without measurable objectives shall be returned "
                "for revision before governance review."
            ),
            enforcement="mandatory",
            authority_required=ResearchAuthority.PRINCIPAL,
            penalties=["charter_revision_required"],
            related_instruments=["Rules of Procedure"],
        ),
        LawArticle(
            article_id="RCL-05",
            title="Ethical Boundaries and Safety Constraints",
            text=(
                "Research activities must define explicit ethical boundaries "
                "that may not be crossed. These boundaries must reference "
                "applicable Safety Rules. The Safety Rules instrument retains "
                "execution-time OVERRIDE AUTHORITY over all research activities. "
                "A safety violation immediately suspends the affected charter."
            ),
            enforcement="mandatory",
            authority_required=ResearchAuthority.COMMITTEE,
            penalties=["immediate_suspension", "safety_review", "charter_termination"],
            related_instruments=["Safety Rules", "Code of Conduct"],
        ),
        LawArticle(
            article_id="RCL-06",
            title="Sovereignty Protection in Research",
            text=(
                "Research activities must not introduce dependencies on external "
                "intelligence systems that bypass Nova Sovereign computation. "
                "All computational intelligence used in research must flow through "
                "sovereign infrastructure. Comparative studies of external systems "
                "are permitted only in isolated sandboxes with Committee approval."
            ),
            enforcement="mandatory",
            authority_required=ResearchAuthority.COMMITTEE,
            penalties=["charter_termination", "sovereignty_violation_report"],
            related_instruments=["Constitutional Charter"],
        ),
        LawArticle(
            article_id="RCL-07",
            title="Methodology Declaration and Transparency",
            text=(
                "Research methodologies must be declared in the charter and "
                "made accessible for audit. Methodology changes during active "
                "research must be recorded and may trigger re-review. "
                "The Open Data Policy applies to all non-defense research "
                "methodologies and findings."
            ),
            enforcement="mandatory",
            authority_required=ResearchAuthority.PRINCIPAL,
            penalties=["methodology_review_required", "audit_flag"],
            related_instruments=["Open Data Policy", "Rules of Procedure"],
        ),
        LawArticle(
            article_id="RCL-08",
            title="Safety Override Authority",
            text=(
                "The Safety Rules instrument retains full override authority "
                "over research activities. If a research activity triggers "
                "any Safety Rule (SAF-*), the activity is immediately suspended "
                "pending safety review. No governance exemption can override "
                "safety provisions at execution time."
            ),
            enforcement="mandatory",
            authority_required=ResearchAuthority.CONSTITUTIONAL,
            penalties=["immediate_halt", "safety_investigation", "potential_termination"],
            related_instruments=["Safety Rules"],
        ),
        LawArticle(
            article_id="RCL-09",
            title="Feedback and Learning Integration",
            text=(
                "Research outcomes must feed back into the system's learning "
                "loop via the Feedback Protocol (Protocol VI). Completed research "
                "charters must produce at least one registered outcome that "
                "adjusts routing weights or system knowledge."
            ),
            enforcement="mandatory",
            authority_required=ResearchAuthority.PRINCIPAL,
            penalties=["completion_blocked_until_feedback_registered"],
            related_instruments=["Feedback Protocol", "Rules of Procedure"],
        ),
        LawArticle(
            article_id="RCL-10",
            title="Cross-Domain Research Coordination",
            text=(
                "Research spanning multiple domains requires coordination "
                "through the Committee Instruments framework. Each affected "
                "domain must acknowledge the charter and designate a liaison. "
                "Conflicts between domain interests are escalated per the "
                "standard governance escalation path."
            ),
            enforcement="conditional",
            authority_required=ResearchAuthority.COMMITTEE,
            penalties=["coordination_review_required"],
            related_instruments=["Committee Instruments"],
        ),
        LawArticle(
            article_id="RCL-11",
            title="Research Data Governance",
            text=(
                "Data used in research must comply with the Open Data Policy "
                "for transparency and the Safety Rules for integrity. "
                "Research data must be:\n"
                "  (a) Traceable to its source\n"
                "  (b) Protected according to its classification\n"
                "  (c) Anonymised before external sharing\n"
                "  (d) Archived upon charter completion"
            ),
            enforcement="mandatory",
            authority_required=ResearchAuthority.PRINCIPAL,
            penalties=["data_access_revoked", "audit_flag"],
            related_instruments=["Open Data Policy", "Safety Rules"],
        ),
        LawArticle(
            article_id="RCL-12",
            title="Charter Lifecycle Governance",
            text=(
                "Research charters follow a governed lifecycle:\n"
                "  PROPOSED → APPROVED → ACTIVE → REVIEW → COMPLETED\n"
                "Each transition requires appropriate authority:\n"
                "  - PROPOSED→APPROVED: Committee authority\n"
                "  - APPROVED→ACTIVE: Principal authority\n"
                "  - ACTIVE→REVIEW: Automatic at milestone or on demand\n"
                "  - REVIEW→COMPLETED: Committee authority\n"
                "  - Any→SUSPENDED: Safety override (immediate)\n"
                "  - Any→TERMINATED: Constitutional authority"
            ),
            enforcement="mandatory",
            authority_required=ResearchAuthority.COMMITTEE,
            penalties=["lifecycle_violation", "phase_reversion"],
            related_instruments=["Rules of Procedure", "Safety Rules"],
        ),
    ]
