"""
⟲ ADAPTIVE RESPONSE ENGINE — Autonomous Defense Actions

The missing link between classification and response.
Closes the loop: Organism Charter classifies → Adaptive Response acts.

Capabilities:
- Strategy selection per classification tier
- Escalation logic for tier transitions
- Response effectiveness tracking via feedback protocol
- Real-time configuration via dashboard API

Glyphs:
  ⟲ Adaptio   — adaptive response selection
  ⇡ Escalatio — threat escalation
  ⛨ Actio     — defense action execution
  ◎ Effectus  — effectiveness measurement
"""

from .engine import (
    AdaptiveResponseEngine,
    ResponseDecision,
    ResponseConfig,
    get_engine,
)

from .strategies import (
    ResponseStrategy,
    StrategyType,
    RateLimitStrategy,
    ChallengeStrategy,
    BlockStrategy,
    EngageStrategy,
    TarPitStrategy,
    ObserveStrategy,
    get_strategy,
)

from .escalation import (
    EscalationRule,
    EscalationEngine,
    EscalationEvent,
    get_escalation_engine,
)

from .effectiveness import (
    EffectivenessTracker,
    EffectivenessReport,
    get_tracker,
)

from .routes import adaptive_response_router

__all__ = [
    # Engine
    "AdaptiveResponseEngine",
    "ResponseDecision",
    "ResponseConfig",
    "get_engine",
    # Strategies
    "ResponseStrategy",
    "StrategyType",
    "RateLimitStrategy",
    "ChallengeStrategy",
    "BlockStrategy",
    "EngageStrategy",
    "TarPitStrategy",
    "ObserveStrategy",
    "get_strategy",
    # Escalation
    "EscalationRule",
    "EscalationEngine",
    "EscalationEvent",
    "get_escalation_engine",
    # Effectiveness
    "EffectivenessTracker",
    "EffectivenessReport",
    "get_tracker",
    # Router
    "adaptive_response_router",
]
