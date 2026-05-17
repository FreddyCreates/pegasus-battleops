"""
Defense Dashboard Module — Real-Time Monitoring
◎ Live threat feed and visualization.
"""

from .websocket import defense_websocket_endpoint
from .api import dashboard_router

__all__ = ["defense_websocket_endpoint", "dashboard_router"]
