"""
Field — Issue Tracking  ⟁
Simple helpers to log and query field issues against the memory store.
"""

from __future__ import annotations

from ..agents.custos_memoriae.agent import search_memory, recall
from ..schemas import MemoryRecord


def get_open_issues(project_id: str) -> list[MemoryRecord]:
    """Retrieve all field_note memory records for a project."""
    records = recall(project_id, limit=200)
    return [r for r in records if r.record_type == "field_note"]


def search_issues(project_id: str, keyword: str) -> list[MemoryRecord]:
    """Search field issues by keyword."""
    return search_memory(keyword, project_id=project_id)
