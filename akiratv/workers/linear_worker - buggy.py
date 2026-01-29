import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, date
from .base_worker import BaseWorker
import threading

class LinearWorker(BaseWorker):
    def __init__(self, channel: str, schedule_entries: List[Dict], config, logger, transcoding_service):
        super().__init__(channel, config, logger)
        self.schedule_entries = schedule_entries
        self.transcoding_service = transcoding_service
        self.temp_dir: Optional[Path] = None

        # 1. BLACKLIST: Keep track of files that caused crashes
        self.failed_files = set()
        
        # 2. TRACKER: Flag for the background thread
        self.tracker_running = False

    def run(self):
        """Main execution orchestrator with auto-restart loop and Time Tracker."""
        self.logger.info(f"=== RUN STARTED for linear channel: {self.channel} ===")
        
        # === START TIME TRACKER THREAD ===
        # This updates self.current_video based on the system clock
        self.tracker_running = True
        tracker_thread = threading.Thread(target=self._track_current_video, daemon=True)
        tracker_thread.start()

        try:
            while self.running:
                # 1. Check if we have videos left to play
                if not self.schedule_entries:
                    self.logger.warning(f"No schedule entries for {self.channel}. Waiting 60s...")
                    time.sleep(60)
                    continue
                    
                if not self.initialize_worker():
                    self.logger.error(f"Failed to initialize worker for {self.channel}. Retrying in 10s...")
                    time.sleep(10)
                    continue
                
                try:
                    # 2. Setup Phase (Uses Simple Logic - no slicing)
                    self._setup_phase()
                    
                    self.logger.info(f"Starting stream for {self.channel}...")
                    self._streaming_phase()
                    
                    # 3. Crash Recovery Logic
                    # If FFmpeg exits with an error code (not 0)
                    if self.running and self.ffmpeg_process and self.ffmpeg_process.returncode != 0:
                        culprit_filename = self.current_video
                        self.logger.error(f"⚠️ Stream crashed on: {culprit_filename}")
                        
                        # Blacklist the bad file so it doesn't play again
                        if culprit_filename != "Unknown":
                            original_count = len(self.schedule_entries)
                            # Remove the culprit from the schedule list
                            self.schedule_entries = [
                                entry for entry in self.schedule_entries 
                                if Path(entry['file']).name != culprit_filename
                            ]
                            removed_count = original_count - len(self.schedule_entries)
                            
                            if removed_count > 0:
                                self.logger.info(f"🚫 Blacklisted '{culprit_filename}'. Removed {removed_count} entry. Retrying next...")
                                time.sleep(5) # Quick restart
                            else:
                                # If filename didn't match any entry (edge case), just wait
                                time.sleep(10)
                        else:
                            time.sleep(10)
                    
                except Exception as e:
                    self._handle_runtime_error(e)
                    time.sleep(10)
                    
                finally:
                    self._cleanup_phase()
        
        finally:
            self.tracker_running = False

        self.logger.info(f"=== RUN FINISHED for linear channel: {self.channel} ===")

    def _track_current_video(self):
        """Background thread that calculates which video should be playing based on time."""
        while self.tracker_running:
            try:
                # Get current time in seconds since midnight
                now = datetime.now()
                seconds_now = (now - datetime(now.year, now.month, now.day)).total_seconds()
                
                # Find the video in the schedule that matches the current time
                # We assume schedule entries are sorted by time
                current_name = "Unknown"
                
                for i, entry in enumerate(self.schedule_entries):
                    try:
                        video_start_time_str = entry.get("time")
                        if not video_start_time_str:
                            continue
                            
                        video_time = datetime.strptime(video_start_time_str, "%H:%M:%S").time()
                        video_seconds = video_time.hour * 3600 + video_time.minute * 60 + video_time.second
                        
                        # If the current time is greater than the video start time,
                        # it's a candidate. We keep going to find the latest one.
                        if seconds_now >= video_seconds:
                            current_name = Path(entry['file']).name
                        
                    except Exception:
                        pass
                
                # Update the parent class variable (used in error logging)
                self.current_video = current_name
                
            except Exception as e:
                self.logger.error(f"Error in time tracker: {e}")
            
            time.sleep(5) # Update every 5 seconds

    def _setup_phase(self):
        """Setup phase: Create temp directory and build playlist (Simple Version)."""
        self.logger.info(f"Entering SETUP phase for {self.channel}...")
        
        self.temp_dir = self._create_temp_directory()
        
        # Simple approach: Assume the passed list is already correct for the current time
        concat_file = self._build_concat_playlist(self.temp_dir)
        
        # Log what we are starting with
        first_name = Path(self.schedule_entries[0]['file']).name if self.schedule_entries else "N/A"
        self.logger.info(f"🎬 Starting Playlist with: {first_name}")
        
        self.logger.info(f"Setup complete. Playlist created at: {concat_file}")
        return concat_file

    def _streaming_phase(self):
        """Streaming phase: Start FFmpeg process and wait."""
        self.logger.info(f"Entering STREAMING phase for {self.channel}...")
        
        concat_file = self.temp_dir / "playlist.txt"
        first_video_path = Path(self.schedule_entries[0]["file"])

        # Update "Now Playing" and "Next Program"
        current_video = self.schedule_entries[0]["file"]
        next_video = self.schedule_entries[1]["file"] if len(self.schedule_entries) > 1 else "N/A"
        self.update_now_next(current_video, next_video)
        
        args = self._build_ffmpeg_args(concat_file, input_path=first_video_path)
        
        # Call _execute_ffmpeg (from BaseWorker)
        # This method now contains the Watchdog and the blocking wait loop
        self._execute_ffmpeg(args)
        
        self.logger.info(f"_execute_ffmpeg has returned for {self.channel}.")

    def _handle_runtime_error(self, error: Exception):
        """Handle any runtime errors during stream execution."""
        self.logger.error(f"An error occurred in the linear stream for {self.channel}: {error}")

    def _cleanup_phase(self):
        """Cleanup phase: Remove temporary files and directories."""
        self.logger.info(f"Entering CLEANUP phase for {self.channel}...")
        
        # Only clean up the temp directory, DO NOT clean up the HLS output directory
        if self.temp_dir and self.temp_dir.exists():
            self.logger.info(f"Cleaning up temp files for {self.channel}...")
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.logger.info(f"Cleanup complete for {self.channel}.")

    def _create_temp_directory(self) -> Path:
        """Create temporary directory for processing."""
        # Use timestamp to ensure unique dir names for restarts
        temp_dir = Path("temp") / f"concat_{self.channel}_{int(time.time())}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    def _build_concat_playlist(self, temp_dir: Path) -> Path:
        """Build the FFmpeg concat playlist file."""
        concat_file = temp_dir / "playlist.txt"
        
        with open(concat_file, "w", encoding='utf-8') as f:
            for i, entry in enumerate(self.schedule_entries):
                if i == 0:
                    file_path = self._process_first_entry(entry, temp_dir)
                else:
                    file_path = Path(entry['file']).resolve().as_posix()
                
                f.write(f"file '{file_path}'\n")
        
        return concat_file

    def _process_first_entry(self, entry: Dict, temp_dir: Path) -> str:
        """Process the first schedule entry with optional trimming."""
        seek_time = self.calculate_seek_time(entry)
        
        if seek_time > 0:
            return self._trim_video(entry['file'], seek_time, temp_dir)
        else:
            return Path(entry['file']).resolve().as_posix()

    def _trim_video(self, video_path: str, seek_time: float, temp_dir: Path) -> str:
        """Trim video to start at the specified seek time."""
        trimmed_path = temp_dir / f"trimmed_{Path(video_path).name}"
        
        trim_process = subprocess.Popen([
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", str(seek_time), 
            "-c", "copy",
            "-avoid_negative_ts", "1",
            trimmed_path.as_posix() 
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        try:
            trim_process.wait(timeout=30)
            if trim_process.returncode != 0:
                self.logger.warning(f"Failed to trim video {video_path}, using original")
                return Path(video_path).resolve().as_posix()
        except subprocess.TimeoutExpired:
            self.logger.error(f"Trimming video {video_path} timed out, using original")
            trim_process.kill()
            return Path(video_path).resolve().as_posix()
        
        return trimmed_path.resolve().as_posix()

    def _build_ffmpeg_args(self, concat_file: Path, input_path: Path) -> List[str]:
        """Build FFmpeg args with either transcoding or copy."""
        args = [
            "ffmpeg", 
            "-v", "verbose",
            "-re", 
            "-fflags", "+genpts+igndts+discardcorrupt", 
            "-threads", "2"
        ]
        args += ["-f", "concat", "-safe", "0", "-i", str(concat_file)]
        
        if self.config.data["output"]["mode"] in ("http_hls", "ram_http"):
            hls_path = self.config.get_hls_output_path(self.channel)
            hls_conf = self.config.data["output"]["hls"]
            playlist_filename = (hls_path.resolve() / "index.m3u8").as_posix()
            
            encoding_args = self.transcoding_service.get_encoding_args(
                input_path=input_path, 
                channel=self.channel
            )

            stream_map = ["-map", "0:v:0?", "-map", "0:a:0?"]
            
            if not self.config.data.get("ffmpeg", {}).get("transcoding", {}).get("enabled"):
                stream_map.append("-sn")

            args.extend([
                *stream_map,
                *encoding_args,
                "-avoid_negative_ts", "make_zero",
                "-metadata", f"title={self.channel}",
                "-f", "hls",
                "-hls_time", str(hls_conf["segment_time"]),
                "-hls_list_size", str(hls_conf["playlist_size"]),
                "-hls_flags", "delete_segments+append_list+omit_endlist",
                "-hls_segment_filename", str(Path(playlist_filename).parent / "seg_%04d.ts"),
                playlist_filename
            ])
        
        return args

    def calculate_seek_time(self, entry: Dict) -> float:
        """Calculate how many seconds into the video we should start."""
        try:
            scheduled_time = datetime.strptime(entry["time"], "%H:%M:%S").time()
            scheduled_dt = datetime.combine(date.today(), scheduled_time)
            current_dt = datetime.now()
            
            if current_dt < scheduled_dt:
                return 0

            offset_seconds = (current_dt - scheduled_dt).total_seconds()
            video_duration = self._get_entry_duration(entry["file"])
            
            if offset_seconds >= video_duration:
                return 0

            return max(0, offset_seconds)
            
        except Exception as e:
            self.logger.error(f"Seek time calculation failed for {entry['file']}: {e}")
            return 0
    
    def _get_entry_duration(self, base_path: str) -> float:
        """Get total duration of a video file."""
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of", "csv=p=0",
                str(base_path)
            ], capture_output=True, text=True, check=True, timeout=10)
            duration = float(result.stdout.strip())
            return duration if duration > 0 else 5400.0
        except Exception as e:
            self.logger.warning(f"Duration fallback for {base_path}: {e}")
            return 5400.0

    def update_now_next(self, current_video: str, next_video: str):
        """Update the global stats for now/next playing."""
        from ..stats import AKIRATV_STATS, STATS_LOCK
        global AKIRATV_STATS
        with STATS_LOCK:
            AKIRATV_STATS["now_playing"] = current_video
            AKIRATV_STATS["next_program"] = next_video