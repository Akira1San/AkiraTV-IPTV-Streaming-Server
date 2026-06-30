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
from .models import (
    PlayNowRequest,
    ConfigUpdateRequest,
    ChannelUpdateRequest,
    FastScheduleRequest,
    Response
)
from .routes import lifecycle_router, channels_router, config_router, library_router, monitoring_router, guide_router, vod_router, playlist_router, standby_router, websocket_endpoint, fast_scheduler_router, wizard_router

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

app.include_router(wizard_router)
# Register routers
app.include_router(lifecycle_router)
app.include_router(channels_router)
app.include_router(config_router)
app.include_router(library_router)
app.include_router(monitoring_router)
app.include_router(guide_router)
app.include_router(vod_router)
app.include_router(playlist_router)
app.include_router(standby_router)
app.include_router(fast_scheduler_router)

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

def notify_kodi(config):
    """Notify all Kodi devices to reload channels and EPG via JSON-RPC."""
    import logging
    logger = logging.getLogger("AkiraTV")
    kodi_conf = config.get("kodi", {})
    if not kodi_conf.get("enabled"):
        logger.info("[Kodi] Push notifications disabled in config")
        return
    devices = kodi_conf.get("devices", [])
    if not devices:
        logger.warning("[Kodi] No devices configured, skipping push")
        return
    import requests
    payloads = [
        {"jsonrpc": "2.0", "method": "PVR.TriggerChannelUpdate", "id": 1},
        {"jsonrpc": "2.0", "method": "PVR.TriggerEPGUpdate", "id": 2},
    ]
    for device in devices:
        url = f"http://{device['host']}:{device.get('port', 8080)}/jsonrpc"
        logger.info(f"[Kodi] Notifying {device.get('name', 'unknown')} at {url}")
        for payload in payloads:
            try:
                resp = requests.post(url, json=payload, timeout=5)
                logger.info(f"[Kodi] {payload['method']} → {resp.status_code}")
            except requests.RequestException as e:
                logger.warning(f"[Kodi] {device.get('host')}:{device.get('port', 8080)} - {payload['method']} failed: {e}")

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
            output_path=str(xmltv_path),
            config=config
        )
        
        generate_m3u_playlist(config, str(m3u_path))
        
        notify_kodi(config)
        
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

@app.post("/api/logs/clear")
def clear_logs():
    """Clear all log files in the logs directory"""
    import os
    log_dir = os.path.abspath("logs")
    
    cleared = []
    errors = []
    
    if os.path.exists(log_dir):
        for file in os.listdir(log_dir):
            file_path = os.path.join(log_dir, file)
            try:
                if os.path.isfile(file_path):
                    os.truncate(file_path, 0)
                    cleared.append(file)
            except Exception as e:
                errors.append({"file": file, "error": str(e)})
    
    return {
        "success": len(errors) == 0,
        "cleared": cleared,
        "errors": errors,
        "message": f"Cleared {len(cleared)} log file(s)" + (f" with {len(errors)} error(s)" if errors else "")
    }


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

@app.get("/wizard")
def wizard_page():
    """Serve the Collection & Scheduler Wizard UI"""
    wizard_path = Path(__file__).parent / "static" / "wizard.html"
    if wizard_path.exists():
        with open(wizard_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    else:
        return {"error": "Wizard page not found"}

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