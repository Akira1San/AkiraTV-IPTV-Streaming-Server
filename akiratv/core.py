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
from .server.http_server import HttpServer

from pathlib import Path
from datetime import datetime

from .server.app_context import app_context
from .stats import AKIRATV_STATS, STATS_LOCK, get_active_viewers, ACTIVE_CONNECTIONS, ACTIVE_CONNECTIONS_LOCK

from akiratv.assets import sync_channel_logos
from akiratv.config import USER_CHANNELS_DIR

from .config import Config
from .scheduler import get_full_todays_schedule
from .scheduler import get_current_schedule_for_channel

import logging

AKIRATV_INSTANCE = None

os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("AkiraTV")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("logs/worker.log", mode='a', encoding='utf-8')
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class AkiraTV:
    def __init__(self):
        self.config = Config.load_or_create()
        self.workers: dict[str, tuple[BaseWorker, threading.Thread]] = {}
        self.running = False
        self.http_server: HttpServer | None = None
        app_context.set_akiratv(self)

        inventory_path = Path("user/video_inventory.json")
        self.inventory_manager = InventoryManager(inventory_path)
        self.transcoding_service = TranscodingService(self.config, self.inventory_manager)

        global AKIRATV_STATS
        with STATS_LOCK:
            AKIRATV_STATS.update({"config": self.config.data.copy()})
        
        import queue
        self.command_queue = queue.Queue()
        self._command_thread = None
        self._command_thread_running = False
        
        # NEW: Track restart state for linear channels
        self.linear_channel_configs = {}

    def start(self):
        """Main entry point - orchestrates all streaming operations"""
        self.running = True
        logger.info("AkiraTV starting...")
        
        global AKIRATV_STATS
        with STATS_LOCK:
            AKIRATV_STATS.update({
                "status": "Streaming",
                "channels": 0,
                "uptime": "0s",
                "config": self.config.data.copy()
            })
        
        if not self._command_thread:
            self._command_thread = threading.Thread(
                target=self._command_loop,
                daemon=True
            )
            self._command_thread.start()
        
        if not self.initialize_http_server():
            return
        
        output_root = self.config.get_output_root()
        sync_channel_logos(USER_CHANNELS_DIR, output_root)
        
        channels_config = self.config.data.get("channels", {})
        
        for channel_name, channel_conf in channels_config.items():
            if not channel_conf.get("enabled", False):
                logger.info(f"Channel '{channel_name}' is disabled. Skipping.")
                continue

            channel_type = channel_conf.get("type", "linear")
            
            try:
                if channel_type == "vod":
                    self._start_vod_channel(channel_name)
                elif channel_type == "linear":
                    self._start_linear_channel(channel_name)
                elif channel_type == "dynamic":
                    self._start_dynamic_channel(channel_name)
                else:
                    logger.error(f"Unknown channel type '{channel_type}' for channel '{channel_name}'. Skipping.")
                    continue

            except Exception as e:
                logger.error(f"[ERROR] Failed to start worker for {channel_name}: {e}")

        if not self.workers:
            logger.error("No channels were started. Exiting.")
            print("[ERROR] No valid channels to stream. Check your configuration.")
            return

        self.finalize_startup()
        self.monitor_runtime()

    def _start_vod_channel(self, channel_name: str):
        """Start a VOD channel (no auto-restart)"""
        logger.info(f"Starting VOD channel: {channel_name}")
        import queue
        
        command_queue = queue.Queue()
        worker = VODWorker(
            channel=channel_name,
            config=self.config,
            logger=logger,
            transcoding_service=self.transcoding_service,
            command_queue=command_queue
        )
        
        thread = threading.Thread(target=worker.run, daemon=True)
        self.workers[channel_name] = (worker, thread)
        thread.start()
        logger.info(f"[OK] VOD worker for {channel_name} started.")

    def _start_dynamic_channel(self, channel_name: str):
        """Start a dynamic channel (standby with VOD switching)"""
        logger.info(f"Starting Dynamic channel: {channel_name}")
        import queue
        
        from .workers.dynamic_worker import DynamicWorker
        
        # Get schedule if it exists for this channel
        from .scheduler import get_current_schedule_for_channel
        schedule = get_current_schedule_for_channel(channel_name)
        
        command_queue = queue.Queue()
        worker = DynamicWorker(
            channel=channel_name,
            config=self.config,
            logger=logger,
            transcoding_service=self.transcoding_service,
            inventory_manager=self.inventory_manager,
            command_queue=command_queue,
            schedule_entries=schedule
        )
        
        thread = threading.Thread(target=worker.run, daemon=True)
        self.workers[channel_name] = (worker, thread)
        thread.start()
        logger.info(f"[OK] Dynamic worker for {channel_name} started.")

    def _start_linear_channel(self, channel_name: str):
        """Start a linear channel with auto-restart wrapper"""
        logger.info(f"Starting Linear channel: {channel_name}")
        
        from .scheduler import get_current_schedule_for_channel
        schedule = get_current_schedule_for_channel(channel_name)
        
        if not schedule:
            logger.warning(f"No schedule found for linear channel '{channel_name}'. Skipping.")
            return

        # Store the channel config for restarts
        self.linear_channel_configs[channel_name] = {
            "schedule": schedule
        }
        
        # Start the worker with auto-restart wrapper
        thread = threading.Thread(
            target=self._linear_worker_with_restart,
            args=(channel_name,),
            daemon=True
        )
        
        # We store a placeholder worker reference (will be updated in the restart loop)
        self.workers[channel_name] = (None, thread)
        thread.start()
        logger.info(f"[OK] Linear worker for {channel_name} started with auto-restart.")

    def _linear_worker_with_restart(self, channel_name: str):
        """Wrapper that restarts a linear worker when it exits"""
        while self.running:
            try:
                logger.info(f"[REFRESH] Starting/Restarting linear worker for {channel_name}...")
                
                # Get fresh schedule
                from .scheduler import get_current_schedule_for_channel
                schedule = get_current_schedule_for_channel(channel_name)
                
                if not schedule:
                    logger.warning(f"No schedule for {channel_name}, waiting 60s...")
                    time.sleep(60)
                    continue
                
                # Create worker
                worker = LinearWorker(
                    channel=channel_name,
                    schedule_entries=schedule,
                    config=self.config,
                    logger=logger,
                    transcoding_service=self.transcoding_service
                )
                
                # Update the worker reference
                if channel_name in self.workers:
                    _, thread = self.workers[channel_name]
                    self.workers[channel_name] = (worker, thread)
                
                # Run the worker (blocks until it exits)
                worker.run()
                
                # If we reach here, the worker has exited
                if self.running:
                    logger.warning(f"⚠️ Linear worker for {channel_name} exited. Restarting in 10s...")
                    time.sleep(10)  # Cool-down period
                else:
                    logger.info(f"Linear worker for {channel_name} stopped (shutdown requested).")
                    break
                    
            except Exception as e:
                logger.error(f"[ERROR] Error in linear worker for {channel_name}: {e}")
                if self.running:
                    logger.info(f"Retrying in 10s...")
                    time.sleep(10)
                else:
                    break
        
        logger.info(f"Linear worker restart loop for {channel_name} has exited.")

    def initialize_http_server(self):
        """Initialize HTTP server for HLS streaming"""
        output_mode = self.config.data["output"]["mode"]
        if output_mode not in ("http_hls", "ram_http"):
            return True
        
        try:
            hls_root = self.get_hls_root_path()
            hls_root.mkdir(parents=True, exist_ok=True)
            print(f"[FOLDER] HTTP server will serve HLS from: {hls_root.resolve()}")
            
            http_conf = self.config.data["output"]["http"]
            port = http_conf.get("port", 8080)
            bind = http_conf.get("bind", "127.0.0.1")
            
            self.http_server = HttpServer(self.config, AKIRATV_STATS, STATS_LOCK)
            self.http_server.start(str(hls_root), port, bind)
            
            return True
        except Exception as e:
            logger.error(f"HTTP server failed: {e}")
            print("[ERROR] Error: Could not start HTTP server.")
            return False

    def get_hls_root_path(self):
        """Get HLS root path based on output mode"""
        output_mode = self.config.data["output"]["mode"]
        if output_mode == "ram_http":
            return Path(self.config.data["storage"]["ram_path"])
        else:
            return Path(self.config.data["storage"]["disk_path"])

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

    def finalize_startup(self):
        """Final setup after workers are launched"""
        if not self.workers:
            return
            
        first_channel = next(iter(self.workers))
        port = self.config.data["output"]["http"].get("port", 8080)
        bind = self.config.data["output"]["http"].get("bind", "127.0.0.1")
        ip = bind if bind != "0.0.0.0" else "YOUR_LOCAL_IP"
        print(f"[OK] AkiraTV is running! Streaming {len(self.workers)} channel(s).")
        print(f"Watch: http://{ip}:{port}/hls/{first_channel}/index.m3u8")

    def stop(self):
        self._command_thread_running = False
        logger.info("Shutting down AkiraTV...")
        global AKIRATV_STATS
        with STATS_LOCK:
            AKIRATV_STATS["status"] = "Stopped"
        self.running = False

        if self.http_server:
            self.http_server.stop()

        for channel_name, (worker, thread) in self.workers.items():
            if worker:  # Worker might be None during initialization
                logger.info(f"Sending stop signal to worker for channel: {channel_name}")
                worker.stop()
            logger.info(f"Waiting for worker thread to finish: {channel_name}")
            thread.join(timeout=5)
            logger.info(f"Worker for channel: {channel_name} has stopped.")
        
        logger.info("AkiraTV stopped.")

    def monitor_runtime(self):
        try:
            while self.running:
                with STATS_LOCK:
                    AKIRATV_STATS["viewers"] = get_active_viewers()
                
                for worker, _ in self.workers.values():
                    if worker and hasattr(worker, 'dynamic_playlist') and worker.dynamic_playlist:
                        info = worker.dynamic_playlist.get_current_program_info()
                        with STATS_LOCK:
                            AKIRATV_STATS["now_playing"] = info["now"]
                            AKIRATV_STATS["next_program"] = info["next"]
                        break
                
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
            for worker, thread in self.workers.values():
                if worker:
                    worker.running = False
            self.workers.clear()
            
            self.launch_channel_workers(all_entries)
            logger.info("Schedule reloaded successfully.")
        else:
            logger.warning("No schedule entries found after reload.")

    def play_now(self, channel: str, video_path: str):
        """Sends a play_now command to a VOD or Dynamic worker."""
        if channel not in self.workers:
            logger.warning(f"⚠️ Channel '{channel}' not found. Cannot play video.")
            return

        worker, _ = self.workers[channel]

        if isinstance(worker, VODWorker):
            logger.info(f"[PLAY] Sending 'play_now' command to VOD channel '{channel}'.")
            worker.play_now(video_path)
        elif hasattr(worker, 'play_now'):  # DynamicWorker also has play_now
            logger.info(f"[PLAY] Sending 'play_now' command to Dynamic channel '{channel}'.")
            worker.play_now(video_path)
        else:
            logger.warning(f"⚠️ Channel '{channel}' does not support play_now commands.")

    def _command_loop(self):
        self._command_thread_running = True
        while self._command_thread_running:
            try:
                cmd, channel, video_path = self.command_queue.get(timeout=0.2)
            except Exception:
                continue

            if cmd == "play_now":
                self.play_now(channel, video_path)
                print("[MSG] Command received:", cmd, channel)

    def process_commands(self):
        while not self.command_queue.empty():
            cmd, channel, path = self.command_queue.get()
            if cmd == "play_now":
                self.play_now(channel, path)

    def enqueue_play_now(self, channel, video_path):
        self.command_queue.put(("play_now", channel, video_path))