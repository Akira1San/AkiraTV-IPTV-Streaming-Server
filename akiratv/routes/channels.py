"""
Channel management routes for AkiraTV API
Handles all channel-related operations including creation, configuration, and control
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import socket
from pathlib import Path

from ..models import Response, ChannelUpdateRequest, PlayNowRequest
from ..core_api import get_api

router = APIRouter(prefix="/api", tags=["Channels"])

# Dependency for Core API access
def get_core_api():
    """Get CoreAPI instance"""
    return get_api()


@router.get("/channels")
def get_channels(api=Depends(get_core_api)):
    """Get all channels"""
    channels = api.get_channels()
    return {
        "channels": [ch.to_dict() for ch in channels],
        "total": len(channels)
    }


@router.post("/channels", response_model=Response)
def add_channel(channel_name: str, channel_type: str = "linear", api=Depends(get_core_api)):
    """Add a new channel"""
    result = api.add_channel(channel_name, channel_type)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])


@router.get("/channels/urls")
def get_all_channel_urls(api=Depends(get_core_api)):
    """Get streaming URLs for all enabled channels with LAN, Ngrok, and Tailscale variants"""
    try:
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


@router.get("/channels/{channel}")
def get_channel(channel: str, api=Depends(get_core_api)):
    """Get specific channel status"""
    ch = api.get_channel(channel)
    if ch is None:
        raise HTTPException(status_code=404, detail=f"Channel '{channel}' not found")
    return ch.to_dict()


@router.post("/channels/{channel}/enable", response_model=Response)
def enable_channel(channel: str, api=Depends(get_core_api)):
    """Enable a channel"""
    result = api.enable_channel(channel)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])


@router.post("/channels/{channel}/disable", response_model=Response)
def disable_channel(channel: str, api=Depends(get_core_api)):
    """Disable a channel"""
    result = api.disable_channel(channel)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])


@router.patch("/channels/{channel}", response_model=Response)
def update_channel_settings(channel: str, request: ChannelUpdateRequest, api=Depends(get_core_api)):
    """Update channel-specific settings (transcoding, subtitles, type)"""
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
        if request.type not in ["linear", "vod", "dynamic", "live"]:
            raise HTTPException(status_code=400, detail="Channel type must be 'linear', 'vod', 'dynamic', or 'live'")
        
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


@router.get("/channels/{channel}/url")
def get_channel_url(channel: str, api=Depends(get_core_api)):
    """Get streaming URLs for a channel"""
    urls = api.get_channel_url(channel)
    if "error" in urls:
        raise HTTPException(status_code=400, detail=urls["error"])
    return urls


@router.post("/channels/{channel}/play", response_model=Response)
def play_now(channel: str, request: PlayNowRequest, api=Depends(get_core_api)):
    """Play video on VOD/Dynamic channel"""
    result = api.play_now(channel, request.video_path, request.start_position)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])


@router.post("/channels/{channel}/stop", response_model=Response)
def stop_channel(channel: str, api=Depends(get_core_api)):
    """Stop current video on VOD/Dynamic channel"""
    result = api.stop_channel(channel)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])


@router.post("/channels/{channel}/stop-worker", response_model=Response)
def stop_channel_worker(channel: str, api=Depends(get_core_api)):
    """Stop channel worker completely"""
    result = api.stop_channel_worker(channel)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])


@router.post("/channels/{channel}/restart", response_model=Response)
def restart_channel(channel: str, api=Depends(get_core_api)):
    """Restart a specific channel worker"""
    result = api.restart_channel(channel)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])


@router.post("/channels/{channel}/start", response_model=Response)
def start_channel(channel: str, api=Depends(get_core_api)):
    """Start a specific channel worker (for stopped/enabled channels)"""
    result = api.start_channel(channel)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])


@router.post("/channels/{channel}/reload-schedule", response_model=Response)
def reload_channel_schedule(channel: str, api=Depends(get_core_api)):
    """Reload schedule for a specific channel"""
    result = api.reload_schedule(channel)
    if result["success"]:
        return Response(success=True, message=f"Schedule reloaded for {channel}")
    else:
        raise HTTPException(status_code=400, detail=result["error"])


@router.delete("/channels/{channel}", response_model=Response)
def delete_channel(channel: str, api=Depends(get_core_api)):
    """Delete a channel from configuration"""
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
