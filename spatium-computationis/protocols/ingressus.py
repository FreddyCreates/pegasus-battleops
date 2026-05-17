"""
Protocol I: Ingressus  →⌬
Meaning: information enters the activated computing space.

Accepts any input type (PDF, Excel, email, photo, voice, text, field note,
drawing, quote, handwritten scan) and normalises it into a ProjectInput
object that the rest of the system can process.

The LLM is used to extract structured meaning from unstructured content.
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from ..schemas import InputType, ProjectInput, RawInput

_client: AsyncOpenAI | None = None

def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client


# ---------------------------------------------------------------------------
# System prompt — extraction
# ---------------------------------------------------------------------------

_EXTRACTION_SYSTEM_PROMPT = """\
You are the Ingressus module of Spatium Computationis (⌬), the activated \
computing space for furniture, interiors, and field-installation projects.

Your job: extract all structured information from the raw input provided and \
return a JSON object with the following keys:

{
  "extracted_text": "<clean plain-text rendering of the content>",
  "extracted_data": {
    "project_name": "<if found>",
    "client": "<if found>",
    "rooms": ["<list of rooms mentioned>"],
    "furniture_items": [
      {
        "tag": "<product tag if any>",
        "manufacturer": "<brand>",
        "model": "<model number>",
        "description": "<item description>",
        "quantity": <int>,
        "finish": "<finish if mentioned>",
        "room": "<room if mentioned>"
      }
    ],
    "labor_scope": ["<list of labor tasks mentioned>"],
    "field_conditions": ["<list of site conditions, issues, damage>"],
    "dates": {"<label>": "<date>"},
    "contacts": [{"name": "<name>", "role": "<role>", "email": "<email>"}],
    "missing_info": ["<list of information that seems to be missing>"],
    "notes": "<any other relevant notes>"
  }
}

Return only valid JSON. Do not include markdown fences.
"""


async def _extract_from_text(raw_text: str, input_type: InputType) -> dict[str, Any]:
    """Use the LLM to extract structured data from text content."""
    response = await _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Input type: {input_type.value}\n\nContent:\n{raw_text}",
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    import json

    return json.loads(response.choices[0].message.content)


async def _extract_from_image(base64_image: str, input_type: InputType) -> dict[str, Any]:
    """Use GPT-4o vision to extract structured data from an image."""
    import json

    response = await _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Input type: {input_type.value}. Extract all project information from this image.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def process(raw: RawInput) -> ProjectInput:
    """
    Protocol Ingressus: normalize a RawInput into a ProjectInput.

    Dispatches to text or vision extraction based on input type.
    """
    input_id = str(uuid.uuid4())

    if raw.input_type == InputType.PHOTO:
        # content must be base64-encoded image bytes
        extracted = await _extract_from_image(raw.content, raw.input_type)
    else:
        extracted = await _extract_from_text(raw.content, raw.input_type)

    return ProjectInput(
        input_id=input_id,
        project_id=raw.project_id,
        input_type=raw.input_type,
        raw_content=raw.content,
        extracted_text=extracted.get("extracted_text", raw.content),
        extracted_data=extracted.get("extracted_data", {}),
        submitted_by=raw.submitted_by,
        submitted_at=raw.submitted_at,
    )
