"""
Agent: Custos Memoriae  ◉
Role: Project memory and continuity agent.

Stores and retrieves project history, past bids, recurring client rules,
contractor preferences, and manufacturer patterns using SQLite.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from openai import AsyncOpenAI

from ...schemas import IntelligenceObject, MemoryRecord

_client: AsyncOpenAI | None = None

def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client

DB_PATH = Path(__file__).parent.parent.parent / "field" / "memory.db"


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def _init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                record_id   TEXT PRIMARY KEY,
                project_id  TEXT,
                record_type TEXT NOT NULL,
                content     TEXT NOT NULL,
                tags        TEXT NOT NULL DEFAULT '[]',
                created_at  TEXT NOT NULL
            )
            """
        )
        conn.commit()


_init_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# LLM — summarise what to remember
# ---------------------------------------------------------------------------

_MEMORY_SYSTEM_PROMPT = """\
You are Custos Memoriae (◉), the project memory keeper of Spatium Computationis.

Given a compressed intelligence object, decide what should be stored in \
long-term project memory.

Return JSON:
{
  "record_type": "<bid | assumption | client_rule | preference | field_note | contractor_note | product_note>",
  "content": "<clear, reusable memory statement>",
  "tags": ["<tag>", ...]
}

Content should be a statement useful for future reference on this or similar projects.
Return only valid JSON. No markdown fences.
"""


async def remember(obj: IntelligenceObject) -> MemoryRecord:
    """Store a compressed intelligence object in project memory."""
    payload = {
        "glyph": obj.glyph,
        "summary": obj.summary,
        "entities": obj.extracted_entities,
        "project_id": obj.project_id,
    }

    response = await _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": _MEMORY_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    data = json.loads(response.choices[0].message.content)
    now = datetime.now(timezone.utc).isoformat()
    record_id = str(uuid.uuid4())

    with _db() as conn:
        conn.execute(
            "INSERT INTO memory VALUES (?,?,?,?,?,?)",
            (
                record_id,
                obj.project_id,
                data.get("record_type", "field_note"),
                data.get("content", obj.summary),
                json.dumps(data.get("tags", [])),
                now,
            ),
        )
        conn.commit()

    return MemoryRecord(
        record_id=record_id,
        project_id=obj.project_id,
        record_type=data.get("record_type", "field_note"),
        content=data.get("content", obj.summary),
        tags=data.get("tags", []),
        created_at=datetime.fromisoformat(now),
    )


def recall(project_id: str | None, limit: int = 50) -> list[MemoryRecord]:
    """Retrieve memory records for a project."""
    with _db() as conn:
        if project_id:
            rows = conn.execute(
                "SELECT * FROM memory WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM memory ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

    return [
        MemoryRecord(
            record_id=row["record_id"],
            project_id=row["project_id"],
            record_type=row["record_type"],
            content=row["content"],
            tags=json.loads(row["tags"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
        for row in rows
    ]


def search_memory(query: str, project_id: str | None = None, limit: int = 20) -> list[MemoryRecord]:
    """Simple keyword search over memory content."""
    with _db() as conn:
        if project_id:
            rows = conn.execute(
                "SELECT * FROM memory WHERE project_id=? AND content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (project_id, f"%{query}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM memory WHERE content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()

    return [
        MemoryRecord(
            record_id=row["record_id"],
            project_id=row["project_id"],
            record_type=row["record_type"],
            content=row["content"],
            tags=json.loads(row["tags"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
        for row in rows
    ]
