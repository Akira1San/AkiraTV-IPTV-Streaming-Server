# Linear Worker Implementation Tasks

## Overview
This document outlines the tasks required to fix critical bugs and improve the LinearWorker for production use. The LinearWorker handles linear/scheduled channel playback using FFmpeg's concat protocol to seamlessly stitch multiple videos together.

---

## Critical Fixes (Must Fix Before Production)

### 1. Remove Spurious Attribute Assignment in `update_schedule()`
**Priority:** Critical
**File:** `akiratv/workers/linear_worker.py` line 21

**Problem:**
```python
def update_schedule(self, new_schedule_entries: List[Dict]):
    old_count = len(self.schedule_entries) if self.schedule_entries else 0
    self.schedule_entries = new_schedule_entries
    self.logger.info(f"Schedule updated in-place: {old_count} -> {len(new_schedule_entries)} entries")
    self.temp_dir: Optional[Path] = None  # Line 21 - BUG!
```

Line 21 creates a **new** `temp_dir` attribute, shadowing the one created in `_setup_phase()`. This does NOT clean up the old temp directory and causes confusion about which directory is active.

**Fix:** Remove line 21 entirely. Temp directory cleanup is handled in `_cleanup_phase()`.

---

### 2. Initialize `is_in_standby` Attribute
**Priority:** Critical
**File:** `akiratv/workers/linear_worker.py` `__init__` method

**Problem:** The attribute `is_in_standby` is referenced at line 80 but never initialized. This will cause `AttributeError` if `_start_standby()` hasn't been called yet.

**Fix:** Add in `__init__`:
```python
self.is_in_standby = False
```

**Note:** Actually, LinearWorker doesn't have standby mode - that's in DynamicWorker. Check if this attribute is used at all in LinearWorker. If not, remove references. If it's meant for future standby support, initialize it.

**Action:** Review LinearWorker code to see if `is_in_standby` is used. If not, remove line 80 check or implement standby functionality.

---

### 3. Add Input Validation for Schedule Entries
**Priority:** High
**File:** `akiratv/workers/linear_worker.py` `_build_concat_playlist()` method

**Problem:** No validation that entries contain required keys (`'file'`, `'time'`). Will raise `KeyError` if missing.

**Current code (lines 72-78):**
```python
for i, entry in enumerate(self.schedule_entries):
    if i == 0:
        file_path = self._process_first_entry(entry, temp_dir)
    else:
        file_path = Path(entry['file']).resolve().as_posix()  # KeyError if 'file' missing
    f.write(f"file '{file_path}'\n")
```

**Fix:** Add validation in `_validate_prerequisites()`:
```python
def _validate_prerequisites(self) -> bool:
    if not self.schedule_entries:
        self.logger.warning(f"No schedule entries for linear channel {self.channel}. Aborting.")
        return False

    for i, entry in enumerate(self.schedule_entries):
        if 'file' not in entry:
            self.logger.error(f"Schedule entry {i} missing 'file' key")
            return False
        if 'time' not in entry:
            self.logger.error(f"Schedule entry {i} missing 'time' key")
            return False
        if not Path(entry['file']).exists():
            self.logger.error(f"Schedule entry {i} file not found: {entry['file']}")
            return False

    if not self.initialize_worker():
        self.logger.error(f"Failed to initialize worker for {self.channel}. Aborting.")
        return False

    return True
```

---

### 4. Fix Trim Fallback to Ensure File Exists
**Priority:** High
**File:** `akiratv/workers/linear_worker.py` `_trim_video()` method

**Problem:** When trim fails, the method returns the original path, but there's no explicit check that the original file actually exists before returning.

**Current code (lines 114-124):**
```python
if trim_process.returncode != 0:
    self.logger.warning(f"Failed to trim video {video_path}, using original")
    self.logger.debug(f"Trim stderr: {stderr}")
    return Path(video_path).resolve().as_posix()  # What if original doesn't exist?
```

**Fix:** Add existence check:
```python
if trim_process.returncode != 0:
    self.logger.warning(f"Failed to trim video {video_path}, using original")
    self.logger.debug(f"Trim stderr: {stderr}")
    original_path = Path(video_path).resolve()
    if not original_path.exists():
        self.logger.error(f"Original video not found: {original_path}")
        raise FileNotFoundError(f"Video not found: {video_path}")
    return original_path.as_posix()
```

---

## Important Improvements

### 5. Use Config-Based Temp Directory
**Priority:** High
**File:** `akiratv/workers/linear_worker.py` `_create_temp_directory()` method

**Problem:** Creates temp directory in fixed `Path("temp")` location:
```python
temp_dir = Path("temp") / f"concat_{self.channel}_{int(time.time())}"
```

This is inconsistent with VODWorker which uses `config.get_output_root()`. Fixed location may not be cleaned up on crash and may fill up disk.

**Fix:** Use config-based path:
```python
temp_dir = self.config.get_output_root() / f"temp_{self.channel}_{int(time.time())}"
temp_dir.mkdir(parents=True, exist_ok=True)
```

---

### 6. Replace Hardcoded Thread Count
**Priority:** Medium
**File:** `akiratv/workers/linear_worker.py` line 176

**Problem:**
```python
"-threads", "2"
```
Hardcoded to 2 threads, which may not be optimal for all systems.

**Fix:** Make configurable or auto-detect:
```python
import os
cpu_count = os.cpu_count() or 2
threads = min(4, max(1, cpu_count - 1))  # Leave one core for system
args.extend(["-threads", str(threads)])
```

Or read from config:
```python
threads = self.config.data.get("ffmpeg", {}).get("threads", "auto")
if threads != "auto":
    args.extend(["-threads", str(threads)])
```

---

### 7. Add Missing `ffmpeg` Verbose Flag
**Priority:** Low
**File:** `akiratv/workers/linear_worker.py` `_build_ffmpeg_args()` method

**Observation:** LinearWorker uses `"-v", "verbose"` (line 173) and `"-fflags", "+genpts+igndts+discardcorrupt"` (line 175), which are good defaults for robustness. VODWorker doesn't have these. Consider adding to BaseWorker or all workers for consistency.

**Fix:** Document why these flags are needed, or move to BaseWorker if all workers should use them.

---

### 8. Fix Duration Fallback Value
**Priority:** Medium
**File:** `akiratv/workers/linear_worker.py` `_get_entry_duration()` method (lines 243-255)

**Problem:**
```python
return duration if duration > 0 else 5400.0  # 1.5 hours arbitrary
```
The fallback of 5400 seconds (1.5 hours) is arbitrary and may cause scheduling drift if ffprobe fails.

**Fix:** Make fallback configurable or use a more reasonable default (e.g., 3600 = 1 hour) and log a warning:
```python
if duration <= 0:
    self.logger.warning(f"Invalid duration for {base_path}, using fallback 3600s")
    return 3600.0
```

---

## Code Quality Improvements

### 9. Remove Silent Exception Handler
**Priority:** Medium
**File:** `akiratv/workers/linear_worker.py` (check if any bare `except:` exists)

**Note:** LinearWorker doesn't appear to have bare `except:` clauses (unlike DynamicWorker). Good! Keep it that way.

---

### 10. Replace Magic Numbers with Constants
**Priority:** Medium

**Current magic numbers:**
- `timeout=30` for trim (line 113)
- `timeout=10` for ffprobe (line 250)
- Fallback duration `5400.0` (line 252)

**Fix:** Define module-level constants:
```python
TRIM_TIMEOUT = 30  # seconds
FFPROBE_TIMEOUT = 10  # seconds
DEFAULT_VIDEO_DURATION = 3600.0  # seconds (1 hour)
```

---

### 11. Fix Concat Playlist Path Escaping
**Priority:** Low
**File:** `akiratv/workers/linear_worker.py` `_build_concat_playlist()` method

**Problem:** Paths are written directly to concat file:
```python
f.write(f"file '{file_path}'\n")
```

If `file_path` contains single quotes or special characters, this could break FFmpeg's concat parser.

**Fix:** Escape single quotes in path:
```python
escaped_path = file_path.replace("'", "\\'")
f.write(f"file '{escaped_path}'\n")
```

Or use double quotes:
```python
f.write(f'file "{file_path}"\n')
```

---

## Architecture Considerations

### 12. Consider Adding Command Queue for Interruptions
**Priority:** Low (Design Decision)

**Observation:** LinearWorker has no command queue, meaning it cannot be interrupted once playback starts. DynamicWorker and VODWorker have queues.

**Question:** Do you need hot VOD interruptions for linear channels? If yes, add command queue support similar to other workers.

**Implementation:** Would require:
- Add `command_queue` parameter to `__init__`
- Check queue in monitoring loop
- Implement `play_now()` method
- Handle interruption by stopping current FFmpeg and playing VOD, then resuming schedule

---

### 13. Add Schedule Refresh Capability
**Priority:** Low (Design Decision)

**Observation:** LinearWorker uses a static schedule passed at initialization. DynamicWorker refreshes schedule every 5 minutes from `get_current_schedule_for_channel()`.

**Question:** Do you need dynamic schedule updates? If yes, add:
- `last_schedule_check` timestamp
- `_refresh_schedule()` method similar to DynamicWorker
- Call refresh in main loop or monitoring phase

---

## Testing Tasks

### 14. Unit Tests Needed
- Schedule entry validation with malformed data
- First entry trimming with various seek times
- Concat playlist generation with special characters in paths
- Duration fallback behavior when ffprobe fails
- Temp directory cleanup on various failure scenarios
- Trim failure recovery
- Schedule update with `update_schedule()` method

---

## Summary

**Total Tasks:** 14
**Critical (blocking):** 3 (tasks 1, 2, 3)
**High priority:** 2 (tasks 4, 5)
**Medium priority:** 4 (tasks 6, 7, 8, 10)
**Low priority:** 5 (tasks 11, 12, 13, 14)

**Estimated effort:** 2-4 hours for critical + high priority fixes.

---

## Implementation Order

1. **Phase 1 (Critical):** Tasks 1, 2, 3 - Fix crashes and validation
2. **Phase 2 (Important):** Tasks 4, 5 - Ensure reliability and consistency
3. **Phase 3 (Polish):** Tasks 6, 8, 10 - Code quality
4. **Phase 4 (Optional):** Tasks 12, 13 - Feature decisions
5. **Phase 5 (Testing):** Task 14 - Add unit tests

---

## Notes

- LinearWorker uses FFmpeg concat protocol, which requires all videos to have identical codec parameters (resolution, pixel format, codec, profile, etc.). This is a fundamental limitation.
- If your videos have different parameters, consider using DynamicWorker instead, which plays each video separately (no concat) but still outputs to a single HLS stream.
- The `_trim_video()` method uses stream copy (`-c copy`) for fast seeking, which is efficient but only works if the video codec supports accurate seeking.

---

## Comparison with DynamicWorker

| Feature | LinearWorker | DynamicWorker |
|---------|--------------|---------------|
| Scheduling | Static schedule at init | Can refresh from scheduler |
| Video stitching | Concat protocol (single FFmpeg) | Sequential individual plays |
| Parameter requirement | All videos must match | Can handle different params (but HLS changes may cause player buffering) |
| Standby mode | No | Yes |
| VOD interruptions | No | Yes |
| Transcoding | Delegated to service | Copy for scheduled, configurable for VOD |
| Complexity | Simpler | More complex |

**Recommendation:** Use LinearWorker only if all videos have identical parameters. Otherwise, use DynamicWorker with appropriate transcoding settings.
