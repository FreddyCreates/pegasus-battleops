"""
Nova Sovereign Client — Async intelligence client for Spatium Computationis

Replaces the OpenAI AsyncClient pattern throughout the codebase.
Connects to the NOVA Protocol organism runtime for all reasoning,
classification, summarisation, and document generation tasks.

Architecture:
  - NOVAOrganismRuntime (BiologicalHeart φ-heartbeat at 873ms)
  - Julia mathematical engines (law, pipeline, organism, governance)
  - Sovereign consensus via Fibonacci-sphere weighted nodes
  - CIL (Cognitive Internal Language) internal state

Source: FreddyCreates/Decentralized-Production-NOVA-Protocol
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Golden Ratio Constants (from NOVA Protocol)
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2
PHI_HEARTBEAT_MS = 873.0  # 540 * φ


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NOVA_SOVEREIGN_URL = os.getenv(
    "NOVA_SOVEREIGN_URL",
    "http://localhost:8787",  # Default local Nova runtime
)
NOVA_SOVEREIGN_TOKEN = os.getenv("NOVA_SOVEREIGN_TOKEN", "")


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


@dataclass
class NovaSovereignMessage:
    """A message in the Nova Sovereign conversation format."""
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class NovaSovereignChoice:
    """A single choice/completion from Nova Sovereign."""
    index: int
    message: NovaSovereignMessage
    finish_reason: str = "stop"


@dataclass
class NovaSovereignResponse:
    """Response from Nova Sovereign organism intelligence."""
    response_id: str
    choices: list[NovaSovereignChoice]
    biorhythm: float = 0.0
    execution_time_ms: float = 0.0
    organism: str = "SOVEREIGN"

    @property
    def content(self) -> str:
        """Convenience: get the first choice's message content."""
        if self.choices:
            return self.choices[0].message.content
        return ""


@dataclass
class NovaSovereignCompletionProxy:
    """Proxy object mimicking the completions interface for drop-in replacement."""
    client: "NovaSovereignClient"

    async def create(
        self,
        *,
        model: str = "sovereign",
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> NovaSovereignResponse:
        """
        Create a completion via Nova Sovereign.

        This method signature mirrors the OpenAI pattern so existing agent code
        requires minimal changes.
        """
        return await self.client.complete(
            messages=messages,
            model=model,
            response_format=response_format,
            temperature=temperature,
            **kwargs,
        )


@dataclass
class NovaSovereignChatProxy:
    """Proxy object mimicking chat.completions interface."""
    completions: NovaSovereignCompletionProxy


# ---------------------------------------------------------------------------
# Biorhythm calculation (from NOVA Protocol)
# ---------------------------------------------------------------------------

_MAYAN_CYCLE = 1440.0
_SUMERIAN_HOUR = 3600.0
_EGYPTIAN_HOUR = 2160.0
_LUNAR_CYCLE = 2551.0
_SOLAR_CYCLE = 8760.0


def _calculate_biorhythm(timestamp_ms: float) -> float:
    """Calculate biorhythm using 6 ancient calendar cycles (NOVA Protocol)."""
    phases = [
        (timestamp_ms % _MAYAN_CYCLE) / _MAYAN_CYCLE,
        (timestamp_ms % _SUMERIAN_HOUR) / _SUMERIAN_HOUR,
        (timestamp_ms % _EGYPTIAN_HOUR) / _EGYPTIAN_HOUR,
        (timestamp_ms % _LUNAR_CYCLE) / _LUNAR_CYCLE,
        (timestamp_ms % _SOLAR_CYCLE) / _SOLAR_CYCLE,
        (timestamp_ms % PHI_HEARTBEAT_MS) / PHI_HEARTBEAT_MS,
    ]
    waves = [math.sin(2 * math.pi * p) for p in phases]
    pythagorean_sum = math.sqrt(sum(w**2 for w in waves)) / math.sqrt(6.0)
    phi_weighted = pythagorean_sum * PHI / (PHI + 1.0)
    return (phi_weighted + 1.0) / 2.0


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class NovaSovereignClient:
    """
    Async client for the Nova Sovereign organism intelligence runtime.

    Drop-in replacement for OpenAI's AsyncOpenAI. Provides the same
    `client.chat.completions.create(...)` interface so existing agent code
    needs only an import change.

    The client routes requests to the NOVA organism runtime which uses
    Julia mathematical engines, Fibonacci-sphere consensus, and φ-derived
    biorhythms instead of external LLM APIs.
    """

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
    ):
        self.base_url = (base_url or NOVA_SOVEREIGN_URL).rstrip("/")
        self.token = token or NOVA_SOVEREIGN_TOKEN
        self._http: httpx.AsyncClient | None = None

        # Provide the chat.completions interface for drop-in compatibility
        self.chat = NovaSovereignChatProxy(
            completions=NovaSovereignCompletionProxy(client=self)
        )

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = "Bearer " + self.token
            self._http = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=120.0,
            )
        return self._http

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        model: str = "sovereign",
        response_format: dict[str, str] | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> NovaSovereignResponse:
        """
        Send a completion request to the Nova Sovereign runtime.

        Maps the OpenAI-style messages format to the Nova organism task protocol.
        """
        start_ms = time.time() * 1000.0

        payload = {
            "organism": model,
            "messages": messages,
            "temperature": temperature,
            "request_id": str(uuid.uuid4()),
            "biorhythm": _calculate_biorhythm(start_ms),
        }
        if response_format:
            payload["response_format"] = response_format

        http = await self._get_http()

        try:
            resp = await http.post("/v1/sovereign/complete", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, httpx.ConnectError) as exc:
            logger.warning(
                "Nova Sovereign runtime unreachable (%s). Entering degraded mode.",
                exc,
            )
            data = self._local_fallback(messages, response_format)

        execution_time = time.time() * 1000.0 - start_ms

        # Parse response
        choices_data = data.get("choices", [])
        choices = []
        for i, c in enumerate(choices_data):
            msg = c.get("message", {})
            choices.append(
                NovaSovereignChoice(
                    index=i,
                    message=NovaSovereignMessage(
                        role=msg.get("role", "assistant"),
                        content=msg.get("content", ""),
                    ),
                    finish_reason=c.get("finish_reason", "stop"),
                )
            )

        if not choices:
            # Ensure at least one choice
            content = data.get("content", data.get("output", "{}"))
            if isinstance(content, dict):
                content = json.dumps(content)
            choices = [
                NovaSovereignChoice(
                    index=0,
                    message=NovaSovereignMessage(role="assistant", content=content),
                )
            ]

        return NovaSovereignResponse(
            response_id=data.get("response_id", str(uuid.uuid4())),
            choices=choices,
            biorhythm=data.get("biorhythm", _calculate_biorhythm(time.time() * 1000.0)),
            execution_time_ms=execution_time,
            organism=data.get("organism", model),
        )

    def _local_fallback(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None,
    ) -> dict[str, Any]:
        """
        Local fallback when the Nova runtime is unreachable.

        Returns a structured placeholder so the system continues operating.
        The Actio protocol will flag this as degraded.
        """
        system_msg = next(
            (m["content"] for m in messages if m["role"] == "system"), ""
        )
        user_msg = next(
            (m["content"] for m in messages if m["role"] == "user"), ""
        )

        # If JSON is expected, return a structured fallback
        if response_format and response_format.get("type") == "json_object":
            content = json.dumps({
                "status": "degraded",
                "reason": "Nova Sovereign runtime unreachable",
                "input_summary": user_msg[:200],
                "fallback": True,
            })
        else:
            content = (
                f"[Nova Sovereign — degraded mode] "
                f"Runtime unreachable. Input received: {user_msg[:200]}"
            )

        return {
            "choices": [
                {
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "organism": "fallback",
            "biorhythm": _calculate_biorhythm(time.time() * 1000.0),
        }

    async def close(self):
        """Close the HTTP client."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_client: NovaSovereignClient | None = None


def get_nova_client() -> NovaSovereignClient:
    """
    Get the module-level Nova Sovereign client singleton.

    Drop-in replacement for the `_get_client() -> AsyncOpenAI` pattern
    used throughout the agents and protocols.
    """
    global _client
    if _client is None:
        _client = NovaSovereignClient()
    return _client
