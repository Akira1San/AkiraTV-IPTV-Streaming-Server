"""
Android Bridge - Simplified functions for Kotlin to call via ChaQuPy

This module provides a clean interface between Android/Kotlin and AkiraTV's Python core.
No FastAPI/uvicorn needed - the Kotlin HTTP server handles API endpoints!
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("AkiraTV")

# Android-specific paths (set via set_android_paths)
_android_usb_path: Optional[str] = None
_android_storage_path: Optional[str] = None


def is_android() -> bool:
    """Check if running on Android via ChaQuPy"""
    return os.name == 'java' or 'ANDROID_STORAGE' in os.environ


def set_android_paths(usb_path: str) -> bool:
    """
    Set Android-specific storage paths.
    Called from Kotlin when USB storage is detected.
    
    Args:
        usb_path: Path to USB storage (e.g., /storage/XXXX-XXXX/AkiraTV)
    
    Returns:
        True if paths were set successfully
    """
    global _android_usb_path, _android_storage_path
    
    _android_usb_path = usb_path
    _android_storage_path = usb_path
    
    logger.info(f"Android paths set to: {usb_path}")
    return True


def get_android_paths() -> Dict[str, Optional[str]]:
    """Get the current Android paths configuration"""
    return {
        "usb_path": _android_usb_path,
        "storage_path": _android_storage_path
    }


def get_user_root() -> str:
    """Get the user data root path"""
    if _android_usb_path:
        return os.path.join(_android_usb_path, "user")
    return "user"


def get_videos_root() -> str:
    """Get the videos root path"""
    if _android_usb_path:
        return os.path.join(_android_usb_path, "videos")
    return "videos"


def get_output_root() -> str:
    """Get the output/HLS root path"""
    if _android_usb_path:
        return os.path.join(_android_usb_path, "output")
    return "output"


# ========================================
# Core API Bridge Functions
# ========================================

def start_engine() -> Dict[str, Any]:
    """
    Start the AkiraTV engine.
    
    Returns:
        {"success": bool, "message": str} or {"success": False, "error": str}
    """
    try:
        from .core_api import get_api
        api = get_api()
        return api.start()
    except Exception as e:
        logger.error(f"Error starting engine: {e}")
        return {"success": False, "error": str(e)}


def stop_engine() -> Dict[str, Any]:
    """
    Stop the AkiraTV engine.
    
    Returns:
        {"success": bool, "message": str} or {"success": False, "error": str}
    """
    try:
        from .core_api import get_api
        api = get_api()
        return api.stop()
    except Exception as e:
        logger.error(f"Error stopping engine: {e}")
        return {"success": False, "error": str(e)}


def get_engine_status() -> Dict[str, Any]:
    """
    Get the current engine status.
    
    Returns:
        {"running": bool, "uptime": float}
    """
    try:
        from .core_api import get_api
        api = get_api()
        return {
            "running": api.is_running,
            "uptime": api.uptime
        }
    except Exception as e:
        logger.error(f"Error getting engine status: {e}")
        return {"running": False, "uptime": 0.0}


def get_channels() -> List[str]:
    """
    Get list of available channel names.
    
    Returns:
        List of channel names
    """
    try:
        from .core_api import get_api
        api = get_api()
        channels = api.get_channels()
        return [ch.name for ch in channels]
    except Exception as e:
        logger.error(f"Error getting channels: {e}")
        return []


def get_all_channels() -> List[Dict[str, Any]]:
    """
    Get detailed information about all channels.
    
    Returns:
        List of channel status dictionaries
    """
    try:
        from .core_api import get_api
        api = get_api()
        channels = api.get_channels()
        return [ch.to_dict() for ch in channels]
    except Exception as e:
        logger.error(f"Error getting all channels: {e}")
        return []


def get_channel_info(channel_name: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific channel.
    
    Args:
        channel_name: Name of the channel
    
    Returns:
        Channel status dictionary or None if not found
    """
    try:
        from .core_api import get_api
        api = get_api()
        channel = api.get_channel(channel_name)
        if channel:
            return channel.to_dict()
        return None
    except Exception as e:
        logger.error(f"Error getting channel info for '{channel_name}': {e}")
        return None


def enable_channel(channel_name: str) -> Dict[str, Any]:
    """
    Enable a channel.
    
    Args:
        channel_name: Name of the channel
    
    Returns:
        {"success": bool, "message": str} or {"success": False, "error": str}
    """
    try:
        from .core_api import get_api
        api = get_api()
        return api.enable_channel(channel_name)
    except Exception as e:
        logger.error(f"Error enabling channel '{channel_name}': {e}")
        return {"success": False, "error": str(e)}


def disable_channel(channel_name: str) -> Dict[str, Any]:
    """
    Disable a channel.
    
    Args:
        channel_name: Name of the channel
    
    Returns:
        {"success": bool, "message": str} or {"success": False, "error": str}
    """
    try:
        from .core_api import get_api
        api = get_api()
        return api.disable_channel(channel_name)
    except Exception as e:
        logger.error(f"Error disabling channel '{channel_name}': {e}")
        return {"success": False, "error": str(e)}


def add_channel(channel_name: str, channel_type: str = "linear") -> Dict[str, Any]:
    """
    Add a new channel.
    
    Args:
        channel_name: Name of the new channel
        channel_type: Type of channel ("linear", "vod", or "dynamic")
    
    Returns:
        {"success": bool, "message": str} or {"success": False, "error": str}
    """
    try:
        from .core_api import get_api
        api = get_api()
        return api.add_channel(channel_name, channel_type)
    except Exception as e:
        logger.error(f"Error adding channel '{channel_name}': {e}")
        return {"success": False, "error": str(e)}


def get_channel_url(channel_name: str) -> Optional[Dict[str, str]]:
    """
    Get streaming URLs for a channel.
    
    Args:
        channel_name: Name of the channel
    
    Returns:
        {"stream": str, "epg": str, "dashboard": str} or None
    """
    try:
        from .core_api import get_api
        api = get_api()
        return api.get_channel_url(channel_name)
    except Exception as e:
        logger.error(f"Error getting channel URL for '{channel_name}': {e}")
        return None


def play_now(channel_name: str, video_path: str, start_position: float = 0) -> Dict[str, Any]:
    """
    Play a video immediately on a VOD or Dynamic channel.
    
    Args:
        channel_name: Name of the channel
        video_path: Full path to the video file
        start_position: Start position in seconds (default 0)
    
    Returns:
        {"success": bool, "message": str} or {"success": False, "error": str}
    """
    try:
        from .core_api import get_api
        api = get_api()
        return api.play_now(channel_name, video_path, start_position)
    except Exception as e:
        logger.error(f"Error playing on channel '{channel_name}': {e}")
        return {"success": False, "error": str(e)}


# ========================================
# Configuration Bridge Functions
# ========================================

def get_config() -> Dict[str, Any]:
    """
    Get the current configuration.
    
    Returns:
        Configuration dictionary
    """
    try:
        from .config import Config
        config = Config.load_or_create()
        return config.data
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return {}


def save_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save configuration changes.
    
    Args:
        config_data: New configuration dictionary
    
    Returns:
        {"success": bool, "message": str} or {"success": False, "error": str}
    """
    try:
        from .config import Config
        config = Config(config_data)
        
        # Determine config path based on Android paths
        config_path = os.path.join(get_user_root(), "config.json") if is_android() else "config.json"
        config.save(config_path)
        
        return {"success": True, "message": "Config saved successfully"}
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return {"success": False, "error": str(e)}


def get_storage_info() -> Dict[str, Any]:
    """
    Get storage information (USB paths, disk space, etc.)
    
    Returns:
        Storage information dictionary
    """
    result = {
        "is_android": is_android(),
        "usb_path": _android_usb_path,
        "storage_path": _android_storage_path,
        "user_root": get_user_root(),
        "videos_root": get_videos_root(),
        "output_root": get_output_root()
    }
    
    # Add disk space info if paths exist
    for path_key in ["usb_path", "user_root", "videos_root", "output_root"]:
        path = result.get(path_key)
        if path and os.path.exists(path):
            try:
                stat = os.statvfs(path) if hasattr(os, 'statvfs') else None
                if stat:
                    result[f"{path_key}_free"] = stat.f_bavail * stat.f_frsize
                    result[f"{path_key}_total"] = stat.f_blocks * stat.f_frsize
            except Exception:
                pass
    
    return result


# ========================================
# Library/Inventory Bridge Functions
# ========================================

def get_library_stats() -> Dict[str, Any]:
    """
    Get library statistics.
    
    Returns:
        Library statistics dictionary
    """
    try:
        from .inventory import InventoryManager
        from pathlib import Path
        
        inventory_path = Path(get_user_root()) / "library.json"
        if not inventory_path.exists():
            return {
                "total_videos": 0,
                "total_duration": 0,
                "total_size": 0,
                "resolutions": [],
                "codecs": {}
            }
        
        manager = InventoryManager(inventory_path)
        
        # Calculate stats from inventory
        total_videos = len(manager.inventory_data)
        total_duration = 0
        total_size = 0
        resolutions = set()
        codecs = {}
        
        for item in manager.inventory_data:
            total_duration += item.get("duration", 0)
            total_size += item.get("size", 0)
            
            # Collect resolutions
            for track in item.get("video_tracks", []):
                res = track.get("resolution", "")
                if res:
                    resolutions.add(res)
            
            # Collect codecs
            for track in item.get("video_tracks", []):
                codec = track.get("codec", "").split('.')[0]  # e.g., "h264" from "h264_mp4"
                if codec:
                    codecs[codec] = codecs.get(codec, 0) + 1
        
        return {
            "total_videos": total_videos,
            "total_duration": total_duration,
            "total_size": total_size,
            "resolutions": sorted(list(resolutions)),
            "codecs": codecs
        }
    except Exception as e:
        logger.error(f"Error getting library stats: {e}")
        return {
            "total_videos": 0,
            "total_duration": 0,
            "total_size": 0,
            "resolutions": [],
            "codecs": {}
        }


def scan_library() -> Dict[str, Any]:
    """
    Trigger a library scan (for Android, this would need to be handled differently).
    On Android, the scan should be triggered from Kotlin using WorkManager.
    
    Returns:
        {"success": bool, "message": str}
    """
    # On Android, library scanning should be handled by Kotlin
    # This is a placeholder that returns info about how to trigger scan
    return {
        "success": False,
        "message": "Library scan should be triggered from Android app",
        "note": "Use WorkManager in Kotlin for background scanning"
    }


# ========================================
# Stats/Monitoring Bridge Functions
# ========================================

def get_stats() -> Dict[str, Any]:
    """
    Get current system statistics.
    
    Returns:
        Statistics dictionary
    """
    try:
        from .stats import AKIRATV_STATS, STATS_LOCK, get_active_viewers
        
        with STATS_LOCK:
            stats = dict(AKIRATV_STATS)
        
        stats["active_viewers"] = get_active_viewers()
        
        # Add engine status
        from .core_api import get_api
        api = get_api()
        stats["engine_running"] = api.is_running
        stats["engine_uptime"] = api.uptime
        
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {}


# ========================================
# Test/Health Check Functions
# ========================================

def test_imports() -> Dict[str, bool]:
    """
    Test that all required Python modules can be imported.
    Used for debugging ChaQuPy setup.
    
    Returns:
        Dictionary of module name -> import success
    """
    results = {}
    
    modules_to_test = [
        "akiratv.core_api",
        "akiratv.config",
        "akiratv.inventory",
        "akiratv.core",
        "akiratv.stats"
    ]
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            results[module_name] = True
        except Exception as e:
            results[module_name] = False
            logger.error(f"Failed to import {module_name}: {e}")
    
    return results


def health_check() -> Dict[str, Any]:
    """
    Perform a health check of the AkiraTV system.
    
    Returns:
        Health status dictionary
    """
    try:
        # Test imports
        import_results = test_imports()
        all_imports_ok = all(import_results.values())
        
        # Check if config loads
        config_ok = False
        try:
            from .config import Config
            config = Config.load_or_create()
            config_ok = config is not None
        except Exception:
            pass
        
        # Check engine status
        from .core_api import get_api
        api = get_api()
        
        return {
            "healthy": all_imports_ok and config_ok,
            "imports": import_results,
            "config_loadable": config_ok,
            "engine_running": api.is_running,
            "is_android": is_android(),
            "android_paths": get_android_paths()
        }
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e)
        }
