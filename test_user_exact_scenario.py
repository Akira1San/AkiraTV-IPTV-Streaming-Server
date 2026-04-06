# test_user_exact_scenario.py
"""
Reproduce the USER'S exact scenario from their log:

=== 2026-04-01 (Wednesday) ===
  17:00 [daypart_tag] Commando
  18:38 [gap_filler] red heat
  20:00 [daypart_tag] Above the Law
  20:00 [gap_filler] Double Impact
  21:33 [gap_filler] Wolfhound
  21:44 [gap_filler] Cartels
  23:15 [gap_filler] Total Recall
  23:42 [gap_filler] Belly of the Beast

The user says:
- "the schedule starts from 17:00 as is my first block tag"

But they also say gap filler is working - filling from 17:00 onwards.

Let me analyze:
- 17:00-18:38: First block (Commando) - this runs 98 minutes
- 18:38-20:00: Gap filler (red heat) - this is the gap!
- 20:00: Second block starts

The issue is: The user wants the schedule to start at 00:00, not 17:00!
But they're saying "the schedule starts from 17:00"

Wait, let me re-read the issue more carefully...

Actually the user's issue is:
"but when i add block tags - copy log: - the schedule starts from 17:00"

They mean: when they ADD block tags, the schedule starts at 17:00 instead of 00:00.

BEFORE adding blocks: Gap filler fills the whole day from 00:00
AFTER adding blocks: Gap filler only fills from 17:00 (because blocks are at 17:00 and 20:00)

The bug is: The gap detector sees blocks at 17:00 and 20:00, so it detects
gaps as: 00:00-17:00 and 20:00-24:00

But the gap filler is filling from 17:00 onwards, NOT 00:00-17:00!

Wait no, let me re-read the user's log again...

Actually looking at the log:
  17:00 [daypart_tag] Commando
  18:38 [gap_filler] red heat

The gap_filler IS filling from 18:38 to 20:00. That's correct.

But what about 00:00-17:00? The user doesn't show that, so maybe it's missing?

Let me test: Does gap filler fill 00:00-17:00 or not?
"""

import sys
sys.path.insert(0, '.')

from datetime import date, datetime
from akiratv.daypart_scheduler import (
    generate_daypart_schedule,
    TimeBlock,
    detect_gaps
)


def test_user_exact_scenario():
    """
    Reproduce user's exact scenario:
    - Block 1: 17:00-20:00 (daypart_tag)
    - Block 2: 20:00-24:00 (daypart_tag)
    
    Expected:
    - Gap filler fills 00:00-17:00 (before first block)
    - Gap filler fills 18:38-20:00 (between blocks, if first video ends early)
    """
    print("=" * 60)
    print("TEST: User's exact scenario")
    print("=" * 60)
    
    test_date = date(2026, 4, 1)  # Wednesday
    
    # Same as user's config
    daypart_config = {
        "daypart_config": {
            "time_blocks": [
                {
                    "block_id": "block1",
                    "start_time": "17:00",
                    "end_time": "20:00",
                    "content_type": "tag",
                    "content_value": "action",  # daypart_tag
                },
                {
                    "block_id": "block2",
                    "start_time": "20:00", 
                    "end_time": "24:00",
                    "content_type": "tag",
                    "content_value": "action",
                }
            ],
            "marathons": [],
            "gap_filler": {
                "enabled": True,
                "source": "all",
                "excluded_tags": [],
                "respect_24h_norepeat": True,
                "shuffle": True
            }
        }
    }
    
    # Use video durations similar to user's log:
    # - First video "Commando" runs ~98 min (17:00 to 18:38)
    # - Gap filler "red heat" fills 18:38-20:00
    available_videos = [
        # First block video - ~98 minutes like "Commando"
        {"path": "/commando.mp4", "duration": 5880, "tags": ["action"], "collection": {"id": "a"}},  # 98 min = 18:38
        
        # Gap filler videos
        {"path": "/red_heat.mp4", "duration": 4920, "tags": ["action"], "collection": {"id": "a"}},  # 82 min -> ends 21:22
        {"path": "/double_impact.mp4", "duration": 5700, "tags": ["action"], "collection": {"id": "a"}},  # 95 min
        {"path": "/wolfhound.mp4", "duration": 4200, "tags": ["action"], "collection": {"id": "a"}},  # 70 min
        {"path": "/cartels.mp4", "duration": 2940, "tags": ["action"], "collection": {"id": "a"}},  # 49 min
        
        # Second block video
        {"path": "/above_the_law.mp4", "duration": 5400, "tags": ["action"], "collection": {"id": "a"}},  # 90 min
    ]
    
    # First, let's check what gaps are detected
    blocks = [
        TimeBlock("17:00", "20:00", "tag", "action"),
        TimeBlock("20:00", "24:00", "tag", "action"),
    ]
    detected_gaps = detect_gaps(blocks)
    print(f"Detected gaps: {detected_gaps}")
    
    # Now generate the schedule
    entries, last_time = generate_daypart_schedule(
        daypart_config,
        available_videos,
        "test_channel",
        test_date
    )
    
    print(f"\nFull schedule for {test_date}:")
    for entry in entries:
        print(f"  {entry['time']} [{entry['source']}] {entry.get('file', '')}")
    
    # Check what time range is covered
    if entries:
        times = [e['time'] for e in entries]
        print(f"\nTime range: {min(times)} to {max(times)}")
        
        # Check for gap filler before 17:00
        gap_entries = [e for e in entries if e.get('source') == 'gap_filler']
        before_17 = [e for e in gap_entries if int(e['time'].split(':')[0]) < 17]
        
        print(f"\nGap filler entries: {len(gap_entries)}")
        if before_17:
            print(f"  BEFORE 17:00: {len(before_17)} entries")
            for e in before_17:
                print(f"    {e['time']} - {e['file']}")
        else:
            print("  No gap filler entries before 17:00 - THIS IS THE BUG!")
        
        # User's expectation: Gap filler should fill from 00:00
        # But it seems to start from 17:00 or later
        
        return len(before_17) > 0
    
    return False


if __name__ == "__main__":
    result = test_user_exact_scenario()
    
    if result:
        print("\n*** PASS: Gap filler fills 00:00-17:00 ***")
    else:
        print("\n*** FAIL: Gap filler does NOT fill 00:00-17:00 ***")
        print("This is the bug - gap detector sees blocks at 17:00 and 20:00,")
        print("detects gap 00:00-17:00, but gap filler doesn't fill it!")
        sys.exit(1)
