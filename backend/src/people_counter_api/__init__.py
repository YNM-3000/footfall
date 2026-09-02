"""HTTP/WebSocket service for the people counter dashboard."""

from .app import create_app
from .settings import Settings

__version__ = "0.3.0"

__all__ = ["Settings", "create_app"]
