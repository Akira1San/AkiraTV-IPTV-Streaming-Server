# akiratv/workers/base_worker.py
import subprocess
import time
import threading
from pathlib import Path
from typing import List, Dict, Optional

# === NEW WATCHDOG CLASS ===
class Watchdog(threading.Thread):
    """
    Monitors the FFmpeg process. If no log output is received for a specific 
    timeout duration, it assumes the process is frozen and kills it.
    """
    def __init__(self, process: subprocess.Popen, logger, timeout_seconds=30):
        super().__init__(daemon=True)
        self.process = process
        self.logger = logger
        self.timeout = timeout_seconds
        self.last_heartbeat = time.time()
        self.running = True

    def ping(self):
        """Call this whenever FFmpeg outputs data to keep the watchdog happy."""
        self.last_heartbeat = time.time()

    def run(self):
        while self.running:
            # Check if process is still alive
            if self.process.poll() is not None:
                break 

            # Check for freeze
            if time.time() - self.last_heartbeat > self.timeout:
                self.logger.error(f"🛑 WATCHDOG: FFmpeg process frozen (no output for {self.timeout}s). Killing process...")
                try:
                    self.process.kill()
                except Exception:
                    pass
                break
            
            time.sleep(1)

# === BASE WORKER CLASS ===
class BaseWorker:
    # ... (Your existing __init__ code) ...
    def __init__(self, channel: str, config, logger):
        self.channel = channel
        self.config = config
        self.logger = logger
        self.running = True
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        # Initialize the watchdog placeholder
        self.watchdog: Optional[Watchdog] = None
        self.current_video = "Unknown"

    def initialize_worker(self) -> bool:
        """Initialize worker resources and validate setup."""
        hls_path = self.config.get_hls_output_path(self.channel)
        try:
            hls_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"HLS directory ready for {self.channel}: {hls_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create HLS directory for {self.channel}: {e}")
            return False

    def stop(self):
        """Gracefully stop the worker and its FFmpeg process."""
        self.logger.info(f"Stop signal received for channel {self.channel}...")
        self.running = False
        
        # Stop the watchdog if it's running
        if self.watchdog:
            self.watchdog.running = False

        if hasattr(self, 'ffmpeg_process') and self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            self.logger.info(f"Terminating FFmpeg process for {self.channel}...")
            self.ffmpeg_process.terminate()
            try:
                self.ffmpeg_process.wait(timeout=5)
                self.logger.info(f"FFmpeg for {self.channel} terminated gracefully.")
            except subprocess.TimeoutExpired:
                self.logger.warning(f"FFmpeg for {self.channel} did not stop, force killing...")
                self.ffmpeg_process.kill()
                self.ffmpeg_process.wait()
                self.logger.info(f"FFmpeg for {self.channel} killed.")
        
        self.logger.info(f"Worker for channel {self.channel} stopped.")

    def _execute_ffmpeg(self, args: List[str]):
        """Execute FFmpeg command and handle errors with File Context."""

        self.logger.info(f"Starting FFmpeg for {self.channel}: {' '.join(str(a) for a in args)}")
        try:
            self.ffmpeg_process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=False
            )

            self.watchdog = Watchdog(self.ffmpeg_process, self.logger, timeout_seconds=30)
            self.watchdog.start()

            def log_errors():
                if self.ffmpeg_process.stderr:
                    for line in iter(self.ffmpeg_process.stderr.readline, b''):
                        if line:
                            if self.watchdog:
                                self.watchdog.ping()

                            try:
                                try:
                                    decoded_line = line.decode('utf-8').strip()
                                except UnicodeDecodeError:
                                    decoded_line = line.decode('cp1252', errors='replace').strip()
                                
                                # === 1. DETECT NOW PLAYING ===
                                if "Opening '" in decoded_line:
                                    try:
                                        start = decoded_line.find("'") + 1
                                        end = decoded_line.rfind("'")
                                        path_str = decoded_line[start:end]
                                        
                                        filename = Path(path_str).name
                                        
                                        # Filter out: HLS segments, playlists, and temp files
                                        if not any([
                                            filename.startswith("seg_"),      # HLS segments
                                            filename.endswith(".m3u8"),       # Playlist files
                                            filename.endswith(".tmp"),        # Temp files
                                            filename.endswith(".ts"),         # Individual TS files
                                            "playlist" in filename.lower()    # Any playlist-related files
                                        ]):
                                            # Only update if it's actually a new video file
                                            if self.current_video != filename:
                                                self.current_video = filename
                                                self.logger.info(f"[PLAY] NOW PLAYING: {filename}")
                                    except Exception:
                                        pass

                                # === 2. HARMLESS INFO (FILTER OUT) ===
                                elif any(phrase in decoded_line for phrase in [
                                    "Auto-inserting h264_mp4toannexb",
                                    "Auto-inserting hevc_mp4toannexb",
                                    "Automatically inserted bitstream filter"
                                ]):
                                    # These are normal FFmpeg info messages, not errors
                                    pass

                                # === 3. HARMLESS WARNINGS (DOWNGRADE TO DEBUG) ===
                                elif "Non-monotonic DTS" in decoded_line or "non-monotonic" in decoded_line.lower():
                                    # These are common with concat and usually harmless
                                    # Only log as debug to avoid log spam
                                    if self.logger.isEnabledFor(10):  # DEBUG level
                                        self.logger.debug(f"[{self.current_video}] {decoded_line}")

                                # === 4. REAL ERRORS (WITH CONTEXT) ===
                                elif any(keyword in decoded_line.lower() for keyword in [
                                    "error opening",
                                    "invalid data",
                                    "no such file",
                                    "permission denied",
                                    "could not",
                                    "failed to",
                                    "cannot"
                                ]) and "error" in decoded_line.lower():
                                    # Only log actual errors with context
                                    self.logger.error(f"⚠️ ERROR in [{self.current_video}]: {decoded_line}")

                                # === 5. STREAM INFO (WHEN NEW FILE STARTS) ===
                                elif "Stream #" in decoded_line and self.current_video != "Unknown":
                                    # Log stream info only when a new file is opened
                                    # This helps understand what's being processed
                                    pass  # Could add debug logging here if needed

                                # === 6. CLEANUP LOGS ===
                                elif "Deleting old segment" in decoded_line:
                                    # Normal HLS cleanup
                                    pass

                            except Exception as e:
                                self.logger.error(f"Error decoding FFmpeg output: {e}")
            
            error_thread = threading.Thread(target=log_errors, daemon=True)
            error_thread.start()

            while self.running and self.ffmpeg_process and self.ffmpeg_process.poll() is None:
                time.sleep(0.5)

            if self.watchdog:
                self.watchdog.running = False
            error_thread.join(timeout=1)

            if self.ffmpeg_process and self.ffmpeg_process.returncode != 0:
                self.logger.error(f"FFmpeg exited with code {self.ffmpeg_process.returncode} for {self.channel}")

        except Exception as e:
            self.logger.error(f"FFmpeg failed to start for {self.channel}: {e}")

    def update_now_next(self, current_video: str, next_video: str):
        """Update the global stats for now/next playing."""
        from ..stats import AKIRATV_STATS, STATS_LOCK
        global AKIRATV_STATS
        with STATS_LOCK:
            AKIRATV_STATS["now_playing"] = current_video
            AKIRATV_STATS["next_program"] = next_video