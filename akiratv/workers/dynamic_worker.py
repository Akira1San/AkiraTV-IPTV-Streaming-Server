# akiratv/workers/dynamic_worker.py
"""
DynamicWorker: A hybrid worker that follows a schedule but allows interruptions.

Logging Prefix Convention:
----------------------------
This module uses optional prefixes to indicate message categories:
[HOT]      - VOD interruption / immediate playback
[TV]       - Scheduled broadcast content
[OK]       - Successful completion of an operation
[STANDBY]  - Standby mode related messages
[START]    - Starting video playback
[PLAY]     - VOD playback actions
[CONFIG]   - Configuration and transcoding settings
[MSG]      - Queue and message handling

Messages without prefixes are general informational or error logs.
"""

import threading
import time
import subprocess
import queue
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, date, timedelta
from .base_worker import BaseWorker
from akiratv.server.app_context import app_context
from akiratv.collections import FFMPEG_PATH, FFPROBE_PATH


class DynamicWorker(BaseWorker):
    """
    A hybrid worker that follows a schedule but allows interruptions.
    When no schedule is active, plays standby content.
    VOD interruptions temporarily override the schedule.
    """
    
    def __init__(self, channel, config, logger, transcoding_service,
                 inventory_manager, command_queue, schedule_entries=None):
        super().__init__(channel, config, logger)
        self.transcoding_service = transcoding_service
        self.inventory_manager = inventory_manager
        self.command_queue = command_queue
        self.schedule_entries = schedule_entries or []
        self.is_playing_vod = False
        self.current_video = None  # Track currently playing video
        self.current_schedule_index = 0
        self.target_resolution = self._get_channel_resolution()
        self.last_schedule_check = time.time()
        self.error_thread = None  # Track error logging thread for cleanup
        self.hls_dir = self.config.get_hls_output_path(self.channel)
        self.is_in_standby = False
        self._duration_cache: dict = {}  # Cache ffprobe results to avoid repeated calls
        
    def update_schedule(self, new_schedule_entries: List[Dict]):
        """Update schedule entries in-place without restarting the worker."""
        old_count = len(self.schedule_entries) if self.schedule_entries else 0
        self.schedule_entries = new_schedule_entries
        self.last_schedule_check = time.time()  # Reset to prevent immediate refresh
        self.logger.info(f"Schedule updated in-place: {old_count} -> {len(new_schedule_entries)} entries")

    def _get_channel_resolution(self) -> str:
        """Get the target resolution for this channel from config."""
        try:
            channel_config = self.config.data.get("channels", {}).get(self.channel, {})
            specs = channel_config.get("output_specs", {})
            width = specs.get("width", 1280)
            height = specs.get("height", 720)
            return f"{width}x{height}"
        except Exception as e:
            self.logger.warning(f"Could not determine channel resolution: {e}. Using 1280x720.")
            return "1280x720"

    def run(self):
        """Main execution loop for dynamic worker with schedule support."""
        self.logger.info(f"=== DynamicWorker started for channel: {self.channel} ===")
        
        if not self.initialize_worker():
            self.logger.error(f"Failed to initialize worker for {self.channel}")
            return
        
        while self.running:
            try:
                # Refresh schedule periodically (every 5 minutes)
                if time.time() - self.last_schedule_check > 300:
                    self._refresh_schedule()
                
                # Check for VOD interruption first
                try:
                    cmd, video_path, start_position = self.command_queue.get_nowait()
                    if cmd == "play_now":
                        self.logger.info(f"[HOT] VOD interruption: {video_path} (start: {start_position}s)")
                        self._switch_to_vod(video_path, start_position)
                        continue  # After VOD, check schedule again
                except queue.Empty:
                    pass
                
                # Check if we should play schedule or standby
                now = datetime.now()
                current_schedule = self._get_current_schedule_entry(now)
                
                if current_schedule:
                    # Play scheduled content (blocks until video finishes)
                    self._play_scheduled_content(current_schedule, now)
                    # After video finishes, loop back to check next schedule
                else:
                    # No active schedule, play standby
                    if not self.is_in_standby:
                        self._start_standby()
                    
                    # Monitor standby and check for commands
                    self._monitor_standby()
                
            except Exception as e:
                self.logger.error(f"Error in dynamic worker loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)
        
        self.logger.info(f"DynamicWorker stopped for channel: {self.channel}")

    def _monitor_standby(self):
        """Monitor standby while checking for commands and schedule changes."""
        # Wait for 5 seconds while checking for interruptions
        for _ in range(10):  # 10 x 0.5s = 5 seconds
            if not self.running:
                break
            
            # Check if FFmpeg died
            if self.ffmpeg_process and self.ffmpeg_process.poll() is not None:
                self.logger.warning("Standby process died, will restart...")
                self.is_in_standby = False
                break
            
            # Check for VOD command
            if not self.command_queue.empty():
                break
            
            # Check if schedule changed
            now = datetime.now()
            if self._get_current_schedule_entry(now):
                self.logger.info("Schedule entry found, exiting standby...")
                self._stop_current_ffmpeg()
                self.is_in_standby = False
                break
            
            time.sleep(0.5)

    def _refresh_schedule(self):
        """Refresh schedule from scheduler."""
        try:
            from akiratv.scheduler import get_current_schedule_for_channel
            new_schedule = get_current_schedule_for_channel(self.channel)
            if new_schedule:
                self.schedule_entries = new_schedule
                self.logger.info(f"📅 Schedule refreshed for {self.channel}: {len(new_schedule)} entries")
            self.last_schedule_check = time.time()
        except Exception as e:
            self.logger.error(f"Failed to refresh schedule: {e}")

    def _get_current_schedule_entry(self, current_time: datetime) -> Optional[Dict]:
        """Find which schedule entry should be playing now."""
        if not self.schedule_entries:
            return None
            
        for i, entry in enumerate(self.schedule_entries):
            try:
                scheduled_time = datetime.strptime(entry["time"], "%H:%M:%S").time()
                # Always treat as today first
                scheduled_dt = datetime.combine(date.today(), scheduled_time)

                # Only treat as yesterday if early morning AND entry is late night
                if current_time.hour < 6 and scheduled_time.hour >= 18:
                    scheduled_dt = datetime.combine(date.today() - timedelta(days=1), scheduled_time)

                duration = self._get_entry_duration(entry['file'])
                end_time = scheduled_dt + timedelta(seconds=duration)
                
                if scheduled_dt <= current_time < end_time:
                    self.current_schedule_index = i
                    return entry
            except Exception as e:
                self.logger.error(f"Error checking schedule entry: {e}")
                continue
        
        return None

    def _play_scheduled_content(self, entry: Dict, current_time: datetime):
        """Play scheduled content in NATIVE resolution (copy mode) like VOD."""
        video_path = entry['file']
        self.logger.info(f"[TV] Playing scheduled content: {Path(video_path).name}")
        
        # Calculate seek time
        seek_time = self._calculate_seek_time(entry, current_time)
        
        # Clean up old HLS segments before starting
        self._cleanup_hls_directory()
        
        hls_conf = self.config.data["output"]["hls"]
        playlist_filename = (self.hls_dir.resolve() / "index.m3u8").as_posix()
        
        # Determine if we need transcoding for Kodi compatibility or channel config
        channel_config = self.config.data.get("channels", {}).get(self.channel, {})
        kodi_compatible = channel_config.get("kodi_compatible", False)
        transcode_enabled = self.config.data.get("ffmpeg", {}).get("transcoding", {}).get("enabled", False)

        if transcode_enabled or kodi_compatible:
            encoding_args = self.transcoding_service.get_encoding_args(
                input_path=Path(video_path),
                channel=self.channel,
                force_transcode=kodi_compatible
            )
            self.logger.info(f"[START] Playing scheduled video with transcoding (Kodi compatible: {kodi_compatible})")
        else:
            encoding_args = ["-c:v", "copy", "-c:a", "copy"]
            self.logger.info(f"[START] Playing scheduled video in NATIVE resolution (copy mode)")
        
        args = [
            FFMPEG_PATH,
            "-v", "verbose",
            "-re",
        ]
        
        # Add seek if needed
        if seek_time > 0:
            args.extend(["-ss", str(seek_time)])
        
        args.extend([
            "-i", video_path,
            "-map", "0:v:0?",
            "-map", "0:a:0?",
            *encoding_args,
            "-f", "hls",
            "-hls_time", str(hls_conf["segment_time"]),
            "-hls_list_size", str(hls_conf["playlist_size"]),
            "-hls_flags", "delete_segments+append_list+omit_endlist",
            "-hls_segment_filename", str(Path(playlist_filename).parent / "seg_%04d.ts"),
            playlist_filename
        ])
        
        # Stop current FFmpeg if playing something else
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            self._stop_current_ffmpeg()
        
        # Start FFmpeg (blocking - wait for it to finish)
        # This makes it behave like VOD: start, play, stop
        self._execute_ffmpeg(args)
        
        # Update now playing (optional, for dashboard)
        try:
            app_context.set_now_playing(self.channel, f"Scheduled: {Path(video_path).stem}")
        except (AttributeError, Exception):
            pass
        
        self.logger.info(f"[OK] Scheduled video finished: {Path(video_path).name}")
        self.is_in_standby = False

    def _start_ffmpeg_nonblocking(self, args):
        """Start FFmpeg without blocking the main thread."""
        try:
            self.ffmpeg_process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=False
            )
            
            # Start watchdog
            from .base_worker import Watchdog
            self.watchdog = Watchdog(self.ffmpeg_process, self.logger, timeout_seconds=30)
            self.watchdog.start()
            
            # Start error logging thread with proper cleanup tracking
            def log_errors():
                try:
                    if self.ffmpeg_process and self.ffmpeg_process.stderr:
                        for line in iter(self.ffmpeg_process.stderr.readline, b''):
                            if not self.running:
                                break  # Exit early if worker stopped
                            if line and self.watchdog:
                                self.watchdog.ping()
                except ValueError:
                    # This can happen when stderr pipe is closed while reading (Windows-specific)
                    pass
                except Exception:
                    # Catch any other exceptions to prevent thread crash
                    pass
            
            self.error_thread = threading.Thread(target=log_errors, daemon=True)
            self.error_thread.start()
            
        except Exception as e:
            self.logger.error(f"Failed to start FFmpeg: {e}")

    def _calculate_seek_time(self, entry: Dict, current_time: datetime) -> float:
        """Calculate how many seconds into the scheduled video to start."""
        try:
            scheduled_time = datetime.strptime(entry["time"], "%H:%M:%S").time()
            scheduled_dt = datetime.combine(date.today(), scheduled_time)

            # Only treat as yesterday if early morning AND entry is late night
            if current_time.hour < 6 and scheduled_time.hour >= 18:
                scheduled_dt = datetime.combine(date.today() - timedelta(days=1), scheduled_time)

            if current_time < scheduled_dt:
                return 0
            
            offset_seconds = (current_time - scheduled_dt).total_seconds()
            video_duration = self._get_entry_duration(entry["file"])
            
            if offset_seconds >= video_duration:
                self.logger.warning(f"Schedule time has passed video duration")
                return 0
            
            return max(0, offset_seconds)
            
        except Exception as e:
            self.logger.error(f"Seek time calculation failed: {e}")
            return 0

    def _start_standby(self):
        """Starts a looped standby video."""
        self.logger.info(f"[STANDBY] Entering Standby Mode for {self.channel}...")
        
        standby_file = self._get_best_standby()
        if not standby_file.exists():
            self.logger.error(f"Standby file not found: {standby_file}")
            time.sleep(10)
            return
        
        # Clean up old HLS segments before starting
        self._cleanup_hls_directory()
        
        hls_conf = self.config.data["output"]["hls"]
        playlist_filename = (self.hls_dir.resolve() / "index.m3u8").as_posix()
        
        encoding_args = self.transcoding_service.get_encoding_args(
            input_path=standby_file,
            channel=self.channel
        )
        
        args = [
            FFMPEG_PATH,
            "-v", "verbose",
            "-re",
            "-stream_loop", "-1",  # Loop indefinitely
            "-i", str(standby_file),
            "-map", "0:v:0?",
            "-map", "0:a:0?",
            *encoding_args,
            "-f", "hls",
            "-hls_time", str(hls_conf["segment_time"]),
            "-hls_list_size", str(hls_conf["playlist_size"]),
            "-hls_flags", "delete_segments+append_list+omit_endlist",
            "-hls_segment_filename", str(Path(playlist_filename).parent / "seg_%04d.ts"),
            playlist_filename
        ]
        
        # Stop current FFmpeg if playing something else
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            self._stop_current_ffmpeg()
        
        # Start FFmpeg
        self._start_ffmpeg_nonblocking(args)
        #app_context.set_now_playing(self.channel, "Standby Loop")
        self.logger.info(f"[OK] Standby mode active for {self.channel}")
        self.is_in_standby = True

    def _switch_to_vod(self, video_path: str, start_position: float = 0):
        """Kill current content and play a VOD, then return to schedule/standby."""
        # 1. Stop current FFmpeg
        self._stop_current_ffmpeg()
        self.is_playing_vod = True
        self.is_in_standby = False
        self.current_video = video_path
        
        # 2. Get video metadata
        video_path = Path(video_path)
        if not video_path.exists():
            self.logger.error(f"VOD file not found: {video_path}")
            self.is_playing_vod = False
            return
        
        stats = self.inventory_manager.get_source_details(str(video_path))
        if stats:
            res = f"{stats.get('width', '?')}x{stats.get('height', '?')}"
            self.logger.info(f"[PLAY] Playing VOD: {video_path.name} ({res}) (start: {start_position}s)")
        
        #app_context.set_now_playing(self.channel, video_path.stem)
        
        # 3. Clean up old HLS segments before starting
        self._cleanup_hls_directory()
        
        # 4. Build VOD args
        hls_conf = self.config.data["output"]["hls"]
        playlist_filename = (self.hls_dir.resolve() / "index.m3u8").as_posix()
        
        channel_config = self.config.data.get("channels", {}).get(self.channel, {})
        kodi_compatible = channel_config.get("kodi_compatible", False)
        transcode_enabled = self.config.data.get("ffmpeg", {}).get("transcoding", {}).get("enabled", False)

        if transcode_enabled or kodi_compatible:
            encoding_args = self.transcoding_service.get_encoding_args(
                input_path=video_path,
                channel=self.channel,
                force_transcode=kodi_compatible
            )
            self.logger.info(f"[CONFIG] Transcoding VOD to match channel specs (Kodi: {kodi_compatible})")
        else:
            encoding_args = ["-c:v", "copy", "-c:a", "copy"]
            self.logger.info(f"[START] Playing VOD in native resolution (copy mode)")
        
        args = [
            FFMPEG_PATH,
            "-v", "verbose",
            "-re",
            "-i", str(video_path),
            "-map", "0:v:0?",
            "-map", "0:a:0?",
            *encoding_args,
            "-f", "hls",
            "-hls_time", str(hls_conf["segment_time"]),
            "-hls_list_size", str(hls_conf["playlist_size"]),
            "-hls_flags", "delete_segments+append_list+omit_endlist",
            "-hls_segment_filename", str(Path(playlist_filename).parent / "seg_%04d.ts"),
            playlist_filename
        ]
        
        # 4. Execute and wait for completion
        self._execute_ffmpeg(args)
        
        self.logger.info(f"[OK] VOD finished: {video_path.name}. Returning to schedule/standby.")
        self.is_playing_vod = False
        self.current_video = None

    def _get_entry_duration(self, video_path: str) -> float:
        """Get total duration of a video file (cached to avoid repeated ffprobe calls)."""
        path_key = str(video_path)
        if path_key in self._duration_cache:
            return self._duration_cache[path_key]
        try:
            result = subprocess.run([
                FFPROBE_PATH, "-v", "error", "-show_entries",
                "format=duration", "-of", "csv=p=0",
                path_key
            ], capture_output=True, text=True, check=True, timeout=10)
            duration = float(result.stdout.strip())
            duration = duration if duration > 0 else 5400.0
        except Exception as e:
            self.logger.warning(f"Duration fallback for {video_path}: {e}")
            duration = 5400.0
        self._duration_cache[path_key] = duration
        return duration

    def _stop_current_ffmpeg(self):
        """Stop the current FFmpeg process gracefully."""
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            self.logger.info(f"Stopping current FFmpeg process for {self.channel}...")
            
            # Stop watchdog
            if self.watchdog:
                self.watchdog.running = False
            
            # Clean up error thread before terminating FFmpeg
            if self.error_thread and self.error_thread.is_alive():
                try:
                    # Close stderr to unblock the thread's read operation
                    if self.ffmpeg_process and self.ffmpeg_process.stderr:
                        self.ffmpeg_process.stderr.close()
                    self.error_thread.join(timeout=5)
                except Exception as e:
                    self.logger.warning(f"Error cleaning up error thread: {e}")
                finally:
                    self.error_thread = None
            
            # Terminate FFmpeg
            self.ffmpeg_process.terminate()
            try:
                self.ffmpeg_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.logger.warning(f"FFmpeg did not stop gracefully, killing...")
                self.ffmpeg_process.kill()
                self.ffmpeg_process.wait()
            
            self.ffmpeg_process = None
            self.logger.info(f"FFmpeg stopped for {self.channel}")

    def _get_best_standby(self) -> Path:
        """Find the best standby file matching the channel resolution."""
        # Try resolution-specific standby first
        standby_path = Path("assets/standby") / f"standby_{self.target_resolution}.mp4"
        if standby_path.exists():
            self.logger.info(f"Using resolution-specific standby: {standby_path.name}")
            return standby_path
        
        # Fall back to default
        default_standby = Path("assets/standby/default_standby.mp4")
        if default_standby.exists():
            self.logger.info(f"Using default standby: {default_standby.name}")
            return default_standby
        
        # Last resort: try any standby file (sorted for deterministic selection)
        standby_dir = Path("assets/standby")
        if standby_dir.exists():
            standby_files = sorted(standby_dir.glob("*.mp4"), key=lambda p: p.name)
            if standby_files:
                self.logger.warning(f"No matching standby found, using: {standby_files[0].name}")
                return standby_files[0]
        
        self.logger.error("No standby files found!")
        return Path("assets/standby/default_standby.mp4")  # Return path even if doesn't exist

    def _cleanup_hls_directory(self):
        """Clean up old HLS segments before starting new playback."""
        if self.hls_dir and self.hls_dir.exists():
            # Only delete segment files - keep playlist to avoid player 404
            for f in self.hls_dir.glob("seg_*.ts"):
                try:
                    f.unlink()
                except Exception as e:
                    self.logger.warning(f"Failed to delete segment {f.name}: {e}")

    def play_now(self, video_path: str, start_position: float = 0):
        """Public method to queue a video for immediate playback."""
        self.logger.info(f"[MSG] Queueing video for playback: {video_path} (start: {start_position}s)")
        self.command_queue.put(("play_now", video_path, start_position))