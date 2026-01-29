# akiratv/core.py
import json
import threading
import time
import os
import http.server
import socketserver

from .workers.base_worker import BaseWorker
from .workers.linear_worker import LinearWorker
from .workers.vod_worker import VODWorker
from .workers.transcoding import TranscodingService
from .inventory import InventoryManager
from .server.http_server import HttpServer  # New import

from pathlib import Path
from datetime import datetime
#from typing import List
#from socketserver import ThreadingMixIn
#from .chunk_resolver import resolve_chunks
#from .worker import ChannelWorker

from .server.app_context import app_context  # New import
from .server.dashboard import generate_dashboard_html
from .stats import AKIRATV_STATS, STATS_LOCK, get_active_viewers, ACTIVE_CONNECTIONS, ACTIVE_CONNECTIONS_LOCK

from akiratv.assets import sync_channel_logos
from akiratv.config import USER_CHANNELS_DIR

from .config import Config
from .scheduler import get_full_todays_schedule
from .scheduler import get_current_schedule_for_channel

import logging

AKIRATV_INSTANCE = None

os.makedirs("logs", exist_ok=True)

# --- NEW, ROBUST LOGGING SETUP ---
logger = logging.getLogger("AkiraTV")
logger.setLevel(logging.INFO)

# Create a file handler that explicitly uses UTF-8 encoding
file_handler = logging.FileHandler("logs/worker.log", mode='a', encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Create a formatter to define the log message format
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
file_handler.setFormatter(formatter)

# Add the handler to our logger
logger.addHandler(file_handler)
# --- END OF NEW LOGGING SETUP ---

# Suppress noisy loggers from other libraries
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("ngrok").setLevel(logging.WARNING)

class AkiraTV:
    def __init__(self):
        self.config = Config.load_or_create()
        self.workers: dict[str, tuple[BaseWorker, threading.Thread]] = {} # Use BaseWorker for type hint
        self.running = False
        self.http_server: HttpServer | None = None  # New attribute
        app_context.set_akiratv(self)

        # Initialize the new services
        inventory_path = Path("user/video_inventory.json")
        self.inventory_manager = InventoryManager(inventory_path)
        self.transcoding_service = TranscodingService(self.config, self.inventory_manager)

        # Store in global stats
        global AKIRATV_STATS
        with STATS_LOCK:
            #AKIRATV_STATS["config"] = self.config.data
            AKIRATV_STATS.update({"config": self.config.data.copy()})
        # command_queue
        import queue
        self.command_queue = queue.Queue()
        self._command_thread = None
        self._command_thread_running = False

    def start(self):
        """Main entry point - orchestrates all streaming operations"""
        self.running = True
        logger.info("AkiraTV starting...")
        
        # Update global stats
        global AKIRATV_STATS
        with STATS_LOCK:
            AKIRATV_STATS.update({
                "status": "Streaming",
                "channels": 0,
                "uptime": "0s",
                "config": self.config.data.copy()
            })
        
        # Start the command processing thread
        if not self._command_thread:
            self._command_thread = threading.Thread(
                target=self._command_loop,
                daemon=True
            )
            self._command_thread.start()
        
        # Initialize components
        if not self.initialize_http_server():
            return
        
        # 🔹 COPY USER LOGOS → OUTPUT
        output_root = self.config.get_output_root()
        sync_channel_logos(USER_CHANNELS_DIR, output_root)
        
        # === LAUNCH ALL ENABLED CHANNELS (Linear and VOD) ===
        channels_config = self.config.data.get("channels", {})
        
        for channel_name, channel_conf in channels_config.items():
            if not channel_conf.get("enabled", False):
                logger.info(f"Channel '{channel_name}' is disabled. Skipping.")
                continue

            channel_type = channel_conf.get("type", "linear") # Default to linear for safety
            worker = None

            try:
                if channel_type == "vod":
                    logger.info(f"Starting VOD channel: {channel_name}")
                    import queue # Make sure to import the queue module
                    
                    command_queue = queue.Queue() # Create the queue
                    worker = VODWorker(
                        channel=channel_name,
                        config=self.config,
                        logger=logger,
                        transcoding_service=self.transcoding_service,
                        command_queue=command_queue # <-- ADD THIS ARGUMENT
                    )
                elif channel_type == "linear":
                    logger.info(f"Starting Linear channel: {channel_name}")
                    # Load schedule for this specific channel
                    from .scheduler import get_current_schedule_for_channel
                    schedule = get_current_schedule_for_channel(channel_name)
                    
                    if not schedule:
                        logger.warning(f"No schedule found for linear channel '{channel_name}'. Skipping.")
                        continue

                    worker = LinearWorker(
                        channel=channel_name,
                        schedule_entries=schedule,
                        config=self.config,
                        logger=logger,
                        transcoding_service=self.transcoding_service
                    )
                else:
                    logger.error(f"Unknown channel type '{channel_type}' for channel '{channel_name}'. Skipping.")
                    continue

                # Start the worker in a new thread
                thread = threading.Thread(target=worker.run, daemon=True)
                self.workers[channel_name] = (worker, thread)
                thread.start()
                logger.info(f"✅ Worker for {channel_name} ({channel_type}) started.")

            except Exception as e:
                logger.error(f"❌ Failed to start worker for {channel_name}: {e}")

        if not self.workers:
            logger.error("No channels were started. Exiting.")
            print("❌ No valid channels to stream. Check your configuration.")
            return

        # Final setup and monitoring
        self.finalize_startup()
        self.monitor_runtime()

    def initialize_http_server(self):
            """Initialize HTTP server for HLS streaming"""
            output_mode = self.config.data["output"]["mode"]
            if output_mode not in ("http_hls", "ram_http"):
                return True
            
            try:
                hls_root = self.get_hls_root_path()
                hls_root.mkdir(parents=True, exist_ok=True)
                print(f"📁 HTTP server will serve HLS from: {hls_root.resolve()}")
                
                http_conf = self.config.data["output"]["http"]
                port = http_conf.get("port", 8080)
                bind = http_conf.get("bind", "127.0.0.1")
                
                # Create and start the HTTP server using the new HttpServer class
                self.http_server = HttpServer(self.config, AKIRATV_STATS, STATS_LOCK)
                self.http_server.start(str(hls_root), port, bind)
                
                return True
            except Exception as e:
                logger.error(f"HTTP server failed: {e}")
                print("❌ Error: Could not start HTTP server.")
                return False

    def get_hls_root_path(self):
        """Get HLS root path based on output mode"""
        output_mode = self.config.data["output"]["mode"]
        if output_mode == "ram_http":
            return Path(self.config.data["storage"]["ram_path"])
        else:
            return Path(self.config.data["storage"]["disk_path"])

    # def load_and_validate_schedule(self):
    #     try:
    #         # For XMLTV generation, use full schedule
    #         # But for streaming, use per-channel current schedule
    #         from .scheduler import get_current_schedule_for_channel
            
    #         all_entries = []
    #         for channel, chan_conf in self.config.data.get("channels", {}).items():
    #             if chan_conf.get("enabled", True):
    #                 entries = get_current_schedule_for_channel(channel)
    #                 all_entries.extend(entries)
            
    #         if not all_entries:
    #             logger.warning("No schedule entries for today.")
    #             return None
            
    #         self.log_schedule_info(all_entries)
    #         return all_entries
    #     except Exception as e:
    #         logger.error(f"Failed to load schedule: {e}")
    #         return None

    def log_schedule_info(self, schedule):
        """Log current schedule information for debugging"""
        if not isinstance(schedule, list):
            logger.error("Invalid schedule format: Expected a list of dictionaries.")
            return

        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            logger.info(f"Current time: {current_time}")
            logger.info(f"Playing {len(schedule)} schedule entries:")

            for i, entry in enumerate(schedule):
                try:
                    video_name = Path(entry["file"]).name
                    logger.info(f"  {i+1}. {entry['time']} - {video_name} (channel: {entry['channel']})")
                except KeyError as e:
                    logger.warning(f"Missing key in schedule entry {i+1}: {e}")
                except Exception as e:
                    logger.error(f"Error processing schedule entry {i+1}: {e}")
        except Exception as e:
            logger.error(f"Failed to log schedule information: {e}")

    # def launch_channel_workers(self, schedule):
    #     """Launch worker threads for each channel"""
    #     from collections import defaultdict
    #     channel_entries = defaultdict(list)
    #     for entry in schedule:
    #         channel_entries[entry["channel"]].append(entry)

    #     print(f"🎬 Launching workers for channels: {list(channel_entries.keys())}")

    #     # Update Now/Next in global stats
    #     from .stats import AKIRATV_STATS, STATS_LOCK
    #     if schedule:  # ← Use 'schedule' (the parameter)
    #         # Get first 2 entries
    #         first = schedule[0] if schedule else {}
    #         second = schedule[1] if len(schedule) > 1 else {}
            
    #         # Extract titles (use filename if no title)
    #         now_title = Path(first.get("file", "")).stem if first else "N/A"
    #         next_title = Path(second.get("file", "")).stem if second.get("file") else ""
            
    #         with STATS_LOCK:
    #             AKIRATV_STATS["now_playing"] = now_title
    #             AKIRATV_STATS["next_program"] = next_title
        
    #     workers_started = 0
    #     print(f"🎬 Channels to launch: {list(channel_entries.keys())}")
    #     for channel, entries in channel_entries.items():
    #         print(f"   - {channel}: {len(entries)} entries")
    #         if self.should_skip_channel(channel, entries):
    #             print(f"     → Skipping (disabled or no videos)")
    #             continue
                
    #         if not self.start_channel_worker(channel, entries):
    #             print(f"     → Failed to start worker")
    #             continue
                
    #         workers_started += 1
    #         logger.info(f"Started worker for channel: {channel}")
        
    #     if workers_started == 0:
    #         logger.error("No channels started. Exiting.")
    #         print("❌ No valid channels to stream. Check your schedule and file paths.")
    #         return False
            
    #     self.active_worker_count = workers_started
    #     # Update channel count
    #     with STATS_LOCK:
    #         AKIRATV_STATS["channels"] = workers_started
            
    #     return True

    # def should_skip_channel(self, channel, entries):
    #     """Determine if a channel should be skipped"""
    #     if not entries:
    #         logger.warning(f"No valid videos for channel: {channel}")
    #         return True
            
    #     chan_config = self.config.data.get("channels", {}).get(channel, {})
    #     if not chan_config.get("enabled", True):
    #         logger.info(f"Channel {channel} is disabled in config. Skipping.")
    #         return True
            
    #     return False

    # def start_channel_worker(self, channel, entries):
    #     """Start a single channel worker"""
    #     # Stop and cleanup existing worker properly
    #     if channel in self.workers:
    #         worker, thread = self.workers[channel]
    #         worker.running = False
    #         # Wait for worker to finish (with timeout)
    #         thread.join(timeout=3)
    #         # Cleanup HLS directory
    #         hls_path = self.config.get_hls_output_path(channel)
    #         if hls_path.exists():
    #             import shutil
    #             try:
    #                 shutil.rmtree(hls_path)
    #                 hls_path.mkdir(exist_ok=True)
    #             except:
    #                 pass
        
    #     try:
    #         worker = ChannelWorker(channel, entries, self.config, logger)
    #         thread = threading.Thread(target=worker.run, daemon=True)
    #         self.workers[channel] = (worker, thread)
    #         thread.start()
    #         return True
    #     except Exception as e:
    #         logger.error(f"Failed to start worker for {channel}: {e}")
    #         return False


    def finalize_startup(self):
        """Final setup after workers are launched"""
        if not self.workers:
            return
            
        first_channel = next(iter(self.workers))
        port = self.config.data["output"]["http"].get("port", 8080)
        bind = self.config.data["output"]["http"].get("bind", "127.0.0.1")
        ip = bind if bind != "0.0.0.0" else "YOUR_LOCAL_IP"
        print(f"✅ AkiraTV is running! Streaming {len(self.workers)} channel(s).")
        print(f"▶️  Watch: http://{ip}:{port}/hls/{first_channel}/index.m3u8")

    def stop(self):
        self._command_thread_running = False
        logger.info("Shutting down AkiraTV...")
        global AKIRATV_STATS
        with STATS_LOCK:
            AKIRATV_STATS["status"] = "Stopped"
        self.running = False

        # Stop HTTP server
        if self.http_server:
            self.http_server.stop()

        # --- THIS IS THE CRITICAL PART ---
        for worker, thread in self.workers.values():
            logger.info(f"Sending stop signal to worker for channel: {worker.channel}")
            worker.stop() # Call the worker's own stop method
            thread.join(timeout=5) # Wait for the worker's thread to finish
            logger.info(f"Worker for channel: {worker.channel} has stopped.")
        
        logger.info("AkiraTV stopped.")

    def monitor_runtime(self):
        try:
            while self.running:
                # Update viewers
                with STATS_LOCK:
                    AKIRATV_STATS["viewers"] = get_active_viewers()
                
                # Update Now/Next from dynamic playlist (if exists)
                for worker, _ in self.workers.values():
                    if hasattr(worker, 'dynamic_playlist') and worker.dynamic_playlist:
                        info = worker.dynamic_playlist.get_current_program_info()
                        with STATS_LOCK:
                            AKIRATV_STATS["now_playing"] = info["now"]
                            AKIRATV_STATS["next_program"] = info["next"]
                        break  # Use first worker's info
                
                time.sleep(2)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def reload_schedule(self):
        """Reload schedule without restarting AkiraTV."""
        from .scheduler import get_current_schedule_for_channel
        all_entries = []
        for channel, chan_conf in self.config.data.get("channels", {}).items():
            if chan_conf.get("enabled", True):
                entries = get_current_schedule_for_channel(channel)
                all_entries.extend(entries)
        
        if all_entries:
            # Stop current workers
            for worker, thread in self.workers.values():
                worker.running = False
            self.workers.clear()
            
            # Start new workers with updated schedule
            self.launch_channel_workers(all_entries)
            logger.info("Schedule reloaded successfully.")
        else:
            logger.warning("No schedule entries found after reload.")

    # def create_dynamic_playlists(self, channels):
    #     for channel in channels:
    #         if channel in self.workers:
    #             worker, _ = self.workers[channel]
    #             worker.running = False
                
    #             # Find standby path
    #             standby_path = None
    #             hls_root = self.get_hls_root_path()
    #             for candidate in ["standby.mp4", "logo.mp4", "filler.mp4"]:
    #                 if (hls_root / candidate).exists():
    #                     standby_path = str(hls_root / candidate)
    #                     break
                
    #             # Start new worker with standby
    #             new_worker = ChannelWorker(channel, worker.schedule_entries, self.config, logger)
    #             new_worker.use_dynamic_playlist = True
    #             if standby_path:
    #                 new_worker.standby_path = standby_path  # ← Store for later
    #             thread = threading.Thread(target=new_worker.run, daemon=True)
    #             self.workers[channel] = (new_worker, thread)
    #             thread.start()

    # def create_dynamic_channel(self, channel_name: str):
    #     """Create a new dynamic channel with standby loop."""
    #     # Ensure channel is enabled in config
    #     self.config.data.setdefault("channels", {})
    #     self.config.data["channels"][channel_name] = {"enabled": True}
    #     self.save_config()  # Assuming you have this method

    #     # Create worker with empty schedule
    #     from .worker import ChannelWorker
    #     worker = ChannelWorker(channel_name, [], self.config, logger)
    #     worker.use_dynamic_playlist = True
        
    #     # Find standby path
    #     hls_root = self.get_hls_root_path()
    #     standby_path = None
    #     for candidate in ["standby.mp4", "logo.mp4"]:
    #         if (hls_root / candidate).exists():
    #             standby_path = str(hls_root / candidate)
    #             break
    #     if standby_path:
    #         worker.standby_path = standby_path

    #     # Start worker
    #     thread = threading.Thread(target=worker.run, daemon=True)
    #     self.workers[channel_name] = (worker, thread)
    #     thread.start()
    #     logger.info(f"Started dynamic channel: {channel_name}")

    def play_now(self, channel: str, video_path: str):
        """Sends a play_now command to a VOD worker."""
        if channel not in self.workers:
            logger.warning(f"⚠️ Channel '{channel}' not found. Cannot play video.")
            # Optionally, you could create a dynamic VOD channel on the fly here
            return

        worker, _ = self.workers[channel]

        # Ensure the worker is a VOD worker before calling play_now
        if isinstance(worker, VODWorker):
            logger.info(f"🎬 Sending 'play_now' command to VOD channel '{channel}'.")
            worker.play_now(video_path)
        else:
            logger.warning(f"⚠️ Channel '{channel}' is not a VOD channel. Cannot play video.")

    def _command_loop(self):
        self._command_thread_running = True
        while self._command_thread_running:
            try:
                cmd, channel, video_path = self.command_queue.get(timeout=0.2)
            except Exception:
                continue

            if cmd == "play_now":
                self.play_now(channel, video_path)
                print("📬 Command received:", cmd, channel)

    def process_commands(self):
        while not self.command_queue.empty():
            cmd, channel, path = self.command_queue.get()
            if cmd == "play_now":
                self.play_now(channel, path)


    def enqueue_play_now(self, channel, video_path):
        self.command_queue.put(("play_now", channel, video_path))