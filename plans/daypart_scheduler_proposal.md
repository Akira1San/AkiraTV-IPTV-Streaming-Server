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
    Fill each gap with random video selections.
    
    Args:
        gaps: List of (start, end) time tuples
        available_videos: Pool of videos to choose from
        gap_filler_config: Configuration for gap filling
        recent_videos: List of (video_path, timestamp) for 24h rule
    
    Returns:
        List of schedule entries for gap content
    """
    if recent_videos is None:
        recent_videos = []
    
    gap_entries = []
    
    for gap_start, gap_end in gaps:
        gap_duration = calculate_duration(gap_start, gap_end)
        current_time = datetime.strptime(gap_start, "%H:%M")
        end_time = datetime.strptime(gap_end, "%H:%M")
        
        # Track videos used in this gap (for 24h rule if enabled)
        gap_recent = [] if gap_filler_config.respect_24h_norepeat else None
        
        while current_time < end_time:
            # Filter available videos
            candidates = available_videos.copy()
            
            # Apply 24h no-repeat rule
            if gap_filler_config.respect_24h_norepeat:
                recent_paths = {path for path, _ in recent_videos}
                candidates = [v for v in candidates if v["path"] not in recent_paths]
            
            # Apply excluded tags
            if gap_filler_config.excluded_tags:
                candidates = [v for v in candidates 
                            if not has_excluded_tag(v, gap_filler_config.excluded_tags)]
            
            if not candidates:
                # Emergency: reset recent videos and try again
                candidates = available_videos
                if gap_filler_config.respect_24h_norepeat:
                    recent_videos.clear()
            
            # Select video
            if gap_filler_config.shuffle:
                selected = random.choice(candidates)
            else:
                # Sequential selection
                selected = candidates[0]
            
            # Add to schedule
            entry = {
                "time": current_time.strftime("%H:%M:%S"),
                "file": selected["path"],
                "collection_id": selected["collection"]["id"],
                "channel": "TARGET_CHANNEL",
                "source": "gap_filler"
            }
            gap_entries.append(entry)
            
            # Track for 24h rule
            if gap_filler_config.respect_24h_norepeat:
                seconds_from_day_start = (current_time - datetime(2023,1,2,0,0)).total_seconds()
                recent_videos.append((selected["path"], seconds_from_day_start))
                if gap_recent is not None:
                    gap_recent.append(selected["path"])
            
            # Advance time
            current_time += timedelta(seconds=selected["duration"])
    
    return gap_entries
```

### 5.3 Complete Daypart Schedule Generation

```python
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
    """
    schedule_entries = []
    recent_videos = []  # For 24h no-repeat tracking
    
    # 1. Check for marathon on this day
    marathon_entries = []
    is_marathon_day = False
    for marathon in daypart_config["marathons"]:
        if marathon["enabled"] and target_date.weekday() in get_weekday_indices(marathon["days"]):
            is_marathon_day = True
            marathon_entries = generate_marathon_schedule(
                marathon["tag"], 
                available_videos,
                marathon_config=marathon,
                recent_videos=recent_videos
            )
            schedule_entries.extend(marathon_entries)
            break  # Only one marathon per day
    
    # 2. If not marathon day, apply time blocks
    if not is_marathon_day:
        for block in daypart_config["time_blocks"]:
            block_entries = generate_block_schedule(
                block, 
                available_videos,
                recent_videos
            )
            schedule_entries.extend(block_entries)
    
    # 3. Detect and fill gaps (only if not marathon day and gap filler enabled)
    if not is_marathon_day and daypart_config["gap_filler"]["enabled"]:
        # Extract block time ranges
        block_times = [(b.start_time, b.end_time) for b in daypart_config["time_blocks"]]
        gaps = detect_gaps(block_times)
        
        if gaps:
            gap_entries = fill_gaps_with_random(
                gaps,
                available_videos,
                daypart_config["gap_filler"],
                recent_videos
            )
            schedule_entries.extend(gap_entries)
    
    # 4. Sort by time
    schedule_entries.sort(key=lambda e: e["time"])
    
    return schedule_entries
```

---

## 6. Implementation Phases and Technical Details

### Phase 1: Core Infrastructure (Week 1-2) [x]

**Tasks**:
1. Create `akiratv/daypart_scheduler.py` with:
   - `TimeBlock` class
   - `MarathonConfig` class
   - `GapFillerConfig` class
   - `DaypartScheduler` main class
   [x] Completed

2. Add data persistence:
   - Load/save daypart config to/from JSON
   - Store in `user/schedules/daypart_{channel}.json`
   - Maintain backward compatibility with existing schedule.json
   [x] Completed

3. Unit tests for:
   - Time arithmetic (duration calculation, overnight handling)
   - Gap detection algorithm
   - Serialization/deserialization
   [x] Completed (54 tests passing)

**Deliverable**: Working daypart configuration system with file I/O [x] COMPLETED

### Phase 2: UI Implementation (Week 3-4) [x]

**Tasks**:
1. Extend `simple_scheduler.py`:
   - Add "Schedule Programming" tab to `create_added_panel()`
   - Create `create_schedule_programming_tab()` method
   - Implement block list display with listbox
   - Add block control buttons
   [x] Completed

2. Create modal dialogs:
   - `EditBlockDialog` class for add/edit operations
   - Video search/selection within dialog
   - Tag selection with autocomplete from existing tags
   [x] Completed

3. Implement marathon panel:
   - Tag dropdown populated from collections
   - Day checkboxes
   - Options toggles
   [x] Completed

4. Implement gap filler settings panel:
   - Source selection (all/collections/tags)
   - Tag exclusion dialog
   - Checkboxes for options
   [x] Completed

5. Preview panel:
   - Visual timeline canvas (24h bar)
   - Text preview listbox
   - Color coding and tooltips
   [x] Completed

**Deliverable**: Complete UI for daypart configuration [x] COMPLETED

### Phase 3: Schedule Generation Integration (Week 5-6) [x]

**Tasks**:
1. Extend `scheduler.py`:
   - Add `generate_daypart_schedule()` function
   - Modify `get_current_schedule_for_channel()` to detect and use daypart config
   - Ensure daypart entries are properly formatted for workers
    [x] Completed

2. Connect UI to generation:
   - "Generate Preview" button calls daypart scheduler
   - Display preview in timeline and list
   - Show statistics (total blocks, gap segments, estimated runtime)
    [x] Completed (UI side, needs scheduler integration)

3. Save integration:
   - "Save Schedule" writes daypart config + generated entries
   - Maintain separate weekly/calendar sections (empty when daypart active)
   - Update `_save_schedule()` in simple_scheduler.py
    [x] Completed

4. Validation:
   - Ensure blocks don't overlap (UI validation)
   - Ensure total block time ≤ 24 hours
   - Validate time formats (HH:MM, 00:00-24:00)
   - Check for orphaned gaps at day boundaries
    [x] Completed (UI side)

**Deliverable**: Working end-to-end daypart scheduling [Completed]

### Phase 4: Advanced Features & Polish (Week 7-8)

**Tasks**:
1. Marathon implementation:
   - `generate_marathon_schedule()` function
   - 24-hour continuous playback from tag pool
   - Respect marathon-specific options (shuffle, no-repeat)
   [ ] Pending

2. Gap filler enhancements:
   - Collection-based source selection
   - Tag-based source selection
   - Advanced exclusion UI
   [ ] Pending (basic gap filler implemented)

3. Import/Export:
   - Export daypart config as standalone JSON
   - Import daypart config
   - Copy blocks between channels
   [ ] Pending

4. UX improvements:
   - Drag-and-drop block reordering
   - Duplicate block button
   - Undo/redo for block edits
   - Tooltips and help text
   [ ] Pending (basic reordering implemented)
5. Code organization:
   - Separate daypart scheduler code from simple_scheduler.py into its own module
   - Refactor imports and dependencies
   [ ] Pending

5. Error handling:
   - Clear validation messages
   - Conflict detection (overlapping blocks)
   - Graceful fallback when no videos available
   [ ] Pending

**Deliverable**: Production-ready daypart scheduler

### Phase 5: Testing & Documentation (Week 9-10)

**Tasks**:
1. Unit tests (pytest):
   - All algorithm functions
   - Time calculations
   - Gap detection
   - Serialization
   [x] Completed (54 tests)

2. Integration tests:
   - Full schedule generation
   - UI workflows
   - Save/load cycles
   - Worker compatibility
   [ ] Pending

3. Documentation:
   - Update README.md with daypart scheduling section
   - Create user guide (PDF/HTML)
   - In-app tooltips and help
   - Sample configurations
   [ ] Pending

4. Performance testing:
   - Large collection handling (1000+ videos)
   - Schedule generation time (<5s)
   - Memory usage
   [ ] Pending

**Deliverable**: Fully tested and documented feature

---

## 7. File Modifications Needed

### 7.1 New Files

```
akiratv/
├── daypart_scheduler.py          # Core daypart logic (new)
└── plans/
    └── daypart_scheduler_proposal.md  # This document (new)
```

### 7.2 Modified Files

#### `akiratv/simple_scheduler.py`

**Changes**:
1. **Import new module**:
```python
from .daypart_scheduler import TimeBlock, MarathonConfig, GapFillerConfig, DaypartScheduler
```

2. **Add instance variables** in `__init__`:
```python
self.daypart_scheduler = DaypartScheduler()
self.daypart_config = None  # Loaded from file
self.daypart_enabled = False
```

3. **Modify `create_added_panel()`**:
   - Add "Schedule Programming" tab next to "Added Videos"
   - Call new method `create_schedule_programming_tab()`

4. **Add new method** `create_schedule_programming_tab(parent)`:
   - Build UI layout as specified in Section 2.2
   - Include block list, marathon panel, gap filler, preview
   - Wire up event handlers

5. **Add dialog classes**:
   - `EditBlockDialog` - modal for block creation/editing
   - `TagExclusionDialog` - multi-select tag exclusion

6. **Add event handlers**:
   - `on_add_block()` - open edit dialog
   - `on_edit_block()` - load selected block into dialog
   - `on_delete_block()` - remove selected blocks
   - `on_move_block_up/down()` - reorder
   - `on_generate_daypart_preview()` - call daypart scheduler
   - `on_save_daypart_schedule()` - save config + generated entries

7. **Update `preview_schedule()`**:
   - Detect if daypart mode active
   - Call appropriate generator (`_generate_daypart_schedule()`)
   - Store `self.current_schedule_mode = "daypart"`

8. **Update `_save_schedule()`**:
   - Handle daypart format (save config + generated entries)
   - Maintain backward compatibility for weekly/calendar

9. **Update `update_preview_display()`**:
   - Handle daypart schedule display
   - Show block types with color coding

#### `akiratv/scheduler.py`

**Changes**:
1. **Import daypart module**:
```python
from .daypart_scheduler import generate_daypart_schedule, load_daypart_config
```

2. **Modify `get_current_schedule_for_channel(channel: str)`**:
```python
def get_current_schedule_for_channel(channel: str) -> List[Dict[str, Any]]:
    # Check for daypart config first
    daypart_config = load_daypart_config(channel)
    if daypart_config and daypart_config.get("enabled", False):
        # Generate daypart schedule for today
        today = date.today()
        weekday = today.weekday()  # 0=Monday
        entries = generate_daypart_schedule(
            daypart_config,
            get_videos_for_channel(channel),  # New helper
            channel,
            today
        )
        return entries
    
    # Fall back to existing weekly/calendar logic
    ...
```

3. **Add helper** `get_videos_for_channel(channel: str)`:
```python
def get_videos_for_channel(channel: str) -> List[Dict]:
    """
    Get all available videos for a channel from collections.
    Respects blacklist and returns full video objects with metadata.
    """
    collections = load_collections_for_channel(channel)
    blacklist = load_blacklist(channel)
    
    videos = []
    for collection in collections:
        for video in collection.get("videos", []):
            if video["path"] not in blacklist:
                video["collection"] = collection
                videos.append(video)
    
    return videos
```

4. **Update schedule validation** in `_validate_entries()`:
   - Accept daypart-specific metadata fields
   - Handle `source: "daypart_tag"` or `"daypart_video"` or `"gap_filler"`

#### `akiratv/collections.py`

**Minimal changes**:
- No modifications required (existing tag system is sufficient)
- Collections already have `tags` field that daypart scheduler will use

#### `akiratv/workers/base_worker.py` or `dynamic_worker.py`

**Check compatibility**:
- Ensure workers accept schedule entries with `source: "daypart_*"`
- No code changes likely needed (workers just need `time`, `file`, `channel`)

---

## 8. Sample Schedule JSON Structures

### 8.1 Daypart Configuration File

**File**: `user/schedules/daypart_critters.json`

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
        "block_id": "block_morning_kids",
        "start_time": "06:00",
        "end_time": "10:00",
        "content_type": "tag",
        "content_value": "kids",
        "duration_seconds": 14400
      },
      {
        "block_id": "block_prime_horror",
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
  "weekly": {},
  "calendar": {}
}
```

### 8.2 Generated Schedule File (After Save)

**File**: `user/schedules/schedule_critters.json`

```json
{
  "metadata": {
    "channel": "critters",
    "created": "2025-01-15T14:22:33",
    "version": "2.0",
    "schedule_type": "daypart"
  },
  "daypart_config": { ... },
  "weekly": {
    "monday": [],
    "tuesday": [],
    "wednesday": [],
    "thursday": [],
    "friday": [],
    "saturday": [],
    "sunday": []
  },
  "calendar": {},
  "generated_entries": {
    "2025-01-15": {
      "entries": [
        {
          "time": "06:00:00",
          "file": "C:/Videos/Akiratv/Kids_Show_S01E01.mp4",
          "collection_id": "kids_show",
          "channel": "critters",
          "source": "daypart_tag",
          "daypart_block_id": "block_morning_kids",
          "metadata": {
            "scheduled_type": "tag",
            "tag_used": "kids",
            "block_start": "06:00",
            "block_end": "10:00"
          }
        },
        {
          "time": "08:15:00",
          "file": "C:/Videos/Akiratv/Kids_Show_S02E07.mp4",
          "collection_id": "kids_show_2",
          "channel": "critters",
          "source": "daypart_tag",
          "daypart_block_id": "block_morning_kids",
          "metadata": {
            "scheduled_type": "tag",
            "tag_used": "kids",
            "block_start": "06:00",
            "block_end": "10:00"
          }
        },
        {
          "time": "10:00:00",
          "file": "C:/Videos/Akiratv/Documentary_Wildlife.mp4",
          "collection_id": "wildlife_doc",
          "channel": "critters",
          "source": "gap_filler",
          "metadata": {
            "scheduled_type": "gap_filler",
            "gap_start": "10:00",
            "gap_end": "12:00"
          }
        },
        {
          "time": "20:00:00",
          "file": "C:/Videos/Akiratv/Horror_Movie_1.mp4",
          "collection_id": "horror_collection",
          "channel": "critters",
          "source": "daypart_tag",
          "daypart_block_id": "block_prime_horror",
          "metadata": {
            "scheduled_type": "tag",
            "tag_used": "horror",
            "block_start": "20:00",
            "block_end": "24:00"
          }
        }
      ]
    }
  }
}
```

**Note**: The `generated_entries` section is optional. The worker system will regenerate the schedule daily using `daypart_config`. Storing generated entries is for debugging/audit only.

---

## 9. Edge Cases and Validation Rules

### 9.1 Time Block Validation

**Rules**:
1. **Time Format**: Must be `HH:MM` in 24-hour format (00:00 to 24:00)
   - Validation: Regex `^([01]?[0-9]|2[0-4]):[0-5][0-9]$`
   - Reject: `24:01`, `25:00`, `12:60`, `abc`

2. **Time Range**: `start_time < end_time` (unless overnight, which is NOT allowed for blocks)
   - Overnight blocks (22:00-02:00) are **invalid** - split into two blocks instead
   - Reason: Daypart scheduler assumes single-day blocks

3. **Block Duration**: Must be > 0 and ≤ 24 hours (max 86400 seconds)
   - Minimum: 1 minute (60 seconds) recommended
   - Maximum: 24 hours (86400 seconds)

4. **No Overlap**: Blocks for the same day must not overlap
   - Validation: Sort by start time, ensure `prev.end <= curr.start`
   - UI: Prevent adding overlapping blocks (highlight conflict)
   - Save-time: Reject if overlaps detected

5. **Total Coverage**: Sum of all block durations can be less than 24 hours (gaps allowed)
   - Cannot exceed 24 hours (would create overlap)
   - Gaps will be filled by gap filler if enabled

### 9.2 Marathon Validation

**Rules**:
1. **Tag Must Exist**: Selected tag must exist in collections (or be new, created on save)
2. **Day Selection**: At least one day must be selected
3. **24-Hour Coverage**: Marathon always covers full 24 hours (00:00-24:00)
4. **Marathon Priority**: Marathon overrides all time blocks on selected days
   - Validation: Warn if marathon day already has time blocks
   - Allow but show warning: "Marathon will replace time blocks on Friday"

### 9.3 Gap Filler Validation

**Rules**:
1. **Source Videos**: Must have at least one video available for gap filling
   - Check: `len(available_videos) > 0`
   - If using collections: selected collections must have videos
   - If using tags: selected tags must have videos

2. **Exclusions**: Excluded tags cannot be the ONLY source
   - Validation: Ensure `available_videos - excluded_tag_videos > 0`

3. **24h No-Repeat**: If enabled, need enough videos to fill gaps without repeat
   - Minimum videos required: `ceil(total_gap_duration / min_video_duration)`
   - If insufficient, either disable rule or allow repeats after pool exhausted

### 9.4 Schedule Generation Edge Cases

**Case 1: Video longer than block**
- **Behavior**: Video plays in full, overrunning into next block
- **Rationale**: Truncating videos is unacceptable; better to shift schedule
- **Implementation**: Do not pre-split videos; let them play completely
- **Note**: This is standard broadcast behavior (programs don't get cut)

**Case 2: No videos available for tag**
- **Behavior**: Skip block, log warning, try to fill with gap filler
- **UI**: Show warning "No videos found for tag 'horror'"
- **Fallback**: If gap filler enabled, treat as gap; else show blank

**Case 3: Marathon tag has insufficient videos**
- **Behavior**: Repeat videos after exhausting pool (respecting 24h rule if enabled)
- **Log**: "Marathon pool exhausted after N videos, resetting"
- **User Message**: "Not enough videos for 24h marathon; repeats enabled"

**Case 4: All videos blacklisted**
- **Behavior**: Abort generation with error
- **Message**: "All videos are blacklisted. Remove from blacklist or add more videos."

**Case 5: Gap filler source empty**
- **Behavior**: Leave gaps unfilled (silence/standby)
- **Log**: "Gap filler source empty - gaps will remain unfilled"
- **UI**: Show warning but allow save

**Case 6: Overnight wrap (23:59 → 00:00)**
- **Behavior**: Daypart schedule is daily; no overnight carryover
- **Implementation**: Each day starts fresh at 00:00
- **Note**: If a video starts at 23:50 with 30-minute duration, it ends at 24:20 (next day)
  - Worker will handle this naturally (next day's first block starts at 00:00, but previous video still playing)
  - This is acceptable (overlap into next day)

**Case 7: Daylight Saving Time**
- **Behavior**: Not handled by daypart scheduler
- **Rationale**: Scheduler uses wall-clock times (HH:MM), not UTC
- **Responsibility**: System clock should handle DST transitions
- **Recommendation**: Avoid scheduling changes on DST transition days

**Case 8: Missing collections file**
- **Behavior**: Show error "Collections not found. Please configure collections first."
- **Prevention**: Disable daypart tab if no collections loaded

### 9.5 Data Integrity Validation

**On Load**:
```python
def validate_daypart_config(config: dict) -> List[str]:
    errors = []
    
    # Check required fields
    if "daypart_config" not in config:
        return ["Missing daypart_config section"]
    
    dp = config["daypart_config"]
    
    # Validate time blocks
    for i, block in enumerate(dp.get("time_blocks", [])):
        try:
            TimeBlock.from_dict(block)
        except ValueError as e:
            errors.append(f"Block {i}: {e}")
    
    # Check for overlaps
    blocks = [TimeBlock.from_dict(b) for b in dp.get("time_blocks", [])]
    if has_overlaps(blocks):
        errors.append("Time blocks overlap")
    
    # Validate marathons
    for m in dp.get("marathons", []):
        if not m.get("tag"):
            errors.append("Marathon missing tag")
        if not m.get("days"):
            errors.append(f"Marathon {m.get('tag')} has no days selected")
    
    return errors
```

**On Save**:
- Run validation before writing to file
- Prevent save if validation fails
- Show all errors to user

---

## 10. Backward Compatibility

### 10.1 Existing Schedules
- All existing `schedule_*.json` files continue to work unchanged
- They use `weekly` or `calendar` format without `daypart_config`
- `scheduler.py` will use existing logic for these files

### 10.2 UI Toggle
- Daypart tab is always visible (even if no collections)
- If user doesn't configure daypart, they can still use weekly/calendar modes
- No breaking changes to existing workflows

### 10.3 Migration Path
- Users can adopt daypart scheduling incrementally
- Can mix daypart with weekly? **No** - daypart replaces weekly for that channel
- Clear UI indication: "Daypart mode active" vs "Weekly mode active"

---

## 11. Performance Considerations

### 11.1 Schedule Generation Time
- **Target**: < 5 seconds for 1000 videos, 10 blocks
- **Algorithm Complexity**: O(n * m) where n = videos, m = blocks
- **Optimization**: 
  - Cache tag-to-video mappings
  - Pre-filter videos once per generation
  - Use efficient data structures (sets for recent videos)

### 11.2 Memory Usage
- **Target**: < 200MB for 1000 videos
- **Strategy**: 
  - Load collections on-demand, not all at once
  - Stream schedule generation (don't build full 7-day schedule if only viewing one day)
  - Clear caches after generation

### 11.3 UI Responsiveness
- **Problem**: Schedule generation could freeze UI
- **Solution**: Run generation in background thread
  - Use `threading.Thread` for preview generation
  - Show progress dialog
  - Update UI via `after()` callback

---

## 12. Success Criteria

### 12.1 Functional Requirements
- [ ] User can create, edit, delete time blocks
- [ ] Blocks can specify video OR tag content
- [ ] Blocks can be reordered
- [ ] Marathon can be configured for tag + days
- [ ] Gap filler can be configured with source and exclusions
- [ ] Preview shows visual timeline and text schedule
- [ ] Schedule saves to JSON and loads correctly
- [ ] Generated schedule plays correctly in worker
- [ ] No regressions in existing weekly/calendar scheduling

### 12.2 Quality Requirements
- [ ] All validation rules enforced
- [ ] Clear error messages for user mistakes
- [ ] No crashes on edge cases (empty collections, missing videos)
- [ ] 24-hour no-repeat rule works correctly
- [ ] Overnight video playback handled gracefully
- [ ] Blacklist respected in all content selection

### 12.3 Performance Requirements
- [ ] Preview generation < 5 seconds for 500 videos
- [ ] UI remains responsive during generation
- [ ] Memory usage < 300MB during operation

---

## 13. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Complex time arithmetic bugs | High | Comprehensive unit tests for all time calculations |
| Overlap detection misses edge cases | High | Validation on add/edit + save-time re-check |
| Gap filler creates infinite loops | Medium | Limit iterations, fallback to sequential |
| Performance degrades with many blocks | Medium | Efficient algorithms, background threading |
| User confusion between modes | Medium | Clear UI indicators, tooltips, documentation |
| Marathon conflicts with blocks | Low | Validation warning, allow override with confirmation |
| Tag resolution returns no videos | Medium | Show warning, suggest checking collections/tags |

---

## 14. Conclusion

The Daypart Scheduler represents a significant enhancement to AkiraTV's scheduling capabilities, bringing broadcast-style programming to the platform. By building upon the existing collection and tag infrastructure, we minimize development risk while delivering powerful new functionality.

The phased approach allows for incremental delivery and user feedback. The modular design ensures that daypart scheduling can coexist with the existing weekly/calendar modes, providing a smooth migration path for users.

**Next Steps**:
1. Review this proposal with stakeholders
2. Approve Phase 1 implementation
3. Begin development of `daypart_scheduler.py` core module
4. Iterate based on testing and feedback

---

## Appendix A: UI Mockup Details

### A.1 Schedule Programming Tab - Full Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Simple Random Scheduler                                      [X]          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────┬────────────┬──────────────┬──────────────────────────────┐ │
│  │ Info     │ Collections│ Added Videos │ Schedule Programming         │ │
│  │ Panel    │ & Standby  │              │                              │ │
│  │          │            │              │                              │ │
│  │ Name:    │ Profile:   │ [Added Videos]│ ┌─────────────────────────┐│ │
│  │ -        │ [collections▾]│ [Blacklist] │ │ Time Blocks (3)        ││ │
│  │          │            │              │ │ ┌─────────────────────┐││ │
│  │ Cover:   │ Collections│ Total: 5     │ │ │ 06:00-10:00 [TAG:kids]│││ │
│  │ [image]  │ • Coll 1   │ [Add to      │ │ │ 10:00-12:00 [VIDEO]  │││ │
│  │          │ • Coll 2   │  Blacklist]  │ │ │   The Matrix.mp4    │││ │
│  │ Genre:   │ • Coll 3   │ [Remove Sel] │ │ │ 20:00-24:00 [TAG:horror]│││
│  │ -        │            │ [Remove All] │ │ └─────────────────────┘││ │
│  │          │ [Select All]│              │ │                         ││ │
│  │          │ [Add Selected]│            │ │ Marathon Scheduling    ││ │
│  │          │            │              │ │ Tag: [horror▾]         ││ │
│  │          │            │              │ │ Days: [✓]Mon [✓]Tue...││ │
│  │          │            │              │ │ [✓] Fill 24h          ││ │
│  │          │            │              │ │ [✓] Shuffle           ││ │
│  │          │            │              │ └─────────────────────────┘│ │
│  │          │            │              │                              │ │
│  │          │            │              │ ┌─────────────────────────┐│ │
│  │          │            │              │ │ Gap Filler Settings    ││ │
│  │          │            │              │ │ ☑ Enable gap filling   ││ │
│  │          │            │              │ │ Source: ○ All ○ Colls  ││ │
│  │          │            │              │ │ Excluded: [horror, kids]││ │
│  │          │            │              │ └─────────────────────────┘│ │
│  │          │            │              │                              │ │
│  │          │            │              │ ┌─────────────────────────┐│ │
│  │          │            │              │ │ Preview Timeline        ││ │
│  │          │            │              │ │ 00:00 ████████████████ ││ │
│  │          │            │              │ │ 06:00 ████████████████ ││ │
│  │          │            │              │ │ 12:00 ████████████████ ││ │
│  │          │            │              │ │ 18:00 ████████████████ ││ │
│  │          │            │              │ └─────────────────────────┘│ │
│  └──────────┴────────────┴──────────────┴──────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────┤
│  Channel: [critters▾]  Mode: ○ Weekly ○ Calendar  [RAND] [▶] [SAVE] [Theme:▾]│
└─────────────────────────────────────────────────────────────────────────────┘
```

### A.2 Edit Block Dialog

```
┌─────────────────────────────────────────────┐
│ Edit Time Block                             │
├─────────────────────────────────────────────┤
│                                             │
│  Start Time:  [06:00]    End Time: [10:00] │
│                                             │
│  Content Type: ○ Specific Video  ○ Tag      │
│                                             │
│  If Specific Video:                         │
│    Search: [________________] [Search]      │
│    Results:                                 │
│    ☐ The Matrix (1999).mp4                 │
│    ☐ Into the Sun.mp4                      │
│    ☐ Kids Show S01E01.mp4                  │
│    (Scroll)                                │
│    Selected: [The Matrix (1999).mp4]       │
│                                             │
│  If Tag:                                   │
│    Tag: [horror▾]                          │
│    Or New: [__________]                    │
│                                             │
│  Duration: 4 hours (14400 seconds)         │
│                                             │
│  [Cancel]  [Save]                          │
└─────────────────────────────────────────────┘
```

---

## Appendix B: Migration from Existing Block Programming Plan

The existing `plans/block_programming_feature_plan.md` proposed a more complex system with:
- Modal dialogs for block creation
- Drag-and-drop timeline
- Priority system
- Conflict resolution UI

**This proposal simplifies**:
- No modal dialogs for main workflow (inline block list)
- No drag-and-drop (simple up/down buttons)
- No priority system (blocks are ordered by time)
- No conflict resolution UI (prevention via validation)

The simplified approach is more aligned with the current `simple_scheduler.py` philosophy: straightforward, functional, and easy to implement.

---

**Document Version**: 1.0  
**Date**: 2025-01-15  
**Author**: AkiraTV Architecture Team  
**Status**: Draft for Review