"""
FastAPI REST server for AkiraTV
Provides HTTP API for controlling AkiraTV through CoreAPI

Run with: uvicorn akiratv.api_server:app --reload --port 8000
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio
import json

from .core_api import get_api, ChannelStatus, LibraryStats

# ========================================
# PYDANTIC MODELS (Request/Response)
# ========================================

class PlayNowRequest(BaseModel):
    video_path: str = Field(..., description="Full path to video file")

class ConfigUpdateRequest(BaseModel):
    updates: Dict[str, Any] = Field(..., description="Configuration updates")

class ChannelUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    transcoding: Optional[str] = None  # "global" | "enabled" | "disabled"
    subtitles: Optional[str] = None    # "global" | "enabled" | "disabled"

class Response(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Any] = None

# ========================================
# FASTAPI APP
# ========================================

app = FastAPI(
    title="AkiraTV API",
    description="REST API for controlling AkiraTV streaming engine",
    version="1.0.0"
)

# Enable CORS for web interfaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add this after creating the app
# Mount static files directory
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Get CoreAPI instance (lazy initialization)
api = None

def get_core_api():
    """Get CoreAPI instance only when needed"""
    global api
    if api is None:
        api = get_api()
    return api

# WebSocket connections for live updates
active_connections: List[WebSocket] = []

# ========================================
# LIFECYCLE ENDPOINTS
# ========================================

@app.post("/api/start", response_model=Response)
def start_engine():
    """Start AkiraTV engine"""
    api = get_core_api()
    result = api.start()
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=500, detail=result["error"])

@app.post("/api/stop", response_model=Response)
def stop_engine():
    """Stop AkiraTV engine"""
    api = get_core_api()
    result = api.stop()
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=500, detail=result["error"])

@app.post("/api/restart", response_model=Response)
def restart_engine():
    """Restart AkiraTV engine"""
    api = get_core_api()
    result = api.restart()
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=500, detail=result["error"])

@app.get("/api/status")
def get_status():
    """Get engine status"""
    api = get_core_api()
    return {
        "is_running": api.is_running,
        "uptime": api.uptime,
        "stats": api.stats
    }

# ========================================
# CHANNEL ENDPOINTS
# ========================================

@app.get("/api/channels")
def get_channels():
    """Get all channels"""
    api = get_core_api()
    channels = api.get_channels()
    return {
        "channels": [ch.to_dict() for ch in channels],
        "total": len(channels)
    }

@app.post("/api/channels", response_model=Response)
def add_channel(channel_name: str, channel_type: str = "linear"):
    """Add a new channel"""
    api = get_core_api()
    result = api.add_channel(channel_name, channel_type)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])

@app.get("/api/channels/{channel}")
def get_channel(channel: str):
    """Get specific channel status"""
    api = get_core_api()
    ch = api.get_channel(channel)
    if ch is None:
        raise HTTPException(status_code=404, detail=f"Channel '{channel}' not found")
    return ch.to_dict()

@app.post("/api/channels/{channel}/enable", response_model=Response)
def enable_channel(channel: str):
    """Enable a channel"""
    api = get_core_api()
    result = api.enable_channel(channel)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])

@app.post("/api/channels/{channel}/disable", response_model=Response)
def disable_channel(channel: str):
    """Disable a channel"""
    api = get_core_api()
    result = api.disable_channel(channel)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])

@app.patch("/api/channels/{channel}", response_model=Response)
def update_channel_settings(channel: str, request: ChannelUpdateRequest):
    """Update channel-specific settings (transcoding, subtitles)"""
    api = get_core_api()
    
    # Get current config
    config = api.get_config()
    channels_config = config.get("channels", {})
    
    if channel not in channels_config:
        raise HTTPException(status_code=404, detail=f"Channel '{channel}' not found")
    
    # Prepare updates
    updates = {}
    channel_updates = {}
    
    if request.transcoding is not None:
        if request.transcoding == "global":
            # Remove channel-specific override
            if "transcoding" in channels_config[channel]:
                del channels_config[channel]["transcoding"]
        else:
            # Set channel-specific override
            channel_updates["transcoding"] = {"enabled": request.transcoding == "enabled"}
    
    if request.subtitles is not None:
        if request.subtitles == "global":
            # Remove channel-specific override
            if "enable_subtitles" in channels_config[channel]:
                del channels_config[channel]["enable_subtitles"]
        else:
            # Set channel-specific override
            channel_updates["enable_subtitles"] = request.subtitles == "enabled"
    
    # Apply channel updates
    if channel_updates:
        channels_config[channel].update(channel_updates)
    
    # Update the config
    updates["channels"] = channels_config
    result = api.update_config(updates)
    
    if result["success"]:
        return Response(success=True, message=f"Channel '{channel}' settings updated")
    else:
        raise HTTPException(status_code=400, detail=result["error"])

@app.get("/api/channels/{channel}/url")
def get_channel_url(channel: str):
    """Get streaming URLs for a channel"""
    api = get_core_api()
    urls = api.get_channel_url(channel)
    if "error" in urls:
        raise HTTPException(status_code=400, detail=urls["error"])
    return urls

@app.post("/api/channels/{channel}/play", response_model=Response)
def play_now(channel: str, request: PlayNowRequest):
    """Play video on VOD/Dynamic channel"""
    api = get_core_api()
    result = api.play_now(channel, request.video_path)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])

# ========================================
# CONFIGURATION ENDPOINTS
# ========================================

@app.get("/api/config")
def get_config():
    """Get full configuration"""
    api = get_core_api()
    return api.get_config()

@app.patch("/api/config", response_model=Response)
def update_config(request: ConfigUpdateRequest):
    """Update configuration"""
    api = get_core_api()
    result = api.update_config(request.updates)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])

@app.post("/api/config/save", response_model=Response)
def save_config():
    """Save configuration to disk"""
    api = get_core_api()
    result = api.save_config()
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])

@app.get("/api/config/defaults")
def get_default_config():
    """Get default configuration"""
    from .config import Config
    return Config.default_config()

# ========================================
# LIBRARY ENDPOINTS
# ========================================

@app.get("/api/library/stats")
def get_library_stats():
    """Get library statistics"""
    api = get_core_api()
    stats = api.get_library_stats()
    if stats is None:
        raise HTTPException(status_code=503, detail="Engine not running")
    return stats.to_dict()

@app.post("/api/library/scan", response_model=Response)
def scan_library(path: Optional[str] = None):
    """Trigger library scan"""
    api = get_core_api()
    result = api.scan_library(path)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])

# ========================================
# MONITORING ENDPOINTS
# ========================================

@app.get("/api/stats")
def get_stats():
    """Get live statistics"""
    api = get_core_api()
    return api.stats

@app.get("/api/viewers")
def get_viewers():
    """Get active viewer count"""
    api = get_core_api()
    return {"viewers": api.get_viewers()}

@app.get("/api/logs")
def get_logs(limit: int = 100):
    """Get recent log entries"""
    api = get_core_api()
    logs = api.get_logs(limit)
    return {"logs": logs, "count": len(logs)}

# ========================================
# UTILITY ENDPOINTS
# ========================================

@app.post("/api/cache/clear", response_model=Response)
def clear_cache():
    """Clear HLS cache"""
    api = get_core_api()
    result = api.clear_cache()
    if result["success"]:
        return Response(
            success=True,
            message=result["message"],
            data={"deleted": result.get("deleted", 0)}
        )
    else:
        raise HTTPException(status_code=500, detail=result["error"])

@app.post("/api/schedule/reload", response_model=Response)
def reload_schedule(channel: Optional[str] = None):
    """Reload schedule for all channels or specific channel"""
    api = get_core_api()
    result = api.reload_schedule(channel)
    if result["success"]:
        message = f"Schedule reloaded for {channel}" if channel else "All schedules reloaded"
        return Response(success=True, message=message)
    else:
        raise HTTPException(status_code=400, detail=result["error"])

@app.post("/api/channels/{channel}/reload-schedule", response_model=Response)
def reload_channel_schedule(channel: str):
    """Reload schedule for a specific channel"""
    api = get_core_api()
    result = api.reload_schedule(channel)
    if result["success"]:
        return Response(success=True, message=f"Schedule reloaded for {channel}")
    else:
        raise HTTPException(status_code=400, detail=result["error"])

@app.delete("/api/channels/{channel}", response_model=Response)
def delete_channel(channel: str):
    """Delete a channel from configuration"""
    api = get_core_api()
    
    # Get current config
    config = api.get_config()
    channels_config = config.get("channels", {})
    
    if channel not in channels_config:
        raise HTTPException(status_code=404, detail=f"Channel '{channel}' not found")
    
    # Remove the channel from config
    del channels_config[channel]
    
    # Update the full config
    config["channels"] = channels_config
    
    # Save directly to config.json file
    try:
        import json
        config_path = "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        
        return Response(success=True, message=f"Channel '{channel}' deleted successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")

# ========================================
# WEBSOCKET FOR LIVE UPDATES
# ========================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send minimal initial status (no API calls)
        await websocket.send_json({
            "type": "connected",
            "status": {
                "server": "running"
            }
        })
        
        # Keep connection alive by waiting for disconnect
        # No automatic updates - only manual API calls
        while True:
            try:
                await websocket.receive_text()  # Wait for any message
            except WebSocketDisconnect:
                break
            
    except WebSocketDisconnect:
        pass
    finally:
        # Clean up connection
        if websocket in active_connections:
            active_connections.remove(websocket)

async def broadcast_event(event: Dict[str, Any]):
    """Broadcast event to all connected WebSocket clients"""
    dead_connections = []
    for connection in active_connections:
        try:
            await connection.send_json(event)
        except:
            dead_connections.append(connection)
    
    # Clean up dead connections
    for connection in dead_connections:
        active_connections.remove(connection)

# ========================================
# EVENT HANDLERS
# ========================================

# Register event handlers to broadcast via WebSocket
def setup_event_handlers():
    """Setup event handlers for broadcasting"""
    # Simplified: No WebSocket broadcasting for now to avoid async issues
    # The web UI will refresh data through regular API calls
    pass

# Setup on startup
@app.on_event("startup")
async def startup():
    setup_event_handlers()
    print("🚀 AkiraTV API Server started")
    print("📖 API docs: http://localhost:8000/docs")
    print("🔌 WebSocket: ws://localhost:8000/ws")

@app.on_event("shutdown")
async def shutdown():
    print("🛑 AkiraTV API Server shutting down")

# ========================================
# HEALTH CHECK
# ========================================

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "server": "running"
    }

# Update the root endpoint to serve index.html
@app.get("/")
def root():
    """Serve the web UI"""
    ui_path = Path(__file__).parent / "static" / "index.html"
    if ui_path.exists():
        with open(ui_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    else:
        return {
            "name": "AkiraTV API",
            "version": "1.0.0",
            "docs": "/docs",
            "websocket": "/ws",
            "note": "Web UI not found. Create 'static' directory with index.html, styles.css, and app.js"
        }