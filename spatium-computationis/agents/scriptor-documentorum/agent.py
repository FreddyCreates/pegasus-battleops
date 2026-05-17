"""
Agent: Scriptor Documentorum  ▣✎
Role: Document generation agent.

Takes structured data (budgets, bids, punch lists, etc.) and renders
official client-facing documents as plain text (with optional DOCX export).

Handles: proposals, labor bids, furniture budgets, scope sheets, work orders,
change orders, RFIs, punch lists, sign-off forms, closeout packets.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from openai import AsyncOpenAI

from ...schemas import ActionType, DocumentType, GeneratedDocument, IntelligenceObject

_client: AsyncOpenAI | None = None

def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client
_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "documents" / "templates"

_jinja = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


# ---------------------------------------------------------------------------
# Action → document type mapping
# ---------------------------------------------------------------------------

_ACTION_TO_DOC_TYPE: dict[ActionType, DocumentType] = {
    ActionType.GENERATE_BID: DocumentType.LABOR_BID,
    ActionType.CREATE_ESTIMATE: DocumentType.FURNITURE_BUDGET,
    ActionType.REQUEST_MISSING_INFO: DocumentType.RFI,
    ActionType.FLAG_RISK: DocumentType.RFI,
    ActionType.CREATE_CHANGE_ORDER: DocumentType.CHANGE_ORDER,
    ActionType.UPDATE_PUNCH_LIST: DocumentType.PUNCH_LIST,
    ActionType.SUMMARIZE_FIELD_ISSUE: DocumentType.FIELD_REPORT,
    ActionType.PREPARE_INSTALL_PACKET: DocumentType.INSTALL_PACKET,
    ActionType.CREATE_CLIENT_DOCUMENT: DocumentType.CLIENT_SUMMARY,
}


# ---------------------------------------------------------------------------
# LLM — generate document content
# ---------------------------------------------------------------------------

_DOC_SYSTEM_PROMPT = """\
You are Scriptor Documentorum (▣✎), the document generation intelligence of \
Spatium Computationis.

Given project intelligence and a document type, produce a professional, \
complete document in plain text.

Document types and their expected content:
  furniture_budget  — itemised furniture cost summary with totals and assumptions
  labor_bid         — itemised labor scope with crew, schedule, inclusions/exclusions
  change_order      — formal change order with description, cost delta, schedule impact
  rfi               — Request for Information with specific questions and context
  punch_list        — itemised list of open/complete field items
  closeout_packet   — project summary, completion checklist, final sign-offs
  scope_sheet       — plain-language scope of work
  install_packet    — room-by-room installer instructions
  field_report      — field condition summary with issues and recommendations
  client_summary    — executive summary for client consumption

Return JSON:
{
  "title": "<document title>",
  "content_text": "<full document text, well-formatted with sections>"
}

Write in professional, clear language. Use section headers. No markdown fences in output JSON.
"""


async def run(obj: IntelligenceObject, action: ActionType) -> GeneratedDocument:
    """Scriptor Documentorum: generate a document from an IntelligenceObject."""
    doc_type = _ACTION_TO_DOC_TYPE.get(action, DocumentType.CLIENT_SUMMARY)

    payload = {
        "document_type": doc_type.value,
        "project_id": obj.project_id,
        "summary": obj.summary,
        "entities": obj.extracted_entities,
        "missing_fields": obj.missing_fields,
    }

    response = await _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _DOC_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    data = json.loads(response.choices[0].message.content)

    return GeneratedDocument(
        document_id=str(uuid.uuid4()),
        project_id=obj.project_id,
        document_type=doc_type,
        title=data.get("title", doc_type.value.replace("_", " ").title()),
        content_text=data.get("content_text", ""),
    )
