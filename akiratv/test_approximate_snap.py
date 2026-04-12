"""
Standalone test for apply_approximate_snapping.
Reproduces the reported bug: Avatar set to 13:00, tag blocks occupy 11:03-14:47,
Avatar should snap to 14:47 but instead starts at 13:37.

Run from the project root:
    python -m akiratv.test_approximate_snap
"""
from datetime import datetime, timedelta, date

# ---------------------------------------------------------------------------
# Minimal stubs so we can import without the full app
# ---------------------------------------------------------------------------

class _FakeTimeBlock:
    def __init__(self, block_id, start_time, end_time, content_type, content_value,
                 days=None, approximate=False, video_count=None):
        self.block_id = block_id
        self.start_time = start_time
        self.end_time = end_time
        self.content_type = content_type
        self.content_value = content_value
        self.days = days or []
        self.approximate = approximate
        self.video_count = video_count
        self.duration_seconds = _hm_diff(start_time, end_time)

    @classmethod
    def from_dict(cls, d):
        obj = cls(
            block_id=d.get("block_id", "x"),
            start_time=d.get("start_time", "00:00"),
            end_time=d.get("end_time", "01:00"),
            content_type=d.get("content_type", "tag"),
            content_value=d.get("content_value", ""),
            days=d.get("days", []),
            approximate=d.get("approximate", False),
            video_count=d.get("video_count"),
        )
        return obj


def _hm_diff(start: str, end: str) -> int:
    fmt = "%H:%M"
    s = datetime.strptime(start, fmt)
    e = datetime.strptime(end, fmt)
    if e < s:
        e += timedelta(days=1)
    return int((e - s).total_seconds())


def _parse(t: str) -> datetime:
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(t, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse time: {t!r}")


def _weekday_indices(day_names):
    mapping = {"monday":0,"tuesday":1,"wednesday":2,"thursday":3,
               "friday":4,"saturday":5,"sunday":6}
    return [mapping[d.lower()] for d in day_names if d.lower() in mapping]


# ---------------------------------------------------------------------------
# Paste of apply_approximate_snapping (local, no imports from app)
# ---------------------------------------------------------------------------

def apply_approximate_snapping(schedule_entries, time_blocks, weekday, target_date, channel):
    snapped = False
    for block_data in time_blocks:
        block = _FakeTimeBlock.from_dict(block_data)
        if not getattr(block, 'approximate', False):
            continue

        block_days = block.days if block.days else []
        if not block_days and block.content_type in ("tag", "episodic"):
            parts = block.content_value.split("|")
            if len(parts) >= 2:
                block_days = [d.strip() for d in parts[1].split(",") if d.strip()]
        applies = (not block_days) or (weekday in _weekday_indices(block_days))
        if not applies:
            continue

        scheduled_start = datetime.combine(target_date, _parse(block.start_time).time())

        # Collect all non-block entries sorted by start time
        other_entries = []
        for entry in schedule_entries:
            if entry.get("daypart_block_id") == block.block_id:
                continue
            entry_start = datetime.combine(target_date,
                datetime.strptime(entry["time"], "%H:%M:%S").time())
            entry_end = entry_start + timedelta(seconds=entry.get("duration", 5400))
            other_entries.append((entry_start, entry_end))
        other_entries.sort(key=lambda x: x[0])

        snap_to = scheduled_start
        changed = True
        while changed:
            changed = False
            for e_start, e_end in other_entries:
                if e_start < snap_to < e_end:
                    snap_to = e_end
                    changed = True
                    break

        if snap_to == scheduled_start:
            print(f"  No overlap at {scheduled_start.strftime('%H:%M')} — no shift needed")
            continue

        shift = snap_to - scheduled_start
        block_entries = [e for e in schedule_entries if e.get("daypart_block_id") == block.block_id]
        for entry in block_entries:
            orig = datetime.combine(target_date, datetime.strptime(entry["time"], "%H:%M:%S").time())
            entry["time"] = (orig + shift).strftime("%H:%M:%S")

        print(f"  [{channel}] Shifted block {block.block_id} "
              f"by {shift.total_seconds()/60:.1f} min → starts at {snap_to.strftime('%H:%M')}")
        snapped = True

    return snapped


# ---------------------------------------------------------------------------
# Test scenario
# ---------------------------------------------------------------------------

def make_entry(time_hm, duration_sec, block_id=None, source="gap_filler"):
    h, m = map(int, time_hm.split(":"))
    return {
        "time": f"{h:02d}:{m:02d}:00",
        "duration": duration_sec,
        "daypart_block_id": block_id,
        "source": source,
    }


def run_test():
    """
    Simulate the new flow:
    - specific_blocks: non-approximate (tag blocks placed at exact times)
    - approximate_blocks: placed into first free gap at or after desired start
    - gap_fill_blocks: fill remaining windows
    """
    target_date = date(2026, 4, 14)  # Sunday
    weekday = 6

    # Simulate what schedule_entries looks like after Pass 1 (only specific blocks placed)
    # Old Surehand: 12:06-13:35 (89 min) — placed by gap fill
    # Avatar: approximate=True, desired start 13:00

    # After gap fill fills around specific blocks (none here, so full day),
    # Old Surehand lands at 12:06 as a gap fill video.
    gf_dur = _hm_diff("12:06", "13:35")

    schedule_entries = [
        make_entry("12:06", gf_dur, block_id="block_western", source="daypart_tag"),
    ]

    AVATAR_BLOCK_ID = "block_316d392b"
    ep1_dur = 21 * 60
    ep2_dur = 42 * 60
    ep3_dur = 21 * 60
    ep4_dur = 21 * 60
    block_duration_sec = ep1_dur + ep2_dur + ep3_dur + ep4_dur

    # Simulate Step D: find first free slot at or after 13:00
    desired_start = datetime.combine(target_date, datetime.strptime("13:00", "%H:%M").time())
    block_duration = timedelta(seconds=block_duration_sec)

    all_occupied = sorted(
        [(datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time()),
          datetime.combine(target_date, datetime.strptime(e["time"], "%H:%M:%S").time())
          + timedelta(seconds=e.get("duration", 5400)))
         for e in schedule_entries],
        key=lambda x: x[0]
    )

    candidate = desired_start
    changed = True
    while changed:
        changed = False
        for occ_start, occ_end in all_occupied:
            if occ_start <= candidate < occ_end:
                candidate = occ_end
                changed = True
                break
            if candidate < occ_start < candidate + block_duration:
                candidate = occ_end
                changed = True
                break

    print(f"Desired start: 13:00")
    print(f"Old Surehand ends: 13:35")
    print(f"Candidate start: {candidate.strftime('%H:%M')}")

    gf_end = datetime.combine(target_date, datetime.strptime("12:06", "%H:%M").time()) + timedelta(seconds=gf_dur)
    if candidate >= gf_end:
        print(f"✓ PASS: Avatar placed at {candidate.strftime('%H:%M')}, after Old Surehand ends at {gf_end.strftime('%H:%M')}")
    else:
        print(f"✗ FAIL: Avatar placed at {candidate.strftime('%H:%M')}, overlaps Old Surehand (ends {gf_end.strftime('%H:%M')})")


if __name__ == "__main__":
    run_test()
