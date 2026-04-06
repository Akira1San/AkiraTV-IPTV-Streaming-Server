# Task: Fix Streaming Startup Issues - No Logs, No HLS Segments

**Created:** 2026-04-05  
**Status:** Pending Implementation  
**Priority:** Critical (Blocks all streaming functionality)  
**Assigned To:** Development Team  
**Related Files:** `akiratv/core.py`, `akiratv/server/http_server.py`, `config.json`, `user/schedules/*.json`, `user/collections/*.json`

---

## Problem Statement

After launching `launch_web.sh` and pressing "Start Streaming" from the web interface:
- No logs appear in `logs/worker.log`
- No HLS `.ts` segments are generated in the RAM directory (`/home/akira/akiratv/`)
- The stream URL `http://192.168.50.183:8081/hls/TatkoTV/index.m3u8` does not work
- No visible errors in the web UI or terminal
- Engine appears to fail silently

This indicates a critical failure in the AkiraTV engine startup sequence that prevents any worker threads from running and generating HLS content.

---

## Root Cause Analysis

### 1. Missing Log File → Import Failure
- The logger is configured in `akiratv/core.py` at module import.
- `logs/worker.log` does **not exist**, meaning `akiratv/core.py` failed to import.
- Most likely cause: **Missing or broken `aiohttp` dependency** (required by `akiratv/server/http_server.py`).
- Secondary cause: Relative log path (`logs/worker.log`) may create file in unexpected location if working directory differs.

### 2. Invalid Video Paths in Schedules
- Schedule files (e.g., `user/schedules/schedule_TatkoTV.json`) contain **Windows paths**:
  ```
  "C:/Videos/tatkotv3/..."
  ```
- Actual videos are at `/home/akira/Videos/tatkotv3/`.
- Even if logger were working, FFmpeg would fail to locate videos, producing no segments.

### 3. No Fallback Logging to stderr
- Current logging setup only writes to file; if file creation fails, all errors are silent.
- No `StreamHandler` to stderr means startup errors are invisible in terminal.

### 4. HTTP Server Port Configuration
- `config.json` sets HTTP port to `8081`.
- Must ensure port is available and binding to correct interface (`0.0.0.0` for network access).

---

## Implementation Tasks

### Task 1: Fix Logging Configuration (Core Module)

**File:** `akiratv/core.py`

**Changes:**
- Replace simple `logging.FileHandler` with a robust `setup_logging()` function.
- Use absolute path: `project_root = Path(__file__).resolve().parent.parent`.
- Create logs directory: `logs_dir = project_root / "logs"`.
- Add both `FileHandler` and `StreamHandler(sys.stderr)`.
- Wrap in try/except to fall back to stderr-only if file cannot be opened.
- Prevent duplicate handlers on reload (check existing handlers).

**Expected Result:**
- Log file always created at `<project_root>/logs/worker.log`.
- Critical errors visible in terminal stderr immediately.
- Logger initialized message appears on startup.

---

### Task 2: Verify and Repair Dependencies

**Actions:**
```bash
cd /home/akira/akira/AkiraTV_NEW
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

**Verification:**
```bash
python -c "import aiohttp; print('aiohttp OK')"
python -c "import akiratv.core; print('Core imported')"
```

- If `aiohttp` import fails, reinstall with `pip install aiohttp==3.13.5`.
- If binary dependencies (`yarl`, `multidict`) are problematic, reinstall them too.

---

### Task 3: Normalize Video Paths in Schedules and Collections

**Problem:** All schedule and collection JSON files contain Windows paths (`C:/Videos/tatkotv3/`).

**Solution:** Write a conversion script to update paths to Linux paths (`/home/akira/Videos/tatkotv3/`).

**Script Location:** `utils/fix_linux_paths.py`

**Logic:**
- For each JSON file in `user/schedules/` and `user/collections/`:
  - Load JSON.
  - Recursively find all `"file"` or `"path"` string values.
  - If starts with `C:/Videos/tatkotv3/` or `C:\Videos\tatkotv3\`, replace with `/home/akira/Videos/tatkotv3/` + tail.
  - Save file with pretty-printed JSON.

**Run:**
```bash
python utils/fix_linux_paths.py
```

**Verification:**
```bash
grep -r "C:/Videos" user/schedules/ user/collections/  # Should return no results
grep -r "/home/akira/Videos" user/schedules/ user/collections/  # Should show matches
```

**Note:** Also regenerate schedules via web wizard if available to ensure canonical format.

---

### Task 4: Ensure HTTP Server Starts Correctly

**File:** `akiratv/core.py` (`initialize_http_server` method)

**Checkpoints:**
- Output mode is `"ram_http"` or `"http_hls"` in `config.json`.
- `storage.ram_path` is set correctly (`"/home/akira/akiratv"` in config).
- `output.http.port` (8081) is free: `ss -tulpn | grep :8081`.
- `output.http.bind` is `"0.0.0.0"` to accept external connections.

**Add Logging:**
- Before starting server, log: `[HTTP] Starting server on {bind}:{port}, serving from {hls_root}`.
- After start, log: `[HTTP] Server listening on http://{bind}:{port}/hls/`.
- Catch exceptions in `initialize_http_server` and log full traceback.

---

### Task 5: Test Startup Sequence Manually

**Steps:**

1. **Stop any running servers.**  
   Kill `uvicorn` and Python processes if needed.

2. **Start fresh:**
   ```bash
   cd /home/akira/akira/AkiraTV_NEW
   ./launch_web.sh
   ```

3. **Observe terminal output:**
   - Should see "Logging initialized".
   - Should see "AkiraTV API Server started".
   - Browser opens to `http://127.0.0.1:8000`.

4. **Click "Start Streaming"** in web UI.

5. **Check terminal for logs:**
   - `AkiraTV starting...`
   - `HTTP server will serve HLS from: /home/akira/akiratv`
   - `Stream URL: http://0.0.0.0:8081/hls/`
   - `Starting Dynamic channel: TatkoTV`
   - `FFmpeg started for TatkoTV: ...`

6. **Verify log file:**
   ```bash
   tail -f logs/worker.log
   ```
   Should show live entries.

7. **Check HLS directory:**
   ```bash
   ls -la /home/akira/akiratv/TatkoTV/
   ```
   Should show `index.m3u8` and `seg_*.ts` files appearing within seconds.

8. **Test stream URL:**
   - Browser: `http://192.168.50.183:8081/hls/TatkoTV/index.m3u8` (should download playlist).
   - VLC: Open network stream with same URL.
   - Should play video without errors.

---

### Task 6: Add Health Check Endpoint

**File:** `akiratv/api_server.py` (or use existing `/health`)

- Ensure `/health` returns `{"status": "healthy", "engine_running": bool}`.
- Useful for automated monitoring.

---

### Task 7: Improve Error Reporting to UI

**File:** `akiratv/static/app.js`

- After `/api/start` call, if `result.success === false`, display `result.error` prominently.
- Log full error to console for debugging.
- Consider adding a "Show Debug" toggle to view raw error messages.

---

## Success Criteria

1. **Logging:**
   - `logs/worker.log` exists and contains entries from startup to playback.
   - Errors also appear on stderr in terminal.

2. **HLS Generation:**
   - `/home/akira/akiratv/TatkoTV/index.m3u8` is created.
   - Multiple `seg_*.ts` files appear (at least 4, as per `playlist_size` config).

3. **HTTP Server:**
   - Listening on `0.0.0.0:8081` (`ss -tulpn` shows Python).
   - Returns correct HLS playlist and segments for any enabled channel.

4. **Stream Playback:**
   - Stream URL `http://192.168.50.183:8081/hls/TatkoTV/index.m3u8` plays in VLC/browser.
   - Video is visible and audio works.

5. **No Silent Failures:**
   - All critical errors (import failures, missing directories, FFmpeg errors) are logged and, if appropriate, reported to UI.

---

## Implementation Order

1. **Fix logging** (Task 1) – gives immediate visibility.
2. **Verify dependencies** (Task 2) – ensures core modules can import.
3. **Fix paths** (Task 3) – ensures FFmpeg can find video files.
4. **Test startup** (Task 5) – validates everything works.
5. **Add health check** (Task 6) – optional but useful.
6. **Improve UI error reporting** (Task 7) – better UX.

---

## Notes

- The current config uses `"output": {"mode": "ram_http"}` with `storage.ram_path = "/home/akira/akiratv"`. Ensure this directory is writable.
- RAM storage is used to avoid disk I/O; HLS segments are written there.
- The HTTP server (`aiohttp`) serves files from that directory under `/hls/{channel}/`.
- For dynamic channels like `TatkoTV`, the worker will:
  1. Check schedule for current time.
  2. Find matching video entry.
  3. Start FFmpeg with HLS output to `ram_path/TatkoTV/`.
  4. Keep segments rotating based on `playlist_size`.
- If no schedule entry exists for current time, it enters standby mode (looping standby video).

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| `aiohttp` binary wheels incompatible with system | Use `pip install --no-binary :all:` or install system packages (`libffi`, `openssl`, `python3-dev`). |
| Path conversion breaks other channels | Test conversion on backup; check all schedule files. |
| Port 8081 in use | Change to 8082 or free the port. |
| Permissions on `/home/akira/akiratv` | Ensure write permissions for user `akira`. |
| Standby video missing | Verify `assets/standby/default_standby.mp4` exists. |

---

## Completion Checklist

- [ ] Logging configured with absolute path and stderr fallback.
- [ ] `aiohttp` and dependencies verified working.
- [x] All schedule and collection paths converted to Linux paths. (Completed 2026-04-06)
- [ ] `logs/worker.log` appears and writes entries on startup.
- [ ] HLS directory for at least one channel created and populated.
- [ ] HTTP server starts without errors and binds to expected port.
- [ ] Stream URL accessible and plays video.
- [ ] No unhandled exceptions in core import (`python -c "import akiratv.core"` succeeds).
- [ ] Web UI can start/stop engine and shows errors if any.

---

## References

- `launch_web.sh` – Web UI launcher  
- `config.json` – Configuration (output mode, paths, port)  
- `akiratv/core.py` – Engine core, logging, worker management  
- `akiratv/server/http_server.py` – aiohttp HLS server  
- `akiratv/workers/dynamic_worker.py` – Dynamic channel worker (TatkoTV)  
- `user/schedules/schedule_TatkoTV.json` – Schedule with Windows paths  
- `user/collections/collections_TatkoTV.json` – Collection data with Windows paths  

---

**Action:** Implement tasks in order, testing after each step. Use `logs/worker.log` as primary diagnostic source once fixed. If issues persist, check that all paths are correct and that FFmpeg is installed and accessible (`ffmpeg -version` should work).
