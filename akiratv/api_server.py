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
        
        # Determine local IP
        if bind == "0.0.0.0":
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except:
                local_ip = "127.0.0.1"
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
            
            # Note: Ngrok URL would need to be configured or detected
            # For now, we'll leave it as a placeholder that can be configured
            
            channel_urls[channel_name] = urls
        
        return {
            "channels": channel_urls,
            "local_ip": local_ip,
            "port": port,
            "tailscale_ip": tailscale_ip
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get channel URLs: {str(e)}")

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
                
                # Get today's schedule
                today_schedule = schedule_data.get("weekly", {}).get(current_day, [])
                
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
        from datetime import datetime
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
                
                # Process each day of the week
                for day in days_order:
                    day_schedule = schedule_data.get("weekly", {}).get(day, [])
                    
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

def time_to_minutes(time_str):
    """Convert HH:MM:SS to minutes since midnight"""
    try:
        parts = time_str.split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        return hours * 60 + minutes
    except:
        return 0

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