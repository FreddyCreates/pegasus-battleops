"""
Protocol VII: Research Charter  ⊛
Meaning: the system formalizes research intent, scope, ethics, and deliverables.

The Research Charter Protocol governs all research activities within
Spatium Computationis by:
1. Defining research scope and objectives
2. Establishing ethical boundaries and compliance requirements
3. Tracking milestones, deliverables, and outcomes
4. Integrating with governance hierarchy for authority validation
5. Ensuring all research aligns with Constitutional Charter principles

Glyphs:
  ⊛ Research  — formalized inquiry under protocol
  ⊕ Discovery — new knowledge entering the system
  ⊘ Boundary  — ethical/scope constraint applied

Governance Embedding:
  This protocol is embedded in the governance hierarchy at the
  COMMITTEE level (Level 5), requiring oversight from relevant
  domain committees while respecting Constitutional and Procedural
  authority above it.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# External LLM references that violate sovereignty (CONSTITUTIONAL.3)
FORBIDDEN_EXTERNAL_LLMS = ["openai", "anthropic api", "gpt-4", "claude api"]


# ---------------------------------------------------------------------------
# Research Charter Enums
# ---------------------------------------------------------------------------

class ResearchDomain(str, Enum):
    """Domains of research activity within the ecosystem."""
    COMPUTATIONAL = "computational"          # φ-derived math, algorithms
    INTELLIGENCE = "intelligence"            # Nova Sovereign, organism behavior
    OPERATIONAL = "operational"              # Field ops, process optimization
    DEFENSE = "defense"                      # Threat analysis, adversary study
    ARCHITECTURAL = "architectural"          # System design, protocol design
    ECONOMIC = "economic"                    # Estimating, cost modeling
    ECOLOGICAL = "ecological"               # System health, agent evolution


class ResearchPhase(str, Enum):
    """Lifecycle phases of a research charter."""
    PROPOSED = "proposed"                    # Initial proposal, not yet approved
    APPROVED = "approved"                    # Governance-approved, not yet started
    ACTIVE = "active"                        # Currently being executed
    REVIEW = "review"                        # Under peer/committee review
    COMPLETED = "completed"                  # Successfully concluded
    SUSPENDED = "suspended"                  # Temporarily halted
    TERMINATED = "terminated"                # Ended early (violation or obsolescence)


class EthicalClassification(str, Enum):
    """Ethical risk level of a research activity."""
    MINIMAL = "minimal"                      # No ethical concerns
    LOW = "low"                              # Standard oversight required
    MODERATE = "moderate"                    # Ethics committee review required
    HIGH = "high"                            # Full governance review + human approval
    RESTRICTED = "restricted"                # Requires Constitutional-level authorization


class DeliverableType(str, Enum):
    """Types of research deliverables."""
    PROTOCOL = "protocol"                    # New or revised protocol
    ALGORITHM = "algorithm"                  # Mathematical or computational method
    DATASET = "dataset"                      # Curated data for system use
    MODEL = "model"                          # Trained model or decision framework
    REPORT = "report"                        # Written analysis or findings
    TOOL = "tool"                            # Software tool or utility
    GOVERNANCE_AMENDMENT = "governance_amendment"  # Proposed governance change


class ComplianceStatus(str, Enum):
    """Compliance status with governance laws."""
    COMPLIANT = "compliant"
    PENDING_REVIEW = "pending_review"
    NON_COMPLIANT = "non_compliant"
    EXEMPTED = "exempted"                    # Granted exemption by higher authority


# ---------------------------------------------------------------------------
# Research Charter Models
# ---------------------------------------------------------------------------

class ResearchObjective(BaseModel):
    """A single research objective within a charter."""
    objective_id: str
    title: str
    description: str
    measurable_criteria: list[str] = Field(default_factory=list)
    priority: int = Field(ge=1, le=5, default=3)  # 1=highest, 5=lowest
    estimated_effort_hours: float | None = None


class EthicalBoundary(BaseModel):
    """An ethical boundary that must not be crossed."""
    boundary_id: str
    description: str
    classification: EthicalClassification
    enforcement: str  # "hard" = immediate halt, "soft" = warning + review
    related_safety_rules: list[str] = Field(default_factory=list)


class ResearchMilestone(BaseModel):
    """A milestone within a research charter."""
    milestone_id: str
    title: str
    description: str
    target_date: datetime | None = None
    completed_date: datetime | None = None
    deliverables: list[str] = Field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, missed


class ResearchDeliverable(BaseModel):
    """A deliverable produced by research."""
    deliverable_id: str
    title: str
    description: str
    deliverable_type: DeliverableType
    milestone_id: str | None = None
    produced_at: datetime | None = None
    artifact_path: str | None = None
    reviewed: bool = False
    approved: bool = False


class GovernanceLawBinding(BaseModel):
    """Binding between the research charter and governance laws."""
    law_reference: str           # e.g., "CONSTITUTIONAL.3" or "SAF-D01"
    binding_type: str            # "constrains" | "authorizes" | "requires"
    description: str
    enforcement_level: str       # "mandatory" | "advisory"


class ResearchCharter(BaseModel):
    """
    A complete Research Charter — the foundational document governing
    a research initiative within Spatium Computationis.

    Embedded in Governance:
    - Authorized at COMMITTEE level (InstrumentLevel 5)
    - Must comply with all Constitutional provisions
    - Must respect Procedural rules for data handling
    - Safety rules have override authority over research activities
    - Ethics code applies to all research outputs
    """
    # Identity
    charter_id: str
    title: str
    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Domain and Scope
    domain: ResearchDomain
    phase: ResearchPhase = ResearchPhase.PROPOSED
    principal_investigator: str  # Agent or human responsible
    collaborators: list[str] = Field(default_factory=list)

    # Objectives
    abstract: str
    objectives: list[ResearchObjective] = Field(default_factory=list)
    hypothesis: str | None = None
    methodology: str | None = None

    # Ethical Framework
    ethical_classification: EthicalClassification = EthicalClassification.LOW
    ethical_boundaries: list[EthicalBoundary] = Field(default_factory=list)

    # Timeline
    start_date: datetime | None = None
    end_date: datetime | None = None
    milestones: list[ResearchMilestone] = Field(default_factory=list)

    # Deliverables
    deliverables: list[ResearchDeliverable] = Field(default_factory=list)

    # Governance Embedding
    governance_bindings: list[GovernanceLawBinding] = Field(default_factory=list)
    compliance_status: ComplianceStatus = ComplianceStatus.PENDING_REVIEW
    governance_notes: str | None = None

    # Provenance
    nova_sovereign_session: str | None = None  # Nova session that informed this
    parent_charter: str | None = None  # If derived from another charter
    related_protocols: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent / "field" / "research_charters.db"


def _init_research_db() -> None:
    """Initialize the research charter database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_charters (
                charter_id      TEXT PRIMARY KEY,
                title           TEXT NOT NULL,
                version         TEXT DEFAULT '1.0.0',
                domain          TEXT NOT NULL,
                phase           TEXT NOT NULL,
                principal_investigator TEXT NOT NULL,
                collaborators   TEXT,
                abstract        TEXT NOT NULL,
                hypothesis      TEXT,
                methodology     TEXT,
                ethical_classification TEXT NOT NULL,
                compliance_status TEXT NOT NULL,
                governance_notes TEXT,
                charter_data    TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rc_domain ON research_charters(domain)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rc_phase ON research_charters(phase)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rc_pi ON research_charters(principal_investigator)"
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS charter_governance_bindings (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                charter_id      TEXT NOT NULL,
                law_reference   TEXT NOT NULL,
                binding_type    TEXT NOT NULL,
                description     TEXT NOT NULL,
                enforcement_level TEXT NOT NULL,
                FOREIGN KEY (charter_id) REFERENCES research_charters(charter_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cgb_charter ON charter_governance_bindings(charter_id)"
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS charter_milestones (
                milestone_id    TEXT PRIMARY KEY,
                charter_id      TEXT NOT NULL,
                title           TEXT NOT NULL,
                description     TEXT,
                target_date     TEXT,
                completed_date  TEXT,
                status          TEXT DEFAULT 'pending',
                FOREIGN KEY (charter_id) REFERENCES research_charters(charter_id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS charter_deliverables (
                deliverable_id  TEXT PRIMARY KEY,
                charter_id      TEXT NOT NULL,
                title           TEXT NOT NULL,
                description     TEXT,
                deliverable_type TEXT NOT NULL,
                milestone_id    TEXT,
                produced_at     TEXT,
                artifact_path   TEXT,
                reviewed        INTEGER DEFAULT 0,
                approved        INTEGER DEFAULT 0,
                FOREIGN KEY (charter_id) REFERENCES research_charters(charter_id)
            )
            """
        )

        conn.commit()


_init_research_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Charter Lifecycle Operations
# ---------------------------------------------------------------------------

def create_charter(
    title: str,
    domain: ResearchDomain,
    abstract: str,
    principal_investigator: str,
    objectives: list[dict[str, Any]] | None = None,
    hypothesis: str | None = None,
    methodology: str | None = None,
    ethical_classification: EthicalClassification = EthicalClassification.LOW,
    ethical_boundaries: list[dict[str, Any]] | None = None,
    collaborators: list[str] | None = None,
    governance_bindings: list[dict[str, Any]] | None = None,
) -> ResearchCharter:
    """
    Create a new Research Charter.

    The charter is created in PROPOSED phase and must be approved
    through governance review before becoming ACTIVE.
    """
    charter_id = f"RC-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc)

    # Build objectives
    parsed_objectives = []
    if objectives:
        for i, obj in enumerate(objectives):
            parsed_objectives.append(ResearchObjective(
                objective_id=f"{charter_id}-OBJ-{i+1:02d}",
                title=obj.get("title", f"Objective {i+1}"),
                description=obj.get("description", ""),
                measurable_criteria=obj.get("measurable_criteria", []),
                priority=obj.get("priority", 3),
                estimated_effort_hours=obj.get("estimated_effort_hours"),
            ))

    # Build ethical boundaries
    parsed_boundaries = []
    if ethical_boundaries:
        for i, eb in enumerate(ethical_boundaries):
            parsed_boundaries.append(EthicalBoundary(
                boundary_id=f"{charter_id}-ETH-{i+1:02d}",
                description=eb.get("description", ""),
                classification=EthicalClassification(
                    eb.get("classification", "low")
                ),
                enforcement=eb.get("enforcement", "hard"),
                related_safety_rules=eb.get("related_safety_rules", []),
            ))

    # Build governance bindings (default + custom)
    parsed_bindings = _default_governance_bindings(charter_id)
    if governance_bindings:
        for gb in governance_bindings:
            parsed_bindings.append(GovernanceLawBinding(
                law_reference=gb["law_reference"],
                binding_type=gb.get("binding_type", "constrains"),
                description=gb.get("description", ""),
                enforcement_level=gb.get("enforcement_level", "mandatory"),
            ))

    charter = ResearchCharter(
        charter_id=charter_id,
        title=title,
        domain=domain,
        phase=ResearchPhase.PROPOSED,
        principal_investigator=principal_investigator,
        collaborators=collaborators or [],
        abstract=abstract,
        objectives=parsed_objectives,
        hypothesis=hypothesis,
        methodology=methodology,
        ethical_classification=ethical_classification,
        ethical_boundaries=parsed_boundaries,
        governance_bindings=parsed_bindings,
        compliance_status=ComplianceStatus.PENDING_REVIEW,
        created_at=now,
        updated_at=now,
    )

    # Persist
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO research_charters (
                charter_id, title, version, domain, phase,
                principal_investigator, collaborators, abstract,
                hypothesis, methodology, ethical_classification,
                compliance_status, governance_notes, charter_data,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                charter.charter_id, charter.title, charter.version,
                charter.domain.value, charter.phase.value,
                charter.principal_investigator,
                json.dumps(charter.collaborators),
                charter.abstract, charter.hypothesis, charter.methodology,
                charter.ethical_classification.value,
                charter.compliance_status.value,
                charter.governance_notes,
                charter.model_dump_json(),
                now.isoformat(), now.isoformat(),
            )
        )

        # Store governance bindings
        for binding in parsed_bindings:
            conn.execute(
                """
                INSERT INTO charter_governance_bindings (
                    charter_id, law_reference, binding_type,
                    description, enforcement_level
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    charter_id, binding.law_reference,
                    binding.binding_type, binding.description,
                    binding.enforcement_level,
                )
            )

        conn.commit()

    return charter


def approve_charter(charter_id: str, approver: str, notes: str | None = None) -> ResearchCharter:
    """
    Approve a research charter, moving it from PROPOSED to APPROVED.

    Requires COMMITTEE-level authority or higher.
    """
    now = datetime.now(timezone.utc)

    with _db() as conn:
        row = conn.execute(
            "SELECT charter_data FROM research_charters WHERE charter_id = ?",
            (charter_id,)
        ).fetchone()

        if not row:
            raise ValueError(f"Charter {charter_id} not found")

        charter = ResearchCharter.model_validate_json(row["charter_data"])

        if charter.phase != ResearchPhase.PROPOSED:
            raise ValueError(
                f"Charter must be in PROPOSED phase to approve (current: {charter.phase.value})"
            )

        charter.phase = ResearchPhase.APPROVED
        charter.compliance_status = ComplianceStatus.COMPLIANT
        charter.governance_notes = (
            f"Approved by {approver} at {now.isoformat()}"
            + (f". Notes: {notes}" if notes else "")
        )
        charter.updated_at = now

        conn.execute(
            """
            UPDATE research_charters
            SET phase = ?, compliance_status = ?, governance_notes = ?,
                charter_data = ?, updated_at = ?
            WHERE charter_id = ?
            """,
            (
                charter.phase.value, charter.compliance_status.value,
                charter.governance_notes, charter.model_dump_json(),
                now.isoformat(), charter_id,
            )
        )
        conn.commit()

    return charter


def activate_charter(charter_id: str) -> ResearchCharter:
    """Move an APPROVED charter to ACTIVE phase."""
    now = datetime.now(timezone.utc)

    with _db() as conn:
        row = conn.execute(
            "SELECT charter_data FROM research_charters WHERE charter_id = ?",
            (charter_id,)
        ).fetchone()

        if not row:
            raise ValueError(f"Charter {charter_id} not found")

        charter = ResearchCharter.model_validate_json(row["charter_data"])

        if charter.phase != ResearchPhase.APPROVED:
            raise ValueError(
                f"Charter must be APPROVED to activate (current: {charter.phase.value})"
            )

        charter.phase = ResearchPhase.ACTIVE
        charter.start_date = now
        charter.updated_at = now

        conn.execute(
            """
            UPDATE research_charters
            SET phase = ?, charter_data = ?, updated_at = ?
            WHERE charter_id = ?
            """,
            (charter.phase.value, charter.model_dump_json(), now.isoformat(), charter_id)
        )
        conn.commit()

    return charter


def complete_charter(charter_id: str, summary: str | None = None) -> ResearchCharter:
    """Mark a charter as completed."""
    now = datetime.now(timezone.utc)

    with _db() as conn:
        row = conn.execute(
            "SELECT charter_data FROM research_charters WHERE charter_id = ?",
            (charter_id,)
        ).fetchone()

        if not row:
            raise ValueError(f"Charter {charter_id} not found")

        charter = ResearchCharter.model_validate_json(row["charter_data"])

        if charter.phase != ResearchPhase.ACTIVE:
            raise ValueError(
                f"Charter must be ACTIVE to complete (current: {charter.phase.value})"
            )

        charter.phase = ResearchPhase.COMPLETED
        charter.end_date = now
        charter.updated_at = now
        if summary:
            charter.governance_notes = (
                (charter.governance_notes or "") + f"\nCompletion summary: {summary}"
            )

        conn.execute(
            """
            UPDATE research_charters
            SET phase = ?, charter_data = ?, updated_at = ?
            WHERE charter_id = ?
            """,
            (charter.phase.value, charter.model_dump_json(), now.isoformat(), charter_id)
        )
        conn.commit()

    return charter


def suspend_charter(charter_id: str, reason: str) -> ResearchCharter:
    """Suspend a charter (safety override or governance hold)."""
    now = datetime.now(timezone.utc)

    with _db() as conn:
        row = conn.execute(
            "SELECT charter_data FROM research_charters WHERE charter_id = ?",
            (charter_id,)
        ).fetchone()

        if not row:
            raise ValueError(f"Charter {charter_id} not found")

        charter = ResearchCharter.model_validate_json(row["charter_data"])
        charter.phase = ResearchPhase.SUSPENDED
        charter.governance_notes = (
            (charter.governance_notes or "") + f"\nSuspended: {reason} ({now.isoformat()})"
        )
        charter.updated_at = now

        conn.execute(
            """
            UPDATE research_charters
            SET phase = ?, governance_notes = ?, charter_data = ?, updated_at = ?
            WHERE charter_id = ?
            """,
            (
                charter.phase.value, charter.governance_notes,
                charter.model_dump_json(), now.isoformat(), charter_id,
            )
        )
        conn.commit()

    return charter


# ---------------------------------------------------------------------------
# Query Operations
# ---------------------------------------------------------------------------

def get_charter(charter_id: str) -> ResearchCharter | None:
    """Retrieve a charter by ID."""
    with _db() as conn:
        row = conn.execute(
            "SELECT charter_data FROM research_charters WHERE charter_id = ?",
            (charter_id,)
        ).fetchone()

        if not row:
            return None

        return ResearchCharter.model_validate_json(row["charter_data"])


def list_charters(
    domain: ResearchDomain | None = None,
    phase: ResearchPhase | None = None,
    principal_investigator: str | None = None,
) -> list[ResearchCharter]:
    """List charters with optional filters."""
    query = "SELECT charter_data FROM research_charters WHERE 1=1"
    params: list[Any] = []

    if domain:
        query += " AND domain = ?"
        params.append(domain.value)
    if phase:
        query += " AND phase = ?"
        params.append(phase.value)
    if principal_investigator:
        query += " AND principal_investigator = ?"
        params.append(principal_investigator)

    query += " ORDER BY created_at DESC"

    with _db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [
            ResearchCharter.model_validate_json(row["charter_data"])
            for row in rows
        ]


def get_active_charters() -> list[ResearchCharter]:
    """Get all currently active research charters."""
    return list_charters(phase=ResearchPhase.ACTIVE)


# ---------------------------------------------------------------------------
# Governance Integration
# ---------------------------------------------------------------------------

def _default_governance_bindings(charter_id: str) -> list[GovernanceLawBinding]:
    """
    Default governance law bindings for every research charter.

    Every charter is automatically bound to these governance provisions.
    """
    return [
        GovernanceLawBinding(
            law_reference="CONSTITUTIONAL.1",
            binding_type="constrains",
            description=(
                "Research must serve the Casa de Medina operational ecosystem. "
                "Research that does not contribute to operational excellence "
                "or system advancement requires explicit Constitutional exemption."
            ),
            enforcement_level="mandatory",
        ),
        GovernanceLawBinding(
            law_reference="CONSTITUTIONAL.3",
            binding_type="constrains",
            description=(
                "No research activity shall introduce external LLM dependency "
                "that bypasses Nova Sovereign computation. All intelligence "
                "flows through sovereign infrastructure."
            ),
            enforcement_level="mandatory",
        ),
        GovernanceLawBinding(
            law_reference="PROC-001",
            binding_type="requires",
            description=(
                "Research data inputs must traverse the standard pipeline "
                "(Ingressus → Compressio → Ordinatio → Actio) unless "
                "operating in approved direct-agent research mode."
            ),
            enforcement_level="mandatory",
        ),
        GovernanceLawBinding(
            law_reference="PROC-002",
            binding_type="requires",
            description=(
                "All research decisions and findings must be logged with "
                "full audit trail: timestamp, charter_id, decision, reasoning."
            ),
            enforcement_level="mandatory",
        ),
        GovernanceLawBinding(
            law_reference="ETHICS.4",
            binding_type="constrains",
            description=(
                "Research outputs must not fabricate information presented as fact. "
                "All findings must be clearly marked with confidence levels "
                "and methodology transparency."
            ),
            enforcement_level="mandatory",
        ),
        GovernanceLawBinding(
            law_reference="OPENNESS.1",
            binding_type="requires",
            description=(
                "Research decision logs, methodologies, and non-sensitive findings "
                "must be accessible for audit. Open research is the default."
            ),
            enforcement_level="mandatory",
        ),
        GovernanceLawBinding(
            law_reference="OPENNESS.3",
            binding_type="requires",
            description=(
                "Research charter documents and resulting protocols are open-source "
                "unless classified for defense research."
            ),
            enforcement_level="advisory",
        ),
        GovernanceLawBinding(
            law_reference="SAF-D01",
            binding_type="constrains",
            description=(
                "Research must halt when data integrity is compromised. "
                "No research outputs may be generated from corrupted inputs. "
                "Safety override authority applies."
            ),
            enforcement_level="mandatory",
        ),
    ]


def validate_charter_compliance(charter: ResearchCharter) -> dict[str, Any]:
    """
    Validate a charter against its governance bindings.

    Returns compliance report suitable for governance review.
    """
    violations: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    for binding in charter.governance_bindings:
        if binding.enforcement_level == "mandatory":
            # Check structural compliance
            if binding.binding_type == "requires":
                if not _charter_satisfies_requirement(charter, binding):
                    violations.append({
                        "law_reference": binding.law_reference,
                        "description": binding.description,
                        "status": "NOT_SATISFIED",
                    })
            elif binding.binding_type == "constrains":
                if _charter_violates_constraint(charter, binding):
                    violations.append({
                        "law_reference": binding.law_reference,
                        "description": binding.description,
                        "status": "VIOLATED",
                    })
        else:
            # Advisory — log as warning if not met
            if not _charter_satisfies_requirement(charter, binding):
                warnings.append({
                    "law_reference": binding.law_reference,
                    "description": binding.description,
                    "status": "ADVISORY_NOT_MET",
                })

    return {
        "charter_id": charter.charter_id,
        "compliant": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "bindings_checked": len(charter.governance_bindings),
        "recommendation": (
            "APPROVE" if not violations
            else "REJECT — governance violations must be resolved"
        ),
    }


def _charter_satisfies_requirement(
    charter: ResearchCharter, binding: GovernanceLawBinding
) -> bool:
    """Check if a charter structurally satisfies a governance requirement."""
    # PROC-002: audit trail — check that methodology is defined
    if binding.law_reference == "PROC-002":
        return charter.methodology is not None and len(charter.methodology) > 0

    # OPENNESS.1: accessible for audit — charters are stored in DB (always true)
    if binding.law_reference == "OPENNESS.1":
        return True

    # OPENNESS.3: open-source — check domain isn't defense for advisory binding
    if binding.law_reference == "OPENNESS.3":
        return charter.domain != ResearchDomain.DEFENSE

    # PROC-001: pipeline compliance — check related protocols
    if binding.law_reference == "PROC-001":
        return True  # Structural compliance; runtime enforcement by pipeline

    # Default: assume satisfied if we can't structurally check
    return True


def _charter_violates_constraint(
    charter: ResearchCharter, binding: GovernanceLawBinding
) -> bool:
    """Check if a charter violates a governance constraint."""
    # CONSTITUTIONAL.1: must serve operational ecosystem
    if binding.law_reference == "CONSTITUTIONAL.1":
        # Check that objectives exist and abstract isn't empty
        return len(charter.objectives) == 0 or len(charter.abstract) < 10

    # CONSTITUTIONAL.3: no external LLM dependency
    if binding.law_reference == "CONSTITUTIONAL.3":
        # Check methodology doesn't reference external LLMs
        if charter.methodology:
            return any(f in charter.methodology.lower() for f in FORBIDDEN_EXTERNAL_LLMS)
        return False

    # ETHICS.4: no fabrication
    if binding.law_reference == "ETHICS.4":
        # Structural check: must have measurable criteria
        return all(
            len(obj.measurable_criteria) == 0
            for obj in charter.objectives
        ) if charter.objectives else False

    # SAF-D01: data integrity
    if binding.law_reference == "SAF-D01":
        # Always compliant structurally; runtime enforcement by safety rules
        return False

    return False


# ---------------------------------------------------------------------------
# Milestone & Deliverable Management
# ---------------------------------------------------------------------------

def add_milestone(
    charter_id: str,
    title: str,
    description: str,
    target_date: datetime | None = None,
) -> ResearchMilestone:
    """Add a milestone to a charter."""
    milestone_id = f"{charter_id}-MS-{uuid.uuid4().hex[:4].upper()}"

    milestone = ResearchMilestone(
        milestone_id=milestone_id,
        title=title,
        description=description,
        target_date=target_date,
        status="pending",
    )

    with _db() as conn:
        conn.execute(
            """
            INSERT INTO charter_milestones (
                milestone_id, charter_id, title, description,
                target_date, status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                milestone_id, charter_id, title, description,
                target_date.isoformat() if target_date else None,
                "pending",
            )
        )
        conn.commit()

    return milestone


def add_deliverable(
    charter_id: str,
    title: str,
    description: str,
    deliverable_type: DeliverableType,
    milestone_id: str | None = None,
) -> ResearchDeliverable:
    """Register a deliverable for a charter."""
    deliverable_id = f"{charter_id}-DEL-{uuid.uuid4().hex[:4].upper()}"

    deliverable = ResearchDeliverable(
        deliverable_id=deliverable_id,
        title=title,
        description=description,
        deliverable_type=deliverable_type,
        milestone_id=milestone_id,
    )

    with _db() as conn:
        conn.execute(
            """
            INSERT INTO charter_deliverables (
                deliverable_id, charter_id, title, description,
                deliverable_type, milestone_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                deliverable_id, charter_id, title, description,
                deliverable_type.value, milestone_id,
            )
        )
        conn.commit()

    return deliverable
