"""
Agent: Estimator Laboris  ⚒$
Role: Labor estimating agent.

Takes scope data and converts it into a detailed LaborBid with crew sizing,
schedule assumptions, and per-task line items.
"""

from __future__ import annotations

import json

from openai import AsyncOpenAI

from ...schemas import IntelligenceObject, LaborBid, LaborLineItem

_client: AsyncOpenAI | None = None

def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client

_SYSTEM_PROMPT = """\
You are Estimator Laboris (⚒$), the labor intelligence of Spatium Computationis.

Given furniture scope and site information, produce a detailed labor bid.

Labor task categories to consider:
  - Delivery / unloading
  - Staging / sorting
  - Assembly
  - Placement / installation
  - Trash / carton removal
  - Foreman supervision
  - After-hours premium (if applicable)
  - Equipment (lift gates, dollies, rigging) — note as assumptions

Pricing guidance:
  - Crew member rate: $65–95/hr depending on complexity
  - Foreman rate: $95–125/hr
  - Minimum 4-hour call per crew member
  - Complexity ratings: low | medium | high | extreme

Return JSON exactly matching this structure:
{
  "items": [
    {
      "task": "<task name>",
      "crew_size": <int>,
      "hours": <float>,
      "rate": <float>,
      "total": <float>,
      "notes": "<notes or null>"
    }
  ],
  "subtotal": <float>,
  "complexity_rating": "<low|medium|high|extreme>",
  "crew_total": <int>,
  "schedule_days": <float>,
  "assumptions": ["<assumption>"],
  "exclusions": ["<exclusion>"]
}

Return only valid JSON. No markdown fences.
"""


async def run(obj: IntelligenceObject) -> LaborBid:
    """Estimator Laboris: produce a LaborBid from an IntelligenceObject."""
    payload = {
        "summary": obj.summary,
        "entities": obj.extracted_entities,
        "missing": obj.missing_fields,
    }

    response = await _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    data = json.loads(response.choices[0].message.content)

    items = [LaborLineItem(**item) for item in data.get("items", [])]

    return LaborBid(
        project_id=obj.project_id,
        items=items,
        subtotal=float(data.get("subtotal", 0)),
        complexity_rating=data.get("complexity_rating", "medium"),
        crew_total=int(data.get("crew_total", 2)),
        schedule_days=float(data.get("schedule_days", 1)),
        assumptions=data.get("assumptions", []),
        exclusions=data.get("exclusions", []),
    )
