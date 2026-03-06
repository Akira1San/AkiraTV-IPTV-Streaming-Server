# Viewer Analytics Feature Plan

## Overview

Add a Viewer Analytics page with charts showing:
- Viewer counts over time (time-series graph)
- Per-channel popularity (bar/pie chart)
- Peak viewing times
- Unique viewer statistics

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ViewerTracker Module                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Current: Real-time tracking (already implemented)        │    │
│  │ New: History storage with periodic sampling              │    │
│  │   - _history: List[Dict] with timestamp, channel, count  │    │
│  │   - Sample every 60 seconds                               │    │
│  │   - Keep last 24 hours of data                            │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ GET /api/viewers/analytics                                │    │
│  │   Returns: {history, channel_stats, peak_times, totals}  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Analytics Page (analytics.html)               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ - Viewer count over time chart (line graph)              │    │
│  │ - Channel popularity chart (pie/bar chart)                │    │
│  │ - Peak viewing times (bar chart by hour)                 │    │
│  │ - Summary stats cards                                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Tasks

### 1. Extend ViewerTracker Module

**File:** `akiratv/viewer_tracker.py`

Add history tracking:
```python
class ViewerTracker:
    HISTORY_INTERVAL = 60  # Sample every 60 seconds
    HISTORY_MAX_HOURS = 24  # Keep 24 hours of data
    
    def __init__(self):
        # ... existing code ...
        self._history: List[Dict] = []
        self._last_sample_time = 0
    
    def sample_history(self) -> None:
        """Take a snapshot of current viewers for history."""
        now = time.time()
        if now - self._last_sample_time < self.HISTORY_INTERVAL:
            return
        
        self._last_sample_time = now
        snapshot = {
            "timestamp": now,
            "datetime": datetime.now().isoformat(),
            "total": self.total_viewers,
            "per_channel": self.get_counts()
        }
        self._history.append(snapshot)
        
        # Trim old entries (keep 24 hours)
        cutoff = now - (self.HISTORY_MAX_HOURS * 3600)
        self._history = [h for h in self._history if h["timestamp"] > cutoff]
    
    def get_history(self) -> List[Dict]:
        """Get viewer history for analytics."""
        return self._history
    
    def get_analytics(self) -> Dict:
        """Get comprehensive analytics data."""
        # Calculate channel popularity
        channel_totals = defaultdict(int)
        for entry in self._history:
            for channel, count in entry.get("per_channel", {}).items():
                channel_totals[channel] += count
        
        # Calculate peak times (by hour)
        hourly_counts = defaultdict(list)
        for entry in self._history:
            dt = datetime.fromisoformat(entry["datetime"])
            hour = dt.hour
            hourly_counts[hour].append(entry["total"])
        
        peak_hours = {
            hour: sum(counts) / len(counts)
            for hour, counts in hourly_counts.items()
        }
        
        return {
            "history": self._history,
            "channel_popularity": dict(channel_totals),
            "peak_hours": peak_hours,
            "total_samples": len(self._history)
        }
```

### 2. Add API Endpoint

**File:** `akiratv/api_server.py`

```python
@app.get("/api/viewers/analytics")
def get_viewer_analytics():
    """Get viewer analytics data for charts."""
    viewer_tracker.sample_history()  # Take a sample if due
    return viewer_tracker.get_analytics()
```

### 3. Create Analytics Page

**File:** `akiratv/static/analytics.html`

- Use Chart.js for visualizations (CDN)
- Line chart for viewer count over time
- Pie/bar chart for channel popularity
- Bar chart for peak viewing hours
- Summary cards for key metrics

### 4. Add Navigation

**File:** `akiratv/static/index.html`

Add button to Control Panel:
```html
<button class="btn btn-secondary" onclick="openAnalytics()">
    📊 Analytics
</button>
```

**File:** `akiratv/static/app.js`

Add function:
```javascript
function openAnalytics() {
    window.open('/static/analytics.html', '_blank');
}
```

## Files to Modify/Create

| File | Action |
|------|--------|
| `akiratv/viewer_tracker.py` | MODIFY - Add history tracking |
| `akiratv/api_server.py` | MODIFY - Add analytics endpoint |
| `akiratv/static/analytics.html` | CREATE - Analytics page with charts |
| `akiratv/static/index.html` | MODIFY - Add Analytics button |
| `akiratv/static/app.js` | MODIFY - Add openAnalytics function |

## UI Design

### Analytics Page Layout

```
┌────────────────────────────────────────────────────────────┐
│  📊 Viewer Analytics                          [Refresh]    │
├────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Peak     │  │ Unique   │  │ Avg      │  │ Total    │   │
│  │ Viewers  │  │ IPs      │  │ Viewers  │  │ Hours    │   │
│  │   12     │  │   45     │  │   5.2    │  │   24     │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  📈 Viewers Over Time (24h)                                │
│  ┌────────────────────────────────────────────────────┐   │
│  │                    [Line Chart]                     │   │
│  │  10 ─                                          ●─── │   │
│  │   8 ─                                    ●────      │   │
│  │   6 ─                          ●───                 │   │
│  │   4 ─              ●────                            │   │
│  │   2 ─    ●───                                      │   │
│  │   0 ──────────────────────────────────────────────  │   │
│  │      00:00  04:00  08:00  12:00  16:00  20:00      │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  📺 Channel Popularity          │  ⏰ Peak Viewing Hours   │
│  ┌─────────────────────────┐    │  ┌──────────────────┐   │
│  │     [Pie Chart]         │    │  │   [Bar Chart]    │   │
│  │                         │    │  │                  │   │
│  │   TatkoTV  ████████ 45% │    │  │  20:00 ████████ │   │
│  │   Horror    ██████ 30%  │    │  │  21:00 ███████  │   │
│  │   Asian     ████ 15%    │    │  │  19:00 █████    │   │
│  │   Other     ██ 10%      │    │  │  22:00 ████     │   │
│  └─────────────────────────┘    │  └──────────────────┘   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Dependencies

- **Chart.js** - For charts (load from CDN: https://cdn.jsdelivr.net/npm/chart.js)
- No additional Python dependencies needed

## Priority

**Medium** - Nice-to-have feature for monitoring and insights
