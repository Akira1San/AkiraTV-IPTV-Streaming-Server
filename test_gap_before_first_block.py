# test_gap_before_first_block.py
"""
Test for the specific gap scenario: what happens before the first block?

The user says blocks start at 17:00, but what about 00:00-17:00?
Should that be filled by gap filler?
"""

import sys
sys.path.insert(0, '.')

from datetime import date, datetime
from akiratv.daypart_scheduler import (
    generate_daypart_schedule,
    TimeBlock,
    detect_gaps
)


def test_gap_before_first_block():
    """
    Test the specific scenario: What happens before the first block at 17:00?
    
    User's blocks: 17:00-20:00 and 20:00-24:00
    Expected gaps: 00:00-17:00 (should be filled by gap filler)
    
    The question is: Is gap filler filling 00:00-17:00?
    """
    print("=" * 60)
    print("TEST: Gap before first block (00:00-17:00)")
    print("=" * 60)
    
    test_date = date(2026, 4, 1)  # Wednesday
    
    # Config with blocks at 17:00 and 20:00
    daypart_config = {
        "daypart_config": {
            "time_blocks": [
                {
                    "block_id": "block1",
                    "start_time": "17:00",
                    "end_time": "20:00",
                    "content_type": "tag",
                    "content_value": "action",
                },
                {
                    "block_id": "block2",
                    "start_time": "20:00", 
                    "end_time": "24:00",
                    "content_type": "tag",
                    "content_value": "comedy",
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
    
    # Videos for blocks - SHORT so first block ends BEFORE 20:00
    # Block 1 (17:00-20:00): 90 min video -> ends at 18:30
    # Block 2 (20:00-24:00): 90 min video -> ends at 21:30
    available_videos = [
        {"path": "/action1.mp4", "duration": 5400, "tags": ["action"], "collection": {"id": "a"}},  # 90 min = 18:30
        {"path": "/comedy1.mp4", "duration": 5400, "tags": ["comedy"], "collection": {"id": "c"}},  # 90 min = 21:30
    ]
    
    entries, last_time = generate_daypart_schedule(
        daypart_config,
        available_videos,
        "test_channel",
        test_date
    )
    
    print(f"\nFull schedule for {test_date}:")
    for entry in entries:
        print(f"  {entry['time']} [{entry['source']}] {entry.get('file', '')}")
    
    # Analyze: Is there a gap filler entry BEFORE 17:00?
    gap_entries = [e for e in entries if e.get('source') == 'gap_filler']
    
    print(f"\n--- Analysis ---")
    print(f"Total entries: {len(entries)}")
    print(f"Gap filler entries: {len(gap_entries)}")
    
    if gap_entries:
        print("\nGap filler entries:")
        for ge in sorted(gap_entries, key=lambda x: x['time']):
            print(f"  {ge['time']} - {ge['file']}")
        
        # Check for gap filler before 17:00
        before_17 = [e for e in gap_entries if int(e['time'].split(':')[0]) < 17]
        if before_17:
            print(f"\n*** Found {len(before_17)} gap filler entries BEFORE 17:00 ***")
            print("FIXED: Gap filler now correctly fills 00:00-17:00!")
            for e in before_17:
                print(f"  {e['time']} - {e['file']}")
            return True
        else:
            print("\n*** No gap filler entries BEFORE 17:00 ***")
            print("This might be the bug - gap filler should fill 00:00-17:00!")
            return False
    else:
        print("\n*** No gap filler entries at all! ***")
        return False


if __name__ == "__main__":
    result = test_gap_before_first_block()
    
    if result:
        print("\n*** TEST: Gap filler is filling 00:00-17:00 ***")
    else:
        print("\n*** TEST FAILED: Gap filler NOT filling 00:00-17:00 ***")
        sys.exit(1)
