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

    # Load all entries for today (both calendar and weekly)
    entries = []

    # 1. Calendar-specific entries
    if today_date in full_schedule:
        date_entries = full_schedule[today_date]
        logger.info(f"Loaded {len(date_entries)} calendar entry(ies) for {today_date}")
        entries.extend(_validate_entries(date_entries, source=f"date:{today_date}"))

    # 2. Weekly recurring entries
    weekly = full_schedule.get("weekly", {})
    if today_dow in weekly:
        weekly_entries = weekly[today_dow]
        logger.info(f"Loaded {len(weekly_entries)} weekly entry(ies) for {today_dow}")
        entries.extend(_validate_entries(weekly_entries, source=f"weekly:{today_dow}"))

    if not entries:
        logger.warning(f"No schedule entries found for {today_date} ({today_dow})")
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
        logger.info(f"Found current entry at index {current_entry_index}, returning {len(result)} entries")
    else:
        # No entries started yet - return all (start from first)
        result = entries
        logger.info(f"No current entry found, returning all {len(result)} entries")

    return result

def get_current_schedule_for_channel(channel: str) -> List[Dict[str, Any]]:
    """Load only current + future entries for a specific channel."""
    current_dt = datetime.now()
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
        weekly = sched.get("weekly", {})
        entries = weekly.get(today_dow, [])
        # Ensure channel field
        for entry in entries:
            entry["channel"] = channel
    except Exception as e:
        logger.warning(f"Failed to load {schedule_file}: {e}")
        return []

    if not entries:
        return []

    # Sort by time
    entries.sort(key=lambda x: x["time"])

    # Find current entry (last one that started before now)
    current_entry_index = -1
    for i, entry in enumerate(entries):
        entry_time = datetime.strptime(entry["time"], "%H:%M:%S").time()
        entry_dt = datetime.combine(current_dt.date(), entry_time)
        
        # Handle overnight
        # if entry_time > current_dt.time():
        #     entry_dt = datetime.combine(current_dt.date() - timedelta(days=1), entry_time)
        # Handle overnight: if entry time is > 2 hours ahead, it's yesterday
        if (datetime.combine(datetime.min, entry_time) - datetime.combine(datetime.min, current_dt.time())).total_seconds() > 7200:
            # Entry time is more than 2 hours ahead → treat as yesterday
            entry_dt = datetime.combine(current_dt.date() - timedelta(days=1), entry_time)
        else:
            entry_dt = datetime.combine(current_dt.date(), entry_time)
        
        if entry_dt <= current_dt:
            current_entry_index = i
        else:
            break

    # Return from current entry onward
    if current_entry_index >= 0:
        return entries[current_entry_index:]
    else:
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