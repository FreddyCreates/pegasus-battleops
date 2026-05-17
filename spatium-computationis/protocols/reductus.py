"""
Protocol V: Reductus  ↺
Meaning: field reality returns back into the system.

Field updates (photos, notes, damage reports, completion statuses) re-enter
the system through Reductus, which:
  1. Normalises the field input via Ingressus.
  2. Compresses it via Compressio.
  3. Identifies what needs updating (estimate, punch list, memory, documents).
  4. Triggers the relevant agents via Actio.
  5. Returns a summary of all changes applied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..schemas import ActionResult, RawInput
from . import ingressus, compressio, ordinatio, actio


@dataclass
class ReductusReport:
    """Summary of what changed after a field update was re-ingested."""
    project_id: str | None
    field_input_id: str
    actions_taken: list[ActionResult] = field(default_factory=list)
    summary: str = ""
    processed_at: datetime = field(default_factory=datetime.utcnow)


async def process_field_update(raw: RawInput) -> ReductusReport:
    """
    Reductus: re-ingest a field update and cascade changes through the system.

    This is the feedback loop (↺) that keeps estimates, punch lists, and
    project memory current as reality evolves on the jobsite.
    """
    # Step 1 — Ingressus: normalise the field input
    project_input = await ingressus.process(raw)

    # Step 2 — Compressio: compress into operational intelligence
    intel_obj = await compressio.compress(project_input)

    actions: list[ActionResult] = []

    # Step 3 — Always update project memory with field reality
    from ..agents.custos_memoriae.agent import remember
    memory_record = await remember(intel_obj)
    actions.append(
        ActionResult(
            action_id=memory_record.record_id,
            action_type="update_memory",  # type: ignore[arg-type]
            agent="custos_memoriae",
            project_id=intel_obj.project_id,
            result_summary=f"Memory updated: {memory_record.content[:80]}",
            payload=memory_record.model_dump(),
        )
    )

    # Step 4 — Ordinatio: route to the primary agent for this field input
    decision = await ordinatio.route(intel_obj)

    # Step 5 — Actio: execute the primary action
    primary_result = await actio.execute(decision, intel_obj)
    actions.append(primary_result)

    # Step 6 — If missing info was flagged, generate an RFI
    from ..schemas import ActionType
    if ActionType.REQUEST_MISSING_INFO in primary_result.next_actions:
        from ..agents.scriptor_documentorum.agent import run as gen_doc
        rfi_doc = await gen_doc(intel_obj, ActionType.REQUEST_MISSING_INFO)
        actions.append(
            ActionResult(
                action_id=rfi_doc.document_id,
                action_type=ActionType.REQUEST_MISSING_INFO,
                agent="scriptor_documentorum",
                project_id=intel_obj.project_id,
                result_summary=f"RFI generated: {rfi_doc.title}",
                payload=rfi_doc.model_dump(),
            )
        )

    summary_parts = [a.result_summary for a in actions]
    summary = " | ".join(summary_parts)

    return ReductusReport(
        project_id=raw.project_id,
        field_input_id=project_input.input_id,
        actions_taken=actions,
        summary=summary,
    )
