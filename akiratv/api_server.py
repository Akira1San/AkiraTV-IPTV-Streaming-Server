"""
FastAPI REST server for AkiraTV
Provides HTTP API for controlling AkiraTV through CoreAPI

Run with: uvicorn akiratv.api_server:app --reload --port 8000
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio
import json

from .core_api import get_api, ChannelStatus, LibraryStats
from .fast_scheduler import FastScheduler
from .models import (
    PlayNowRequest,
    ConfigUpdateRequest,
    ChannelUpdateRequest,
    FastScheduleRequest,
    Response
)
from .routes import lifecycle_router, channels_router, config_router, library_router, monitoring_router, guide_router, vod_router, websocket_endpoint

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

# Register routers
app.include_router(lifecycle_router)
app.include_router(channels_router)
app.include_router(config_router)
app.include_router(library_router)
app.include_router(monitoring_router)
app.include_router(guide_router)
app.include_router(vod_router)

# Register WebSocket endpoint
app.websocket("/ws")(websocket_endpoint)

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