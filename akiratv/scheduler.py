# akiratv/scheduler.py
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
from pathlib import Path
import logging

BASE_DIR = Path(__file__).resolve().parents[1]  # C:\AkiraTV\AkiraTV
USER_DIR = BASE_DIR / "user"
SCHEDULE_DIR = USER_DIR / "schedules"

SCHEDULE_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("AkiraTV")

def get_full_todays_schedule() -> List[Dict[str, Any]]:
    """
    Load today's schedule entries and return only the current + future entries.
    
    Supports both calendar-specific entries and weekly recurring entries:
    - Calendar entries override weekly programming for special dates
    - Calendar format: "2026-12-25_wednesday" with date, day, and entries
    - Weekly format: standard day-of-week scheduling
    
    For 24/7 linear channels, this ensures:
    - At 14:10, plays the movie scheduled for 13:52 (if it's still running)
    - At 15:30, seamlessly switches to next scheduled movie
    - Handles overnight wrap (Sunday 23:59 → Monday 00:00)
    """
    current_dt = datetime.now()
    today_date = current_dt.strftime("%Y-%m-%d")
    today_dow = current_dt.strftime("%A").lower()

    try:
        schedule_file = SCHEDULE_DIR / "schedule.json"
        if not schedule_file.exists():
            schedule_file = Path("schedule.json")  # fallback

        with open(schedule_file, "r", encoding="utf-8") as f:
            full_schedule = json.load(f)
    except FileNotFoundError:
        logger.error("schedule.json not found!")
        raise FileNotFoundError("schedule.json is missing. Please create one.")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in schedule.json: {e}")
        raise ValueError(f"schedule.json is invalid: {e}")

    # Load all entries for today (calendar takes priority over weekly)
    entries = []
    calendar_found = False

    # 1. Check for enhanced calendar entries (new format)
    calendar_section = full_schedule.get("calendar", {})
    if calendar_section:
        # Look for calendar entry matching today's date
        for calendar_key, calendar_data in calendar_section.items():
            if isinstance(calendar_data, dict) and calendar_data.get("date") == today_date:
                calendar_entries = calendar_data.get("entries", [])
                logger.info(f"📅 Found enhanced calendar entry for {today_date} ({calendar_data.get('day', 'Unknown')}) - {calendar_data.get('description', 'No description')}")
                logger.info(f"📅 Loaded {len(calendar_entries)} calendar entry(ies), overriding weekly schedule")
                entries.extend(_validate_entries(calendar_entries, source=f"calendar:{calendar_key}"))
                calendar_found = True
                break

    # 2. Check for legacy calendar entries (old format: direct date keys)
    if not calendar_found and today_date in full_schedule:
        date_entries = full_schedule[today_date]
        logger.info(f"📅 Found legacy calendar entry for {today_date}")
        logger.info(f"📅 Loaded {len(date_entries)} legacy calendar entry(ies)")
        entries.extend(_validate_entries(date_entries, source=f"legacy_date:{today_date}"))
        calendar_found = True

    # 3. Weekly recurring entries (only if no calendar entry found)
    if not calendar_found:
        weekly = full_schedule.get("weekly", {})
        if today_dow in weekly:
            weekly_entries = weekly[today_dow]
            logger.info(f"📆 Using weekly schedule for {today_dow}")
            logger.info(f"📆 Loaded {len(weekly_entries)} weekly entry(ies) for {today_dow}")
            entries.extend(_validate_entries(weekly_entries, source=f"weekly:{today_dow}"))
        else:
            logger.warning(f"📆 No weekly schedule found for {today_dow}")

    if not entries:
        logger.warning(f"[ERROR] No schedule entries found for {today_date} ({today_dow})")
        return []

    # Sort all entries by time
    entries.sort(key=lambda x: x["time"])

    # Find the current entry (the last entry that started before now)
    current_entry_index = -1
    for i, entry in enumerate(entries):
        entry_time = datetime.strptime(entry["time"], "%H:%M:%S").time()
        entry_dt = datetime.combine(current_dt.date(), entry_time)
        
        # Entry already started earlier today
        if entry_time < current_dt.time():
            # Entry is for tomorrow (overnight)
            entry_dt = datetime.combine(current_dt.date(), entry_time)
        else:
            # Entry is for today
            entry_dt = datetime.combine(current_dt.date(), entry_time)
        
        if entry_dt <= current_dt:
            current_entry_index = i
        else:
            break

    # Return from current entry to end
    if current_entry_index >= 0:
        result = entries[current_entry_index:]
        logger.info(f"[OK] Found current entry at index {current_entry_index}, returning {len(result)} entries")
    else:
        # No entries started yet - return all (start from first)
        result = entries
        logger.info(f"[OK] No current entry found, returning all {len(result)} entries")

    return result

def get_current_fast_schedule_entry(channel: str) -> Dict[str, Any]:
    """
    Get the current entry that should be playing for a Fast Scheduler channel.
    Returns entry with resume position for crash recovery.
    """
    try:
        from .fast_scheduler import FastScheduler
        
        fast_scheduler = FastScheduler(channel)
        checkpoint_result = fast_scheduler.load_checkpoint()
        
        if checkpoint_result["success"] and fast_scheduler.state.schedule_entries:
            current_entry = fast_scheduler.get_current_entry()
            if current_entry:
                resume_position = fast_scheduler.get_resume_position(current_entry)
                
                return {
                    "success": True,
                    "entry": {
                        "time": current_entry.time,
                        "video": current_entry.video_path,
                        "display_name": current_entry.video_name,
                        "duration": current_entry.duration,
                        "type": current_entry.entry_type,
                        "metadata": current_entry.metadata or {}
                    },
                    "resume_position": resume_position,
                    "message": f"Fast Scheduler entry for {channel}"
                }
        
        return {"success": False, "error": "No current Fast Scheduler entry"}
        
    except Exception as e:
        return {"success": False, "error": f"Fast Scheduler error: {str(e)}"}

def get_current_schedule_for_channel(channel: str) -> List[Dict[str, Any]]:
    """
    Load only current + future entries for a specific channel.
    
    Supports both calendar-specific entries and weekly recurring entries:
    - Calendar entries override weekly programming for special dates
    - Calendar format: "2026-12-25_wednesday" with date, day, and entries
    - Weekly format: standard day-of-week scheduling
    - Fast Scheduler: Dynamic in-memory schedules (checked first)
    """
    # First, check if there's a Fast Scheduler for this channel
    try:
        from .fast_scheduler import FastScheduler
        
        # Check if there's a fast schedule checkpoint for this channel
        fast_scheduler = FastScheduler(channel)
        checkpoint_result = fast_scheduler.load_checkpoint()
        
        if checkpoint_result["success"] and fast_scheduler.state.schedule_entries:
            current_entry = fast_scheduler.get_current_entry()
            logger.info(f"Using Fast Scheduler for channel '{channel}' with {len(fast_scheduler.state.schedule_entries)} entries")
            if current_entry:
                resume_position = fast_scheduler.get_resume_position(current_entry)
                logger.info(f"Current Fast Scheduler entry: {current_entry.video_name} (scheduled: {current_entry.time}, resume: {resume_position:.1f}s)")
            else:
                logger.info(f"No current Fast Scheduler entry found for channel '{channel}'")
            
            # Convert Fast Scheduler entries to the format expected by the worker
            current_time = datetime.now().strftime("%H:%M")
            fast_entries = []
            
            # Find the current entry (the one that should be playing now)
            current_entry = fast_scheduler.get_current_entry()
            if current_entry:
                # Include the current entry first with resume position
                resume_position = fast_scheduler.get_resume_position(current_entry)
                fast_entry = {
                    "time": current_entry.time,
                    "file": current_entry.video_path,  # Use "file" for compatibility with linear worker
                    "video": current_entry.video_path,
                    "display_name": current_entry.video_name,
                    "duration": current_entry.duration,
                    "type": current_entry.entry_type,
                    "metadata": current_entry.metadata or {},
                    "resume_position": resume_position  # Add resume position for crash recovery
                }
                fast_entries.append(fast_entry)
                
                # Then add future entries
                for entry in fast_scheduler.state.schedule_entries:
                    # Only include future entries (after current)
                    if entry.time > current_entry.time:
                        fast_entry = {
                            "time": entry.time,
                            "file": entry.video_path,  # Use "file" for compatibility with linear worker
                            "video": entry.video_path,
                            "display_name": entry.video_name,
                            "duration": entry.duration,
                            "type": entry.entry_type,
                            "metadata": entry.metadata or {}
                        }
                        fast_entries.append(fast_entry)
            else:
                # No current entry, just include future entries
                for entry in fast_scheduler.state.schedule_entries:
                    if entry.time >= current_time:
                        fast_entry = {
                            "time": entry.time,
                            "file": entry.video_path,  # Use "file" for compatibility with linear worker
                            "video": entry.video_path,
                            "display_name": entry.video_name,
                            "duration": entry.duration,
                            "type": entry.entry_type,
                            "metadata": entry.metadata or {}
                        }
                        fast_entries.append(fast_entry)
            
            if fast_entries:
                logger.info(f"Fast Scheduler provided {len(fast_entries)} entries for channel '{channel}'")
                return fast_entries
            else:
                logger.info(f"Fast Scheduler has no future entries for channel '{channel}', falling back to JSON")
                
    except Exception as e:
        logger.debug(f"Fast Scheduler not available for channel '{channel}': {e}")
    
    # Fallback to traditional JSON schedule loading
    current_dt = datetime.now()
    today_date = current_dt.strftime("%Y-%m-%d")
    today_dow = current_dt.strftime("%A").lower()
    
    # Load per-channel schedule
    schedule_file = SCHEDULE_DIR / f"schedule_{channel}.json"
    if not schedule_file.exists():
        schedule_file = Path(f"schedule_{channel}.json")  # fallback
    if not schedule_file.exists():
        return []
    
    try:
        with open(schedule_file, "r", encoding="utf-8") as f:
            sched = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load {schedule_file}: {e}")
        return []

    entries = []
    calendar_found = False

    # 1. Check for enhanced calendar entries (new format)
    calendar_section = sched.get("calendar", {})
    if calendar_section:
        # Look for calendar entry matching today's date
        for calendar_key, calendar_data in calendar_section.items():
            if isinstance(calendar_data, dict) and calendar_data.get("date") == today_date:
                calendar_entries = calendar_data.get("entries", [])
                logger.info(f"📅 Found calendar entry for {channel} on {today_date} ({calendar_data.get('day', 'Unknown')})")
                # Ensure channel field
                for entry in calendar_entries:
                    entry["channel"] = channel
                entries.extend(calendar_entries)
                calendar_found = True
                break

    # 2. Check for legacy calendar entries (old format: direct date keys)
    if not calendar_found and today_date in sched:
        date_entries = sched[today_date]
        logger.info(f"📅 Found legacy calendar entry for {channel} on {today_date}")
        # Ensure channel field
        for entry in date_entries:
            entry["channel"] = channel
        entries.extend(date_entries)
        calendar_found = True

    # 3. Weekly recurring entries (only if no calendar entry found)
    if not calendar_found:
        weekly = sched.get("weekly", {})
        weekly_entries = weekly.get(today_dow, [])
        if weekly_entries:
            logger.info(f"📆 Using weekly schedule for {channel} on {today_dow}")
            # Ensure channel field
            for entry in weekly_entries:
                entry["channel"] = channel
            entries.extend(weekly_entries)

    if not entries:
        return []

    # Sort by time
    entries.sort(key=lambda x: x["time"])

    # Find current entry (last one that started before now)
    current_entry_index = -1
    current_dt = datetime.now()
    
    for i, entry in enumerate(entries):
        try:
            entry_time = datetime.strptime(entry["time"], "%H:%M:%S").time()
            current_time = current_dt.time()
            
            # Handle overnight/schedule wrap-around
            # If entry time is more than 2 hours ahead, treat as yesterday
            # This handles cases where schedule spans midnight
            time_diff_seconds = (datetime.combine(datetime.min, entry_time) - datetime.combine(datetime.min, current_time)).total_seconds()
            
            if time_diff_seconds > 7200:
                # Entry time is more than 2 hours ahead - treat as yesterday
                entry_dt = datetime.combine(current_dt.date() - timedelta(days=1), entry_time)
            else:
                # Entry is today (either in past or within 2 hours ahead)
                entry_dt = datetime.combine(current_dt.date(), entry_time)
            
            if entry_dt <= current_dt:
                current_entry_index = i
            else:
                # Stop at first future entry - don't include entries that haven't started yet
                break
        except (ValueError, KeyError) as e:
            logger.warning(f"Error parsing entry time for {entry.get('file', 'unknown')}: {e}")
            continue

    # Return from current entry onward
    if current_entry_index >= 0:
        logger.info(f"Found {current_entry_index + 1} past schedule entry(ies), starting from entry {current_entry_index + 1}")
        return entries[current_entry_index:]
    else:
        # No past entries found - check if there are any future entries for today
        if entries:
            # Return entries but log that we're starting from beginning
            logger.info(f"No past entries found. Starting from beginning (first entry at {entries[0].get('time', 'unknown')})")
        return entries  # Start from beginning if no past entries


def _validate_entries(entries: List[Dict], source: str) -> List[Dict]:
    """Ensure each entry has required fields."""
    valid = []
    for i, entry in enumerate(entries):
        try:
            if not isinstance(entry, dict):
                raise ValueError("not a dictionary")
            if "time" not in entry or "file" not in entry:
                raise ValueError("missing 'time' or 'file'")
            if "channel" not in entry:
                entry["channel"] = "default"
            if "tags" not in entry:
                entry["tags"] = []
            valid.append(entry)
        except Exception as e:
            logger.warning(f"Skipping invalid entry in {source}[{i}]: {e}")
    return valid


def create_calendar_entry(date_str: str, description: str, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a properly formatted calendar entry.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        description: Human-readable description of the event
        entries: List of schedule entries with time, file, channel
    
    Returns:
        Dictionary with calendar entry format
    
    Example:
        create_calendar_entry(
            "2026-12-25", 
            "Christmas Day Marathon",
            [{"time": "08:00:00", "file": "Christmas_Movie.mp4", "channel": "akiratv"}]
        )
    """
    try:
        # Parse date and get day name
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        day_name = date_obj.strftime("%A").lower()
        
        # Create calendar key with date and day
        calendar_key = f"{date_str}_{day_name}"
        
        # Validate entries
        validated_entries = _validate_entries(entries, source=f"calendar:{calendar_key}")
        
        return {
            calendar_key: {
                "date": date_str,
                "day": date_obj.strftime("%A"),
                "description": description,
                "entries": validated_entries
            }
        }
    except ValueError as e:
        logger.error(f"Invalid date format '{date_str}': {e}")
        raise ValueError(f"Date must be in YYYY-MM-DD format: {e}")


def get_calendar_entries_for_date_range(start_date: str, end_date: str, schedule_file: str = None) -> Dict[str, Any]:
    """
    Get all calendar entries within a date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format  
        schedule_file: Optional specific schedule file path
    
    Returns:
        Dictionary of calendar entries within the date range
    """
    if schedule_file is None:
        schedule_file = SCHEDULE_DIR / "schedule.json"
        if not schedule_file.exists():
            schedule_file = Path("schedule.json")
    
    try:
        with open(schedule_file, "r", encoding="utf-8") as f:
            full_schedule = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load schedule file: {e}")
        return {}
    
    calendar_section = full_schedule.get("calendar", {})
    if not calendar_section:
        return {}
    
    # Parse date range
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    # Filter calendar entries within date range
    filtered_entries = {}
    for calendar_key, calendar_data in calendar_section.items():
        if isinstance(calendar_data, dict) and "date" in calendar_data:
            entry_date = datetime.strptime(calendar_data["date"], "%Y-%m-%d")
            if start_dt <= entry_date <= end_dt:
                filtered_entries[calendar_key] = calendar_data
    
    return filtered_entries