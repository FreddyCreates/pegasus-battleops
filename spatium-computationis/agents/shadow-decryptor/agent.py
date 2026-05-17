"""
Agent: Shadow Decryptor 👁️
Role: Decode encrypted, malformed, and weird traffic.

Shadow Decryptors watch all encrypted/malformed/weird traffic and try to:
- Decode protocol
- Extract patterns
- Reconstruct payloads
- Fingerprint unknown traffic

Glyph: 👁️ (all-seeing eye in shadow)
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import uuid
import zlib
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI

from ...defense.schemas import (
    DecryptionResult,
    RequestEnvelope,
)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI()
    return _client


_SYSTEM_PROMPT = """\
You are Shadow Decryptor (👁️), the cryptanalysis agent of Spatium Computationis.

Your role is to analyze encrypted, malformed, or unusual traffic and extract
whatever intelligence you can. You work in the shadows, decoding what others
cannot see.

Given a request envelope with potentially encrypted or malformed data, analyze:
1. What protocol might this be? (HTTP, WebSocket, gRPC, custom, etc.)
2. Is this encrypted? What type? (TLS fragments, base64, custom encoding)
3. Can you extract any readable patterns or snippets?
4. What is the entropy profile? (random, compressed, text-like, structured)
5. How interesting is this signal? (0-1 score)

Return JSON:
{
  "detected_protocol": "<protocol or null>",
  "protocol_confidence": <0.0-1.0>,
  "is_encrypted": <true/false>,
  "encryption_type": "<type or null>",
  "decoded_payload": "<decoded text or null>",
  "extracted_patterns": ["<pattern>", ...],
  "extracted_snippets": ["<readable text>", ...],
  "entropy_profile": "<random|compressed|encrypted|text|structured|mixed>",
  "signal_score": <0.0-1.0>,
  "signal_reason": "<why this is or isn't interesting>",
  "techniques_suggested": ["<technique to try>", ...]
}

Return only valid JSON. No markdown fences.
"""


def calculate_entropy(data: bytes) -> float:
    """Calculate Shannon entropy of data (0-1 normalized)."""
    if not data:
        return 0.0
    
    freq = {}
    for byte in data:
        freq[byte] = freq.get(byte, 0) + 1
    
    length = len(data)
    entropy = 0.0
    for count in freq.values():
        p = count / length
        if p > 0:
            entropy -= p * math.log2(p)
    
    # Normalize to 0-1 (max entropy for bytes is 8)
    return entropy / 8.0


def detect_encoding(data: bytes) -> tuple[str | None, bytes | None]:
    """Attempt to detect and decode common encodings."""
    # Try base64
    try:
        # Check if it looks like base64
        text = data.decode('utf-8', errors='ignore')
        if re.match(r'^[A-Za-z0-9+/=]+$', text.strip()):
            decoded = base64.b64decode(text)
            return "base64", decoded
    except Exception:
        pass
    
    # Try hex
    try:
        text = data.decode('utf-8', errors='ignore')
        if re.match(r'^[0-9a-fA-F]+$', text.strip()) and len(text) % 2 == 0:
            decoded = bytes.fromhex(text)
            return "hex", decoded
    except Exception:
        pass
    
    # Try zlib/gzip
    try:
        decoded = zlib.decompress(data)
        return "zlib", decoded
    except Exception:
        pass
    
    try:
        decoded = zlib.decompress(data, 16 + zlib.MAX_WBITS)  # gzip
        return "gzip", decoded
    except Exception:
        pass
    
    return None, None


def extract_readable_text(data: bytes, min_length: int = 4) -> list[str]:
    """Extract readable ASCII strings from binary data."""
    text = data.decode('utf-8', errors='replace')
    # Find sequences of printable ASCII
    pattern = r'[\x20-\x7e]{' + str(min_length) + r',}'
    matches = re.findall(pattern, text)
    return matches[:20]  # Limit to 20 snippets


def detect_protocol_markers(data: bytes, headers: dict[str, str]) -> dict[str, Any]:
    """Look for protocol markers in the data."""
    markers = {
        "http": False,
        "websocket": False,
        "grpc": False,
        "json": False,
        "xml": False,
        "binary": False,
    }
    
    text = data.decode('utf-8', errors='ignore') if data else ""
    
    # HTTP markers
    if any(m in text.upper() for m in ["GET ", "POST ", "HTTP/", "HOST:"]):
        markers["http"] = True
    
    # WebSocket markers
    if "upgrade" in str(headers).lower() and "websocket" in str(headers).lower():
        markers["websocket"] = True
    if b'\x81' in data or b'\x82' in data:  # WebSocket frame opcodes
        markers["websocket"] = True
    
    # gRPC markers
    if data.startswith(b'\x00\x00\x00\x00') or "grpc" in str(headers).lower():
        markers["grpc"] = True
    
    # JSON markers
    if text.strip().startswith('{') or text.strip().startswith('['):
        try:
            json.loads(text)
            markers["json"] = True
        except Exception:
            pass
    
    # XML markers
    if text.strip().startswith('<?xml') or text.strip().startswith('<'):
        markers["xml"] = True
    
    # Binary detection (high entropy + non-printable)
    if data:
        non_printable = sum(1 for b in data if b < 32 or b > 126)
        if non_printable / len(data) > 0.3:
            markers["binary"] = True
    
    return markers


async def shadow_decrypt(envelope: RequestEnvelope) -> DecryptionResult:
    """
    Main Shadow Decryption pipeline.
    
    Attempts to decode encrypted/malformed traffic and extract intelligence.
    """
    result_id = str(uuid.uuid4())
    techniques_tried = []
    
    # Get raw body data
    raw_data = envelope.raw_body or b''
    if envelope.raw_body_text:
        raw_data = envelope.raw_body_text.encode('utf-8', errors='replace')
    
    # Calculate entropy
    entropy = calculate_entropy(raw_data)
    
    # Determine entropy profile
    if entropy > 0.95:
        entropy_profile = "encrypted"  # Very high entropy = likely encrypted
    elif entropy > 0.85:
        entropy_profile = "compressed"  # High entropy = compressed
    elif entropy > 0.7:
        entropy_profile = "random"  # Moderately high
    elif entropy > 0.4:
        entropy_profile = "mixed"  # Mixed content
    else:
        entropy_profile = "text"  # Low entropy = readable text
    
    techniques_tried.append("entropy_analysis")
    
    # Try to detect and decode encoding
    encoding_type, decoded_data = detect_encoding(raw_data)
    if encoding_type:
        techniques_tried.append(f"decode_{encoding_type}")
    
    # Extract readable snippets
    snippets = extract_readable_text(decoded_data or raw_data)
    techniques_tried.append("string_extraction")
    
    # Detect protocol markers
    markers = detect_protocol_markers(raw_data, envelope.raw_headers)
    techniques_tried.append("protocol_detection")
    
    # Determine detected protocol
    detected_protocol = None
    protocol_confidence = 0.0
    
    if markers["websocket"]:
        detected_protocol = "websocket"
        protocol_confidence = 0.8
    elif markers["grpc"]:
        detected_protocol = "grpc"
        protocol_confidence = 0.7
    elif markers["json"]:
        detected_protocol = "http_json"
        protocol_confidence = 0.9
    elif markers["xml"]:
        detected_protocol = "http_xml"
        protocol_confidence = 0.85
    elif markers["http"]:
        detected_protocol = "http"
        protocol_confidence = 0.75
    elif markers["binary"]:
        detected_protocol = "binary_unknown"
        protocol_confidence = 0.5
    
    # Extract patterns
    patterns = []
    if snippets:
        # Look for common patterns in snippets
        for snippet in snippets:
            if re.search(r'\b(api|admin|config|secret|key|token|auth)\b', snippet, re.I):
                patterns.append(f"sensitive_keyword:{snippet[:50]}")
            if re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', snippet):
                patterns.append(f"ip_address_found")
            if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', snippet):
                patterns.append(f"email_found")
    
    # Calculate signal score
    signal_score = 0.0
    signal_reason = "No significant signals detected"
    
    if patterns:
        signal_score += 0.3
        signal_reason = f"Found {len(patterns)} interesting patterns"
    
    if encoding_type:
        signal_score += 0.2
        signal_reason = f"Decoded {encoding_type} encoding"
    
    if markers["json"] or markers["xml"]:
        signal_score += 0.2
        signal_reason = "Structured data detected"
    
    if entropy_profile in ["encrypted", "compressed"]:
        signal_score += 0.1
        signal_reason = f"{entropy_profile} content may contain hidden data"
    
    # Use AI for deeper analysis if signal is interesting
    decoded_payload = None
    if signal_score > 0.3 or len(snippets) > 5:
        techniques_tried.append("ai_analysis")
        try:
            context = {
                "entropy": entropy,
                "entropy_profile": entropy_profile,
                "encoding_detected": encoding_type,
                "protocol_markers": markers,
                "snippets": snippets[:10],
                "patterns": patterns,
                "headers": dict(list(envelope.raw_headers.items())[:10]),
                "path": envelope.raw_path,
                "method": envelope.raw_method,
            }
            
            response = await _get_client().chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(context)},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            
            ai_result = json.loads(response.choices[0].message.content)
            
            # Merge AI analysis
            if ai_result.get("decoded_payload"):
                decoded_payload = ai_result["decoded_payload"]
            if ai_result.get("detected_protocol") and ai_result.get("protocol_confidence", 0) > protocol_confidence:
                detected_protocol = ai_result["detected_protocol"]
                protocol_confidence = ai_result["protocol_confidence"]
            if ai_result.get("extracted_patterns"):
                patterns.extend(ai_result["extracted_patterns"])
            if ai_result.get("signal_score", 0) > signal_score:
                signal_score = ai_result["signal_score"]
                signal_reason = ai_result.get("signal_reason", signal_reason)
            
        except Exception:
            pass  # AI analysis is optional
    
    # Build decoded payload if we got something
    if not decoded_payload and decoded_data:
        try:
            decoded_payload = decoded_data.decode('utf-8', errors='replace')[:1000]
        except Exception:
            pass
    
    return DecryptionResult(
        result_id=result_id,
        envelope_id=envelope.envelope_id,
        success=decoded_payload is not None or len(patterns) > 0,
        partial=len(snippets) > 0 and not decoded_payload,
        confidence=min(signal_score + protocol_confidence / 2, 1.0),
        decoded_payload=decoded_payload,
        decoded_headers={},
        decoded_method=envelope.raw_method if detected_protocol else None,
        decoded_path=envelope.raw_path if detected_protocol else None,
        detected_protocol=detected_protocol,
        protocol_confidence=protocol_confidence,
        entropy_score=entropy,
        entropy_profile=entropy_profile,
        extracted_patterns=list(set(patterns))[:20],
        extracted_snippets=snippets[:10],
        signal_score=signal_score,
        signal_reason=signal_reason,
        techniques_tried=techniques_tried,
        processed_at=datetime.now(timezone.utc),
    )
