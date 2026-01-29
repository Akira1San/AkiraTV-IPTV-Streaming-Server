# akiratv/stats.py
import threading

# Global stats (Thread-Safe)
AKIRATV_STATS = {
    "status": "Stopped",
    "channels": 0,
    "viewers": 0,
    "storage": "Disk",
    "uptime": "0s",
    "config": {}
}
STATS_LOCK = threading.Lock()

# Viewer tracking
ACTIVE_CONNECTIONS = 0
ACTIVE_CONNECTIONS_LOCK = threading.Lock()

def get_active_viewers():
    """Return number of active HTTP connections (thread-safe)."""
    with ACTIVE_CONNECTIONS_LOCK:
        return ACTIVE_CONNECTIONS