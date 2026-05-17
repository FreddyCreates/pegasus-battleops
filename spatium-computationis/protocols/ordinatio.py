"""
Protocol III: Ordinatio  ≡
Meaning: information is sorted into the correct region.

Classifies a compressed IntelligenceObject and produces a RoutingDecision
that names the target agent and action.
"""

from __future__ import annotations

import json

from openai import AsyncOpenAI

from ..schemas import ActionType, IntelligenceObject, Region, RoutingDecision

_client: AsyncOpenAI | None = None

def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client

_ROUTING_SYSTEM_PROMPT = """\
You are the Ordinatio module of Spatium Computationis (≡).

Given a compressed intelligence object, decide:
1. Which agent should handle it.
2. What action should be taken.

Available agents:
  auctor_operis        — master orchestration (ambiguous / multi-region input)
  estimator_mobilia    — furniture pricing and budgets
  estimator_laboris    — labor estimating and install scope
  inspector_campi      — field conditions, punch lists, damage
  scriptor_documentorum — document generation
  interpres_designii   — designer-to-installer translation
  custos_memoriae      — project memory and history

Available actions:
  generate_bid | create_estimate | request_missing_info | flag_risk |
  create_change_order | update_punch_list | summarize_field_issue |
  prepare_install_packet | create_client_document | route_to_agent |
  update_memory

Return JSON:
{
  "target_region": "<region>",
  "target_agent": "<agent>",
  "action": "<action>",
  "priority": <1-5, 1=urgent>,
  "reasoning": "<one sentence>"
}

Return only valid JSON. No markdown fences.
"""


async def route(obj: IntelligenceObject) -> RoutingDecision:
    """
    Protocol Ordinatio: route an IntelligenceObject to the correct agent.
    """
    payload = {
        "glyph": obj.glyph,
        "region": obj.region.value,
        "summary": obj.summary,
        "missing_fields": obj.missing_fields,
        "confidence": obj.confidence,
    }

    response = await _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _ROUTING_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    data = json.loads(response.choices[0].message.content)

    try:
        region = Region(data.get("target_region", obj.region.value))
    except ValueError:
        region = obj.region

    try:
        action = ActionType(data.get("action", "route_to_agent"))
    except ValueError:
        action = ActionType.ROUTE_TO_AGENT

    return RoutingDecision(
        object_id=obj.object_id,
        target_region=region,
        target_agent=data.get("target_agent", "auctor_operis"),
        action=action,
        priority=int(data.get("priority", 3)),
        reasoning=data.get("reasoning", ""),
    )
