# akiratv/playlist.py
from pathlib import Path

def build_ffmpeg_concat_file(video_paths: list[Path], output_txt: Path):
    with open(output_txt, "w", encoding="utf-8") as f:
        for p in video_paths:
            # 🔑 Use raw string with forward slashes (FFmpeg prefers this)
            f.write(f"file '{p.resolve().as_posix()}'\n")