# akiratv/daypart_scheduler.py
"""
Daypart Scheduler for AkiraTV

Provides broadcast-style scheduling with time blocks, marathons, and gap filling.
"""

import json
import random
import uuid
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger("AkiraTV")

# Base directory setup
BASE_DIR = Path(__file__).resolve().parents[1]
USER_DIR = BASE_DIR / "user"
SCHEDULE_DIR = USER_DIR / "schedules"
SCHEDULE_DIR.mkdir(parents=True, exist_ok=True)

# Episodic state: tracks which episode index each block is at across days
EPISODIC_STATE_DIR = USER_DIR / "episodic_state"
EPISODIC_STATE_DIR.mkdir(parents=True, exist_ok=True)


def _load_episodic_state(channel: str) -> dict:
    """Load the episodic episode-index state for a channel."""
    state_file = EPISODIC_STATE_DIR / f"{channel}_episodic_state.json"
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_episodic_state(channel: str, state: dict):
    """Persist the episodic episode-index state for a channel."""
    state_file = EPISODIC_STATE_DIR / f"{channel}_episodic_state.json"
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.warning(f"[{channel}] Could not save episodic state: {e}")

# Approximate timing utilities live in a separate module
from .daypart_approximate import (
    approximate_block_timing,
    approximate_block_timing_v2,
    apply_approximate_snapping as _apply_approximate_snapping,
)


def parse_time_string(time_str: str) -> datetime:
    """
    Parse a time string in HH:MM format.
    Handles special case of "24:00" which represents midnight (next day).
    
    Args:
        time_str: Time string like "06:00" or "24:00"
    
    Returns:
        datetime object (date component is arbitrary, usually 1900-01-01)
    """
    if time_str == "24:00":
        # Return 00:00 of next day
        return datetime.strptime("00:00", "%H:%M") + timedelta(days=1)
    return datetime.strptime(time_str, "%H:%M")


def format_time_string(dt: datetime) -> str:
    """Format datetime to HH:MM string, handling 24:00 case"""
    if dt.hour == 0 and dt.minute == 0 and dt.day != 1:
        # Represent midnight as 24:00 if it's the next day
        return "24:00"
    return dt.strftime("%H:%M")


# ============================================================================
# DATA CLASSES
# ============================================================================

class TimeBlock:
    """
    Represents a scheduled time block with specific content.
    
    Args:
        start_time: "HH:MM" format (24-hour)
        end_time: "HH:MM" format (24-hour)
        content_type: "video" or "tag"
        content_value: 
            - If type="video": full video path
            - If type="tag": tag name
        block_id: unique identifier (auto-generated if None)
    """
    def __init__(self, start_time: str, end_time: str, 
                 content_type: str, content_value: str, 
                 block_id: str = None, days: list = None, video_count: str = None,
                 approximate: bool = False):
        self.block_id = block_id or f"block_{uuid.uuid4().hex[:8]}"
        self.start_time = start_time
        self.end_time = end_time
        self.content_type = content_type  # "video" or "tag"
        self.content_value = content_value
        self.days = days or []  # List of days for tag blocks
        self.video_count = video_count  # "single", "2", "3", "all", etc.
        self.approximate = approximate  # Whether timing was approximated
        
    def __repr__(self):
        return f"TimeBlock({self.start_time}-{self.end_time}, {self.content_type}={self.content_value})"
    
    @property
    def duration_seconds(self) -> int:
        """Calculate block duration in seconds"""
        start_dt = parse_time_string(self.start_time)
        end_dt = parse_time_string(self.end_time)
        if end_dt < start_dt:
            # Handle overnight blocks (e.g., 22:00-02:00) - NOT allowed for daypart blocks
            # But we calculate anyway for validation
            end_dt += timedelta(days=1)
        return int((end_dt - start_dt).total_seconds())
    
    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        result = {
            "block_id": self.block_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "content_type": self.content_type,
            "content_value": self.content_value,
            "duration_seconds": self.duration_seconds
        }
        if self.days:
            result["days"] = self.days
        if self.video_count:
            result["video_count"] = self.video_count
        if self.approximate:
            result["approximate"] = self.approximate
        collection_file = getattr(self, 'collection_file', None)
        if collection_file:
            result["collection_file"] = collection_file
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TimeBlock':
        """Deserialize from dictionary"""
        block = cls(
            start_time=data["start_time"],
            end_time=data["end_time"],
            content_type=data["content_type"],
            content_value=data["content_value"],
            block_id=data.get("block_id"),
            days=data.get("days", []),
            video_count=data.get("video_count"),
            approximate=data.get("approximate", False)
        )
        if "collection_file" in data:
            block.collection_file = data["collection_file"]
        return block


class MarathonConfig:
    """
    Configuration for a 24-hour marathon on specific days.
    
    Args:
        tag: Tag name to marathon
        days: List of weekday names ["monday", "friday", ...]
        enabled: Whether this marathon is active
        shuffle: Randomize order within the 24h period
        no_repeat_24h: Don't repeat videos within 24 hours
    """
    def __init__(self, tag: str, days: list, enabled: bool = True,
                 shuffle: bool = True, no_repeat_24h: bool = True):
        self.tag = tag
        self.days = days  # List of weekday strings
        self.enabled = enabled
        self.shuffle = shuffle
        self.no_repeat_24h = no_repeat_24h
    
    def __repr__(self):
        return f"MarathonConfig({self.tag} on {self.days})"
    
    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "days": self.days,
            "enabled": self.enabled,
            "shuffle": self.shuffle,
            "no_repeat_24h": self.no_repeat_24h
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MarathonConfig':
        return cls(
            tag=data["tag"],
            days=data.get("days", []),
            enabled=data.get("enabled", True),
            shuffle=data.get("shuffle", True),
            no_repeat_24h=data.get("no_repeat_24h", True)
        )


class GapFillerConfig:
    """
    Configuration for filling unscheduled time gaps.
    
    Args:
        enabled: Enable automatic gap filling
        source: "all", "collections", or "tags"
        collection_ids: List of collection IDs to use when source="collections"
        tags: List of tags to use when source="tags"
        excluded_tags: List of tags to exclude from gap filling
        respect_24h_norepeat: Apply 24-hour no-repeat rule
        shuffle: Randomize selection
    """
    def __init__(self, enabled: bool = True, source: str = "all",
                 collection_ids: list = None, tags: list = None,
                 excluded_tags: list = None, respect_24h_norepeat: bool = True,
                 shuffle: bool = True):
        self.enabled = enabled
        self.source = source  # "all", "collections", "tags"
        self.collection_ids = collection_ids or []  # If source="collections"
        self.tags = tags or []  # If source="tags"
        self.excluded_tags = excluded_tags or []
        self.respect_24h_norepeat = respect_24h_norepeat
        self.shuffle = shuffle
    
    def __repr__(self):
        return f"GapFillerConfig(source={self.source}, enabled={self.enabled})"
    
    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "source": self.source,
            "collection_ids": self.collection_ids,
            "tags": self.tags,
            "excluded_tags": self.excluded_tags,
            "respect_24h_norepeat": self.respect_24h_norepeat,
            "shuffle": self.shuffle
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GapFillerConfig':
        """Create GapFillerConfig from dictionary"""
        return cls(
            enabled=data.get("enabled", True),
            source=data.get("source", "all"),
            collection_ids=data.get("collection_ids", []),
            tags=data.get("tags", []),
            excluded_tags=data.get("excluded_tags", []),
            respect_24h_norepeat=data.get("respect_24h_norepeat", True),
            shuffle=data.get("shuffle", True)
        )


class ScheduledEntry:
    """
    Represents any scheduled content (block or gap filler video).
    
    This class provides a unified interface for both explicit TimeBlocks
    and gap filler videos, allowing the approximate calc to consider both
    when finding the best position for new daypart blocks.
    
    Args:
        start_time: "HH:MM" format (24-hour)
        end_time: "HH:MM" format (24-hour)
        duration_seconds: Duration in seconds
        source: "block" or "gap_filler"
        content_type: "video", "tag", or "gap_video"
        content_value: video path, tag name, or description
    """
    def __init__(self, start_time: str, end_time: str, duration_seconds: int,
                 source: str, content_type: str, content_value: str):
        self.start_time = start_time
        self.end_time = end_time
        self.duration_seconds = duration_seconds
        self.source = source  # "block" or "gap_filler"
        self.content_type = content_type  # "video", "tag", "gap_video"
        self.content_value = content_value
        
    def __repr__(self):
        return f"ScheduledEntry({self.start_time}-{self.end_time}, source={self.source}, type={self.content_type})"
    
    @property
    def duration_hours(self) -> float:
        """Calculate duration in hours"""
        return self.duration_seconds / 3600
    
    @classmethod
    def from_time_block(cls, block: TimeBlock) -> 'ScheduledEntry':
        """Create a ScheduledEntry from a TimeBlock"""
        return cls(
            start_time=block.start_time,
            end_time=block.end_time,
            duration_seconds=block.duration_seconds,
            source="block",
            content_type=block.content_type,
            content_value=block.content_value
        )
    
    @classmethod
    def from_gap_filler_entry(cls, entry: dict) -> 'ScheduledEntry':
        """
        Create a ScheduledEntry from a gap filler entry dict.
        
        Args:
            entry: Dict with 'time', 'duration', 'file', etc.
        """
        time_str = entry.get("time", "00:00")
        # Handle HH:MM:SS format - extract HH:MM
        if ":" in time_str:
            parts = time_str.split(":")
            if len(parts) >= 3:
                time_str = f"{parts[0]}:{parts[1]}"
        
        duration = entry.get("duration", 5400)  # Default 90 minutes
        
        # Calculate end time
        start_dt = parse_time_string(time_str)
        end_dt = start_dt + timedelta(seconds=duration)
        end_time_str = format_time_string(end_dt)
        
        return cls(
            start_time=time_str,
            end_time=end_time_str,
            duration_seconds=duration,
            source="gap_filler",
            content_type="gap_video",
            content_value=entry.get("file", "")
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_duration(start_time: str, end_time: str) -> int:
    """Calculate duration in seconds between two HH:MM times"""
    start_dt = parse_time_string(start_time)
    end_dt = parse_time_string(end_time)
    if end_dt < start_dt:
        end_dt += timedelta(days=1)
    return int((end_dt - start_dt).total_seconds())


def get_weekday_indices(day_names: List[str]) -> List[int]:
    """Convert weekday names to indices (0=Monday, 6=Sunday)"""
    days_lower = [d.lower() for d in day_names]
    mapping = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }
    return [mapping[d] for d in days_lower if d in mapping]


def has_excluded_tag(video: dict, excluded_tags: List[str]) -> bool:
    """Check if video has any excluded tag"""
    video_tags = video.get("tags", [])
    return any(tag in video_tags for tag in excluded_tags)


def validate_time_format(time_str: str) -> bool:
    """Validate HH:MM format (00:00 to 24:00)"""
    import re
    if not re.match(r"^([01]?[0-9]|2[0-4]):[0-5][0-9]$", time_str):
        return False
    # Additional check: 24:00 is valid but 24:01 is not
    hour, minute = map(int, time_str.split(":"))
    return 0 <= hour <= 24 and 0 <= minute <= 59


def detect_gaps(time_blocks: List[TimeBlock], day_start: str = "00:00", day_end: str = "24:00") -> List[Tuple[str, str]]:
    """
    Identify unscheduled time periods between blocks.
    Returns list of (start_time, end_time) tuples.
    """
    if not time_blocks:
        return [(day_start, day_end)]
    
    # Sort blocks by start time
    sorted_blocks = sorted(time_blocks, key=lambda b: b.start_time)
    
    gaps = []
    current_time = parse_time_string(day_start)
    
    for block in sorted_blocks:
        block_start = parse_time_string(block.start_time)
        block_end = parse_time_string(block.end_time)
        
        # Handle overnight block end
        if block_end < block_start:
            block_end += timedelta(days=1)
        
        if current_time < block_start:
            # Gap detected
            gaps.append((format_time_string(current_time), block.start_time))
        
        # Move current time to block end
        current_time = block_end
        if current_time < block_start:
            current_time += timedelta(days=1)
    
    # Check for gap at end of day
    day_end_dt = parse_time_string(day_end)
    if current_time < day_end_dt:
        gaps.append((format_time_string(current_time), day_end))
    
    return gaps


def has_overlapping_blocks(blocks: List[TimeBlock]) -> bool:
    """Check if any time blocks overlap"""
    if len(blocks) <= 1:
        return False
    
    sorted_blocks = sorted(blocks, key=lambda b: b.start_time)
    
    for i in range(len(sorted_blocks) - 1):
        curr = sorted_blocks[i]
        next_block = sorted_blocks[i + 1]
        
        curr_start = parse_time_string(curr.start_time)
        curr_end = parse_time_string(curr.end_time)
        next_start = parse_time_string(next_block.start_time)
        
        # Handle overnight
        if curr_end < curr_start:
            curr_end += timedelta(days=1)
        
        if curr_end > next_start:
            return True
    
    return False


def validate_time_block(block: TimeBlock) -> Optional[str]:
    """
    Validate a time block.
    Returns error message string if invalid, None if valid.
    """
    # Check time format
    if not validate_time_format(block.start_time):
        return "Invalid start time format: {}".format(block.start_time)
    if not validate_time_format(block.end_time):
        return "Invalid end time format: {}".format(block.end_time)
    
    # Check time range
    try:
        start_dt = parse_time_string(block.start_time)
        end_dt = parse_time_string(block.end_time)
    except ValueError:
        return "Invalid time format"
    
    # Overnight blocks not allowed
    if end_dt < start_dt:
        return "Overnight blocks not allowed: {}-{}".format(block.start_time, block.end_time)
    
    # Check duration
    duration = block.duration_seconds
    if duration <= 0:
        return f"Block duration must be positive: {duration} seconds"
    if duration > 86400:
        return f"Block duration exceeds 24 hours: {duration} seconds"
    
    # Check content type
    if block.content_type not in ["video", "tag", "episodic"]:
        return f"Invalid content_type: {block.content_type}"
    
    # Validate tag blocks have valid video_count
    if block.content_type == "tag":
        content = block.content_value
        parts = content.split("|")
        tag = parts[0] if parts else block.content_value
        
        # Extract video_count
        video_count = getattr(block, 'video_count', None)
        if not video_count and len(parts) >= 3:
            video_count = parts[2]
        if not video_count:
            video_count = "single"
        
        # Validate video_count is valid
        valid_counts = ["single", "all", "2", "3", "4", "5"]
        if video_count not in valid_counts:
            return f"Invalid video_count: {video_count}. Must be one of: {valid_counts}"
    
    if not block.content_value:
        return "Content value cannot be empty"
    
    return None


# ============================================================================
# SCHEDULE GENERATION
# ============================================================================

def generate_block_schedule(block: TimeBlock, available_videos: List[dict],
                           recent_videos: List[Tuple[str, datetime]] = None,
                           channel: str = "",
                           start_datetime: datetime = None,
                           preview_mode: bool = False,
                           preview_ep_state: dict = None) -> List[dict]:
    """
    Generate schedule entries for a time block.
    
    Args:
        block: TimeBlock configuration
        available_videos: Pool of videos to choose from
        recent_videos: List of (video_path, timestamp) for 24h rule
        channel: Channel name for logging
        start_datetime: Optional datetime to start scheduling from (for continuous scheduling)
    
    Returns:
        List of schedule entries for this block
    """
    if recent_videos is None:
        recent_videos = []
    
    entries = []
    block_duration = block.duration_seconds
    
    # Use provided start_datetime or parse from block.start_time
    if start_datetime is not None:
        current_time = start_datetime
    else:
        current_time = parse_time_string(block.start_time)
    
    end_time = parse_time_string(block.end_time)
    
    # Filter videos by content type
    if block.content_type == "video":
        # Specific video(s) - may be multiple (semicolon-separated)
        video_paths = [v.strip() for v in block.content_value.split(";") if v.strip()]
        
        for video_path in video_paths:
            video = None
            for v in available_videos:
                if v["path"] == video_path:
                    video = v
                    break
            
            if not video:
                logger.warning(f"[{channel}] Video not found: {video_path}")
                continue
            
            # Play the video (may overrun into next block - that's OK)
            entry = {
                "time": current_time.strftime("%H:%M:%S"),
                "file": video["path"],
                "duration": video.get("duration", 5400),  # Default 90 minutes if not set
                "collection_id": video.get("collection", {}).get("id", "unknown"),
                "channel": channel,
                "source": "daypart_video",
                "daypart_block_id": block.block_id,
                "metadata": {
                    "scheduled_type": "video",
                    "block_start": block.start_time,
                    "block_end": block.end_time
                }
            }
            entries.append(entry)
            current_time += timedelta(seconds=video["duration"])
        
    elif block.content_type == "tag":
        # Tag-based random selection
        # Parse content_value: "tag_name|days|video_count" or "tag_name|days" or just "tag_name"
        content = block.content_value
        parts = content.split("|")
        tag = parts[0]
        
        # Extract video_count from block or from content_value
        video_count = getattr(block, 'video_count', None)
        if not video_count and len(parts) >= 3:
            video_count = parts[2]
        if not video_count:
            video_count = "single"
        
        # Check both video-level tags and collection-level tags (videos inherit tags from their collection)
        tag_videos = [v for v in available_videos 
                      if tag in v.get("tags", []) or tag in v.get("collection", {}).get("tags", [])
                      or tag == v.get("collection", {}).get("name", "")]
        
        # If no tag match and block has a collection_file, fall back to all videos from that file
        if not tag_videos:
            col_file = getattr(block, 'collection_file', "") or ""
            if col_file:
                tag_videos = [v for v in available_videos
                              if v.get("collection", {}).get("source_file", "") == col_file
                              or v.get("_col_file", "") == col_file]
            # Last resort: use all available_videos if still empty
            if not tag_videos:
                tag_videos = list(available_videos)
        
        if not tag_videos:
            logger.warning(f"[{channel}] No videos found for tag: {tag}")
            return entries
        
        # Determine max videos to play
        max_videos = None
        if video_count == "all":
            max_videos = len(tag_videos)
        elif video_count != "single" and video_count:
            try:
                max_videos = int(video_count)
            except (ValueError, TypeError):
                max_videos = 1  # Default to single if invalid
        else:
            # video_count is "single" or empty
            max_videos = 1
        
        # Fill the block with videos from this tag
        video_index = 0
        
        # Calculate the actual end time for the block
        if start_datetime is not None:
            # Calculate block end based on duration
            block_start_dt = start_datetime
            block_end_dt = block_start_dt + timedelta(seconds=block.duration_seconds)
        else:
            # Use the traditional end_time (time only)
            block_end_dt = None
        
        while True:
            # Check if we've reached the video count limit
            if max_videos is not None and video_index >= max_videos:
                break
            
            # Check time-based end condition
            if block_end_dt is not None and current_time >= block_end_dt:
                break
            elif block_end_dt is None and current_time.time() >= end_time.time():
                break
            
            # Filter by 24h rule
            candidates = tag_videos.copy()
            if recent_videos:
                recent_paths = {path for path, _ in recent_videos}
                candidates = [v for v in candidates if v["path"] not in recent_paths]
            
            if not candidates:
                # Emergency: reset recent videos and try again
                candidates = tag_videos
                recent_videos.clear()
            
            # Select video
            selected = random.choice(candidates)
            
            entry = {
                "time": current_time.strftime("%H:%M:%S"),
                "file": selected["path"],
                "duration": selected.get("duration", 5400),  # Default 90 minutes if not set
                "collection_id": selected.get("collection", {}).get("id", "unknown"),
                "channel": channel,
                "source": "daypart_tag",
                "daypart_block_id": block.block_id,
                "metadata": {
                    "scheduled_type": "tag",
                    "tag_used": tag,
                    "video_count": video_count,
                    "block_start": block.start_time,
                    "block_end": block.end_time
                }
            }
            entries.append(entry)
            
            # Track for 24h rule
            if recent_videos is not None:
                recent_videos.append((selected["path"], current_time))
            
            current_time += timedelta(seconds=selected["duration"])
            video_index += 1

    elif block.content_type == "episodic":
        # Episodic block: play episodes from a collection in order, advancing across days.
        # content_value format: "collection_id|start_season|start_episode|episodes_per_block"
        parts = block.content_value.split("|")
        collection_id      = parts[0] if len(parts) > 0 else ""
        start_season       = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
        start_episode      = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        episodes_per_block = parts[3] if len(parts) > 3 else "1"

        # Determine how many episodes to play this block
        if episodes_per_block == "all":
            max_ep = None
        else:
            try:
                max_ep = int(episodes_per_block)
            except (ValueError, TypeError):
                max_ep = 1

        # Filter videos belonging to this collection
        col_videos = [v for v in available_videos
                      if v.get("collection", {}).get("id", "") == collection_id]

        # Fallback: if each episode is its own collection (one-per-episode layout),
        # load ALL videos from the block's collection_file as the full series pool.
        if len(col_videos) <= 1:
            col_file = getattr(block, "collection_file", "") or ""
            if col_file:
                try:
                    import json as _json
                    with open(col_file, "r", encoding="utf-8") as _f:
                        _data = _json.load(_f)
                    col_videos = []
                    for _col in _data.get("collections", []):
                        for _v in _col.get("videos", []):
                            _v = dict(_v)
                            _v["collection"] = _col
                            col_videos.append(_v)
                    logger.info(f"[{channel}] Episodic block: loaded {len(col_videos)} videos from collection file (one-per-episode layout)")
                except Exception as _ex:
                    logger.warning(f"[{channel}] Episodic block: could not load collection file {col_file}: {_ex}")

        if not col_videos:
            logger.warning(f"[{channel}] Episodic block: no videos for collection '{collection_id}'")
            return entries

        # Sort by season/episode using metadata, falling back to filename
        def _ep_sort_key(v):
            meta = v.get("metadata", {})
            s = meta.get("season", 0) or 0
            e = meta.get("episode", 0) or 0
            if s == 0 and e == 0:
                import re
                fname = Path(v["path"]).stem
                m = re.search(r"[Ss](\d+)[Ee](\d+)", fname)
                if m:
                    s, e = int(m.group(1)), int(m.group(2))
                else:
                    m2 = re.search(r"(\d+)[xX](\d+)", fname)
                    if m2:
                        s, e = int(m2.group(1)), int(m2.group(2))
            return (s, e)

        col_videos.sort(key=_ep_sort_key)

        # State source: live uses disk, preview uses in-memory dict passed from caller
        block_key = f"{block.block_id}_{collection_id}"
        if preview_mode:
            state_dict = preview_ep_state if preview_ep_state is not None else {}
        else:
            state_dict = _load_episodic_state(channel)

        if block_key in state_dict:
            ep_index = state_dict[block_key]
            logger.info(f"[{channel}] Episodic block resuming at index {ep_index}")
        else:
            ep_index = 0
            for i, v in enumerate(col_videos):
                s, e = _ep_sort_key(v)
                if s > start_season or (s == start_season and e >= start_episode):
                    ep_index = i
                    break
            logger.info(f"[{channel}] Episodic block starting fresh at index {ep_index} (S{start_season}E{start_episode})")

        played = 0

        # Calculate block end time — only used when episodes_per_block is "all"
        # (fill the time window). When a specific count is set, play exactly
        # that many episodes regardless of how long they run.
        if max_ep is None:
            if start_datetime is not None:
                block_end_dt = start_datetime + timedelta(seconds=block.duration_seconds)
            else:
                block_end_dt = None
        else:
            block_end_dt = None  # count-based: ignore time window

        while True:
            if max_ep is not None and played >= max_ep:
                break
            if block_end_dt is not None and current_time >= block_end_dt:
                break
            elif block_end_dt is None and max_ep is None and current_time.time() >= end_time.time():
                break
            if not col_videos:
                break

            # Wrap around when we reach the end of the collection
            ep_index = ep_index % len(col_videos)
            video = col_videos[ep_index]

            s, e = _ep_sort_key(video)
            entry = {
                "time": current_time.strftime("%H:%M:%S"),
                "file": video["path"],
                "duration": video.get("duration", 5400),
                "collection_id": collection_id,
                "channel": channel,
                "source": "daypart_episodic",
                "daypart_block_id": block.block_id,
                "metadata": {
                    "scheduled_type": "episodic",
                    "collection_id": collection_id,
                    "season": s,
                    "episode": e,
                    "block_start": block.start_time,
                    "block_end": block.end_time
                }
            }
            entries.append(entry)
            current_time += timedelta(seconds=video.get("duration", 5400))
            ep_index += 1
            played += 1

        # Advance state for next day
        next_index = ep_index % len(col_videos)
        if preview_mode:
            # Write back to in-memory dict so next day's call picks up here
            if preview_ep_state is not None:
                preview_ep_state[block_key] = next_index
            logger.info(f"[{channel}] Episodic block (preview) played {played} ep(s); next index={next_index}")
        else:
            state_dict[block_key] = next_index
            _save_episodic_state(channel, state_dict)
            logger.info(f"[{channel}] Episodic block played {played} ep(s); next index={next_index}")

    return entries


def generate_marathon_schedule(tag: str, available_videos: List[dict],
                              marathon_config: MarathonConfig = None,
                              recent_videos: List[Tuple[str, datetime]] = None,
                              channel: str = "") -> List[dict]:
    """
    Generate 24-hour marathon schedule from a tag pool.
    
    Args:
        tag: Tag to marathon
        available_videos: Pool of videos
        marathon_config: Marathon configuration
        recent_videos: For 24h no-repeat tracking
        channel: Channel name
    
    Returns:
        List of schedule entries for 24 hours
    """
    if recent_videos is None:
        recent_videos = []
    
    if marathon_config is None:
        marathon_config = MarathonConfig(tag, ["monday"], shuffle=True, no_repeat_24h=True)
    
    # Filter videos by tag
    # Check both video-level tags and collection-level tags (videos inherit tags from their collection)
    tag_videos = [v for v in available_videos 
                  if tag in v.get("tags", []) or tag in v.get("collection", {}).get("tags", [])]
    
    if not tag_videos:
        logger.warning(f"[{channel}] Marathon: No videos for tag '{tag}'")
        return []
    
    entries = []
    current_time = parse_time_string("00:00")
    end_time = parse_time_string("24:00")
    
    # Prepare video pool
    if marathon_config.shuffle:
        random.shuffle(tag_videos)
    
    video_index = 0
    used_videos = set()
    
    while current_time < end_time:
        # Get candidates respecting 24h rule
        candidates = tag_videos.copy()
        
        if marathon_config.no_repeat_24h:
            recent_paths = {path for path, _ in recent_videos}
            candidates = [v for v in candidates if v["path"] not in recent_paths]
            
            # If exhausted, reset
            if not candidates:
                logger.info(f"[{channel}] Marathon pool exhausted, resetting 24h rule")
                candidates = tag_videos
                recent_videos.clear()
        
        if not candidates:
            # All videos somehow excluded - use all
            candidates = tag_videos
        
        # Select video
        if marathon_config.shuffle and len(candidates) > 1:
            selected = random.choice(candidates)
        else:
            # Sequential
            selected = candidates[video_index % len(candidates)]
            video_index += 1
        
        entry = {
            "time": current_time.strftime("%H:%M:%S"),
            "file": selected["path"],
            "duration": selected.get("duration", 5400),  # Default 90 minutes if not set
            "collection_id": selected.get("collection", {}).get("id", "unknown"),
            "channel": channel,
            "source": "daypart_marathon",
            "metadata": {
                "scheduled_type": "marathon",
                "tag": tag,
                "shuffle": marathon_config.shuffle
            }
        }
        entries.append(entry)
        
        # Track for 24h rule
        if marathon_config.no_repeat_24h:
            recent_videos.append((selected["path"], current_time))
        
        current_time += timedelta(seconds=selected["duration"])
    
    return entries


def fill_gaps_with_random(gaps: List[Tuple[str, str]], available_videos: List[dict],
                         gap_filler_config: GapFillerConfig,
                         recent_videos: List[Tuple[str, datetime]] = None,
                         channel: str = "",
                         base_datetime: datetime = None,
                         target_date: date = None) -> List[dict]:
    """
    Fill each gap with random video selections.
    
    Args:
        gaps: List of (start, end) time tuples
        available_videos: Pool of videos
        gap_filler_config: Configuration
        recent_videos: For 24h rule tracking
        channel: Channel name
        base_datetime: Optional datetime to start from (for cross-day continuity)
    
    Returns:
        List of schedule entries for gap content
    """
    if recent_videos is None:
        recent_videos = []
    
    # Default target_date to today if not provided
    if target_date is None:
        from datetime import date as date_module
        target_date = date_module.today()
    
    gap_entries = []
    
    # Pre-filter available videos based on gap filler source
    filtered_videos = available_videos.copy()
    
    # Apply source-based filtering (collections or tags)
    if gap_filler_config.source == "collections" and gap_filler_config.collection_ids:
        # Filter to only include videos from specified collections
        filtered_videos = [v for v in filtered_videos 
                          if v.get("collection", {}).get("id", "") in gap_filler_config.collection_ids]
        logger.debug(f"[{channel}] Gap filler: filtered to {len(filtered_videos)} videos from collections {gap_filler_config.collection_ids}")
    elif gap_filler_config.source == "tags" and gap_filler_config.tags:
        # Filter to only include videos with specified tags
        filtered_videos = [v for v in filtered_videos
                          if any(tag in v.get("tags", []) for tag in gap_filler_config.tags)]
        logger.debug(f"[{channel}] Gap filler: filtered to {len(filtered_videos)} videos with tags {gap_filler_config.tags}")
    
    # If no videos match the filter, fall back to all videos
    if not filtered_videos:
        logger.warning(f"[{channel}] Gap filler: No videos match source filter, using all videos")
        filtered_videos = available_videos.copy()
    
    for gap_start, gap_end in gaps:
        gap_duration = calculate_duration(gap_start, gap_end)
        
        # Use base_datetime if provided to handle cross-day continuity
        # base_datetime represents where the previous day ended
        if base_datetime is not None:
            if gap_start == "00:00":
                # Special case: gap starts at midnight, use base_datetime
                # This handles the case where previous day ended at, say, 00:43
                # We should fill from 00:43 to 17:00, not from 00:00 to 17:00
                current_time = base_datetime
                # Calculate end time properly when base_datetime pushes past midnight
                # The gap ends at 24:00 of the target date
                target_date = base_datetime.date()
                end_time = datetime.combine(target_date, datetime.min.time()) + timedelta(days=1)
            else:
                # Gap doesn't start at 00:00 - check if base_datetime is within this gap
                gap_start_dt = datetime.combine(target_date, parse_time_string(gap_start).time())
                gap_end_dt = datetime.combine(target_date, parse_time_string(gap_end).time())
                if gap_end_dt < gap_start_dt:
                    gap_end_dt += timedelta(days=1)
                
                # If base_datetime falls within this gap, use it as the start time
                if base_datetime >= gap_start_dt and base_datetime < gap_end_dt:
                    current_time = base_datetime
                    end_time = gap_end_dt
                else:
                    # base_datetime is outside this gap, use normal parsing
                    current_time = parse_time_string(gap_start)
                    end_time = parse_time_string(gap_end)
                    if end_time < current_time:
                        end_time += timedelta(days=1)
        else:
            current_time = parse_time_string(gap_start)
            end_time = parse_time_string(gap_end)
            # Handle overnight gap - only if start is after end
            if end_time < current_time:
                end_time += timedelta(days=1)
        
        # Track videos used in this gap (for 24h rule if enabled)
        gap_recent = [] if gap_filler_config.respect_24h_norepeat else None
        
        while current_time < end_time:
            # Filter available videos (use pre-filtered list)
            candidates = filtered_videos.copy()

            # Only schedule videos that fit entirely within the remaining gap.
            # This prevents gap filler from bleeding into the next daypart block.
            remaining_seconds = (end_time - current_time).total_seconds()
            fitting = [v for v in candidates if (v.get("duration") or 0) <= remaining_seconds]

            # Apply excluded tags
            pool = fitting if fitting else []
            if pool and gap_filler_config.excluded_tags:
                pool = [v for v in pool
                        if not has_excluded_tag(v, gap_filler_config.excluded_tags)]
            if not pool:
                pool = fitting  # excluded tags filtered everything, relax that

            # If nothing fits at all, stop — don't overshoot into the next block
            if not pool:
                break

            # Apply 24h no-repeat rule
            if gap_filler_config.respect_24h_norepeat:
                recent_paths = {path for path, _ in recent_videos}
                no_repeat_pool = [v for v in pool if v["path"] not in recent_paths]
                if no_repeat_pool:
                    pool = no_repeat_pool
                else:
                    logger.info(f"[{channel}] Gap filler: All videos used in last 24h, resetting")
                    recent_videos.clear()

            if not pool:
                logger.error(f"[{channel}] Gap filler: No videos available at all!")
                break

            # Select video
            if gap_filler_config.shuffle:
                selected = random.choice(pool)
            else:
                selected = pool[0]
            
            # Add to schedule
            entry = {
                "time": current_time.strftime("%H:%M:%S"),
                "file": selected["path"],
                "duration": selected.get("duration", 5400),  # Default 90 minutes if not set
                "collection_id": selected.get("collection", {}).get("id", "unknown"),
                "channel": channel,
                "source": "gap_filler",
                "metadata": {
                    "scheduled_type": "gap_filler",
                    "gap_start": gap_start,
                    "gap_end": gap_end
                }
            }
            gap_entries.append(entry)
            
            # Track for 24h rule
            if gap_filler_config.respect_24h_norepeat:
                recent_videos.append((selected["path"], current_time))
                if gap_recent is not None:
                    gap_recent.append(selected["path"])
            
            # Advance time
            current_time += timedelta(seconds=selected["duration"])
    
    return gap_entries


def _handle_approximate_blocks(schedule_entries: List[dict], time_blocks: List[dict],
                                 daypart_inner: dict, weekday: int,
                                 target_date: date, channel: str,
                                 available_videos: List[dict] = None,
                                 recent_videos: List = None):
    """
    Handle blocks with approximate=True by moving them to suitable gaps.
    
    This function finds blocks that have approximate=True and attempts to move them
    to time slots that don't overlap with existing scheduled content.
    
    Args:
        schedule_entries: Current list of scheduled entries (will be modified)
        time_blocks: List of time block dicts from config
        daypart_inner: Inner daypart config dict
        weekday: Current weekday (0=Monday)
        target_date: Target date for scheduling
        channel: Channel name for logging
        available_videos: List of available videos for scheduling
        recent_videos: List of recently played videos for 24h no-repeat
    """
    if available_videos is None:
        available_videos = []
    if recent_videos is None:
        recent_videos = []
    
    # Find blocks with approximate=True that apply to today
    approximate_blocks = []
    
    logger.info(f"[_handle_approximate_blocks] Checking {len(time_blocks)} time blocks for approximate=True")
    
    for block_data in time_blocks:
        block = TimeBlock.from_dict(block_data)
        
        # Check if this block has approximate=True
        logger.info(f"[_handle_approximate_blocks] Block {block.block_id}: approximate={getattr(block, 'approximate', False)}, content_type={block.content_type}")
        
        if not getattr(block, 'approximate', False):
            continue
    
        # Get block days
        block_days = block.days if hasattr(block, 'days') and block.days else None
    
        if not block_days and block.content_type == "tag":
            # Try to extract days from content_value
            content_parts = block.content_value.split("|")
            if len(content_parts) >= 2:
                days_str = content_parts[1]
                block_days = [d.strip() for d in days_str.split(",") if d.strip()]
    
        # Check if block applies today
        applies_today = False
        if block.content_type == "video" or not block_days:
            applies_today = True
        elif weekday in get_weekday_indices(block_days):
            applies_today = True
    
        if applies_today:
            approximate_blocks.append((block, block_data))
    
    if not approximate_blocks:
        return  # No approximate blocks to handle
    
    logger.info(f"[{channel}] Handling {len(approximate_blocks)} approximate block(s)")
    
    # Get existing scheduled entries as ScheduledEntry objects for approximation
    existing_entries = []
    for entry in schedule_entries:
        time_str = entry.get("time", "00:00")
        # Handle HH:MM:SS format
        if ":" in time_str:
            parts = time_str.split(":")
            if len(parts) >= 3:
                time_str = f"{parts[0]}:{parts[1]}"
        
        duration = entry.get("duration", 5400)
        start_dt = parse_time_string(time_str)
        end_dt = start_dt + timedelta(seconds=duration)
        end_time_str = format_time_string(end_dt)
        
        source = entry.get("source", "unknown")
        existing_entries.append(ScheduledEntry(
            start_time=time_str,
            end_time=end_time_str,
            duration_seconds=duration,
            source=source,
            content_type=entry.get("metadata", {}).get("scheduled_type", "video"),
            content_value=entry.get("file", "")
        ))
    
    # Sort existing entries by start time
    existing_entries.sort(key=lambda e: e.start_time)
    
    # CRITICAL: Remove only the approximate blocks' own entries BEFORE calculating gaps
    # This ensures gaps are calculated with all other scheduled content intact
    # Note: daypart_block_id is stored at the top level of the entry dict
    approximate_block_ids = {block.block_id for block, _ in approximate_blocks}
    schedule_entries[:] = [e for e in schedule_entries 
                          if e.get("daypart_block_id") not in approximate_block_ids]
    
    # Now rebuild existing_entries from the filtered schedule_entries
    existing_entries = []
    for entry in schedule_entries:
        time_str = entry.get("time", "00:00")
        # Handle HH:MM:SS format
        if ":" in time_str:
            parts = time_str.split(":")
            if len(parts) >= 3:
                time_str = f"{parts[0]}:{parts[1]}"
        
        duration = entry.get("duration", 5400)
        start_dt = parse_time_string(time_str)
        end_dt = start_dt + timedelta(seconds=duration)
        end_time_str = format_time_string(end_dt)
        
        source = entry.get("source", "unknown")
        existing_entries.append(ScheduledEntry(
            start_time=time_str,
            end_time=end_time_str,
            duration_seconds=duration,
            source=source,
            content_type=entry.get("metadata", {}).get("scheduled_type", "video"),
            content_value=entry.get("file", "")
        ))
    
    # Sort existing entries by start time
    existing_entries.sort(key=lambda e: e.start_time)
    
    # Calculate gaps from existing entries
    if existing_entries:
        gaps = []
        current_gap_start = parse_time_string("00:00")
        for entry in existing_entries:
            entry_start = parse_time_string(entry.start_time)
            if current_gap_start < entry_start:
                gaps.append((format_time_string(current_gap_start), entry.start_time))
            entry_end = parse_time_string(entry.end_time)
            current_gap_start = entry_end
        
        # Add final gap to end of day
        day_end = parse_time_string("24:00")
        if current_gap_start < day_end:
            gaps.append((format_time_string(current_gap_start), "24:00"))
    else:
        # No existing entries - full day is available
        gaps = [("00:00", "24:00")]
    
    logger.info(f"[{channel}] Current gaps for approximate placement: {gaps}")
    
    # Process each approximate block
    for block, block_data in approximate_blocks:
        # Calculate block duration
        block_duration_hours = block.duration_seconds / 3600
        
        # Try to find the gap closest to the block's configured start time
        desired_start_dt = parse_time_string(block.start_time)
        best_gap = None
        best_distance = None
        for gap_start, gap_end in gaps:
            gap_start_dt = parse_time_string(gap_start)
            gap_end_dt = parse_time_string(gap_end)
            
            # Handle overnight gaps
            if gap_end_dt < gap_start_dt:
                gap_end_dt += timedelta(days=1)
            
            gap_duration_hours = (gap_end_dt - gap_start_dt).total_seconds() / 3600
            
            # Check if gap is large enough
            if gap_duration_hours >= block_duration_hours:
                # Measure distance: how far is the gap start from the desired start?
                distance = abs((gap_start_dt - desired_start_dt).total_seconds())
                if best_distance is None or distance < best_distance:
                    best_gap = (gap_start, gap_end)
                    best_distance = distance
        
        if best_gap:
            gap_start, gap_end = best_gap
            logger.info(f"[{channel}] Moving approximate block {block.block_id} to gap {gap_start}-{gap_end}")
            
            # Update the block's times
            block.start_time = gap_start
            
            # Calculate end time
            gap_start_dt = parse_time_string(gap_start)
            block_end_dt = gap_start_dt + timedelta(seconds=block.duration_seconds)
            block.end_time = format_time_string(block_end_dt)
            
            # Remove old entries for this block and reschedule
            schedule_entries[:] = [e for e in schedule_entries 
                                   if e.get("daypart_block_id") != block.block_id]
            
            # Generate new entries at the new time
            block_start_dt = datetime.combine(target_date, parse_time_string(block.start_time).time())
            new_entries = generate_block_schedule(
                block,
                available_videos,
                recent_videos,
                channel,
                start_datetime=block_start_dt
            )
            
            # Add the new entries
            schedule_entries.extend(new_entries)
            
            # Remove this gap from the list (since it's now occupied)
            # and add remaining time as new gaps if any
            if gap_start != format_time_string(block_end_dt):
                # There's remaining time after the block
                gaps.remove((gap_start, gap_end))
                remaining_start = format_time_string(block_end_dt)
                gaps.append((remaining_start, gap_end))
            else:
                gaps.remove((gap_start, gap_end))
        else:
            logger.warning(f"[{channel}] No suitable gap found for approximate block {block.block_id}")


def _gaps_from_actual_ends(
    schedule_entries: list,
    time_blocks_today: list,
    target_date,
    current_time: datetime,
    base_datetime: datetime = None
) -> list:
    """
    Compute gap windows using actual video end times from scheduled entries,
    with block start times as the gap end boundaries.

    This prevents:
    - Gap filler overshooting into a daypart block (gap ends at block START)
    - Duplicate entries after a block (gap starts at actual last video end)
    """
    # Day always starts at midnight of target_date.
    # Cross-day continuity is handled by adjusting the first gap's start below.
    day_start_dt = datetime.combine(target_date, datetime.min.time())
    day_end_dt = day_start_dt + timedelta(days=1)

    # Collect block windows sorted by start time
    # For approximate blocks, use the actual scheduled start from entries (post-snap),
    # not the configured start_time which may differ after snapping.
    block_windows = []
    for block in time_blocks_today:
        try:
            configured_bs = datetime.combine(target_date, parse_time_string(block.start_time).time())
            configured_be = datetime.combine(target_date, parse_time_string(block.end_time).time())
            if configured_be <= configured_bs:
                configured_be += timedelta(days=1)

            if getattr(block, 'approximate', False):
                # Find the actual start from scheduled entries (post-snap)
                block_entries = [e for e in schedule_entries
                                 if e.get("daypart_block_id") == block.block_id]
                if block_entries:
                    actual_start = min(
                        datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time())
                        for e in block_entries
                    )
                    last_e = max(block_entries, key=lambda e: e["time"])
                    actual_end = (datetime.combine(target_date, datetime.strptime(last_e["time"], "%H:%M:%S").time())
                                  + timedelta(seconds=last_e.get("duration", 5400)))
                    block_windows.append((actual_start, actual_end))
                    continue

            block_windows.append((configured_bs, configured_be))
        except Exception:
            pass
    block_windows.sort(key=lambda x: x[0])

    # For each block, find the actual end time of the last scheduled entry within it
    def actual_end_of_block(bs, be):
        best = bs  # fallback: block start (nothing scheduled)
        for entry in schedule_entries:
            try:
                t = datetime.strptime(entry["time"], "%H:%M:%S")
                entry_start = datetime.combine(target_date, t.time())
                dur = entry.get("duration", 0) or 0
                entry_end = entry_start + timedelta(seconds=dur)
                if bs <= entry_start < be:
                    if entry_end > best:
                        best = entry_end
            except Exception:
                pass
        return best

    gaps = []
    cursor = day_start_dt

    for bs, be in block_windows:
        if cursor < bs:
            gap_start_str = cursor.strftime("%H:%M")
            gap_end_str = bs.strftime("%H:%M")
            if gap_end_str == "00:00":
                gap_end_str = "24:00"
            gaps.append((gap_start_str, gap_end_str))
        cursor = max(cursor, actual_end_of_block(bs, be))

    # Gap after last block to end of day
    if cursor < day_end_dt:
        gap_start_str = cursor.strftime("%H:%M")
        gaps.append((gap_start_str, "24:00"))

    # Adjust the very first gap's start for cross-day continuity
    if gaps:
        if base_datetime and base_datetime.date() < target_date:
            adjusted_start = base_datetime.strftime("%H:%M")
            gaps[0] = (adjusted_start, gaps[0][1])
        elif base_datetime and base_datetime.date() == target_date:
            first_gap_start_dt = datetime.combine(target_date, parse_time_string(gaps[0][0]).time())
            if base_datetime > first_gap_start_dt:
                adjusted_start = base_datetime.strftime("%H:%M")
                gaps[0] = (adjusted_start, gaps[0][1])

    # Remove zero-length gaps using time-aware comparison (not string comparison)
    def gap_duration_seconds(s, e):
        try:
            st = parse_time_string(s)
            et = parse_time_string(e)
            if e == "24:00":
                et = parse_time_string("00:00") + timedelta(days=1)
            if et <= st:
                et += timedelta(days=1)
            return (et - st).total_seconds()
        except Exception:
            return 0

    gaps = [(s, e) for s, e in gaps if gap_duration_seconds(s, e) > 60]

    logger.info(f"[_gaps_from_actual_ends] gaps={gaps}")
    return gaps



def generate_daypart_schedule(daypart_config: dict, available_videos: List[dict],
                             channel: str, target_date: date,
                             base_datetime: datetime = None,
                             preview_mode: bool = False,
                             preview_ep_state: dict = None) -> List[dict]:
    """
    Generate a complete day schedule using daypart configuration.
    
    Process:
    1. Check if target_date has marathon (overrides time blocks)
    2. Apply time blocks for the day
    3. Detect gaps between blocks
    4. Fill gaps with random content (if enabled)
    5. Sort all entries by time
    
    Args:
        daypart_config: Full daypart configuration dict
        available_videos: List of video dicts with metadata
        channel: Channel name
        target_date: Date to generate schedule for
        base_datetime: Optional base datetime for continuous scheduling across days
                      If None, starts at midnight of target_date
    
    Returns:
        Tuple of (List of schedule entries, last datetime used)
    """
    schedule_entries = []
    recent_videos = []  # For 24h no-repeat tracking
    
    # Determine the base time for this day
    # If base_datetime is provided and is before or on target_date, use it for continuity
    # This handles cross-day continuity (e.g., base_datetime=2026-03-31 23:30, target_date=2026-04-01)
    if base_datetime and base_datetime.date() < target_date:
        # Previous day continued into this day - use the exact time
        day_start = base_datetime
    elif base_datetime and base_datetime.date() == target_date:
        # Same day - only use base_datetime if it's past midnight (continuing from earlier in the day)
        # If base_datetime is exactly midnight, treat it as a fresh start
        if base_datetime.time() > datetime.min.time():
            day_start = base_datetime
        else:
            day_start = datetime.combine(target_date, datetime.min.time())
    else:
        day_start = datetime.combine(target_date, datetime.min.time())
    
    logger.info(f"[{channel}] Generating schedule for {target_date} ({target_date.strftime('%A')}), day_start={day_start}")
    
    # Track current time for scheduling
    current_time = day_start
    
    # 1. Check for marathon on this day
    marathon_entries = []
    is_marathon_day = False
    weekday = target_date.weekday()  # 0=Monday
    
    daypart_inner = daypart_config.get("daypart_config", {})
    
    for marathon in daypart_inner.get("marathons", []):
        if not marathon.get("enabled", True):
            continue
        
        marathon_days = marathon.get("days", [])
        if weekday in get_weekday_indices(marathon_days):
            is_marathon_day = True
            logger.info(f"[{channel}] Marathon day for tag '{marathon['tag']}'")
            # Convert dict to MarathonConfig
            marathon_cfg = MarathonConfig.from_dict(marathon)
            marathon_entries = generate_marathon_schedule(
                marathon["tag"], 
                available_videos,
                marathon_config=marathon_cfg,
                recent_videos=recent_videos,
                channel=channel
            )
            schedule_entries.extend(marathon_entries)
            break  # Only one marathon per day
    
    # 2. If not marathon day, apply time blocks
    if not is_marathon_day:
        daypart_inner = daypart_config.get("daypart_config", {})
        time_blocks = daypart_inner.get("time_blocks", [])

        # Sort blocks by start time
        def _block_sort_key(bd):
            try:
                return parse_time_string(bd.get("start_time", "00:00")).time()
            except Exception:
                return datetime.min.time()
        time_blocks = sorted(time_blocks, key=_block_sort_key)

        # Separate gap fill blocks (00:00-23:59 all-day) from specific blocks.
        # Gap fill blocks are processed last to fill remaining time around specific blocks.
        # Approximate blocks are handled after gap fill — placed into the first free gap
        # at or after their configured start time.
        specific_blocks = []
        approximate_blocks = []
        gap_fill_blocks = []
        for bd in time_blocks:
            st = bd.get("start_time", "00:00")
            et = bd.get("end_time", "23:59")
            if st == "00:00" and et in ("23:59", "24:00"):
                gap_fill_blocks.append(bd)
            elif bd.get("content_type") == "episodic":
                specific_blocks.append(bd)
            elif bd.get("approximate", False) or (bd.get("approximate", "false") == "true"):
                approximate_blocks.append(bd)
            else:
                specific_blocks.append(bd)

        # --- Pass 1: schedule non-approximate specific blocks at their exact times ---
        for block_data in specific_blocks:
            block = TimeBlock.from_dict(block_data)

            block_days = block.days if hasattr(block, 'days') and block.days else None
            if not block_days and block.content_type in ("tag", "episodic"):
                content_parts = block.content_value.split("|")
                if len(content_parts) >= 2:
                    block_days = [d.strip() for d in content_parts[1].split(",") if d.strip()]

            block_start_dt = datetime.combine(target_date, parse_time_string(block.start_time).time())
            # For episodic blocks, always use the configured start time (they have a fixed slot).
            # For tag/video blocks, push forward if a previous block ran long.
            if block.content_type == "episodic":
                effective_start = block_start_dt
            else:
                effective_start = max(block_start_dt, current_time)

            applies_today = (not block_days) or (weekday in get_weekday_indices(block_days))
            if applies_today:
                block_entries = generate_block_schedule(
                    block, available_videos, recent_videos, channel,
                    start_datetime=effective_start,
                    preview_mode=preview_mode,
                    preview_ep_state=preview_ep_state
                )
                schedule_entries.extend(block_entries)
                if block_entries:
                    last_entry = block_entries[-1]
                    last_entry_time = datetime.strptime(last_entry["time"], "%H:%M:%S")
                    last_entry_duration = last_entry.get("duration", 5400)
                    last_entry_end = datetime.combine(target_date, last_entry_time.time()) + timedelta(seconds=last_entry_duration)
                    current_time = last_entry_end

        # --- Pass 2: gap fill + approximate snapping ---
        # Also trigger Pass 2 when GapFillerConfig.enabled even without a 00:00-23:59 block —
        # synthesize a virtual gap fill block driven by the GapFillerConfig settings.
        gf_config = GapFillerConfig.from_dict(daypart_inner.get("gap_filler", {}))
        if not gap_fill_blocks and gf_config.enabled and available_videos:
            # Build a synthetic all-day tag block using the gap filler's source/tags
            if gf_config.source == "tags" and gf_config.tags:
                gf_tag = gf_config.tags[0]
            else:
                # Use a tag that matches all videos — pick the most common collection tag
                # or fall back to a wildcard by using content_type="tag" with empty tag
                gf_tag = ""
            synthetic_gf = {
                "start_time": "00:00",
                "end_time": "24:00",
                "content_type": "tag",
                "content_value": gf_tag,
                "block_id": f"_synthetic_gf_{target_date}",
                "days": [],
                "video_count": "all",
                "approximate": False,
                "collection_file": "",
            }
            gap_fill_blocks = [synthetic_gf]

        # Helper: shift episodic blocks past any video that overlaps their start time.
        # Safe to call multiple times — idempotent.
        if gap_fill_blocks:
            if base_datetime and base_datetime.date() < target_date:
                fill_from = datetime.combine(target_date, datetime.min.time())
            elif base_datetime and base_datetime.date() == target_date and base_datetime.time() > datetime.min.time():
                fill_from = base_datetime
            else:
                fill_from = datetime.combine(target_date, datetime.min.time())

            day_end_dt = datetime.combine(target_date, datetime.strptime("23:59", "%H:%M").time())

            def _fill_windows(windows, strict_fit=False):
                for gf_data in gap_fill_blocks:
                    gf_block = TimeBlock.from_dict(gf_data)
                    gf_block.collection_file = gf_data.get("collection_file", "") or ""
                    # Only use videos from the gap fill block's own collection file
                    gf_col_file = gf_block.collection_file
                    if gf_col_file:
                        gf_videos = [v for v in available_videos
                                     if v.get("_col_file", "") == gf_col_file]
                        if not gf_videos:
                            gf_videos = available_videos  # fallback
                    else:
                        gf_videos = available_videos
                    for win_start, win_end in windows:
                        if (win_end - win_start).total_seconds() <= 0:
                            continue
                        if strict_fit:
                            current = win_start
                            while current < win_end:
                                remaining = (win_end - current).total_seconds()
                                fitting = [v for v in gf_videos if v.get("duration", 5400) <= remaining]
                                pool = fitting if fitting else gf_videos
                                # Apply excluded tags from GapFillerConfig
                                if gf_config.excluded_tags:
                                    pool = [v for v in pool if not any(
                                        t in v.get("tags", []) or t in v.get("collection", {}).get("tags", [])
                                        for t in gf_config.excluded_tags
                                    )] or pool
                                if recent_videos:
                                    recent_paths = {p for p, _ in recent_videos}
                                    filtered = [v for v in pool if v["path"] not in recent_paths]
                                    if filtered:
                                        pool = filtered
                                selected = random.choice(pool)
                                real_dur = selected.get("duration", 5400)
                                entry = {
                                    "time": current.strftime("%H:%M:%S"),
                                    "file": selected["path"],
                                    "duration": real_dur,
                                    "collection_id": selected.get("collection", {}).get("id", "unknown"),
                                    "channel": channel,
                                    "source": "daypart_tag",
                                    "daypart_block_id": gf_block.block_id,
                                    "metadata": {"scheduled_type": "tag"}
                                }
                                schedule_entries.append(entry)
                                if recent_videos is not None:
                                    recent_videos.append((selected["path"], current))
                                current += timedelta(seconds=real_dur)
                            continue
                        win_block = TimeBlock(
                            start_time=win_start.strftime("%H:%M"),
                            end_time=win_end.strftime("%H:%M"),
                            content_type=gf_block.content_type,
                            content_value=gf_block.content_value,
                            block_id=gf_block.block_id,
                            days=gf_block.days,
                            video_count=gf_block.video_count,
                            approximate=False
                        )
                        win_block.collection_file = gf_block.collection_file
                        win_entries = generate_block_schedule(
                            win_block, gf_videos, recent_videos, channel,
                            start_datetime=win_start,
                            preview_mode=preview_mode,
                            preview_ep_state=preview_ep_state
                        )
                        schedule_entries.extend(win_entries)

            # Step A: fill windows AROUND non-approximate specific blocks using strict_fit
            # so gap fill videos don't overrun into fixed episodic/specific slots.
            specific_occupied = sorted(
                [(datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time()),
                  datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time())
                  + timedelta(seconds=e.get("duration", 5400)))
                 for e in schedule_entries
                 if e.get("daypart_block_id") in {TimeBlock.from_dict(bd).block_id for bd in specific_blocks}],
                key=lambda x: x[0]
            )
            step_a_windows = []
            cursor_a = fill_from
            for occ_start, occ_end in specific_occupied:
                if cursor_a < occ_start:
                    step_a_windows.append((cursor_a, occ_start))
                cursor_a = max(cursor_a, occ_end)
            if cursor_a < day_end_dt:
                step_a_windows.append((cursor_a, day_end_dt))
            _fill_windows(step_a_windows, strict_fit=True)

            # Step B: snap approximate blocks against the gap fill entries
            snapped = _apply_approximate_snapping(
                schedule_entries, specific_blocks, weekday, target_date, channel
            )

            # Step C: remove ALL gap fill entries, then re-fill around
            # the (possibly snapped) specific block positions
            specific_block_ids = {TimeBlock.from_dict(bd).block_id for bd in specific_blocks}
            schedule_entries[:] = [
                e for e in schedule_entries
                if e.get("daypart_block_id") in specific_block_ids
            ]

            occupied = sorted(
                [(datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time()),
                  datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time())
                  + timedelta(seconds=e.get("duration", 5400)))
                 for e in schedule_entries],
                key=lambda x: x[0]
            )
            free_windows = []
            cursor = fill_from
            for occ_start, occ_end in occupied:
                if cursor < occ_start:
                    free_windows.append((cursor, occ_start))
                cursor = max(cursor, occ_end)
            if cursor < day_end_dt:
                free_windows.append((cursor, day_end_dt))

            _fill_windows(free_windows)

            # Step D: place approximate blocks by snapping to the gap fill video
            # that is playing at the configured time (i.e. contains desired_start),
            # then re-fill around them.
            #
            # Logic:
            #   1. Find the gap fill video that CONTAINS desired_start
            #      (started before AND ends after desired_start).
            #   2. If found, place the block at that video's start time.
            #   3. If no such video exists (desired_start is already in a gap),
            #      use desired_start directly.
            if approximate_blocks:
                for block_data in approximate_blocks:
                    block = TimeBlock.from_dict(block_data)
                    block.collection_file = block_data.get("collection_file", "") or ""

                    block_days = block.days if hasattr(block, 'days') and block.days else None
                    if not block_days and block.content_type in ("tag", "episodic"):
                        content_parts = block.content_value.split("|")
                        if len(content_parts) >= 2:
                            block_days = [d.strip() for d in content_parts[1].split(",") if d.strip()]
                    applies_today = (not block_days) or (weekday in get_weekday_indices(block_days))
                    if not applies_today:
                        continue

                    desired_start = datetime.combine(target_date, parse_time_string(block.start_time).time())
                    gap_fill_ids = {TimeBlock.from_dict(bd).block_id for bd in gap_fill_blocks}
                    specific_block_ids_snap = {TimeBlock.from_dict(bd).block_id for bd in specific_blocks}

                    # Collect specific block intervals (e.g. episodic fixed slots)
                    specific_intervals = []
                    for e in schedule_entries:
                        if e.get("daypart_block_id") in specific_block_ids_snap:
                            es = datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time())
                            ee = es + timedelta(seconds=e.get("duration", 5400))
                            specific_intervals.append((es, ee))
                    # Merge overlapping specific intervals into contiguous blocks
                    specific_intervals.sort()
                    merged_specific = []
                    for sp_s, sp_e in specific_intervals:
                        if merged_specific and sp_s <= merged_specific[-1][1]:
                            merged_specific[-1] = (merged_specific[-1][0], max(merged_specific[-1][1], sp_e))
                        else:
                            merged_specific.append((sp_s, sp_e))

                    # Step 1: find the gap fill video at desired_start and snap to its start
                    # (only if it doesn't land inside a specific block)
                    MAX_LOOKBACK = timedelta(minutes=45)
                    actual_start = desired_start
                    for e in schedule_entries:
                        if e.get("daypart_block_id") not in gap_fill_ids:
                            continue
                        gf_start = datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time())
                        gf_end = gf_start + timedelta(seconds=e.get("duration", 5400))
                        if gf_start <= desired_start <= gf_end:
                            if desired_start - gf_start <= MAX_LOOKBACK:
                                in_specific = any(gf_start >= sp_s and gf_start < sp_e
                                                  for sp_s, sp_e in merged_specific)
                                if not in_specific:
                                    actual_start = gf_start
                            break

                    # Step 2: if actual_start lands inside or overlaps a specific block,
                    # Step 2: push actual_start past any specific block it overlaps or runs into
                    changed = True
                    while changed:
                        changed = False
                        for sp_s, sp_e in merged_specific:
                            # actual_start is inside specific block
                            if actual_start < sp_e and actual_start >= sp_s:
                                actual_start = sp_e
                                changed = True
                                break
                            # desired_start is inside specific block
                            if desired_start >= sp_s and desired_start < sp_e:
                                actual_start = sp_e
                                changed = True
                                break
                            # actual_start is before specific block — check if gap fill video
                            # at actual_start runs into the specific block
                            if actual_start < sp_s:
                                for e in schedule_entries:
                                    if e.get("daypart_block_id") not in gap_fill_ids:
                                        continue
                                    e_s = datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time())
                                    if e_s == actual_start:
                                        e_e = e_s + timedelta(seconds=e.get("duration", 5400))
                                        if e_e > sp_s:
                                            actual_start = sp_e
                                            changed = True
                                        break
                                if changed:
                                    break

                    logger.info(f"[{channel}] Approximate block {block.block_id}: "
                                f"desired={desired_start.strftime('%H:%M')} → placed at {actual_start.strftime('%H:%M')}")

                    block_entries = generate_block_schedule(
                        block, available_videos, recent_videos, channel,
                        start_datetime=actual_start,
                        preview_mode=preview_mode,
                        preview_ep_state=preview_ep_state
                    )
                    schedule_entries.extend(block_entries)

                # After all approximate blocks are placed, re-adjust episodic entries
                # that now start inside an approximate block's time range.
                # Shift the entire episodic sequence forward to start after the conflict.
                for ep_block_data in specific_blocks:
                    ep_block = TimeBlock.from_dict(ep_block_data)
                    if ep_block.content_type != "episodic":
                        continue
                    ep_entries = sorted(
                        [e for e in schedule_entries if e.get("daypart_block_id") == ep_block.block_id],
                        key=lambda e: e["time"]
                    )
                    if not ep_entries:
                        continue
                    ep_first_start = datetime.combine(target_date, datetime.strptime(ep_entries[0]["time"], "%H:%M:%S").time())
                    # Find latest end of any non-episodic entry that ends after ep_first_start
                    latest_conflict_end = ep_first_start
                    for e in schedule_entries:
                        if e.get("daypart_block_id") == ep_block.block_id:
                            continue
                        e_start = datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time())
                        e_end = e_start + timedelta(seconds=e.get("duration", 5400))
                        if e_end > ep_first_start:
                            latest_conflict_end = max(latest_conflict_end, e_end)
                    if latest_conflict_end > ep_first_start:
                        shift = latest_conflict_end - ep_first_start
                        logger.info(f"[{channel}] Shifting episodic block {ep_block.block_id} "
                                    f"by {shift.total_seconds()/60:.1f} min to {latest_conflict_end.strftime('%H:%M')} "
                                    f"due to approximate block overlap")
                        for e in ep_entries:
                            orig = datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time())
                            e["time"] = (orig + shift).strftime("%H:%M:%S")

                # Re-fill any remaining gaps around all placed blocks (specific + approximate)
                all_block_ids = ({TimeBlock.from_dict(bd).block_id for bd in specific_blocks}
                                 | {TimeBlock.from_dict(bd).block_id for bd in approximate_blocks})
                schedule_entries[:] = [e for e in schedule_entries
                                       if e.get("daypart_block_id") in all_block_ids]

                final_occupied = sorted(
                    [(datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time()),
                      datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time())
                      + timedelta(seconds=e.get("duration", 5400)))
                     for e in schedule_entries],
                    key=lambda x: x[0]
                )
                final_windows = []
                cursor2 = fill_from
                approx_block_ids = {TimeBlock.from_dict(bd).block_id for bd in approximate_blocks}
                for occ_start, occ_end in final_occupied:
                    if cursor2 < occ_start:
                        final_windows.append((cursor2, occ_start))
                    cursor2 = max(cursor2, occ_end)
                if cursor2 < day_end_dt:
                    final_windows.append((cursor2, day_end_dt))
                # Fill windows: use strict_fit so videos fill continuously without gaps
                _fill_windows(final_windows, strict_fit=True)

                # Remove any gap fill entries that start inside an approximate block's time range
                # (can happen when a strict_fit entry overruns and the post-block fill overlaps)
                approx_intervals = []
                for e in schedule_entries:
                    if e.get("daypart_block_id") in approx_block_ids:
                        e_start = datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time())
                        e_end = e_start + timedelta(seconds=e.get("duration", 5400))
                        approx_intervals.append((e_start, e_end))

                def _overlaps_approx(entry):
                    if entry.get("daypart_block_id") in approx_block_ids:
                        return False  # keep approx entries themselves
                    e_start = datetime.combine(target_date, datetime.strptime(entry["time"], "%H:%M:%S").time())
                    for a_start, a_end in approx_intervals:
                        if e_start >= a_start and e_start < a_end:
                            return True
                    return False

                schedule_entries[:] = [e for e in schedule_entries if not _overlaps_approx(e)]

        # Snap episodic blocks to the nearest video boundary after all placement is done.
        # Algorithm (proven in test_episodic_snap.py):
        #   1. If a video is playing AT ep_configured → snap to its end
        #   2. Otherwise → snap to the latest video end <= ep_configured
        #   3. Remove gap fill entries that START inside the episodic slot
        #   4. Re-fill gaps around the snapped episodic
        if not is_marathon_day and gap_fill_blocks:
            gf_ids_snap = {TimeBlock.from_dict(bd).block_id for bd in gap_fill_blocks}
            approx_ids_snap = {TimeBlock.from_dict(bd).block_id for bd in approximate_blocks} if approximate_blocks else set()
            snap_search_ids = gf_ids_snap | approx_ids_snap
            MAX_SNAP_BACK = timedelta(minutes=90)

            for ep_bd in specific_blocks:
                ep_blk = TimeBlock.from_dict(ep_bd)
                if ep_blk.content_type != "episodic":
                    continue
                ep_ents = sorted(
                    [e for e in schedule_entries if e.get("daypart_block_id") == ep_blk.block_id],
                    key=lambda e: e["time"]
                )
                if not ep_ents:
                    continue

                ep_configured = datetime.combine(target_date, parse_time_string(ep_blk.start_time).time())
                ep_first = datetime.combine(target_date, datetime.strptime(ep_ents[0]["time"], "%H:%M:%S").time())

                # Find snap point
                playing_at_configured = None
                best_end_before = None
                for e in schedule_entries:
                    if e.get("daypart_block_id") not in snap_search_ids:
                        continue
                    e_s = datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time())
                    e_e = e_s + timedelta(seconds=e.get("duration", 5400))
                    if e_s <= ep_configured and e_e > ep_configured and e_e <= ep_configured + MAX_SNAP_BACK:
                        if playing_at_configured is None or e_e > playing_at_configured:
                            playing_at_configured = e_e
                    elif e_e <= ep_configured:
                        if best_end_before is None or e_e > best_end_before:
                            best_end_before = e_e

                snap_to = playing_at_configured if playing_at_configured is not None else best_end_before
                if snap_to is None or snap_to == ep_first:
                    continue

                # Shift episodic entries
                shift = snap_to - ep_first
                logger.info(f"[{channel}] Episodic snap: {ep_blk.block_id} "
                            f"{ep_first.strftime('%H:%M')} → {snap_to.strftime('%H:%M')}")
                for e in ep_ents:
                    orig = datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time())
                    e["time"] = (orig + shift).strftime("%H:%M:%S")

                # Compute new episodic slot (truncate to seconds for comparison)
                ep_start = datetime.combine(target_date, datetime.strptime(ep_ents[0]["time"], "%H:%M:%S").time())
                ep_end_raw = datetime.combine(target_date, datetime.strptime(ep_ents[-1]["time"], "%H:%M:%S").time()) \
                             + timedelta(seconds=ep_ents[-1].get("duration", 5400))
                # Truncate to seconds to avoid sub-second precision issues
                ep_end = ep_end_raw.replace(microsecond=0)

                # Remove entries that START inside the episodic slot (gap fill + approximate)
                schedule_entries[:] = [
                    e for e in schedule_entries
                    if e.get("daypart_block_id") == ep_blk.block_id
                    or not (
                        e.get("daypart_block_id") in snap_search_ids
                        and ep_start <= datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time()) < ep_end
                    )
                ]

                # Re-fill gaps around the snapped episodic:
                # Strip all gap fill entries, then re-fill cleanly around
                # the episodic (and approximate blocks if any).
                non_gf_ids = {ep_blk.block_id} | approx_ids_snap
                # Keep episodic + approximate blocks; strip all gap fill
                schedule_entries[:] = [
                    e for e in schedule_entries
                    if e.get("daypart_block_id") in non_gf_ids
                    or e.get("daypart_block_id") not in snap_search_ids
                ]
                # Also keep specific blocks that aren't episodic
                # (already handled — non_gf_ids covers episodic, approx covers approx)

                all_occ = sorted(
                    [(datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time()),
                      datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time())
                      + timedelta(seconds=e.get("duration", 5400)))
                     for e in schedule_entries],
                    key=lambda x: x[0]
                )
                refill_wins = []
                cur = fill_from
                for occ_s, occ_e in all_occ:
                    if cur < occ_s:
                        refill_wins.append((cur, occ_s))
                    cur = max(cur, occ_e)
                if cur < day_end_dt:
                    refill_wins.append((cur, day_end_dt))
                _fill_windows(refill_wins, strict_fit=True)

                # Final cleanup: remove any gap fill that starts inside episodic slot
                # (strict_fit refill may overrun into it)
                schedule_entries[:] = [
                    e for e in schedule_entries
                    if e.get("daypart_block_id") == ep_blk.block_id
                    or not (
                        e.get("daypart_block_id") in snap_search_ids
                        and ep_start <= datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time()) < ep_end
                    )
                ]

    # 2b. TEMPORARILY DISABLED - approximate blocks are handled AFTER gap filling now
    # print("[generate_daypart_schedule] Calling _handle_approximate_blocks...")
    # _handle_approximate_blocks(
    #     schedule_entries,
    #     daypart_inner.get("time_blocks", []),
    #     daypart_inner,
    #     weekday,
    #     target_date,
    #     channel,
    #     available_videos,
    #     recent_videos
    # )
    
    # After approximate handling, recalculate current_time from the last scheduled entry
    if schedule_entries:
        last_entry = schedule_entries[-1]
        last_entry_time = datetime.strptime(last_entry["time"], "%H:%M:%S")
        last_entry_duration = last_entry.get("duration", 5400)
        last_entry_end = datetime.combine(target_date, last_entry_time.time()) + timedelta(seconds=last_entry_duration)
        current_time = last_entry_end
    
    # 3. Detect and fill gaps (only if not marathon day and gap filler enabled)
    if not is_marathon_day:
        gap_filler_config = GapFillerConfig.from_dict(daypart_inner.get("gap_filler", {}))
        
        if gap_filler_config.enabled:
            # Filter time blocks that apply to this day (same logic as block application)
            time_blocks_today = []
            for block_data in daypart_inner.get("time_blocks", []):
                block = TimeBlock.from_dict(block_data)
                
                # Get block days
                block_days = block.days if hasattr(block, 'days') and block.days else None
                
                if not block_days and block.content_type == "tag":
                    # Try to extract days from content_value (backward compatibility)
                    content_parts = block.content_value.split("|")
                    if len(content_parts) >= 2:
                        days_str = content_parts[1]
                        block_days = [d.strip() for d in days_str.split(",") if d.strip()]
                
                # Check if this block applies to today
                if block.content_type == "video" or not block_days:
                    # Video blocks or tag blocks without specific days apply to all days
                    time_blocks_today.append(block)
                elif weekday in get_weekday_indices(block_days):
                    # Tag block with specific days - check if today is in the list
                    time_blocks_today.append(block)
            
            # Only fill gaps if there are blocks for this day
            # If no blocks apply to this day, skip gap filling entirely
            if not time_blocks_today:
                # Check if we should still fill gaps (gap_filler enabled with videos)
                # This handles the case where no time blocks exist but we want to fill the day
                if gap_filler_config.enabled and available_videos:
                    logger.info(f"[{channel}] No blocks but gap filler enabled - filling full day")
                    # Determine actual start: cross-day continuity or midnight
                    if base_datetime and base_datetime.date() < target_date:
                        gap_start_str = base_datetime.strftime("%H:%M")
                    else:
                        gap_start_str = "00:00"
                    gap_entries = fill_gaps_with_random(
                        [(gap_start_str, "24:00")],
                        available_videos,
                        gap_filler_config,
                        recent_videos,
                        channel,
                        base_datetime=None,
                        target_date=target_date
                    )
                    schedule_entries.extend(gap_entries)
                else:
                    logger.info(f"[{channel}] No blocks for this day ({target_date.strftime('%A')}), skipping gap filling")
            else:
                # Use actual scheduled end times to define gap boundaries,
                # so gap filler starts exactly where the last video ended.
                gaps = _gaps_from_actual_ends(
                    schedule_entries, time_blocks_today, target_date, current_time, base_datetime
                )
                
                if gaps:
                    logger.info(f"[{channel}] Filling {len(gaps)} gap(s): {gaps}")
                    # Gaps already have correct start times from _gaps_from_actual_ends.
                    # Pass base_datetime=None so fill_gaps_with_random uses the gap
                    # start string directly without date-comparison confusion.
                    for gap_start, gap_end in gaps:
                        gap_entries = fill_gaps_with_random(
                            [(gap_start, gap_end)],
                            available_videos,
                            gap_filler_config,
                            recent_videos,
                            channel,
                            base_datetime=None,
                            target_date=target_date
                        )
                        schedule_entries.extend(gap_entries)
                else:
                    logger.info(f"[{channel}] No gaps to fill")
    
    # Approximate blocks without gap fill: place them into the first free slot
    # at or after their configured start time.
    if not is_marathon_day and not gap_fill_blocks and approximate_blocks:
        for block_data in approximate_blocks:
            block = TimeBlock.from_dict(block_data)
            block.collection_file = block_data.get("collection_file", "") or ""

            block_days = block.days if hasattr(block, 'days') and block.days else None
            if not block_days and block.content_type in ("tag", "episodic"):
                content_parts = block.content_value.split("|")
                if len(content_parts) >= 2:
                    block_days = [d.strip() for d in content_parts[1].split(",") if d.strip()]
            applies_today = (not block_days) or (weekday in get_weekday_indices(block_days))
            if not applies_today:
                continue

            desired_start = datetime.combine(target_date, parse_time_string(block.start_time).time())
            block_duration = timedelta(seconds=block.duration_seconds)

            all_occupied = []
            for e in schedule_entries:
                occ_start = datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time())
                occ_end = occ_start + timedelta(seconds=e.get("duration", 5400))
                all_occupied.append((occ_start, occ_end))
            all_occupied.sort(key=lambda x: x[0])

            candidate = desired_start
            changed = True
            while changed:
                changed = False
                for occ_start, occ_end in all_occupied:
                    if occ_start <= candidate < occ_end:
                        candidate = occ_end
                        changed = True
                        break
                    if candidate < occ_start < candidate + block_duration:
                        candidate = occ_end
                        changed = True
                        break

            logger.info(f"[{channel}] Approximate block {block.block_id} (no-gapfill): "
                        f"desired={desired_start.strftime('%H:%M')} → placed at {candidate.strftime('%H:%M')}")
            block_entries = generate_block_schedule(
                block, available_videos, recent_videos, channel,
                start_datetime=candidate,
                preview_mode=preview_mode,
                preview_ep_state=preview_ep_state
            )
            schedule_entries.extend(block_entries)
    
    # After approximate handling, sort entries by time
    # 4. Sort by time
    schedule_entries.sort(key=lambda e: e["time"])
    
    # Track the last time used for continuous scheduling
    # Calculate the actual end time of the last entry for proper day-to-day continuity
    last_datetime = current_time
    if schedule_entries:
        last_entry = schedule_entries[-1]
        last_entry_time = datetime.combine(target_date, datetime.strptime(last_entry["time"], "%H:%M:%S").time())
        # Get video duration from the entry if available
        duration = last_entry.get("duration", 0)
        if not duration:
            # Try to get duration from the file path or use default
            # Default to 90 minutes if not available
            duration = 5400  # 90 minutes in seconds
        # Calculate the end time by adding video duration
        last_datetime = last_entry_time + timedelta(seconds=duration)

        # IMPORTANT: Do NOT reset to midnight!
        # We must preserve the actual end time for cross-day continuity.
        # If a video ends at 23:54, the next day should start at 23:54.
        # Resetting to midnight creates unwanted gaps in the schedule.
        # The caller (mixin or scheduler) will handle starting fresh at midnight
        # when appropriate by passing no base_datetime or midnight base_datetime.
        # 
        # Previously, we had code here that reset to midnight when the schedule
        # ran past midnight. This was WRONG because it broke cross-day continuity.
        # The correct behavior is to return the actual end time so the next day
        # can continue from where this day left off.
        pass  # Keep the actual end time
        
        # NOTE: The gap-filling logic in lines 925-942 handles adjusting gaps
        # when continuing from a previous day. This is the correct approach,
        # not resetting last_datetime.
    
    logger.info(f"[{channel}] Completed {target_date}, last_datetime={last_datetime}, entries={len(schedule_entries)}")
    
    return schedule_entries, last_datetime


# ============================================================================
# PERSISTENCE
# ============================================================================

def load_daypart_config(channel: str) -> Optional[dict]:
    """
    Load daypart configuration for a channel.
    
    Args:
        channel: Channel name
    
    Returns:
        Daypart config dict or None if not found
    """
    config_file = SCHEDULE_DIR / f"daypart_{channel}.json"
    
    if not config_file.exists():
        logger.debug(f"[{channel}] No daypart config found at {config_file}")
        return None
    
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            logger.info(f"[{channel}] Loaded daypart config from {config_file}")
            return config
    except Exception as e:
        logger.error(f"[{channel}] Failed to load daypart config: {e}")
        return None


def save_daypart_config(channel: str, config: dict) -> bool:
    """
    Save daypart configuration for a channel.
    
    Args:
        channel: Channel name
        config: Daypart config dict
    
    Returns:
        True if saved successfully
    """
    config_file = SCHEDULE_DIR / f"daypart_{channel}.json"
    
    try:
        # Validate before saving
        errors = validate_daypart_config(config)
        if errors:
            logger.error(f"[{channel}] Daypart config validation failed: {errors}")
            return False
        
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"[{channel}] Saved daypart config to {config_file}")
        return True
    except Exception as e:
        logger.error(f"[{channel}] Failed to save daypart config: {e}")
        return False


def validate_daypart_config(config: dict) -> List[str]:
    """
    Validate daypart configuration.
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Check required sections
    if "daypart_config" not in config:
        return ["Missing 'daypart_config' section"]
    
    dp = config["daypart_config"]
    
    # Validate time blocks
    blocks = []
    for i, block_data in enumerate(dp.get("time_blocks", [])):
        try:
            block = TimeBlock.from_dict(block_data)
            error = validate_time_block(block)
            if error:
                errors.append(f"Block {i}: {error}")
            else:
                blocks.append(block)
        except KeyError as e:
            errors.append(f"Block {i}: Missing required field {e}")
        except Exception as e:
            errors.append(f"Block {i}: Invalid data: {e}")
    
    # Check for overlaps
    if has_overlapping_blocks(blocks):
        errors.append("Time blocks overlap")
    
    # Check total block time doesn't exceed 24 hours (excluding marathons)
    total_seconds = sum(b.duration_seconds for b in blocks)
    if total_seconds > 86400:
        errors.append(f"Total block time exceeds 24 hours: {total_seconds/3600:.1f} hours")
    
    # Validate marathons
    for i, marathon in enumerate(dp.get("marathons", [])):
        if not marathon.get("tag"):
            errors.append(f"Marathon {i}: Missing tag")
        if not marathon.get("days"):
            errors.append(f"Marathon {i} (tag={marathon.get('tag')}): No days selected")
        # Check tag is string
        if not isinstance(marathon.get("tag"), str):
            errors.append(f"Marathon {i}: Tag must be a string")
        # Check days is list
        if not isinstance(marathon.get("days"), list):
            errors.append(f"Marathon {i}: Days must be a list")
    
    # Validate gap filler
    gap_filler_data = dp.get("gap_filler", {})
    if not isinstance(gap_filler_data, dict):
        errors.append("gap_filler must be a dictionary")
    else:
        # Check source
        source = gap_filler_data.get("source", "all")
        if source not in ["all", "collections", "tags"]:
            errors.append(f"Invalid gap_filler source: {source}")
        # If source is collections, check collection_ids
        if source == "collections" and not gap_filler_data.get("collection_ids"):
            errors.append("gap_filler source='collections' but no collection_ids specified")
        # If source is tags, check tags
        if source == "tags" and not gap_filler_data.get("tags"):
            errors.append("gap_filler source='tags' but no tags specified")
    
    return errors


# ============================================================================
# MAIN SCHEDULER CLASS
# ============================================================================

class DaypartScheduler:
    """
    Main daypart scheduler class for managing daypart configurations.
    """
    
    def __init__(self):
        self.configs: Dict[str, dict] = {}  # channel -> config
        self.enabled_channels: set = set()
    
    def load_config(self, channel: str) -> Optional[dict]:
        """Load and cache daypart config for a channel"""
        if channel in self.configs:
            return self.configs[channel]
        
        config = load_daypart_config(channel)
        if config:
            self.configs[channel] = config
        return config
    
    def save_config(self, channel: str, config: dict) -> bool:
        """Save daypart config for a channel"""
        success = save_daypart_config(channel, config)
        if success:
            self.configs[channel] = config
        return success
    
    def is_enabled(self, channel: str) -> bool:
        """Check if daypart scheduling is enabled for a channel"""
        config = self.load_config(channel)
        if not config:
            return False
        return config.get("enabled", False)
    
    def enable_channel(self, channel: str, enabled: bool = True):
        """Enable/disable daypart scheduling for a channel"""
        config = self.load_config(channel) or {}
        config["enabled"] = enabled
        self.save_config(channel, config)
        
        if enabled:
            self.enabled_channels.add(channel)
        else:
            self.enabled_channels.discard(channel)
    
    def generate_schedule_for_day(self, channel: str, target_date: date = None) -> List[dict]:
        """
        Generate schedule for a specific channel and date.
        
        Args:
            channel: Channel name
            target_date: Date to generate (default: today)
        
        Returns:
            List of schedule entries
        """
        if target_date is None:
            target_date = date.today()
        
        config = self.load_config(channel)
        if not config:
            logger.warning(f"[{channel}] No daypart config found")
            return []
        
        if not config.get("enabled", False):
            logger.info(f"[{channel}] Daypart scheduling disabled")
            return []
        
        # Get available videos (to be implemented by caller)
        # This is a placeholder - the actual video loading happens in scheduler.py
        logger.warning(f"[{channel}] generate_schedule_for_day() requires video pool - should be called from scheduler.py")
        return []
    
    def clear_cache(self):
        """Clear cached configurations"""
        self.configs.clear()
        self.enabled_channels.clear()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_default_daypart_config() -> dict:
    """Create a default daypart configuration template"""
    return {
        "metadata": {
            "version": "2.0",
            "schedule_type": "daypart",
            "created": datetime.now().isoformat()
        },
        "daypart_config": {
            "time_blocks": [],
            "marathons": [],
            "gap_filler": {
                "enabled": True,
                "source": "all",
                "collection_ids": [],
                "tags": [],
                "excluded_tags": [],
                "respect_24h_norepeat": True,
                "shuffle": True
            }
        },
        "weekly": {},
        "calendar": {},
        "enabled": False
    }


def get_available_tags_from_collections(collections: List[dict]) -> List[str]:
    """Extract all unique tags from a list of collections"""
    tags = set()
    for collection in collections:
        collection_tags = collection.get("tags", [])
        if isinstance(collection_tags, list):
            tags.update(collection_tags)
    return sorted(list(tags))


# ============================================================================
# UNIT TEST SUPPORT
# ============================================================================

if __name__ == "__main__":
    # Simple sanity tests
    print("Testing TimeBlock...")
    block = TimeBlock("06:00", "10:00", "tag", "kids")
    assert block.duration_seconds == 14400
    print("[PASS] TimeBlock duration: {}s".format(block.duration_seconds))
    
    block_dict = block.to_dict()
    block2 = TimeBlock.from_dict(block_dict)
    assert block2.start_time == block.start_time
    print("[PASS] TimeBlock serialization/deserialization")
    
    print("\nTesting gap detection...")
    blocks = [
        TimeBlock("06:00", "10:00", "tag", "kids"),
        TimeBlock("12:00", "14:00", "tag", "documentary"),
        TimeBlock("20:00", "24:00", "tag", "horror")
    ]
    gaps = detect_gaps(blocks)
    expected_gaps = [("00:00", "06:00"), ("10:00", "12:00"), ("14:00", "20:00")]
    assert gaps == expected_gaps, "Expected {}, got {}".format(expected_gaps, gaps)
    print("[PASS] Gaps detected: {}".format(gaps))
    
    print("\nTesting overlap detection...")
    overlapping_blocks = [
        TimeBlock("06:00", "10:00", "tag", "a"),
        TimeBlock("09:00", "12:00", "tag", "b")  # Overlaps
    ]
    assert has_overlapping_blocks(overlapping_blocks), "Should detect overlap"
    print("[PASS] Overlap detection works")
    
    non_overlapping = [
        TimeBlock("06:00", "10:00", "tag", "a"),
        TimeBlock("10:00", "12:00", "tag", "b")  # Exactly adjacent
    ]
    assert not has_overlapping_blocks(non_overlapping), "Should not detect overlap for adjacent blocks"
    print("[PASS] Adjacent blocks are not overlapping")
    
    print("\nTesting MarathonConfig...")
    marathon = MarathonConfig("80s", ["friday", "saturday"])
    assert marathon.tag == "80s"
    assert "friday" in marathon.days
    print("[PASS] MarathonConfig works")
    
    print("\nTesting GapFillerConfig...")
    gap_config = GapFillerConfig(enabled=True, source="all", excluded_tags=["horror"])
    assert gap_config.enabled
    assert "horror" in gap_config.excluded_tags
    print("[PASS] GapFillerConfig works")
    
    print("\nAll basic tests passed!")
