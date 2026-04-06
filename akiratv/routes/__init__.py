"""
Routes package for AkiraTV API
Contains modular route handlers organized by functional domain
"""

from .lifecycle import router as lifecycle_router
from .channels import router as channels_router
from .config import router as config_router
from .library import router as library_router
from .monitoring import router as monitoring_router
from .guide import router as guide_router
from .vod import router as vod_router
from .playlist import router as playlist_router
from .standby import router as standby_router
from .websocket import websocket_endpoint
from .fast_scheduler import router as fast_scheduler_router
from .wizard import router as wizard_router

__all__ = [
    "lifecycle_router",
    "channels_router",
    "config_router",
    "library_router",
    "monitoring_router",
    "guide_router",
    "vod_router",
    "playlist_router",
    "standby_router",
    "websocket_endpoint",
    "fast_scheduler_router",
    "wizard_router",
]
