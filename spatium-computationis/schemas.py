"""
Core Pydantic schemas for Spatium Computationis.
All data moving through the system must conform to these models.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class InputType(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"
    EMAIL = "email"
    PHOTO = "photo"
    VOICE = "voice"
    TEXT = "text"
    FIELD_NOTE = "field_note"
    DRAWING = "drawing"
    QUOTE = "quote"
    HANDWRITTEN = "handwritten"


class Region(str, Enum):
    REGIO_DESIGNII = "regio_designii"
    REGIO_MOBILIA = "regio_mobilia"
    REGIO_LABORIS = "regio_laboris"
    REGIO_CAMPI = "regio_campi"
    REGIO_DOCUMENTORUM = "regio_documentorum"
    REGIO_CONTRACTUS = "regio_contractus"
    MEMORY = "memory"
    CORE = "core"


class ActionType(str, Enum):
    GENERATE_BID = "generate_bid"
    CREATE_ESTIMATE = "create_estimate"
    REQUEST_MISSING_INFO = "request_missing_info"
    FLAG_RISK = "flag_risk"
    CREATE_CHANGE_ORDER = "create_change_order"
    UPDATE_PUNCH_LIST = "update_punch_list"
    SUMMARIZE_FIELD_ISSUE = "summarize_field_issue"
    PREPARE_INSTALL_PACKET = "prepare_install_packet"
    CREATE_CLIENT_DOCUMENT = "create_client_document"
    ROUTE_TO_AGENT = "route_to_agent"
    UPDATE_MEMORY = "update_memory"


class DocumentType(str, Enum):
    FURNITURE_BUDGET = "furniture_budget"
    LABOR_BID = "labor_bid"
    CHANGE_ORDER = "change_order"
    RFI = "rfi"
    PUNCH_LIST = "punch_list"
    CLOSEOUT_PACKET = "closeout_packet"
    SCOPE_SHEET = "scope_sheet"
    INSTALL_PACKET = "install_packet"
    FIELD_REPORT = "field_report"
    CLIENT_SUMMARY = "client_summary"


# ---------------------------------------------------------------------------
# Input / Ingressus
# ---------------------------------------------------------------------------

class RawInput(BaseModel):
    """Raw input as it arrives at the system boundary (Protocol: Ingressus)."""
    input_type: InputType
    content: str = Field(description="Raw text, base64 image, or file path")
    filename: str | None = None
    project_id: str | None = None
    submitted_by: str | None = None
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectInput(BaseModel):
    """Normalized input after Ingressus processing."""
    input_id: str
    project_id: str | None
    input_type: InputType
    raw_content: str
    extracted_text: str
    extracted_data: dict[str, Any] = Field(default_factory=dict)
    submitted_by: str | None
    submitted_at: datetime
    normalized_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Compressed Intelligence Object — Compressio
# ---------------------------------------------------------------------------

class IntelligenceObject(BaseModel):
    """Compressed operational intelligence unit (Protocol: Compressio). ⌬"""
    object_id: str
    project_id: str | None
    glyph: str = Field(description="Primary glyph tag e.g. ◈$, ⚒$, ⟁✓")
    region: Region
    summary: str = Field(description="One-sentence compressed meaning")
    extracted_entities: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    source_input_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Routing — Ordinatio
# ---------------------------------------------------------------------------

class RoutingDecision(BaseModel):
    """Output of Ordinatio — where this intelligence object goes. ≡"""
    object_id: str
    target_region: Region
    target_agent: str
    action: ActionType
    priority: int = Field(ge=1, le=5, default=3, description="1=urgent, 5=low")
    reasoning: str


# ---------------------------------------------------------------------------
# Agent outputs
# ---------------------------------------------------------------------------

class FurnitureLineItem(BaseModel):
    tag: str | None
    manufacturer: str | None
    model: str | None
    description: str
    quantity: int
    unit_price: float | None
    total_price: float | None
    room: str | None
    finish: str | None
    lead_time: str | None
    freight_assumption: str | None
    notes: str | None = None


class FurnitureBudget(BaseModel):
    project_id: str | None
    items: list[FurnitureLineItem]
    subtotal: float
    freight_estimate: float
    grand_total: float
    assumptions: list[str] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LaborLineItem(BaseModel):
    task: str
    crew_size: int
    hours: float
    rate: float
    total: float
    notes: str | None = None


class LaborBid(BaseModel):
    project_id: str | None
    items: list[LaborLineItem]
    subtotal: float
    complexity_rating: str
    crew_total: int
    schedule_days: float
    assumptions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PunchItem(BaseModel):
    item_id: str
    room: str | None
    description: str
    status: str = "open"
    responsible_party: str | None = None
    photo_ref: str | None = None
    notes: str | None = None


class PunchList(BaseModel):
    project_id: str | None
    items: list[PunchItem]
    open_count: int
    complete_count: int
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InstallerInstruction(BaseModel):
    room: str
    sequence: int
    instruction: str
    items_involved: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class InstallPacket(BaseModel):
    project_id: str | None
    project_name: str | None
    instructions: list[InstallerInstruction]
    site_notes: list[str] = Field(default_factory=list)
    access_notes: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GeneratedDocument(BaseModel):
    document_id: str
    project_id: str | None
    document_type: DocumentType
    title: str
    content_text: str
    file_path: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Memory — Custos Memoriae
# ---------------------------------------------------------------------------

class MemoryRecord(BaseModel):
    record_id: str
    project_id: str | None
    record_type: str = Field(description="e.g. bid, assumption, client_rule, preference")
    content: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# System action output — Actio
# ---------------------------------------------------------------------------

class ActionResult(BaseModel):
    """Final output of the Actio protocol. ⚡"""
    action_id: str
    action_type: ActionType
    agent: str
    project_id: str | None
    result_summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    next_actions: list[ActionType] = Field(default_factory=list)
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
