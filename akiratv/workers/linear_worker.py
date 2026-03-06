import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, date
from .base_worker import BaseWorker


class LinearWorker(BaseWorker):
    def __init__(self, channel: str, schedule_entries: List[Dict], config, logger, transcoding_service):
        super().__init__(channel, config, logger)
        self.schedule_entries = schedule_entries
        self.transcoding_service = transcoding_service
    
    def update_schedule(self, new_schedule_entries: List[Dict]):
        """Update schedule entries in-place without restarting the stream."""
        old_count = len(self.schedule_entries) if self.schedule_entries else 0
        self.schedule_entries = new_schedule_entries
        self.logger.info(f"Schedule updated in-place: {old_count} -> {len(new_schedule_entries)} entries")
        self.temp_dir: Optional[Path] = None

    def run(self):
        """Main execution orchestrator for a linear channel."""
        self.logger.info(f"=== RUN STARTED for linear channel: {self.channel} ===")
        
        if not self._validate_prerequisites():
            return
        
        try:
            self._setup_phase()
            self._streaming_phase()
            self._monitoring_phase()
        except Exception as e:
            self._handle_runtime_error(e)
        finally:
            self._cleanup_phase()

    def _validate_prerequisites(self) -> bool:
        """Validate that all prerequisites are met before starting."""
        if not self.schedule_entries:
            self.logger.warning(f"No schedule entries for linear channel {self.channel}. Aborting.")
            return False
            
        if not self.initialize_worker():
            self.logger.error(f"Failed to initialize worker for {self.channel}. Aborting.")
            return False
        
        return True

    def _setup_phase(self):
        """Setup phase: Create temp directory and build playlist."""
        self.logger.info(f"Entering SETUP phase for {self.channel}...")
        
        self.temp_dir = self._create_temp_directory()
        concat_file = self._build_concat_playlist(self.temp_dir)
        
        self.logger.info(f"Setup complete. Playlist created at: {concat_file}")
        return concat_file

    def _create_temp_directory(self) -> Path:
        """Create temporary directory for processing."""
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
        
        self.logger.info(f"First video seek time calculated: {seek_time:.2f} seconds")
        
        if seek_time > 0:
            trimmed_path = self._trim_video(entry['file'], seek_time, temp_dir)
            self.logger.info(f"First video trimmed to start at {seek_time:.2f}s")
            return trimmed_path
        else:
            self.logger.info(f"First video starts from beginning (no trim needed)")
            return Path(entry['file']).resolve().as_posix()

    def _trim_video(self, video_path: str, seek_time: float, temp_dir: Path) -> str:
        """Trim video to start at the specified seek time."""
        trimmed_path = temp_dir / f"trimmed_{Path(video_path).name}"
        
        #self.logger.info(f"Trimming {video_path} starting at {seek_time:.2f}s...")
        self.logger.info(f"✂️ Trimming {Path(video_path).name} starting at {seek_time:.2f}s...")
        
        trim_process = subprocess.Popen([
            "ffmpeg", "-y",
            "-ss", str(seek_time),
            "-i", video_path,
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            str(trimmed_path)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        
        try:
            _, stderr = trim_process.communicate(timeout=30)
            if trim_process.returncode != 0:
                self.logger.warning(f"Failed to trim video {video_path}, using original")
                self.logger.debug(f"Trim stderr: {stderr}")
                return Path(video_path).resolve().as_posix()
            self.logger.info(f"Successfully trimmed video")
        except subprocess.TimeoutExpired:
            self.logger.error(f"Trimming video {video_path} timed out, using original")
            trim_process.kill()
            return Path(video_path).resolve().as_posix()
        
        return trimmed_path.resolve().as_posix()

    def _streaming_phase(self):
        """Streaming phase: Start FFmpeg process."""
        self.logger.info(f"Entering STREAMING phase for {self.channel}...")
        
        concat_file = self.temp_dir / "playlist.txt"
        first_video_path = Path(self.schedule_entries[0]["file"])
        
        args = self._build_ffmpeg_args(concat_file, input_path=first_video_path)
        
        self.logger.info(f"Starting FFmpeg stream for {self.channel}...")
        self._execute_ffmpeg(args)
        self.logger.info(f"FFmpeg stream ended for {self.channel}.")

    def _monitoring_phase(self):
        """Monitoring phase: Keep the stream alive and monitor status."""
        self.logger.info(f"Entering MONITORING loop for {self.channel}...")
        
        while self.running and self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            time.sleep(0.5)
        
        self.logger.info(f"MONITORING loop has ended for {self.channel}.")
        self._check_ffmpeg_status()

    def _check_ffmpeg_status(self):
        """Check FFmpeg process exit status and log errors if any."""
        if self.ffmpeg_process and self.ffmpeg_process.returncode != 0:
            self.logger.error(f"FFmpeg exited with code {self.ffmpeg_process.returncode} for {self.channel}")

    def _handle_runtime_error(self, error: Exception):
        """Handle any runtime errors during stream execution."""
        self.logger.error(f"An error occurred in the linear stream for {self.channel}: {error}")

    def _cleanup_phase(self):
        """Cleanup phase: Remove temporary files and directories."""
        self.logger.info(f"Entering CLEANUP phase for {self.channel}...")
        
        if self.temp_dir and self.temp_dir.exists():
            self.logger.info(f"Cleaning up temp files for {self.channel}...")
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.logger.info(f"Cleanup complete for {self.channel}.")
        
        self.logger.info(f"Linear stream for {self.channel} has ended.")

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
            # Check if this is a Fast Scheduler entry with pre-calculated resume position
            if "resume_position" in entry:
                resume_pos = float(entry["resume_position"])
                self.logger.info(f"Using Fast Scheduler resume position: {resume_pos:.2f}s")
                return max(0, resume_pos)
            
            # Traditional schedule entry - calculate based on time
            scheduled_time = datetime.strptime(entry["time"], "%H:%M:%S").time()
            scheduled_dt = datetime.combine(date.today(), scheduled_time)
            current_dt = datetime.now()
            
            if current_dt < scheduled_dt:
                self.logger.info(f"Current time is before scheduled time, starting from beginning")
                return 0

            offset_seconds = (current_dt - scheduled_dt).total_seconds()
            video_duration = self._get_entry_duration(entry["file"])
            
            self.logger.info(f"Time offset: {offset_seconds:.2f}s, Video duration: {video_duration:.2f}s")
            
            if offset_seconds >= video_duration:
                self.logger.warning(f"Offset exceeds video duration, starting from beginning")
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