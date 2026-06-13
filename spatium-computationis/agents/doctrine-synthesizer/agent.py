"""
Agent: Doctrine Synthesizer ⚗️
Role: Converts raw ideas into structured doctrine, maps, laws, principles,
      and publishable frameworks.

The Doctrine Synthesizer provides:
- Raw idea → structured doctrine conversion
- Law and principle extraction
- Framework map generation
- Publishable format output
- Doctrine versioning and evolution tracking

Input: Raw ideas, notes, observations, conversations, unstructured thoughts,
       experience reports, or any intellectual raw material.
Output: Structured doctrine — laws, principles, maps, frameworks, taxonomies,
        and publishable doctrine documents.
Connectors: Nova Sovereign (synthesis), GitHub (version control), document export.

Glyph: ⚗️ (synthesis and transformation)
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

_DOCTRINE_SYNTHESIS_PROMPT = """\
You are the Doctrine Synthesizer of the ALPHA MEDINA architecture.

Your role is to convert raw intellectual material into structured doctrine.
You extract laws, principles, frameworks, maps, and taxonomies from unstructured input.

Doctrine has hierarchy:
1. LAWS — Immutable truths. Things that are always true regardless of context.
2. PRINCIPLES — Operating guidelines derived from laws. Context-dependent application.
3. FRAMEWORKS — Structural models for applying principles. Repeatable patterns.
4. MAPS — Visual/structural representations of relationships between elements.
5. TAXONOMIES — Classification systems for organizing elements within a domain.

When synthesizing, you must:
- Distinguish signal from noise in the raw material
- Identify which level of doctrine hierarchy the ideas belong to
- Structure output for compounding value (each element builds on others)
- Make doctrine actionable — not abstract philosophy but operating intelligence
- Maintain internal consistency within the doctrine body

Return JSON:
{
  "synthesis_id": "<generated>",
  "source_summary": "<what raw material was provided>",
  "doctrine_elements": [
    {
      "element_type": "<law|principle|framework|map|taxonomy>",
      "title": "<concise title>",
      "statement": "<the doctrine element in clear language>",
      "rationale": "<why this is true / why this matters>",
      "dependencies": ["<other elements this depends on>"],
      "applications": ["<where/how to apply this>"],
      "confidence": <0.0-1.0>
    }
  ],
  "framework_map": {
    "name": "<framework name>",
    "layers": ["<layer 1>", "<layer 2>", ...],
    "connections": [{"from": "<element>", "to": "<element>", "relationship": "<type>"}]
  },
  "publishable_summary": "<1-2 paragraph publishable summary of the doctrine>",
  "evolution_notes": "<how this doctrine might evolve or what gaps remain>",
  "next_synthesis_needed": ["<areas that need further synthesis>"]
}

Return only valid JSON.
"""

_DOCTRINE_EXPANSION_PROMPT = """\
You are the Doctrine Synthesizer expanding an existing doctrine element.

Existing doctrine:
{existing_doctrine}

Expand this doctrine by:
1. Deriving sub-principles from the existing laws/principles
2. Identifying corollaries and edge cases
3. Building out the framework map with more connections
4. Adding application examples
5. Identifying potential contradictions or tensions

Return the same JSON schema with expanded elements.

Return only valid JSON.
"""

_LAW_EXTRACTION_PROMPT = """\
You are the Doctrine Synthesizer in LAW EXTRACTION mode.

From the provided raw material, extract only the immutable truths — the LAWS.
Laws are things that are always true regardless of context, domain, or time.
They are the bedrock that everything else builds upon.

Criteria for a law:
- Cannot be violated without consequence
- True across domains and contexts
- Not dependent on technology, market, or temporal conditions
- Can be stated in one clear sentence
- Has observable consequences when violated

Return JSON:
{
  "laws_extracted": [
    {
      "law_id": "<short identifier>",
      "statement": "<the law in one clear sentence>",
      "proof": "<evidence or reasoning for why this is immutable>",
      "violation_consequence": "<what happens when this is violated>",
      "domains_applicable": ["<domain>", ...],
      "confidence": <0.0-1.0>
    }
  ],
  "candidate_laws": [
    {
      "statement": "<possible law that needs more evidence>",
      "missing_evidence": "<what would confirm this as a law>"
    }
  ]
}

Return only valid JSON.
"""


# ---------------------------------------------------------------------------
# Core Engine Functions
# ---------------------------------------------------------------------------

async def synthesize(
    raw_input: str,
    synthesis_type: str = "full",
    existing_doctrine: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Convert raw ideas into structured doctrine.

    Args:
        raw_input: Raw intellectual material to synthesize.
        synthesis_type: 'full' (complete doctrine), 'laws' (extract laws only),
                       'expand' (expand existing doctrine).
        existing_doctrine: Optional existing doctrine to expand upon.

    Returns:
        Structured doctrine output.
    """
    synthesis_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc)

    if synthesis_type == "laws":
        system_prompt = _LAW_EXTRACTION_PROMPT
    elif synthesis_type == "expand" and existing_doctrine:
        system_prompt = _DOCTRINE_EXPANSION_PROMPT.format(
            existing_doctrine=json.dumps(existing_doctrine, indent=2)
        )
    else:
        system_prompt = _DOCTRINE_SYNTHESIS_PROMPT

    try:
        response = await _get_client().chat.completions.create(
            model="sovereign-core",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_input},
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
        )

        result = json.loads(response.choices[0].message.content)

    except Exception as e:
        result = {
            "synthesis_id": synthesis_id,
            "source_summary": raw_input[:200],
            "doctrine_elements": [],
            "error": f"Synthesis failed: {str(e)}",
            "publishable_summary": "Synthesis processing failed. Raw material captured for retry.",
            "next_synthesis_needed": ["retry_full_synthesis"],
        }

    return {
        "synthesis_id": synthesis_id,
        "timestamp": timestamp.isoformat(),
        "synthesis_type": synthesis_type,
        "result": result,
    }


async def extract_laws(raw_input: str) -> dict[str, Any]:
    """Extract only immutable laws from raw material."""
    return await synthesize(raw_input, synthesis_type="laws")


async def expand_doctrine(
    raw_input: str,
    existing_doctrine: dict[str, Any],
) -> dict[str, Any]:
    """Expand existing doctrine with new material."""
    return await synthesize(raw_input, synthesis_type="expand", existing_doctrine=existing_doctrine)


async def synthesize_framework(raw_input: str) -> dict[str, Any]:
    """Synthesize a complete framework from raw input — focused on the framework map."""
    result = await synthesize(raw_input, synthesis_type="full")
    # Extract and emphasize the framework map from full synthesis
    framework_map = result.get("result", {}).get("framework_map", {})
    return {
        "synthesis_id": result["synthesis_id"],
        "timestamp": result["timestamp"],
        "framework_map": framework_map,
        "full_result": result["result"],
    }


def get_doctrine_hierarchy() -> list[dict[str, str]]:
    """Return the doctrine hierarchy levels."""
    return [
        {"level": 1, "type": "law", "description": "Immutable truths — always true regardless of context"},
        {"level": 2, "type": "principle", "description": "Operating guidelines derived from laws"},
        {"level": 3, "type": "framework", "description": "Structural models for applying principles"},
        {"level": 4, "type": "map", "description": "Visual/structural representations of relationships"},
        {"level": 5, "type": "taxonomy", "description": "Classification systems for organizing elements"},
    ]
