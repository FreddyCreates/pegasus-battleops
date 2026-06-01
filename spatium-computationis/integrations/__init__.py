"""
Integrations — Shared API clients and data stores for external services.
"""

from .godaddy_client import GoDaddyClient
from .marketing_store import MarketingStore

__all__ = ["GoDaddyClient", "MarketingStore"]
