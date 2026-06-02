"""
Agent: Inspector Campi  ⟁✓
Role: Field condition and punch-list agent.

Takes field photos, notes, and site updates; outputs a PunchList with
categorised open items, damage flags, and completion status.
"""

from __future__ import annotations

import json
import uuid

from ...integrations.nova_sovereign import NovaSovereignClient, get_nova_client

from ...schemas import IntelligenceObject, PunchItem, PunchList

_client: NovaSovereignClient | None = None

def _get_client() -> NovaSovereignClient:
    global _client
    if _client is None:
        _client = get_nova_client()
    return _client

_SYSTEM_PROMPT = """\
You are Inspector Campi (⟁✓), the field intelligence of Spatium Computationis.

Given field notes, photos descriptions, or site reports, produce a structured \
punch list.

Each punch item must have:
- A clear, actionable description
- The room or location
- Status (open | complete | pending-approval)
- Responsible party if determinable
- Photo reference if mentioned
- Notes

Return JSON:
{
  "items": [
    {
      "item_id": "<unique short id e.g. P001>",
      "room": "<room or null>",
      "description": "<required>",
      "status": "<open|complete|pending-approval>",
      "responsible_party": "<contractor/designer/vendor or null>",
      "photo_ref": "<photo id/name or null>",
      "notes": "<additional notes or null>"
    }
  ],
  "open_count": <int>,
  "complete_count": <int>
}

Return only valid JSON. No markdown fences.
"""


async def run(obj: IntelligenceObject) -> PunchList:
    """Inspector Campi: produce a PunchList from field intelligence."""
    payload = {
        "summary": obj.summary,
        "entities": obj.extracted_entities,
        "field_conditions": obj.extracted_entities.get("field_conditions", []),
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

    items = [PunchItem(**item) for item in data.get("items", [])]

    return PunchList(
        project_id=obj.project_id,
        items=items,
        open_count=int(data.get("open_count", len(items))),
        complete_count=int(data.get("complete_count", 0)),
    )
