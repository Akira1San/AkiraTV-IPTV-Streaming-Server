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

@app.post("/api/xmltv/generate", response_model=Response)
def generate_xmltv():
    """Generate XMLTV file for Kodi"""
    try:
        from .ui.xmltv import generate_xmltv, generate_m3u_playlist
        from pathlib import Path
        
        # Get config to determine output path
        api = get_core_api()
        config = api.get_config()
        
        # Determine output directory based on storage config
        storage = config.get("storage", {})
        if storage.get("type") == "ram":
            output_dir = Path(storage.get("ram_path", "R:/akiratv"))
        else:
            output_dir = Path(storage.get("disk_path", "./output"))
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate XMLTV
        xmltv_path = output_dir / "xmltv.xml"
        m3u_path = output_dir / "channels.m3u"
        
        generate_xmltv(
            schedules_dir="user/schedules",
            collections_dir="user/collections", 
            output_path=str(xmltv_path)
        )
        
        generate_m3u_playlist(config, str(m3u_path))
        
        # Get server info for URLs
        output_config = config.get("output", {})
        http_config = output_config.get("http", {})
        port = http_config.get("port", 8081)
        
        return Response(
            success=True,
            message="XMLTV and M3U files generated successfully",
            data={
                "xmltv_path": str(xmltv_path),
                "m3u_path": str(m3u_path),
                "xmltv_url": f"http://YOUR_IP:{port}/xmltv.xml",
                "m3u_url": f"http://YOUR_IP:{port}/channels.m3u"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate XMLTV: {str(e)}")

@app.get("/api/config/file")
def open_config_file():
    """Get config file path for opening"""
    import os
    config_path = os.path.abspath("config.json")
    return {
        "path": config_path,
        "exists": os.path.exists(config_path),
        "message": f"Config file location: {config_path}"
    }

@app.get("/api/logs")
def get_logs_info():
    """Get logs directory information"""
    import os
    log_dir = os.path.abspath("logs")
    
    # Ensure logs directory exists
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Get list of log files
    log_files = []
    if os.path.exists(log_dir):
        for file in os.listdir(log_dir):
            if file.endswith('.log'):
                file_path = os.path.join(log_dir, file)
                log_files.append({
                    "name": file,
                    "path": file_path,
                    "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
                })
    
    return {
        "directory": log_dir,
        "files": log_files,
        "message": f"Logs directory: {log_dir}"
    }

@app.post("/api/playlist/create", response_model=Response)
def create_playlist(folder_path: str):
    """Create playlist from video folder"""
    try:
        from pathlib import Path
        
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            raise HTTPException(status_code=400, detail="Invalid folder path")
        
        # Create playlists directory
        playlists_dir = Path("playlists")
        playlists_dir.mkdir(exist_ok=True)
        
        # Find all video files
        video_extensions = [".mp4", ".mkv", ".avi", ".mov", ".m4v", ".wmv", ".flv"]
        video_files = []
        for ext in video_extensions:
            video_files.extend(folder.rglob(f"*{ext}"))
        
        video_files = sorted(video_files)
        
        if not video_files:
            raise HTTPException(status_code=400, detail="No video files found in folder")
        
        # Generate live.m3u playlist
        live_playlist_path = playlists_dir / "live.m3u"
        with open(live_playlist_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for video in video_files:
                f.write(f"#EXTINF:-1,{video.stem}\n{video}\n")
        
        return Response(
            success=True,
            message=f"Playlist created with {len(video_files)} videos",
            data={
                "playlist_path": str(live_playlist_path),
                "video_count": len(video_files),
                "videos": [{"name": v.stem, "path": str(v)} for v in video_files]
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create playlist: {str(e)}")

@app.get("/api/playlist/videos")
def get_playlist_videos():
    """Get videos from current playlist"""
    try:
        from pathlib import Path
        
        live_playlist_path = Path("playlists") / "live.m3u"
        if not live_playlist_path.exists():
            return {"videos": [], "message": "No playlist found"}
        
        videos = []
        with open(live_playlist_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            current_title = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF:"):
                    # Extract title from #EXTINF:-1,Title
                    current_title = line.split(",", 1)[1] if "," in line else "Unknown"
                elif line and not line.startswith("#") and current_title:
                    videos.append({
                        "name": current_title,
                        "path": line
                    })
                    current_title = None
        
        return {"videos": videos, "count": len(videos)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read playlist: {str(e)}")

@app.post("/api/playlist/play-selected", response_model=Response)
def play_selected_video(channel: str, video_name: str):
    """Play selected video from playlist"""
    try:
        from pathlib import Path
        
        # Find video path in playlist
        live_playlist_path = Path("playlists") / "live.m3u"
        if not live_playlist_path.exists():
            raise HTTPException(status_code=404, detail="No playlist found")
        
        video_path = None
        with open(live_playlist_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if line.strip().startswith("#EXTINF:") and video_name in line:
                    # Next line should be the path
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and not next_line.startswith("#"):
                            video_path = next_line
                            break
        
        if not video_path:
            raise HTTPException(status_code=404, detail=f"Video '{video_name}' not found in playlist")
        
        if not Path(video_path).exists():
            raise HTTPException(status_code=404, detail=f"Video file not found: {video_path}")
        
        # Play the video
        api = get_core_api()
        result = api.play_now(channel, video_path)
        
        if result["success"]:
            return Response(success=True, message=f"Now playing: {Path(video_path).name}")
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to play video: {str(e)}")

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