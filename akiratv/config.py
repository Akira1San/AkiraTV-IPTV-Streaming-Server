# akiratv/config.py
import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("AkiraTV")

USER_ROOT = Path("user")
USER_CHANNELS_DIR = USER_ROOT / "channels"

DEFAULT_CONFIG = {
    "ffmpeg": {
        "bin_dir": None,
        "hwaccel": "cuda",
        "enable_subtitles": False,
        "transcoding": {
            "enabled": False,
            "bitrate": "auto",
            "custom_bitrate": "1500k",
            "video_quality": "source",
            "encoder": "auto",
            "audio_quality": "copy",
            "fps": "auto",
            "threads": "2",
            "subtitle_font_size": "28"
        }
    },
    "storage": {
        "type": "disk",
        "ram_path": "./output",
        "disk_path": "./output"
    },
    "output": {
        "mode": "http_hls",
        "http": {
            "port": 8081,
            "bind": "0.0.0.0"
        },
        "hls": {
            "segment_time": 6,
            "playlist_size": 4
        }
    },
    "streaming": {
        "strategy": "concat",
        "mode": "static",
        "pre_gen": True
    },
    "channels": {
        "myAkiraTV": {
            "enabled": True,
            "type": "linear"
        },
        "live": {
            "enabled": True,
            "type": "vod"
        }
    },
    "worker": {
        "auto_restart_ffmpeg": True,
        "max_ram_usage_percent": 80
    },
    "ui": {
        "dark_mode": False
    }
}

class Config:
    def __init__(self, data: dict):
        self.data = data

    @staticmethod
    def default_config() -> dict:
        """Returns a copy of the default configuration dictionary."""
        import copy
        return copy.deepcopy(DEFAULT_CONFIG)

    @classmethod
    def load_or_create(cls, path: str = "config.json") -> "Config":
        """
        Load existing config or create default.
        Returns Config instance - does NOT exit!
        """
        if not os.path.exists(path):
            logger.info(f"No config found at {path}, creating default...")
            cls._write_default(path)
            logger.info(f"[OK] Created default config at {path}")
            logger.info("You can edit this file and reload without restarting the server.")
            # Return the default config instead of exiting
            return cls(cls.default_config())
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Only log config load once or when in debug mode
            logger.debug(f"[OK] Loaded config from {path}")
            return cls(cls._merge_with_defaults(data))
        except json.JSONDecodeError as e:
            logger.error(f"[ERROR] Invalid JSON in {path}: {e}")
            logger.info("Using default config instead")
            return cls(cls.default_config())
        except Exception as e:
            logger.error(f"[ERROR] Failed to load config: {e}")
            logger.info("Using default config instead")
            return cls(cls.default_config())

    @staticmethod
    def _merge_with_defaults(user_data: dict) -> dict:
        """Deep merge user config with defaults"""
        import copy
        
        def deep_merge(base, override):
            merged = copy.deepcopy(base)
            for k, v in override.items():
                if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
                    merged[k] = deep_merge(merged[k], v)
                else:
                    merged[k] = v
            return merged
        
        return deep_merge(DEFAULT_CONFIG, user_data)

    @staticmethod
    def _write_default(path: str):
        """Write default config to file"""
        with open(path, "w", encoding="utf-8") as f:
            example = {
                "__comment__": "AkiraTV Configuration - Edit values below and save",
                **DEFAULT_CONFIG
            }
            json.dump(example, f, indent=2)

    def save(self, path: str = "config.json"):
        """Save current config to file"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
        logger.info(f"[OK] Config saved to {path}")

    def get_channel_config(self, channel: str) -> dict:
        """Get merged config for a specific channel"""
        base = self.data["ffmpeg"].copy()
        overrides = self.data["channels"].get(channel, {})
        base.update(overrides)
        return base

    def get_ffmpeg_bin_dir(self) -> str | None:
        """Return bin_dir from config, or None if not set."""
        ffmpeg_section = self.data.get("ffmpeg", {})
        return ffmpeg_section.get("bin_dir") or None

    def get_hwaccel(self, channel: str) -> str:
        """Get hardware acceleration setting for channel"""
        return self.get_channel_config(channel).get("hwaccel", "none")

    def subtitles_enabled(self, channel: str) -> bool:
        """Check if subtitles are enabled for channel"""
        return self.get_channel_config(channel).get("enable_subtitles", True)

    def get_hls_output_path(self, channel: str) -> Path:
        """Get HLS output path for a specific channel"""
        mode = self.data["output"]["mode"]
        if mode == "ram_http":
            ram_path = self.data["storage"].get("ram_path")
            if not ram_path:
                raise ValueError("RAM mode selected but ram_path not set")
            return Path(ram_path) / channel
        else:
            disk_path = self.data["storage"].get("disk_path", "./output")
            return Path(disk_path) / channel

    def get_output_root(self) -> Path:
        """
        Returns the root output directory (RAM or disk),
        without appending channel name.
        """
        mode = self.data["output"]["mode"]
        if mode == "ram_http":
            ram_path = self.data["storage"].get("ram_path")
            if not ram_path:
                raise ValueError("RAM mode selected but ram_path not set")
            return Path(ram_path)
        else:
            disk_path = self.data["storage"].get("disk_path", "./output")
            return Path(disk_path)