"""
Protocol IV: Actio  ⚡
Meaning: the system produces the needed action.

Dispatches a RoutingDecision + IntelligenceObject to the appropriate
sub-agent and returns an ActionResult.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from ..schemas import (
    ActionResult,
    ActionType,
    IntelligenceObject,
    RoutingDecision,
)


async def execute(
    decision: RoutingDecision,
    obj: IntelligenceObject,
) -> ActionResult:
    """
    Protocol Actio: dispatch to the correct agent and return ActionResult.

    Imports are deferred to avoid circular dependencies and to allow
    each agent module to be loaded independently.
    """
    agent_name = decision.target_agent
    result_payload: dict = {}
    next_actions: list[ActionType] = []

    if agent_name == "estimator_mobilia":
        from ..agents.estimator_mobilia.agent import run
        budget = await run(obj)
        result_payload = budget.model_dump()
        result_summary = (
            f"Furniture budget generated: {len(budget.items)} items, "
            f"total ${budget.grand_total:,.2f}"
        )
        if budget.missing_info:
            next_actions.append(ActionType.REQUEST_MISSING_INFO)

    elif agent_name == "estimator_laboris":
        from ..agents.estimator_laboris.agent import run
        bid = await run(obj)
        result_payload = bid.model_dump()
        result_summary = (
            f"Labor bid generated: {len(bid.items)} tasks, "
            f"total ${bid.subtotal:,.2f}"
        )

    elif agent_name == "inspector_campi":
        from ..agents.inspector_campi.agent import run
        punch = await run(obj)
        result_payload = punch.model_dump()
        result_summary = (
            f"Punch list generated: {punch.open_count} open items"
        )

    elif agent_name == "scriptor_documentorum":
        from ..agents.scriptor_documentorum.agent import run
        doc = await run(obj, decision.action)
        result_payload = doc.model_dump()
        result_summary = f"Document generated: {doc.title}"

    elif agent_name == "interpres_designii":
        from ..agents.interpres_designii.agent import run
        packet = await run(obj)
        result_payload = packet.model_dump()
        result_summary = (
            f"Install packet generated: {len(packet.instructions)} room instructions"
        )

    elif agent_name == "custos_memoriae":
        from ..agents.custos_memoriae.agent import remember
        record = await remember(obj)
        result_payload = record.model_dump()
        result_summary = f"Memory updated: {record.record_type}"

    else:
        # Fallback: auctor_operis handles ambiguous input
        from ..agents.auctor_operis.agent import run
        result_payload, result_summary, next_actions = await run(obj)

    return ActionResult(
        action_id=str(uuid.uuid4()),
        action_type=decision.action,
        agent=agent_name,
        project_id=obj.project_id,
        result_summary=result_summary,
        payload=result_payload,
        next_actions=next_actions,
        executed_at=datetime.utcnow(),
    )
