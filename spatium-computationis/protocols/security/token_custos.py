"""
Protocol: Token Custos  🎫
Meaning: Manage authentication tokens.

Handles:
- Token generation
- Token refresh
- Token revocation
- Token introspection
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class TokenType(str, Enum):
    """Types of tokens."""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    SESSION = "session"
    TEMPORARY = "temporary"


class TokenStatus(str, Enum):
    """Token status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ROTATED = "rotated"


class TokenInfo(BaseModel):
    """Information about a token."""
    token_id: str
    token_type: TokenType
    subject: str
    scopes: list[str] = Field(default_factory=list)
    status: TokenStatus = TokenStatus.ACTIVE
    
    # Timing
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    
    # Metadata
    client_id: str | None = None
    issuer: str = "spatium_computationis"
    audience: str = "api"
    claims: dict[str, Any] = Field(default_factory=dict)


class TokenCreationResult(BaseModel):
    """Result of token creation."""
    success: bool
    token: str | None = None
    token_info: TokenInfo | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "tokens.db"


def _init_token_db() -> None:
    """Initialize the token database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Tokens
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tokens (
                token_id        TEXT PRIMARY KEY,
                token_hash      TEXT UNIQUE NOT NULL,
                token_type      TEXT NOT NULL,
                subject         TEXT NOT NULL,
                scopes          TEXT DEFAULT '[]',
                status          TEXT DEFAULT 'active',
                issued_at       TEXT NOT NULL,
                expires_at      TEXT,
                last_used_at    TEXT,
                client_id       TEXT,
                issuer          TEXT DEFAULT 'spatium_computationis',
                audience        TEXT DEFAULT 'api',
                claims          TEXT DEFAULT '{}',
                refresh_token_id TEXT,
                revoked_at      TEXT,
                revoked_reason  TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tok_hash ON tokens(token_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tok_subject ON tokens(subject)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tok_status ON tokens(status)")
        
        # Refresh tokens
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                refresh_id      TEXT PRIMARY KEY,
                token_hash      TEXT UNIQUE NOT NULL,
                access_token_id TEXT NOT NULL,
                subject         TEXT NOT NULL,
                issued_at       TEXT NOT NULL,
                expires_at      TEXT,
                used            INTEGER DEFAULT 0,
                used_at         TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rt_hash ON refresh_tokens(token_hash)")
        
        conn.commit()


_init_token_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Token Generation
# ---------------------------------------------------------------------------

SECRET_KEY = "spatium-token-secret-change-in-production"


def _generate_token(length: int = 32) -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(length)


def _hash_token(token: str) -> str:
    """Hash a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def _create_jwt(payload: dict, expires_in_seconds: int) -> str:
    """Create a simple JWT-like token."""
    header = {"alg": "HS256", "typ": "JWT"}
    
    now = datetime.now(timezone.utc)
    payload["iat"] = int(now.timestamp())
    payload["exp"] = int((now + timedelta(seconds=expires_in_seconds)).timestamp())
    
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def create_token(
    subject: str,
    token_type: TokenType = TokenType.ACCESS,
    scopes: list[str] | None = None,
    expires_in_seconds: int = 3600,
    client_id: str | None = None,
    claims: dict[str, Any] | None = None,
    include_refresh: bool = True,
) -> TokenCreationResult:
    """
    Protocol Token Custos: create a new token.
    """
    token_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=expires_in_seconds)
    
    effective_scopes = scopes or ["read"]
    effective_claims = claims or {}
    
    try:
        if token_type == TokenType.API_KEY:
            # API keys are opaque tokens
            token = f"sk_{_generate_token(32)}"
        elif token_type == TokenType.SESSION:
            token = _generate_token(48)
        else:
            # Access tokens are JWTs
            jwt_payload = {
                "sub": subject,
                "jti": token_id,
                "scopes": effective_scopes,
                "aud": "api",
                "iss": "spatium_computationis",
                **effective_claims,
            }
            token = _create_jwt(jwt_payload, expires_in_seconds)
        
        token_hash = _hash_token(token)
        
        # Store token
        with _db() as conn:
            conn.execute(
                """
                INSERT INTO tokens (
                    token_id, token_hash, token_type, subject, scopes, status,
                    issued_at, expires_at, client_id, issuer, audience, claims
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    token_id,
                    token_hash,
                    token_type.value,
                    subject,
                    json.dumps(effective_scopes),
                    TokenStatus.ACTIVE.value,
                    now.isoformat(),
                    expires_at.isoformat(),
                    client_id,
                    "spatium_computationis",
                    "api",
                    json.dumps(effective_claims),
                )
            )
            
            # Create refresh token if requested
            refresh_token = None
            if include_refresh and token_type == TokenType.ACCESS:
                refresh_id = str(uuid.uuid4())
                refresh_token = _generate_token(48)
                refresh_hash = _hash_token(refresh_token)
                refresh_expires = now + timedelta(days=30)
                
                conn.execute(
                    """
                    INSERT INTO refresh_tokens (
                        refresh_id, token_hash, access_token_id, subject, issued_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        refresh_id,
                        refresh_hash,
                        token_id,
                        subject,
                        now.isoformat(),
                        refresh_expires.isoformat(),
                    )
                )
                
                # Update access token with refresh reference
                conn.execute(
                    "UPDATE tokens SET refresh_token_id = ? WHERE token_id = ?",
                    (refresh_id, token_id)
                )
            
            conn.commit()
        
        token_info = TokenInfo(
            token_id=token_id,
            token_type=token_type,
            subject=subject,
            scopes=effective_scopes,
            status=TokenStatus.ACTIVE,
            issued_at=now,
            expires_at=expires_at,
            client_id=client_id,
            claims=effective_claims,
        )
        
        # Include refresh token in response if created
        final_token = token
        if refresh_token:
            final_token = json.dumps({
                "access_token": token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": expires_in_seconds,
            })
        
        return TokenCreationResult(
            success=True,
            token=final_token,
            token_info=token_info,
        )
        
    except Exception as e:
        return TokenCreationResult(
            success=False,
            error=str(e),
        )


async def revoke_token(
    token: str | None = None,
    token_id: str | None = None,
    reason: str | None = None,
) -> bool:
    """
    Protocol Token Custos: revoke a token.
    """
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        if token:
            token_hash = _hash_token(token)
            cursor = conn.execute(
                """
                UPDATE tokens SET status = ?, revoked_at = ?, revoked_reason = ?
                WHERE token_hash = ? AND status = ?
                """,
                (TokenStatus.REVOKED.value, now.isoformat(), reason, token_hash, TokenStatus.ACTIVE.value)
            )
        elif token_id:
            cursor = conn.execute(
                """
                UPDATE tokens SET status = ?, revoked_at = ?, revoked_reason = ?
                WHERE token_id = ? AND status = ?
                """,
                (TokenStatus.REVOKED.value, now.isoformat(), reason, token_id, TokenStatus.ACTIVE.value)
            )
        else:
            return False
        
        conn.commit()
        return cursor.rowcount > 0


async def refresh_token(
    refresh_token_value: str,
    expires_in_seconds: int = 3600,
) -> TokenCreationResult:
    """
    Protocol Token Custos: refresh an access token.
    """
    token_hash = _hash_token(refresh_token_value)
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        # Find refresh token
        row = conn.execute(
            """
            SELECT rt.*, t.subject, t.scopes, t.client_id, t.claims
            FROM refresh_tokens rt
            JOIN tokens t ON rt.access_token_id = t.token_id
            WHERE rt.token_hash = ? AND rt.used = 0
            """,
            (token_hash,)
        ).fetchone()
        
        if not row:
            return TokenCreationResult(
                success=False,
                error="Invalid or already used refresh token",
            )
        
        # Check expiration
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at < now:
            return TokenCreationResult(
                success=False,
                error="Refresh token expired",
            )
        
        # Mark refresh token as used
        conn.execute(
            "UPDATE refresh_tokens SET used = 1, used_at = ? WHERE refresh_id = ?",
            (now.isoformat(), row["refresh_id"])
        )
        
        # Revoke old access token
        conn.execute(
            "UPDATE tokens SET status = ? WHERE token_id = ?",
            (TokenStatus.ROTATED.value, row["access_token_id"])
        )
        
        conn.commit()
    
    # Create new token pair
    scopes = json.loads(row["scopes"]) if row["scopes"] else []
    claims = json.loads(row["claims"]) if row["claims"] else {}
    
    return await create_token(
        subject=row["subject"],
        token_type=TokenType.ACCESS,
        scopes=scopes,
        expires_in_seconds=expires_in_seconds,
        client_id=row["client_id"],
        claims=claims,
        include_refresh=True,
    )


async def introspect_token(token: str) -> TokenInfo | None:
    """
    Protocol Token Custos: get information about a token.
    """
    token_hash = _hash_token(token)
    
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM tokens WHERE token_hash = ?",
            (token_hash,)
        ).fetchone()
        
        if not row:
            return None
        
        return TokenInfo(
            token_id=row["token_id"],
            token_type=TokenType(row["token_type"]),
            subject=row["subject"],
            scopes=json.loads(row["scopes"]) if row["scopes"] else [],
            status=TokenStatus(row["status"]),
            issued_at=datetime.fromisoformat(row["issued_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            last_used_at=datetime.fromisoformat(row["last_used_at"]) if row["last_used_at"] else None,
            client_id=row["client_id"],
            issuer=row["issuer"],
            audience=row["audience"],
            claims=json.loads(row["claims"]) if row["claims"] else {},
        )


async def revoke_all_tokens(subject: str, reason: str | None = None) -> int:
    """Revoke all tokens for a subject."""
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        cursor = conn.execute(
            """
            UPDATE tokens SET status = ?, revoked_at = ?, revoked_reason = ?
            WHERE subject = ? AND status = ?
            """,
            (TokenStatus.REVOKED.value, now.isoformat(), reason, subject, TokenStatus.ACTIVE.value)
        )
        conn.commit()
        return cursor.rowcount


async def cleanup_expired_tokens(older_than_days: int = 30) -> int:
    """Clean up expired tokens."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    
    with _db() as conn:
        cursor = conn.execute(
            "DELETE FROM tokens WHERE expires_at < ? AND status != ?",
            (cutoff.isoformat(), TokenStatus.ACTIVE.value)
        )
        conn.commit()
        return cursor.rowcount
