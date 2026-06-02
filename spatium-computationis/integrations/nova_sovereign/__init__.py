"""
Nova Sovereign Integration  ⌬⟁

Bridge between Spatium Computationis and the Decentralized-Production-NOVA-Protocol.

This replaces OpenAI as the intelligence backend. All reasoning, classification,
and generation flows through the Nova Sovereign organisms and their φ-derived
computational primitives.

Source: https://github.com/FreddyCreates/Decentralized-Production-NOVA-Protocol
"""

from .client import NovaSovereignClient, get_nova_client

__all__ = ["NovaSovereignClient", "get_nova_client"]
