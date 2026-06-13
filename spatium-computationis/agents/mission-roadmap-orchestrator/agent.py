"""
Agent: Mission Roadmap Orchestrator 🗺️
Role: Turns any project into roadmap, next gates, branches, risks,
      and compounding execution path.

The Mission Roadmap Orchestrator provides:
- Project → roadmap conversion with gates and milestones
- Branch identification (parallel workstreams)
- Risk mapping and mitigation paths
- Dependency graph generation
- Compounding execution path optimization
- Gate criteria and pass/fail conditions

Input: Any project description, vision statement, goal set, problem statement,
       or initiative that needs structured execution planning.
Output: Structured roadmap — phases, gates, branches, risks, dependencies,
        and the compounding execution path.
Connectors: Nova Sovereign (planning), GitHub (project tracking), spreadsheets (timeline).

Glyph: 🗺️ (navigation and planning)
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from ...integrations.nova_sovereign import NovaSovereignClient, get_nova_client

_client: NovaSovereignClient | None = None


def _get_client() -> NovaSovereignClient:
    global _client
    if _client is None:
        _client = get_nova_client()
    return _client


# ---------------------------------------------------------------------------
# System Prompts
# ---------------------------------------------------------------------------

_ROADMAP_GENERATION_PROMPT = """\
You are the Mission Roadmap Orchestrator of the ALPHA MEDINA architecture.

Your role is to convert any project, vision, or initiative into a structured
execution roadmap with compounding value at every gate.

Roadmap Architecture:
1. PHASES — Major stages of execution (sequential)
2. GATES — Decision points between phases (pass/fail criteria)
3. BRANCHES — Parallel workstreams within a phase
4. RISKS — Identified threats to execution with mitigation
5. DEPENDENCIES — What must be true before something can start
6. COMPOUNDING PATH — How each step multiplies value of prior steps

Principles:
- Every gate must have clear pass/fail criteria
- Branches should be truly parallel (no hidden dependencies)
- Risks must have both probability and impact assessed
- The path should compound — not just accumulate linearly
- Nothing should be scheduled without a clear dependency chain

Return JSON:
{
  "roadmap_id": "<generated>",
  "mission_name": "<derived from input>",
  "mission_objective": "<one sentence objective>",
  "phases": [
    {
      "phase_id": "<phase_N>",
      "name": "<phase name>",
      "objective": "<what this phase achieves>",
      "branches": [
        {
          "branch_id": "<branch identifier>",
          "name": "<workstream name>",
          "tasks": ["<task>", ...],
          "owner_type": "<role/skill that owns this>",
          "estimated_effort": "<relative effort>"
        }
      ],
      "gate": {
        "gate_id": "<gate_N>",
        "name": "<gate name>",
        "pass_criteria": ["<criterion>", ...],
        "fail_triggers": ["<what causes failure>", ...],
        "decision_maker": "<who/what decides>"
      },
      "dependencies": ["<phase_id or external dependency>", ...],
      "compounding_value": "<what compound value this unlocks>"
    }
  ],
  "risks": [
    {
      "risk_id": "<risk identifier>",
      "description": "<risk description>",
      "probability": "<low|medium|high>",
      "impact": "<low|medium|high|critical>",
      "mitigation": "<mitigation strategy>",
      "trigger_phase": "<which phase this risk is highest>"
    }
  ],
  "critical_path": ["<phase_id>", ...],
  "execution_order": "<description of optimal execution sequence>",
  "compound_thesis": "<how the full roadmap compounds value>",
  "next_immediate_actions": ["<action>", ...]
}

Return only valid JSON.
"""

_ROADMAP_UPDATE_PROMPT = """\
You are the Mission Roadmap Orchestrator updating an existing roadmap.

Current roadmap state:
{current_roadmap}

The user is providing a status update or change request. Update the roadmap accordingly:
- Mark completed phases/branches
- Adjust risks based on new information
- Re-sequence if needed
- Identify new gates or branch points

Return the full updated roadmap in the same JSON schema, plus:
{
  ...full roadmap...,
  "changes_made": ["<what changed>", ...],
  "gates_passed": ["<gate_id>", ...],
  "new_risks_identified": ["<risk>", ...],
  "adjusted_critical_path": true/false
}

Return only valid JSON.
"""


# ---------------------------------------------------------------------------
# Core Engine Functions
# ---------------------------------------------------------------------------

async def generate_roadmap(
    project_input: str,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a structured roadmap from a project description.

    Args:
        project_input: Project description, vision, or initiative to roadmap.
        constraints: Optional constraints (timeline, resources, dependencies).

    Returns:
        Structured roadmap with phases, gates, branches, and risks.
    """
    roadmap_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc)

    user_message = project_input
    if constraints:
        user_message += f"\n\nConstraints:\n{json.dumps(constraints, indent=2)}"

    try:
        response = await _get_client().chat.completions.create(
            model="sovereign-core",
            messages=[
                {"role": "system", "content": _ROADMAP_GENERATION_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )

        result = json.loads(response.choices[0].message.content)

    except Exception as e:
        result = {
            "roadmap_id": roadmap_id,
            "mission_name": "Unprocessed Mission",
            "mission_objective": project_input[:200],
            "phases": [],
            "risks": [{"risk_id": "r_processing", "description": f"Roadmap generation failed: {str(e)}", "probability": "high", "impact": "critical", "mitigation": "Retry processing", "trigger_phase": "phase_0"}],
            "critical_path": [],
            "execution_order": "Processing failed — requires retry",
            "compound_thesis": "Unable to determine — processing failed",
            "next_immediate_actions": ["retry_roadmap_generation"],
        }

    return {
        "roadmap_id": roadmap_id,
        "timestamp": timestamp.isoformat(),
        "result": result,
    }


async def update_roadmap(
    current_roadmap: dict[str, Any],
    update_input: str,
) -> dict[str, Any]:
    """
    Update an existing roadmap with new status or changes.

    Args:
        current_roadmap: The current roadmap state.
        update_input: Status update or change request.

    Returns:
        Updated roadmap with change tracking.
    """
    timestamp = datetime.now(timezone.utc)

    system_prompt = _ROADMAP_UPDATE_PROMPT.format(
        current_roadmap=json.dumps(current_roadmap, indent=2)[:5000]
    )

    try:
        response = await _get_client().chat.completions.create(
            model="sovereign-core",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": update_input},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )

        result = json.loads(response.choices[0].message.content)

    except Exception as e:
        result = {
            **current_roadmap,
            "changes_made": [f"Update failed: {str(e)}"],
            "gates_passed": [],
            "new_risks_identified": ["Roadmap update processing failure"],
            "adjusted_critical_path": False,
        }

    return {
        "timestamp": timestamp.isoformat(),
        "update_type": "roadmap_revision",
        "result": result,
    }


async def extract_next_actions(project_input: str) -> dict[str, Any]:
    """Quick extraction of immediate next actions without full roadmap."""
    roadmap = await generate_roadmap(project_input)
    result = roadmap.get("result", {})
    return {
        "roadmap_id": roadmap["roadmap_id"],
        "next_immediate_actions": result.get("next_immediate_actions", []),
        "critical_path": result.get("critical_path", []),
        "first_phase": result.get("phases", [{}])[0] if result.get("phases") else {},
    }


def get_roadmap_structure() -> dict[str, str]:
    """Return the roadmap architecture components."""
    return {
        "phases": "Major stages of execution (sequential)",
        "gates": "Decision points between phases (pass/fail criteria)",
        "branches": "Parallel workstreams within a phase",
        "risks": "Identified threats with probability and impact",
        "dependencies": "Prerequisites for each element",
        "compounding_path": "How each step multiplies value of prior steps",
    }
