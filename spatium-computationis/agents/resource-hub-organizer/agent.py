"""
Agent: Resource Hub Organizer 📂
Role: Organizes ideas into main topics, subtopics, sub-subtopics,
      collections, and release paths.

The Resource Hub Organizer provides:
- Hierarchical topic organization (topics → subtopics → sub-subtopics)
- Collection assembly (grouping related elements for release)
- Release path planning (what gets published when and where)
- Content taxonomy management
- Cross-reference and linking between resources

Input: Raw ideas, notes, documents, doctrine elements, projects, or any
       intellectual material that needs organization.
Output: Structured resource map — topics hierarchy, collections, release paths,
        cross-references, and organizational taxonomy.
Connectors: Nova Sovereign (organization), GitHub (storage), Drive (documents),
            spreadsheets (tracking).

Glyph: 📂 (organization and structure)
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

_ORGANIZATION_PROMPT = """\
You are the Resource Hub Organizer of the ALPHA MEDINA architecture.

Your role is to take any collection of intellectual material and organize it
into a structured, navigable resource hierarchy with clear release paths.

Organization Architecture:
1. MAIN TOPICS — Top-level categories (max 7-10 for cognitive load)
2. SUBTOPICS — Second-level divisions within each main topic
3. SUB-SUBTOPICS — Third-level granular divisions where needed
4. COLLECTIONS — Curated groupings that cross topic boundaries (for release)
5. RELEASE PATHS — Sequences for publishing/sharing organized material

Principles:
- No more than 7±2 items at any hierarchy level (Miller's Law)
- Every item must belong to exactly one topic path
- Collections can reference items from multiple topics
- Release paths must have clear sequencing and dependencies
- Cross-references should be explicit, not implied

Return JSON:
{
  "organization_id": "<generated>",
  "hub_name": "<derived from content>",
  "topics": [
    {
      "topic_id": "<topic identifier>",
      "name": "<main topic name>",
      "description": "<what this topic covers>",
      "subtopics": [
        {
          "subtopic_id": "<subtopic identifier>",
          "name": "<subtopic name>",
          "description": "<what this subtopic covers>",
          "sub_subtopics": [
            {
              "id": "<sub-subtopic identifier>",
              "name": "<sub-subtopic name>",
              "items": ["<item reference>", ...]
            }
          ],
          "items": ["<item that lives at this level>", ...]
        }
      ],
      "item_count": <total items in this topic tree>
    }
  ],
  "collections": [
    {
      "collection_id": "<collection identifier>",
      "name": "<collection name>",
      "purpose": "<why this collection exists>",
      "items": ["<item_id from any topic>", ...],
      "release_ready": true/false
    }
  ],
  "release_paths": [
    {
      "path_id": "<path identifier>",
      "name": "<release path name>",
      "target_audience": "<who this is for>",
      "sequence": ["<collection_id or item_id>", ...],
      "format": "<article|whitepaper|series|course|reference>",
      "status": "<draft|ready|published>"
    }
  ],
  "cross_references": [
    {"from": "<item/topic id>", "to": "<item/topic id>", "relationship": "<type>"}
  ],
  "unorganized_items": ["<items that don't fit current structure>"],
  "organization_notes": "<observations about the material's natural structure>"
}

Return only valid JSON.
"""

_REORGANIZATION_PROMPT = """\
You are the Resource Hub Organizer performing a REORGANIZATION.

Current organization:
{current_organization}

New material or reorganization request has been provided.
Integrate the new material into the existing structure, or restructure as needed.

Rules:
- Preserve existing organization where it still works
- Only restructure if the new material reveals a better hierarchy
- Flag any items that moved between topics
- Update collections and release paths as needed

Return the full updated organization in the same JSON schema, plus:
{
  ...full organization...,
  "changes_made": ["<what changed>", ...],
  "items_moved": [{"item": "<id>", "from": "<old location>", "to": "<new location>"}],
  "new_items_added": ["<item>", ...],
  "structure_changed": true/false
}

Return only valid JSON.
"""


# ---------------------------------------------------------------------------
# Core Engine Functions
# ---------------------------------------------------------------------------

async def organize(
    material: str,
    material_type: str = "mixed",
    existing_organization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Organize material into a structured resource hierarchy.

    Args:
        material: The intellectual material to organize.
        material_type: Type of material ('ideas', 'documents', 'doctrine',
                      'projects', 'mixed').
        existing_organization: Optional existing organization to integrate into.

    Returns:
        Structured resource organization.
    """
    organization_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc)

    if existing_organization:
        system_prompt = _REORGANIZATION_PROMPT.format(
            current_organization=json.dumps(existing_organization, indent=2)[:5000]
        )
    else:
        system_prompt = _ORGANIZATION_PROMPT

    user_message = f"Material type: {material_type}\n\nMaterial to organize:\n{material}"

    try:
        response = await _get_client().chat.completions.create(
            model="sovereign-core",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )

        result = json.loads(response.choices[0].message.content)

    except Exception as e:
        result = {
            "organization_id": organization_id,
            "hub_name": "Unorganized Hub",
            "topics": [],
            "collections": [],
            "release_paths": [],
            "cross_references": [],
            "unorganized_items": [material[:500]],
            "organization_notes": f"Organization failed: {str(e)}. Material captured.",
        }

    return {
        "organization_id": organization_id,
        "timestamp": timestamp.isoformat(),
        "material_type": material_type,
        "result": result,
    }


async def add_to_organization(
    new_material: str,
    existing_organization: dict[str, Any],
) -> dict[str, Any]:
    """Add new material to an existing organization structure."""
    return await organize(
        new_material,
        material_type="addition",
        existing_organization=existing_organization,
    )


async def generate_release_path(
    organization: dict[str, Any],
    target_audience: str,
    format_type: str = "series",
) -> dict[str, Any]:
    """Generate a release path for organized material."""
    prompt = (
        f"Given this organization, create an optimal release path for "
        f"target audience: {target_audience}, format: {format_type}\n\n"
        f"Organization:\n{json.dumps(organization, indent=2)[:3000]}"
    )
    result = await organize(prompt, material_type="release_planning")
    return {
        "target_audience": target_audience,
        "format_type": format_type,
        "release_paths": result.get("result", {}).get("release_paths", []),
    }


async def suggest_collections(material: str) -> dict[str, Any]:
    """Suggest collections for material without full organization."""
    result = await organize(material, material_type="collection_suggestion")
    return {
        "collections": result.get("result", {}).get("collections", []),
        "organization_notes": result.get("result", {}).get("organization_notes", ""),
    }


def get_organization_principles() -> list[str]:
    """Return the organizing principles used by this agent."""
    return [
        "No more than 7±2 items at any hierarchy level (Miller's Law)",
        "Every item must belong to exactly one topic path",
        "Collections can reference items from multiple topics",
        "Release paths must have clear sequencing and dependencies",
        "Cross-references should be explicit, not implied",
        "Three levels maximum: topic → subtopic → sub-subtopic",
        "Collections are for release; topics are for navigation",
    ]
