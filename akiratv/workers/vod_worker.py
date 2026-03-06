# akiratv/workers/vod_worker.py
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict
from .base_worker import BaseWorker

class VODWorker(BaseWorker):
    def __init__(self, channel: str, config, logger, transcoding_service, command_queue):
        super().__init__(channel, config, logger)
        self.transcoding_service = transcoding_service
        self.command_queue = command_queue
        self.use_dynamic_playlist = True  # A flag to identify this worker type
        self.video_to_play = None
        self.current_video = None  # Track currently playing video
        self.temp_dir: Optional[Path] = None
        self.hls_dir: Optional[Path] = None

    def run(self):
        """Main execution for a VOD channel."""
        if not self.initialize_worker():
            return
        
        self.logger.info(f"VOD channel '{self.channel}' is running and waiting for commands.")
        while self.running:
            # Check for a new command from the queue
            try:
                # Get a command with a timeout so the loop doesn't block forever
                cmd, video_path = self.command_queue.get(timeout=0.5)
                if cmd == "play_now" and video_path:
                    self.logger.info(f"Received 'play_now' command for: {video_path}")
                    self.video_to_play = video_path  # Set the flag
            except:
                # No command received in the timeout period, just loop again
                pass

            # If a video has been requested, play it
            if self.video_to_play:
                self.current_video = self.video_to_play  # Track currently playing video
                self._play_video(self.video_to_play)
                self.video_to_play = None  # Reset the flag
                self.current_video = None  # Video finished playing
            else:
                # Nothing to do, just wait
                time.sleep(1)

    def _play_video(self, video_path: str):
        """Orchestrates the video playback process."""
        try:
            self._setup_phase(video_path)
            self._streaming_phase(video_path)
            self._monitoring_phase()
        except Exception as e:
            self._handle_runtime_error(e)
        finally:
            self._cleanup_phase()

    def _setup_phase(self, video_path: str):
        """Setup phase: Create temp directory and prepare for streaming."""
        self.logger.info(f"Entering SETUP phase for {self.channel}...")
        
        # Create temporary directory for HLS segments
        self.temp_dir = self._create_temp_directory()
        
        # Get the actual HLS output directory
        self.hls_dir = self.config.get_hls_output_path(self.channel)
        
        # Clean up old segments in the actual HLS directory
        self._cleanup_hls_directory()
        
        self.logger.info(f"Setup complete. Using temp directory: {self.temp_dir}")

    def _create_temp_directory(self) -> Path:
        """Create temporary directory for processing."""
        storage = self.config.data.get("storage", {})
        
        if storage.get("type") == "ram":
            # For RAM storage, create a temp directory on disk first
            temp_dir = Path(tempfile.mkdtemp(prefix=f"akiratv_{self.channel}_"))
        else:
            # For disk storage, create a temp directory in the output path
            temp_dir = self.config.get_output_root() / f"temp_{self.channel}_{int(time.time())}"
            temp_dir.mkdir(parents=True, exist_ok=True)
        
        return temp_dir

    def _cleanup_hls_directory(self):
        """Clean up old segments in the HLS directory."""
        if self.hls_dir and self.hls_dir.exists():
            for f in self.hls_dir.glob("*"):
                try:
                    f.unlink()
                except Exception as e:
                    self.logger.warning(f"Failed to delete {f}: {e}")

    def _streaming_phase(self, video_path: str):
        """Streaming phase: Start FFmpeg process."""
        self.logger.info(f"Entering STREAMING phase for {self.channel}...")
        
        args = self._build_ffmpeg_args(video_path)
        
        self.logger.info(f"Calling _execute_ffmpeg for {self.channel}...")
        self._execute_ffmpeg(args)
        self.logger.info(f"_execute_ffmpeg has returned for {self.channel}.")

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
            error_msg = self.ffmpeg_process.stderr.read() if self.ffmpeg_process.stderr else "Unknown error"
            self.logger.error(f"FFmpeg failed for {self.channel}: {error_msg}")

    def _handle_runtime_error(self, error: Exception):
        """Handle any runtime errors during stream execution."""
        self.logger.error(f"An error occurred in the VOD stream for {self.channel}: {error}")

    def _cleanup_phase(self):
        """Cleanup phase: Remove temporary files and directories."""
        self.logger.info(f"Entering CLEANUP phase for {self.channel}...")
        
        # Clean up temp directory
        if self.temp_dir and self.temp_dir.exists():
            self.logger.info(f"Cleaning up temp files for {self.channel}...")
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.logger.info(f"Cleanup complete for {self.channel}.")
        
        self.logger.info(f"VOD stream for {self.channel} has ended.")

    def _build_ffmpeg_args(self, video_path: str) -> List[str]:
        """Build FFmpeg arguments for VOD streaming."""
        # Get CHANNEL-SPECIFIC config (respects overrides!)
        channel_config = self.config.get_channel_config(self.channel)
        transcoding_config = channel_config.get("transcoding", {})
        subtitles_enabled = channel_config.get("enable_subtitles", True)
        
        self.logger.info(f"Channel '{self.channel}' transcoding: {transcoding_config.get('enabled')}")
        self.logger.info(f"Channel '{self.channel}' subtitles: {subtitles_enabled}")

        # Find optional external subtitle (only if enabled)
        subtitle_path = self._find_external_subtitle(Path(video_path)) if subtitles_enabled else None

        # HLS config
        hls_conf = self.config.data["output"]["hls"]
        segment_time = hls_conf.get("segment_time", 6)

        # Build FFmpeg command
        args = ["ffmpeg", "-re", "-i", str(video_path)]
        self.logger.info(f"Input video: {video_path}")
        self.logger.info(f"Subtitle file: {subtitle_path}")

        # Add subtitle input if exists
        if subtitle_path:
            args.extend(["-i", str(subtitle_path)])

        # Stream mapping
        args.extend([
            "-map", "0:v:0",
            "-map", "0:a?"
        ])

        # Determine if we need transcoding
        video_quality = transcoding_config.get("video_quality", "source")
        needs_scaling = video_quality != "source"
        
        # CRITICAL FIX: Only force transcoding if BOTH transcoding AND subtitles are enabled
        force_transcode_for_subs = subtitle_path is not None and transcoding_config.get("enabled", False) and subtitles_enabled
        
        # Final decision: transcode only if explicitly enabled OR if scaling needed
        use_transcoding = transcoding_config.get("enabled", False) and (force_transcode_for_subs or needs_scaling)
        
        self.logger.info(f"Will transcode: {use_transcoding} (enabled={transcoding_config.get('enabled')}, subs={bool(subtitle_path)}, scaling={needs_scaling})")

        # Build video filter chain (only if transcoding)
        if use_transcoding and subtitle_path:
            base_font = 28
            base_height = 1080
            font_size = int(transcoding_config.get("subtitle_font_size", base_font))
            
            if needs_scaling:
                try:
                    width, height = map(int, video_quality.split("x"))
                    output_height = height
                except Exception as e:
                    self.logger.warning(f"Failed to parse video_quality '{video_quality}': {e}")
                    output_height = base_height
            else:
                output_height = base_height

            scaled_font_size = int(font_size * (output_height / base_height))
            scaled_font_size = max(10, min(scaled_font_size, 48))
            self.logger.info(f"Subtitle font size computed: {scaled_font_size}")

            safe_sub = subtitle_path.as_posix().replace(":", "\\:")
            vf_chain = [f"subtitles='{safe_sub}':force_style='Fontsize={scaled_font_size}'"]

            if needs_scaling:
                vf_chain.append(f"scale=-2:{output_height}")
                self.logger.info(f"Applying scale filter for output: {video_quality}")

            args.extend(["-vf", ",".join(vf_chain)])
        elif use_transcoding and needs_scaling:
            # Scaling without subtitles
            try:
                width, height = map(int, video_quality.split("x"))
                args.extend(["-vf", f"scale=-2:{height}"])
                self.logger.info(f"Applying scale filter (no subs): {video_quality}")
            except Exception as e:
                self.logger.warning(f"Failed to parse video_quality '{video_quality}': {e}")

        # Disable subtitle stream if not using them
        if not subtitle_path or not use_transcoding:
            args.append("-sn")

        # Get encoding arguments from the transcoding service
        if use_transcoding:
            # We force transcoding because we've already decided we need it
            encoding_args = self.transcoding_service.get_encoding_args(Path(video_path), channel=self.channel, force_transcode=True)
            self.logger.info("Using transcoding (quality mode)")
        else:
            # We force copy because we've decided we don't need to transcode
            encoding_args = self.transcoding_service.get_encoding_args(Path(video_path), channel=self.channel, force_transcode=False)
            self.logger.info("Using stream copy (fast mode - 0% CPU)")

        args.extend(encoding_args)

        # HLS output - use temp directory for segments
        temp_playlist = str(self.temp_dir / "index.m3u8")
        args.extend([
            "-avoid_negative_ts", "make_zero",
            "-f", "hls",
            "-hls_time", str(segment_time),
            "-hls_list_size", "10",  # Increased from 3 to 10
            "-hls_flags", "delete_segments+append_list+omit_endlist",
            "-hls_segment_filename", str(self.temp_dir / "seg_%04d.ts"),
            temp_playlist
        ])

        # Start a thread to copy segments from temp to actual HLS directory
        self._start_segment_copy_thread()

        self.logger.info("Starting FFmpeg for VOD channel:")
        self.logger.info(" ".join(args))

        return args

    def _start_segment_copy_thread(self):
        """Start a thread to copy segments from temp directory to HLS directory and manage deletion."""
        def copy_and_manage_segments():
            segment_files = {}  # Dictionary to track segment files and their modification times
            
            while self.running:
                try:
                    # Copy playlist file if it exists
                    temp_playlist = self.temp_dir / "index.m3u8"
                    if temp_playlist.exists():
                        shutil.copy2(temp_playlist, self.hls_dir / "index.m3u8")
                    
                    # Get the current playlist to determine which segments should be kept
                    playlist_content = ""
                    if (self.hls_dir / "index.m3u8").exists():
                        with open(self.hls_dir / "index.m3u8", "r") as f:
                            playlist_content = f.read()
                    
                    # Copy new segment files and track them
                    for segment_file in self.temp_dir.glob("seg_*.ts"):
                        dest_file = self.hls_dir / segment_file.name
                        
                        # Copy if new or updated
                        if not dest_file.exists() or segment_file.stat().st_mtime > dest_file.stat().st_mtime:
                            shutil.copy2(segment_file, dest_file)
                            self.logger.debug(f"Copied segment {segment_file.name}")
                        
                        # Track the segment
                        segment_files[segment_file.name] = segment_file.stat().st_mtime
                    
                    # Delete old segments not in the current playlist
                    # Keep only the last 10 segments
                    if len(segment_files) > 10:
                        # Sort by modification time (oldest first)
                        sorted_segments = sorted(segment_files.items(), key=lambda x: x[1])
                        
                        # Delete the oldest segments beyond the 10 most recent
                        for segment_name, _ in sorted_segments[:-10]:
                            segment_path = self.hls_dir / segment_name
                            if segment_path.exists():
                                segment_path.unlink()
                                self.logger.debug(f"Deleted old segment {segment_name}")
                                del segment_files[segment_name]
                    
                    time.sleep(0.5)  # Check every 0.5 seconds
                except Exception as e:
                    self.logger.error(f"Error managing segments: {e}")
                    time.sleep(1)  # Wait a bit longer if there's an error
        
        copy_thread = threading.Thread(target=copy_and_manage_segments, daemon=True)
        copy_thread.start()

    def play_now(self, video_path: str):
        """Public method to queue a play_now command. Should not be called directly by UI."""
        self.command_queue.put(("play_now", video_path))

    def _find_external_subtitle(self, video_path: Path) -> Optional[Path]:
        """
        Looks for an external subtitle file with the same name as the video.
        Checks for common extensions like .srt, .sub, .ass.
        """
        channel_config = self.config.get_channel_config(self.channel)
        if not channel_config.get("enable_subtitles", True):
            return None  # Subtitles are disabled for this channel

        video_dir = video_path.parent
        video_name = video_path.stem
        common_extensions = [".srt", ".sub", ".ass", ".vtt"]
        
        for ext in common_extensions:
            subtitle_path = video_dir / f"{video_name}{ext}"
            if subtitle_path.exists():
                self.logger.info(f"Found external subtitle: {subtitle_path}")
                return subtitle_path
        
        self.logger.info(f"No external subtitle found for {video_path}")
        return None