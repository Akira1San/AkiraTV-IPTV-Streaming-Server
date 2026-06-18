# Implementation Plan: FFmpeg/FFprobe Path Config (Web UI)

## Overview

Extend the backend plan (config schema + path resolution + startup wiring) with a **web UI** for setting custom FFmpeg/FFprobe binary paths. Users configure paths through the Settings modal; the UI saves them to `config.json` via the existing `PATCH /api/config` endpoint. By default (null/empty), the UI displays the auto-detected path as a read-only placeholder.

---

## Tasks

### Wave 0 — Backend Core

- [x] **0.1** Add `"bin_dir": null` to `DEFAULT_CONFIG["ffmpeg"]` in `akiratv/config.py:14`
  - Insert before `"hwaccel"` so it appears first in the ffmpeg block
  - Single field replaces the earlier `path`/`ffprobe_path` pair — user points to a directory containing both binaries
  - `_merge_with_defaults` auto-fills `null` for legacy configs

- [x] **0.2** Add `Config.get_ffmpeg_bin_dir() -> str | None` in `akiratv/config.py`
  - Read `ffmpeg.bin_dir` from `self.data`
  - Coerce empty string `""` to `None` via `or None`

- [x] **0.3** Modify `get_ffmpeg_bin_path(bin_dir_override=None)` in `akiratv/collections.py:19`
  - If `bin_dir_override` is set: validate directory exists, look for `ffmpeg` and `ffprobe` inside
    - Both found → log INFO and use them
    - Directory invalid or binaries missing → log WARNING and fall through
  - Existing 4-step auto-detection chain unchanged

- [x] **0.4** Add `init_ffmpeg_paths(config)` in `akiratv/collections.py`
  - `global FFMPEG_PATH, FFPROBE_PATH`
  - Read `bin_dir` from `config.get_ffmpeg_bin_dir()`, call `get_ffmpeg_bin_path(bin_dir)`, assign results
  - Wrap in `except Exception` to satisfy no-crash guarantee

- [x] **0.5** Wire `init_ffmpeg_paths(self.config)` into `AkiraTV.__init__` in `akiratv/core.py:52`
  - Call after `Config.load_or_create()` and before `TranscodingService(...)`

### Wave 1 — API Enhancement

- [x] **1.1** Add effective FFmpeg bin dir to `get_config()` response in `akiratv/core_api.py:685`
  - After `config.data.copy()`, inject `_ffmpeg_bin_dir` key derived from `Path(FFMPEG_PATH).parent`
  - Single field tells the UI the *actual* bin directory in use (auto-detected or overridden)

### Wave 2 — Frontend: Settings Modal

- [x] **2.1** Add "FFmpeg Binary Directory" section to `akiratv/static/index.html` (before "Subtitle Settings"):
  ```html
  <div class="config-section">
      <h4>🎞️ FFmpeg Binary Directory</h4>
      <p class="help-text">Point to a directory containing ffmpeg and ffprobe. Leave empty to use auto-detected. Changes apply after restart.</p>
      <div class="config-grid">
          <div class="config-item">
              <label>Bin Directory:</label>
              <input type="text" id="ffmpegBinDir" class="config-input" placeholder="Auto-detected: /usr/bin">
          </div>
      </div>
  </div>
  ```

- [x] **2.2** Update `loadConfigurationData()` in `akiratv/static/app.js`
  - Read `_ffmpeg_bin_dir` from the API response (the effective bin dir)
  - Set as `placeholder` on the input field
  - Set `input.value` to `config.ffmpeg.bin_dir` (the config-stored override, or empty if null)

- [x] **2.3** Update `saveConfiguration()` in `akiratv/static/app.js`
  - Read `ffmpegBinDir` input value
  - If empty → send `null` (to restore auto-detection on next startup)
  - If non-empty → send the trimmed string value
  - Add to PATCH payload under `ffmpeg.bin_dir`

### Wave 3 — Edge Cases & Polish

- [x] **3.1** Handle empty field save: empty string `""` is sent as `null` to config.json
- [x] **3.2** Ensure `config.json` `null` values round-trip cleanly through JSON serialization
- [x] **3.3** Show help text: "Changes apply after restart"

---

## File Change Summary

| File | Change |
|------|--------|
| `akiratv/config.py` | +`"bin_dir": null` in DEFAULT_CONFIG, +`get_ffmpeg_bin_dir()` method |
| `akiratv/collections.py` | `get_ffmpeg_bin_path(bin_dir_override)` with dir-based override, +`init_ffmpeg_paths()` function |
| `akiratv/core.py` | +1 line: call `init_ffmpeg_paths(self.config)` in `__init__` |
| `akiratv/core_api.py` | +1 line: inject `_ffmpeg_bin_dir` into `get_config()` response |
| `akiratv/static/index.html` | +1 "FFmpeg Binary Directory" section with single input |
| `akiratv/static/app.js` | Update `loadConfigurationData()` and `saveConfiguration()` for single field |

---

## Design Decisions

1. **Single `bin_dir` field** — instead of two separate path fields, user points to a directory containing both `ffmpeg` and `ffprobe`. Simpler UX and matches the common use case (custom FFmpeg build in a single directory).

2. **No new API endpoint** — `GET /api/config` already serves config data; inject `_ffmpeg_bin_dir` as a read-only field. `PATCH /api/config` already persists new keys through deep-merge.

3. **Underscore prefix** (`_ffmpeg_bin_dir`) signals runtime values, not persisted config keys. They won't be written to `config.json`.

4. **Placeholder shows auto-detected bin dir** — when config value is null, input is empty but placeholder shows the current effective directory. This makes it obvious what's in use.

5. **Restart required** — FFmpeg path changes only take effect after AkiraTV restart. The UI communicates this via help text.

## Data Flow

```
User types bin dir in Settings modal
  → saveConfiguration() reads input value
  → PATCH /api/config { updates: { ffmpeg: { bin_dir: "/opt/custom/bin" } } }
  → core_api.update_config() deep-merges and config.save()
  → config.json now has the override
  → Next startup: init_ffmpeg_paths() reads config.get_ffmpeg_bin_dir()
  → get_ffmpeg_bin_path(bin_dir) looks for ffmpeg/ffprobe inside
  → FFMPEG_PATH / FFPROBE_PATH set to custom paths
  → GET /api/config returns { ..., ffmpeg: { bin_dir: "...", ... }, _ffmpeg_bin_dir: "..." }
  → UI shows custom dir as input value, or empty + placeholder for auto-detected
```
