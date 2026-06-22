# akiratv/xmltv.py
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import time
import socket

def generate_xmltv(schedules_dir, collections_dir, output_path="xmltv.xml"):
    """
    Generate XMLTV file from schedule and collections data.
    Supports multiple channels, real dates, custom directories.
    Supports both weekly recurring schedules and calendar-specific entries.
    
    Calendar entries take priority over weekly entries for specific dates.
    Calendar format: "2026-12-25_wednesday" with date, day, and entries
    """
    # --- 1. Load all schedule data from the specified directory ---
    schedule_data = {"weekly": {}, "calendar": {}}
    schedules_path = Path(schedules_dir)
    if not schedules_path.is_dir():
        print(f"[ERROR] Error: Schedules directory not found at '{schedules_dir}'")
        return

    for schedule_file in schedules_path.glob("*.json"):
        try:
            with open(schedule_file, "r", encoding="utf-8") as f:
                sched = json.load(f)
            
            # Merge weekly entries
            weekly = sched.get("weekly", {})
            for day, entries in weekly.items():
                if day not in schedule_data["weekly"]:
                    schedule_data["weekly"][day] = []
                for entry in entries:
                    # Ensure channel field exists
                    if "channel" not in entry:
                        # Default channel if not specified in the entry
                        entry["channel"] = "default" 
                    schedule_data["weekly"][day].append(entry)
            
            # Merge calendar entries (new format)
            calendar = sched.get("calendar", {})
            for calendar_key, calendar_data in calendar.items():
                if isinstance(calendar_data, dict) and "entries" in calendar_data:
                    if calendar_key not in schedule_data["calendar"]:
                        schedule_data["calendar"][calendar_key] = calendar_data
                    else:
                        # Merge entries for same calendar key
                        schedule_data["calendar"][calendar_key]["entries"].extend(calendar_data["entries"])
            
            # Also check for legacy date-keyed entries (direct date keys like "2026-12-25")
            for key, entries in sched.items():
                if key not in ["weekly", "calendar"] and isinstance(entries, list):
                    # This might be a legacy date entry
                    try:
                        # Check if key looks like a date
                        datetime.strptime(key, "%Y-%m-%d")
                        if key not in schedule_data["calendar"]:
                            schedule_data["calendar"][key] = {
                                "date": key,
                                "day": datetime.strptime(key, "%Y-%m-%d").strftime("%A").lower(),
                                "entries": entries
                            }
                    except ValueError:
                        pass  # Not a date key, skip
            
            # print(f"[OK] Loaded schedule from {schedule_file.name}")  # DEBUG: Enable for schedule loading
        except Exception as e:
            # print(f"⚠️ Failed to load {schedule_file}: {e}")  # DEBUG: Enable for error tracking
            pass

    if not schedule_data["weekly"] and not schedule_data["calendar"]:
        print("[ERROR] Error: No schedule data was loaded. Please check your schedule files.")
        return

    # --- 2. Load all collections data from the specified directory ---
    collections_data = {"collections": []}
    collections_path = Path(collections_dir)
    if not collections_path.is_dir():
        # print(f"[ERROR] Error: Collections directory not found at '{collections_dir}'")  # DEBUG: Enable for error tracking
        return

    for collections_file in collections_path.glob("*.json"):
        try:
            with open(collections_file, "r", encoding="utf-8") as f:
                col_data = json.load(f)
            # Merge collections
            collections_data["collections"].extend(col_data.get("collections", []))
            # print(f"[OK] Loaded collection from {collections_file.name}")  # DEBUG: Enable for collection loading
        except Exception as e:
            # print(f"⚠️ Failed to load {collections_file}: {e}")  # DEBUG: Enable for error tracking
            pass

    if not collections_data["collections"]:
        # print("[ERROR] Error: No collection data was loaded. Please check your collection files.")  # DEBUG: Enable for error tracking
        pass

    # --- 3. Build a lookup table: video_path -> collection metadata ---
    video_lookup = {}
    for col in collections_data.get("collections", []):
        for video in col.get("videos", []):
            path = video["path"]
            # Use normalized paths for reliable matching (e.g., forward slashes)
            normalized_path = Path(path).as_posix() 
            video_lookup[normalized_path] = {
                "name": col.get("name", Path(path).stem),
                "name_bg": col.get("name_bg", None),
                "description": col.get("description", "No description."),
                "genre": col.get("genre", ["Movie"]),
                "year": col.get("year", None),
                "rating": col.get("rating", "NR"),
                "cover": col.get("cover", None),  # Use "cover" instead of "poster"
                "videos": [video]  # Keep the video object to access duration
            }
    
    # [SEARCH] Debug: Print the video lookup to see if paths are matching
    # print(f"[SEARCH] Debug: Video lookup contains {len(video_lookup)} entries")
    # for path, meta in video_lookup.items():
    #     print(f"[SEARCH] Debug: Path: {path}, Name: {meta.get('name')}, Channel: {path.split('/')[2] if len(path.split('/')) > 2 else 'unknown'}")

    # --- 4. Create the XMLTV structure ---
    root = ET.Element("tv")
    root.set("generator-info-name", "AkiraTV")
    root.set("generator-info-url", "https://github.com/yourname/akiratv")

    # Discover all channels from the loaded schedule (both weekly and calendar)
    all_channels = set()
    weekly = schedule_data.get("weekly", {})
    calendar = schedule_data.get("calendar", {})
    
    # Channels from weekly entries
    for day_entries in weekly.values():
        for entry in day_entries:
            all_channels.add(entry.get("channel", "default"))
    
    # Channels from calendar entries
    for calendar_key, calendar_data in calendar.items():
        if isinstance(calendar_data, dict):
            for entry in calendar_data.get("entries", []):
                all_channels.add(entry.get("channel", "default"))

    # Add channel definitions
    for channel_id in sorted(all_channels):
        channel_el = ET.SubElement(root, "channel")
        channel_el.set("id", channel_id)
        display_name = ET.SubElement(channel_el, "display-name")
        display_name.text = channel_id.replace("_", " ").title()
        
        # Auto-detect local IP for logo URL
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = "127.0.0.1"

        logo_url = f"http://{local_ip}:8081/channels/{channel_id}/logo.png"
        icon = ET.SubElement(channel_el, "icon")
        icon.set("src", logo_url)

    # --- 5. Generate programme entries ---
    # Track statistics
    weekly_count = 0
    calendar_count = 0
    
    # Process calendar entries first (they take priority for specific dates)
    for calendar_key, calendar_data in calendar.items():
        if isinstance(calendar_data, dict):
            date_str = calendar_data.get("date", "")
            entries = calendar_data.get("entries", [])
            for entry in entries:
                prog = create_programme_from_calendar(entry, video_lookup, date_str)
                if prog is not None:
                    root.append(prog)
                    calendar_count += 1
    
    # Process weekly entries (recurring schedule)
    for day_name, entries in weekly.items():
        for entry in entries:
            # Check if this entry is already covered by a calendar entry
            # Skip weekly entries for dates that have calendar overrides
            prog = create_programme(entry, video_lookup, day_name, calendar)
            if prog is not None:
                root.append(prog)
                weekly_count += 1
    
    # Log statistics
    print(f"[OK] Generated XMLTV with {calendar_count} calendar entries and {weekly_count} weekly entries")

    # --- 6. Write the final XMLTV file ---
    try:
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        print(f"[OK] XMLTV EPG saved to: {output_path}")
    except Exception as e:
        # print(f"[ERROR] Error writing XMLTV file: {e}")  # DEBUG: Enable for error tracking
        pass

def create_programme(entry, video_lookup, day_name, calendar=None):
    """Create a single <programme> element with real timestamps for Bulgarian time.
    
    Args:
        entry: Schedule entry dict with time, file, channel
        video_lookup: Dict mapping video paths to metadata
        day_name: Day name (monday, tuesday, etc.)
        calendar: Optional calendar dict to check for date overrides
    """
    try:
        # Normalize the file path from the schedule for reliable lookup
        file_path = Path(entry["file"]).as_posix()
        
        # Parse scheduled start time
        start_time = datetime.strptime(entry["time"], "%H:%M:%S")
        
        # Map day name to date (use upcoming week)
        today = datetime.now().date()
        day_offset = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }.get(day_name.lower(), 0)
        
        # Find next occurrence of this day
        days_ahead = (day_offset - today.weekday()) % 7
        if days_ahead == 0 and start_time.time() < datetime.now().time():
            days_ahead = 7  # Use next week if time already passed today
        program_date = today + timedelta(days=days_ahead)
        
        # Check if this date has a calendar override FOR THE SAME CHANNEL
        if calendar:
            date_str = program_date.strftime("%Y-%m-%d")
            entry_channel = entry.get("channel", "default")
            for calendar_key, calendar_data in calendar.items():
                if isinstance(calendar_data, dict) and calendar_data.get("date") == date_str:
                    # Check if any calendar entry is for the same channel
                    for cal_entry in calendar_data.get("entries", []):
                        if cal_entry.get("channel", "default") == entry_channel:
                            # This date has a calendar override for this channel, skip weekly entry
                            return None
        
        # Build start datetime (naive - this is assumed to be BULGARIAN LOCAL TIME)
        start_dt = datetime.combine(program_date, start_time.time())
        
        # Get video metadata
        meta = video_lookup.get(file_path, {})
        
        # Default 90 min duration if not found
        duration_seconds = 5400
        
        # Try to get real duration from lookup
        if "videos" in meta and len(meta["videos"]) > 0 and "duration" in meta["videos"][0]:
            duration_seconds = int(float(meta["videos"][0]["duration"])) # Ensure it's an int
        
        # Calculate stop datetime (naive)
        stop_dt = start_dt + timedelta(seconds=duration_seconds)
        
        # Bulgarian Timezone Handling
        is_dst = time.localtime().tm_isdst > 0
        tz_offset_hours = 3 if is_dst else 2
        
        # To get UTC, we subtract the local timezone offset from the naive local time
        utc_start_dt = start_dt - timedelta(hours=tz_offset_hours)
        utc_stop_dt = stop_dt - timedelta(hours=tz_offset_hours)
        
        # Now, make them timezone-aware UTC objects for proper formatting
        utc_start_dt = utc_start_dt.replace(tzinfo=timezone.utc)
        utc_stop_dt = utc_stop_dt.replace(tzinfo=timezone.utc)
        
        # Format as required by XMLTV (YYYYMMDDHHMMSS +HHMM)
        start_str = utc_start_dt.strftime("%Y%m%d%H%M%S %z")
        stop_str = utc_stop_dt.strftime("%Y%m%d%H%M%S %z")

        # Create programme element
        prog = ET.Element("programme")
        prog.set("start", start_str)
        prog.set("stop", stop_str)
        prog.set("channel", entry["channel"])

        # Title (English)
        title = ET.SubElement(prog, "title")
        title.set("lang", "en")
        title.text = meta.get("name", Path(entry["file"]).stem)

        # Title (Bulgarian) - if available
        if meta.get("name_bg"):
            title_bg = ET.SubElement(prog, "title")
            title_bg.set("lang", "bg")
            title_bg.text = meta["name_bg"]

        # Description
        desc = ET.SubElement(prog, "desc")
        desc.set("lang", "en")
        desc.text = meta.get("description", "AkiraTV Stream")

        # Genre
        for genre in meta.get("genre", ["Movie"]):
            cat = ET.SubElement(prog, "category")
            cat.set("lang", "en")
            cat.text = genre

        # Rating
        if meta.get("rating", "NR") != "NR":
            rating = ET.SubElement(prog, "rating")
            rating.set("system", "MPAA")
            val = ET.SubElement(rating, "value")
            val.text = meta["rating"]

        # Year
        if meta.get("year"):
            date_el = ET.SubElement(prog, "date")
            date_el.text = str(meta["year"])

        # NEW: Add cover/icon if available (using "cover" instead of "poster")
        if meta.get("cover"):
            # Get local IP for creating URL
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except:
                local_ip = "127.0.0.1"
            
            # Convert local path to URL
            cover_path = Path(meta["cover"])
            # Create a relative path for the URL
            cover_url = f"http://{local_ip}:8081/{cover_path.as_posix()}"
            
            # Add icon element
            icon = ET.SubElement(prog, "icon")
            icon.set("src", cover_url)

        return prog

    except Exception as e:
        # print(f"⚠️  Error creating programme for {entry.get('file', 'unknown file')}: {e}")  # DEBUG: Enable for error tracking
        return None

def create_programme_from_calendar(entry, video_lookup, date_str):
    """Create a single <programme> element from a calendar entry with a specific date.
    
    Args:
        entry: Schedule entry dict with time, file, channel
        video_lookup: Dict mapping video paths to metadata
        date_str: Date string in YYYY-MM-DD format
    """
    try:
        # Normalize the file path from the schedule for reliable lookup
        file_path = Path(entry["file"]).as_posix()
        
        # Parse the specific date
        program_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Parse scheduled start time
        start_time = datetime.strptime(entry["time"], "%H:%M:%S")
        
        # Build start datetime (naive - this is assumed to be BULGARIAN LOCAL TIME)
        start_dt = datetime.combine(program_date, start_time.time())
        
        # Get video metadata
        meta = video_lookup.get(file_path, {})
        
        # Default 90 min duration if not found
        duration_seconds = 5400
        
        # Try to get real duration from lookup
        if "videos" in meta and len(meta["videos"]) > 0 and "duration" in meta["videos"][0]:
            duration_seconds = int(float(meta["videos"][0]["duration"])) # Ensure it's an int
        
        # Calculate stop datetime (naive)
        stop_dt = start_dt + timedelta(seconds=duration_seconds)
        
        # Bulgarian Timezone Handling
        is_dst = time.localtime().tm_isdst > 0
        tz_offset_hours = 3 if is_dst else 2
        
        # To get UTC, we subtract the local timezone offset from the naive local time
        utc_start_dt = start_dt - timedelta(hours=tz_offset_hours)
        utc_stop_dt = stop_dt - timedelta(hours=tz_offset_hours)
        
        # Now, make them timezone-aware UTC objects for proper formatting
        utc_start_dt = utc_start_dt.replace(tzinfo=timezone.utc)
        utc_stop_dt = utc_stop_dt.replace(tzinfo=timezone.utc)
        
        # Format as required by XMLTV (YYYYMMDDHHMMSS +HHMM)
        start_str = utc_start_dt.strftime("%Y%m%d%H%M%S %z")
        stop_str = utc_stop_dt.strftime("%Y%m%d%H%M%S %z")

        # Create programme element
        prog = ET.Element("programme")
        prog.set("start", start_str)
        prog.set("stop", stop_str)
        prog.set("channel", entry.get("channel", "default"))

        # Title (English)
        title = ET.SubElement(prog, "title")
        title.set("lang", "en")
        title.text = meta.get("name", Path(entry["file"]).stem)

        # Title (Bulgarian) - if available
        if meta.get("name_bg"):
            title_bg = ET.SubElement(prog, "title")
            title_bg.set("lang", "bg")
            title_bg.text = meta["name_bg"]

        # Description
        desc = ET.SubElement(prog, "desc")
        desc.set("lang", "en")
        desc.text = meta.get("description", "AkiraTV Stream")

        # Genre
        for genre in meta.get("genre", ["Movie"]):
            cat = ET.SubElement(prog, "category")
            cat.set("lang", "en")
            cat.text = genre

        # Rating
        if meta.get("rating", "NR") != "NR":
            rating = ET.SubElement(prog, "rating")
            rating.set("system", "MPAA")
            val = ET.SubElement(rating, "value")
            val.text = meta["rating"]

        # Year
        if meta.get("year"):
            date_el = ET.SubElement(prog, "date")
            date_el.text = str(meta["year"])

        # Add cover/icon if available
        if meta.get("cover"):
            # Get local IP for creating URL
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except:
                local_ip = "127.0.0.1"
            
            # Convert local path to URL
            cover_path = Path(meta["cover"])
            # Create a relative path for the URL
            cover_url = f"http://{local_ip}:8081/{cover_path.as_posix()}"
            
            # Add icon element
            icon = ET.SubElement(prog, "icon")
            icon.set("src", cover_url)

        return prog

    except Exception as e:
        # print(f"⚠️  Error creating calendar programme for {entry.get('file', 'unknown file')}: {e}")  # DEBUG: Enable for error tracking
        return None

def generate_m3u_playlist(config, output_path="channels.m3u"):
    """Generate M3U playlist for Kodi with tvg-id and tvg-url linking to XMLTV."""
    # Get local IP for M3U playlist
    import socket
    http_conf = config.get("output", {}).get("http", {})
    port = http_conf.get("port", 8081)
    bind = http_conf.get("bind", "127.0.0.1")

    if bind == "0.0.0.0":
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except:
            ip = "YOUR_LOCAL_IP"
    else:
        ip = bind

    base_url = f"http://{ip}:{port}"

    with open(output_path, "w", encoding="utf-8") as f:
        # --- THIS IS THE NEW, IMPORTANT PART ---
        # We add the tvg-url attribute directly to the #EXTM3U line
        f.write(f'#EXTM3U tvg-url="{base_url}/hls/xmltv.xml"\n')  # <-- MODIFIED LINE
        
        for channel_id in config.get("channels", {}):
            if config["channels"][channel_id].get("enabled", True):
                f.write(
                    f'#EXTINF:-1 tvg-id="{channel_id}" '
                    f'tvg-name="{channel_id.title()}" '
                    f'tvg-logo="{base_url}/channels/{channel_id}/logo.png" '
                    f'group-title="AkiraTV",'
                    f'{channel_id.title()}\n'
                    f'{base_url}/hls/{channel_id}/index.m3u8\n'
                )
    
    # print(f"[OK] M3U playlist saved to: {output_path}")
    # print(f"[WEB] Local M3U URL: http://{ip}:{port}/channels.m3u")