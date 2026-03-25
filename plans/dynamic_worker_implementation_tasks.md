# Dynamic Worker Implementation Tasks

## Overview
This document outlines the tasks required to fix critical bugs and improve the DynamicWorker for production use. The DynamicWorker is a hybrid worker that combines scheduled programming, VOD interruptions, and standby mode.

---

## Critical Fixes (Must Fix Before Testing)

### 1. Fix Command Queue Race Condition
**Priority:** Critical
**File:** `akiratv/workers/dynamic_worker.py` lines 60-68

**Problem:** The check-then-get pattern is not atomic and can miss commands.

**Current code:**
```python
if not self.command_queue.empty():
    try:
        cmd, video_path, start_position = self.command_queue.get_nowait()
        if cmd == "play_now":
            self._switch_to_vod(video_path, start_position)
            continue
    except:
        pass
```

**Fix:**
```python
try:
    cmd, video_path, start_position = self.command_queue.get_nowait()
    if cmd == "play_now":
        self.logger.info(f"[HOT] VOD interruption: {video_path} (start: {start_position}s)")
        self._switch_to_vod(video_path, start_position)
        continue
except queue.Empty:
    pass
```

**Also:** Add `import queue` at the top of the file.

---

### 2. Initialize `is_in_standby` Attribute
**Priority:** Critical
**File:** `akiratv/workers/dynamic_worker.py` `__init__` method

**Problem:** Attribute is referenced (lines 80, 105, 115, 145) but never initialized, causing `AttributeError` if checked before first standby.

**Fix:** Add in `__init__`:
```python
self.is_in_standby = False
```

---

### 3. Remove Dead Code
**Priority:** High
**File:** `akiratv/workers/dynamic_worker.py`

**Problem:** Two methods are defined but never called:
- `_monitor_and_handle_commands()` (lines 325-352)
- `_manage_schedule_or_standby()` (lines 133-147)

**Fix:** Remove these methods to reduce code complexity and confusion.

---

### 4. Fix Error Thread Leak on Rapid VOD Switches
**Priority:** High
**File:** `akiratv/workers/dynamic_worker.py` `_stop_current_ffmpeg()` method

**Problem:** The error thread is joined with a 2-second timeout. If it doesn't finish, the thread is abandoned but may still be reading stderr, leading to resource leaks during rapid VOD switches.

**Current code (lines 439-448):**
```python
if self.error_thread and self.error_thread.is_alive():
    try:
        if self.ffmpeg_process and self.ffmpeg_process.stderr:
            self.ffmpeg_process.stderr.close()
        self.error_thread.join(timeout=2)
    except Exception as e:
        self.logger.warning(f"Error cleaning up error thread: {e}")
    finally:
        self.error_thread = None
```

**Fix:** Increase timeout to 5 seconds and ensure stderr is closed before joining:
```python
if self.error_thread and self.error_thread.is_alive():
    try:
        if self.ffmpeg_process and self.ffmpeg_process.stderr:
            self.ffmpeg_process.stderr.close()
        self.error_thread.join(timeout=5)
    except Exception as e:
        self.logger.warning(f"Error cleaning up error thread: {e}")
    finally:
        self.error_thread = None
```

---

### 5. CRITICAL BUG: HLS Segments Not Being Deleted
**Priority:** Critical
**File:** `akiratv/workers/dynamic_worker.py` FFmpeg HLS output arguments

**Problem (Reported by user testing):** After playing multiple videos, HLS segments accumulate instead of being deleted. The HLS playlist shows `#EXT-X-DISCONTINUITY` and contains many old segments (e.g., 35 segments created). The `-hls_flags` includes `delete_segments`, but segments are not being removed from the output directory.

**Current code (lines 200-206 in `_play_scheduled_content()` and similar in `_switch_to_vod()` and `_start_standby()`):**
```python
args.extend([
    *encoding_args,
    "-avoid_negative_ts", "make_zero",
    "-metadata", f"title={self.channel}",
    "-f", "hls",
    "-hls_time", str(hls_conf["segment_time"]),
    "-hls_list_size", str(hls_conf["playlist_size"]),
    "-hls_flags", "delete_segments+append_list+omit_endlist",
    "-hls_segment_filename", str(Path(playlist_filename).parent / "seg_%04d.ts"),
    playlist_filename
])
```

**Analysis:** The `delete_segments` flag tells FFmpeg to delete old segments **as it writes new ones**, based on `-hls_list_size`. However, there are two issues:

1. **Multiple FFmpeg processes overwrite the same HLS directory** without cleaning up old segments from previous runs. Each new FFmpeg instance starts fresh and doesn't delete segments left by the previous instance.
2. The `delete_segments` flag only deletes segments **during a single FFmpeg session** as the playlist rolls over. When FFmpeg exits, it doesn't clean up all old segments.

**Scenario:**
- Video 1 plays → creates seg_0001.ts through seg_0010.ts
- Video 1 ends, FFmpeg exits
- Video 2 starts → NEW FFmpeg process, creates seg_0011.ts, etc.
- Old segments (seg_0001-0010) remain forever

**Fix Strategy:** Before starting a new FFmpeg process, clean up the HLS directory:

```python
def _cleanup_hls_directory(self):
    """Clean up old HLS segments before starting new playback."""
    hls_path = self.config.get_hls_output_path(self.channel)
    if hls_path.exists():
        for f in hls_path.glob("seg_*.ts"):
            try:
                f.unlink()
                self.logger.debug(f"Deleted old segment: {f.name}")
            except Exception as e:
                self.logger.warning(f"Failed to delete old segment {f.name}: {e}")
        # Also delete old playlist
        playlist = hls_path / "index.m3u8"
        if playlist.exists():
            try:
                playlist.unlink()
            except Exception as e:
                self.logger.warning(f"Failed to delete old playlist: {e}")
```

**Call this cleanup** at the start of:
- `_play_scheduled_content()` (before starting FFmpeg)
- `_switch_to_vod()` (before starting FFmpeg)
- `_start_standby()` (before starting FFmpeg)

**Alternative:** Could also be done in `_stop_current_ffmpeg()` after terminating the process.

**Also verify:** The `hls_list_size` config is set appropriately (e.g., 10) so FFmpeg keeps only the last N segments during playback.

---

## Important Improvements

### 6. Standardize FFmpeg Execution Model
**Priority:** High
**File:** `akiratv/workers/dynamic_worker.py`

**Problem:** Three different execution patterns:
- Scheduled content: `_execute_ffmpeg()` (blocking, from BaseWorker)
- Standby: `_start_ffmpeg_nonblocking()` (non-blocking)
- VOD: `_execute_ffmpeg()` (blocking)

This inconsistency complicates error handling and thread management.

**Options:**
- **Option A:** Use `_execute_ffmpeg()` everywhere (simpler, but standby would need to be non-blocking to allow interruptions)
- **Option B:** Use `_start_ffmpeg_nonblocking()` everywhere and manage blocking behavior in the caller

**Recommendation:** Keep current design (it works) but document the rationale clearly.

---

### 7. Add Input Validation for Schedule Entries
**Priority:** Medium
**File:** `akiratv/workers/dynamic_worker.py` `_play_scheduled_content()` and `_get_current_schedule_entry()`

**Problem:** No validation that entries contain required keys (`'file'`, `'time'`).

**Fix:** Add validation in `_validate_prerequisites()` or at the start of `_play_scheduled_content()`:
```python
required_keys = ['file', 'time']
for entry in self.schedule_entries:
    missing = [k for k in required_keys if k not in entry]
    if missing:
        raise ValueError(f"Schedule entry missing required keys: {missing}")
```

---

### 8. Refresh Target Resolution on Schedule Update
**Priority:** Medium
**File:** `akiratv/workers/dynamic_worker.py` `_refresh_schedule()` method

**Problem:** `self.target_resolution` is set once in `__init__` (line 29) from channel config. If channel config changes at runtime, the resolution won't update, causing standby file mismatch.

**Fix:** Either:
- Refresh `self.target_resolution` in `_refresh_schedule()`
- Or make it a property that reads from config each time

---

### 9. Improve Standby File Selection
**Priority:** Low
**File:** `akiratv/workers/dynamic_worker.py` `_get_best_standby()` method

**Problem:** The "any standby file" fallback returns the first file from `glob()`, which is arbitrary order.

**Fix:** Sort files for deterministic selection:
```python
standby_files = sorted(standby_dir.glob("*.mp4"), key=lambda p: p.name)
```

---

## Code Quality Improvements

### 10. Replace Magic Numbers with Constants
**Priority:** Medium

**Current magic numbers:**
- `300` (schedule refresh interval, line 56)
- `5` (error sleep, line 90)
- `10` (monitor iterations, line 97)
- `0.5` (monitor sleep, line 119)
- `2` (restart delay, line 351)
- `3` (terminate timeout, line 453)

**Fix:** Define at module level:
```python
SCHEDULE_REFRESH_INTERVAL = 300  # seconds
ERROR_RETRY_DELAY = 5  # seconds
STANDBY_MONITOR_ITERATIONS = 10
MONITOR_SLEEP_INTERVAL = 0.5  # seconds
FFMPEG_RESTART_DELAY = 2  # seconds
FFMPEG_TERMINATE_TIMEOUT = 3  # seconds
```

---

### 11. Standardize Logging Format
**Priority:** Low
**File:** `akiratv/workers/dynamic_worker.py`

**Problem:** Mixed logging styles with prefixes like `[HOT]`, `[TV]`, `[OK]`, `[STANDBY]`, `[CONFIG]`, `[PLAY]`.

**Options:**
- Keep as-is (human-readable)
- Use structured logging: `self.logger.info("Playing VOD", extra={"type": "vod", "file": video_path.name})`

**Recommendation:** Keep current style for debugging, but document log format.

---

### 12. Add Missing Import
**Priority:** Critical (for queue fix)
**File:** `akiratv/workers/dynamic_worker.py`

**Fix:** Add at top:
```python
import queue
```

---

## Testing Tasks

### 13. Unit Tests Needed
- Command queue race condition handling
- Schedule entry validation with malformed data
- Standby file fallback chain with missing files
- Seek time calculation at boundaries
- `_stop_current_ffmpeg` with multiple error threads
- VOD interruption during standby, scheduled playback, and another VOD
- Schedule refresh while playing
- FFmpeg failure recovery

---

## Configuration Tasks

### 14. Document Channel Configuration
Create documentation for channel config options:

```json
{
  "channels": {
    "dynamic_channel": {
      "type": "dynamic",
      "transcoding": {
        "enabled": true/false,
        "video_quality": "1920x1080",
        "bitrate": "2500k"
      },
      "enable_subtitles": true/false,
      "output_specs": {
        "width": 1920,
        "height": 1080
      }
    }
  }
}
```

---

## Integration Tasks

### 15. Implement Now Playing / Next Video Overlay in Kodi
**Priority:** Low (Feature)
**Related:** Player-side display to show now playing and upcoming video information without transcoding.

**Problem:** Want to display "Now Playing: [video title]" and "Next: [video title]" as an on-screen overlay in Kodi. Since `-c copy` mode is used for performance, text cannot be burned into the video stream.

**Solution:** Use player-side overlay approach:
1. Enable `app_context.set_now_playing()` calls in DynamicWorker to publish now/next info to the API
2. Create/update Kodi addon to fetch this data from AkiraTV API (WebSocket or HTTP endpoint)
3. Render overlay in Kodi UI using the addon

**Implementation Steps:**

1. **Enable now/next tracking in DynamicWorker:**
   - Uncomment `app_context.set_now_playing()` calls in:
     - `_play_scheduled_content()` (line 240-243)
     - `_switch_to_vod()` (line 395-396)
   - Also consider adding "next video" updates when schedule changes

2. **Ensure API exposes now/next data:**
   - Verify `app_context.set_now_playing()` updates a global state
   - Add endpoint or WebSocket to broadcast this state to clients
   - May need to add `next_program` field (see `BaseWorker.update_now_next()`)

3. **Modify Kodi addon:**
   - Add overlay UI element (e.g., using Kodi's `ControlLabel` or similar)
   - Poll or subscribe to AkiraTV API for now/next updates
   - Display overlay with semi-transparent background, auto-hide after few seconds

4. **Testing:**
   - Verify now playing updates correctly during scheduled playback
   - Verify next video info updates when schedule changes
   - Test overlay appearance and timing in Kodi

**Alternative:** If player-side overlay is not feasible, consider enabling transcoding with `drawtext` filter for burned-in text (requires significant CPU).

---

## Performance Tasks

### 16. Add Backpressure to Main Loop (renumbered from 15)
**Priority:** Low

**Problem:** Main loop spins when in standby with no schedule changes, causing unnecessary CPU usage.

**Fix:** Add longer sleep when in standby and no commands pending:
```python
if self.is_in_standby and self.command_queue.empty():
    time.sleep(1)  # Longer sleep when idle
```

---

## Summary

**Total Tasks:** 16
**Critical (block testing):** 5 (tasks 1, 2, 3, 4, 12)
**High priority:** 3 (tasks 6, 7, 8)
**Medium priority:** 4 (tasks 9, 10, 11, 16)
**Low priority:** 4 (tasks 13, 14, 15)

**Estimated effort:** 4-8 hours for critical + high priority fixes.

---

## Implementation Order

1. **Phase 1 (Critical):** Tasks 1, 2, 3, 4, 12 - Make the worker run without crashes
2. **Phase 2 (Important):** Tasks 6, 7, 8 - Fix resource leaks and add validation
3. **Phase 3 (Polish):** Tasks 9, 10, 16 - Code quality and performance
4. **Phase 4 (Documentation):** Task 14 - Document configuration
5. **Phase 5 (Testing):** Tasks 13, 15 - Add unit tests and integration features

---

## Notes

- The DynamicWorker is already designed to use `-c copy` for scheduled content (line 184), which meets the requirement of no transcoding.
- However, using `-c copy` with videos of different parameters may cause HLS player buffering. Test with Kodi to verify compatibility.
- If buffering occurs, enable transcoding in channel config to convert all videos to a common format.

## User Testing Findings

**Date:** 2023-10-23 (user report)
**Test Setup:** 1-minute videos with different resolutions, H.265 codec
**Players:** SMPlayer, Kodi TV (Tanix box)
**Result:** Videos played successfully in both players.
**Key Insight:** All videos must use the same codec (H.265) and likely same audio codec for reliable playback.
**Bug Identified:** HLS segments are not being deleted between videos. After multiple videos, 35+ segments accumulated. Playlist shows `#EXT-X-DISCONTINUITY` and correct segment list, but old segments remain on disk.
**Status:** Task 5 added to fix segment deletion.

**Regression (2023-10-25):** After implementing Task 5 (delete all files in HLS directory), videos stopped after the first video. Kodi player would error when the playlist file (`index.m3u8`) was deleted during cleanup, causing playback to halt even though the worker continued.

**Fix Applied:** Modified `_cleanup_hls_directory()` to only delete segment files (`seg_*.ts`) and preserve the playlist. This prevents segment accumulation while keeping the playlist always present, avoiding player 404 errors.

**Commit:** bd8ad64 - "Fix HLS segment cleanup: only delete seg_*.ts, preserve playlist"

---

## Notes

- The DynamicWorker is already designed to use `-c copy` for scheduled content (line 184), which meets the requirement of no transcoding.
- However, using `-c copy` with videos of different parameters may cause HLS player buffering. Test with Kodi to verify compatibility.
- If buffering occurs, enable transcoding in channel config to convert all videos to a common format.
