from pathlib import Path
from typing import List
from .base_worker import BaseWorker
from akiratv.collections import FFMPEG_PATH


class LiveWorker(BaseWorker):
    def __init__(self, channel: str, config, logger, transcoding_service, port: int):
        super().__init__(channel, config, logger)
        self.port = port
        self.transcoding_service = transcoding_service
        self.stream_url = f"tcp://0.0.0.0:{port}?listen=1"

    def run(self):
        self.logger.info(f"=== RUN STARTED for live channel: {self.channel} ===")

        if not self.initialize_worker():
            return

        self.logger.info(f"Live worker for {self.channel} listening on port {self.port}")
        self.logger.info(f"OBS should connect to: tcp://127.0.0.1:{self.port}")

        args = self._build_ffmpeg_args()
        self._execute_ffmpeg(args, enable_watchdog=False)

        self.logger.info(f"Live worker for {self.channel} stopped (OBS disconnected).")

    def _build_ffmpeg_args(self) -> List[str]:
        hls_path = self.config.get_hls_output_path(self.channel)
        hls_conf = self.config.data["output"]["hls"]
        playlist = (hls_path / "index.m3u8").as_posix()

        encoding_args = self.transcoding_service.get_encoding_args(
            input_path=None, channel=self.channel
        )

        args = [
            FFMPEG_PATH,
            "-v", "verbose",
            "-i", self.stream_url,
            "-map", "0:v:0?", "-map", "0:a:0?",
            *encoding_args,
            "-f", "hls",
            "-hls_time", str(hls_conf["segment_time"]),
            "-hls_list_size", str(hls_conf["playlist_size"]),
            "-hls_flags", "delete_segments+append_list+omit_endlist",
            "-hls_segment_filename", str(hls_path / "seg_%04d.ts"),
            playlist
        ]
        return args
