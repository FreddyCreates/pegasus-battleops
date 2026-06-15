"""
ALPHA MEDINA Skill Registration
Register all 5 foundation skills with the agent scaffold registry.
"""

from __future__ import annotations

from spatium_computationis.scaffolds.base import (
    AgentCapability,
    AgentConfig,
    CapabilityType,
    register_agent,
)


def register_all_medina_skills() -> None:
    """Register all ALPHA MEDINA foundation skills."""
    
    # 1. Medina Operating System
    register_agent(
        AgentConfig(
            agent_name="medina-operating-system",
            agent_class="MedinaOperatingSystem",
            version="1.0.0",
            glyph="🧠",
            description="Core cognitive operating framework with multi-layer processing: perception, reasoning, synthesis, output, and state tracking.",
            primary_region="core",
            capabilities=[
                AgentCapability(
                    capability_id="cap_medina_process",
                    capability_type=CapabilityType.ANALYSIS,
                    name="Full Processing",
                    description="Process input through full cognitive framework (perception → reasoning → synthesis → output → state tracking)",
                    input_types=["text"],
                    output_types=["json"],
                    quality_score=0.95,
                    reliability_score=0.90,
                ),
                AgentCapability(
                    capability_id="cap_medina_perceive",
                    capability_type=CapabilityType.ANALYSIS,
                    name="Perception Layer",
                    description="Strip noise, identify signal",
                    input_types=["text"],
                    output_types=["json"],
                    quality_score=0.92,
                    reliability_score=0.88,
                ),
                AgentCapability(
                    capability_id="cap_medina_synthesize",
                    capability_type=CapabilityType.GENERATION,
                    name="Synthesis Layer",
                    description="Produce actionable output from input",
                    input_types=["text"],
                    output_types=["json"],
                    quality_score=0.93,
                    reliability_score=0.89,
                ),
            ],
            requires_nova_sovereign=True,
        )
    )
    
    # 2. Anti-Drift Reviewer
    register_agent(
        AgentConfig(
            agent_name="anti-drift-reviewer",
            agent_class="AntiDriftReviewer",
            version="1.0.0",
            glyph="🔍",
            description="Audits outputs for depth drift, doctrine drift, structure drift, red-team weakness, and state/context loss.",
            primary_region="core",
            capabilities=[
                AgentCapability(
                    capability_id="cap_drift_audit",
                    capability_type=CapabilityType.ANALYSIS,
                    name="Full Drift Audit",
                    description="Check for all 5 drift types: depth, doctrine, structure, red-team, state/context",
                    input_types=["text"],
                    output_types=["json"],
                    quality_score=0.94,
                    reliability_score=0.91,
                ),
                AgentCapability(
                    capability_id="cap_drift_comparative",
                    capability_type=CapabilityType.ANALYSIS,
                    name="Comparative Audit",
                    description="Compare current content against baseline to detect drift over time",
                    input_types=["text", "text"],
                    output_types=["json"],
                    quality_score=0.92,
                    reliability_score=0.89,
                ),
                AgentCapability(
                    capability_id="cap_drift_quick",
                    capability_type=CapabilityType.DECISION,
                    name="Quick Check",
                    description="Quick pass/warn/fail verdict",
                    input_types=["text"],
                    output_types=["json"],
                    quality_score=0.90,
                    reliability_score=0.87,
                ),
            ],
            requires_nova_sovereign=True,
        )
    )
    
    # 3. Doctrine Synthesizer
    register_agent(
        AgentConfig(
            agent_name="doctrine-synthesizer",
            agent_class="DoctrineSynthesizer",
            version="1.0.0",
            glyph="⚗️",
            description="Converts raw ideas into structured doctrine: laws, principles, frameworks, maps, and taxonomies.",
            primary_region="core",
            capabilities=[
                AgentCapability(
                    capability_id="cap_doctrine_synthesize",
                    capability_type=CapabilityType.GENERATION,
                    name="Doctrine Synthesis",
                    description="Convert raw ideas into structured doctrine hierarchy",
                    input_types=["text"],
                    output_types=["json"],
                    quality_score=0.93,
                    reliability_score=0.90,
                ),
                AgentCapability(
                    capability_id="cap_doctrine_laws",
                    capability_type=CapabilityType.ANALYSIS,
                    name="Law Extraction",
                    description="Extract only immutable laws from raw material",
                    input_types=["text"],
                    output_types=["json"],
                    quality_score=0.91,
                    reliability_score=0.88,
                ),
                AgentCapability(
                    capability_id="cap_doctrine_framework",
                    capability_type=CapabilityType.GENERATION,
                    name="Framework Synthesis",
                    description="Synthesize framework maps from raw input",
                    input_types=["text"],
                    output_types=["json"],
                    quality_score=0.92,
                    reliability_score=0.89,
                ),
            ],
            requires_nova_sovereign=True,
        )
    )
    
    # 4. Mission Roadmap Orchestrator
    register_agent(
        AgentConfig(
            agent_name="mission-roadmap-orchestrator",
            agent_class="MissionRoadmapOrchestrator",
            version="1.0.0",
            glyph="🗺️",
            description="Turns any project into roadmap with phases, gates, branches, risks, dependencies, and compounding execution path.",
            primary_region="core",
            capabilities=[
                AgentCapability(
                    capability_id="cap_roadmap_generate",
                    capability_type=CapabilityType.GENERATION,
                    name="Roadmap Generation",
                    description="Generate structured roadmap from project description",
                    input_types=["text"],
                    output_types=["json"],
                    quality_score=0.94,
                    reliability_score=0.91,
                ),
                AgentCapability(
                    capability_id="cap_roadmap_update",
                    capability_type=CapabilityType.TRANSFORMATION,
                    name="Roadmap Update",
                    description="Update existing roadmap with new status or changes",
                    input_types=["json", "text"],
                    output_types=["json"],
                    quality_score=0.91,
                    reliability_score=0.88,
                ),
                AgentCapability(
                    capability_id="cap_roadmap_actions",
                    capability_type=CapabilityType.ANALYSIS,
                    name="Next Actions",
                    description="Extract immediate next actions from project",
                    input_types=["text"],
                    output_types=["json"],
                    quality_score=0.90,
                    reliability_score=0.87,
                ),
            ],
            requires_nova_sovereign=True,
        )
    )
    
    # 5. Resource Hub Organizer
    register_agent(
        AgentConfig(
            agent_name="resource-hub-organizer",
            agent_class="ResourceHubOrganizer",
            version="1.0.0",
            glyph="📂",
            description="Organizes ideas into topics, subtopics, collections, and release paths.",
            primary_region="core",
            capabilities=[
                AgentCapability(
                    capability_id="cap_hub_organize",
                    capability_type=CapabilityType.TRANSFORMATION,
                    name="Organization",
                    description="Organize material into structured resource hierarchy",
                    input_types=["text"],
                    output_types=["json"],
                    quality_score=0.93,
                    reliability_score=0.90,
                ),
                AgentCapability(
                    capability_id="cap_hub_release",
                    capability_type=CapabilityType.GENERATION,
                    name="Release Path",
                    description="Generate release path for organized material",
                    input_types=["json"],
                    output_types=["json"],
                    quality_score=0.91,
                    reliability_score=0.88,
                ),
                AgentCapability(
                    capability_id="cap_hub_collections",
                    capability_type=CapabilityType.ANALYSIS,
                    name="Collection Suggestions",
                    description="Suggest collections for material",
                    input_types=["text"],
                    output_types=["json"],
                    quality_score=0.90,
                    reliability_score=0.87,
                ),
            ],
            requires_nova_sovereign=True,
        )
    )


if __name__ == "__main__":
    register_all_medina_skills()
    print("✓ All ALPHA MEDINA skills registered successfully")
