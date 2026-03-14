"""
TV Guide Routes
Provides endpoints for TV guide data (current, weekly, date-specific)
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
from pathlib import Path
import json

from ..core_api import get_api
from ..scheduler import resolve_collection_to_path

router = APIRouter(prefix="/api/guide", tags=["TV Guide"])

def get_core_api():
    """Get CoreAPI instance"""
    return get_api()

# ========================================
# HELPER FUNCTIONS
# ========================================

def time_to_minutes(time_str):
    """Convert HH:MM:SS to minutes since midnight"""
    try:
        parts = time_str.split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        return hours * 60 + minutes
    except:
        return 0

def get_schedule_for_date(schedule_data: dict, date_str: str, day_name: str) -> list:
    """
    Get schedule entries for a specific date.
    First checks calendar section (e.g., "2026-02-21_saturday"), then falls back to weekly.
    
    Args:
        schedule_data: The loaded schedule JSON (has 'weekly' and 'calendar' keys)
        date_str: Date string in YYYY-MM-DD format
        day_name: Day name in lowercase (e.g., "saturday")
    
    Returns:
        List of schedule entries for the date
    """
    # First, try calendar section (for calendar-based schedules)
    calendar_key = f"{date_str}_{day_name}"
    calendar_entry = schedule_data.get("calendar", {}).get(calendar_key)
    if calendar_entry and calendar_entry.get("entries"):
        return calendar_entry["entries"]
    
    # Fall back to weekly section (for weekly-based schedules)
    weekly_entries = schedule_data.get("weekly", {}).get(day_name, [])
    if weekly_entries:
        return weekly_entries
    
    return []


def get_program_file_path(program: dict, channel_name: str = None) -> str:
    """
    Get the full file path from a program entry.
    
    Supports both old format (file field) and new format (collection_id field).
    
    Args:
        program: Schedule entry dict with either 'file' or 'collection_id'
        channel_name: Optional channel name to help resolve collection
    
    Returns:
        Full path to video file, or empty string if not found
    """
    # Check for new collection_id format first
    collection_id = program.get("collection_id")
    if collection_id:
        file_path = resolve_collection_to_path(collection_id, channel_name)
        if file_path:
            return file_path
        # If collection not found, log and return empty
        print(f"Warning: Collection not found: {collection_id}")
        return ""
    
    # Fall back to old file format (for backward compatibility)
    return program.get("file", "")


def get_program_display_name(program: dict, channel_name: str = None) -> str:
    """
    Get the display name from a program entry.
    
    Uses collection name if available, otherwise falls back to file stem.
    
    Args:
        program: Schedule entry dict
        channel_name: Optional channel name
    
    Returns:
        Display name for the program
    """
    # Check for collection_id to get collection name
    collection_id = program.get("collection_id")
    if collection_id:
        # Try to get collection name from collections
        from pathlib import Path
        collections_dir = Path("user/collections")
        if collections_dir.exists():
            for collection_file in collections_dir.glob("collections_*.json"):
                try:
                    with open(collection_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for collection in data.get("collections", []):
                            if collection.get("id") == collection_id:
                                return collection.get("name", collection_id)
                except Exception:
                    pass
        # If collection not found, use collection_id as display name
        return collection_id.replace("_", " ").title()
    
    # Fall back to file name stem
    file_path = program.get("file", "")
    if file_path:
        return Path(file_path).stem
    
    return "Unknown"

# ========================================
# GUIDE ENDPOINTS
# ========================================

@router.get("")
def get_tv_guide(api = Depends(get_core_api)):
    """Get TV guide data for all channels"""
    try:
        # Get current time
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        current_day = now.strftime("%A").lower()
        
        # Get all channels
        channels = api.get_channels()
        
        guide_data = {}
        
        for channel in channels:
            if not channel.enabled:
                continue
                
            channel_name = channel.name
            schedule_file = Path(f"user/schedules/schedule_{channel_name}.json")
            
            if not schedule_file.exists():
                # No schedule file, show as "No schedule"
                guide_data[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "current_program": None,
                    "next_program": None,
                    "schedule": []
                }
                continue
            
            try:
                with open(schedule_file, 'r', encoding='utf-8') as f:
                    schedule_data = json.load(f)
                
                # Get today's date string for calendar lookup
                today_date_str = now.strftime("%Y-%m-%d")
                
                # Get today's schedule (check calendar first, then weekly)
                today_schedule = get_schedule_for_date(schedule_data, today_date_str, current_day)
                
                # Find current and next programs
                current_program = None
                next_program = None
                
                # Convert current time to minutes for comparison
                current_minutes = time_to_minutes(current_time)
                
                # Sort schedule by time
                sorted_schedule = sorted(today_schedule, key=lambda x: time_to_minutes(x["time"]))
                
                for i, program in enumerate(sorted_schedule):
                    program_minutes = time_to_minutes(program["time"])
                    
                    # Check if this program is currently playing
                    if i < len(sorted_schedule) - 1:
                        next_program_minutes = time_to_minutes(sorted_schedule[i + 1]["time"])
                        if program_minutes <= current_minutes < next_program_minutes:
                            current_program = program
                            next_program = sorted_schedule[i + 1]
                            break
                    else:
                        # Last program of the day
                        if program_minutes <= current_minutes:
                            current_program = program
                            # Next program would be first program of tomorrow
                            if sorted_schedule:
                                next_program = sorted_schedule[0]
                            break
                
                # If no current program found, use the last program that started
                if not current_program and sorted_schedule:
                    for program in reversed(sorted_schedule):
                        if time_to_minutes(program["time"]) <= current_minutes:
                            current_program = program
                            break
                
                # Format programs for display
                if current_program:
                    current_program["display_name"] = get_program_display_name(current_program, channel_name)
                    current_program["duration_estimate"] = "~90 min"  # Could be calculated from file
                
                if next_program:
                    next_program["display_name"] = get_program_display_name(next_program, channel_name)
                    next_program["duration_estimate"] = "~90 min"
                
                # Get next few programs for the guide
                upcoming_programs = []
                current_index = -1
                
                # Find current program index
                for i, program in enumerate(sorted_schedule):
                    if current_program and program["time"] == current_program["time"]:
                        current_index = i
                        break
                
                # Get next 5 programs
                for i in range(max(0, current_index), min(len(sorted_schedule), current_index + 6)):
                    program = sorted_schedule[i].copy()
                    program["display_name"] = get_program_display_name(program, channel_name)
                    program["is_current"] = (i == current_index)
                    upcoming_programs.append(program)
                
                guide_data[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "current_program": current_program,
                    "next_program": next_program,
                    "schedule": upcoming_programs
                }
                
            except Exception as e:
                # Error reading schedule file
                guide_data[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "current_program": None,
                    "next_program": None,
                    "schedule": [],
                    "error": f"Error reading schedule: {str(e)}"
                }
        
        return {
            "guide": guide_data,
            "current_time": current_time,
            "current_day": current_day,
            "timestamp": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get TV guide: {str(e)}")

@router.get("/weekly")
def get_weekly_tv_guide(api = Depends(get_core_api)):
    """Get full weekly TV guide for all channels"""
    try:
        # Get current time for highlighting current program
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        current_day = now.strftime("%A").lower()
        current_minutes = time_to_minutes(current_time)
        
        # Get all channels
        channels = api.get_channels()
        
        weekly_guide = {}
        days_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        
        for channel in channels:
            if not channel.enabled:
                continue
                
            channel_name = channel.name
            schedule_file = Path(f"user/schedules/schedule_{channel_name}.json")
            
            if not schedule_file.exists():
                # No schedule file
                weekly_guide[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "weekly_schedule": {},
                    "error": "No schedule file found"
                }
                continue
            
            try:
                with open(schedule_file, 'r', encoding='utf-8') as f:
                    schedule_data = json.load(f)
                
                weekly_schedule = {}
                
                # Calculate dates for each day of the current week
                # Find the date for Monday of this week
                today = now.date()
                days_since_monday = today.weekday()  # Monday = 0, Sunday = 6
                monday_date = today - timedelta(days=days_since_monday)
                
                # Process each day of the week
                for i, day in enumerate(days_order):
                    # Calculate the date for this day
                    day_date = monday_date + timedelta(days=i)
                    day_date_str = day_date.strftime("%Y-%m-%d")
                    
                    # Get schedule for this date (check calendar first, then weekly)
                    day_schedule = get_schedule_for_date(schedule_data, day_date_str, day)
                    
                    # Sort programs by time
                    sorted_programs = sorted(day_schedule, key=lambda x: time_to_minutes(x["time"]))
                    
                    # Format programs for display
                    formatted_programs = []
                    for i, program in enumerate(sorted_programs):
                        formatted_program = program.copy()
                        formatted_program["display_name"] = get_program_display_name(program, channel_name)
                        formatted_program["duration_estimate"] = "~90 min"
                        
                        # Mark current program if it's today and currently playing
                        if day == current_day:
                            program_minutes = time_to_minutes(program["time"])
                            if i < len(sorted_programs) - 1:
                                next_program_minutes = time_to_minutes(sorted_programs[i + 1]["time"])
                                formatted_program["is_current"] = program_minutes <= current_minutes < next_program_minutes
                            else:
                                # Last program of the day
                                formatted_program["is_current"] = program_minutes <= current_minutes
                        else:
                            formatted_program["is_current"] = False
                        
                        formatted_programs.append(formatted_program)
                    
                    weekly_schedule[day] = {
                        "day_name": day.capitalize(),
                        "programs": formatted_programs,
                        "program_count": len(formatted_programs),
                        "is_today": day == current_day
                    }
                
                weekly_guide[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "weekly_schedule": weekly_schedule
                }
                
            except Exception as e:
                weekly_guide[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "weekly_schedule": {},
                    "error": f"Error reading schedule: {str(e)}"
                }
        
        return {
            "weekly_guide": weekly_guide,
            "current_time": current_time,
            "current_day": current_day,
            "days_order": days_order,
            "timestamp": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get weekly TV guide: {str(e)}")

@router.get("/date/{date_str}")
def get_guide_for_date(date_str: str, api = Depends(get_core_api)):
    """Get TV guide data for a specific date (YYYY-MM-DD format)"""
    try:
        # Parse the date string
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Get the day name for the selected date
        day_name = selected_date.strftime("%A").lower()
        
        # Get all channels
        channels = api.get_channels()
        
        guide_data = {}
        
        for channel in channels:
            if not channel.enabled:
                continue
                
            channel_name = channel.name
            schedule_file = Path(f"user/schedules/schedule_{channel_name}.json")
            
            if not schedule_file.exists():
                # No schedule file, show as "No schedule"
                guide_data[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "schedule": [],
                    "error": "No schedule file found"
                }
                continue
            
            try:
                with open(schedule_file, 'r', encoding='utf-8') as f:
                    schedule_data = json.load(f)
                
                # Get the schedule for the selected date (check calendar first, then weekly)
                day_schedule = get_schedule_for_date(schedule_data, date_str, day_name)
                
                # Sort schedule by time
                sorted_schedule = sorted(day_schedule, key=lambda x: time_to_minutes(x["time"]))
                
                # Format programs for display
                formatted_schedule = []
                for program in sorted_schedule:
                    formatted_program = program.copy()
                    formatted_program["display_name"] = get_program_display_name(program, channel_name)
                    formatted_program["duration_estimate"] = "~90 min"
                    formatted_schedule.append(formatted_program)
                
                guide_data[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "schedule": formatted_schedule,
                    "program_count": len(formatted_schedule)
                }
                
            except Exception as e:
                # Error reading schedule file
                guide_data[channel_name] = {
                    "channel": channel_name,
                    "type": channel.type,
                    "status": channel.status,
                    "schedule": [],
                    "error": f"Error reading schedule: {str(e)}"
                }
        
        return {
            "guide": guide_data,
            "selected_date": date_str,
            "day_name": day_name.capitalize(),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get TV guide for date: {str(e)}")
