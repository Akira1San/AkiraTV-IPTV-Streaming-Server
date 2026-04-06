# Viewer IP and Channel Tracking Feature

## Overview

Implement a viewer tracking system that displays IP addresses of viewers and the TV channel they are currently watching in the admin interface.

## Current State

- The system has a basic viewer count via `/api/viewers` endpoint
- `akiratv/analytics.py` exists but is from the old codebase and needs to be cleaned up
- The HLS handler in `akiratv/server/http_server.py` serves video files but doesn't track viewers
- The admin UI (`index.html`) shows only a viewer count, not detailed information

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        HTTP Server                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ hls_handler()                                            │    │
│  │   ├── Extract IP from request.remote or X-Forwarded-For  │    │
│  │   ├── Extract Channel from path (e.g., /hls/akiratv/...) │    │
│  │   └── Call viewer_tracker.record_view(channel, ip)       │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ViewerTracker Module                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ _viewers: Dict[str, Dict[str, float]]                    │    │
│  │   Structure: {channel: {ip: last_seen_timestamp}}        │    │
│  │                                                          │    │
│  │ Methods:                                                 │    │
│  │   - record_view(channel, ip)                             │    │
│  │   - cleanup_stale() - remove inactive viewers            │    │
│  │   - get_all_viewers() - return all viewer data           │    │
│  │   - get_viewer_list() - return as list for API           │    │
│  │   - get_channel_viewers(channel) - per-channel filter    │    │
│  │   - get_counts() - viewer counts per channel             │    │
│  │   - total_viewers - property returning unique IP count   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ GET /api/viewers/detail                                  │    │
│  │   Returns: {total, viewers: [...], per_channel: {...}}   │    │
│  │                                                          │    │
│  │ GET /api/viewers/channel/{channel_name}                  │    │
│  │   Returns: {channel, viewers: [...], count}              │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Admin UI (index.html)                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Viewer Details Panel                                     │    │
│  │   ├── Total viewer count                                 │    │
│  │   ├── Grouped by channel                                 │    │
│  │   │   ├── Channel name with viewer count                 │    │
│  │   │   └── List of IPs with "last seen" time              │    │
│  │   └── Auto-refresh every 10 seconds                      │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Tasks

### 1. Create Viewer Tracker Module

**File:** `akiratv/viewer_tracker.py`

```python
# akiratv/viewer_tracker.py
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
```

### 2. Modify HLS Handler

**File:** `akiratv/server/http_server.py`

Add at the beginning of `hls_handler()` method:

```python
async def hls_handler(self, request):
    """Serve HLS files with proper headers and retry logic for permission errors."""
    path = request.match_info['path']
    
    # === VIEWER TRACKING ===
    # Extract channel name from path (e.g., "akiratv/index.m3u8" -> "akiratv")
    parts = path.split('/')
    channel_name = parts[0] if parts else "unknown"
    
    # Get client IP (handle reverse proxies)
    client_ip = request.remote
    if 'X-Forwarded-For' in request.headers:
        # Take first IP if multiple (original client)
        forwarded = request.headers['X-Forwarded-For']
        client_ip = forwarded.split(',')[0].strip()
    
    # Record this view
    from ..viewer_tracker import viewer_tracker
    viewer_tracker.record_view(channel_name, client_ip or "unknown")
    # === END VIEWER TRACKING ===
    
    # ... rest of existing handler code ...
```

### 3. Add API Endpoints

**File:** `akiratv/api_server.py`

Add after the existing `/api/viewers` endpoint:

```python
from .viewer_tracker import viewer_tracker

@app.get("/api/viewers/detail")
def get_viewer_details():
    """Get detailed viewer information with IPs and channels."""
    viewer_tracker.cleanup_stale()  # Clean up before returning
    return {
        "total": viewer_tracker.total_viewers,
        "viewers": viewer_tracker.get_viewer_list(),
        "per_channel": viewer_tracker.get_counts()
    }

@app.get("/api/viewers/channel/{channel_name}")
def get_channel_viewers(channel_name: str):
    """Get viewers for a specific channel."""
    viewer_tracker.cleanup_stale()
    viewers = viewer_tracker.get_channel_viewers(channel_name)
    return {
        "channel": channel_name,
        "viewers": viewers,
        "count": len(viewers)
    }
```

### 4. Add UI Panel

**File:** `akiratv/static/index.html`

Add after the stats-grid section (around line 46):

```html
<!-- Viewer Details Panel -->
<div class="section" id="viewerDetailsSection">
    <div class="section-title">👥 Active Viewers</div>
    <div id="viewerDetailsContent">
        <div class="viewer-summary">
            <span>Total: <strong id="totalViewers">0</strong></span>
            <button class="btn btn-small" onclick="refreshViewerDetails()">🔄 Refresh</button>
        </div>
        <div id="viewerList" class="viewer-list">
            <!-- Populated by JavaScript -->
        </div>
    </div>
</div>
```

### 5. Add JavaScript Functions

**File:** `akiratv/static/app.js`

Add the following functions:

```javascript
// Viewer Details Functions
async function refreshViewerDetails() {
    try {
        const response = await fetch('/api/viewers/detail');
        const data = await response.json();
        
        // Update total
        document.getElementById('totalViewers').textContent = data.total;
        
        // Build viewer list
        const listEl = document.getElementById('viewerList');
        if (data.viewers.length === 0) {
            listEl.innerHTML = '<p class="no-viewers">No active viewers</p>';
            return;
        }
        
        // Group by channel
        const byChannel = {};
        data.viewers.forEach(v => {
            if (!byChannel[v.channel]) byChannel[v.channel] = [];
            byChannel[v.channel].push(v);
        });
        
        let html = '';
        for (const [channel, viewers] of Object.entries(byChannel)) {
            html += `<div class="channel-group">
                <div class="channel-header">${channel} (${viewers.length})</div>
                <div class="channel-viewers">`;
            
            viewers.forEach(v => {
                html += `<div class="viewer-row">
                    <span class="viewer-ip">${v.ip}</span>
                    <span class="viewer-time">${v.seconds_ago}s ago</span>
                </div>`;
            });
            
            html += '</div></div>';
        }
        listEl.innerHTML = html;
        
    } catch (error) {
        console.error('Failed to fetch viewer details:', error);
    }
}

// Auto-refresh every 10 seconds
setInterval(refreshViewerDetails, 10000);

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    refreshViewerDetails();
});
```

### 6. Add CSS Styles

**File:** `akiratv/static/styles.css`

Add the following styles:

```css
/* Viewer Details Panel */
.viewer-summary {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 15px;
    background: var(--card-bg);
    border-radius: 8px;
    margin-bottom: 15px;
}

.viewer-list {
    max-height: 400px;
    overflow-y: auto;
}

.channel-group {
    margin-bottom: 15px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    overflow: hidden;
}

.channel-header {
    background: var(--primary-color);
    color: white;
    padding: 10px 15px;
    font-weight: 600;
}

.channel-viewers {
    padding: 10px;
}

.viewer-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 12px;
    border-bottom: 1px solid var(--border-color);
}

.viewer-row:last-child {
    border-bottom: none;
}

.viewer-ip {
    font-family: monospace;
    color: var(--text-color);
}

.viewer-time {
    color: var(--text-muted);
    font-size: 0.9em;
}

.no-viewers {
    text-align: center;
    color: var(--text-muted);
    padding: 20px;
}

.btn-small {
    padding: 5px 10px;
    font-size: 0.85em;
}
```

### 7. Clean Up Old Analytics Module

**Task:** Remove or update `akiratv/analytics.py`

The old `analytics.py` module contains similar functionality but is not integrated. Options:
1. Delete the file entirely if not used elsewhere
2. Update it to use the new `ViewerTracker` class
3. Keep it for backward compatibility but mark as deprecated

## Configuration Options (Optional)

Consider adding these to `config.json`:

```json
{
  "viewer_tracking": {
    "enabled": true,
    "timeout_seconds": 60,
    "auto_refresh_interval": 10,
    "log_views": false
  }
}
```

## Security Considerations

1. **IP Privacy:** The admin interface should be protected by authentication
2. **Proxy Support:** The `X-Forwarded-For` header handling supports reverse proxies
3. **Rate Limiting:** Consider rate limiting the `/api/viewers/detail` endpoint

## Testing

1. Start a channel stream
2. Open viewer page from different browser/incognito window
3. Verify IP appears in admin UI
4. Wait 60+ seconds and verify viewer is removed from list
5. Test with reverse proxy (X-Forwarded-For header)

## Files to Modify

| File | Action |
|------|--------|
| `akiratv/viewer_tracker.py` | CREATE - New module |
| `akiratv/server/http_server.py` | MODIFY - Add tracking to hls_handler |
| `akiratv/api_server.py` | MODIFY - Add new endpoints |
| `akiratv/static/index.html` | MODIFY - Add viewer panel |
| `akiratv/static/app.js` | MODIFY - Add JavaScript functions |
| `akiratv/static/styles.css` | MODIFY - Add CSS styles |
| `akiratv/analytics.py` | DELETE or DEPRECATE |

## Priority

**Medium** - This is a useful monitoring feature but not critical for core functionality.
