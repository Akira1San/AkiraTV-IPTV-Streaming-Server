"""
Mockup test for episodic snap algorithm.

Scenario:
- Gap fill videos fill the day randomly (each ~90min)
- One episodic block configured at 13:00
- Episodic should start right after the gap fill video that ends
  closest to 13:00 (either the one playing AT 13:00 ends, or the
  last one that ended before 13:00)

Expected result:
  - Episodic starts at the natural video boundary nearest 13:00
  - No gap fill video starts inside the episodic slot
  - Gap fill resumes right after episodic ends
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional
import random

# ── Data ────────────────────────────────────────────────────────────────────

@dataclass
class Entry:
    start: datetime
    duration: int          # seconds
    title: str
    kind: str              # "gap" | "episodic"

    @property
    def end(self) -> datetime:
        return self.start + timedelta(seconds=self.duration)

    def __repr__(self):
        return (f"{self.start.strftime('%H:%M')}-{self.end.strftime('%H:%M')} "
                f"[{self.kind}] {self.title}")


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_gap_fill(day: datetime, titles: List[str], durations: List[int]) -> List[Entry]:
    """Fill the full day with random gap fill videos."""
    entries = []
    cur = day.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = day.replace(hour=23, minute=59, second=0, microsecond=0)
    pool = list(zip(titles, durations))
    random.shuffle(pool)
    idx = 0
    while cur < end_of_day:
        title, dur = pool[idx % len(pool)]
        entries.append(Entry(cur, dur, title, "gap"))
        cur += timedelta(seconds=dur)
        idx += 1
    return entries


def make_episodic(ep_configured: datetime, episodes: List[tuple]) -> List[Entry]:
    """Create episodic entries starting at ep_configured."""
    entries = []
    cur = ep_configured
    for title, dur in episodes:
        entries.append(Entry(cur, dur, title, "episodic"))
        cur += timedelta(seconds=dur)
    return entries


# ── Snap algorithm ───────────────────────────────────────────────────────────

def snap_episodic(gap_entries: List[Entry],
                  ep_entries: List[Entry],
                  ep_configured: datetime,
                  max_snap_back: timedelta = timedelta(minutes=90)) -> List[Entry]:
    """
    Snap episodic block to the nearest gap fill video boundary.

    Rules:
    1. If a gap fill video is playing AT ep_configured (started before,
       ends after), snap episodic to start right after that video ends.
    2. Otherwise snap to the latest gap fill video end that is <= ep_configured.
    3. Remove any gap fill entry that STARTS inside the episodic slot.
    4. Re-fill the gaps around the snapped episodic.
    """
    ep_first = ep_entries[0].start
    ep_last_end = ep_entries[-1].end

    # Step 1: find snap point
    playing_at_configured: Optional[datetime] = None
    best_end_before: Optional[datetime] = None

    for e in gap_entries:
        if e.start <= ep_configured and e.end > ep_configured:
            # Playing at configured time — use its end
            if e.end <= ep_configured + max_snap_back:
                if playing_at_configured is None or e.end > playing_at_configured:
                    playing_at_configured = e.end
        elif e.end <= ep_configured:
            if best_end_before is None or e.end > best_end_before:
                best_end_before = e.end

    snap_to = playing_at_configured if playing_at_configured is not None else best_end_before

    if snap_to is None or snap_to == ep_first:
        print(f"  [snap] no snap needed, episodic stays at {ep_first.strftime('%H:%M')}")
        snap_to = ep_first
    else:
        shift = snap_to - ep_first
        print(f"  [snap] {ep_first.strftime('%H:%M')} → {snap_to.strftime('%H:%M')} "
              f"(shift {shift.total_seconds()/60:+.1f}min)")
        ep_entries = [
            Entry(e.start + shift, e.duration, e.title, e.kind)
            for e in ep_entries
        ]

    ep_start = ep_entries[0].start
    ep_end = ep_entries[-1].end

    # Step 2: remove gap fill entries that START inside the episodic slot
    kept_gap = [e for e in gap_entries if not (ep_start <= e.start < ep_end)]
    removed = len(gap_entries) - len(kept_gap)
    if removed:
        print(f"  [snap] removed {removed} gap fill entries inside episodic slot")

    # Step 3: re-fill gaps around episodic
    all_entries = sorted(kept_gap + ep_entries, key=lambda e: e.start)

    # Find windows that need filling
    day_start = ep_entries[0].start.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start.replace(hour=23, minute=59)
    windows = []
    cursor = day_start
    for e in all_entries:
        if cursor < e.start:
            windows.append((cursor, e.start))
        cursor = max(cursor, e.end)
    if cursor < day_end:
        windows.append((cursor, day_end))

    # Fill each window with gap fill videos (simple: pick random from pool)
    gap_pool = [(e.title, e.duration) for e in gap_entries]
    new_gap = []
    for win_start, win_end in windows:
        cur = win_start
        idx = 0
        while cur < win_end:
            title, dur = gap_pool[idx % len(gap_pool)]
            new_gap.append(Entry(cur, dur, title, "gap"))
            cur += timedelta(seconds=dur)
            idx += 1

    final = sorted(all_entries + new_gap, key=lambda e: e.start)

    # Final cleanup: remove any gap fill that starts inside episodic slot
    final = [e for e in final
             if e.kind == "episodic"
             or not (ep_start <= e.start < ep_end)]

    return final


# ── Test runner ───────────────────────────────────────────────────────────────

def run_test(seed: int):
    random.seed(seed)
    day = datetime(2026, 4, 15)
    ep_configured = day.replace(hour=13, minute=0)

    # Gap fill pool: ~90min movies
    titles = [
        "Winnetou 1", "Winnetou 2", "Winnetou 3",
        "Der Schatz Im Silbersee", "Old Surehand",
        "Die Pyramide Des Sonnengottes", "Der Schut",
        "Unter Geiern", "The Magnificent Seven",
    ]
    durations = [5400, 5700, 5460, 5820, 5340, 6000, 5580, 5760, 7670]

    gap = make_gap_fill(day, titles, durations)
    episodes = [
        ("Avatar S01E01", 1305),
        ("Avatar S01E02-E03", 2527),
        ("Avatar S01E04", 1276),
        ("Avatar S01E05", 1299),
    ]
    ep = make_episodic(ep_configured, episodes)

    print(f"\n{'='*60}")
    print(f"Seed {seed} — ep configured at {ep_configured.strftime('%H:%M')}")
    print(f"{'='*60}")

    result = snap_episodic(gap, ep, ep_configured)

    # Print schedule around the episodic block
    ep_start = next(e.start for e in result if e.kind == "episodic")
    ep_end = max(e.end for e in result if e.kind == "episodic")

    print("\nSchedule (11:00–18:00):")
    for e in result:
        if e.start.hour >= 11 and e.start.hour <= 18:
            marker = " ✓" if e.kind == "episodic" else ""
            print(f"  {e}{marker}")

    # Validate
    errors = []
    for e in result:
        if e.kind == "gap" and ep_start <= e.start < ep_end:
            errors.append(f"GAP FILL INSIDE EPISODIC: {e}")
    if errors:
        print("\n❌ ERRORS:")
        for err in errors:
            print(f"  {err}")
    else:
        print(f"\n✅ Clean — episodic {ep_start.strftime('%H:%M')}–{ep_end.strftime('%H:%M')}")


if __name__ == "__main__":
    for seed in range(10):
        run_test(seed)
