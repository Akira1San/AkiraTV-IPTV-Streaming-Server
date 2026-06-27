"""
Core API for AkiraTV - UI-agnostic control layer
Provides thread-safe interface for all AkiraTV operations
"""
import threading
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

from .core import AkiraTV
from .collections import FFMPEG_PATH, FFPROBE_PATH
from .stats import AKIRATV_STATS, STATS_LOCK, get_active_viewers

logger = logging.getLogger("AkiraTV")

@dataclass
class ChannelStatus:
    """Status information for a channel"""
    name: str
    type: str  # "linear" | "vod" | "dynamic" | "live"
    enabled: bool
    status: str  # "running" | "stopped" | "error"
    now_playing: str = ""
    next_program: str = ""
    viewers: int = 0
    uptime: float = 0.0  # seconds
    current_video: Optional[str] = None
    port: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class LibraryStats:
    """Library statistics"""
    total_videos: int
    total_duration: float  # seconds
    total_size: int  # bytes
    resolutions: List[str]
    codecs: Dict[str, int]  # codec -> count
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class CoreAPI:
    """
    Thread-safe public interface for AkiraTV
    
    Usage:
        api = CoreAPI()
        api.start()
        channels = api.get_channels()
        api.play_now("MovieChannel", "/path/to/video.mp4")
        api.stop()
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._engine: Optional[AkiraTV] = None
            self._engine_thread: Optional[threading.Thread] = None
            self._running = False
            self._start_time: Optional[float] = None
            self._api_lock = threading.RLock()  # Reentrant lock
            self._event_handlers: Dict[str, List[Callable]] = {}
            self._initialized = True
            logger.info("CoreAPI initialized")

    # ========================================
    # LIFECYCLE METHODS
    # ========================================
    
    def start(self) -> Dict[str, Any]:
        """
        Start AkiraTV engine
        
        Returns:
            {"success": bool, "message": str} or {"success": False, "error": str}
        """
        with self._api_lock:
            if self._running:
                return {"success": True, "message": "Already running"}
            
            try:
                logger.info("CoreAPI: Starting engine...")
                self._engine = AkiraTV()
                self._engine_thread = threading.Thread(
                    target=self._engine.start,
                    daemon=True,
                    name="AkiraTV-Engine"
                )
                self._engine_thread.start()
                self._running = True
                self._start_time = time.time()
                self._emit("engine_started", {"timestamp": datetime.now().isoformat()})
                logger.info("CoreAPI: Engine started successfully")
                return {"success": True, "message": "Started successfully"}
            except Exception as e:
                error_msg = f"Failed to start: {str(e)}"
                logger.error(f"CoreAPI: {error_msg}", exc_info=True)
                self._emit("engine_error", {"error": error_msg})
                return {"success": False, "error": error_msg}

    def stop(self) -> Dict[str, Any]:
        """
        Stop AkiraTV engine
        
        Returns:
            {"success": bool, "message": str} or {"success": False, "error": str}
        """
        with self._api_lock:
            if not self._running or not self._engine:
                return {"success": True, "message": "Already stopped"}
            
            try:
                logger.info("CoreAPI: Stopping engine...")
                self._engine.stop()
                if self._engine_thread:
                    self._engine_thread.join(timeout=10)
                self._running = False
                self._engine = None
                self._start_time = None
                self._emit("engine_stopped", {"timestamp": datetime.now().isoformat()})
                logger.info("CoreAPI: Engine stopped successfully")
                return {"success": True, "message": "Stopped successfully"}
            except Exception as e:
                error_msg = f"Failed to stop: {str(e)}"
                logger.error(f"CoreAPI: {error_msg}", exc_info=True)
                return {"success": False, "error": error_msg}

    def restart(self) -> Dict[str, Any]:
        """
        Restart AkiraTV engine
        
        Returns:
            {"success": bool, "message": str} or {"success": False, "error": str}
        """
        logger.info("CoreAPI: Restarting engine...")
        stop_result = self.stop()
        if not stop_result["success"]:
            return stop_result
        
        # Brief pause to ensure clean shutdown
        time.sleep(2)
        
        return self.start()

    @property
    def is_running(self) -> bool:
        """Check if engine is currently running"""
        return self._running and self._engine is not None

    @property
    def uptime(self) -> float:
        """Get engine uptime in seconds"""
        if self._start_time:
            return time.time() - self._start_time
        return 0.0

    # ========================================
    # CHANNEL CONTROL
    # ========================================
    
    def get_channels(self) -> List[ChannelStatus]:
        """
        Get status of all channels (from config only)
        
        Returns:
            List of ChannelStatus objects
        """
        channels = []
        known_channels = set()
        
        # Get config
        if self._engine:
            config = self._engine.config.data
        else:
            from .config import Config
            config = Config.load_or_create().data
        
        # Add channels from config ONLY - don't add channels from schedule files
        for name, conf in config.get("channels", {}).items():
            known_channels.add(name)
            
            # Check if worker is running
            is_running = self._running and self._engine and name in self._engine.workers
            
            ch_type = conf.get("type", "linear")
            port = None
            if ch_type == "live":
                port = conf.get("port")
                if port is None and self._engine and hasattr(self._engine, 'workers') and name in self._engine.workers:
                    worker, _ = self._engine.workers[name]
                    if worker and hasattr(worker, 'port'):
                        port = worker.port

            status = ChannelStatus(
                name=name,
                type=ch_type,
                enabled=conf.get("enabled", True),
                status="running" if is_running else "stopped",
                viewers=0,
                uptime=self.uptime if is_running else 0.0,
                port=port
            )
            channels.append(status)
        
        # Update with live stats from first running channel
        if channels:
            with STATS_LOCK:
                now_playing = AKIRATV_STATS.get("now_playing", "")
                next_program = AKIRATV_STATS.get("next_program", "")
            
            for ch in channels:
                if ch.status == "running":
                    ch.now_playing = now_playing
                    ch.next_program = next_program
                    ch.viewers = get_active_viewers()
                    break
        
        return channels

    def get_channel(self, channel: str) -> Optional[ChannelStatus]:
        """
        Get status of a specific channel
        
        Args:
            channel: Channel name
            
        Returns:
            ChannelStatus or None if not found
        """
        channels = self.get_channels()
        for ch in channels:
            if ch.name == channel:
                # Add current video information for VOD/Dynamic channels
                if self._running and self._engine and channel in self._engine.workers:
                    worker, thread = self._engine.workers[channel]
                    if worker and hasattr(worker, 'video_to_play'):
                        ch.current_video = worker.video_to_play
                    elif hasattr(worker, 'current_video'):
                        ch.current_video = worker.current_video
                    else:
                        ch.current_video = None
                else:
                    ch.current_video = None
                return ch
        return None

    def enable_channel(self, channel: str) -> Dict[str, Any]:
        """
        Enable a channel (requires restart to take effect)
        
        Args:
            channel: Channel name
            
        Returns:
            {"success": bool, "message": str}
        """
        result = self._update_channel_config(channel, {"enabled": True})
        if result["success"]:
            self._emit("channel_enabled", {"channel": channel})
        return result

    def disable_channel(self, channel: str) -> Dict[str, Any]:
        """
        Disable a channel (requires restart to take effect)
        
        Args:
            channel: Channel name
            
        Returns:
            {"success": bool, "message": str}
        """
        result = self._update_channel_config(channel, {"enabled": False})
        if result["success"]:
            self._emit("channel_disabled", {"channel": channel})
        return result

    def add_channel(self, channel_name: str, channel_type: str = "linear") -> Dict[str, Any]:
        """
        Add a new channel to the configuration
        
        Args:
            channel_name: Name of the new channel
            channel_type: Type of channel ("linear", "vod", "dynamic", "live")
            
        Returns:
            {"success": bool, "message": str}
        """
        # Validate channel name
        if not channel_name or not channel_name.strip():
            return {"success": False, "error": "Channel name cannot be empty"}
        
        channel_name = channel_name.strip()
        
        # Check if channel already exists
        existing_channels = self.get_channels()
        if any(ch.name == channel_name for ch in existing_channels):
            return {"success": False, "error": f"Channel '{channel_name}' already exists"}
        
        # Validate channel name format
        if not channel_name.replace("_", "").replace("-", "").isalnum():
            return {"success": False, "error": "Use only letters, numbers, '-', or '_'"}
        
        # Validate channel type
        if channel_type not in ["linear", "vod", "dynamic", "live"]:
            return {"success": False, "error": "Channel type must be 'linear', 'vod', 'dynamic', or 'live'"}
        
        try:
            # Add channel to config
            config = self._get_config_object()
            
            if "channels" not in config.data:
                config.data["channels"] = {}
            
            config.data["channels"][channel_name] = {
                "enabled": True,
                "type": channel_type,
                "transcoding": {
                    "enabled": False
                }
            }
            
            config.save()
            
            self._emit("channel_added", {"channel": channel_name, "type": channel_type})
            logger.info(f"CoreAPI: Added channel '{channel_name}' with type '{channel_type}'")
            
            return {"success": True, "message": f"Channel '{channel_name}' added successfully"}
        except Exception as e:
            error_msg = f"Failed to add channel: {str(e)}"
            logger.error(f"CoreAPI: {error_msg}")
            return {"success": False, "error": error_msg}

    def get_channel_url(self, channel: str) -> Dict[str, str]:
        """
        Get streaming URLs for a channel
        
        Args:
            channel: Channel name
            
        Returns:
            {"stream": str, "epg": str, "dashboard": str} or {"error": str}
        """
        if not self._engine:
            config_obj = self._get_config_object()
            config = config_obj.data
        else:
            config = self._engine.config.data
        
        http_conf = config.get("output", {}).get("http", {})
        port = http_conf.get("port", 8080)
        bind = http_conf.get("bind", "127.0.0.1")
        
        # Determine IP address
        if bind == "0.0.0.0":
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
            except:
                ip = "127.0.0.1"
        else:
            ip = bind
        
        return {
            "stream": f"http://{ip}:{port}/hls/{channel}/index.m3u8",
            "epg": f"http://{ip}:{port}/xmltv.xml",
            "dashboard": f"http://{ip}:{port}/dashboard"
        }

    def play_now(self, channel: str, video_path: str, start_position: float = 0) -> Dict[str, Any]:
        """
        Play video on VOD or Dynamic channel immediately
        
        Args:
            channel: Channel name
            video_path: Full path to video file
            start_position: Start position in seconds (default 0)
            
        Returns:
            {"success": bool, "message": str} or {"success": False, "error": str}
        """
        if not self._running:
            return {"success": False, "error": "Engine not running"}
        
        if not self._engine:
            return {"success": False, "error": "Engine not initialized"}
        
        video_file = Path(video_path)
        if not video_file.exists():
            return {"success": False, "error": f"Video file not found: {video_path}"}
        
        # Check if channel exists and is VOD/Dynamic
        channel_status = self.get_channel(channel)
        if not channel_status:
            return {"success": False, "error": f"Channel '{channel}' not found"}
        
        if channel_status.type not in ["vod", "dynamic"]:
            return {"success": False, "error": f"Channel '{channel}' is not VOD or Dynamic type"}
        
        try:
            self._engine.enqueue_play_now(channel, video_path, start_position)
            self._emit("video_queued", {"channel": channel, "video": video_file.name, "start_position": start_position})
            logger.info(f"CoreAPI: Queued {video_file.name} on {channel} (start: {start_position}s)")
            return {"success": True, "message": f"Queued {video_file.name}"}
        except Exception as e:
            error_msg = f"Failed to queue video: {str(e)}"
            logger.error(f"CoreAPI: {error_msg}")
            return {"success": False, "error": error_msg}

    def stop_channel(self, channel: str) -> Dict[str, Any]:
        """
        Stop playback on a specific VOD or Dynamic channel
        
        Args:
            channel: Channel name
            
        Returns:
            {"success": bool, "message": str} or {"success": False, "error": str}
        """
        if not self._running:
            return {"success": False, "error": "Engine not running"}
        
        if not self._engine:
            return {"success": False, "error": "Engine not initialized"}
        
        # Check if channel exists and is VOD/Dynamic
        channel_status = self.get_channel(channel)
        if not channel_status:
            return {"success": False, "error": f"Channel '{channel}' not found"}
        
        if channel_status.type not in ["vod", "dynamic"]:
            return {"success": False, "error": f"Channel '{channel}' is not VOD or Dynamic type"}
        
        try:
            # Check if worker exists and is running
            if hasattr(self._engine, 'workers') and channel in self._engine.workers:
                worker, thread = self._engine.workers[channel]
                if worker and hasattr(worker, 'ffmpeg_process'):
                    # Stop the current FFmpeg process (this will stop current video)
                    if worker.ffmpeg_process and worker.ffmpeg_process.poll() is None:
                        worker.ffmpeg_process.terminate()
                        try:
                            worker.ffmpeg_process.wait(timeout=3)
                        except:
                            worker.ffmpeg_process.kill()
                        self._emit("video_stopped", {"channel": channel})
                        logger.info(f"CoreAPI: Stopped current video on {channel}")
                        return {"success": True, "message": f"Stopped current video on {channel}"}
                    else:
                        return {"success": True, "message": f"No video currently playing on {channel}"}
                else:
                    return {"success": False, "error": f"Channel '{channel}' worker not available"}
            else:
                return {"success": False, "error": f"Channel '{channel}' is not running"}
        except Exception as e:
            error_msg = f"Failed to stop channel: {str(e)}"
            logger.error(f"CoreAPI: {error_msg}")
            return {"success": False, "error": error_msg}

    def stop_channel_worker(self, channel: str) -> Dict[str, Any]:
        """
        Stop a running channel worker completely
        
        Args:
            channel: Channel name
            
        Returns:
            {"success": bool, "message": str} or {"success": False, "error": str}
        """
        if not self._running:
            return {"success": False, "error": "Engine not running"}
        
        if not self._engine:
            return {"success": False, "error": "Engine not initialized"}
        
        # Check if channel exists
        channel_status = self.get_channel(channel)
        if not channel_status:
            return {"success": False, "error": f"Channel '{channel}' not found"}
        
        try:
            # For linear and live channels, mark as stopped to prevent auto-restart
            if channel_status.type in ("linear", "live"):
                logger.info(f"CoreAPI: Marking {channel_status.type} channel '{channel}' as stopped")
                self._engine.stopped_linear_channels.add(channel)
            
            # Check if worker exists and is running
            if hasattr(self._engine, 'workers') and channel in self._engine.workers:
                worker, thread = self._engine.workers[channel]
                if worker:
                    logger.info(f"CoreAPI: Stopping worker for channel '{channel}'")
                    worker.stop()  # Stop the worker
                    thread.join(timeout=5)  # Wait for thread to finish
                    
                    # Remove from workers dict
                    del self._engine.workers[channel]
                    
                    self._emit("channel_stopped", {"channel": channel})
                    logger.info(f"CoreAPI: Channel '{channel}' worker stopped")
                    return {"success": True, "message": f"Channel '{channel}' stopped"}
                else:
                    # For linear channels with None worker (auto-restart wrapper), 
                    # we already marked it as stopped, so just remove from workers dict
                    if channel_status.type == "linear":
                        del self._engine.workers[channel]
                        self._emit("channel_stopped", {"channel": channel})
                        logger.info(f"CoreAPI: Linear channel '{channel}' stopped")
                        return {"success": True, "message": f"Channel '{channel}' stopped"}
                    return {"success": False, "error": f"Channel '{channel}' worker not available"}
            else:
                return {"success": True, "message": f"Channel '{channel}' is not running"}
        except Exception as e:
            error_msg = f"Failed to stop channel worker: {str(e)}"
            logger.error(f"CoreAPI: {error_msg}")
            return {"success": False, "error": error_msg}

    def restart_channel(self, channel: str) -> Dict[str, Any]:
        """
        Restart a specific channel worker
        
        Args:
            channel: Channel name
            
        Returns:
            {"success": bool, "message": str} or {"success": False, "error": str}
        """
        if not self._running:
            return {"success": False, "error": "Engine not running"}
        
        if not self._engine:
            return {"success": False, "error": "Engine not initialized"}
        
        # Check if channel exists and is enabled
        channel_status = self.get_channel(channel)
        if not channel_status:
            return {"success": False, "error": f"Channel '{channel}' not found"}
        
        if not channel_status.enabled:
            return {"success": False, "error": f"Channel '{channel}' is disabled"}
        
        try:
            # First stop the channel if it's running
            if hasattr(self._engine, 'workers') and channel in self._engine.workers:
                stop_result = self.stop_channel_worker(channel)
                if not stop_result["success"]:
                    logger.warning(f"CoreAPI: Failed to stop channel '{channel}' before restart: {stop_result.get('error')}")
                else:
                    logger.info(f"CoreAPI: Stopped channel '{channel}' for restart")
            
            # Brief pause to ensure clean shutdown
            import time
            time.sleep(1)
            
            # Restart the channel by calling the appropriate engine method based on channel type
            channel_type = channel_status.type
            
            if channel_type == "linear":
                if channel in self._engine.stopped_linear_channels:
                    self._engine.stopped_linear_channels.remove(channel)
                start_method = "_start_linear_channel"
            elif channel_type == "live":
                if channel in self._engine.stopped_linear_channels:
                    self._engine.stopped_linear_channels.remove(channel)
                start_method = "_start_live_channel"
            elif channel_type == "dynamic":
                start_method = "_start_dynamic_channel"
            elif channel_type == "vod":
                start_method = "_start_vod_channel"
            else:
                return {"success": False, "error": f"Unknown channel type: {channel_type}"}
            
            if hasattr(self._engine, start_method):
                getattr(self._engine, start_method)(channel)
                # Give the worker time to start
                time.sleep(0.5)
                
                # Verify the worker started successfully
                if hasattr(self._engine, 'workers') and channel in self._engine.workers:
                    self._emit("channel_restarted", {"channel": channel})
                    logger.info(f"CoreAPI: Channel '{channel}' restarted successfully")
                    return {"success": True, "message": f"Channel '{channel}' restarted successfully"}
                else:
                    return {"success": False, "error": f"Failed to restart channel '{channel}' - worker not found after start"}
            else:
                return {"success": False, "error": f"Channel restart not supported for channel type: {channel_type}"}
                
        except Exception as e:
            error_msg = f"Failed to restart channel: {str(e)}"
            logger.error(f"CoreAPI: {error_msg}")
            return {"success": False, "error": error_msg}

    def start_channel(self, channel: str) -> Dict[str, Any]:
        """
        Start a specific channel worker (for stopped/enabled channels)
        
        Args:
            channel: Channel name
            
        Returns:
            {"success": bool, "message": str} or {"success": False, "error": str}
        """
        if not self._running:
            return {"success": False, "error": "Engine not running"}
        
        if not self._engine:
            return {"success": False, "error": "Engine not initialized"}
        
        # Check if channel exists and is enabled
        channel_status = self.get_channel(channel)
        if not channel_status:
            return {"success": False, "error": f"Channel '{channel}' not found"}
        
        if not channel_status.enabled:
            return {"success": False, "error": f"Channel '{channel}' is disabled. Enable it first."}
        
        # Check if channel is already running
        if hasattr(self._engine, 'workers') and channel in self._engine.workers:
            return {"success": False, "error": f"Channel '{channel}' is already running"}
        
        try:
            # Get channel type from config
            config = self.get_config()
            channels_config = config.get("channels", {})
            channel_type = channels_config.get(channel, {}).get("type", "linear")
            
            if channel_type == "linear":
                if channel in self._engine.stopped_linear_channels:
                    self._engine.stopped_linear_channels.remove(channel)
                self._engine._start_linear_channel(channel)
            elif channel_type == "live":
                if channel in self._engine.stopped_linear_channels:
                    self._engine.stopped_linear_channels.remove(channel)
                self._engine._start_live_channel(channel)
            elif channel_type == "vod":
                self._engine._start_vod_channel(channel)
            elif channel_type == "dynamic":
                self._engine._start_dynamic_channel(channel)
            else:
                return {"success": False, "error": f"Unknown channel type '{channel_type}'"}
            
            self._emit("channel_started", {"channel": channel})
            logger.info(f"CoreAPI: Channel '{channel}' started successfully")
            return {"success": True, "message": f"Channel '{channel}' started successfully"}
            
        except Exception as e:
            error_msg = f"Failed to start channel: {str(e)}"
            logger.error(f"CoreAPI: {error_msg}")
            return {"success": False, "error": error_msg}

    # ========================================
    # SCHEDULING
    # ========================================
    
    def reload_schedule(self, channel: Optional[str] = None) -> Dict[str, Any]:
        """
        Reload schedule for all channels or specific channel
        
        Args:
            channel: Optional channel name to reload (None = all channels)
            
        Returns:
            {"success": bool, "message": str}
        """
        if not self._running or not self._engine:
            return {"success": False, "error": "Engine not running"}
        
        try:
            if hasattr(self._engine, 'reload_schedule'):
                self._engine.reload_schedule()
                self._emit("schedule_reloaded", {"channel": channel})
                return {"success": True, "message": "Schedule reloaded"}
            else:
                # Fallback: restart engine
                logger.warning("CoreAPI: reload_schedule not implemented, restarting engine")
                return self.restart()
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ========================================
    # CONFIGURATION
    # ========================================
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration

        Returns:
            Complete config dictionary with effective FFmpeg paths injected
        """
        if self._engine:
            result = self._engine.config.data.copy()
        else:
            config = self._get_config_object()
            result = config.data.copy()
        result["_ffmpeg_bin_dir"] = str(Path(FFMPEG_PATH).parent)
        return result

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update configuration (deep merge)
        
        Args:
            updates: Dictionary of config updates
            
        Returns:
            {"success": bool, "message": str}
        """
        try:
            config = self._get_config_object()
            
            # Deep merge updates
            self._deep_update(config.data, updates)
            config.save()
            
            # If engine is running, reload config
            if self._engine:
                self._engine.config = config
            
            self._emit("config_updated", {"updates": updates})
            logger.info("CoreAPI: Config updated successfully")
            return {"success": True, "message": "Config updated"}
        except Exception as e:
            error_msg = f"Failed to update config: {str(e)}"
            logger.error(f"CoreAPI: {error_msg}")
            return {"success": False, "error": error_msg}

    def save_config(self) -> Dict[str, Any]:
        """
        Save current config to disk
        
        Returns:
            {"success": bool, "message": str}
        """
        if self._engine:
            try:
                self._engine.config.save()
                return {"success": True, "message": "Config saved"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            return {"success": False, "error": "No active config"}

    # ========================================
    # LIBRARY / INVENTORY
    # ========================================
    
    def get_library_stats(self) -> Optional[LibraryStats]:
        """
        Get library statistics
        
        Returns:
            LibraryStats object or None if engine not running
        """
        if not self._engine:
            return None
        
        inventory = self._engine.inventory_manager.inventory_data
        
        if not inventory:
            return LibraryStats(
                total_videos=0,
                total_duration=0.0,
                total_size=0,
                resolutions=[],
                codecs={}
            )
        
        # Calculate stats
        total_duration = sum(v.get("duration_seconds", 0) for v in inventory)
        resolutions = set()
        codecs = {}
        
        for item in inventory:
            # Resolutions
            tracks = item.get("video_tracks", [])
            if tracks:
                w = tracks[0].get("width")
                h = tracks[0].get("height")
                if w and h:
                    resolutions.add(f"{w}x{h}")
                
                # Codecs
                codec = tracks[0].get("codec", "unknown")
                codecs[codec] = codecs.get(codec, 0) + 1
        
        return LibraryStats(
            total_videos=len(inventory),
            total_duration=total_duration,
            total_size=0,  # TODO: Calculate from file sizes
            resolutions=sorted(resolutions),
            codecs=codecs
        )

    def scan_library(self, path: Optional[str] = None) -> Dict[str, Any]:
        """
        Trigger library scan (placeholder for future implementation)
        
        Args:
            path: Optional path to scan
            
        Returns:
            {"success": bool, "message": str}
        """
        # TODO: Implement async library scanning
        return {"success": False, "error": "Not implemented yet"}

    # ========================================
    # MONITORING & STATS
    # ========================================
    
    @property
    def stats(self) -> Dict[str, Any]:
        """
        Get live statistics
        
        Returns:
            Dictionary of current stats
        """
        with STATS_LOCK:
            base_stats = AKIRATV_STATS.copy()
        
        # Add additional info
        base_stats["uptime"] = self.uptime
        base_stats["is_running"] = self.is_running
        base_stats["viewers"] = get_active_viewers()
        
        return base_stats

    def get_viewers(self) -> int:
        """
        Get active viewer count
        
        Returns:
            Number of active viewers
        """
        return get_active_viewers()

    # ========================================
    # EVENT SYSTEM
    # ========================================
    
    def on(self, event: str, handler: Callable[[Dict[str, Any]], None]):
        """
        Register event handler
        
        Args:
            event: Event name (e.g., "engine_started", "channel_enabled")
            handler: Callback function that receives event data
            
        Example:
            api.on("engine_started", lambda data: print(f"Started at {data['timestamp']}"))
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
        logger.debug(f"CoreAPI: Registered handler for event '{event}'")

    def off(self, event: str, handler: Optional[Callable] = None):
        """
        Unregister event handler(s)
        
        Args:
            event: Event name
            handler: Specific handler to remove, or None to remove all handlers for event
        """
        if event not in self._event_handlers:
            return
        
        if handler is None:
            # Remove all handlers for this event
            del self._event_handlers[event]
        else:
            # Remove specific handler
            self._event_handlers[event] = [h for h in self._event_handlers[event] if h != handler]

    def _emit(self, event: str, data: Dict[str, Any]):
        """
        Emit event to all registered handlers
        
        Args:
            event: Event name
            data: Event data
        """
        for handler in self._event_handlers.get(event, []):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"CoreAPI: Event handler error for '{event}': {e}", exc_info=True)

    # ========================================
    # UTILITY / MAINTENANCE
    # ========================================
    
    def clear_cache(self) -> Dict[str, Any]:
        """
        Clear HLS cache
        
        Returns:
            {"success": bool, "deleted": int, "message": str}
        """
        try:
            config = self.get_config()
            storage = config.get("storage", {})
            
            if storage.get("type") == "ram":
                output_root = Path(storage.get("ram_path", "./output"))
            else:
                output_root = Path(storage.get("disk_path", "./output"))
            
            if not output_root.exists():
                return {"success": True, "deleted": 0, "message": "No cache found"}
            
            deleted = 0
            for item in output_root.rglob("*"):
                if item.suffix in (".ts", ".m3u8", ".m4s", ".mp4"):
                    try:
                        item.unlink()
                        deleted += 1
                    except:
                        pass
            
            logger.info(f"CoreAPI: Cleared {deleted} cache files")
            return {"success": True, "deleted": deleted, "message": f"Deleted {deleted} files"}
        except Exception as e:
            return {"success": False, "error": str(e), "deleted": 0}

    def get_logs(self, limit: int = 100) -> List[str]:
        """
        Get recent log entries
        
        Args:
            limit: Maximum number of lines to return
            
        Returns:
            List of log lines
        """
        try:
            log_file = Path("logs/worker.log")
            if not log_file.exists():
                return []
            
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            return lines[-limit:]
        except Exception as e:
            logger.error(f"CoreAPI: Failed to read logs: {e}")
            return []

    # ========================================
    # INTERNAL HELPERS
    # ========================================
    
    def _get_config_object(self):
        """Get Config object (cached if engine running)"""
        if self._engine:
            return self._engine.config
        else:
            from .config import Config
            return Config.load_or_create()

    def delete_channel(self, channel: str) -> Dict[str, Any]:
        """Delete a channel from the configuration"""
        try:
            config = self._get_config_object()
            
            if "channels" not in config.data or channel not in config.data["channels"]:
                return {"success": False, "error": f"Channel '{channel}' not found"}
            
            # Stop channel if it's running
            if self._running and hasattr(self._engine, 'workers') and channel in self._engine.workers:
                stop_result = self.stop_channel_worker(channel)
                if not stop_result["success"]:
                    logger.warning(f"CoreAPI: Failed to stop channel '{channel}' before deletion: {stop_result.get('error')}")
            
            # Remove from config
            del config.data["channels"][channel]
            config.save()
            
            self._emit("channel_deleted", {"channel": channel})
            logger.info(f"CoreAPI: Deleted channel '{channel}'")
            
            return {"success": True, "message": f"Channel '{channel}' deleted successfully"}
        except Exception as e:
            error_msg = f"Failed to delete channel: {str(e)}"
            logger.error(f"CoreAPI: {error_msg}")
            return {"success": False, "error": error_msg}

    def _update_channel_config(self, channel: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update channel-specific configuration"""
        try:
            config = self._get_config_object()
            
            if "channels" not in config.data:
                config.data["channels"] = {}
            
            if channel not in config.data["channels"]:
                config.data["channels"][channel] = {}
            
            config.data["channels"][channel].update(updates)
            config.save()
            
            return {"success": True, "message": f"Channel '{channel}' updated"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _deep_update(self, target: Dict, source: Dict):
        """Deep merge source dict into target dict"""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value


# ========================================
# CONVENIENCE SINGLETON ACCESSOR
# ========================================

_api_instance = None

def get_api() -> CoreAPI:
    """
    Get global CoreAPI instance
    
    Returns:
        CoreAPI singleton instance
    """
    global _api_instance
    if _api_instance is None:
        _api_instance = CoreAPI()
    return _api_instance