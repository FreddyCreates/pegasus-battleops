"""
Protocol: Sanitatio  🧹
Meaning: Sanitize and validate input data.

Handles:
- Input sanitization
- XSS prevention
- SQL injection prevention
- Content validation
"""

from __future__ import annotations

import html
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SanitizationType(str, Enum):
    """Types of sanitization."""
    HTML = "html"
    SQL = "sql"
    PATH = "path"
    FILENAME = "filename"
    URL = "url"
    EMAIL = "email"
    GENERAL = "general"


class ValidationLevel(str, Enum):
    """Validation strictness levels."""
    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"


class SanitizationResult(BaseModel):
    """Result of sanitization."""
    original: str
    sanitized: str
    sanitization_type: SanitizationType
    changes_made: list[str] = Field(default_factory=list)
    is_safe: bool = True
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ValidationResult(BaseModel):
    """Result of content validation."""
    valid: bool
    content_type: str
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    risk_score: float = 0.0  # 0.0 = safe, 1.0 = dangerous


# ---------------------------------------------------------------------------
# Sanitization Patterns
# ---------------------------------------------------------------------------

# HTML/XSS patterns
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
SCRIPT_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
EVENT_HANDLER_PATTERN = re.compile(r"\s+on\w+\s*=", re.IGNORECASE)
JAVASCRIPT_URL_PATTERN = re.compile(r"javascript:", re.IGNORECASE)

# SQL injection patterns
SQL_INJECTION_PATTERNS = [
    re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|EXEC|EXECUTE)\b)", re.IGNORECASE),
    re.compile(r"(--|#|/\*|\*/)", re.IGNORECASE),
    re.compile(r"(\b(OR|AND)\b\s+\d+\s*=\s*\d+)", re.IGNORECASE),
    re.compile(r"(\b(UNION|JOIN)\b.*\b(SELECT)\b)", re.IGNORECASE),
    re.compile(r"(;\s*(SELECT|INSERT|UPDATE|DELETE|DROP))", re.IGNORECASE),
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERN = re.compile(r"(\.\.[\\/]|[\\/]\.\.)")
NULL_BYTE_PATTERN = re.compile(r"\x00")

# Dangerous filename characters
UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# URL validation
URL_PATTERN = re.compile(
    r"^https?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
    r"localhost|"
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    r"(?::\d+)?"
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE
)

# Email validation
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def sanitize_input(
    content: str,
    sanitization_type: SanitizationType = SanitizationType.GENERAL,
    level: ValidationLevel = ValidationLevel.MODERATE,
) -> SanitizationResult:
    """
    Protocol Sanitatio: sanitize input content.
    """
    changes: list[str] = []
    warnings: list[str] = []
    sanitized = content
    
    if sanitization_type == SanitizationType.HTML:
        sanitized, changes, warnings = _sanitize_html(content, level)
    elif sanitization_type == SanitizationType.SQL:
        sanitized, changes, warnings = _sanitize_sql(content, level)
    elif sanitization_type == SanitizationType.PATH:
        sanitized, changes, warnings = _sanitize_path(content, level)
    elif sanitization_type == SanitizationType.FILENAME:
        sanitized, changes, warnings = _sanitize_filename(content, level)
    elif sanitization_type == SanitizationType.URL:
        sanitized, changes, warnings = _sanitize_url(content, level)
    elif sanitization_type == SanitizationType.EMAIL:
        sanitized, changes, warnings = _sanitize_email(content, level)
    else:
        sanitized, changes, warnings = _sanitize_general(content, level)
    
    return SanitizationResult(
        original=content,
        sanitized=sanitized,
        sanitization_type=sanitization_type,
        changes_made=changes,
        is_safe=len(warnings) == 0,
        warnings=warnings,
    )


async def validate_content(
    content: str,
    expected_type: str = "text",
    level: ValidationLevel = ValidationLevel.MODERATE,
) -> ValidationResult:
    """
    Protocol Sanitatio: validate content safety.
    """
    issues: list[str] = []
    suggestions: list[str] = []
    risk_score = 0.0
    
    # Check for script injection
    if SCRIPT_PATTERN.search(content):
        issues.append("Script tags detected")
        risk_score += 0.4
        suggestions.append("Remove all script tags")
    
    # Check for event handlers
    if EVENT_HANDLER_PATTERN.search(content):
        issues.append("Event handler attributes detected")
        risk_score += 0.3
        suggestions.append("Remove event handler attributes (onclick, onload, etc.)")
    
    # Check for javascript: URLs
    if JAVASCRIPT_URL_PATTERN.search(content):
        issues.append("JavaScript URL detected")
        risk_score += 0.4
        suggestions.append("Remove javascript: URLs")
    
    # Check for SQL injection patterns
    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.search(content):
            issues.append("Potential SQL injection pattern detected")
            risk_score += 0.2
            break
    
    # Check for path traversal
    if PATH_TRAVERSAL_PATTERN.search(content):
        issues.append("Path traversal pattern detected")
        risk_score += 0.3
        suggestions.append("Remove ../ and ..\\ sequences")
    
    # Check for null bytes
    if NULL_BYTE_PATTERN.search(content):
        issues.append("Null byte detected")
        risk_score += 0.5
        suggestions.append("Remove null bytes")
    
    # Content length check
    if len(content) > 1_000_000:
        issues.append("Content exceeds 1MB limit")
        risk_score += 0.1
        suggestions.append("Reduce content size")
    
    return ValidationResult(
        valid=risk_score < 0.5,
        content_type=expected_type,
        issues=issues,
        suggestions=suggestions,
        risk_score=min(1.0, risk_score),
    )


# ---------------------------------------------------------------------------
# Sanitization Implementations
# ---------------------------------------------------------------------------

def _sanitize_html(content: str, level: ValidationLevel) -> tuple[str, list[str], list[str]]:
    """Sanitize HTML content."""
    changes = []
    warnings = []
    sanitized = content
    
    # Remove script tags
    if SCRIPT_PATTERN.search(sanitized):
        sanitized = SCRIPT_PATTERN.sub("", sanitized)
        changes.append("Removed script tags")
        warnings.append("Script tags were present")
    
    # Remove event handlers
    if EVENT_HANDLER_PATTERN.search(sanitized):
        sanitized = EVENT_HANDLER_PATTERN.sub(" ", sanitized)
        changes.append("Removed event handlers")
        warnings.append("Event handlers were present")
    
    # Remove javascript: URLs
    if JAVASCRIPT_URL_PATTERN.search(sanitized):
        sanitized = JAVASCRIPT_URL_PATTERN.sub("", sanitized)
        changes.append("Removed javascript: URLs")
        warnings.append("JavaScript URLs were present")
    
    if level == ValidationLevel.STRICT:
        # Remove all HTML tags
        if HTML_TAG_PATTERN.search(sanitized):
            sanitized = HTML_TAG_PATTERN.sub("", sanitized)
            changes.append("Removed all HTML tags")
    
    # Escape remaining HTML entities
    sanitized = html.escape(sanitized, quote=True)
    if sanitized != content:
        changes.append("Escaped HTML entities")
    
    return sanitized, changes, warnings


def _sanitize_sql(content: str, level: ValidationLevel) -> tuple[str, list[str], list[str]]:
    """Sanitize content for SQL safety."""
    changes = []
    warnings = []
    sanitized = content
    
    # Remove SQL comments
    if "--" in sanitized or "/*" in sanitized:
        sanitized = sanitized.replace("--", "").replace("/*", "").replace("*/", "")
        changes.append("Removed SQL comments")
        warnings.append("SQL comments were present")
    
    # Escape single quotes
    if "'" in sanitized:
        sanitized = sanitized.replace("'", "''")
        changes.append("Escaped single quotes")
    
    # Check for suspicious patterns
    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.search(content):
            warnings.append("Potential SQL injection pattern detected")
            break
    
    return sanitized, changes, warnings


def _sanitize_path(content: str, level: ValidationLevel) -> tuple[str, list[str], list[str]]:
    """Sanitize file path."""
    changes = []
    warnings = []
    sanitized = content
    
    # Remove null bytes
    if "\x00" in sanitized:
        sanitized = sanitized.replace("\x00", "")
        changes.append("Removed null bytes")
        warnings.append("Null bytes were present")
    
    # Remove path traversal
    while PATH_TRAVERSAL_PATTERN.search(sanitized):
        sanitized = PATH_TRAVERSAL_PATTERN.sub("", sanitized)
        changes.append("Removed path traversal sequences")
        warnings.append("Path traversal attempted")
    
    # Normalize slashes
    sanitized = sanitized.replace("\\", "/")
    
    # Remove leading slashes for relative paths
    if level == ValidationLevel.STRICT:
        sanitized = sanitized.lstrip("/")
        if sanitized != content.lstrip("/"):
            changes.append("Removed leading slashes")
    
    return sanitized, changes, warnings


def _sanitize_filename(content: str, level: ValidationLevel) -> tuple[str, list[str], list[str]]:
    """Sanitize filename."""
    changes = []
    warnings = []
    sanitized = content
    
    # Remove unsafe characters
    if UNSAFE_FILENAME_CHARS.search(sanitized):
        sanitized = UNSAFE_FILENAME_CHARS.sub("_", sanitized)
        changes.append("Replaced unsafe filename characters")
        warnings.append("Unsafe characters were present")
    
    # Remove leading/trailing dots and spaces
    original_sanitized = sanitized
    sanitized = sanitized.strip(". ")
    if sanitized != original_sanitized:
        changes.append("Removed leading/trailing dots and spaces")
    
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
        changes.append("Truncated filename to 255 characters")
    
    # Ensure not empty
    if not sanitized:
        sanitized = f"file_{uuid.uuid4().hex[:8]}"
        changes.append("Generated default filename")
    
    return sanitized, changes, warnings


def _sanitize_url(content: str, level: ValidationLevel) -> tuple[str, list[str], list[str]]:
    """Sanitize URL."""
    changes = []
    warnings = []
    sanitized = content.strip()
    
    # Remove javascript: URLs
    if sanitized.lower().startswith("javascript:"):
        sanitized = ""
        changes.append("Removed javascript: URL")
        warnings.append("JavaScript URL was present")
    
    # Remove data: URLs in strict mode
    if level == ValidationLevel.STRICT and sanitized.lower().startswith("data:"):
        sanitized = ""
        changes.append("Removed data: URL")
        warnings.append("Data URL was present")
    
    # Validate URL format
    if sanitized and not URL_PATTERN.match(sanitized):
        warnings.append("URL format may be invalid")
    
    return sanitized, changes, warnings


def _sanitize_email(content: str, level: ValidationLevel) -> tuple[str, list[str], list[str]]:
    """Sanitize email address."""
    changes = []
    warnings = []
    sanitized = content.strip().lower()
    
    # Remove any HTML
    if "<" in sanitized or ">" in sanitized:
        sanitized = HTML_TAG_PATTERN.sub("", sanitized)
        changes.append("Removed HTML from email")
        warnings.append("HTML was present in email")
    
    # Validate format
    if not EMAIL_PATTERN.match(sanitized):
        warnings.append("Email format may be invalid")
    
    return sanitized, changes, warnings


def _sanitize_general(content: str, level: ValidationLevel) -> tuple[str, list[str], list[str]]:
    """General purpose sanitization."""
    changes = []
    warnings = []
    sanitized = content
    
    # Remove null bytes
    if "\x00" in sanitized:
        sanitized = sanitized.replace("\x00", "")
        changes.append("Removed null bytes")
        warnings.append("Null bytes were present")
    
    # Check for script injection
    if SCRIPT_PATTERN.search(sanitized):
        sanitized = SCRIPT_PATTERN.sub("", sanitized)
        changes.append("Removed script tags")
        warnings.append("Script tags were present")
    
    # HTML escape in strict mode
    if level == ValidationLevel.STRICT:
        escaped = html.escape(sanitized, quote=True)
        if escaped != sanitized:
            sanitized = escaped
            changes.append("Escaped HTML entities")
    
    return sanitized, changes, warnings
