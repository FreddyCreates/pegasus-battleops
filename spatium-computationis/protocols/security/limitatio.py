"""
Protocol: Limitatio  ⚡
Meaning: Control request rates and prevent abuse.

Handles:
- Rate limiting by IP, user, or API key
- Quota management
- Burst allowance
- Distributed rate limiting
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class RateLimitScope(str, Enum):
    """Scope for rate limiting."""
    GLOBAL = "global"
    IP = "ip"
    USER = "user"
    API_KEY = "api_key"
    ENDPOINT = "endpoint"


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""
    scope: RateLimitScope
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    
    # Limits
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    
    # Burst allowance
    burst_size: int = 10
    
    # Penalties
    penalty_duration_seconds: int = 60
    max_penalties: int = 5
    
    # Custom rules
    custom_limits: dict[str, int] = Field(default_factory=dict)


class RateLimitResult(BaseModel):
    """Result of a rate limit check."""
    request_id: str
    scope: RateLimitScope
    identifier: str  # IP, user ID, etc.
    
    # Status
    allowed: bool
    remaining: int
    limit: int
    reset_at: datetime
    
    # Headers for response
    headers: dict[str, str] = Field(default_factory=dict)
    
    # If blocked
    retry_after_seconds: int | None = None
    penalty_count: int = 0
    
    # Metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "ratelimit.db"


def _init_ratelimit_db() -> None:
    """Initialize the rate limit database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Request counts (sliding window)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS request_counts (
                identifier      TEXT NOT NULL,
                scope           TEXT NOT NULL,
                window_start    TEXT NOT NULL,
                count           INTEGER DEFAULT 1,
                PRIMARY KEY (identifier, scope, window_start)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rc_id ON request_counts(identifier)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rc_window ON request_counts(window_start)")
        
        # Penalties
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS penalties (
                identifier      TEXT PRIMARY KEY,
                penalty_count   INTEGER DEFAULT 1,
                blocked_until   TEXT NOT NULL,
                first_penalty   TEXT NOT NULL,
                last_penalty    TEXT NOT NULL
            )
            """
        )
        
        # Quotas
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quotas (
                identifier      TEXT NOT NULL,
                quota_type      TEXT NOT NULL,
                used            INTEGER DEFAULT 0,
                limit_value     INTEGER NOT NULL,
                reset_at        TEXT NOT NULL,
                PRIMARY KEY (identifier, quota_type)
            )
            """
        )
        
        # Rate limit configurations (per identifier)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rate_configs (
                identifier      TEXT PRIMARY KEY,
                config          TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )
            """
        )
        
        conn.commit()


_init_ratelimit_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Default Configuration
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = RateLimitConfig(
    scope=RateLimitScope.IP,
    requests_per_minute=60,
    requests_per_hour=1000,
    requests_per_day=10000,
    burst_size=10,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def check_rate_limit(
    identifier: str,
    scope: RateLimitScope = RateLimitScope.IP,
    config: RateLimitConfig | None = None,
) -> RateLimitResult:
    """
    Protocol Limitatio: check if a request should be rate limited.
    """
    request_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    cfg = config or DEFAULT_CONFIG
    
    # Check if currently penalized
    penalty_info = _check_penalty(identifier)
    if penalty_info:
        blocked_until, penalty_count = penalty_info
        if blocked_until > now:
            return RateLimitResult(
                request_id=request_id,
                scope=scope,
                identifier=identifier,
                allowed=False,
                remaining=0,
                limit=cfg.requests_per_minute,
                reset_at=blocked_until,
                retry_after_seconds=int((blocked_until - now).total_seconds()),
                penalty_count=penalty_count,
                headers={
                    "X-RateLimit-Limit": str(cfg.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(blocked_until.timestamp())),
                    "Retry-After": str(int((blocked_until - now).total_seconds())),
                },
            )
    
    # Get current count for this minute
    minute_start = now.replace(second=0, microsecond=0)
    current_count = _get_request_count(identifier, scope, minute_start)
    
    # Check against limit
    if current_count >= cfg.requests_per_minute:
        # Apply penalty
        penalty_count = _apply_penalty(identifier, cfg.penalty_duration_seconds)
        blocked_until = now + timedelta(seconds=cfg.penalty_duration_seconds)
        
        return RateLimitResult(
            request_id=request_id,
            scope=scope,
            identifier=identifier,
            allowed=False,
            remaining=0,
            limit=cfg.requests_per_minute,
            reset_at=minute_start + timedelta(minutes=1),
            retry_after_seconds=cfg.penalty_duration_seconds,
            penalty_count=penalty_count,
            headers={
                "X-RateLimit-Limit": str(cfg.requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int((minute_start + timedelta(minutes=1)).timestamp())),
                "Retry-After": str(cfg.penalty_duration_seconds),
            },
        )
    
    # Allow the request
    remaining = cfg.requests_per_minute - current_count - 1
    reset_at = minute_start + timedelta(minutes=1)
    
    return RateLimitResult(
        request_id=request_id,
        scope=scope,
        identifier=identifier,
        allowed=True,
        remaining=max(0, remaining),
        limit=cfg.requests_per_minute,
        reset_at=reset_at,
        headers={
            "X-RateLimit-Limit": str(cfg.requests_per_minute),
            "X-RateLimit-Remaining": str(max(0, remaining)),
            "X-RateLimit-Reset": str(int(reset_at.timestamp())),
        },
    )


async def record_request(
    identifier: str,
    scope: RateLimitScope = RateLimitScope.IP,
) -> None:
    """Record a request for rate limiting."""
    now = datetime.now(timezone.utc)
    window_start = now.replace(second=0, microsecond=0).isoformat()
    
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO request_counts (identifier, scope, window_start, count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(identifier, scope, window_start) DO UPDATE SET count = count + 1
            """,
            (identifier, scope.value, window_start)
        )
        conn.commit()


def _get_request_count(
    identifier: str,
    scope: RateLimitScope,
    window_start: datetime,
) -> int:
    """Get the request count for a window."""
    with _db() as conn:
        row = conn.execute(
            "SELECT count FROM request_counts WHERE identifier = ? AND scope = ? AND window_start = ?",
            (identifier, scope.value, window_start.isoformat())
        ).fetchone()
        
        return row["count"] if row else 0


def _check_penalty(identifier: str) -> tuple[datetime, int] | None:
    """Check if identifier is currently penalized."""
    with _db() as conn:
        row = conn.execute(
            "SELECT blocked_until, penalty_count FROM penalties WHERE identifier = ?",
            (identifier,)
        ).fetchone()
        
        if row:
            blocked_until = datetime.fromisoformat(row["blocked_until"])
            return blocked_until, row["penalty_count"]
        return None


def _apply_penalty(identifier: str, duration_seconds: int) -> int:
    """Apply a penalty to an identifier."""
    now = datetime.now(timezone.utc)
    blocked_until = now + timedelta(seconds=duration_seconds)
    
    with _db() as conn:
        row = conn.execute(
            "SELECT penalty_count FROM penalties WHERE identifier = ?",
            (identifier,)
        ).fetchone()
        
        if row:
            new_count = row["penalty_count"] + 1
            # Exponential backoff
            extended_duration = duration_seconds * (2 ** min(new_count - 1, 5))
            blocked_until = now + timedelta(seconds=extended_duration)
            
            conn.execute(
                "UPDATE penalties SET penalty_count = ?, blocked_until = ?, last_penalty = ? WHERE identifier = ?",
                (new_count, blocked_until.isoformat(), now.isoformat(), identifier)
            )
            conn.commit()
            return new_count
        else:
            conn.execute(
                "INSERT INTO penalties (identifier, penalty_count, blocked_until, first_penalty, last_penalty) VALUES (?, 1, ?, ?, ?)",
                (identifier, blocked_until.isoformat(), now.isoformat(), now.isoformat())
            )
            conn.commit()
            return 1


async def reset_penalty(identifier: str) -> bool:
    """Reset penalties for an identifier."""
    with _db() as conn:
        cursor = conn.execute(
            "DELETE FROM penalties WHERE identifier = ?",
            (identifier,)
        )
        conn.commit()
        return cursor.rowcount > 0


async def get_quota_status(
    identifier: str,
    quota_type: str,
) -> dict[str, Any]:
    """Get current quota status."""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM quotas WHERE identifier = ? AND quota_type = ?",
            (identifier, quota_type)
        ).fetchone()
        
        if row:
            return {
                "used": row["used"],
                "limit": row["limit_value"],
                "remaining": max(0, row["limit_value"] - row["used"]),
                "reset_at": row["reset_at"],
            }
        return {
            "used": 0,
            "limit": 0,
            "remaining": 0,
            "reset_at": None,
        }


async def set_custom_limit(
    identifier: str,
    config: RateLimitConfig,
) -> None:
    """Set a custom rate limit configuration for an identifier."""
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO rate_configs (identifier, config, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(identifier) DO UPDATE SET config = ?, updated_at = ?
            """,
            (
                identifier,
                config.model_dump_json(),
                now.isoformat(),
                now.isoformat(),
                config.model_dump_json(),
                now.isoformat(),
            )
        )
        conn.commit()


async def cleanup_old_records(older_than_hours: int = 24) -> int:
    """Clean up old rate limit records."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
    
    with _db() as conn:
        cursor = conn.execute(
            "DELETE FROM request_counts WHERE window_start < ?",
            (cutoff.isoformat(),)
        )
        conn.commit()
        return cursor.rowcount
