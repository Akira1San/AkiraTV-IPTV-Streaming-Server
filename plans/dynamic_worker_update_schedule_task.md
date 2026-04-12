# DynamicWorker `update_schedule` Implementation Task

**Created:** 2026-04-11
**Status:** Pending

## Problem

When schedule reload is triggered (e.g., via cron or manual reload), the system tries to update schedules in-place for all channels. For channels using `DynamicWorker` (type: `dynamic`), the reload fails because:

1. DynamicWorker does NOT have an `update_schedule()` method
2. The fallback logic in `core.py` line 389-391 sets `worker.running = False`
3. This causes the current video to play until end, then worker exits
4. No auto-restart mechanism exists for DynamicWorker (unlike LinearWorker which has `_linear_worker_with_restart`)
5. Result: Channel gets stuck/buffering and eventually stops

### Log Evidence

```
2026-04-11 15:39:11,463 [WARNING] Worker for akiratv doesn't support in-place update, will restart
2026-04-11 15:39:12,518 [ERROR] FFmpeg exited with code None for akiratv
2026-04-11 15:39:12,518 [INFO] [OK] Scheduled video finished: Casper.mp4
2026-04-11 15:39:12,518 [INFO] DynamicWorker stopped for channel: akiratv
```

(Worker stops but never restarts)

### Affected Channels

- `akiratv` - type: dynamic
- `TatkoTV` - type: dynamic

## Solution

Add `update_schedule()` method to DynamicWorker, similar to how LinearWorker implements it (line 17-21 in `linear_worker.py`).

## Implementation

### 1. Add `update_schedule()` method to DynamicWorker

**File:** `akiratv/workers/dynamic_worker.py`

**Location:** Add method after `__init__` or near `_refresh_schedule()`

```python
def update_schedule(self, new_schedule_entries: List[Dict]):
    """Update schedule entries in-place without restarting the worker."""
    old_count = len(self.schedule_entries) if self.schedule_entries else 0
    self.schedule_entries = new_schedule_entries
    self.last_schedule_check = time.time()  # Reset to prevent immediate refresh
    self.logger.info(f"Schedule updated in-place: {old_count} -> {len(new_schedule_entries)} entries")
```

### 2. Verify schedule structure compatibility

Check that the schedule entry dict structure used by DynamicWorker matches what LinearWorker uses:

- `time` - HH:MM:SS format
- `file` - video file path
- (Optional) other fields

### 3. Test the implementation

1. Start a dynamic channel with scheduled content
2. Trigger schedule reload (or wait for auto-reload)
3. Verify:
   - No "doesn't support in-place update" warning appears
   - "Schedule updated in-place" log appears
   - Channel continues playing without interruption
   - Next scheduled video plays correctly

## Related Files

- `akiratv/workers/dynamic_worker.py` - Main implementation file
- `akiratv/workers/linear_worker.py` - Reference implementation (lines 17-21)
- `akiratv/core.py` - Schedule reload logic (lines 375-398)

## Similar Reference

See `plans/linear_worker_implementation_tasks.md` for the LinearWorker implementation which already has this method.