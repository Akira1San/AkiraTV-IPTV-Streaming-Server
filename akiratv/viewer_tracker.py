# akiratv/viewer_tracker.py
"""Thread-safe viewer tracking with IP and channel information."""

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List, Optional


class ViewerTracker:
    """Thread-safe viewer tracking with IP and channel information."""
    
    VIEWER_TIMEOUT = 60  # seconds before viewer is considered inactive
    
    def __init__(self):
        self._lock = Lock()
        # Structure: {channel: {ip: last_seen_timestamp}}
        self._viewers: Dict[str, Dict[str, float]] = defaultdict(dict)
    
    def record_view(self, channel: str, ip: str) -> None:
        """Record a viewer accessing a channel."""
        now = time.time()
        with self._lock:
            self._viewers[channel][ip] = now
    
    def cleanup_stale(self) -> None:
        """Remove viewers who haven't been seen for VIEWER_TIMEOUT seconds."""
        now = time.time()
        with self._lock:
            for channel in list(self._viewers.keys()):
                stale_ips = [
                    ip for ip, last_seen in self._viewers[channel].items()
                    if now - last_seen > self.VIEWER_TIMEOUT
                ]
                for ip in stale_ips:
                    del self._viewers[channel][ip]
                # Remove empty channel entries
                if not self._viewers[channel]:
                    del self._viewers[channel]
    
    def get_all_viewers(self) -> Dict[str, Dict[str, float]]:
        """Get all active viewers with timestamps."""
        with self._lock:
            return dict(self._viewers)
    
    def get_viewer_list(self) -> List[Dict]:
        """Get viewers as a list for API responses."""
        now = time.time()
        result = []
        with self._lock:
            for channel, ips in self._viewers.items():
                for ip, last_seen in ips.items():
                    result.append({
                        "ip": ip,
                        "channel": channel,
                        "last_seen": last_seen,
                        "seconds_ago": round(now - last_seen, 1)
                    })
        return result
    
    def get_channel_viewers(self, channel: str) -> List[Dict]:
        """Get viewers for a specific channel."""
        now = time.time()
        with self._lock:
            if channel not in self._viewers:
                return []
            return [
                {"ip": ip, "last_seen": last_seen, "seconds_ago": round(now - last_seen, 1)}
                for ip, last_seen in self._viewers[channel].items()
            ]
    
    def get_counts(self) -> Dict[str, int]:
        """Get viewer counts per channel."""
        with self._lock:
            return {channel: len(ips) for channel, ips in self._viewers.items()}
    
    @property
    def total_viewers(self) -> int:
        """Get total unique viewers across all channels."""
        with self._lock:
            all_ips = set()
            for ips in self._viewers.values():
                all_ips.update(ips.keys())
            return len(all_ips)


# Global instance
viewer_tracker = ViewerTracker()
