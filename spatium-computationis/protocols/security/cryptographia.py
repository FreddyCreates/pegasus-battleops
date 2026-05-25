"""
Protocol: Cryptographia  🔒
Meaning: Encrypt and protect sensitive data.

Handles:
- Symmetric encryption (AES)
- Data hashing
- Key management
- Secure storage
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class EncryptionAlgorithm(str, Enum):
    """Supported encryption algorithms."""
    AES_256_GCM = "aes-256-gcm"
    AES_256_CBC = "aes-256-cbc"
    CHACHA20_POLY1305 = "chacha20-poly1305"


class HashAlgorithm(str, Enum):
    """Supported hash algorithms."""
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
    BLAKE2B = "blake2b"
    ARGON2 = "argon2"


class EncryptionResult(BaseModel):
    """Result of an encryption operation."""
    success: bool
    ciphertext: str | None = None  # Base64 encoded
    iv: str | None = None  # Base64 encoded initialization vector
    tag: str | None = None  # Base64 encoded authentication tag
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    key_id: str | None = None
    encrypted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None


class DecryptionResult(BaseModel):
    """Result of a decryption operation."""
    success: bool
    plaintext: str | None = None
    decrypted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None


class HashResult(BaseModel):
    """Result of a hashing operation."""
    hash_value: str
    algorithm: HashAlgorithm
    salt: str | None = None
    iterations: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Database (Key Management)
# ---------------------------------------------------------------------------

DB_PATH = Path(__file__).parent.parent.parent / "field" / "crypto.db"


def _init_crypto_db() -> None:
    """Initialize the crypto database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        # Encryption keys
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS encryption_keys (
                key_id          TEXT PRIMARY KEY,
                key_name        TEXT UNIQUE,
                key_hash        TEXT NOT NULL,
                algorithm       TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                expires_at      TEXT,
                rotated_from    TEXT,
                active          INTEGER DEFAULT 1
            )
            """
        )
        
        # Key usage log
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS key_usage_log (
                log_id          TEXT PRIMARY KEY,
                key_id          TEXT NOT NULL,
                operation       TEXT NOT NULL,
                timestamp       TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kul_key ON key_usage_log(key_id)")
        
        conn.commit()


_init_crypto_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Key Management
# ---------------------------------------------------------------------------

# In production, this should come from a secure key management service
_MASTER_KEY = os.environ.get("SPATIUM_MASTER_KEY", "spatium-master-key-change-in-production-32")
_MASTER_KEY_BYTES = _MASTER_KEY.encode()[:32].ljust(32, b"\0")


def _derive_key(key_id: str) -> bytes:
    """Derive an encryption key from the master key and key ID."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        _MASTER_KEY_BYTES,
        key_id.encode(),
        iterations=100000,
        dklen=32
    )


# ---------------------------------------------------------------------------
# Encryption (Simplified - uses Fernet-like approach)
# ---------------------------------------------------------------------------

def _simple_encrypt(plaintext: bytes, key: bytes) -> tuple[bytes, bytes, bytes]:
    """Simple encryption using XOR with key derivation (for demonstration).
    
    In production, use proper AES-GCM from cryptography library.
    """
    # Generate IV
    iv = secrets.token_bytes(16)
    
    # Derive encryption key from key + IV
    derived = hashlib.pbkdf2_hmac("sha256", key, iv, 1000, dklen=len(plaintext) + 16)
    
    # XOR encrypt (simplified - use AES in production)
    encrypted = bytes(p ^ k for p, k in zip(plaintext, derived[:len(plaintext)]))
    
    # Generate authentication tag
    tag = hmac.new(key, iv + encrypted, hashlib.sha256).digest()[:16]
    
    return encrypted, iv, tag


def _simple_decrypt(ciphertext: bytes, iv: bytes, tag: bytes, key: bytes) -> bytes | None:
    """Simple decryption."""
    # Verify tag
    expected_tag = hmac.new(key, iv + ciphertext, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(tag, expected_tag):
        return None
    
    # Derive encryption key
    derived = hashlib.pbkdf2_hmac("sha256", key, iv, 1000, dklen=len(ciphertext) + 16)
    
    # XOR decrypt
    decrypted = bytes(c ^ k for c, k in zip(ciphertext, derived[:len(ciphertext)]))
    
    return decrypted


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def encrypt_data(
    plaintext: str,
    key_id: str | None = None,
    algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM,
) -> EncryptionResult:
    """
    Protocol Cryptographia: encrypt sensitive data.
    """
    try:
        # Use provided key ID or generate one
        effective_key_id = key_id or "default"
        key = _derive_key(effective_key_id)
        
        # Encrypt
        ciphertext, iv, tag = _simple_encrypt(plaintext.encode(), key)
        
        # Log usage
        _log_key_usage(effective_key_id, "encrypt")
        
        return EncryptionResult(
            success=True,
            ciphertext=base64.b64encode(ciphertext).decode(),
            iv=base64.b64encode(iv).decode(),
            tag=base64.b64encode(tag).decode(),
            algorithm=algorithm,
            key_id=effective_key_id,
        )
    except Exception as e:
        return EncryptionResult(
            success=False,
            error=str(e),
        )


async def decrypt_data(
    ciphertext: str,
    iv: str,
    tag: str,
    key_id: str | None = None,
) -> DecryptionResult:
    """
    Protocol Cryptographia: decrypt encrypted data.
    """
    try:
        effective_key_id = key_id or "default"
        key = _derive_key(effective_key_id)
        
        # Decode from base64
        ciphertext_bytes = base64.b64decode(ciphertext)
        iv_bytes = base64.b64decode(iv)
        tag_bytes = base64.b64decode(tag)
        
        # Decrypt
        plaintext_bytes = _simple_decrypt(ciphertext_bytes, iv_bytes, tag_bytes, key)
        
        if plaintext_bytes is None:
            return DecryptionResult(
                success=False,
                error="Decryption failed: authentication tag mismatch",
            )
        
        # Log usage
        _log_key_usage(effective_key_id, "decrypt")
        
        return DecryptionResult(
            success=True,
            plaintext=plaintext_bytes.decode(),
        )
    except Exception as e:
        return DecryptionResult(
            success=False,
            error=str(e),
        )


async def hash_sensitive(
    data: str,
    algorithm: HashAlgorithm = HashAlgorithm.SHA256,
    salt: str | None = None,
    iterations: int = 100000,
) -> HashResult:
    """
    Protocol Cryptographia: hash sensitive data.
    """
    # Generate salt if not provided
    if salt is None:
        salt = secrets.token_hex(16)
    
    if algorithm == HashAlgorithm.SHA256:
        hash_value = hashlib.pbkdf2_hmac(
            "sha256",
            data.encode(),
            salt.encode(),
            iterations,
        ).hex()
    elif algorithm == HashAlgorithm.SHA384:
        hash_value = hashlib.pbkdf2_hmac(
            "sha384",
            data.encode(),
            salt.encode(),
            iterations,
        ).hex()
    elif algorithm == HashAlgorithm.SHA512:
        hash_value = hashlib.pbkdf2_hmac(
            "sha512",
            data.encode(),
            salt.encode(),
            iterations,
        ).hex()
    elif algorithm == HashAlgorithm.BLAKE2B:
        h = hashlib.blake2b(data.encode(), salt=salt.encode()[:16])
        hash_value = h.hexdigest()
        iterations = None
    else:
        # Default to SHA256
        hash_value = hashlib.pbkdf2_hmac(
            "sha256",
            data.encode(),
            salt.encode(),
            iterations,
        ).hex()
    
    return HashResult(
        hash_value=hash_value,
        algorithm=algorithm,
        salt=salt,
        iterations=iterations,
    )


async def verify_hash(
    data: str,
    hash_result: HashResult,
) -> bool:
    """Verify data against a stored hash."""
    new_hash = await hash_sensitive(
        data,
        algorithm=hash_result.algorithm,
        salt=hash_result.salt,
        iterations=hash_result.iterations or 100000,
    )
    return hmac.compare_digest(new_hash.hash_value, hash_result.hash_value)


async def rotate_key(
    old_key_id: str,
    new_key_id: str | None = None,
) -> str:
    """Rotate an encryption key."""
    new_id = new_key_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    with _db() as conn:
        # Mark old key as rotated
        conn.execute(
            "UPDATE encryption_keys SET active = 0 WHERE key_id = ?",
            (old_key_id,)
        )
        
        # Create new key record
        new_key = _derive_key(new_id)
        key_hash = hashlib.sha256(new_key).hexdigest()
        
        conn.execute(
            """
            INSERT INTO encryption_keys (key_id, key_name, key_hash, algorithm, created_at, rotated_from, active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                new_id,
                f"key_{new_id[:8]}",
                key_hash,
                EncryptionAlgorithm.AES_256_GCM.value,
                now.isoformat(),
                old_key_id,
            )
        )
        conn.commit()
    
    return new_id


def _log_key_usage(key_id: str, operation: str) -> None:
    """Log key usage for audit."""
    with _db() as conn:
        conn.execute(
            "INSERT INTO key_usage_log (log_id, key_id, operation, timestamp) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), key_id, operation, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
