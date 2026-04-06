# Approximate Calc Improvement Plan

## Problem

Currently the Approximate feature only works with explicit TimeBlock objects (user-defined video blocks). It doesn't account for gap filler videos that fill the 24-hour schedule.

Example issue:
```
16:59 [gap_filler] Belly of the Beast
17:00 [daypart_tag] The Terminator 3
20:00 [daypart_tag] Hard To Kill
```

There's only 1 minute gap between the gap filler video and the daypart block.

## How It Should Work

### Process Flow:
1. **First**: Gap filler fills 24/h a day with random videos
2. **Second**: Approximate calc looks at the created daypart blocks
3. **Third**: Approximate tries to move them in order for the random gen previewer to generate a smooth 24/h a day schedule

### Example 1 - Replace Gap Video
- Gap video starts at 12:30
- Daypart tag block is set for 17:00
- **Result**: Approximate moves/replaces the 12:30 video with the daypart tag block, becoming: `12:30 [daypart_tag] ...`

### Example 2 - Shift Block to Fit
- Gap video starts at 13:00, duration is 1h 30min (ends 14:30)
- Daypart block tag starts at 14:00
- **Result**: Approximate moves the block to start at 14:30 to avoid cutting the gap video

### Example 3 - Continuous Stream
- Goal: Create a continuous stream of videos without gaps or cuts
- If a daypart block would create a gap or cut a video, move it to fill the gap

## Implementation Requirements

### 1. Get Gap Filler Videos
- Need to access the generated schedule entries from gap filler
- These entries have: start_time, end_time, duration, video_path
- Similar to TimeBlock but from gap filler source

### 2. Merge Sources for Approximate Calc
- Combine: explicit TimeBlocks + gap filler videos
- Treat both as "existing content" that shouldn't be cut

### 3. Calculate Optimal Position
- For each daypart block, find the best position
- Priority: Fill gaps, avoid cuts, keep original time if possible
- Consider video durations when shifting

### 4. Generate Smooth Schedule
- After approximation, the preview should show continuous videos
- No short videos at gap boundaries
- All daypart blocks properly positioned

## Data Structures Needed

```python
class ScheduledEntry:
    """Represents any scheduled content (block or gap video)"""
    start_time: str      # "HH:MM"
    end_time: str       # "HH:MM"
    duration_seconds: int
    source: str         # "block" or "gap_filler"
    content_type: str   # "video", "tag"
    content_value: str  # video path or tag name
```

## Files to Modify

1. `akiratv/daypart_scheduler.py`
   - Add `ScheduledEntry` class
   - Modify `approximate_block_timing()` to accept gap filler entries
   - Add logic to merge blocks + gap videos

2. `akiratv/daypart_scheduler_mixin.py`
   - Pass gap filler schedule to Approximate function

3. `akiratv/simple_scheduler.py` or preview generation
   - Get gap filler entries before running approximation