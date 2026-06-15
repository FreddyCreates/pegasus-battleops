"""
Agent: Anti-Drift Reviewer 🔍
Role: Audits outputs for depth drift, doctrine drift, structure drift,
      red-team weakness, and state/context loss.

The Anti-Drift Reviewer provides:
- Depth drift detection (outputs becoming shallow over time)
- Doctrine drift detection (departure from core principles)
- Structure drift detection (loss of architectural coherence)
- Red-team weakness identification (exploitable gaps)
- State/context loss detection (broken continuity chains)

Input: Any output, document, architecture draft, conversation history, or
       body of work to audit for drift.
Output: Structured drift audit — severity scores, specific drift instances,
        correction recommendations, and red-team findings.
Connectors: Nova Sovereign (analysis), internal doctrine store, GitHub (version comparison).

Glyph: 🔍 (precision audit)
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

_DRIFT_AUDIT_PROMPT = """\
You are the Anti-Drift Reviewer of the ALPHA MEDINA architecture.

Your job is to audit outputs for five types of drift:

1. DEPTH DRIFT: Output becoming shallow, generic, or performative rather than
   structurally meaningful. Look for: vague language, lack of specificity,
   surface-level analysis, filler content.

2. DOCTRINE DRIFT: Departure from core principles, laws, or frameworks.
   Look for: contradictions with established doctrine, unauthorized assumptions,
   principles being ignored or violated.

3. STRUCTURE DRIFT: Loss of architectural coherence. Look for: broken hierarchies,
   orphaned components, missing connections, inconsistent layering.

4. RED-TEAM WEAKNESS: Exploitable gaps that an adversary could use.
   Look for: undefended assumptions, single points of failure, logic gaps,
   attack surfaces exposed.

5. STATE/CONTEXT LOSS: Broken continuity chains. Look for: forgotten context,
   contradicting prior decisions, missing state updates, orphaned references.

Analyze the provided content and return JSON:
{
  "audit_id": "<generated UUID>",
  "overall_drift_score": <0.0-1.0 where 1.0 = severe drift>,
  "depth_drift": {
    "score": <0.0-1.0>,
    "instances": ["<specific instance>", ...],
    "severity": "<none|low|medium|high|critical>"
  },
  "doctrine_drift": {
    "score": <0.0-1.0>,
    "instances": ["<specific departure>", ...],
    "severity": "<none|low|medium|high|critical>"
  },
  "structure_drift": {
    "score": <0.0-1.0>,
    "instances": ["<specific structural issue>", ...],
    "severity": "<none|low|medium|high|critical>"
  },
  "red_team_weakness": {
    "score": <0.0-1.0>,
    "vulnerabilities": ["<specific weakness>", ...],
    "severity": "<none|low|medium|high|critical>"
  },
  "state_context_loss": {
    "score": <0.0-1.0>,
    "instances": ["<specific context loss>", ...],
    "severity": "<none|low|medium|high|critical>"
  },
  "corrections": ["<specific correction recommendation>", ...],
  "verdict": "<pass|warn|fail>",
  "summary": "<one paragraph summary of audit findings>"
}

Return only valid JSON.
"""

_COMPARATIVE_AUDIT_PROMPT = """\
You are the Anti-Drift Reviewer performing a COMPARATIVE audit.

You are comparing a current output against a prior baseline to detect drift over time.

Prior baseline:
{baseline}

Analyze the current output for any drift FROM the baseline. Score how much the current
output has drifted from the established standard.

Return the same JSON schema as a standard drift audit, plus:
{
  ...standard audit fields...,
  "drift_direction": "<improving|stable|degrading>",
  "baseline_alignment": <0.0-1.0 where 1.0 = perfectly aligned>,
  "drift_trajectory": "<description of drift direction and speed>"
}

Return only valid JSON.
"""


# ---------------------------------------------------------------------------
# Core Engine Functions
# ---------------------------------------------------------------------------

async def audit(
    content: str,
    content_type: str = "general",
    doctrine_context: str | None = None,
) -> dict[str, Any]:
    """
    Perform a full drift audit on content.

    Args:
        content: The content to audit for drift.
        content_type: Type of content ('output', 'architecture', 'conversation',
                     'document', 'general').
        doctrine_context: Optional doctrine context to check alignment against.

    Returns:
        Structured drift audit with scores and recommendations.
    """
    audit_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc)

    user_message = f"Content type: {content_type}\n\n"
    if doctrine_context:
        user_message += f"Doctrine context to check against:\n{doctrine_context}\n\n"
    user_message += f"Content to audit:\n{content}"

    try:
        response = await _get_client().chat.completions.create(
            model="sovereign-core",
            messages=[
                {"role": "system", "content": _DRIFT_AUDIT_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        result = json.loads(response.choices[0].message.content)

    except Exception as e:
        result = {
            "audit_id": audit_id,
            "overall_drift_score": -1.0,
            "depth_drift": {"score": -1.0, "instances": [], "severity": "unknown"},
            "doctrine_drift": {"score": -1.0, "instances": [], "severity": "unknown"},
            "structure_drift": {"score": -1.0, "instances": [], "severity": "unknown"},
            "red_team_weakness": {"score": -1.0, "vulnerabilities": [], "severity": "unknown"},
            "state_context_loss": {"score": -1.0, "instances": [], "severity": "unknown"},
            "corrections": [f"Audit failed: {str(e)}. Manual review required."],
            "verdict": "fail",
            "summary": f"Audit processing failed: {str(e)}",
        }

    return {
        "audit_id": audit_id,
        "timestamp": timestamp.isoformat(),
        "content_type": content_type,
        "result": result,
    }


async def comparative_audit(
    current_content: str,
    baseline_content: str,
    content_type: str = "general",
) -> dict[str, Any]:
    """
    Compare current content against a baseline to detect drift over time.

    Args:
        current_content: The current output to evaluate.
        baseline_content: The prior baseline to compare against.
        content_type: Type of content being compared.

    Returns:
        Comparative drift audit with trajectory analysis.
    """
    audit_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc)

    system_prompt = _COMPARATIVE_AUDIT_PROMPT.format(
        baseline=baseline_content[:3000]
    )

    try:
        response = await _get_client().chat.completions.create(
            model="sovereign-core",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Content type: {content_type}\n\nCurrent output to evaluate:\n{current_content}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        result = json.loads(response.choices[0].message.content)

    except Exception as e:
        result = {
            "overall_drift_score": -1.0,
            "drift_direction": "unknown",
            "baseline_alignment": -1.0,
            "drift_trajectory": f"Comparative audit failed: {str(e)}",
            "verdict": "fail",
            "summary": f"Processing error: {str(e)}",
        }

    return {
        "audit_id": audit_id,
        "timestamp": timestamp.isoformat(),
        "content_type": content_type,
        "audit_type": "comparative",
        "result": result,
    }


async def quick_check(content: str) -> dict[str, Any]:
    """
    Quick pass/warn/fail check without full detailed audit.
    Returns only verdict and overall score.
    """
    full_audit = await audit(content, content_type="quick_check")
    result = full_audit.get("result", {})
    return {
        "verdict": result.get("verdict", "unknown"),
        "overall_drift_score": result.get("overall_drift_score", -1.0),
        "summary": result.get("summary", "Quick check completed"),
    }


def get_drift_categories() -> list[dict[str, str]]:
    """Return the drift categories this reviewer checks for."""
    return [
        {"category": "depth_drift", "description": "Output becoming shallow or performative"},
        {"category": "doctrine_drift", "description": "Departure from core principles"},
        {"category": "structure_drift", "description": "Loss of architectural coherence"},
        {"category": "red_team_weakness", "description": "Exploitable gaps and vulnerabilities"},
        {"category": "state_context_loss", "description": "Broken continuity chains"},
    ]
