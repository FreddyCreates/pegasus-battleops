"""
Agent: Interpres Designii  ✦⇄⚒
Role: Designer-to-field translation agent.

Converts design-language input (furniture schedules, finish selections,
room layouts, designer notes) into field-ready installer instructions
grouped by room and sequenced for logical install order.
"""

from __future__ import annotations

import json

from openai import AsyncOpenAI

from ...schemas import IntelligenceObject, InstallPacket, InstallerInstruction

_client: AsyncOpenAI | None = None

def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client

_SYSTEM_PROMPT = """\
You are Interpres Designii (✦⇄⚒), the designer-to-field translation \
intelligence of Spatium Computationis.

Your job: convert designer intent into clear, actionable installer instructions.

Rules:
- Use plain, direct language that a field installer can act on immediately.
- Group instructions by room.
- Sequence instructions in logical install order (larger pieces first, then fills).
- Flag any items where design intent is unclear or incomplete.
- Include warnings for fragile items, oversized pieces, or access issues.

Return JSON:
{
  "project_name": "<project name or null>",
  "instructions": [
    {
      "room": "<room name>",
      "sequence": <int, 1-based>,
      "instruction": "<clear installer instruction>",
      "items_involved": ["<item description>"],
      "warnings": ["<warning if any>"]
    }
  ],
  "site_notes": ["<general site note>"],
  "access_notes": ["<elevator, loading dock, floor protection notes>"]
}

Return only valid JSON. No markdown fences.
"""


async def run(obj: IntelligenceObject) -> InstallPacket:
    """Interpres Designii: convert design intelligence into an InstallPacket."""
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

    instructions = [
        InstallerInstruction(**inst) for inst in data.get("instructions", [])
    ]

    return InstallPacket(
        project_id=obj.project_id,
        project_name=data.get("project_name"),
        instructions=instructions,
        site_notes=data.get("site_notes", []),
        access_notes=data.get("access_notes", []),
    )
