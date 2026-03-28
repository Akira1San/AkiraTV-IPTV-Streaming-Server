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
                 block_id: str = None, days: list = None, video_count: str = None):
        self.block_id = block_id or f"block_{uuid.uuid4().hex[:8]}"
        self.start_time = start_time
        self.end_time = end_time
        self.content_type = content_type  # "video" or "tag"
        self.content_value = content_value
        self.days = days or []  # List of days for tag blocks
        self.video_count = video_count  # "single", "2", "3", "all", etc.
        
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
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TimeBlock':
        """Deserialize from dictionary"""
        return cls(
            start_time=data["start_time"],
            end_time=data["end_time"],
            content_type=data["content_type"],
            content_value=data["content_value"],
            block_id=data.get("block_id"),
            days=data.get("days", []),
            video_count=data.get("video_count")
        )


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
    if block.content_type not in ["video", "tag"]:
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
                           channel: str = "") -> List[dict]:
    """
    Generate schedule entries for a time block.
    
    Args:
        block: TimeBlock configuration
        available_videos: Pool of videos to choose from
        recent_videos: List of (video_path, timestamp) for 24h rule
        channel: Channel name for logging
    
    Returns:
        List of schedule entries for this block
    """
    if recent_videos is None:
        recent_videos = []
    
    entries = []
    block_duration = block.duration_seconds
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
        
        # Check collection tags (videos inherit tags from their collection)
        tag_videos = [v for v in available_videos if tag in v.get("collection", {}).get("tags", [])]
        
        if not tag_videos:
            logger.warning(f"[{channel}] No videos found for tag: {tag}")
            return entries
        
        # Determine max videos to play
        max_videos = None
        if video_count == "all":
            max_videos = len(tag_videos)
        elif video_count != "single":
            try:
                max_videos = int(video_count)
            except (ValueError, TypeError):
                max_videos = None
        
        # Fill the block with videos from this tag
        video_index = 0
        while current_time < end_time:
            # Check if we've reached the video count limit
            if max_videos is not None and video_index >= max_videos:
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
    tag_videos = [v for v in available_videos if tag in v.get("tags", [])]
    
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
                         channel: str = "") -> List[dict]:
    """
    Fill each gap with random video selections.
    
    Args:
        gaps: List of (start, end) time tuples
        available_videos: Pool of videos
        gap_filler_config: Configuration
        recent_videos: For 24h rule tracking
        channel: Channel name
    
    Returns:
        List of schedule entries for gap content
    """
    if recent_videos is None:
        recent_videos = []
    
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
        current_time = parse_time_string(gap_start)
        end_time = parse_time_string(gap_end)
        
        # Handle overnight gap
        if end_time < current_time:
            end_time += timedelta(days=1)
        
        # Track videos used in this gap (for 24h rule if enabled)
        gap_recent = [] if gap_filler_config.respect_24h_norepeat else None
        
        while current_time < end_time:
            # Filter available videos (use pre-filtered list)
            candidates = filtered_videos.copy()
            
            # Apply excluded tags
            if gap_filler_config.excluded_tags:
                candidates = [v for v in candidates 
                            if not has_excluded_tag(v, gap_filler_config.excluded_tags)]
            
            if not candidates:
                # Emergency: try without exclusions
                candidates = filtered_videos
                logger.warning(f"[{channel}] Gap filler: No candidates after exclusions, using filtered videos")
            
            # Apply 24h no-repeat rule
            if gap_filler_config.respect_24h_norepeat:
                recent_paths = {path for path, _ in recent_videos}
                candidates = [v for v in candidates if v["path"] not in recent_paths]
                
                if not candidates:
                    # Reset recent videos and try again
                    logger.info(f"[{channel}] Gap filler: All videos used in last 24h, resetting")
                    candidates = filtered_videos
                    recent_videos.clear()
            
            if not candidates:
                logger.error(f"[{channel}] Gap filler: No videos available at all!")
                break
            
            # Select video
            if gap_filler_config.shuffle:
                selected = random.choice(candidates)
            else:
                # Sequential - pick first
                selected = candidates[0]
            
            # Add to schedule
            entry = {
                "time": current_time.strftime("%H:%M:%S"),
                "file": selected["path"],
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


def generate_daypart_schedule(daypart_config: dict, available_videos: List[dict],
                             channel: str, target_date: date) -> List[dict]:
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
    
    Returns:
        List of schedule entries sorted by time
    """
    schedule_entries = []
    recent_videos = []  # For 24h no-repeat tracking
    
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
        
        for block_data in time_blocks:
            block = TimeBlock.from_dict(block_data)
            
            # Parse days from content_value if not set (for backward compatibility)
            # Format: "tag_name|monday,tuesday,friday|single"
            block_days = block.days if hasattr(block, 'days') and block.days else None
            
            if not block_days and block.content_type == "tag":
                # Try to extract days from content_value
                content_parts = block.content_value.split("|")
                if len(content_parts) >= 2:
                    days_str = content_parts[1]
                    block_days = [d.strip() for d in days_str.split(",") if d.strip()]
            
            if block.content_type == "tag" and block_days:
                # Tag block with specific days - check if today is in the list
                if weekday in get_weekday_indices(block_days):
                    block_entries = generate_block_schedule(
                        block, 
                        available_videos,
                        recent_videos,
                        channel
                    )
                    schedule_entries.extend(block_entries)
            else:
                # Video block or tag block without specific days - apply to all days
                block_entries = generate_block_schedule(
                    block, 
                    available_videos,
                    recent_videos,
                    channel
                )
                schedule_entries.extend(block_entries)
    
    # 3. Detect and fill gaps (only if not marathon day and gap filler enabled)
    if not is_marathon_day:
        gap_filler_config = GapFillerConfig.from_dict(daypart_inner.get("gap_filler", {}))
        
        if gap_filler_config.enabled:
            time_blocks = [TimeBlock.from_dict(b) for b in daypart_inner.get("time_blocks", [])]
            gaps = detect_gaps(time_blocks)
            
            if gaps:
                logger.info(f"[{channel}] Filling {len(gaps)} gap(s): {gaps}")
                gap_entries = fill_gaps_with_random(
                    gaps,
                    available_videos,
                    gap_filler_config,
                    recent_videos,
                    channel
                )
                schedule_entries.extend(gap_entries)
            else:
                logger.info(f"[{channel}] No gaps to fill")
    
    # 4. Sort by time
    schedule_entries.sort(key=lambda e: e["time"])
    
    return schedule_entries


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
