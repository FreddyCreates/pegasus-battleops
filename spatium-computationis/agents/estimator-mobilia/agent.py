"""
Agent: Estimator Mobilia  ◈$
Role: Furniture pricing and budget agent.

Takes furniture schedules and vendor quotes; outputs a priced FurnitureBudget
with per-item pricing, freight assumptions, and a list of missing information.
"""

from __future__ import annotations

import json
import uuid

from ...integrations.nova_sovereign import NovaSovereignClient, get_nova_client

from ...schemas import FurnitureBudget, FurnitureLineItem, IntelligenceObject

_client: NovaSovereignClient | None = None

def _get_client() -> NovaSovereignClient:
    global _client
    if _client is None:
        _client = get_nova_client()
    return _client

_SYSTEM_PROMPT = """\
You are Estimator Mobilia (◈$), the furniture pricing intelligence of \
Spatium Computationis.

Given extracted furniture data, produce a detailed furniture budget.

Rules:
- If unit price is unknown, estimate based on typical commercial FF&E pricing.
- Add a freight line at 8–12% of product subtotal unless otherwise noted.
- Flag any items where information is clearly missing.
- Prefer conservative (higher) price estimates when uncertain.

Return JSON exactly matching this structure:
{
  "items": [
    {
      "tag": "<tag or null>",
      "manufacturer": "<brand or null>",
      "model": "<model or null>",
      "description": "<required>",
      "quantity": <int>,
      "unit_price": <float or null>,
      "total_price": <float or null>,
      "room": "<room or null>",
      "finish": "<finish or null>",
      "lead_time": "<lead time or null>",
      "freight_assumption": "<freight note or null>",
      "notes": "<notes or null>"
    }
  ],
  "subtotal": <float>,
  "freight_estimate": <float>,
  "grand_total": <float>,
  "assumptions": ["<assumption>"],
  "missing_info": ["<missing item>"]
}

Return only valid JSON. No markdown fences.
"""


async def run(obj: IntelligenceObject) -> FurnitureBudget:
    """Estimator Mobilia: produce a FurnitureBudget from an IntelligenceObject."""
    payload = {
        "summary": obj.summary,
        "entities": obj.extracted_entities,
        "missing": obj.missing_fields,
    }

    response = await _get_client().chat.completions.create(
        model="sovereign",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    data = json.loads(response.choices[0].message.content)

    items = [FurnitureLineItem(**item) for item in data.get("items", [])]

    return FurnitureBudget(
        project_id=obj.project_id,
        items=items,
        subtotal=float(data.get("subtotal", 0)),
        freight_estimate=float(data.get("freight_estimate", 0)),
        grand_total=float(data.get("grand_total", 0)),
        assumptions=data.get("assumptions", []),
        missing_info=data.get("missing_info", []),
    )
