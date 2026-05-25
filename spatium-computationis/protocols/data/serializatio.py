"""
Protocol: Serializatio  📦
Meaning: Data serialization and deserialization.

Handles:
- JSON serialization
- Binary formats (MessagePack, Protocol Buffers-like)
- Compression
- Schema-aware serialization
"""

from __future__ import annotations

import base64
import gzip
import json
import pickle
from datetime import datetime, timezone, date
from decimal import Decimal
from enum import Enum
from typing import Any, Type, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field


T = TypeVar("T")


class SerializationFormat(str, Enum):
    """Supported serialization formats."""
    JSON = "json"
    JSON_COMPACT = "json_compact"
    JSON_PRETTY = "json_pretty"
    PICKLE = "pickle"
    BASE64 = "base64"
    COMPRESSED = "compressed"


class SerializationResult(BaseModel):
    """Result of serialization."""
    success: bool
    data: str | bytes | None = None
    format: SerializationFormat
    original_size: int = 0
    serialized_size: int = 0
    compression_ratio: float | None = None
    error: str | None = None


class DeserializationResult(BaseModel):
    """Result of deserialization."""
    success: bool
    data: Any = None
    format: SerializationFormat
    error: str | None = None


# ---------------------------------------------------------------------------
# Custom JSON Encoder
# ---------------------------------------------------------------------------

class EnhancedJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles common Python types."""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("utf-8")
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, Enum):
            return obj.value
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def serialize(
    data: Any,
    format: SerializationFormat = SerializationFormat.JSON,
) -> SerializationResult:
    """
    Protocol Serializatio: serialize data to the specified format.
    """
    try:
        original_size = len(str(data))
        
        if format == SerializationFormat.JSON:
            result = json.dumps(data, cls=EnhancedJSONEncoder)
        elif format == SerializationFormat.JSON_COMPACT:
            result = json.dumps(data, cls=EnhancedJSONEncoder, separators=(",", ":"))
        elif format == SerializationFormat.JSON_PRETTY:
            result = json.dumps(data, cls=EnhancedJSONEncoder, indent=2)
        elif format == SerializationFormat.PICKLE:
            result = base64.b64encode(pickle.dumps(data)).decode("utf-8")
        elif format == SerializationFormat.BASE64:
            if isinstance(data, bytes):
                result = base64.b64encode(data).decode("utf-8")
            else:
                json_str = json.dumps(data, cls=EnhancedJSONEncoder)
                result = base64.b64encode(json_str.encode()).decode("utf-8")
        elif format == SerializationFormat.COMPRESSED:
            json_str = json.dumps(data, cls=EnhancedJSONEncoder, separators=(",", ":"))
            compressed = gzip.compress(json_str.encode("utf-8"))
            result = base64.b64encode(compressed).decode("utf-8")
        else:
            result = json.dumps(data, cls=EnhancedJSONEncoder)
        
        serialized_size = len(result)
        compression_ratio = None
        
        if format == SerializationFormat.COMPRESSED:
            compression_ratio = 1 - (serialized_size / original_size) if original_size > 0 else 0
        
        return SerializationResult(
            success=True,
            data=result,
            format=format,
            original_size=original_size,
            serialized_size=serialized_size,
            compression_ratio=compression_ratio,
        )
        
    except Exception as e:
        return SerializationResult(
            success=False,
            format=format,
            error=str(e),
        )


async def deserialize(
    data: str | bytes,
    format: SerializationFormat = SerializationFormat.JSON,
    target_type: Type[T] | None = None,
) -> DeserializationResult:
    """
    Protocol Serializatio: deserialize data from the specified format.
    """
    try:
        result: Any
        
        if format == SerializationFormat.JSON or format == SerializationFormat.JSON_COMPACT or format == SerializationFormat.JSON_PRETTY:
            result = json.loads(data)
        elif format == SerializationFormat.PICKLE:
            if isinstance(data, str):
                decoded = base64.b64decode(data)
            else:
                decoded = base64.b64decode(data)
            result = pickle.loads(decoded)
        elif format == SerializationFormat.BASE64:
            if isinstance(data, str):
                decoded = base64.b64decode(data).decode("utf-8")
            else:
                decoded = base64.b64decode(data).decode("utf-8")
            try:
                result = json.loads(decoded)
            except json.JSONDecodeError:
                result = decoded
        elif format == SerializationFormat.COMPRESSED:
            if isinstance(data, str):
                compressed = base64.b64decode(data)
            else:
                compressed = base64.b64decode(data)
            decompressed = gzip.decompress(compressed).decode("utf-8")
            result = json.loads(decompressed)
        else:
            result = json.loads(data)
        
        # Convert to target type if specified
        if target_type is not None:
            if hasattr(target_type, "model_validate"):
                result = target_type.model_validate(result)
            elif hasattr(target_type, "from_dict"):
                result = target_type.from_dict(result)
        
        return DeserializationResult(
            success=True,
            data=result,
            format=format,
        )
        
    except Exception as e:
        return DeserializationResult(
            success=False,
            format=format,
            error=str(e),
        )


async def serialize_to_bytes(data: Any) -> bytes:
    """Serialize data to compressed bytes."""
    result = await serialize(data, SerializationFormat.COMPRESSED)
    if result.success and result.data:
        return base64.b64decode(result.data)
    raise ValueError(result.error or "Serialization failed")


async def deserialize_from_bytes(data: bytes) -> Any:
    """Deserialize data from compressed bytes."""
    encoded = base64.b64encode(data).decode("utf-8")
    result = await deserialize(encoded, SerializationFormat.COMPRESSED)
    if result.success:
        return result.data
    raise ValueError(result.error or "Deserialization failed")


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def json_dumps(data: Any, **kwargs) -> str:
    """JSON dumps with enhanced encoder."""
    return json.dumps(data, cls=EnhancedJSONEncoder, **kwargs)


def json_loads(data: str | bytes) -> Any:
    """JSON loads."""
    return json.loads(data)


def estimate_size(data: Any) -> int:
    """Estimate serialized size of data."""
    try:
        return len(json.dumps(data, cls=EnhancedJSONEncoder, separators=(",", ":")))
    except Exception:
        return 0


def deep_copy(data: Any) -> Any:
    """Create a deep copy via serialization."""
    return json.loads(json.dumps(data, cls=EnhancedJSONEncoder))
