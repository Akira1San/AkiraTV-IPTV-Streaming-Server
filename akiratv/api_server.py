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
from .fast_scheduler import FastScheduler
from .viewer_tracker import viewer_tracker

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
    type: Optional[str] = None         # "linear" | "vod" | "dynamic"

class FastScheduleRequest(BaseModel):
    collections: Optional[List[str]] = None  # Collection names to load
    start_time: Optional[str] = "00:00"      # Start time HH:MM
    schedule_hours: Optional[int] = 24       # Hours of content to generate
    bumper_frequency: Optional[int] = 3      # Insert bumper every N videos
    trailer_probability: Optional[float] = 0.3  # Probability of showing trailers

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

# Mount user directory for covers, logos, etc.
user_dir = Path(__file__).parent.parent / "user"
if user_dir.exists():
    app.mount("/user", StaticFiles(directory=str(user_dir)), name="user")
    print(f"Serving user assets from: {user_dir}")
else:
    print(f"User directory not found at: {user_dir}")
    # Create user directory if it doesn't exist
    user_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/user", StaticFiles(directory=str(user_dir)), name="user")

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

@app.get("/api/channels/urls")
def get_all_channel_urls():
    """Get streaming URLs for all enabled channels with LAN, Ngrok, and Tailscale variants"""
    try:
        import socket
        from pathlib import Path
        
        api = get_core_api()
        config = api.get_config()
        
        # Get HTTP server configuration
        http_conf = config.get("output", {}).get("http", {})
        port = http_conf.get("port", 8081)
        bind = http_conf.get("bind", "127.0.0.1")
        
        # Determine local IP - try multiple methods for robustness
        local_ip = "127.0.0.1"
        if bind == "0.0.0.0":
            # Method 1: Try connecting to Google DNS
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except:
                pass
            
            # Method 2: If method 1 failed, try getting hostname IP
            if local_ip == "127.0.0.1":
                try:
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)
                    # If still localhost, try another method
                    if local_ip.startswith("127."):
                        # Method 3: Get all network interfaces
                        import subprocess
                        try:
                            # Windows: use ipconfig
                            result = subprocess.run(['ipconfig'], capture_output=True, text=True)
                            lines = result.stdout.split('\n')
                            for i, line in enumerate(lines):
                                if 'IPv4 Address' in line or 'IPv4' in line:
                                    # Extract IP from line like "   IPv4 Address. . . . . . . . . . . : 192.168.50.183"
                                    if ':' in line:
                                        ip = line.split(':')[-1].strip()
                                        if ip and not ip.startswith('127.'):
                                            local_ip = ip
                                            break
                        except:
                            pass
                except:
                    pass
        else:
            local_ip = bind
        
        # Try to detect Tailscale IP
        tailscale_ip = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("100.100.100.100", 1))  # Tailscale network dummy IP
            tailscale_ip = s.getsockname()[0]
            s.close()
        except:
            pass
        
        # Get enabled channels
        channels = api.get_channels()
        enabled_channels = [ch for ch in channels if ch.enabled]
        
        channel_urls = {}
        
        for channel in enabled_channels:
            channel_name = channel.name
            urls = {
                "lan": {
                    "stream": f"http://{local_ip}:{port}/hls/{channel_name}/index.m3u8",
                    "epg": f"http://{local_ip}:{port}/xmltv.xml"
                }
            }
            
            # Add Tailscale URLs if available
            if tailscale_ip and tailscale_ip != local_ip:
                urls["tailscale"] = {
                    "stream": f"http://{tailscale_ip}:{port}/hls/{channel_name}/index.m3u8",
                    "epg": f"http://{tailscale_ip}:{port}/xmltv.xml"
                }
            
            channel_urls[channel_name] = urls
        
        return {
            "channels": channel_urls,
            "local_ip": local_ip,
            "tailscale_ip": tailscale_ip
        }
    
    except Exception as e:
        print(f"Error getting channel URLs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
    """Update channel-specific settings (transcoding, subtitles, type)"""
    api = get_core_api()
    
    # Get current config
    config = api.get_config()
    channels_config = config.get("channels", {})
    
    if channel not in channels_config:
        raise HTTPException(status_code=404, detail=f"Channel '{channel}' not found")
    
    # Prepare updates
    updates = {}
    channel_updates = {}
    
    # Handle type change
    if request.type is not None:
        if request.type not in ["linear", "vod", "dynamic"]:
            raise HTTPException(status_code=400, detail="Channel type must be 'linear', 'vod', or 'dynamic'")
        
        current_type = channels_config[channel].get("type", "linear")
        if request.type != current_type:
            channel_updates["type"] = request.type
            print(f"[REFRESH] Changing channel '{channel}' type from '{current_type}' to '{request.type}'")
    
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
        message = f"Channel '{channel}' settings updated"
        if request.type is not None:
            message += f" (type changed to {request.type})"
        return Response(success=True, message=message)
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

@app.post("/api/channels/{channel}/stop", response_model=Response)
def stop_channel(channel: str):
    """Stop current video on VOD/Dynamic channel"""
    api = get_core_api()
    result = api.stop_channel(channel)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])

@app.post("/api/channels/{channel}/stop-worker", response_model=Response)
def stop_channel_worker(channel: str):
    """Stop channel worker completely"""
    api = get_core_api()
    result = api.stop_channel_worker(channel)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])

@app.post("/api/channels/{channel}/restart", response_model=Response)
def restart_channel(channel: str):
    """Restart a specific channel worker"""
    api = get_core_api()
    result = api.restart_channel(channel)
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
            output_dir = Path(storage.get("ram_path", "./output"))
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

@app.get("/api/guide")
def get_tv_guide():
    """Get TV guide data for all channels"""
    try:
        import json
        from datetime import datetime, timedelta
        from pathlib import Path
        
        # Get current time
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        current_day = now.strftime("%A").lower()
        
        # Get all channels
        api = get_core_api()
        channels = api.get_channels()
        
        guide_data = {}
        
        for channel in channels:
            if not channel.enabled:
                continue
                
            channel_name = channel.name
            schedule_file = Path(f"user/schedules/schedule_{channel_name}.json")
            
            if not schedule_file.exists():
                # No schedule file, show as "No schedule"
                guide_data[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "current_program": None,
                    "next_program": None,
                    "schedule": []
                }
                continue
            
            try:
                with open(schedule_file, 'r', encoding='utf-8') as f:
                    schedule_data = json.load(f)
                
                # Get today's date string for calendar lookup
                today_date_str = now.strftime("%Y-%m-%d")
                
                # Get today's schedule (check calendar first, then weekly)
                today_schedule = get_schedule_for_date(schedule_data, today_date_str, current_day)
                
                # Find current and next programs
                current_program = None
                next_program = None
                
                # Convert current time to minutes for comparison
                current_minutes = time_to_minutes(current_time)
                
                # Sort schedule by time
                sorted_schedule = sorted(today_schedule, key=lambda x: time_to_minutes(x["time"]))
                
                for i, program in enumerate(sorted_schedule):
                    program_minutes = time_to_minutes(program["time"])
                    
                    # Check if this program is currently playing
                    if i < len(sorted_schedule) - 1:
                        next_program_minutes = time_to_minutes(sorted_schedule[i + 1]["time"])
                        if program_minutes <= current_minutes < next_program_minutes:
                            current_program = program
                            next_program = sorted_schedule[i + 1]
                            break
                    else:
                        # Last program of the day
                        if program_minutes <= current_minutes:
                            current_program = program
                            # Next program would be first program of tomorrow
                            if sorted_schedule:
                                next_program = sorted_schedule[0]
                            break
                
                # If no current program found, use the last program that started
                if not current_program and sorted_schedule:
                    for program in reversed(sorted_schedule):
                        if time_to_minutes(program["time"]) <= current_minutes:
                            current_program = program
                            break
                
                # Format programs for display
                if current_program:
                    current_program["display_name"] = Path(current_program["file"]).stem
                    current_program["duration_estimate"] = "~90 min"  # Could be calculated from file
                
                if next_program:
                    next_program["display_name"] = Path(next_program["file"]).stem
                    next_program["duration_estimate"] = "~90 min"
                
                # Get next few programs for the guide
                upcoming_programs = []
                current_index = -1
                
                # Find current program index
                for i, program in enumerate(sorted_schedule):
                    if current_program and program["time"] == current_program["time"]:
                        current_index = i
                        break
                
                # Get next 5 programs
                for i in range(max(0, current_index), min(len(sorted_schedule), current_index + 6)):
                    program = sorted_schedule[i].copy()
                    program["display_name"] = Path(program["file"]).stem
                    program["is_current"] = (i == current_index)
                    upcoming_programs.append(program)
                
                guide_data[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "current_program": current_program,
                    "next_program": next_program,
                    "schedule": upcoming_programs
                }
                
            except Exception as e:
                # Error reading schedule file
                guide_data[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "current_program": None,
                    "next_program": None,
                    "schedule": [],
                    "error": f"Error reading schedule: {str(e)}"
                }
        
        return {
            "guide": guide_data,
            "current_time": current_time,
            "current_day": current_day,
            "timestamp": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get TV guide: {str(e)}")

@app.get("/api/guide/weekly")
def get_weekly_tv_guide():
    """Get full weekly TV guide for all channels"""
    try:
        import json
        from datetime import datetime, timedelta
        from pathlib import Path
        
        # Get current time for highlighting current program
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        current_day = now.strftime("%A").lower()
        current_minutes = time_to_minutes(current_time)
        
        # Get all channels
        api = get_core_api()
        channels = api.get_channels()
        
        weekly_guide = {}
        days_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        
        for channel in channels:
            if not channel.enabled:
                continue
                
            channel_name = channel.name
            schedule_file = Path(f"user/schedules/schedule_{channel_name}.json")
            
            if not schedule_file.exists():
                # No schedule file
                weekly_guide[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "weekly_schedule": {},
                    "error": "No schedule file found"
                }
                continue
            
            try:
                with open(schedule_file, 'r', encoding='utf-8') as f:
                    schedule_data = json.load(f)
                
                weekly_schedule = {}
                
                # Calculate dates for each day of the current week
                # Find the date for Monday of this week
                today = now.date()
                days_since_monday = today.weekday()  # Monday = 0, Sunday = 6
                monday_date = today - timedelta(days=days_since_monday)
                
                # Process each day of the week
                for i, day in enumerate(days_order):
                    # Calculate the date for this day
                    day_date = monday_date + timedelta(days=i)
                    day_date_str = day_date.strftime("%Y-%m-%d")
                    
                    # Get schedule for this date (check calendar first, then weekly)
                    day_schedule = get_schedule_for_date(schedule_data, day_date_str, day)
                    
                    # Sort programs by time
                    sorted_programs = sorted(day_schedule, key=lambda x: time_to_minutes(x["time"]))
                    
                    # Format programs for display
                    formatted_programs = []
                    for i, program in enumerate(sorted_programs):
                        formatted_program = program.copy()
                        formatted_program["display_name"] = Path(program["file"]).stem
                        formatted_program["duration_estimate"] = "~90 min"
                        
                        # Mark current program if it's today and currently playing
                        if day == current_day:
                            program_minutes = time_to_minutes(program["time"])
                            if i < len(sorted_programs) - 1:
                                next_program_minutes = time_to_minutes(sorted_programs[i + 1]["time"])
                                formatted_program["is_current"] = program_minutes <= current_minutes < next_program_minutes
                            else:
                                # Last program of the day
                                formatted_program["is_current"] = program_minutes <= current_minutes
                        else:
                            formatted_program["is_current"] = False
                        
                        formatted_programs.append(formatted_program)
                    
                    weekly_schedule[day] = {
                        "day_name": day.capitalize(),
                        "programs": formatted_programs,
                        "program_count": len(formatted_programs),
                        "is_today": day == current_day
                    }
                
                weekly_guide[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "weekly_schedule": weekly_schedule
                }
                
            except Exception as e:
                weekly_guide[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "weekly_schedule": {},
                    "error": f"Error reading schedule: {str(e)}"
                }
        
        return {
            "weekly_guide": weekly_guide,
            "current_time": current_time,
            "current_day": current_day,
            "days_order": days_order,
            "timestamp": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get weekly TV guide: {str(e)}")

@app.get("/api/guide/date/{date_str}")
def get_guide_for_date(date_str: str):
    """Get TV guide data for a specific date (YYYY-MM-DD format)"""
    try:
        import json
        from datetime import datetime, timedelta
        from pathlib import Path
        
        # Parse the date string
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Get the day name for the selected date
        day_name = selected_date.strftime("%A").lower()
        
        # Get all channels
        api = get_core_api()
        channels = api.get_channels()
        
        guide_data = {}
        
        for channel in channels:
            if not channel.enabled:
                continue
                
            channel_name = channel.name
            schedule_file = Path(f"user/schedules/schedule_{channel_name}.json")
            
            if not schedule_file.exists():
                # No schedule file, show as "No schedule"
                guide_data[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "schedule": [],
                    "error": "No schedule file found"
                }
                continue
            
            try:
                with open(schedule_file, 'r', encoding='utf-8') as f:
                    schedule_data = json.load(f)
                
                # Get the schedule for the selected date (check calendar first, then weekly)
                day_schedule = get_schedule_for_date(schedule_data, date_str, day_name)
                
                # Sort schedule by time
                sorted_schedule = sorted(day_schedule, key=lambda x: time_to_minutes(x["time"]))
                
                # Format programs for display
                formatted_schedule = []
                for program in sorted_schedule:
                    formatted_program = program.copy()
                    formatted_program["display_name"] = Path(program["file"]).stem
                    formatted_program["duration_estimate"] = "~90 min"
                    formatted_schedule.append(formatted_program)
                
                guide_data[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "schedule": formatted_schedule,
                    "program_count": len(formatted_schedule)
                }
                
            except Exception as e:
                # Error reading schedule file
                guide_data[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "schedule": [],
                    "error": f"Error reading schedule: {str(e)}"
                }
        
        return {
            "guide": guide_data,
            "selected_date": date_str,
            "day_name": day_name.capitalize(),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get TV guide for date: {str(e)}")

def time_to_minutes(time_str):
    """Convert HH:MM:SS to minutes since midnight"""
    try:
        parts = time_str.split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        return hours * 60 + minutes
    except:
        return 0

def get_schedule_for_date(schedule_data: dict, date_str: str, day_name: str) -> list:
    """
    Get schedule entries for a specific date.
    First checks calendar section (e.g., "2026-02-21_saturday"), then falls back to weekly.
    
    Args:
        schedule_data: The loaded schedule JSON (has 'weekly' and 'calendar' keys)
        date_str: Date string in YYYY-MM-DD format
        day_name: Day name in lowercase (e.g., "saturday")
    
    Returns:
        List of schedule entries for the date
    """
    # First, try calendar section (for calendar-based schedules)
    calendar_key = f"{date_str}_{day_name}"
    calendar_entry = schedule_data.get("calendar", {}).get(calendar_key)
    if calendar_entry and calendar_entry.get("entries"):
        return calendar_entry["entries"]
    
    # Fall back to weekly section (for weekly-based schedules)
    weekly_entries = schedule_data.get("weekly", {}).get(day_name, [])
    if weekly_entries:
        return weekly_entries
    
    return []

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

@app.post("/api/standby/create", response_model=Response)
def create_standby_loop():
    """Create standby loop videos for all resolutions found in inventory"""
    try:
        from pathlib import Path
        from collections import Counter
        import json
        import threading
        import asyncio
        
        def _create_standby():
            try:
                from .standby import create_standby_video
                
                # Create standby directory
                standby_dir = Path("assets/standby")
                standby_dir.mkdir(parents=True, exist_ok=True)
                
                # Get all unique resolutions from inventory
                resolutions = []
                inventory_file = Path("user/video_inventory.json")
                
                if inventory_file.exists():
                    with open(inventory_file, 'r', encoding='utf-8') as f:
                        inventory_data = json.load(f)
                    
                    for item in inventory_data:
                        video_tracks = item.get("video_tracks", [])
                        if video_tracks and len(video_tracks) > 0:
                            width = video_tracks[0].get("width")
                            height = video_tracks[0].get("height")
                            if width and height:
                                resolutions.append((width, height))
                    
                    if resolutions:
                        resolution_counts = Counter(resolutions)
                        resolutions = [
                            (f"{width}x{height}", width, height)
                            for (width, height), count in resolution_counts.most_common()
                        ]
                
                # Fallback to common resolutions if inventory is empty
                if not resolutions:
                    resolutions = [
                        ("1920x1080", 1920, 1080),
                        ("1280x720", 1280, 720),
                        ("720x400", 720, 400)
                    ]
                
                created_files = []
                codec = "h265"  # Default to h265
                
                # Create a standby video for each resolution
                for res_name, width, height in resolutions:
                    output_path = standby_dir / f"standby_{res_name}.mp4"
                    
                    try:
                        created_path = create_standby_video(
                            duration=30,
                            codec=codec,
                            output_path=output_path,
                            resolution=(width, height)
                        )
                        created_files.append(f"{res_name}: {created_path.name}")
                    except Exception as e:
                        print(f"Failed to create standby for {res_name}: {e}")
                        continue
                
                # Also create a default standby (most common resolution)
                if resolutions:
                    default_res = resolutions[0]  # Most common resolution
                    default_path = standby_dir / "default_standby.mp4"
                    try:
                        create_standby_video(
                            duration=30,
                            codec=codec,
                            output_path=default_path,
                            resolution=(default_res[1], default_res[2])
                        )
                        created_files.append(f"default: {default_path.name}")
                    except Exception as e:
                        print(f"Failed to create default standby: {e}")
                
                return created_files
                
            except Exception as e:
                print(f"Error in _create_standby: {e}")
                raise
        
        # Run standby creation
        created_files = _create_standby()
        
        if created_files:
            files_list = "\n".join(created_files)
            return Response(
                success=True,
                message=f"Standby loops created successfully",
                data={
                    "created_files": created_files,
                    "directory": "assets/standby/",
                    "files_list": files_list
                }
            )
        else:
            raise HTTPException(status_code=500, detail="No standby files were created")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create standby loops: {str(e)}")

# ========================================
# WIZARD ENDPOINTS
# ========================================

@app.post("/api/wizard/log", response_model=Response)
def log_wizard_event(request: dict):
    """Log wizard events to file"""
    try:
        from pathlib import Path
        import json
        from datetime import datetime
        
        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Create wizard log file
        log_file = logs_dir / "wizard.log"
        
        # Format log entry
        timestamp = request.get("timestamp", datetime.now().isoformat())
        level = request.get("level", "info").upper()
        message = request.get("message", "")
        data = request.get("data", {})
        
        log_entry = f"[{timestamp}] [{level}] {message}"
        if data:
            log_entry += f" | Data: {json.dumps(data, ensure_ascii=False)}"
        log_entry += "\n"
        
        # Append to log file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        return Response(success=True, message="Log entry written")
        
    except Exception as e:
        # Don't fail the wizard if logging fails
        print(f"Failed to write wizard log: {e}")
        return Response(success=False, error=str(e))

@app.post("/api/wizard/scan-folder", response_model=Response)
def scan_folder_for_videos(request: dict):
    """Scan folder for video files"""
    try:
        from pathlib import Path
        
        folder_path = request.get("folder_path")
        if not folder_path:
            raise HTTPException(status_code=400, detail="folder_path is required")
        
        folder = Path(folder_path)
        if not folder.exists():
            raise HTTPException(status_code=400, detail=f"Folder does not exist: {folder_path}")
        
        if not folder.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {folder_path}")
        
        # Video file extensions
        video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.m4v', '.wmv', '.flv', '.webm', '.mpg', '.mpeg', '.ts', '.m2ts'}
        
        videos = []
        total_size = 0
        
        print(f"[SEARCH] Scanning folder: {folder_path}")
        
        # Scan for video files
        for file_path in folder.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                try:
                    file_size = file_path.stat().st_size
                    videos.append({
                        'name': file_path.name,
                        'path': str(file_path),
                        'size': file_size,
                        'format': file_path.suffix[1:].upper(),
                        'relative_path': str(file_path.relative_to(folder))
                    })
                    total_size += file_size
                    print(f"[FOLDER] Found video: {file_path.name}")
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    continue
        
        # Sort by name
        videos.sort(key=lambda x: x['name'].lower())
        
        print(f"[OK] Scan complete: {len(videos)} videos found, {total_size} bytes total")
        
        return Response(
            success=True,
            message=f"Found {len(videos)} video files",
            data={
                "videos": videos,
                "total_size": total_size,
                "folder_path": str(folder),
                "video_count": len(videos)
            }
        )
        
    except Exception as e:
        print(f"[ERROR] Folder scan error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to scan folder: {str(e)}")

@app.post("/api/wizard/collection/check", response_model=Response)
def check_collection_exists(request: dict):
    """Check if a collection already exists"""
    try:
        from pathlib import Path
        
        collection_name = request.get("collection_name", "").strip()
        if not collection_name:
            return Response(success=True, data={"exists": False})
        
        # Convert collection name to potential channel names and check for existing files
        potential_channel_name = collection_name.lower().replace(' ', '_').replace('-', '_')
        potential_channel_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in potential_channel_name)
        potential_channel_name = '_'.join(potential_channel_name.split('_'))  # Clean up multiple underscores
        
        collections_dir = Path("user/collections")
        
        # Check for various possible collection file names
        possible_files = [
            collections_dir / f"collections_{potential_channel_name}.json",
            collections_dir / f"collections_{collection_name.lower().replace(' ', '_')}.json",
            collections_dir / f"collections_{collection_name.lower()}.json"
        ]
        
        exists = any(file.exists() for file in possible_files)
        
        return Response(
            success=True,
            data={
                "exists": exists,
                "collection_name": collection_name,
                "potential_files": [str(f) for f in possible_files if f.exists()]
            }
        )
        
    except Exception as e:
        print(f"[ERROR] Collection check error: {str(e)}")
        return Response(success=True, data={"exists": False})  # Fail gracefully


@app.post("/api/wizard/collection/create", response_model=Response)
def create_collection_wizard(request: dict):
    """Create collection file from wizard (collections only, no channel creation)"""
    try:
        from pathlib import Path
        import json
        
        # Extract data from request
        collection_name = request.get("collection_name")
        channel_name = request.get("channel_name")
        folder_path = request.get("folder_path")
        collection_data = request.get("collection_data", {})
        overwrite_existing = request.get("overwrite_existing", False)
        
        print(f"[WIZARD] Creating collection via wizard:")
        print(f"   Collection: {collection_name}")
        print(f"   Channel: {channel_name}")
        print(f"   Folder: {folder_path}")
        print(f"   Overwrite: {overwrite_existing}")
        
        # Validate inputs
        if not collection_name or not collection_name.strip():
            raise HTTPException(status_code=400, detail="Collection name is required")
        
        if not channel_name or not channel_name.strip():
            raise HTTPException(status_code=400, detail="Channel name is required")
        
        # Verify channel exists
        api = get_core_api()
        existing_channels = api.get_channels()
        channel_names = [ch.name for ch in existing_channels]
        
        if channel_name not in channel_names:
            raise HTTPException(
                status_code=400, 
                detail=f"Channel '{channel_name}' does not exist. Available channels: {', '.join(channel_names) if channel_names else 'None'}. Please create the channel first using 'Add Channel'."
            )
        
        print(f"[OK] Channel '{channel_name}' exists and is available.")
        
        # Create collections directory
        collections_dir = Path("user/collections")
        collections_dir.mkdir(parents=True, exist_ok=True)
        
        # Create collection file
        collection_file = collections_dir / f"collections_{channel_name}.json"
        
        # Check if collection file already exists
        if collection_file.exists() and not overwrite_existing:
            raise HTTPException(
                status_code=409, 
                detail=f"Collection file already exists: {collection_file.name}. Use overwrite_existing=true to replace it."
            )
        
        # Prepare collection data in the correct AkiraTV format
        collections = []
        
        for video in collection_data.get("videos", []):
            # Generate collection ID from video name
            video_name = video.get("name", "")
            collection_id = video_name.lower()
            # Clean up the ID - remove file extension and special characters
            collection_id = collection_id.rsplit('.', 1)[0]  # Remove extension
            collection_id = ''.join(c if c.isalnum() else '_' for c in collection_id)  # Replace special chars
            collection_id = '_'.join(collection_id.split())  # Replace spaces with underscores
            
            # Generate display name from video name
            display_name = video_name.rsplit('.', 1)[0]  # Remove extension
            # Clean up display name - remove common prefixes and improve formatting
            display_name = display_name.replace('encoded_', '').replace('_', ' ')
            display_name = ' '.join(word.capitalize() for word in display_name.split())
            
            # Convert Windows path to forward slashes for AkiraTV
            video_path = video.get("path", "").replace("\\", "/")
            
            # Try to get video duration using FFprobe
            duration = get_video_duration(video_path)
            
            collection_entry = {
                "id": collection_id,
                "name": display_name,
                "cover": None,
                "description": "",
                "genre": [],
                "year": 2026,  # Could be extracted from filename or metadata
                "videos": [
                    {
                        "path": video_path,
                        "duration": duration
                    }
                ]
            }
            collections.append(collection_entry)
        
        # Create the proper AkiraTV collections format
        collection_content = {
            "collections": collections
        }
        
        print(f"[FOLDER] Writing collection file: {collection_file}")
        print(f"   Collections count: {len(collections)}")
        print(f"   Sample collection: {collections[0] if collections else 'None'}")
        
        # Write collection file
        with open(collection_file, 'w', encoding='utf-8') as f:
            json.dump(collection_content, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Collection file created successfully")
        
        return Response(
            success=True,
            message=f"Collection '{collection_name}' created successfully for channel '{channel_name}'",
            data={
                "collection_file": str(collection_file),
                "channel_name": channel_name,
                "collections_count": len(collections),
                "video_count": sum(len(c["videos"]) for c in collections),
                "overwrite_existing": overwrite_existing
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"[ERROR] Collection creation error: {str(e)}")
        print(f"   Request data: {request}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create collection: {str(e)}")

def get_video_duration(video_path):
    """Get video duration using FFprobe"""
    try:
        import subprocess
        import json
        
        # Use ffprobe to get video duration
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration = float(data.get('format', {}).get('duration', 0))
            print(f"   📹 Duration for {video_path}: {duration:.2f}s")
            return duration
        else:
            print(f"   ⚠️ FFprobe failed for {video_path}: {result.stderr}")
            return 0
            
    except Exception as e:
        print(f"   ⚠️ Could not get duration for {video_path}: {e}")
        return 0

@app.post("/api/wizard/schedule/create", response_model=Response)
def create_schedule_wizard(
    channel_name: str,
    schedule_type: str,
    schedule_data: dict
):
    """Create schedule from wizard"""
    try:
        from pathlib import Path
        import json
        
        # Validate inputs
        if not channel_name.strip():
            raise HTTPException(status_code=400, detail="Channel name is required")
        
        if schedule_type not in ['weekly', 'daily']:
            raise HTTPException(status_code=400, detail="Invalid schedule type")
        
        # Check if channel exists
        api = get_core_api()
        channel = api.get_channel(channel_name)
        if not channel:
            raise HTTPException(status_code=404, detail=f"Channel '{channel_name}' not found")
        
        # Create schedules directory
        schedules_dir = Path("user/schedules")
        schedules_dir.mkdir(parents=True, exist_ok=True)
        
        # Create schedule file
        schedule_file = schedules_dir / f"schedule_{channel_name}.json"
        
        # Prepare schedule content
        schedule_content = {
            "channel": channel_name,
            "type": schedule_type,
            "created": schedule_data.get("created", ""),
            "weekly": schedule_data.get("weekly", {}),
            "metadata": {
                "total_slots": sum(len(day_schedule) for day_schedule in schedule_data.get("weekly", {}).values()),
                "days_with_schedule": len(schedule_data.get("weekly", {})),
                "created_by": "wizard"
            }
        }
        
        # Write schedule file
        with open(schedule_file, 'w', encoding='utf-8') as f:
            json.dump(schedule_content, f, indent=2, ensure_ascii=False)
        
        # Reload schedule for the channel
        reload_result = api.reload_schedule(channel_name)
        if not reload_result["success"]:
            print(f"Warning: Failed to reload schedule for {channel_name}: {reload_result.get('error')}")
        
        return Response(
            success=True,
            message=f"Schedule created successfully for channel '{channel_name}'",
            data={
                "schedule_file": str(schedule_file),
                "channel_name": channel_name,
                "schedule_type": schedule_type,
                "total_slots": schedule_content["metadata"]["total_slots"],
                "days_with_schedule": schedule_content["metadata"]["days_with_schedule"]
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")

# ========================================
# FAST SCHEDULER ENDPOINTS
# ========================================

# Global fast schedulers cache
fast_schedulers: Dict[str, FastScheduler] = {}

def get_fast_scheduler(channel_name: str) -> FastScheduler:
    """Get or create a FastScheduler instance for a channel"""
    if channel_name not in fast_schedulers:
        fast_schedulers[channel_name] = FastScheduler(channel_name)
    return fast_schedulers[channel_name]

@app.post("/api/fast-schedule/{channel}/load-collections", response_model=Response)
def load_fast_schedule_collections(channel: str, request: FastScheduleRequest):
    """Load collections for fast scheduling"""
    try:
        scheduler = get_fast_scheduler(channel)
        result = scheduler.load_collections(request.collections)
        
        if result["success"]:
            return Response(
                success=True, 
                message=result["message"],
                data={"videos_loaded": result["videos_loaded"]}
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load collections: {str(e)}")

@app.post("/api/fast-schedule/{channel}/generate", response_model=Response)
def generate_fast_schedule(channel: str, request: FastScheduleRequest):
    """Generate a fast schedule for a channel"""
    try:
        scheduler = get_fast_scheduler(channel)
        
        # Update settings if provided
        if request.schedule_hours:
            scheduler.schedule_length_hours = request.schedule_hours
        if request.bumper_frequency:
            scheduler.bumper_frequency = request.bumper_frequency
        if request.trailer_probability is not None:
            scheduler.trailer_probability = request.trailer_probability
        
        # Generate schedule
        result = scheduler.generate_schedule(request.start_time or "00:00")
        
        if result["success"]:
            # Auto-save checkpoint
            scheduler.save_checkpoint()
            
            return Response(
                success=True,
                message=result["message"],
                data={
                    "entries": result["entries"],
                    "videos": result.get("videos", 0),
                    "bumpers": result.get("bumpers", 0)
                }
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate schedule: {str(e)}")

@app.get("/api/fast-schedule/{channel}/info")
def get_fast_schedule_info(channel: str):
    """Get fast schedule information for a channel"""
    try:
        scheduler = get_fast_scheduler(channel)
        info = scheduler.get_schedule_info()
        return {"success": True, "data": info}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get schedule info: {str(e)}")

@app.get("/api/fast-schedule/{channel}/current")
def get_current_fast_schedule_entry(channel: str):
    """Get the current schedule entry that should be playing"""
    try:
        scheduler = get_fast_scheduler(channel)
        current_entry = scheduler.get_current_entry()
        resume_position = scheduler.get_resume_position(current_entry) if current_entry else 0.0
        
        return {
            "success": True,
            "data": {
                "current_entry": current_entry.__dict__ if current_entry else None,
                "resume_position": resume_position
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get current entry: {str(e)}")

@app.get("/api/fast-schedule/{channel}/upcoming")
def get_upcoming_fast_schedule_entries(channel: str, count: int = 5):
    """Get upcoming schedule entries"""
    try:
        scheduler = get_fast_scheduler(channel)
        upcoming = scheduler.get_upcoming_entries(count)
        return {"success": True, "data": {"upcoming": upcoming}}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get upcoming entries: {str(e)}")

@app.post("/api/fast-schedule/{channel}/save-checkpoint", response_model=Response)
def save_fast_schedule_checkpoint(channel: str):
    """Save fast schedule checkpoint"""
    try:
        scheduler = get_fast_scheduler(channel)
        result = scheduler.save_checkpoint()
        
        if result["success"]:
            return Response(success=True, message=result["message"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save checkpoint: {str(e)}")

@app.post("/api/fast-schedule/{channel}/load-checkpoint", response_model=Response)
def load_fast_schedule_checkpoint(channel: str):
    """Load fast schedule checkpoint"""
    try:
        scheduler = get_fast_scheduler(channel)
        result = scheduler.load_checkpoint()
        
        if result["success"]:
            return Response(
                success=True, 
                message=result["message"],
                data={
                    "entries": result.get("entries", 0),
                    "saved_at": result.get("saved_at")
                }
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load checkpoint: {str(e)}")

@app.get("/api/fast-schedule/collections")
def get_available_collections():
    """Get list of available collection files"""
    try:
        collections_dir = Path("user/collections")
        if not collections_dir.exists():
            return {"success": True, "data": {"collections": []}}
        
        collections = []
        for collection_file in collections_dir.glob("collections_*.json"):
            collection_name = collection_file.stem.replace("collections_", "")
            try:
                with open(collection_file, 'r', encoding='utf-8') as f:
                    collection_data = json.load(f)
                video_count = len(collection_data) if isinstance(collection_data, dict) else 0
                
                collections.append({
                    "name": collection_name,
                    "file": collection_file.name,
                    "video_count": video_count
                })
            except Exception as e:
                collections.append({
                    "name": collection_name,
                    "file": collection_file.name,
                    "video_count": 0,
                    "error": str(e)
                })
        
        return {"success": True, "data": {"collections": collections}}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get collections: {str(e)}")

@app.get("/api/fast-schedule/{channel}/status")
def get_fast_schedule_status(channel: str):
    """Check if a channel is using Fast Scheduler and get its status"""
    try:
        from .scheduler import get_current_fast_schedule_entry
        
        # Check if channel has a fast schedule
        result = get_current_fast_schedule_entry(channel)
        
        if result["success"]:
            return {
                "success": True,
                "data": {
                    "has_fast_schedule": True,
                    "current_entry": result["entry"],
                    "resume_position": result["resume_position"],
                    "message": result["message"]
                }
            }
        else:
            return {
                "success": True,
                "data": {
                    "has_fast_schedule": False,
                    "error": result["error"]
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get fast schedule status: {str(e)}")

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
    print("AkiraTV API Server started")
    print("API docs: http://localhost:8000/docs")
    print("WebSocket: ws://localhost:8000/ws")

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

@app.get("/viewer")
def viewer_page():
    """Serve the viewer UI for regular users"""
    viewer_path = Path(__file__).parent / "static" / "viewer.html"
    if viewer_path.exists():
        with open(viewer_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    else:
        return {"error": "Viewer page not found"}

# ========================================
# VOD LIBRARY API
# ========================================

@app.get("/api/vod/library")
def get_vod_library():
    """Get video library from all collections"""
    try:
        import os
        import json
        from pathlib import Path
        
        collections_dir = Path("user/collections")
        videos = []
        collections = []
        
        if not collections_dir.exists():
            return {"videos": [], "collections": []}
        
        # Load all collection files
        for collection_file in collections_dir.glob("collections_*.json"):
            try:
                with open(collection_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                collection_name = collection_file.stem.replace('collections_', '')
                collections.append(collection_name)
                
                for item in data.get('collections', []):
                    # Extract video info
                    for video_data in item.get('videos', []):
                        video = {
                            'id': item['id'],
                            'name': item['name'],
                            'description': item.get('description', ''),
                            'cover': item.get('cover'),
                            'genre': item.get('genre', []),
                            'rating': item.get('rating', 'NR'),
                            'year': item.get('year'),
                            'duration': video_data.get('duration'),
                            'path': video_data['path'],
                            'collection': collection_name
                        }
                        videos.append(video)
                        
            except Exception as e:
                print(f"Error loading collection file {collection_file}: {e}")
                continue
        
        return {
            "success": True,
            "videos": videos,
            "collections": collections
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load video library: {str(e)}")

@app.get("/api/vod/video/{video_id}")
def get_video_details(video_id: str):
    """Get detailed information about a specific video"""
    try:
        # This would be implemented to get specific video details
        # For now, return basic info
        return {"success": True, "video": {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get video details: {str(e)}")

# ========================================
# MAIN ENTRY POINT
# ========================================

if __name__ == "__main__":
    import uvicorn
    
    # Get port from config
    api = get_core_api()
    config = api.get_config()
    http_conf = config.get("output", {}).get("http", {})
    port = http_conf.get("port", 8081)
    bind = http_conf.get("bind", "0.0.0.0")
    
    print(f"[START] Starting AkiraTV API Server")
    print(f"[DOC] API docs: http://localhost:{port}/docs")
    print(f"[WEB] Web UI: http://localhost:{port}")
    print(f"[WS] WebSocket: ws://localhost:{port}/ws")
    
    uvicorn.run(
        "akiratv.api_server:app",
        host=bind,
        port=port,
        reload=False,
        log_level="info"
    )