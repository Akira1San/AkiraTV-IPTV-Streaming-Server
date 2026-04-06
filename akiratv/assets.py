# akiratv/assets.py
from pathlib import Path
import shutil

def sync_channel_logos(user_channels_dir: Path, output_root: Path):
    """
    Copy channel logos from user folder into output storage.
    """
    output_channels = output_root / "channels"
    output_channels.mkdir(parents=True, exist_ok=True)

    if not user_channels_dir.exists():
        return

    for channel_dir in user_channels_dir.iterdir():
        img = channel_dir / "logo.png"
        if not img.exists():
            continue

        target_dir = output_channels / channel_dir.name
        target_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(img, target_dir / "logo.png")
