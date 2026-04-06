"""
Video Position Manager for AkiraTV
Manages saved playback positions for VOD videos to enable resume functionality.
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional

# Storage file path
VIDEO_POSITIONS_FILE = Path("user/video_positions.json")


def _ensure_storage_dir():
    """Ensure the user directory exists."""
    VIDEO_POSITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_positions() -> Dict[str, float]:
    """
    Load all saved video positions from storage.
    
    Returns:
        Dictionary mapping video paths to position in seconds
    """
    _ensure_storage_dir()
    
    if not VIDEO_POSITIONS_FILE.exists():
        return {}
    
    try:
        with open(VIDEO_POSITIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Ensure all values are floats
            return {k: float(v) for k, v in data.items()}
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading video positions: {e}")
        return {}


def save_positions(positions: Dict[str, float]) -> bool:
    """
    Save all video positions to storage.
    
    Args:
        positions: Dictionary mapping video paths to position in seconds
        
    Returns:
        True if successful, False otherwise
    """
    _ensure_storage_dir()
    
    try:
        with open(VIDEO_POSITIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(positions, f, indent=2)
        return True
    except IOError as e:
        print(f"Error saving video positions: {e}")
        return False


def get_position(video_path: str) -> Optional[float]:
    """
    Get the saved position for a specific video.
    
    Args:
        video_path: Full path to the video file
        
    Returns:
        Position in seconds, or None if not found
    """
    positions = load_positions()
    return positions.get(video_path)


def save_position(video_path: str, position_seconds: float) -> bool:
    """
    Save the playback position for a video.
    
    Args:
        video_path: Full path to the video file
        position_seconds: Position in seconds
        
    Returns:
        True if successful, False otherwise
    """
    positions = load_positions()
    positions[video_path] = float(position_seconds)
    return save_positions(positions)


def remove_position(video_path: str) -> bool:
    """
    Remove the saved position for a video.
    
    Args:
        video_path: Full path to the video file
        
    Returns:
        True if successful, False otherwise
    """
    positions = load_positions()
    if video_path in positions:
        del positions[video_path]
        return save_positions(positions)
    return True


def clear_all_positions() -> bool:
    """
    Clear all saved video positions.
    
    Returns:
        True if successful, False otherwise
    """
    return save_positions({})


def cleanup_missing_videos() -> int:
    """
    Remove positions for videos that no longer exist.
    
    Returns:
        Number of positions removed
    """
    positions = load_positions()
    original_count = len(positions)
    
    # Filter out positions for videos that don't exist
    cleaned_positions = {
        path: pos 
        for path, pos in positions.items() 
        if Path(path).exists()
    }
    
    # Save only existing video positions
    if len(cleaned_positions) != original_count:
        save_positions(cleaned_positions)
    
    return original_count - len(cleaned_positions)
