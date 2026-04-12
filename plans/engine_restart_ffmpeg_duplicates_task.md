# Engine Restart - FFmpeg Duplicate Workers Bug

**Created:** 2026-04-11
**Status:** Pending

## Problem

When using the "Restart" button from the web interface (Control Panel) to restart all channels globally, duplicate FFmpeg processes are created. The old FFmpeg workers are not properly terminated before starting new ones.

### Symptoms

- After clicking "Restart" button, multiple FFmpeg processes appear for the same channel
- Stream duplication / conflicts occur
- Old streams don't stop properly

## Root Cause Analysis

### Current Flow

1. **User clicks Restart** → calls `/api/restart` (POST)
2. **`core_api.restart()`** is called (line 143 in `core_api.py`):
   - Calls `self.stop()` first
   - Then calls `self.start()`

3. **`core_api.stop()`** (line 116):
   - Sets `self._engine.stop()` 
   - Joins `self._engine_thread` with timeout 10s

4. **`engine.stop()`** (`core.py` line 324):
   - Sets `self.running = False`
   - Iterates `self.workers.items()` and calls `worker.stop()` for each
   - Joins each thread with timeout 5s

5. **`worker.stop()`** (`base_worker.py` line 67):
   - Sets `self.running = False`
   - Calls `self.ffmpeg_process.terminate()` with 5s timeout
   - If timeout, calls `self.ffmpeg_process.kill()`

### The Bug

The issue is in the **timing and cleanup**:

1. **Thread join timeout is too short**: 5 seconds may not be enough for FFmpeg to gracefully terminate, especially if it's in the middle of writing a segment or buffering.

2. **Worker may not check `running` flag during blocking operations**: For example:
   - `DynamicWorker._play_scheduled_content()` blocks until video finishes
   - Setting `running = False` doesn't immediately stop it

3. **No guarantee FFmpeg is killed**: If 5-second timeout expires, FFmpeg might still be running (or in a zombie state)

4. **Race condition**: The restart happens, new workers start, but old FFmpeg processes might still be running and serving the same channel.

## Code Locations

| File | Line | Issue |
|------|------|-------|
| `core_api.py` | 116-141 | `stop()` - only 10s timeout for engine thread |
| `core.py` | 335-341 | `stop()` - 5s timeout per worker thread |
| `base_worker.py` | 76-86 | `stop()` - 5s timeout for FFmpeg termination |
| `dynamic_worker.py` | 75-112 | Main loop may not check `running` flag during video playback |

## Potential Fixes

### Option 1: Increase Timeouts (Quick Fix)

Increase timeouts in multiple places:
- FFmpeg terminate timeout: 5s → 10s
- Thread join timeout: 5s → 15s
- Engine thread join: 10s → 20s

### Option 2: Add Process Kill (More Reliable)

Before starting new workers, explicitly kill any remaining FFmpeg processes by channel name:

```python
# In core.py before starting channels
import os
import signal

# Find and kill any orphaned FFmpeg processes for this channel
def kill_orphaned_ffmpeg(channel_name):
    # Use pgrep/pkill or iterate /proc to find FFmpeg processes
    # that might be orphaned from previous run
    pass
```

### Option 3: Add Grace Period + Verification

Add a delay between stop and start, with verification that all processes are terminated:

```python
def restart(self):
    stop_result = self.stop()
    if not stop_result["success"]:
        return stop_result
    
    # Wait for all processes to actually terminate
    time.sleep(3)
    
    # Verify no FFmpeg processes running for our channels
    # If still running, force kill
    
    time.sleep(2)  # Cool-down period
    
    return self.start()
```

### Option 4: Use PID Tracking (Best Solution)

Track PIDs of spawned FFmpeg processes and ensure they're cleaned up:

- Store FFmpeg PID in worker instance
- On restart, verify PID is dead before starting new
- Use `os.kill(pid, 0)` to check if process exists

## Recommendation

Implement **Option 3** (Grace Period + Verification) as a balance between quick fix and proper solution. For a more robust solution, implement **Option 4** (PID Tracking).

## Test Scenario

1. Start AkiraTV with multiple channels (linear, dynamic, vod)
2. Let channels run for a few minutes
3. Click "Restart" from web UI
4. Check:
   - No duplicate FFmpeg processes for any channel
   - No stream conflicts
   - All channels restart and play correctly

## Related Issues

- `plans/dynamic_worker_update_schedule_task.md` - Related to DynamicWorker restart issues
- The "doesn't support in-place update" warning in schedule reload is a related symptom of restart issues
