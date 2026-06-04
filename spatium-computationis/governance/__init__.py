"""
Governance Hierarchy — Spatium Computationis  ⌬⚖

Constitutional, procedural, committee, personnel, ethics, openness,
and safety instruments that govern system operation.

Hierarchy (highest to lowest authority):
  1. Constitutional Instruments  — foundational principles
  2. Rules of Procedure          — procedural governance
  3. Committee Instruments       — committee structure and mandates
  4. Personnel Instruments       — personnel governance
  5. Code of Conduct             — ethics and behaviour
  6. Open Data Policy            — openness and transparency
  7. Safety Rules / Objectives   — operational safety

Source authority: Casa de Medina — Architectos de Architectura Inteligente
Protocol reference: FreddyCreates/Decentralized-Production-NOVA-Protocol
"""

from .rules_of_procedure import RulesOfProcedure
from .code_of_conduct import CodeOfConduct
from .open_data_policy import OpenDataPolicy
from .safety_rules import SafetyRules, SafetyObjectives
from .hierarchy import GovernanceHierarchy
from .research_charter_law import ResearchCharterLaw, ResearchAuthority, ResearchReviewOutcome

__all__ = [
    "RulesOfProcedure",
    "CodeOfConduct",
    "OpenDataPolicy",
    "SafetyRules",
    "SafetyObjectives",
    "GovernanceHierarchy",
    "ResearchCharterLaw",
    "ResearchAuthority",
    "ResearchReviewOutcome",
]
