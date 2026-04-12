"""
Approximate block timing utilities for daypart scheduling.

This module handles snapping scheduled blocks to avoid overlapping
with gap fill videos, ensuring continuous streaming.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .daypart_scheduler import TimeBlock, ScheduledEntry

logger = logging.getLogger("AkiraTV")


def _parse(t: str) -> datetime:
    """Local import-free time parser (delegates to daypart_scheduler)."""
    from .daypart_scheduler import parse_time_string
    return parse_time_string(t)


def _fmt(dt: datetime) -> str:
    from .daypart_scheduler import format_time_string
    return format_time_string(dt)


def _weekday_indices(day_names: list) -> list:
    from .daypart_scheduler import get_weekday_indices
    return get_weekday_indices(day_names)


# ---------------------------------------------------------------------------
# Legacy helpers (used by EditBlockDialog.try_approximate)
# ---------------------------------------------------------------------------

def approximate_block_timing(new_block_start: str, new_block_end: str,
                              existing_blocks: list,
                              gaps: List[Tuple[str, str]],
                              tag_duration_hours: float = 1.0) -> Optional[Tuple[str, str]]:
    """
    Approximate block timing to fit around existing blocks without cutting them.
    Returns (adjusted_start, adjusted_end) or None.
    """
    try:
        start_dt = _parse(new_block_start)
        end_dt = _parse(new_block_end)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        block_duration = (end_dt - start_dt).total_seconds() / 3600
    except Exception as e:
        logger.warning(f"Error parsing times {new_block_start}-{new_block_end}: {e}")
        block_duration = tag_duration_hours

    if not existing_blocks:
        return (new_block_start, new_block_end)

    existing_intervals = []
    for block in existing_blocks:
        try:
            b_start = _parse(block.start_time)
            b_end = _parse(block.end_time)
            if b_end < b_start:
                b_end += timedelta(days=1)
            existing_intervals.append((b_start, b_end, block))
        except Exception:
            continue

    if not existing_intervals:
        return (new_block_start, new_block_end)

    existing_intervals.sort(key=lambda x: x[0])
    proposed_start = _parse(new_block_start)
    proposed_end = _parse(new_block_end)
    possible_adjustments = []

    for b_start, b_end, block in existing_intervals:
        if proposed_start < b_end and proposed_end > b_start:
            adjusted_start = b_end
            adjusted_end = adjusted_start + timedelta(hours=block_duration)
            adjusted_start_str = _fmt(adjusted_start)
            adjusted_end_str = _fmt(adjusted_end)
            time_diff_seconds = abs((adjusted_start - proposed_start).total_seconds())

            fits_in_gap = False
            for gap_start, gap_end in gaps:
                gs = _parse(gap_start)
                ge = _parse(gap_end)
                if ge < gs:
                    ge += timedelta(days=1)
                if adjusted_start >= gs and adjusted_end <= ge:
                    fits_in_gap = True
                    break

            fits_between = False
            idx = existing_intervals.index((b_start, b_end, block))
            if idx + 1 < len(existing_intervals):
                next_start, _, _ = existing_intervals[idx + 1]
                if adjusted_end <= next_start:
                    fits_between = True
            else:
                if adjusted_end.hour <= 24 and adjusted_end.minute == 0:
                    fits_between = True

            if fits_in_gap or fits_between:
                possible_adjustments.append((adjusted_start_str, adjusted_end_str, time_diff_seconds))

    if possible_adjustments:
        possible_adjustments.sort(key=lambda x: x[2])
        return (possible_adjustments[0][0], possible_adjustments[0][1])

    return (new_block_start, new_block_end)


def approximate_block_timing_v2(new_block_start: str, new_block_end: str,
                                 existing_entries: list,
                                 gaps: List[Tuple[str, str]],
                                 tag_duration_hours: float = 1.0) -> Optional[Tuple[str, str]]:
    """
    Approximate block timing considering both blocks and gap filler videos.
    Returns (adjusted_start, adjusted_end) or None.
    """
    try:
        start_dt = _parse(new_block_start)
        end_dt = _parse(new_block_end)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        block_duration = (end_dt - start_dt).total_seconds() / 3600
    except Exception as e:
        logger.warning(f"Error parsing times {new_block_start}-{new_block_end}: {e}")
        block_duration = tag_duration_hours

    if not existing_entries:
        return (new_block_start, new_block_end)

    existing_intervals = []
    for entry in existing_entries:
        try:
            e_start = _parse(entry.start_time)
            e_end = _parse(entry.end_time)
            if e_end < e_start:
                e_end += timedelta(days=1)
            existing_intervals.append((e_start, e_end, entry))
        except Exception:
            continue

    if not existing_intervals:
        return (new_block_start, new_block_end)

    existing_intervals.sort(key=lambda x: x[0])
    proposed_start = _parse(new_block_start)
    proposed_end = _parse(new_block_end)
    possible_adjustments = []

    for e_start, e_end, entry in existing_intervals:
        if proposed_start < e_end and proposed_end > e_start:
            adjusted_start = e_end
            adjusted_end = adjusted_start + timedelta(hours=block_duration)
            adjusted_start_str = _fmt(adjusted_start)
            adjusted_end_str = _fmt(adjusted_end)
            time_diff_seconds = abs((adjusted_start - proposed_start).total_seconds())

            fits_in_gap = False
            for gap_start, gap_end in gaps:
                gs = _parse(gap_start)
                ge = _parse(gap_end)
                if ge < gs:
                    ge += timedelta(days=1)
                if adjusted_start >= gs and adjusted_end <= ge:
                    fits_in_gap = True
                    break

            fits_between = False
            idx = existing_intervals.index((e_start, e_end, entry))
            if idx + 1 < len(existing_intervals):
                next_start, _, _ = existing_intervals[idx + 1]
                if adjusted_end <= next_start:
                    fits_between = True
            else:
                if adjusted_end.hour <= 24 and adjusted_end.minute == 0:
                    fits_between = True

            if fits_in_gap or fits_between:
                possible_adjustments.append((adjusted_start_str, adjusted_end_str, time_diff_seconds))

    if possible_adjustments:
        possible_adjustments.sort(key=lambda x: x[2])
        return (possible_adjustments[0][0], possible_adjustments[0][1])

    return (new_block_start, new_block_end)


# ---------------------------------------------------------------------------
# Runtime snapping (used by generate_daypart_schedule)
# ---------------------------------------------------------------------------

def apply_approximate_snapping(schedule_entries: List[dict], time_blocks: List[dict],
                                weekday: int, target_date, channel: str) -> bool:
    """
    For blocks marked approximate=True, snap their start time to avoid overlapping
    with gap fill videos.

    Rule: find the earliest point at or after the block's scheduled start where no
    other entry is playing. Iterates until the position is clear of all overlaps.

    Returns True if any snapping was done.
    """
    from .daypart_scheduler import TimeBlock, parse_time_string, get_weekday_indices

    snapped = False
    for block_data in time_blocks:
        block = TimeBlock.from_dict(block_data)
        if not getattr(block, 'approximate', False):
            continue

        block_days = block.days if hasattr(block, 'days') and block.days else []
        if not block_days and block.content_type in ("tag", "episodic"):
            parts = block.content_value.split("|")
            if len(parts) >= 2:
                block_days = [d.strip() for d in parts[1].split(",") if d.strip()]
        applies = (not block_days) or (weekday in get_weekday_indices(block_days))
        if not applies:
            continue

        scheduled_start = datetime.combine(target_date, parse_time_string(block.start_time).time())

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

        # Walk forward from scheduled_start until we find a clear position
        snap_to = scheduled_start
        changed = True
        while changed:
            changed = False
            for e_start, e_end in other_entries:
                if e_start < snap_to < e_end:
                    # snap_to is inside this entry — push past it
                    snap_to = e_end
                    changed = True
                    break

        if snap_to == scheduled_start:
            continue  # No overlap, no shift needed

        shift = snap_to - scheduled_start
        block_entries = [e for e in schedule_entries if e.get("daypart_block_id") == block.block_id]
        for entry in block_entries:
            orig = datetime.combine(target_date, datetime.strptime(entry["time"], "%H:%M:%S").time())
            entry["time"] = (orig + shift).strftime("%H:%M:%S")

        logger.info(f"[{channel}] Approximate: shifted block {block.block_id} "
                    f"by {shift.total_seconds()/60:.1f} min → starts at {snap_to.strftime('%H:%M')}")
        snapped = True

    return snapped
