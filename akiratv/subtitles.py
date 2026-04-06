# akiratv/subtitles.py
from pathlib import Path
from typing import Optional

def find_subtitle(video_path: Path) -> Optional[Path]:
    srt = video_path.with_suffix(".srt")
    if srt.exists():
        return srt
    return None