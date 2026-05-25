"""
Protocol: Fasciculus  📦
Meaning: Batch processing operations.

Handles:
- Batch creation and management
- Parallel batch processing
- Progress tracking
- Error handling
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field


class BatchStatus(str, Enum):
    """Batch processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some items failed
    CANCELLED = "cancelled"


class BatchConfig(BaseModel):
    """Configuration for batch processing."""
    batch_size: int = 100
    max_concurrent: int = 10
    retry_failed: bool = True
    max_retries: int = 3
    timeout_seconds: int = 300


class BatchItem(BaseModel):
    """An item in a batch."""
    item_id: str
    data: dict[str, Any]
    status: str = "pending"
    result: Any = None
    error: str | None = None
    retries: int = 0


class BatchResult(BaseModel):
    """Result of batch processing."""
    batch_id: str
    status: BatchStatus
    total_items: int
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    
    # Results
    results: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    
    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "batches.db"


def _init_batches_db() -> None:
    """Initialize the batches database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS batches (
                batch_id        TEXT PRIMARY KEY,
                name            TEXT,
                processor       TEXT NOT NULL,
                config          TEXT NOT NULL,
                status          TEXT DEFAULT 'pending',
                total_items     INTEGER DEFAULT 0,
                processed       INTEGER DEFAULT 0,
                successful      INTEGER DEFAULT 0,
                failed          INTEGER DEFAULT 0,
                created_at      TEXT NOT NULL,
                started_at      TEXT,
                completed_at    TEXT,
                duration_ms     REAL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bat_status ON batches(status)")
        
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS batch_items (
                item_id         TEXT PRIMARY KEY,
                batch_id        TEXT NOT NULL,
                data            TEXT NOT NULL,
                status          TEXT DEFAULT 'pending',
                result          TEXT,
                error           TEXT,
                retries         INTEGER DEFAULT 0,
                processed_at    TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bi_batch ON batch_items(batch_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bi_status ON batch_items(status)")
        
        conn.commit()


_init_batches_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Processor Registry
# ---------------------------------------------------------------------------

_batch_processors: dict[str, Callable[[dict], Awaitable[Any]]] = {}


def register_batch_processor(name: str, processor: Callable[[dict], Awaitable[Any]]) -> None:
    """Register a batch item processor."""
    _batch_processors[name] = processor


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def create_batch(
    items: list[dict[str, Any]],
    processor: str,
    name: str | None = None,
    config: BatchConfig | None = None,
) -> str:
    """
    Protocol Fasciculus: create a batch for processing.
    """
    batch_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    cfg = config or BatchConfig()
    
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO batches (batch_id, name, processor, config, status, total_items, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """,
            (batch_id, name, processor, cfg.model_dump_json(), len(items), now.isoformat())
        )
        
        for item in items:
            item_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO batch_items (item_id, batch_id, data, status) VALUES (?, ?, ?, 'pending')",
                (item_id, batch_id, json.dumps(item))
            )
        
        conn.commit()
    
    return batch_id


async def process_batch(
    batch_id: str,
    config: BatchConfig | None = None,
) -> BatchResult:
    """
    Protocol Fasciculus: process a batch.
    """
    start_time = time.perf_counter()
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        # Get batch info
        batch_row = conn.execute(
            "SELECT * FROM batches WHERE batch_id = ?",
            (batch_id,)
        ).fetchone()
        
        if not batch_row:
            return BatchResult(
                batch_id=batch_id,
                status=BatchStatus.FAILED,
                total_items=0,
            )
        
        processor_name = batch_row["processor"]
        stored_config = BatchConfig.model_validate_json(batch_row["config"])
        cfg = config or stored_config
        
        # Mark as processing
        conn.execute(
            "UPDATE batches SET status = 'processing', started_at = ? WHERE batch_id = ?",
            (now.isoformat(), batch_id)
        )
        conn.commit()
    
    # Get processor
    processor = _batch_processors.get(processor_name)
    if not processor:
        with _db() as conn:
            conn.execute(
                "UPDATE batches SET status = 'failed' WHERE batch_id = ?",
                (batch_id,)
            )
            conn.commit()
        return BatchResult(
            batch_id=batch_id,
            status=BatchStatus.FAILED,
            total_items=batch_row["total_items"],
            errors=[{"error": f"Processor not found: {processor_name}"}],
        )
    
    # Get pending items
    with _db() as conn:
        items = conn.execute(
            "SELECT * FROM batch_items WHERE batch_id = ? AND status IN ('pending', 'failed')",
            (batch_id,)
        ).fetchall()
    
    # Process items with concurrency limit
    semaphore = asyncio.Semaphore(cfg.max_concurrent)
    results: list[dict] = []
    errors: list[dict] = []
    
    async def process_item(item_row):
        async with semaphore:
            item_id = item_row["item_id"]
            data = json.loads(item_row["data"])
            
            try:
                result = await asyncio.wait_for(
                    processor(data),
                    timeout=cfg.timeout_seconds / cfg.max_concurrent
                )
                
                with _db() as conn:
                    conn.execute(
                        "UPDATE batch_items SET status = 'completed', result = ?, processed_at = ? WHERE item_id = ?",
                        (json.dumps(result), datetime.now(timezone.utc).isoformat(), item_id)
                    )
                    conn.commit()
                
                results.append({"item_id": item_id, "result": result})
                return True
                
            except Exception as e:
                retries = item_row["retries"] + 1
                status = "failed" if retries >= cfg.max_retries else "pending"
                
                with _db() as conn:
                    conn.execute(
                        "UPDATE batch_items SET status = ?, error = ?, retries = ? WHERE item_id = ?",
                        (status, str(e), retries, item_id)
                    )
                    conn.commit()
                
                errors.append({"item_id": item_id, "error": str(e)})
                return False
    
    # Process all items
    tasks = [process_item(item) for item in items]
    task_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful = sum(1 for r in task_results if r is True)
    failed = len(items) - successful
    
    # Update batch status
    duration_ms = (time.perf_counter() - start_time) * 1000
    completed_at = datetime.now(timezone.utc)
    
    if failed == 0:
        status = BatchStatus.COMPLETED
    elif successful == 0:
        status = BatchStatus.FAILED
    else:
        status = BatchStatus.PARTIAL
    
    with _db() as conn:
        conn.execute(
            """
            UPDATE batches SET 
                status = ?, processed = processed + ?, successful = successful + ?,
                failed = failed + ?, completed_at = ?, duration_ms = ?
            WHERE batch_id = ?
            """,
            (status.value, len(items), successful, failed, completed_at.isoformat(), duration_ms, batch_id)
        )
        conn.commit()
    
    return BatchResult(
        batch_id=batch_id,
        status=status,
        total_items=batch_row["total_items"],
        processed_items=len(items),
        successful_items=successful,
        failed_items=failed,
        results=results,
        errors=errors,
        started_at=now,
        completed_at=completed_at,
        duration_ms=duration_ms,
    )


async def get_batch_status(batch_id: str) -> BatchResult | None:
    """Get status of a batch."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM batches WHERE batch_id = ?",
            (batch_id,)
        ).fetchone()
        
        if not row:
            return None
        
        return BatchResult(
            batch_id=row["batch_id"],
            status=BatchStatus(row["status"]),
            total_items=row["total_items"],
            processed_items=row["processed"],
            successful_items=row["successful"],
            failed_items=row["failed"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            duration_ms=row["duration_ms"],
        )
