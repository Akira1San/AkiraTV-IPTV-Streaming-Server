# Simple Scheduler Calendar Fix Plan

## Problem
Calendar mode generates incorrect timing. Videos show times like `00:00:00`, `00:29:26` instead of cumulative times like `00:00:00`, `01:39:16`.

## Root Cause
The `_generate_calendar_schedule` method:
1. Generates a weekly schedule with correct cumulative times from reference date
2. Flattens entries preserving day names (monday, tuesday, etc.)
3. Redistributes to calendar dates using flawed day-matching logic
4. Times get reset because the redistribution doesn't preserve cumulative timing

## Solution

### Current Code (Broken)
```python
def _generate_calendar_schedule(self, mode, start_date, end_date, target_channel):
    # ... generates temp_schedule with cumulative times
    # Then tries to redistribute with flawed logic:
    while entry_idx < len(all_entries):
        day_diff = (current_dt.date() - ref_date.date()).days
        entry_day = all_entries[entry_idx][0]  # Just day name!
        # ...
```

### Fixed Code
```python
def _generate_calendar_schedule(self, mode, start_date, end_date, target_channel):
    """Generate calendar schedule for a date range"""
    calendar = {}
    weekly = {day: [] for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}

    total_days = (end_date - start_date).days + 1
    total_duration_needed = total_days * 24 * 3600

    # Generate schedule entries - track absolute time
    all_entries = []
    start_datetime = datetime(start_date.year, start_date.month, start_date.day, 0, 0)

    if mode == "random":
        temp_schedule = {day: [] for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}
        self._generate_random_schedule(self.added_videos, temp_schedule, start_datetime, total_duration_needed, target_channel)

        # Flatten with absolute timestamps
        for day, entries in temp_schedule.items():
            for entry in entries:
                all_entries.append((day, entry))
    else:
        temp_schedule = {day: [] for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]}
        self._generate_sequential_schedule(self.added_videos, temp_schedule, start_datetime, total_duration_needed, target_channel)

        for day, entries in temp_schedule.items():
            for entry in entries:
                all_entries.append((day, entry))

    # Distribute entries to calendar dates - preserve timing
    entry_idx = 0
    days_order = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    current_dt = start_date
    while current_dt <= end_date:
        day_name = current_dt.strftime("%A").lower()
        date_str = current_dt.strftime("%Y-%m-%d")
        calendar_key = f"{date_str}_{day_name}"

        day_entries = []
        # Process all entries that belong to this day
        while entry_idx < len(all_entries):
            entry = all_entries[entry_idx][1]
            entry_time_str = entry["time"]
            entry_time = datetime.strptime(entry_time_str, "%H:%M:%S")

            # Calculate what date this entry falls on based on its absolute time
            entry_total_seconds = entry_time.hour * 3600 + entry_time.minute * 60 + entry_time.second
            entry_start_dt = start_datetime + timedelta(seconds=entry_total_seconds)
            entry_date = entry_start_dt.date()

            if entry_date != current_dt.date():
                break  # Entry is for a different date

            # This entry belongs to this day - use it
            day_entries.append(entry)
            entry_idx += 1

        # Sort by time within the day
        day_entries.sort(key=lambda x: x["time"])

        calendar[calendar_key] = {
            "date": date_str,
            "day": day_name.title(),
            "description": f"Auto-generated calendar schedule",
            "entries": day_entries
        }

        # Also add to weekly schedule (for fallback)
        weekly[day_name].extend(day_entries)

        current_dt += timedelta(days=1)

    return {
        "calendar": calendar,
        "weekly": weekly
    }
```

## Key Changes
1. Pass `start_datetime` instead of reference date to generation methods
2. Calculate entry's actual date based on its absolute timestamp
3. Distribute entries to correct calendar dates based on absolute time
4. Sort entries by time within each day

## Testing
1. Generate a weekly schedule - verify times are cumulative
2. Generate a calendar schedule - verify times are cumulative across all dates
3. Check saved JSON file structure has both "calendar" and "weekly" sections
4. Verify calendar entries have correct date-based keys like "2024-01-15_monday"
