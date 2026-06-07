"""
⟲ RESPONSE STRATEGIES — Defensive action implementations

Each strategy defines HOW the system responds to a classified entity.
Strategies are composable and measurable.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..schemas import AdaptiveAction, ThreatLevel


# ---------------------------------------------------------------------------
# Strategy Types
# ---------------------------------------------------------------------------

class StrategyType(str, Enum):
    """Available response strategy types."""
    OBSERVE = "observe"
    RATE_LIMIT = "rate_limit"
    CHALLENGE = "challenge"
    BLOCK = "block"
    ENGAGE = "engage"
    TAR_PIT = "tar_pit"


# ---------------------------------------------------------------------------
# Strategy Parameters
# ---------------------------------------------------------------------------

class StrategyParams(BaseModel):
    """Configuration parameters for a response strategy."""
    # Rate limiting
    requests_per_minute: int = 10
    burst_allowance: int = 3

    # Challenge
    challenge_type: str = "js_fingerprint"  # js_fingerprint, captcha, proof_of_work
    challenge_difficulty: int = 1  # 1-5

    # Block
    block_duration_seconds: int = 3600
    block_scope: str = "ip"  # ip, fingerprint, subnet

    # Engage (deception)
    engagement_persona: str = "vulnerable_server"
    response_delay_ms: int = 0
    fake_data_richness: int = 3  # 1-5

    # Tar pit
    tar_pit_delay_ms: int = 5000
    tar_pit_max_delay_ms: int = 30000
    tar_pit_escalation_factor: float = 1.5


# ---------------------------------------------------------------------------
# Strategy Result
# ---------------------------------------------------------------------------

class StrategyResult(BaseModel):
    """Result of executing a response strategy."""
    strategy_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    strategy_type: StrategyType
    action: AdaptiveAction
    success: bool = True

    # What was done
    description: str = ""
    parameters_used: dict[str, Any] = Field(default_factory=dict)

    # Timing
    execution_ms: float = 0.0
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # For effectiveness tracking
    entity_ip: str = ""
    entity_fingerprint: str | None = None


# ---------------------------------------------------------------------------
# Base Strategy
# ---------------------------------------------------------------------------

class ResponseStrategy(ABC):
    """Base class for all response strategies."""

    strategy_type: StrategyType
    description: str = ""

    def __init__(self, params: StrategyParams | None = None):
        self.params = params or StrategyParams()

    @abstractmethod
    def execute(
        self,
        ip_address: str,
        fingerprint_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> StrategyResult:
        """Execute the response strategy against a target entity."""
        ...

    @abstractmethod
    def get_adaptive_action(self) -> AdaptiveAction:
        """Return the AdaptiveAction enum this strategy maps to."""
        ...


# ---------------------------------------------------------------------------
# Concrete Strategies
# ---------------------------------------------------------------------------

class ObserveStrategy(ResponseStrategy):
    """
    ◎ OBSERVE — Passive monitoring, no active intervention.
    Used for Tier A cooperative entities and low-confidence classifications.
    """

    strategy_type = StrategyType.OBSERVE
    description = "Passive observation — monitor without intervention"

    def execute(
        self,
        ip_address: str,
        fingerprint_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> StrategyResult:
        return StrategyResult(
            strategy_type=self.strategy_type,
            action=self.get_adaptive_action(),
            success=True,
            description="Entity under passive observation",
            parameters_used={"mode": "passive"},
            entity_ip=ip_address,
            entity_fingerprint=fingerprint_id,
        )

    def get_adaptive_action(self) -> AdaptiveAction:
        return AdaptiveAction.OBSERVE


class RateLimitStrategy(ResponseStrategy):
    """
    ⟲ RATE LIMIT — Throttle request frequency.
    Applied to aggressive crawlers or high-volume Tier A entities.
    """

    strategy_type = StrategyType.RATE_LIMIT
    description = "Throttle request frequency to configured limits"

    def execute(
        self,
        ip_address: str,
        fingerprint_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> StrategyResult:
        start = time.monotonic()

        # Rate limit enforcement logic
        limit_config = {
            "requests_per_minute": self.params.requests_per_minute,
            "burst_allowance": self.params.burst_allowance,
            "scope": "ip",
            "target": ip_address,
        }

        elapsed = (time.monotonic() - start) * 1000

        return StrategyResult(
            strategy_type=self.strategy_type,
            action=self.get_adaptive_action(),
            success=True,
            description=(
                f"Rate limit applied: {self.params.requests_per_minute} req/min "
                f"with burst={self.params.burst_allowance}"
            ),
            parameters_used=limit_config,
            execution_ms=elapsed,
            entity_ip=ip_address,
            entity_fingerprint=fingerprint_id,
        )

    def get_adaptive_action(self) -> AdaptiveAction:
        return AdaptiveAction.RATE_LIMIT


class ChallengeStrategy(ResponseStrategy):
    """
    ⛨ CHALLENGE — Issue verification challenge.
    Forces entity to prove it is not automated/hostile.
    """

    strategy_type = StrategyType.CHALLENGE
    description = "Issue JS/CAPTCHA/PoW challenge to verify entity"

    def execute(
        self,
        ip_address: str,
        fingerprint_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> StrategyResult:
        start = time.monotonic()

        challenge_config = {
            "challenge_type": self.params.challenge_type,
            "difficulty": self.params.challenge_difficulty,
            "target": ip_address,
            "expires_in_seconds": 300,
        }

        elapsed = (time.monotonic() - start) * 1000

        return StrategyResult(
            strategy_type=self.strategy_type,
            action=self.get_adaptive_action(),
            success=True,
            description=(
                f"Challenge issued: {self.params.challenge_type} "
                f"(difficulty={self.params.challenge_difficulty})"
            ),
            parameters_used=challenge_config,
            execution_ms=elapsed,
            entity_ip=ip_address,
            entity_fingerprint=fingerprint_id,
        )

    def get_adaptive_action(self) -> AdaptiveAction:
        return AdaptiveAction.CHALLENGE


class BlockStrategy(ResponseStrategy):
    """
    ⛨ BLOCK — Deny access temporarily or permanently.
    Applied to confirmed hostile entities (Tier B).
    """

    strategy_type = StrategyType.BLOCK
    description = "Block entity access for configured duration"

    def execute(
        self,
        ip_address: str,
        fingerprint_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> StrategyResult:
        start = time.monotonic()

        block_config = {
            "target": ip_address,
            "scope": self.params.block_scope,
            "duration_seconds": self.params.block_duration_seconds,
            "fingerprint": fingerprint_id,
        }

        elapsed = (time.monotonic() - start) * 1000

        # Determine if temporary or permanent
        is_permanent = self.params.block_duration_seconds >= 86400 * 30
        action = (
            AdaptiveAction.BLOCK_PERMANENT if is_permanent
            else AdaptiveAction.BLOCK_TEMPORARY
        )

        return StrategyResult(
            strategy_type=self.strategy_type,
            action=action,
            success=True,
            description=(
                f"{'Permanent' if is_permanent else 'Temporary'} block: "
                f"{self.params.block_duration_seconds}s on {self.params.block_scope}"
            ),
            parameters_used=block_config,
            execution_ms=elapsed,
            entity_ip=ip_address,
            entity_fingerprint=fingerprint_id,
        )

    def get_adaptive_action(self) -> AdaptiveAction:
        if self.params.block_duration_seconds >= 86400 * 30:
            return AdaptiveAction.BLOCK_PERMANENT
        return AdaptiveAction.BLOCK_TEMPORARY


class EngageStrategy(ResponseStrategy):
    """
    🜏 ENGAGE — Active deception, feed fake intelligence.
    Keeps adversary occupied while extracting their techniques.
    """

    strategy_type = StrategyType.ENGAGE
    description = "Engage with deceptive responses to extract adversary techniques"

    def execute(
        self,
        ip_address: str,
        fingerprint_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> StrategyResult:
        start = time.monotonic()

        engage_config = {
            "persona": self.params.engagement_persona,
            "richness": self.params.fake_data_richness,
            "delay_ms": self.params.response_delay_ms,
            "target": ip_address,
        }

        elapsed = (time.monotonic() - start) * 1000

        return StrategyResult(
            strategy_type=self.strategy_type,
            action=self.get_adaptive_action(),
            success=True,
            description=(
                f"Engagement active: persona={self.params.engagement_persona}, "
                f"richness={self.params.fake_data_richness}/5"
            ),
            parameters_used=engage_config,
            execution_ms=elapsed,
            entity_ip=ip_address,
            entity_fingerprint=fingerprint_id,
        )

    def get_adaptive_action(self) -> AdaptiveAction:
        return AdaptiveAction.ENGAGE


class TarPitStrategy(ResponseStrategy):
    """
    ⟲ TAR PIT — Progressively slow responses to waste attacker resources.
    Each subsequent request gets slower, draining attacker bandwidth.
    """

    strategy_type = StrategyType.TAR_PIT
    description = "Progressive response delay to waste attacker resources"

    def execute(
        self,
        ip_address: str,
        fingerprint_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> StrategyResult:
        start = time.monotonic()

        # Calculate current delay based on request count
        request_count = (context or {}).get("request_count", 1)
        current_delay = min(
            self.params.tar_pit_delay_ms * (
                self.params.tar_pit_escalation_factor ** (request_count - 1)
            ),
            self.params.tar_pit_max_delay_ms,
        )

        tar_pit_config = {
            "initial_delay_ms": self.params.tar_pit_delay_ms,
            "current_delay_ms": int(current_delay),
            "max_delay_ms": self.params.tar_pit_max_delay_ms,
            "escalation_factor": self.params.tar_pit_escalation_factor,
            "request_number": request_count,
            "target": ip_address,
        }

        elapsed = (time.monotonic() - start) * 1000

        return StrategyResult(
            strategy_type=self.strategy_type,
            action=self.get_adaptive_action(),
            success=True,
            description=(
                f"Tar pit active: {int(current_delay)}ms delay "
                f"(request #{request_count}, escalation={self.params.tar_pit_escalation_factor}x)"
            ),
            parameters_used=tar_pit_config,
            execution_ms=elapsed,
            entity_ip=ip_address,
            entity_fingerprint=fingerprint_id,
        )

    def get_adaptive_action(self) -> AdaptiveAction:
        return AdaptiveAction.RATE_LIMIT  # Tar pit is a form of rate limiting


# ---------------------------------------------------------------------------
# Strategy Factory
# ---------------------------------------------------------------------------

_STRATEGY_MAP: dict[StrategyType, type[ResponseStrategy]] = {
    StrategyType.OBSERVE: ObserveStrategy,
    StrategyType.RATE_LIMIT: RateLimitStrategy,
    StrategyType.CHALLENGE: ChallengeStrategy,
    StrategyType.BLOCK: BlockStrategy,
    StrategyType.ENGAGE: EngageStrategy,
    StrategyType.TAR_PIT: TarPitStrategy,
}


def get_strategy(
    strategy_type: StrategyType,
    params: StrategyParams | None = None,
) -> ResponseStrategy:
    """Factory: get a strategy instance by type."""
    cls = _STRATEGY_MAP.get(strategy_type)
    if cls is None:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
    return cls(params=params)
