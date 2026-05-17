"""
Agent: Auctor Operis  ⌬
Role: Prime orchestration agent.

Receives ambiguous or multi-region input, understands full project context,
routes data to sub-agents, and aggregates their outputs into a coherent
project-level response.
"""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from ...schemas import ActionType, IntelligenceObject

_client: AsyncOpenAI | None = None

def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client

_SYSTEM_PROMPT = """\
You are Auctor Operis (⌬), the prime intelligence agent of Spatium Computationis.

You receive compressed project intelligence and must decide:
1. What is the core operational meaning?
2. Which sub-agents need to act (can be multiple)?
3. What is missing?
4. What is the highest-priority next action?

Sub-agents available:
  estimator_mobilia    (◈$) — furniture pricing
  estimator_laboris    (⚒$) — labor estimating
  inspector_campi      (⟁✓) — field conditions and punch lists
  scriptor_documentorum (▣✎) — document generation
  interpres_designii   (✦⇄⚒) — designer-to-installer translation
  custos_memoriae      (◉)   — project memory

Return JSON:
{
  "summary": "<concise operational summary>",
  "agents_needed": ["<agent_name>", ...],
  "next_actions": ["<action>", ...],
  "missing_info": ["<item>", ...],
  "risk_flags": ["<risk>", ...]
}

Return only valid JSON. No markdown fences.
"""


async def run(
    obj: IntelligenceObject,
) -> tuple[dict[str, Any], str, list[ActionType]]:
    """
    Auctor Operis: orchestrate a response to an ambiguous intelligence object.

    Returns (payload_dict, result_summary, next_actions).
    """
    response = await _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "glyph": obj.glyph,
                        "region": obj.region.value,
                        "summary": obj.summary,
                        "entities": obj.extracted_entities,
                        "missing": obj.missing_fields,
                    }
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    data = json.loads(response.choices[0].message.content)

    next_actions: list[ActionType] = []
    for action_str in data.get("next_actions", []):
        try:
            next_actions.append(ActionType(action_str))
        except ValueError:
            pass

    summary = data.get("summary", "Orchestration complete.")
    return data, summary, next_actions
