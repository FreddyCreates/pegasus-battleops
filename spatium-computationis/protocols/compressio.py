"""
Protocol II: Compressio  ⌬
Meaning: raw information becomes compressed operational intelligence.

Converts a ProjectInput into an IntelligenceObject — a glyph-tagged,
region-classified, summarised unit of meaning that the rest of the
system can route and act on.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from ..integrations.nova_sovereign import NovaSovereignClient, get_nova_client

from ..schemas import IntelligenceObject, ProjectInput, Region
from ..glyphs.glyph_map import REGION_GLYPHS

_client: NovaSovereignClient | None = None

def _get_client() -> NovaSovereignClient:
    global _client
    if _client is None:
        _client = get_nova_client()
    return _client

_COMPRESSION_SYSTEM_PROMPT = """\
You are the Compressio module of Spatium Computationis (⌬).

Your job: given extracted project data, produce a single compressed \
intelligence object that captures the essential operational meaning.

Return a JSON object:
{
  "glyph": "<primary glyph from: ✦ ◈ ⚒ ⟁ ▣ ⇄ ◉ ◈$ ⚒$ ⟁✓ ▣✎ ✦⇄⚒>",
  "region": "<one of: regio_designii | regio_mobilia | regio_laboris | regio_campi | regio_documentorum | regio_contractus | memory | core>",
  "summary": "<one sentence: what this input means operationally>",
  "extracted_entities": {
    "<any key domain entities as key-value pairs>"
  },
  "missing_fields": ["<list of information that is clearly missing but needed>"],
  "confidence": <float 0.0-1.0>
}

Glyph selection guide:
  ✦ = designer intent (furniture schedules, finish selections, plans)
  ◈$ = furniture pricing / budget
  ⚒$ = labor pricing / install scope
  ⟁✓ = field conditions, punch items, site photos, damage
  ▣✎ = explicit request to generate a document
  ✦⇄⚒ = designer-to-installer translation needed
  ◉ = project history / memory update
  ⌬ = general / ambiguous input

Return only valid JSON. No markdown fences.
"""


async def compress(project_input: ProjectInput) -> IntelligenceObject:
    """
    Protocol Compressio: convert a ProjectInput into an IntelligenceObject.
    """
    payload = {
        "input_type": project_input.input_type.value,
        "extracted_text": project_input.extracted_text[:3000],
        "extracted_data": project_input.extracted_data,
    }

    response = await _get_client().chat.completions.create(
        model="sovereign",
        messages=[
            {"role": "system", "content": _COMPRESSION_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    data = json.loads(response.choices[0].message.content)

    region_str = data.get("region", "core")
    try:
        region = Region(region_str)
    except ValueError:
        region = Region.CORE

    return IntelligenceObject(
        object_id=str(uuid.uuid4()),
        project_id=project_input.project_id,
        glyph=data.get("glyph", "⌬"),
        region=region,
        summary=data.get("summary", ""),
        extracted_entities=data.get("extracted_entities", {}),
        missing_fields=data.get("missing_fields", []),
        confidence=float(data.get("confidence", 1.0)),
        source_input_id=project_input.input_id,
    )
