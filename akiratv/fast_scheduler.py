#!/usr/bin/env python3
"""
AkiraTV Fast Scheduler
Dynamic, in-memory scheduling system that creates schedules on-the-fly
without requiring JSON files.
"""

import json
import time
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import threading
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ScheduleEntry:
    """Single schedule entry"""
    time: str  # HH:MM format
    video_name: str
    video_path: str
    duration: float  # in seconds
    entry_type: str = "content"  # "content", "bumper", "trailer"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class FastScheduleState:
    """Current state of the fast scheduler"""
    channel_name: str
    current_entry: Optional[ScheduleEntry] = None
    current_position: float = 0.0  # seconds into current video
    schedule_entries: List[ScheduleEntry] = None
    last_update: str = ""
    is_running: bool = False
    
    def __post_init__(self):
        if self.schedule_entries is None:
            self.schedule_entries = []

class FastScheduler:
    """
    Fast Scheduler - Dynamic scheduling system
    
    Features:
    - Creates schedules from collection libraries
    - In-memory dictionary-based storage
    - Crash recovery with resume functionality
    - Dynamic bumpers and trailers
    - Checkpoint/restore system
    """
    
    def __init__(self, channel_name: str, config_dir: str = "user"):
        self.channel_name = channel_name
        self.config_dir = Path(config_dir)
        self.collections_dir = self.config_dir / "collections"
        self.checkpoints_dir = self.config_dir / "fast_schedules"
        self.checkpoints_dir.mkdir(exist_ok=True)
        
        # Schedule state
        self.state = FastScheduleState(channel_name=channel_name)
        self.available_videos = []  # List of all available videos from collections
        self.bumpers = []  # List of bumper videos
        self.trailers = []  # List of trailer videos
        
        # Settings
        self.schedule_length_hours = 24  # Generate 24 hours of content
        self.bumper_frequency = 3  # Insert bumper every N videos
        self.trailer_probability = 0.3  # 30% chance to show trailer before video
        
        # Threading
        self._lock = threading.Lock()
        
        logger.info(f"FastScheduler initialized for channel '{channel_name}'")
    
    def load_collections(self, collection_names: List[str] = None) -> Dict[str, Any]:
        """
        Load videos from collection files
        
        Args:
            collection_names: List of collection names to load, or None for all
            
        Returns:
            {"success": bool, "message": str, "videos_loaded": int}
        """
        try:
            self.available_videos = []
            loaded_count = 0
            
            # Get collection files
            if collection_names is None:
                collection_files = list(self.collections_dir.glob("collections_*.json"))
            else:
                collection_files = [
                    self.collections_dir / f"collections_{name}.json" 
                    for name in collection_names
                ]
            
            for collection_file in collection_files:
                if not collection_file.exists():
                    logger.warning(f"Collection file not found: {collection_file}")
                    continue
                    
                try:
                    with open(collection_file, 'r', encoding='utf-8') as f:
                        collection_data = json.load(f)
                    
                    # Extract videos from collection - handle both formats
                    if isinstance(collection_data, dict):
                        # Check if it's the new format with "collections" array
                        if 'collections' in collection_data and isinstance(collection_data['collections'], list):
                            # New format: {"collections": [{"id": "...", "videos": [...]}]}
                            for collection in collection_data['collections']:
                                if 'videos' in collection and isinstance(collection['videos'], list):
                                    for video in collection['videos']:
                                        if 'path' in video:
                                            video_entry = {
                                                'name': collection.get('name', collection.get('id', 'Unknown')),
                                                'path': video['path'],
                                                'duration': video.get('duration', 3600),  # Default 1 hour
                                                'collection': collection_file.stem,
                                                'metadata': {
                                                    'id': collection.get('id'),
                                                    'description': collection.get('description', ''),
                                                    'genre': collection.get('genre', []),
                                                    'rating': collection.get('rating', 'NR'),
                                                    'year': collection.get('year')
                                                }
                                            }
                                            self.available_videos.append(video_entry)
                                            loaded_count += 1
                        else:
                            # Old format: {"video_name": {"path": "...", "duration": ...}}
                            for video_name, video_info in collection_data.items():
                                if isinstance(video_info, dict) and 'path' in video_info:
                                    video_entry = {
                                        'name': video_name,
                                        'path': video_info['path'],
                                        'duration': video_info.get('duration', 3600),  # Default 1 hour
                                        'collection': collection_file.stem,
                                        'metadata': video_info
                                    }
                                    self.available_videos.append(video_entry)
                                    loaded_count += 1
                                
                except Exception as e:
                    logger.error(f"Error loading collection {collection_file}: {e}")
                    continue
            
            logger.info(f"Loaded {loaded_count} videos from {len(collection_files)} collections")
            return {
                "success": True,
                "message": f"Loaded {loaded_count} videos from {len(collection_files)} collections",
                "videos_loaded": loaded_count
            }
            
        except Exception as e:
            error_msg = f"Failed to load collections: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def generate_schedule(self, start_time: str = "00:00") -> Dict[str, Any]:
        """
        Generate a dynamic schedule from available videos
        
        Args:
            start_time: Start time in HH:MM format
            
        Returns:
            {"success": bool, "message": str, "entries": int}
        """
        try:
            if not self.available_videos:
                return {"success": False, "error": "No videos available. Load collections first."}
            
            with self._lock:
                self.state.schedule_entries = []
                
                # Parse start time
                start_hour, start_minute = map(int, start_time.split(':'))
                current_time = datetime.now().replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
                
                # Generate schedule entries
                videos_added = 0
                bumpers_added = 0
                
                # Shuffle videos for variety
                shuffled_videos = self.available_videos.copy()
                random.shuffle(shuffled_videos)
                
                end_time = current_time + timedelta(hours=self.schedule_length_hours)
                
                while current_time < end_time and shuffled_videos:
                    # Add trailer before video (sometimes)
                    if self.trailers and random.random() < self.trailer_probability:
                        trailer = random.choice(self.trailers)
                        trailer_entry = ScheduleEntry(
                            time=current_time.strftime("%H:%M"),
                            video_name=f"Trailer: {trailer['name']}",
                            video_path=trailer['path'],
                            duration=trailer.get('duration', 30),
                            entry_type="trailer"
                        )
                        self.state.schedule_entries.append(trailer_entry)
                        current_time += timedelta(seconds=trailer['duration'])
                    
                    # Add main video
                    video = shuffled_videos.pop(0)
                    video_entry = ScheduleEntry(
                        time=current_time.strftime("%H:%M"),
                        video_name=video['name'],
                        video_path=video['path'],
                        duration=video['duration'],
                        entry_type="content",
                        metadata=video.get('metadata', {})
                    )
                    self.state.schedule_entries.append(video_entry)
                    current_time += timedelta(seconds=video['duration'])
                    videos_added += 1
                    
                    # Add bumper after every N videos
                    if self.bumpers and videos_added % self.bumper_frequency == 0:
                        bumper = random.choice(self.bumpers)
                        bumper_entry = ScheduleEntry(
                            time=current_time.strftime("%H:%M"),
                            video_name=f"Bumper: {bumper['name']}",
                            video_path=bumper['path'],
                            duration=bumper.get('duration', 10),
                            entry_type="bumper"
                        )
                        self.state.schedule_entries.append(bumper_entry)
                        current_time += timedelta(seconds=bumper['duration'])
                        bumpers_added += 1
                    
                    # Refill videos if we run out
                    if not shuffled_videos and current_time < end_time:
                        shuffled_videos = self.available_videos.copy()
                        random.shuffle(shuffled_videos)
                
                self.state.last_update = datetime.now().isoformat()
                
                logger.info(f"Generated schedule: {videos_added} videos, {bumpers_added} bumpers, {len(self.state.schedule_entries)} total entries")
                
                return {
                    "success": True,
                    "message": f"Generated schedule with {len(self.state.schedule_entries)} entries",
                    "entries": len(self.state.schedule_entries),
                    "videos": videos_added,
                    "bumpers": bumpers_added
                }
                
        except Exception as e:
            error_msg = f"Failed to generate schedule: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_current_entry(self) -> Optional[ScheduleEntry]:
        """Get the current schedule entry based on time"""
        if not self.state.schedule_entries:
            return None
            
        current_time = datetime.now().strftime("%H:%M")
        
        # Find the entry that should be playing now
        for i, entry in enumerate(self.state.schedule_entries):
            if entry.time <= current_time:
                # Check if this is still the current entry or if we've moved to the next
                if i + 1 < len(self.state.schedule_entries):
                    next_entry = self.state.schedule_entries[i + 1]
                    if next_entry.time > current_time:
                        return entry
                else:
                    # Last entry of the day
                    return entry
        
        # If no entry found, return the first one
        return self.state.schedule_entries[0] if self.state.schedule_entries else None
    
    def get_resume_position(self, entry: ScheduleEntry) -> float:
        """Calculate resume position for crashed/restarted playback"""
        if not entry:
            return 0.0
            
        current_time = datetime.now()
        entry_start = datetime.strptime(entry.time, "%H:%M").replace(
            year=current_time.year,
            month=current_time.month,
            day=current_time.day
        )
        
        # Calculate how many seconds into the video we should be
        elapsed_seconds = (current_time - entry_start).total_seconds()
        
        # Clamp to video duration
        resume_position = max(0, min(elapsed_seconds, entry.duration))
        
        return resume_position
    
    def save_checkpoint(self) -> Dict[str, Any]:
        """Save current state to checkpoint file"""
        try:
            checkpoint_file = self.checkpoints_dir / f"fast_schedule_{self.channel_name}.json"
            
            checkpoint_data = {
                "state": asdict(self.state),
                "available_videos": self.available_videos,
                "bumpers": self.bumpers,
                "trailers": self.trailers,
                "settings": {
                    "schedule_length_hours": self.schedule_length_hours,
                    "bumper_frequency": self.bumper_frequency,
                    "trailer_probability": self.trailer_probability
                },
                "saved_at": datetime.now().isoformat()
            }
            
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Checkpoint saved for channel '{self.channel_name}'")
            return {"success": True, "message": "Checkpoint saved"}
            
        except Exception as e:
            error_msg = f"Failed to save checkpoint: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def load_checkpoint(self) -> Dict[str, Any]:
        """Load state from checkpoint file"""
        try:
            checkpoint_file = self.checkpoints_dir / f"fast_schedule_{self.channel_name}.json"
            
            if not checkpoint_file.exists():
                return {"success": False, "error": "No checkpoint found"}
            
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            # Restore state
            state_data = checkpoint_data["state"]
            self.state = FastScheduleState(
                channel_name=state_data["channel_name"],
                current_entry=ScheduleEntry(**state_data["current_entry"]) if state_data.get("current_entry") else None,
                current_position=state_data.get("current_position", 0.0),
                schedule_entries=[ScheduleEntry(**entry) for entry in state_data.get("schedule_entries", [])],
                last_update=state_data.get("last_update", ""),
                is_running=state_data.get("is_running", False)
            )
            
            # Restore data
            self.available_videos = checkpoint_data.get("available_videos", [])
            self.bumpers = checkpoint_data.get("bumpers", [])
            self.trailers = checkpoint_data.get("trailers", [])
            
            # Restore settings
            settings = checkpoint_data.get("settings", {})
            self.schedule_length_hours = settings.get("schedule_length_hours", 24)
            self.bumper_frequency = settings.get("bumper_frequency", 3)
            self.trailer_probability = settings.get("trailer_probability", 0.3)
            
            logger.info(f"Checkpoint loaded for channel '{self.channel_name}'")
            return {
                "success": True,
                "message": "Checkpoint loaded",
                "entries": len(self.state.schedule_entries),
                "saved_at": checkpoint_data.get("saved_at")
            }
            
        except Exception as e:
            error_msg = f"Failed to load checkpoint: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def get_schedule_info(self) -> Dict[str, Any]:
        """Get current schedule information"""
        current_entry = self.get_current_entry()
        resume_position = self.get_resume_position(current_entry) if current_entry else 0.0
        
        return {
            "channel_name": self.channel_name,
            "total_entries": len(self.state.schedule_entries),
            "available_videos": len(self.available_videos),
            "current_entry": asdict(current_entry) if current_entry else None,
            "resume_position": resume_position,
            "last_update": self.state.last_update,
            "is_running": self.state.is_running,
            "settings": {
                "schedule_length_hours": self.schedule_length_hours,
                "bumper_frequency": self.bumper_frequency,
                "trailer_probability": self.trailer_probability
            }
        }
    
    def get_upcoming_entries(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get upcoming schedule entries"""
        current_time = datetime.now().strftime("%H:%M")
        upcoming = []
        
        for entry in self.state.schedule_entries:
            if entry.time >= current_time and len(upcoming) < count:
                upcoming.append(asdict(entry))
        
        return upcoming


# Example usage and testing
if __name__ == "__main__":
    # Test the Fast Scheduler
    scheduler = FastScheduler("test_channel")
    
    # Load collections
    result = scheduler.load_collections()
    print(f"Load collections: {result}")
    
    # Generate schedule
    result = scheduler.generate_schedule("09:00")
    print(f"Generate schedule: {result}")
    
    # Get current info
    info = scheduler.get_schedule_info()
    print(f"Schedule info: {json.dumps(info, indent=2)}")
    
    # Save checkpoint
    result = scheduler.save_checkpoint()
    print(f"Save checkpoint: {result}")