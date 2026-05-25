"""
Protocol: Validatio  ✓
Meaning: Schema and data validation.

Handles:
- JSON Schema validation
- Type checking
- Custom validation rules
- Error reporting
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field


class ValidationType(str, Enum):
    """Types of validation."""
    TYPE = "type"           # Type checking
    REQUIRED = "required"   # Required field
    FORMAT = "format"       # Format validation (email, url, etc.)
    RANGE = "range"         # Numeric range
    LENGTH = "length"       # String/array length
    PATTERN = "pattern"     # Regex pattern
    ENUM = "enum"           # Allowed values
    CUSTOM = "custom"       # Custom validation


class ValidationConfig(BaseModel):
    """Configuration for validation."""
    strict_mode: bool = False
    stop_on_first_error: bool = False
    coerce_types: bool = False
    allow_extra_fields: bool = True


class ValidationIssue(BaseModel):
    """A single validation issue."""
    field: str
    issue_type: ValidationType
    message: str
    expected: Any = None
    actual: Any = None


class ValidationResult(BaseModel):
    """Result of validation."""
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    fields_validated: int = 0
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Schema Types
# ---------------------------------------------------------------------------

PRIMITIVE_TYPES = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}

FORMAT_VALIDATORS = {
    "email": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
    "url": re.compile(r"^https?://[^\s/$.?#].[^\s]*$"),
    "uuid": re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I),
    "date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "datetime": re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"),
    "phone": re.compile(r"^\+?[\d\s-]{10,}$"),
    "ipv4": re.compile(r"^(\d{1,3}\.){3}\d{1,3}$"),
}

# ---------------------------------------------------------------------------
# Custom Validators Registry
# ---------------------------------------------------------------------------

_custom_validators: dict[str, Callable[[Any, dict], bool]] = {}


def register_validator(name: str, validator_fn: Callable[[Any, dict], bool]) -> None:
    """Register a custom validator function."""
    _custom_validators[name] = validator_fn


# ---------------------------------------------------------------------------
# Core Validation
# ---------------------------------------------------------------------------

def _validate_type(value: Any, expected_type: str) -> bool:
    """Validate value type."""
    if expected_type not in PRIMITIVE_TYPES:
        return True  # Unknown type, skip
    
    return isinstance(value, PRIMITIVE_TYPES[expected_type])


def _validate_format(value: str, format_name: str) -> bool:
    """Validate string format."""
    if not isinstance(value, str):
        return False
    
    if format_name not in FORMAT_VALIDATORS:
        return True  # Unknown format, skip
    
    return bool(FORMAT_VALIDATORS[format_name].match(value))


def _validate_range(value: Any, minimum: float | None, maximum: float | None) -> bool:
    """Validate numeric range."""
    if not isinstance(value, (int, float)):
        return False
    
    if minimum is not None and value < minimum:
        return False
    if maximum is not None and value > maximum:
        return False
    
    return True


def _validate_length(
    value: Any,
    min_length: int | None,
    max_length: int | None,
) -> bool:
    """Validate string/array length."""
    if not hasattr(value, "__len__"):
        return False
    
    length = len(value)
    
    if min_length is not None and length < min_length:
        return False
    if max_length is not None and length > max_length:
        return False
    
    return True


def _validate_pattern(value: str, pattern: str) -> bool:
    """Validate string against regex pattern."""
    if not isinstance(value, str):
        return False
    
    return bool(re.match(pattern, value))


def _validate_enum(value: Any, allowed_values: list) -> bool:
    """Validate value is in allowed list."""
    return value in allowed_values


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def validate_schema(
    data: dict | list[dict],
    schema: dict,
    config: ValidationConfig | None = None,
) -> ValidationResult:
    """
    Protocol Validatio: validate data against a JSON-like schema.
    
    Schema format:
    {
        "type": "object",
        "properties": {
            "field_name": {
                "type": "string",
                "required": true,
                "format": "email",
                "minLength": 5,
                "maxLength": 100,
                "pattern": "^[a-z]+$",
                "enum": ["a", "b", "c"]
            }
        }
    }
    """
    import time
    start_time = time.perf_counter()
    
    cfg = config or ValidationConfig()
    issues: list[ValidationIssue] = []
    warnings: list[str] = []
    fields_validated = 0
    
    # Handle list of records
    records = data if isinstance(data, list) else [data]
    
    for record_idx, record in enumerate(records):
        prefix = f"[{record_idx}]." if isinstance(data, list) else ""
        
        # Validate each property in schema
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])
        
        for field_name, field_schema in properties.items():
            full_field = f"{prefix}{field_name}"
            fields_validated += 1
            
            value = record.get(field_name)
            
            # Check required
            if field_name in required_fields or field_schema.get("required", False):
                if value is None and field_name not in record:
                    issues.append(ValidationIssue(
                        field=full_field,
                        issue_type=ValidationType.REQUIRED,
                        message=f"Field '{field_name}' is required",
                    ))
                    if cfg.stop_on_first_error:
                        break
                    continue
            
            # Skip None values for non-required fields
            if value is None:
                continue
            
            # Type validation
            expected_type = field_schema.get("type")
            if expected_type and not _validate_type(value, expected_type):
                issues.append(ValidationIssue(
                    field=full_field,
                    issue_type=ValidationType.TYPE,
                    message=f"Expected type '{expected_type}'",
                    expected=expected_type,
                    actual=type(value).__name__,
                ))
                if cfg.stop_on_first_error:
                    break
                continue
            
            # Format validation
            format_name = field_schema.get("format")
            if format_name and not _validate_format(value, format_name):
                issues.append(ValidationIssue(
                    field=full_field,
                    issue_type=ValidationType.FORMAT,
                    message=f"Value does not match format '{format_name}'",
                    expected=format_name,
                    actual=value,
                ))
                if cfg.stop_on_first_error:
                    break
            
            # Range validation
            minimum = field_schema.get("minimum")
            maximum = field_schema.get("maximum")
            if (minimum is not None or maximum is not None) and not _validate_range(value, minimum, maximum):
                issues.append(ValidationIssue(
                    field=full_field,
                    issue_type=ValidationType.RANGE,
                    message=f"Value out of range [{minimum}, {maximum}]",
                    expected=f"[{minimum}, {maximum}]",
                    actual=value,
                ))
                if cfg.stop_on_first_error:
                    break
            
            # Length validation
            min_length = field_schema.get("minLength")
            max_length = field_schema.get("maxLength")
            if (min_length is not None or max_length is not None) and not _validate_length(value, min_length, max_length):
                issues.append(ValidationIssue(
                    field=full_field,
                    issue_type=ValidationType.LENGTH,
                    message=f"Length out of range [{min_length}, {max_length}]",
                    expected=f"[{min_length}, {max_length}]",
                    actual=len(value) if hasattr(value, "__len__") else None,
                ))
                if cfg.stop_on_first_error:
                    break
            
            # Pattern validation
            pattern = field_schema.get("pattern")
            if pattern and not _validate_pattern(value, pattern):
                issues.append(ValidationIssue(
                    field=full_field,
                    issue_type=ValidationType.PATTERN,
                    message=f"Value does not match pattern",
                    expected=pattern,
                    actual=value,
                ))
                if cfg.stop_on_first_error:
                    break
            
            # Enum validation
            enum_values = field_schema.get("enum")
            if enum_values and not _validate_enum(value, enum_values):
                issues.append(ValidationIssue(
                    field=full_field,
                    issue_type=ValidationType.ENUM,
                    message=f"Value not in allowed values",
                    expected=enum_values,
                    actual=value,
                ))
                if cfg.stop_on_first_error:
                    break
        
        # Check for extra fields
        if cfg.strict_mode and not cfg.allow_extra_fields:
            extra_fields = set(record.keys()) - set(properties.keys())
            for extra in extra_fields:
                warnings.append(f"Extra field '{prefix}{extra}' not in schema")
    
    duration = (time.perf_counter() - start_time) * 1000
    
    return ValidationResult(
        valid=len(issues) == 0,
        issues=issues,
        warnings=warnings,
        fields_validated=fields_validated,
        duration_ms=duration,
    )


async def validate_data(
    data: Any,
    validators: list[dict],
    config: ValidationConfig | None = None,
) -> ValidationResult:
    """
    Protocol Validatio: validate data with custom validators.
    
    Validator format:
    {
        "field": "field_name",
        "type": "custom",
        "validator": "validator_name",
        "params": {}
    }
    """
    import time
    start_time = time.perf_counter()
    
    issues: list[ValidationIssue] = []
    fields_validated = 0
    
    for validator_config in validators:
        field = validator_config.get("field", "")
        validator_name = validator_config.get("validator")
        params = validator_config.get("params", {})
        
        if validator_name and validator_name in _custom_validators:
            fields_validated += 1
            
            # Get field value
            value = data
            if field:
                for part in field.split("."):
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = None
                        break
            
            # Run validator
            try:
                is_valid = _custom_validators[validator_name](value, params)
                if not is_valid:
                    issues.append(ValidationIssue(
                        field=field,
                        issue_type=ValidationType.CUSTOM,
                        message=f"Custom validation '{validator_name}' failed",
                        actual=value,
                    ))
            except Exception as e:
                issues.append(ValidationIssue(
                    field=field,
                    issue_type=ValidationType.CUSTOM,
                    message=f"Validator error: {str(e)}",
                    actual=value,
                ))
    
    duration = (time.perf_counter() - start_time) * 1000
    
    return ValidationResult(
        valid=len(issues) == 0,
        issues=issues,
        fields_validated=fields_validated,
        duration_ms=duration,
    )
