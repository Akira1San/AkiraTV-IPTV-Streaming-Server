# Daypart Scheduler Feature Proposal
## A Comprehensive Upgrade to simple_scheduler.py

---

## 1. Feature Overview and Goals

### 1.1 Executive Summary
This proposal outlines the implementation of a **Daypart Scheduler** - a new scheduling paradigm for AkiraTV that allows users to define specific time blocks throughout the day, each with its own content selection rules. This is an upgrade to the existing `simple_scheduler.py` that currently only supports random/sequential generation for entire days.

### 1.2 Core Objectives
- **Precise Programming**: Schedule specific videos or tag-based content to exact time slots (00:00-24:00)
- **Daypart Structure**: Define multiple time blocks per day (e.g., Morning 06:00-10:00, Prime Time 20:00-23:00)
- **Flexible Content Assignment**: Each block can specify either a specific video or a tag (random selection from that tag)
- **Gap Filling**: Automatically fill unscheduled time gaps with random content from available videos
- **Marathon Mode**: Schedule 24-hour marathons for specific tags on selected days of the week
- **Seamless Integration**: Build upon existing collection/tag system without disrupting current workflows

### 1.3 User Benefits
- **Broadcast-Style Scheduling**: Create realistic TV-like programming schedules
- **Content Strategy**: Align content with audience demographics (kids content in morning, horror at night)
- **Special Events**: Run themed marathons (e.g., "80s Action Every Friday")
- **Backward Compatible**: Existing random/sequential scheduling remains available

---

## 2. UI Design and Layout Specifications

### 2.1 New Tab: "Schedule Programming"

**Location**: Next to "Added Videos" tab in the Added Videos panel (right side of the 4-pane layout)

**Tab Structure**:
```
┌─────────────────────────────────────────────────────────────┐
│ [Collections] [Standby] [Added Videos] [Schedule Programming] ← NEW
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Schedule Programming Tab Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Schedule Programming                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                 │
│  │ Time Blocks     │  │ Marathon        │                 │
│  │ Management      │  │ Scheduling      │                 │
│  │                 │  │                 │                 │
│  │ • Add Block     │  │ • Select Tag    │                 │
│  │ • Edit Block    │  │ • Day of Week   │                 │
│  │ • Delete Block  │  │ • Enable/Disable│                 │
│  │ • Block List    │  │ • Preview       │                 │
│  │   (time, type)  │  │                 │                 │
│  └─────────────────┘  └─────────────────┘                 │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Gap Filler Settings                                 │  │
│  │ □ Enable gap filling with random content           │  │
│  │ Source: [All Videos ▼]                             │  │
│  │ Exclude tags: [Edit...]                            │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Preview Schedule (Read-only)                       │  │
│  │ 00:00 ████████████████████████████████████████    │  │
│  │ 06:00 ████████████████████████████████████████    │  │
│  │ 12:00 ████████████████████████████████████████    │  │
│  │ 18:00 ████████████████████████████████████████    │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  [Generate Preview] [Save Schedule]                       │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Time Block Management Panel

**Components**:
1. **Block List Display** (Listbox)
   - Columns: Start Time | End Time | Content Type | Content (video name or tag)
   - Color coding:
     - Blue: Specific video
     - Green: Tag-based random
     - Red: Marathon block

2. **Block Control Buttons**:
   - `[+] Add Block` - Opens "Edit Block" dialog (create mode)
   - `[✎] Edit Selected` - Opens dialog with selected block data
   - `[-] Delete Selected` - Removes selected block(s)
   - `[↑] Move Up` / `[↓] Move Down` - Reorder blocks

3. **Add/Edit Block Dialog**:
```
┌─────────────────────────────────────────────┐
│ Edit Time Block                             │
├─────────────────────────────────────────────┤
│ Start Time:  [06:00]    End Time: [10:00]  │
│                                             │
│ Content Type: ○ Specific Video  ○ Tag      │
│                                             │
│ If Specific Video:                          │
│   Search: [________________] [Search]       │
│   Results: [Listbox with videos]           │
│   Selected: [Video Name]                   │
│                                             │
│ If Tag:                                    │
│   Tag: [ComboBox with existing tags]       │
│   Or New: [__________]                     │
│                                             │
│ Preview Duration: 4 hours (14400 seconds)  │
│                                             │
│ [Cancel]  [Save]                           │
└─────────────────────────────────────────────┘
```

### 2.4 Marathon Scheduling Panel

**Components**:
1. **Tag Selection**:
   - Dropdown populated with all tags from collections
   - Option to type custom tag

2. **Day Selection**:
   - Checkboxes: Mon Tue Wed Thu Fri Sat Sun
   - Or "Every Day" checkbox

3. **Options**:
   - `[✓] Fill entire 24-hour period`
   - `[✓] Shuffle within marathon`
   - `[✓] Allow repeats within 24h` (default: no)

4. **Marathon Preview**:
   - Shows estimated number of videos needed
   - Total duration confirmation

### 2.5 Gap Filler Settings

**Components**:
1. **Enable Gap Filling** checkbox
2. **Source Selection**:
   - Radio buttons: `All videos` OR `Only from selected collections` OR `Only from specific tags`
3. **Exclusions**:
   - `Exclude tags:` [Edit...] button to select tags to exclude from gap filling
4. **Randomization Options**:
   - `[✓] Respect 24-hour no-repeat rule` (default: yes)
   - `[✓] Shuffle selection` (default: yes)

### 2.6 Preview Panel

**Visual Timeline**:
- Horizontal bar showing 24-hour day (00:00 to 24:00)
- Colored blocks representing scheduled time blocks
- Hover tooltip shows block details
- Legend:
  - Blue: Specific video
  - Green: Tag-based
  - Red: Marathon
  - Gray: Gap filler (random)

**Text Preview**:
```
=== SCHEDULE PREVIEW ===
00:00 - 02:30 [TAG:horror] Random horror video
02:30 - 06:00 [VIDEO] The Matrix (1999).mp4
06:00 - 10:00 [TAG:kids] Random kids content
10:00 - 12:00 [RANDOM] Random from all videos
...
Total blocks: 8 | Gap filler segments: 3
```

---

## 3. Data Structures and Schedule JSON Format

### 3.1 Internal Data Structures

#### TimeBlock Class
```python
class TimeBlock:
    def __init__(self, start_time: str, end_time: str, 
                 content_type: str, content_value: str, 
                 block_id: str = None):
        """
        Args:
            start_time: "HH:MM" format (24-hour)
            end_time: "HH:MM" format (24-hour)
            content_type: "video" or "tag"
            content_value: 
                - If type="video": full video path
                - If type="tag": tag name
            block_id: unique identifier (auto-generated if None)
        """
        self.block_id = block_id or f"block_{uuid.uuid4().hex[:8]}"
        self.start_time = start_time
        self.end_time = end_time
        self.content_type = content_type  # "video" or "tag"
        self.content_value = content_value
        
    @property
    def duration_seconds(self) -> int:
        """Calculate block duration in seconds"""
        start_dt = datetime.strptime(self.start_time, "%H:%M")
        end_dt = datetime.strptime(self.end_time, "%H:%M")
        if end_dt < start_dt:
            # Handle overnight blocks (e.g., 22:00-02:00)
            end_dt += timedelta(days=1)
        return int((end_dt - start_dt).total_seconds())
    
    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "block_id": self.block_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "content_type": self.content_type,
            "content_value": self.content_value,
            "duration_seconds": self.duration_seconds
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TimeBlock':
        """Deserialize from dictionary"""
        return cls(
            start_time=data["start_time"],
            end_time=data["end_time"],
            content_type=data["content_type"],
            content_value=data["content_value"],
            block_id=data.get("block_id")
        )
```

#### MarathonConfig Class
```python
class MarathonConfig:
    def __init__(self, tag: str, days: list, enabled: bool = True,
                 shuffle: bool = True, no_repeat_24h: bool = True):
        """
        Args:
            tag: Tag name to marathon
            days: List of weekday names ["monday", "friday", ...]
            enabled: Whether this marathon is active
            shuffle: Randomize order within the 24h period
            no_repeat_24h: Don't repeat videos within 24 hours
        """
        self.tag = tag
        self.days = days  # List of weekday strings
        self.enabled = enabled
        self.shuffle = shuffle
        self.no_repeat_24h = no_repeat_24h
    
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
```

#### GapFillerConfig Class
```python
class GapFillerConfig:
    def __init__(self, enabled: bool = True, source: str = "all",
                 excluded_tags: list = None, respect_24h_norepeat: bool = True,
                 shuffle: bool = True):
        """
        Args:
            enabled: Enable automatic gap filling
            source: "all", "collections", or "tags"
            excluded_tags: List of tags to exclude from gap filling
            respect_24h_norepeat: Apply 24-hour no-repeat rule
            shuffle: Randomize selection
        """
        self.enabled = enabled
        self.source = source  # "all", "collections", "tags"
        self.collection_ids = []  # If source="collections"
        self.tags = []  # If source="tags"
        self.excluded_tags = excluded_tags or []
        self.respect_24h_norepeat = respect_24h_norepeat
        self.shuffle = shuffle
    
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
```

### 3.2 Daypart Schedule JSON Format

The schedule JSON will be extended to support daypart blocks:

```json
{
  "metadata": {
    "channel": "critters",
    "created": "2025-01-15T10:30:00",
    "version": "2.0",
    "schedule_type": "daypart"
  },
  "daypart_config": {
    "time_blocks": [
      {
        "block_id": "block_abc12345",
        "start_time": "06:00",
        "end_time": "10:00",
        "content_type": "tag",
        "content_value": "kids",
        "duration_seconds": 14400
      },
      {
        "block_id": "block_def67890",
        "start_time": "10:00",
        "end_time": "12:00",
        "content_type": "video",
        "content_value": "C:/Videos/Akiratv/The Matrix (1999).mp4",
        "duration_seconds": 7200
      },
      {
        "block_id": "block_ghi12345",
        "start_time": "12:00",
        "end_time": "14:00",
        "content_type": "tag",
        "content_value": "documentary",
        "duration_seconds": 7200
      },
      {
        "block_id": "block_jkl67890",
        "start_time": "20:00",
        "end_time": "24:00",
        "content_type": "tag",
        "content_value": "horror",
        "duration_seconds": 14400
      }
    ],
    "marathons": [
      {
        "tag": "80s",
        "days": ["friday", "saturday"],
        "enabled": true,
        "shuffle": true,
        "no_repeat_24h": true
      }
    ],
    "gap_filler": {
      "enabled": true,
      "source": "all",
      "collection_ids": [],
      "tags": [],
      "excluded_tags": ["horror", "kids"],
      "respect_24h_norepeat": true,
      "shuffle": true
    }
  },
  "weekly": {
    "monday": [],
    "tuesday": [],
    "wednesday": [],
    "thursday": [],
    "friday": [],
    "saturday": [],
    "sunday": []
  },
  "calendar": {}
}
```

**Key Points**:
- `time_blocks`: Array of scheduled blocks for EVERY day of the week (same blocks apply to all days)
- `marathons`: Tag-based 24-hour marathons on specific days (override time blocks for that day)
- `gap_filler`: Configuration for filling unscheduled time
- `weekly` and `calendar` remain for backward compatibility but will be empty when using daypart mode

### 3.3 Schedule Entry Format (Generated)

When the daypart schedule is processed, it generates actual playout entries:

```json
{
  "time": "06:00:00",
  "file": "C:/Videos/Akiratv/Kids_Show_S01E01.mp4",
  "collection_id": "kids_show",
  "channel": "critters",
  "source": "daypart_tag",
  "daypart_block_id": "block_abc12345",
  "metadata": {
    "scheduled_type": "tag",
    "tag_used": "kids",
    "block_start": "06:00",
    "block_end": "10:00"
  }
}
```

---

## 4. Integration with Existing Collections/Tags System

### 4.1 Tag-Based Content Selection

The system will leverage existing collection tags:

```python
# From collections.py - collections already have tags
collection = {
    "id": "into_the_sun",
    "name": "Into the Sun",
    "tags": ["action", "adventure", "80s"],  # ← Use these
    "videos": [...]
}
```

**Tag Resolution Process**:
1. User selects tag "horror" in a time block
2. Scheduler queries all collections for videos with "horror" tag
3. Builds pool of eligible videos (respecting blacklist, 24h rule, etc.)
4. Randomly selects from pool during schedule generation

### 4.2 Collections as Source

For gap filler "collections" mode:
- User selects specific collections from existing loaded collections
- Only videos from those collections are used
- Respects blacklist and other filters

### 4.3 Blacklist Integration

- Blacklisted videos are excluded from ALL content selection
- Stored in `user/collections/{profile}.ini` as before
- Applied during schedule generation, not at configuration time

### 4.4 Video Duration Awareness

- Each block's duration is calculated from start/end times
- Scheduler fills the block with videos until duration is met
- If a video is longer than remaining time, it still plays (no truncation)
- Next block starts after video completes (may overlap nominal time)

---

## 5. Algorithm for Filling Gaps with Random Content

### 5.1 Gap Detection

```python
def detect_gaps(time_blocks: List[TimeBlock], day_start="00:00", day_end="24:00") -> List[Tuple]:
    """
    Identify unscheduled time periods between blocks.
    Returns list of (start_time, end_time) tuples.
    """
    # Sort blocks by start time
    sorted_blocks = sorted(time_blocks, key=lambda b: b.start_time)
    
    gaps = []
    current_time = datetime.strptime(day_start, "%H:%M")
    
    for block in sorted_blocks:
        block_start = datetime.strptime(block.start_time, "%H:%M")
        
        if current_time < block_start:
            # Gap detected
            gaps.append((current_time.strftime("%H:%M"), 
                        block.start_time))
        
        # Move current time to block end
        current_time = datetime.strptime(block.end_time, "%H:%M")
        if current_time < block_start:
            current_time += timedelta(days=1)  # Handle overnight
    
    # Check for gap at end of day
    day_end_dt = datetime.strptime(day_end, "%H:%M")
    if current_time < day_end_dt:
        gaps.append((current_time.strftime("%H:%M"), day_end))
    
    return gaps
```

### 5.2 Gap Filling Algorithm

```python
def fill_gaps_with_random(gaps: List[Tuple], available_videos: List[dict],
                         gap_filler_config: GapFillerConfig,
                         recent_videos: List[tuple] = None) -> List[dict]:
    """
    Fill detected gaps with random video content.
    
    Args:
        gaps: List of (start_time, end_time) tuples
        available_videos: Pool of eligible videos
        gap_filler_config: Configuration for gap filling behavior
        recent_videos: List of (video_path, last_played_time) tuples
    
    Returns:
        List of schedule entries for gap filler content
    """
    gap_entries = []
    recent_videos = recent_videos or []
    
    for gap_start, gap_end in gaps:
        gap_start_dt = datetime.strptime(gap_start, "%H:%M")
        gap_end_dt = datetime.strptime(gap_end, "%H:%M")
        gap_duration = int((gap_end_dt - gap_start_dt).total_seconds())
        
        remaining_seconds = gap_duration
        current_time = gap_start_dt
        
        while remaining_seconds > 0:
            # Filter available videos based on gap_filler_config
            eligible_videos = filter_videos_for_gap(
                available_videos, 
                gap_filler_config, 
                recent_videos
            )
            
            if not eligible_videos:
                # No videos available, break to avoid infinite loop
                logger.warning(f"No eligible videos for gap {gap_start}-{gap_end}")
                break
            
            # Select random video
            if gap_filler_config.shuffle:
                video = random.choice(eligible_videos)
            else:
                video = eligible_videos[0]
            
            video_duration = video.get("duration", 0)
            
            # Create schedule entry
            entry = {
                "time": current_time.strftime("%H:%M:%S"),
                "file": video["path"],
                "collection_id": video.get("collection_id"),
                "channel": video.get("channel", "default"),
                "source": "gap_filler",
                "metadata": {
                    "scheduled_type": "gap_filler",
                    "gap_start": gap_start,
                    "gap_end": gap_end
                }
            }
            
            gap_entries.append(entry)
            
            # Update tracking
            current_time += timedelta(seconds=video_duration)
            remaining_seconds -= video_duration
            recent_videos.append((video["path"], datetime.now()))
    
    return gap_entries
```

### 5.3 Marathon Scheduling Algorithm

```python
def generate_marathon_schedule(marathon_config: MarathonConfig, 
                               available_videos: List[dict],
                               target_date: datetime) -> List[dict]:
    """
    Generate a 24-hour marathon schedule for a specific day.
    
    Args:
        marathon_config: Configuration for the marathon
        available_videos: Pool of all available videos
        target_date: The date for which to generate the marathon
    
    Returns:
        List of schedule entries for the 24-hour marathon
    """
    # Filter videos by marathon tag
    tagged_videos = [
        v for v in available_videos 
        if marathon_config.tag in v.get("tags", [])
    ]
    
    if not tagged_videos:
        logger.warning(f"No videos found for marathon tag: {marathon_config.tag}")
        return []
    
    # Calculate how many videos needed for 24 hours
    total_duration_needed = 24 * 3600  # 24 hours in seconds
    
    # Get video durations and build playlist
    video_playlist = []
    current_duration = 0
    
    while current_duration < total_duration_needed:
        # Apply shuffling if enabled
        if marathon_config.shuffle:
            random.shuffle(tagged_videos)
        
        for video in tagged_videos:
            if marathon_config.no_repeat_24h:
                # Check if video was played in last 24h
                if was_played_in_last_24h(video["path"]):
                    continue
            
            video_playlist.append(video)
            current_duration += video.get("duration", 0)
            
            if current_duration >= total_duration_needed:
                break
    
    # Generate schedule entries starting at 00:00
    marathon_entries = []
    current_time = datetime.strptime("00:00", "%H:%M")
    
    for video in video_playlist:
        entry = {
            "time": current_time.strftime("%H:%M:%S"),
            "file": video["path"],
            "collection_id": video.get("collection_id"),
            "channel": video.get("channel", "default"),
            "source": "marathon",
            "daypart_marathon_id": marathon_config.tag,
            "metadata": {
                "scheduled_type": "marathon",
                "marathon_tag": marathon_config.tag,
                "marathon_day": target_date.strftime("%A").lower()
            }
        }
        marathon_entries.append(entry)
        
        # Move time forward by video duration
        current_time += timedelta(seconds=video.get("duration", 0))
        
        # Stop if we've gone past 24:00
        if current_time.hour == 0 and current_time.minute == 0 and current_time.day > target_date.day:
            break
    
    return marathon_entries
```

### 5.4 Complete Daypart Generation Flow

```python
def generate_daypart_schedule(channel: str, 
                              date: datetime,
                              time_blocks: List[TimeBlock],
                              marathons: List[MarathonConfig],
                              gap_filler: GapFillerConfig,
                              available_videos: List[dict]) -> List[dict]:
    """
    Main entry point for generating a daypart-based schedule.
    
    Args:
        channel: Channel name
        date: Target date for schedule generation
        time_blocks: List of time blocks for the day
        marathons: List of marathon configurations
        gap_filler: Gap filler configuration
        available_videos: Pool of all available videos
    
    Returns:
        Complete schedule entries for the day
    """
    schedule_entries = []
    
    # Check if this day has a marathon
    day_name = date.strftime("%A").lower()
    active_marathon = None
    
    for marathon in marathons:
        if marathon.enabled and day_name in marathon.days:
            active_marathon = marathon
            break
    
    if active_marathon:
        # Generate marathon schedule (overrides time blocks)
        marathon_entries = generate_marathon_schedule(
            active_marathon, 
            available_videos, 
            date
        )
        schedule_entries.extend(marathon_entries)
    else:
        # Process time blocks
        sorted_blocks = sorted(time_blocks, key=lambda b: b.start_time)
        
        for block in sorted_blocks:
            block_entries = generate_block_schedule(
                block, 
                available_videos,
                schedule_entries  # Pass existing to check for overlaps
            )
            schedule_entries.extend(block_entries)
        
        # Fill gaps if enabled
        if gap_filler.enabled:
            gaps = detect_gaps(time_blocks)
            gap_entries = fill_gaps_with_random(
                gaps, 
                available_videos, 
                gap_filler,
                get_recent_videos(channel, date)
            )
            schedule_entries.extend(gap_entries)
    
    # Sort by time
    schedule_entries.sort(key=lambda e: e["time"])
    
    return schedule_entries
```

---

## 6. Implementation Plan

### 6.1 Phase 1: Core Scheduler (Week 1-2)

**Day 1-3: Data Structures**
- Implement `TimeBlock` class
- Implement `MarathonConfig` class
- Implement `GapFillerConfig` class
- Add serialization/deserialization methods

**Day 4-7: Gap Detection & Filling**
- Implement `detect_gaps()` function
- Implement `fill_gaps_with_random()` function
- Add configuration options for gap filler

**Day 8-10: Integration**
- Integrate with existing `simple_scheduler.py`
- Add backward compatibility mode
- Test with existing schedules

### 6.2 Phase 2: Marathon Mode (Week 3)

**Day 11-13: Marathon Algorithm**
- Implement `generate_marathon_schedule()`
- Add tag-based video filtering
- Implement 24-hour no-repeat logic

**Day 14-15: Day-of-Week Logic**
- Add day selection UI
- Implement weekly pattern matching
- Test marathon on specific days

### 6.3 Phase 3: UI Integration (Week 4-5)

**Day 16-20: New Tab Development**
- Create "Schedule Programming" tab
- Implement Time Block Management panel
- Implement Add/Edit Block dialog

**Day 21-25: Marathon Panel**
- Create Marathon Scheduling panel
- Add tag dropdown population
- Implement day selection checkboxes

**Day 26-28: Gap Filler & Preview**
- Create Gap Filler Settings panel
- Implement Visual Timeline preview
- Add Text Preview generation

**Day 29-30: Testing & Polish**
- Cross-browser testing
- Performance optimization
- User acceptance testing

### 6.4 Phase 4: API Routes (Week 6)

**Day 31-33: Backend Routes**
- Create `/api/schedule/daypart/config` GET/POST
- Create `/api/schedule/daypart/preview` POST
- Create `/api/schedule/daypart/generate` POST

**Day 34-36: Frontend Integration**
- Connect UI to API routes
- Add error handling
- Implement loading states

**Day 37-38: Persistence**
- Save daypart config to schedule JSON
- Load on startup
- Handle migrations

### 6.5 Phase 5: Testing & Documentation (Week 7)

**Day 39-42: Comprehensive Testing**
- Unit tests for all new classes
- Integration tests with existing system
- Edge case handling (overnight blocks, empty tags, etc.)

**Day 43-45: Documentation**
- Update user documentation
- Create video tutorials
- Document API endpoints

---

## 7. Edge Cases and Error Handling

### 7.1 Overlapping Time Blocks

**Scenario**: User creates overlapping blocks (06:00-10:00 and 08:00-12:00)

**Handling**:
1. Validate on save: Reject overlapping blocks
2. Show error message: "Time block overlaps with existing block"
3. Highlight conflicting block in red

### 7.2 Overnight Blocks

**Scenario**: Block spans midnight (e.g., 22:00-02:00)

**Handling**:
1. Allow overnight blocks in UI
2. Calculate duration correctly (4 hours, not 20)
3. Display with special indicator
4. Handle in gap detection (treat as continuous)

### 7.3 Empty Tag Pool

**Scenario**: User selects tag "rare_tag" with no videos

**Handling**:
1. Validate on block creation: Show warning if no videos match
2. At generation time: Log warning, skip block
3. In preview: Show "No videos available" indicator

### 7.4 Insufficient Videos for Marathon

**Scenario**: Tag has 10 hours of content but marathon needs 24

**Handling**:
1. Calculate required vs available duration
2. If insufficient: Log warning
3. Option: Repeat videos (respecting no-repeat setting) or fill with gap filler

### 7.5 Video Duration Exceeds Block

**Scenario**: Block is 1 hour but video is 2 hours

**Handling**:
1. Play entire video (no truncation)
2. Next block starts after video ends (may overlap)
3. Visual indicator in preview showing overlap

### 7.6 Blacklisted Videos in Tags

**Scenario**: Tag includes blacklisted videos

**Handling**:
1. Filter out blacklisted videos at generation time
2. If no videos remain after filtering, log warning
3. Gap filler may be used to fill resulting gaps

---

## 8. Backward Compatibility

### 8.1 Existing Schedule Format

The existing simple scheduler JSON format will continue to work:

```json
{
  "metadata": {
    "channel": "critters",
    "version": "1.0",
    "schedule_type": "simple"
  },
  "weekly": {
    "monday": [
      {"time": "00:00:00", "file": "..."}
    ]
  }
}
```

### 8.2 Migration Path

1. **Detection**: On load, check `metadata.schedule_type`
2. **Mode Selection**: 
   - If "simple": Use existing `simple_scheduler.py`
   - If "daypart": Use new daypart generation logic
3. **Conversion**: Provide one-way migration tool to convert simple schedules to daypart blocks

### 8.3 UI Adaptation

- Show "Simple" vs "Daypart" toggle in UI
- When in Simple mode: Hide Schedule Programming tab
- When switching modes: Warn about data loss (one-way conversion)

---

## 9. Performance Considerations

### 9.1 Caching Strategy

- **Tag Index**: Build once, update on collection changes
- **Video Duration Cache**: Store in memory, persist to disk
- **Blacklist Cache**: Load on startup, refresh on change

### 9.2 Generation Optimization

- **Lazy Loading**: Only load videos needed for visible time range
- **Parallel Processing**: Generate each day in parallel
- **Incremental Updates**: Only regenerate affected days

### 9.3 Memory Management

- **Video Pool Limits**: Cap at 1000 videos per tag
- **Streaming**: Don't load all video metadata at once
- **Cleanup**: Clear caches on schedule save

---

## 10. Testing Strategy

### 10.1 Unit Tests

- `TimeBlock` class methods
- `MarathonConfig` serialization
- `GapFillerConfig` filtering
- `detect_gaps()` algorithm
- `fill_gaps_with_random()` algorithm

### 10.2 Integration Tests

- End-to-end daypart generation
- Marathon on specific day
- Gap filling with various configurations
- Overlap detection and handling

### 10.3 UI Tests

- Tab navigation
- Block CRUD operations
- Preview generation
- Error message display

### 10.4 Performance Tests

- Large tag pools (1000+ videos)
- Many time blocks (20+)
- Overnight marathon generation
- Concurrent schedule generation

---

## 11. API Reference

### 11.1 Configuration Endpoints

#### GET /api/schedule/daypart/config
Get daypart configuration for a channel.

**Response**:
```json
{
  "success": true,
  "config": {
    "time_blocks": [...],
    "marathons": [...],
    "gap_filler": {...}
  }
}
```

#### POST /api/schedule/daypart/config
Save daypart configuration.

**Request**:
```json
{
  "channel": "critters",
  "config": {
    "time_blocks": [...],
    "marathons": [...],
    "gap_filler": {...}
  }
}
```

### 11.2 Preview Endpoints

#### POST /api/schedule/daypart/preview
Generate a preview of the daypart schedule.

**Request**:
```json
{
  "channel": "critters",
  "date": "2025-01-15"
}
```

**Response**:
```json
{
  "success": true,
  "preview": [
    {
      "time": "06:00:00",
      "duration": 14400,
      "content_type": "tag",
      "content_value": "kids",
      "entries": [...]
    }
  ],
  "gaps": [
    {"start": "10:00", "end": "12:00", "duration": 7200}
  ]
}
```

### 11.3 Generation Endpoints

#### POST /api/schedule/daypart/generate
Generate actual schedule entries.

**Request**:
```json
{
  "channel": "critters",
  "days": 7
}
```

---

## 12. Open Questions for Review

1. **UI Framework**: Should we use Qt (PyQt) for desktop or focus on web UI?

2. **Block Templates**: Should we add predefined block templates (e.g., "Weekday Morning", "Friday Night Horror")?

3. **Conflict Resolution**: How should we handle when marathon and time blocks overlap?

4. **Video Transitions**: Should blocks have "lead-out" or "lead-in" time for smooth transitions?

5. **Live TV Integration**: Should daypart scheduling support live TV inputs in specific blocks?

6. **Recurring Schedules**: Beyond weekly, should we support monthly or custom recurrence patterns?

7. **Export Options**: Should we allow exporting schedules to iCal or other formats?

8. **Multi-Channel**: Should a single daypart config apply to multiple channels or be per-channel?

---

## 13. Conclusion

The Daypart Scheduler feature represents a significant upgrade to AkiraTV's scheduling capabilities, bringing broadcast-style programming to the platform. By implementing time-block-based scheduling with tag-based content selection, gap filling, and marathon support, users will have unprecedented control over their channel's programming.

The phased implementation approach allows for incremental delivery and testing, minimizing risk while ensuring each component is thoroughly validated before moving to the next phase.

This proposal provides a comprehensive blueprint for development, but we welcome feedback and adjustments based on user needs and technical constraints discovered during implementation.
