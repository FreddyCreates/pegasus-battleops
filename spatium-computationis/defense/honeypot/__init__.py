"""
Honeypot Module — Deceptive Endpoints
🜏 Attract and capture adversarial behavior.
"""

from .routes import honeypot_router
from .traps import TRAP_REGISTRY, get_trap_response
from .collector import FingerprintCollector

__all__ = [
    "honeypot_router",
    "TRAP_REGISTRY",
    "get_trap_response",
    "FingerprintCollector",
]
