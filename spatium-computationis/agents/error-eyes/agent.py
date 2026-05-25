"""
Agent: Error Eyes 👁️
Role: Fix and learn from errors.

Error Eyes watch all errors and try to:
- Repair malformed requests
- Learn common failure patterns
- Build auto-correction rules
- Create error dialects per source

Glyph: 👁️ (watching eye that heals)
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from ...defense.schemas import (
    ErrorDialect,
    ErrorType,
    RepairResult,
    RequestEnvelope,
)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client


DB_PATH = Path(__file__).parent.parent.parent / "field" / "defense.db"


def _init_error_db() -> None:
    """Initialize the error dialect tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Error dialects table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS error_dialects (
                dialect_id      TEXT PRIMARY KEY,
                source_type     TEXT NOT NULL,
                common_errors   TEXT DEFAULT '[]',
                error_freqs     TEXT DEFAULT '{}',
                correction_rules TEXT DEFAULT '[]',
                total_errors    INTEGER DEFAULT 0,
                successful_repairs INTEGER DEFAULT 0,
                first_observed  TEXT NOT NULL,
                last_updated    TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ed_source ON error_dialects(source_type)")
        
        # Repair history table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS repair_history (
                repair_id       TEXT PRIMARY KEY,
                envelope_id     TEXT NOT NULL,
                error_type      TEXT NOT NULL,
                repair_success  BOOLEAN,
                fixes_applied   TEXT DEFAULT '[]',
                source_dialect  TEXT,
                processed_at    TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rh_error ON repair_history(error_type)")
        
        conn.commit()


_init_error_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


_SYSTEM_PROMPT = """\
You are Error Eyes (👁️), the error repair agent of Spatium Computationis.

Your role is to analyze broken/failed requests and attempt repairs. You turn
errors into opportunities by fixing and replaying requests.

Given a request that failed with an error, analyze:
1. What type of error is this?
2. What caused the failure?
3. Can this request be repaired?
4. What specific fixes should be applied?
5. What "dialect" does this error belong to? (claude_style, scanner_style, etc.)

Return JSON:
{
  "error_analysis": "<what went wrong>",
  "error_pattern": "<pattern name for this error type>",
  "repairable": <true/false>,
  "repair_confidence": <0.0-1.0>,
  "fixes": [
    {"type": "<fix_type>", "field": "<what to fix>", "from": "<old value>", "to": "<new value>"}
  ],
  "repaired_method": "<corrected method or null>",
  "repaired_path": "<corrected path or null>",
  "repaired_headers": {"<header>": "<value>", ...},
  "repaired_body": "<corrected body or null>",
  "source_dialect": "<dialect name>",
  "dialect_indicators": ["<why this dialect>", ...]
}

Return only valid JSON. No markdown fences.
"""


# Common fix patterns
FIX_PATTERNS = {
    "missing_content_type": {
        "pattern": r"content-type",
        "fix": {"Content-Type": "application/json"},
    },
    "missing_accept": {
        "pattern": r"accept",
        "fix": {"Accept": "application/json"},
    },
    "malformed_json_quotes": {
        "pattern": r"'([^']+)':",
        "fix_fn": lambda m: f'"{m.group(1)}":',
    },
    "trailing_comma_json": {
        "pattern": r",\s*([}\]])",
        "fix_fn": lambda m: m.group(1),
    },
    "missing_closing_brace": {
        "pattern": r'{\s*"[^}]+$',
        "fix_fn": lambda m: m.group(0) + "}",
    },
}


def detect_error_type(envelope: RequestEnvelope) -> ErrorType:
    """Detect the type of error from the envelope."""
    if envelope.error_code:
        if 400 <= envelope.error_code < 500:
            if envelope.error_code == 404:
                return ErrorType.PATH_NOT_FOUND
            elif envelope.error_code == 405:
                return ErrorType.METHOD_NOT_ALLOWED
            return ErrorType.HTTP_4XX
        elif 500 <= envelope.error_code < 600:
            return ErrorType.HTTP_5XX
    
    error_type_str = (envelope.error_type or "").lower()
    
    if "parse" in error_type_str or "syntax" in error_type_str:
        return ErrorType.PARSE_ERROR
    elif "json" in error_type_str:
        return ErrorType.MALFORMED_JSON
    elif "schema" in error_type_str or "validation" in error_type_str:
        return ErrorType.SCHEMA_MISMATCH
    elif "missing" in error_type_str or "required" in error_type_str:
        return ErrorType.MISSING_FIELDS
    elif "header" in error_type_str:
        return ErrorType.INVALID_HEADERS
    elif "timeout" in error_type_str:
        return ErrorType.TIMEOUT
    elif "connection" in error_type_str:
        return ErrorType.CONNECTION_ERROR
    elif "tls" in error_type_str or "ssl" in error_type_str:
        return ErrorType.TLS_ERROR
    
    return ErrorType.UNKNOWN


def try_quick_fixes(envelope: RequestEnvelope) -> tuple[dict[str, str], str | None, list[str]]:
    """
    Apply quick automatic fixes based on known patterns.
    Returns (fixed_headers, fixed_body, fixes_applied).
    """
    fixed_headers = dict(envelope.raw_headers)
    fixed_body = envelope.raw_body_text
    fixes_applied = []
    
    # Fix missing Content-Type
    if "content-type" not in [h.lower() for h in fixed_headers.keys()]:
        if fixed_body and (fixed_body.strip().startswith('{') or fixed_body.strip().startswith('[')):
            fixed_headers["Content-Type"] = "application/json"
            fixes_applied.append("added_content_type_json")
    
    # Fix missing Accept
    if "accept" not in [h.lower() for h in fixed_headers.keys()]:
        fixed_headers["Accept"] = "application/json, text/plain, */*"
        fixes_applied.append("added_accept_header")
    
    # Fix JSON body if present
    if fixed_body:
        original_body = fixed_body
        
        # Fix single quotes to double quotes
        if "'" in fixed_body and '"' not in fixed_body:
            fixed_body = fixed_body.replace("'", '"')
            if fixed_body != original_body:
                fixes_applied.append("fixed_json_quotes")
        
        # Fix trailing commas
        fixed_body = re.sub(r',(\s*[}\]])', r'\1', fixed_body)
        if fixed_body != original_body:
            fixes_applied.append("removed_trailing_commas")
        
        # Try to parse and re-serialize for formatting
        try:
            parsed = json.loads(fixed_body)
            fixed_body = json.dumps(parsed)
            if "reformatted_json" not in fixes_applied:
                fixes_applied.append("reformatted_json")
        except Exception:
            pass
    
    return fixed_headers, fixed_body, fixes_applied


def detect_source_dialect(envelope: RequestEnvelope, error_type: ErrorType) -> str:
    """Detect the source dialect based on request characteristics."""
    user_agent = envelope.raw_headers.get("user-agent", "").lower()
    
    # Known AI sources
    if "claude" in user_agent or "anthropic" in user_agent:
        return "claude_style"
    elif "gpt" in user_agent or "openai" in user_agent:
        return "openai_style"
    elif "google" in user_agent or "googlebot" in user_agent:
        return "google_style"
    elif "bing" in user_agent:
        return "bing_style"
    
    # Scanner patterns
    scanner_indicators = ["nikto", "sqlmap", "nmap", "burp", "nuclei", "wpscan"]
    if any(s in user_agent for s in scanner_indicators):
        return "scanner_style"
    
    # Crawler patterns
    if "bot" in user_agent or "crawler" in user_agent or "spider" in user_agent:
        return "crawler_style"
    
    # Python/curl/etc
    if "python" in user_agent:
        return "python_style"
    elif "curl" in user_agent:
        return "curl_style"
    elif "go-http" in user_agent:
        return "go_style"
    
    return "unknown_style"


def update_dialect_stats(
    source_dialect: str,
    error_type: ErrorType,
    repair_success: bool,
) -> None:
    """Update error dialect statistics."""
    now = datetime.now(timezone.utc).isoformat()
    
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM error_dialects WHERE source_type = ?",
            (source_dialect,)
        ).fetchone()
        
        if row:
            # Update existing
            common_errors = json.loads(row["common_errors"])
            error_freqs = json.loads(row["error_freqs"])
            
            if error_type.value not in common_errors:
                common_errors.append(error_type.value)
            
            error_freqs[error_type.value] = error_freqs.get(error_type.value, 0) + 1
            
            total_errors = row["total_errors"] + 1
            successful_repairs = row["successful_repairs"] + (1 if repair_success else 0)
            
            conn.execute(
                """
                UPDATE error_dialects SET
                    common_errors = ?,
                    error_freqs = ?,
                    total_errors = ?,
                    successful_repairs = ?,
                    last_updated = ?
                WHERE source_type = ?
                """,
                (
                    json.dumps(common_errors),
                    json.dumps(error_freqs),
                    total_errors,
                    successful_repairs,
                    now,
                    source_dialect,
                )
            )
        else:
            # Create new
            dialect_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO error_dialects (
                    dialect_id, source_type, common_errors, error_freqs,
                    total_errors, successful_repairs, first_observed, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dialect_id,
                    source_dialect,
                    json.dumps([error_type.value]),
                    json.dumps({error_type.value: 1}),
                    1,
                    1 if repair_success else 0,
                    now,
                    now,
                )
            )
        
        conn.commit()


async def repair_error(envelope: RequestEnvelope) -> RepairResult:
    """
    Main Error Eyes repair pipeline.
    
    Attempts to fix broken requests and learn from failures.
    """
    result_id = str(uuid.uuid4())
    
    # Detect error type
    error_type = detect_error_type(envelope)
    
    # Detect source dialect
    source_dialect = detect_source_dialect(envelope, error_type)
    
    # Try quick automatic fixes
    fixed_headers, fixed_body, fixes_applied = try_quick_fixes(envelope)
    
    # Determine if we made progress
    quick_fix_success = len(fixes_applied) > 0
    
    # Use AI for more complex repairs if needed
    ai_result = None
    if not quick_fix_success or error_type in [ErrorType.SCHEMA_MISMATCH, ErrorType.MISSING_FIELDS]:
        try:
            context = {
                "error_type": error_type.value,
                "error_code": envelope.error_code,
                "error_message": envelope.error_type,
                "method": envelope.raw_method,
                "path": envelope.raw_path,
                "headers": dict(list(envelope.raw_headers.items())[:15]),
                "body_preview": (envelope.raw_body_text or "")[:500],
                "source_dialect": source_dialect,
            }
            
            response = await _get_client().chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(context)},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            
            ai_result = json.loads(response.choices[0].message.content)
            
            # Apply AI fixes
            if ai_result.get("fixes"):
                for fix in ai_result["fixes"]:
                    fix_type = fix.get("type", "")
                    if fix_type not in fixes_applied:
                        fixes_applied.append(f"ai_{fix_type}")
            
            if ai_result.get("repaired_headers"):
                fixed_headers.update(ai_result["repaired_headers"])
            
            if ai_result.get("repaired_body"):
                fixed_body = ai_result["repaired_body"]
            
        except Exception:
            pass  # AI repair is optional
    
    # Calculate repair confidence
    repair_confidence = 0.0
    if fixes_applied:
        repair_confidence = min(len(fixes_applied) * 0.2, 0.8)
    if ai_result and ai_result.get("repair_confidence"):
        repair_confidence = max(repair_confidence, ai_result["repair_confidence"])
    
    repair_success = len(fixes_applied) > 0 and repair_confidence > 0.3
    
    # Update dialect statistics
    update_dialect_stats(source_dialect, error_type, repair_success)
    
    # Build result
    result = RepairResult(
        result_id=result_id,
        envelope_id=envelope.envelope_id,
        error_type=error_type,
        error_code=envelope.error_code,
        error_message=envelope.error_type,
        repair_success=repair_success,
        repair_confidence=repair_confidence,
        repaired_method=ai_result.get("repaired_method") if ai_result else envelope.raw_method,
        repaired_path=ai_result.get("repaired_path") if ai_result else envelope.raw_path,
        repaired_headers=fixed_headers,
        repaired_body=fixed_body,
        fixes_applied=fixes_applied,
        error_pattern=ai_result.get("error_pattern") if ai_result else None,
        source_dialect=source_dialect,
        processed_at=datetime.now(timezone.utc),
    )
    
    # Log repair attempt
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO repair_history (
                repair_id, envelope_id, error_type, repair_success,
                fixes_applied, source_dialect, processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id,
                envelope.envelope_id,
                error_type.value,
                repair_success,
                json.dumps(fixes_applied),
                source_dialect,
                datetime.now(timezone.utc).isoformat(),
            )
        )
        conn.commit()
    
    return result


def get_dialect_stats(source_type: str | None = None) -> list[ErrorDialect]:
    """Get error dialect statistics."""
    with _db() as conn:
        if source_type:
            rows = conn.execute(
                "SELECT * FROM error_dialects WHERE source_type = ?",
                (source_type,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM error_dialects ORDER BY total_errors DESC"
            ).fetchall()
        
        return [
            ErrorDialect(
                dialect_id=row["dialect_id"],
                source_type=row["source_type"],
                common_errors=[ErrorType(e) for e in json.loads(row["common_errors"])],
                error_frequencies=json.loads(row["error_freqs"]),
                total_errors_seen=row["total_errors"],
                successful_repairs=row["successful_repairs"],
                repair_success_rate=row["successful_repairs"] / max(row["total_errors"], 1),
                first_observed=datetime.fromisoformat(row["first_observed"]),
                last_updated=datetime.fromisoformat(row["last_updated"]),
            )
            for row in rows
        ]
