from pathlib import Path
from typing import List, Dict, Optional
from ..inventory import InventoryManager

class TranscodingService:
    """
    A service to build FFmpeg encoding arguments based on a configuration.
    """
    def __init__(self, config, inventory_manager: InventoryManager):
        self.config = config
        self.inventory_manager = inventory_manager

    def get_encoding_args(self, input_path: Path, channel: str, skip_vf: bool = False, force_transcode: bool = False) -> List[str]:
        """
        Build FFmpeg encoding arguments based on transcoding config.
        """
        # 1. Fetch the specific config for this channel
        channel_config = self.config.get_channel_config(channel)
        transcoding_config = channel_config.get("transcoding", self.config.data.get("ffmpeg", {}).get("transcoding", {}))
        
        # Check if transcoding is actually allowed
        transcoding_enabled = transcoding_config.get("enabled", False)

        # If transcoding is OFF (or force_copy is ON), return 'copy' immediately
        if force_transcode is False and not transcoding_enabled:
            return ["-c:v", "copy", "-c:a", "copy"]

        # 2. Proceed with full transcoding logic if enabled
        args = []
        
        # Video encoder
        encoder = transcoding_config.get("encoder", "auto")
        if encoder == "cpu" or encoder == "auto":
            args.extend(["-c:v", "libx264"])
        elif encoder == "nvenc":
            args.extend(["-c:v", "h264_nvenc"])
        elif encoder == "qsv":
            args.extend(["-c:v", "h264_qsv"])
        elif encoder == "amf":
            args.extend(["-c:v", "h264_amf"])
        
        # Video quality / scaling
        video_quality = transcoding_config.get("video_quality", "source")
        if video_quality != "source" and not skip_vf:
            args.extend(["-vf", f"scale={video_quality}"])
        
        # Bitrate logic
        bitrate = transcoding_config.get("bitrate", "auto")
        custom_bitrate = transcoding_config.get("custom_bitrate", "1500k")
        
        if bitrate == "auto":
            video_bitrate = self.inventory_manager.get_source_bitrate(str(input_path))
        elif bitrate == "custom":
            video_bitrate = custom_bitrate
        else:
            video_bitrate = bitrate
        
        args.extend(["-b:v", video_bitrate])
        
        # Frame rate logic - FIXED
        fps = transcoding_config.get("fps", "auto")
        if fps != "auto":
            # If fps is a specific value (not "auto"), use it
            args.extend(["-r", str(fps)])
        # If fps is "auto", we don't add -r flag, letting FFmpeg use source fps
        
        # Threads logic
        threads = transcoding_config.get("threads", "2")
        if threads != "auto":
            args.extend(["-threads", str(threads)])
        
        # Audio logic
        audio_quality = transcoding_config.get("audio_quality", "copy")
        if audio_quality == "copy":
            args.extend(["-c:a", "copy"])
        else:
            b_audio = audio_quality.split("_")[1] if "_" in audio_quality else "128k"
            args.extend(["-c:a", "aac", "-b:a", b_audio])
        
        return args