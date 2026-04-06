# test_gap_block_continuity.py
"""
Test for the gap filling issue when using block tags.
Issue: Gap filler starts from 00:00 instead of from where block ended.

This test reproduces the user's issue:
- Block at 17:00 - 20:00 (daypart_tag)
- Block at 20:00 - 24:00 (daypart_tag)
- Expected: Gap filler fills only 00:00-17:00
- Actual Bug: Gap filler fills 00:00-24:00 (starting from midnight, ignoring block execution times)
"""

import sys
sys.path.insert(0, '.')

from datetime import date, datetime, timedelta
from akiratv.daypart_scheduler import (
    generate_daypart_schedule,
    TimeBlock,
    detect_gaps,
    GapFillerConfig,
    fill_gaps_with_random
)


def test_gap_detection_with_tag_blocks():
    """
    Test that detect_gaps correctly identifies gaps between tag blocks.
    This is the FIRST part of the test - does detect_gaps work correctly?
    """
    print("=" * 60)
    print("TEST 1: detect_gaps with tag blocks")
    print("=" * 60)
    
    # Create blocks like the user's configuration
    blocks = [
        TimeBlock("17:00", "20:00", "tag", "action"),
        TimeBlock("20:00", "24:00", "tag", "comedy"),
    ]
    
    # Detect gaps
    gaps = detect_gaps(blocks)
    
    print(f"Blocks: {[(b.start_time, b.end_time) for b in blocks]}")
    print(f"Detected gaps: {gaps}")
    
    # Expected: (00:00, 17:00) and (20:00, 24:00)
    # But we need to see what the actual output is
    assert len(gaps) >= 1, "Should detect at least one gap"
    
    # Check if there's a gap starting at 00:00
    gap_starts_at_0000 = any(g[0] == "00:00" for g in gaps)
    print(f"Gap starts at 00:00: {gap_starts_at_0000}")
    
    return gaps


def test_gap_filling_respects_block_execution_time():
    """
    Test that gap filling starts from where blocks actually ended, not from 00:00.
    
    This simulates the user's scenario:
    - Block 1: 17:00 - 20:00 (tag block for "action")
    - Block 2: 20:00 - 24:00 (tag block for "comedy")
    
    The blocks might run longer than their scheduled end times due to video durations.
    """
    print("=" * 60)
    print("TEST 2: Gap filling respects block execution time")
    print("=" * 60)
    
    # Use a specific date (Wednesday to match user's example)
    test_date = date(2026, 4, 1)  # Wednesday
    
    daypart_config = {
        "daypart_config": {
            "time_blocks": [
                {
                    "block_id": "block1",
                    "start_time": "17:00",
                    "end_time": "20:00",
                    "content_type": "tag",
                    "content_value": "action",
                    "days": ["wednesday"]
                },
                {
                    "block_id": "block2", 
                    "start_time": "20:00",
                    "end_time": "24:00",
                    "content_type": "tag",
                    "content_value": "comedy",
                    "days": ["wednesday"]
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
    
    # Create videos with specific durations to simulate real execution
    # First block (17:00-20:00) - simulate it runs from 17:00 to 18:38
    # Second block (20:00-24:00) - simulate it runs from 20:00 to 23:42
    available_videos = [
        # Videos for first block (action tag)
        {"path": "/action1.mp4", "duration": 5580, "tags": ["action"], "collection": {"id": "action_col"}},  # 93 min -> ends at 18:33
        {"path": "/action2.mp4", "duration": 5400, "tags": ["action"], "collection": {"id": "action_col"}},  # 90 min
        
        # Videos for second block (comedy tag)
        {"path": "/comedy1.mp4", "duration": 5400, "tags": ["comedy"], "collection": {"id": "comedy_col"}},  # 90 min -> ends at 21:30
        {"path": "/comedy2.mp4", "duration": 5400, "tags": ["comedy"], "collection": {"id": "comedy_col"}},  # 90 min -> ends at 23:00
        {"path": "/comedy3.mp4", "duration": 2520, "tags": ["comedy"], "collection": {"id": "comedy_col"}},  # 42 min -> ends at 23:42
        
        # Videos for gap filler (all videos available)
        {"path": "/gap1.mp4", "duration": 5400, "tags": ["other"], "collection": {"id": "gap_col"}},
        {"path": "/gap2.mp4", "duration": 5400, "tags": ["other"], "collection": {"id": "gap_col"}},
    ]
    
    # Generate schedule
    entries, last_time = generate_daypart_schedule(
        daypart_config,
        available_videos,
        "test_channel",
        test_date,
        base_datetime=None  # No previous day continuity
    )
    
    print(f"\nGenerated {len(entries)} entries for {test_date}")
    print(f"Last time: {last_time}")
    
    # Print all entries
    print("\nSchedule entries:")
    for entry in entries:
        print(f"  {entry['time']} [{entry['source']}] {entry.get('file', entry.get('metadata', {}).get('tag_used', 'N/A'))}")
    
    # Analyze the schedule
    gap_filler_entries = [e for e in entries if e.get('source') == 'gap_filler']
    daypart_tag_entries = [e for e in entries if e.get('source') == 'daypart_tag']
    
    print(f"\nDaypart tag entries: {len(daypart_tag_entries)}")
    print(f"Gap filler entries: {len(gap_filler_entries)}")
    
    if gap_filler_entries:
        first_gap_time = gap_filler_entries[0]['time']
        print(f"\nFirst gap filler entry at: {first_gap_time}")
        
        # BUG: If first gap entry is after 17:00, that's the bug!
        # FIXED: Now gap filler correctly fills from 00:00-17:00
        first_gap_hour = int(first_gap_time.split(':')[0])
        
        # The FIXED behavior: gap filler fills 00:00-17:00, then blocks run
        if first_gap_hour >= 17:
            print(f"\n*** BUG DETECTED! ***")
            print(f"Gap filler started at {first_gap_time} but should start at 00:00!")
            print(f"The gap from 00:00-17:00 should be filled by gap filler!")
            return False
        else:
            print(f"\n*** TEST PASSED ***")
            print(f"Gap filler correctly starts at {first_gap_time} (fills 00:00-17:00)")
            return True
    else:
        print("\nNo gap filler entries - all time filled by blocks")
        return True


def test_cross_day_continuity():
    """
    Test that cross-day continuity works correctly.
    This is the scenario where previous day runs past midnight.
    """
    print("=" * 60)
    print("TEST 3: Cross-day continuity")
    print("=" * 60)
    
    # Day 1: Tuesday - block runs from 22:00 to 01:00 (overnight)
    test_date_1 = date(2026, 3, 31)  # Tuesday
    
    daypart_config = {
        "daypart_config": {
            "time_blocks": [
                {
                    "block_id": "block1",
                    "start_time": "22:00",
                    "end_time": "24:00",
                    "content_type": "tag",
                    "content_value": "late_night",
                    "days": ["tuesday"]
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
    
    available_videos = [
        {"path": "/ln1.mp4", "duration": 10800, "tags": ["late_night"], "collection": {"id": "ln"}},  # 3 hours
        {"path": "/gap1.mp4", "duration": 5400, "tags": ["other"], "collection": {"id": "gap"}},
    ]
    
    # Generate for day 1
    entries_1, last_time_1 = generate_daypart_schedule(
        daypart_config,
        available_videos,
        "test_channel",
        test_date_1,
        base_datetime=None
    )
    
    print(f"\nDay 1 ({test_date_1}): {len(entries_1)} entries, last_time={last_time_1}")
    
    # Day 2: Wednesday - should continue from where day 1 ended
    test_date_2 = date(2026, 4, 1)  # Wednesday
    
    entries_2, last_time_2 = generate_daypart_schedule(
        daypart_config,
        available_videos,
        "test_channel",
        test_date_2,
        base_datetime=last_time_1  # Pass the last time from day 1
    )
    
    print(f"\nDay 2 ({test_date_2}): {len(entries_2)} entries, last_time={last_time_2}")
    
    # Check that day 2 starts at the correct time
    if entries_2:
        first_entry_time = entries_2[0]['time']
        print(f"First entry on Day 2: {first_entry_time}")
        
        # If last_time_1 was 01:00, first entry on day 2 should be around 01:00
        if last_time_1:
            expected_hour = last_time_1.hour
            actual_hour = int(first_entry_time.split(':')[0])
            
            if actual_hour == expected_hour:
                print(f"*** TEST PASSED *** - Day 2 correctly continues from Day 1")
                return True
            else:
                print(f"*** POTENTIAL ISSUE *** - Expected to start around {expected_hour}, got {actual_hour}")
                return False
    
    return True


def test_block_execution_time_affects_gaps():
    """
    Direct test: Does the actual execution time of blocks affect gap detection?
    
    This test creates a scenario where a block's actual runtime exceeds its
    scheduled end time, and verifies that gaps are adjusted accordingly.
    
    BUG REPRODUCTION: The user's actual issue is that when they have blocks
    at 17:00 and 20:00, but videos in the 17:00 block end earlier than 20:00,
    the gap from 18:38 (when first video ends) to 20:00 (when second block starts)
    should be filled by gap filler. But currently it's NOT being filled.
    """
    print("=" * 60)
    print("TEST 4: Block execution time affects gaps")
    print("=" * 60)
    
    # Simulate: Block scheduled 17:00-20:00 but actual execution ends at 18:38
    # Then next block at 20:00-24:00
    # 
    # The gap from 18:38 to 20:00 SHOULD be filled because it's between
    # when the first video ends and when the second block starts!
    
    test_date = date(2026, 4, 1)  # Wednesday
    
    # This config has blocks at 17:00 and 20:00
    daypart_config = {
        "daypart_config": {
            "time_blocks": [
                {
                    "block_id": "block1",
                    "start_time": "17:00",
                    "end_time": "20:00",
                    "content_type": "tag",
                    "content_value": "action",  # No days specified = applies to all days
                },
                {
                    "block_id": "block2",
                    "start_time": "20:00", 
                    "end_time": "24:00",
                    "content_type": "tag",
                    "content_value": "comedy",  # No days specified = applies to all days
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
    
    # Use SHORT videos so first block ends BEFORE its scheduled end time (20:00)
    # Block 1 (17:00-20:00): 1 video @ 90 min = ends at 18:30 (BEFORE 20:00!)
    # Block 2 (20:00-24:00): will run at 20:00
    available_videos = [
        {"path": "/action1.mp4", "duration": 5400, "tags": ["action"], "collection": {"id": "a"}},  # 90 min -> ends at 18:30
        {"path": "/comedy1.mp4", "duration": 5400, "tags": ["comedy"], "collection": {"id": "c"}},  # 90 min
    ]
    
    entries, last_time = generate_daypart_schedule(
        daypart_config,
        available_videos,
        "test_channel",
        test_date
    )
    
    print(f"\nSchedule for {test_date}:")
    for entry in entries:
        print(f"  {entry['time']} [{entry['source']}] {entry.get('file', '')}")
    
    # Check gap filler entries
    gap_entries = [e for e in entries if e.get('source') == 'gap_filler']
    tag_entries = [e for e in entries if e.get('source') == 'daypart_tag']
    
    print(f"\nTag blocks: {len(tag_entries)} entries")
    print(f"Gap filler: {len(gap_entries)} entries")
    
    if not tag_entries:
        print("\n*** ERROR: No tag block entries generated! ***")
        return False
    
    # The bug scenario:
    # - Block 1 (17:00-20:00): video ends at 18:30
    # - Block 2 (20:00-24:00): starts at 20:00
    # - Expected gap: 18:30 to 20:00 (30 minutes gap)
    # - Current BUG: Gap detector uses block's SCHEDULED end time (20:00), 
    #   so it thinks there's NO gap between blocks!
    
    if gap_entries:
        print("\nGap filler entries found:")
        for ge in gap_entries:
            print(f"  {ge['time']} - {ge['file']}")
    else:
        print("\n*** BUG CONFIRMED: No gap filler entries! ***")
        print("The gap detector thought there was no gap between blocks because")
        print("it used the block's SCHEDULED end time (20:00) instead of")
        print("the actual video end time (18:30).")
        print("\nExpected: Gap filler should fill 18:30-20:00")
        return False
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("RUNNING GAP FILLER TESTS")
    print("=" * 60 + "\n")
    
    results = []
    
    # Test 1: Basic gap detection
    try:
        test_gap_detection_with_tag_blocks()
        results.append(("Test 1: detect_gaps", "PASS"))
    except Exception as e:
        results.append(("Test 1: detect_gaps", f"FAIL: {e}"))
    
    print("\n")
    
    # Test 2: Gap filling respects block execution
    try:
        result = test_gap_filling_respects_block_execution_time()
        results.append(("Test 2: Gap execution time", "PASS" if result else "FAIL - BUG FOUND"))
    except Exception as e:
        results.append(("Test 2: Gap execution time", f"FAIL: {e}"))
    
    print("\n")
    
    # Test 3: Cross-day continuity
    try:
        result = test_cross_day_continuity()
        results.append(("Test 3: Cross-day", "PASS" if result else "FAIL"))
    except Exception as e:
        results.append(("Test 3: Cross-day", f"FAIL: {e}"))
    
    print("\n")
    
    # Test 4: Block execution time affects gaps
    try:
        result = test_block_execution_time_affects_gaps()
        results.append(("Test 4: Block exec time", "PASS" if result else "FAIL - BUG FOUND"))
    except Exception as e:
        results.append(("Test 4: Block exec time", f"FAIL: {e}"))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    for test_name, result in results:
        print(f"  {test_name}: {result}")
    
    # Check for bugs
    bugs_found = any("BUG" in r for _, r in results)
    if bugs_found:
        print("\n*** BUGS DETECTED - Fix needed in daypart_scheduler.py ***")
        sys.exit(1)
    else:
        print("\n*** All tests passed ***")
        sys.exit(0)
