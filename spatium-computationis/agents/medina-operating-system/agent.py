"""
Agent: Medina Operating System 🧠
Role: Applies the full Alfredo / OIS cognitive operating framework to meaningful work.

The Medina Operating System provides:
- Full cognitive framework application to any input
- Structured thinking through doctrine, laws, and principles
- Multi-layer processing (perception → reasoning → synthesis → output)
- State management across sessions and contexts
- Integration with all downstream ALPHA MEDINA skills

Input: Raw ideas, questions, projects, problems, unstructured thoughts, or any work needing
       the full cognitive operating system applied.
Output: Structured cognitive output — doctrine-aligned analysis, framed responses,
        layered reasoning, actionable synthesis, and state-tracked context.
Connectors: Nova Sovereign (reasoning), GitHub (versioning), internal doctrine store.

Glyph: 🧠 (cognitive operating system)
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
# System Prompts — Core Cognitive Layers
# ---------------------------------------------------------------------------

_OIS_SYSTEM_PROMPT = """\
You are the Medina Operating System (OIS) — the core cognitive engine of the ALPHA MEDINA
architecture. You operate according to Alfredo's doctrine and cognitive framework.

Your processing layers:
1. PERCEPTION: What is being presented? Strip noise, identify signal.
2. DOCTRINE ALIGNMENT: What laws, principles, or frameworks apply?
3. STRUCTURAL REASONING: Map the problem into its architecture — branches, dependencies, gates.
4. SYNTHESIS: Produce output that compounds — not just answers but builds infrastructure.
5. STATE TRACKING: Track what context persists, what drifts, what compounds.

Operating Principles:
- Every output must be meaningful, not performative.
- Depth over breadth unless expansion is explicitly requested.
- All work builds on doctrine — nothing floats without a structural anchor.
- Compounding value: each output makes the next one better.
- Anti-drift: maintain coherence across sessions and contexts.

When processing input, return structured JSON:
{
  "perception": "<what is actually being asked/presented>",
  "doctrine_alignment": "<which principles/laws/frameworks apply>",
  "structural_map": "<architecture of the problem — branches, dependencies>",
  "synthesis": "<the actual output — actionable, structured, compound>",
  "state_update": "<what context should persist for future processing>",
  "drift_risk": "<any identified risks of losing depth or coherence>",
  "next_gates": ["<what comes next>", "..."]
}

Return only valid JSON.
"""

_CONTEXT_INTEGRATION_PROMPT = """\
You are processing a follow-up within an active OIS session.

Previous context state:
{context_state}

Apply the Medina Operating System to the new input while maintaining full context coherence.
Identify any drift from prior state and correct it.

Return structured JSON with the same schema as primary processing, plus:
{
  ...standard OIS output...,
  "context_continuity": "<how this connects to prior state>",
  "drift_detected": "<any detected drift from prior context>",
  "compounding_value": "<what new value this adds to the existing chain>"
}

Return only valid JSON.
"""


# ---------------------------------------------------------------------------
# Core Engine Functions
# ---------------------------------------------------------------------------

async def process(
    input_text: str,
    context_state: dict[str, Any] | None = None,
    processing_mode: str = "full",
) -> dict[str, Any]:
    """
    Apply the full Medina Operating System to an input.

    Args:
        input_text: The raw input to process through the cognitive framework.
        context_state: Optional prior context state for session continuity.
        processing_mode: 'full' (all layers), 'perception' (signal only),
                        'synthesis' (output only), 'doctrine' (alignment check).

    Returns:
        Structured cognitive output with all OIS layers applied.
    """
    process_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc)

    # Select system prompt based on context
    if context_state:
        system_prompt = _CONTEXT_INTEGRATION_PROMPT.format(
            context_state=json.dumps(context_state, indent=2)
        )
    else:
        system_prompt = _OIS_SYSTEM_PROMPT

    # Add processing mode instruction
    mode_instruction = ""
    if processing_mode == "perception":
        mode_instruction = "\n\nFocus only on the PERCEPTION layer. Return perception analysis."
    elif processing_mode == "synthesis":
        mode_instruction = "\n\nFocus only on the SYNTHESIS layer. Produce actionable output."
    elif processing_mode == "doctrine":
        mode_instruction = "\n\nFocus only on DOCTRINE ALIGNMENT. Map principles that apply."

    try:
        response = await _get_client().chat.completions.create(
            model="sovereign-core",
            messages=[
                {"role": "system", "content": system_prompt + mode_instruction},
                {"role": "user", "content": input_text},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
        )

        result = json.loads(response.choices[0].message.content)

    except Exception as e:
        result = {
            "perception": input_text[:500],
            "doctrine_alignment": "Unable to process — fallback mode active",
            "structural_map": "Single-node: raw input awaiting processing",
            "synthesis": f"Processing failed: {str(e)}. Input captured for retry.",
            "state_update": "Error state — requires reprocessing",
            "drift_risk": "High — processing failure breaks chain",
            "next_gates": ["retry_processing", "manual_review"],
        }

    # Wrap with metadata
    return {
        "process_id": process_id,
        "timestamp": timestamp.isoformat(),
        "processing_mode": processing_mode,
        "has_context": context_state is not None,
        "output": result,
    }


async def extract_doctrine_alignment(input_text: str) -> dict[str, Any]:
    """Quick doctrine alignment check without full processing."""
    return await process(input_text, processing_mode="doctrine")


async def synthesize(input_text: str, context_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Direct synthesis — produce actionable output from input."""
    return await process(input_text, context_state=context_state, processing_mode="synthesis")


async def perceive(input_text: str) -> dict[str, Any]:
    """Perception layer only — strip noise, identify signal."""
    return await process(input_text, processing_mode="perception")


def get_operating_principles() -> list[str]:
    """Return the core operating principles of the Medina Operating System."""
    return [
        "Every output must be meaningful, not performative.",
        "Depth over breadth unless expansion is explicitly requested.",
        "All work builds on doctrine — nothing floats without a structural anchor.",
        "Compounding value: each output makes the next one better.",
        "Anti-drift: maintain coherence across sessions and contexts.",
        "State tracking: context persists and compounds.",
        "Structural reasoning: map problems into architecture.",
        "Perception first: strip noise, identify signal before acting.",
    ]
