# api_server.py Refactoring Plan

## Overview

Refactor the monolithic `api_server.py` (2,063 lines) into a modular structure using FastAPI routers.

## Current State

- **File**: `akiratv/api_server.py`
- **Lines**: 2,063
- **Issues**: 
  - Difficult to maintain
  - Hard to test individual endpoints
  - Multiple developers cannot work on it simultaneously
  - Debugging is cumbersome

## Target Structure

```
akiratv/
├── api_server.py           # Main app (~200 lines)
├── models.py               # Pydantic models (~100 lines)
└── routes/
    ├── __init__.py         # Export all routers
    ├── lifecycle.py        # Engine start/stop/restart
    ├── channels.py         # Channel management
    ├── config.py           # Configuration endpoints
    ├── library.py          # Library scan/stats
    ├── monitoring.py       # Stats, viewers, logs
    ├── guide.py            # TV guide endpoints
    ├── playlist.py         # Playlist management
    ├── standby.py          # Standby video creation
    ├── wizard.py           # Collection wizard endpoints
    ├── fast_scheduler.py   # Fast scheduling endpoints
    ├── vod.py              # VOD library endpoints
    └── websocket.py        # WebSocket handler
```

---

## Step-by-Step Implementation

### Step 1: Extract Pydantic Models

**File**: `akiratv/models.py`

Extract all Pydantic models from lines 25-48:

```python
"""Pydantic models for API requests and responses"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class PlayNowRequest(BaseModel):
    video_path: str = Field(..., description="Full path to video file")

class ConfigUpdateRequest(BaseModel):
    updates: Dict[str, Any] = Field(..., description="Configuration updates")

class ChannelUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    transcoding: Optional[str] = None
    subtitles: Optional[str] = None
    type: Optional[str] = None

class FastScheduleRequest(BaseModel):
    collections: Optional[List[str]] = None
    start_time: Optional[str] = "00:00"
    schedule_hours: Optional[int] = 24
    bumper_frequency: Optional[int] = 3
    trailer_probability: Optional[float] = 0.3

class Response(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Any] = None
```

### Step 2: Extract Helper Functions

**File**: `akiratv/api_server.py` (keep in main file or move to utils)

Functions to extract:
- `time_to_minutes()` (line 1014)
- `get_schedule_for_date()` (line 1024)
- `get_video_duration()` (line 1552)
- `get_core_api()` (line 89)

### Step 3: Create Route Modules

Each route module follows this pattern:

```python
"""Channel management endpoints"""
from fastapi import APIRouter, HTTPException
from typing import List
from ...models import Response, ChannelUpdateRequest, PlayNowRequest
from ...api_server import get_core_api  # Import from main

router = APIRouter(prefix="/api/channels", tags=["channels"])

@router.get("")
def get_channels():
    """Get all channels"""
    api = get_core_api()
    channels = api.get_channels()
    return {"channels": [ch.to_dict() for ch in channels], "total": len(channels)}
```

#### 3.1 Lifecycle Routes (`routes/lifecycle.py`)
- Lines 103-141
- `/api/start`, `/api/stop`, `/api/restart`, `/api/status`
- ~40 lines

#### 3.2 Channel Routes (`routes/channels.py`)
- Lines 147-403
- 14 channel-related endpoints
- ~260 lines

#### 3.3 Config Routes (`routes/config.py`)
- Lines 408-438
- `/api/config`, `/api/config/save`, `/api/config/defaults`
- ~40 lines

#### 3.4 Library Routes (`routes/library.py`)
- Lines 444-461
- `/api/library/stats`, `/api/library/scan`
- ~30 lines

#### 3.5 Monitoring Routes (`routes/monitoring.py`)
- Lines 467-505
- `/api/stats`, `/api/viewers`, `/api/logs`
- ~60 lines

#### 3.6 Guide Routes (`routes/guide.py`)
- Lines 666-1012
- `/api/guide`, `/api/guide/weekly`, `/api/guide/date/{date_str}`
- ~350 lines

#### 3.7 Playlist Routes (`routes/playlist.py`)
- Lines 1050-1166
- `/api/playlist/create`, `/api/playlist/videos`, `/api/playlist/play-selected`
- ~120 lines

#### 3.8 Standby Routes (`routes/standby.py`)
- Lines 1168-1275
- `/api/standby/create`
- ~110 lines

#### 3.9 Wizard Routes (`routes/wizard.py`)
- Lines 1281-1648
- Collection and schedule wizard endpoints
- ~180 lines

#### 3.10 Fast Scheduler Routes (`routes/fast_scheduler.py`)
- Lines 1654-1859
- `/api/fast-schedule/*` endpoints
- ~200 lines

#### 3.11 VOD Routes (`routes/vod.py`)
- Lines 1974-2036
- `/api/vod/library`, `/api/vod/video/{video_id}`
- ~70 lines

#### 3.12 WebSocket Routes (`routes/websocket.py`)
- Lines 1865-1906
- `/ws` endpoint
- ~50 lines

### Step 4: Refactor Main api_server.py

**File**: `akiratv/api_server.py`

```python
"""
FastAPI REST server for AkiraTV
Provides HTTP API for controlling AkiraTV through CoreAPI
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio

# Import models
from .models import Response

# Import routers
from .routes import (
    lifecycle,
    channels,
    config,
    library,
    monitoring,
    guide,
    playlist,
    standby,
    wizard,
    fast_scheduler,
    vod,
    websocket as ws
)

# ========================================
# FASTAPI APP
# ========================================

app = FastAPI(
    title="AkiraTV API",
    description="REST API for controlling AkiraTV streaming engine",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

user_dir = Path(__file__).parent.parent / "user"
if user_dir.exists():
    app.mount("/user", StaticFiles(directory=str(user_dir)), name="user")

# Lazy initialization
api = None

def get_core_api():
    """Get CoreAPI instance only when needed"""
    global api
    if api is None:
        from .core_api import get_api
        api = get_api()
    return api

# WebSocket connections
active_connections: list = []

# ========================================
# INCLUDE ROUTERS
# ========================================

app.include_router(lifecycle.router)
app.include_router(channels.router)
app.include_router(config.router)
app.include_router(library.router)
app.include_router(monitoring.router)
app.include_router(guide.router)
app.include_router(playlist.router)
app.include_router(standby.router)
app.include_router(wizard.router)
app.include_router(fast_scheduler.router)
app.include_router(vod.router)

# ========================================
# REMAINING ENDPOINTS
# ========================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "status": {"server": "running"}
        })
        
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
            
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)

# ... health check, root endpoint, etc.

# ========================================
# MAIN ENTRY POINT
# ========================================

if __name__ == "__main__":
    import uvicorn
    
    api = get_core_api()
    config = api.get_config()
    http_conf = config.get("output", {}).get("http", {})
    port = http_conf.get("port", 8081)
    bind = http_conf.get("bind", "0.0.0.0")
    
    uvicorn.run(
        "akiratv.api_server:app",
        host=bind,
        port=port,
        reload=False,
        log_level="info"
    )
```

---

## Files to Update

### No Changes Required
- `launch_web.py` - Uses string import `"akiratv.api_server:app"`
- `tests/run_api_tests.py` - Uses module invocation `python -m akiratv.api_server`

### New Files to Create
1. `akiratv/models.py`
2. `akiratv/routes/__init__.py`
3. `akiratv/routes/lifecycle.py`
4. `akiratv/routes/channels.py`
5. `akiratv/routes/config.py`
6. `akiratv/routes/library.py`
7. `akiratv/routes/monitoring.py`
8. `akiratv/routes/guide.py`
9. `akiratv/routes/playlist.py`
10. `akiratv/routes/standby.py`
11. `akiratv/routes/wizard.py`
12. `akiratv/routes/fast_scheduler.py`
13. `akiratv/routes/vod.py`
14. `akiratv/routes/websocket.py`

### Files to Modify
1. `akiratv/api_server.py` - Refactor to use routers

---

## Backward Compatibility

Ensure these still work:
```python
# Import app directly
from akiratv.api_server import app

# Run as module
python -m akiratv.api_server

# Launch web
python launch_web.py
```

---

## Testing Strategy

1. Test each route module independently
2. Test full API via `python -m akiratv.api_server`
3. Test via `python launch_web.py`
4. Run existing test suite

---

## Benefits

| Metric | Before | After |
|--------|--------|-------|
| Main file lines | 2,063 | ~200 |
| Max route file | 2,063 | ~350 |
| Testability | Difficult | Easy |
| Maintainability | Hard | Easy |

---

## Implementation Order

1. Create `akiratv/models.py`
2. Create `akiratv/routes/` directory and `__init__.py`
3. Create route modules (smallest first)
4. Refactor `api_server.py` to use routers
5. Test everything works
