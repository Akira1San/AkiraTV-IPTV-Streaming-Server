# akiratv/storage.py
from pathlib import Path
import os

def ensure_hls_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    # If RAM disk, ensure it's writable
    test_file = path / ".akiratv_test"
    try:
        test_file.write_text("ok")
        test_file.unlink()
    except OSError as e:
        raise RuntimeError(f"Storage path not writable: {path}") from e