"""
Protocol: Authenticatio  🔐
Meaning: Verify the identity of incoming requests.

Handles:
- API key validation
- JWT token verification
- Session management
- Identity extraction
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class AuthMethod(str, Enum):
    """Supported authentication methods."""
    API_KEY = "api_key"
    JWT = "jwt"
    SESSION = "session"
    BASIC = "basic"
    OAUTH2 = "oauth2"
    INTERNAL = "internal"


class AuthStatus(str, Enum):
    """Authentication result status."""
    SUCCESS = "success"
    INVALID_CREDENTIALS = "invalid_credentials"
    EXPIRED = "expired"
    REVOKED = "revoked"
    MISSING_CREDENTIALS = "missing_credentials"
    INVALID_FORMAT = "invalid_format"
    RATE_LIMITED = "rate_limited"


class TokenPayload(BaseModel):
    """Extracted token payload after authentication."""
    subject: str  # User or service ID
    issuer: str = "spatium_computationis"
    audience: str = "api"
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    scopes: list[str] = Field(default_factory=list)
    claims: dict[str, Any] = Field(default_factory=dict)


class AuthenticationResult(BaseModel):
    """Result of an authentication attempt."""
    request_id: str
    auth_method: AuthMethod
    status: AuthStatus
    authenticated: bool = False
    token_payload: TokenPayload | None = None
    
    # Metadata
    client_ip: str | None = None
    user_agent: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Error details
    error_message: str | None = None
    retry_after_seconds: int | None = None


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "auth.db"


def _init_auth_db() -> None:
    """Initialize the authentication database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # API keys
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                key_hash        TEXT PRIMARY KEY,
                key_prefix      TEXT NOT NULL,
                subject         TEXT NOT NULL,
                scopes          TEXT DEFAULT '[]',
                rate_limit      INTEGER DEFAULT 1000,
                active          INTEGER DEFAULT 1,
                created_at      TEXT NOT NULL,
                expires_at      TEXT,
                last_used_at    TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ak_subject ON api_keys(subject)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ak_prefix ON api_keys(key_prefix)")
        
        # Sessions
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id      TEXT PRIMARY KEY,
                subject         TEXT NOT NULL,
                token_hash      TEXT NOT NULL,
                scopes          TEXT DEFAULT '[]',
                created_at      TEXT NOT NULL,
                expires_at      TEXT NOT NULL,
                last_activity   TEXT NOT NULL,
                revoked         INTEGER DEFAULT 0
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sess_subject ON sessions(subject)")
        
        # Auth attempts (for rate limiting and audit)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_attempts (
                attempt_id      TEXT PRIMARY KEY,
                subject         TEXT,
                client_ip       TEXT,
                auth_method     TEXT NOT NULL,
                status          TEXT NOT NULL,
                timestamp       TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_aa_ip ON auth_attempts(client_ip)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_aa_timestamp ON auth_attempts(timestamp)")
        
        conn.commit()


_init_auth_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# API Key Authentication
# ---------------------------------------------------------------------------

def _hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def _get_key_prefix(api_key: str) -> str:
    """Get the prefix of an API key for identification."""
    return api_key[:8] if len(api_key) >= 8 else api_key


async def validate_api_key(api_key: str) -> tuple[bool, TokenPayload | None, str | None]:
    """Validate an API key and return the associated payload."""
    key_hash = _hash_api_key(api_key)
    
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key_hash = ? AND active = 1",
            (key_hash,)
        ).fetchone()
        
        if not row:
            return False, None, "Invalid API key"
        
        # Check expiration
        if row["expires_at"]:
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at < datetime.now(timezone.utc):
                return False, None, "API key expired"
        
        # Update last used
        conn.execute(
            "UPDATE api_keys SET last_used_at = ? WHERE key_hash = ?",
            (datetime.now(timezone.utc).isoformat(), key_hash)
        )
        conn.commit()
        
        scopes = json.loads(row["scopes"]) if row["scopes"] else []
        
        payload = TokenPayload(
            subject=row["subject"],
            scopes=scopes,
            issued_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
        )
        
        return True, payload, None


# ---------------------------------------------------------------------------
# JWT Verification (Simplified)
# ---------------------------------------------------------------------------

SECRET_KEY = "spatium-computationis-secret-key-change-in-production"


def _verify_jwt(token: str) -> tuple[bool, dict | None, str | None]:
    """Verify a JWT token (simplified implementation)."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return False, None, "Invalid token format"
        
        header_b64, payload_b64, signature = parts
        
        # Verify signature
        import base64
        message = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(SECRET_KEY.encode(), message, hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).rstrip(b"=").decode()
        
        if not hmac.compare_digest(signature, expected_sig_b64):
            return False, None, "Invalid signature"
        
        # Decode payload
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_bytes)
        
        # Check expiration
        if "exp" in payload:
            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            if exp < datetime.now(timezone.utc):
                return False, None, "Token expired"
        
        return True, payload, None
        
    except Exception as e:
        return False, None, f"Token verification failed: {str(e)}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def authenticate_request(
    auth_header: str | None = None,
    api_key: str | None = None,
    session_token: str | None = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> AuthenticationResult:
    """
    Protocol Authenticatio: authenticate an incoming request.
    
    Tries authentication methods in order of preference:
    1. API key (if provided)
    2. Bearer token from Authorization header
    3. Session token
    """
    request_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Try API key first
    if api_key:
        valid, payload, error = await validate_api_key(api_key)
        result = AuthenticationResult(
            request_id=request_id,
            auth_method=AuthMethod.API_KEY,
            status=AuthStatus.SUCCESS if valid else AuthStatus.INVALID_CREDENTIALS,
            authenticated=valid,
            token_payload=payload,
            client_ip=client_ip,
            user_agent=user_agent,
            error_message=error,
        )
        _log_attempt(result)
        return result
    
    # Try Bearer token
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        valid, payload_dict, error = _verify_jwt(token)
        
        payload = None
        if valid and payload_dict:
            payload = TokenPayload(
                subject=payload_dict.get("sub", "unknown"),
                issuer=payload_dict.get("iss", "spatium_computationis"),
                audience=payload_dict.get("aud", "api"),
                scopes=payload_dict.get("scopes", []),
                claims=payload_dict,
            )
        
        result = AuthenticationResult(
            request_id=request_id,
            auth_method=AuthMethod.JWT,
            status=AuthStatus.SUCCESS if valid else AuthStatus.INVALID_CREDENTIALS,
            authenticated=valid,
            token_payload=payload,
            client_ip=client_ip,
            user_agent=user_agent,
            error_message=error,
        )
        _log_attempt(result)
        return result
    
    # Try session token
    if session_token:
        valid, payload, error = await _validate_session(session_token)
        result = AuthenticationResult(
            request_id=request_id,
            auth_method=AuthMethod.SESSION,
            status=AuthStatus.SUCCESS if valid else AuthStatus.INVALID_CREDENTIALS,
            authenticated=valid,
            token_payload=payload,
            client_ip=client_ip,
            user_agent=user_agent,
            error_message=error,
        )
        _log_attempt(result)
        return result
    
    # No credentials provided
    return AuthenticationResult(
        request_id=request_id,
        auth_method=AuthMethod.API_KEY,
        status=AuthStatus.MISSING_CREDENTIALS,
        authenticated=False,
        client_ip=client_ip,
        user_agent=user_agent,
        error_message="No authentication credentials provided",
    )


async def _validate_session(session_token: str) -> tuple[bool, TokenPayload | None, str | None]:
    """Validate a session token."""
    token_hash = hashlib.sha256(session_token.encode()).hexdigest()
    
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE token_hash = ? AND revoked = 0",
            (token_hash,)
        ).fetchone()
        
        if not row:
            return False, None, "Invalid or revoked session"
        
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at < datetime.now(timezone.utc):
            return False, None, "Session expired"
        
        # Update last activity
        conn.execute(
            "UPDATE sessions SET last_activity = ? WHERE session_id = ?",
            (datetime.now(timezone.utc).isoformat(), row["session_id"])
        )
        conn.commit()
        
        scopes = json.loads(row["scopes"]) if row["scopes"] else []
        
        payload = TokenPayload(
            subject=row["subject"],
            scopes=scopes,
            issued_at=datetime.fromisoformat(row["created_at"]),
            expires_at=expires_at,
        )
        
        return True, payload, None


def _log_attempt(result: AuthenticationResult) -> None:
    """Log an authentication attempt."""
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO auth_attempts (attempt_id, subject, client_ip, auth_method, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                result.token_payload.subject if result.token_payload else None,
                result.client_ip,
                result.auth_method.value,
                result.status.value,
                result.timestamp.isoformat(),
            )
        )
        conn.commit()


async def validate_token(token: str, expected_type: AuthMethod = AuthMethod.JWT) -> AuthenticationResult:
    """Validate a specific token type."""
    if expected_type == AuthMethod.JWT:
        return await authenticate_request(auth_header=f"Bearer {token}")
    elif expected_type == AuthMethod.API_KEY:
        return await authenticate_request(api_key=token)
    elif expected_type == AuthMethod.SESSION:
        return await authenticate_request(session_token=token)
    else:
        return AuthenticationResult(
            request_id=str(uuid.uuid4()),
            auth_method=expected_type,
            status=AuthStatus.INVALID_FORMAT,
            authenticated=False,
            error_message=f"Unsupported auth method: {expected_type}",
        )
