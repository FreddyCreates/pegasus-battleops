"""
Security Protocols Package — Spatium Computationis

Security-focused protocols for:
- Authentication and authorization
- Rate limiting and throttling
- Encryption and data protection
- Token management

Glyphs:
  🔐 Authenticatio — identity verification
  🛡️ Auctoritas    — permission checking
  ⚡ Limitatio     — rate control
  🔒 Cryptographia — encryption
"""

from .authenticatio import (
    authenticate_request,
    validate_token,
    AuthenticationResult,
    TokenPayload,
    AuthMethod,
    AuthStatus,
)
from .auctoritas import (
    authorize_action,
    check_permission,
    grant_permission,
    revoke_permission,
    AuthorizationResult,
    Permission,
    PermissionLevel,
    ResourceType,
)
from .limitatio import (
    check_rate_limit,
    record_request,
    reset_penalty,
    RateLimitResult,
    RateLimitConfig,
    RateLimitScope,
)
from .cryptographia import (
    encrypt_data,
    decrypt_data,
    hash_sensitive,
    verify_hash,
    rotate_key,
    EncryptionResult,
    DecryptionResult,
    HashResult,
)
from .token_custos import (
    create_token,
    revoke_token,
    refresh_token,
    introspect_token,
    TokenInfo,
    TokenType,
    TokenStatus,
)
from .sanitatio import (
    sanitize_input,
    validate_content,
    SanitizationResult,
    ValidationResult,
    SanitizationType,
    ValidationLevel,
)

__all__ = [
    # Authenticatio
    "authenticate_request",
    "validate_token",
    "AuthenticationResult",
    "TokenPayload",
    "AuthMethod",
    "AuthStatus",
    # Auctoritas
    "authorize_action",
    "check_permission",
    "grant_permission",
    "revoke_permission",
    "AuthorizationResult",
    "Permission",
    "PermissionLevel",
    "ResourceType",
    # Limitatio
    "check_rate_limit",
    "record_request",
    "reset_penalty",
    "RateLimitResult",
    "RateLimitConfig",
    "RateLimitScope",
    # Cryptographia
    "encrypt_data",
    "decrypt_data",
    "hash_sensitive",
    "verify_hash",
    "rotate_key",
    "EncryptionResult",
    "DecryptionResult",
    "HashResult",
    # Token Custos
    "create_token",
    "revoke_token",
    "refresh_token",
    "introspect_token",
    "TokenInfo",
    "TokenType",
    "TokenStatus",
    # Sanitatio
    "sanitize_input",
    "validate_content",
    "SanitizationResult",
    "ValidationResult",
    "SanitizationType",
    "ValidationLevel",
]
