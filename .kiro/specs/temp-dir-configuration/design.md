# Design Document: temp-dir-configuration

## Overview

This feature makes three previously hard-coded filesystem paths configurable in AkiraTV:

1. **Temp directory** — where workers write transient files (trimmed clips, HLS segment staging). Currently hard-coded to `Path("temp")` in `LinearWorker` and derived from `get_output_root()` in `VODWorker`.
2. **FFmpeg binary paths** — where `ffmpeg` and `ffprobe` executables live. Currently auto-detected or hard-coded as `FFPROBE_PATH = r"C:\ffmpeg\bin\ffprobe.exe"` in `collections.py`.
3. **User data root** — the parent directory for collections, schedules, inventory, covers, and playlists. Currently hard-coded as `Path("user/...")` throughout routes.

All three settings are added to `DEFAULT_CONFIG` in `config.py`, exposed via new `Config` methods, persisted through the existing `PATCH /api/config` + `/api/config/save` flow, and surfaced in the Web UI Settings tab.

---

## Architecture

The change is purely additive to the existing layered architecture:

```
Web UI (index.html / app.js)
        │  GET/PATCH /api/config
        ▼
routes/config.py  ──►  CoreAPI  ──►  Config (config.py)
                                          │
                          ┌───────────────┼───────────────┐
                          ▼               ▼               ▼
                    get_temp_dir_path()  get_ffmpeg_paths()  get_user_root()
                          │               │               │
                    LinearWorker    collections.py    routes/*
                    VODWorker       standby.py
                    DynamicWorker   SanityCheck.py
```

No new modules are introduced. All changes are confined to existing files.

---

## Components and Interfaces

### config.py — New DEFAULT_CONFIG keys

```python
DEFAULT_CONFIG = {
    # ... existing keys ...
    "temp_dir": {
        "type": "disk",   # "disk" | "ram"
        "path": "./temp"
    },
    "ffmpeg_bin": {
        "ffmpeg_path": "",   # empty = auto-detect
        "ffprobe_path": ""   # empty = auto-detect
    },
    "paths": {
        "user_root": "./user",
        "playlists_root": "./playlists"
    }
}
```

### config.py — New Config methods

```python
def get_temp_dir_path(self) -> Path:
    """
    Returns the resolved temp directory Path.
    Attempts to create it if it does not exist.
    Falls back to Path("./temp") on permission/invalid-path errors, logging a warning.
    """

def get_ffmpeg_paths(self) -> tuple[str, str]:
    """
    Returns (ffmpeg_path, ffprobe_path).
    Uses configured values when non-empty and the binary exists.
    Falls back to get_ffmpeg_bin_path() auto-detection for missing/invalid entries,
    logging a warning when a configured path is unusable.
    """

def get_user_root(self) -> Path:
    """Returns Path(paths.user_root), defaulting to Path("user")."""

def get_collections_dir(self) -> Path:
    """Returns get_user_root() / "collections"."""

def get_schedules_dir(self) -> Path:
    """Returns get_user_root() / "schedules"."""

def get_inventory_path(self) -> Path:
    """Returns get_user_root() / "video_inventory.json"."""

def get_covers_dir(self) -> Path:
    """Returns get_user_root() / "covers"."""

def get_playlists_dir(self) -> Path:
    """Returns Path(paths.playlists_root), defaulting to Path("playlists")."""
```

### collections.py — Signature change

Remove the dead constant:
```python
# REMOVE:
FFPROBE_PATH = r"C:\ffmpeg\bin\ffprobe.exe"
```

Update `get_video_duration()`:
```python
def get_video_duration(video_path: str, ffprobe_path: str = None) -> float:
    """
    ffprobe_path: explicit binary path. Defaults to get_ffmpeg_bin_path()[1] when None.
    """
```

### standby.py — Signature changes

```python
def create_standby_video(duration=30, codec="h265", output_path=None,
                         resolution=(720, 400), temp_dir: Path = None) -> Path:
    # Uses temp_dir / f"standby_img_{w}x{h}.png" when provided,
    # else falls back to Path("temp") / ...

def add_end_card_to_video(input_path, next_title, duration, output_path,
                          codec="h265", temp_dir: Path = None) -> str:
    # Uses temp_dir / f"endcard_{uuid}.png" when provided,
    # else falls back to Path("temp") / ...
```

### workers/linear_worker.py — _create_temp_directory

```python
def _create_temp_directory(self) -> Path:
    base = self.config.get_temp_dir_path()
    temp_dir = base / f"concat_{self.channel}_{int(time.time())}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir
```

### workers/vod_worker.py — _create_temp_directory

```python
def _create_temp_directory(self) -> Path:
    base = self.config.get_temp_dir_path()
    temp_dir = base / f"vod_{self.channel}_{int(time.time())}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir
```

### workers/dynamic_worker.py

`DynamicWorker` writes HLS output directly to `hls_dir` and does not maintain a separate temp directory. No changes are required; the requirement is satisfied by the absence of hard-coded temp paths.

### workers/SanityCheck.py — probe_file signature

```python
def probe_file(file_path, ffprobe_path: str = "ffprobe"):
    cmd = [ffprobe_path, "-v", "quiet", "-print_format", "json",
           "-show_streams", str(file_path)]
    ...
```

`__main__` block attempts to import `get_ffmpeg_bin_path` and use its result:
```python
if __name__ == "__main__":
    try:
        from akiratv.collections import get_ffmpeg_bin_path
        _, default_ffprobe = get_ffmpeg_bin_path()
    except ImportError:
        default_ffprobe = "ffprobe"
    check_folder(sys.argv[1], ffprobe_path=default_ffprobe)
```

### routes — Hard-coded path migration

Each route obtains the `Config` instance via `app_context.akiratv.config` (or equivalent accessor) and replaces hard-coded paths:

| Route file | Hard-coded path | Replacement call |
|---|---|---|
| `routes/standby.py` | `Path("user/video_inventory.json")` | `config.get_inventory_path()` |
| `routes/guide.py` | `Path("user/schedules/schedule_*.json")` | `config.get_schedules_dir()` |
| `routes/guide.py` | `Path("user/collections")` | `config.get_collections_dir()` |
| `routes/wizard.py` | `Path("user/collections")` | `config.get_collections_dir()` |
| `routes/wizard.py` | `Path("user/schedules")` | `config.get_schedules_dir()` |
| `routes/vod.py` | `Path("user/collections")` | `config.get_collections_dir()` |
| `routes/fast_scheduler.py` | `Path("user/collections")` | `config.get_collections_dir()` |
| `routes/playlist.py` | `Path("playlists")` | `config.get_playlists_dir()` |

### Web UI — Settings tab additions

Three new sub-sections are added inside the existing `<div id="settingsTab">` in `index.html` and wired up in `app.js`:

**Temp Directory sub-section**
- Dropdown: "Temp Dir Mode" — options `Disk` (`"disk"`) / `RAM / tmpfs` (`"ram"`)
- Text input: "Temp Dir Path" — shown for both modes; helper note for RAM mode
- Visibility: always shown; helper note conditionally shown when RAM is selected

**FFmpeg Binaries sub-section**
- Text input: "FFmpeg Path" (maps to `ffmpeg_bin.ffmpeg_path`)
- Text input: "FFprobe Path" (maps to `ffmpeg_bin.ffprobe_path`)
- Static helper note: "Leave blank to use auto-detection"

**Paths sub-section**
- Text input: "User Data Root" (maps to `paths.user_root`)
- Text input: "Playlists Root" (maps to `paths.playlists_root`)

`loadConfig()` / `showConfigModal()` populates all six inputs from `GET /api/config`.  
`saveConfiguration()` includes `temp_dir`, `ffmpeg_bin`, and `paths` objects in the `PATCH /api/config` payload.

---

## Data Models

### config.json additions

```json
{
  "temp_dir": {
    "type": "disk",
    "path": "./temp"
  },
  "ffmpeg_bin": {
    "ffmpeg_path": "",
    "ffprobe_path": ""
  },
  "paths": {
    "user_root": "./user",
    "playlists_root": "./playlists"
  }
}
```

### Validation rules (enforced in routes/config.py PATCH handler)

| Field | Valid values | Error on violation |
|---|---|---|
| `temp_dir.type` | `"disk"` or `"ram"` | HTTP 400 |
| `temp_dir.path` | non-empty string | HTTP 400 |
| `ffmpeg_bin.ffmpeg_path` | string (may be empty) | HTTP 400 if not string |
| `ffmpeg_bin.ffprobe_path` | string (may be empty) | HTTP 400 if not string |
| `paths.user_root` | string (may be empty → default) | HTTP 400 if not string |
| `paths.playlists_root` | string (may be empty → default) | HTTP 400 if not string |

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Config merge always produces temp_dir defaults

*For any* config dict that does not contain a `temp_dir` key, merging it with `DEFAULT_CONFIG` via `_merge_with_defaults()` SHALL produce a config where `temp_dir.type == "disk"` and `temp_dir.path == "./temp"`.

**Validates: Requirements 1.2**

---

### Property 2: Config save/reload round-trip preserves temp_dir

*For any* valid `temp_dir` object (with `type` in `{"disk", "ram"}` and a non-empty `path`), saving it to a config file and reloading that file SHALL produce a `Config` instance with identical `temp_dir` values.

**Validates: Requirements 2.3, 2.4**

---

### Property 3: Invalid temp_dir.type is always rejected

*For any* string that is not `"disk"` or `"ram"`, sending it as `temp_dir.type` in a PATCH request to `/api/config` SHALL return HTTP 400.

**Validates: Requirements 2.2**

---

### Property 4: Worker temp directories are always cleaned up

*For any* temp directory created by `LinearWorker._create_temp_directory()` or `VODWorker._create_temp_directory()`, after the corresponding cleanup phase completes (normally or via exception), the directory SHALL no longer exist on disk.

**Validates: Requirements 4.3, 5.4**

---

### Property 5: User root path methods return sub-paths of user_root

*For any* `user_root` path string configured in `paths.user_root`, the paths returned by `get_collections_dir()`, `get_schedules_dir()`, `get_inventory_path()`, and `get_covers_dir()` SHALL all be sub-paths of `Path(user_root)`.

**Validates: Requirements 10.4, 10.5, 10.6, 10.7**

---

### Property 6: probe_file exception includes the attempted binary path

*For any* non-existent or non-executable `ffprobe_path` string, calling `probe_file(file_path, ffprobe_path=ffprobe_path)` SHALL raise an exception whose message contains the attempted `ffprobe_path` value.

**Validates: Requirements 11.5**

---

## Error Handling

### get_temp_dir_path() fallback

```
configured path → try mkdir → success → return configured path
                            → PermissionError / OSError
                                → log warning with path + error
                                → return Path("./temp")
```

Workers log a secondary warning when the returned path differs from what was configured.

### get_ffmpeg_paths() fallback

```
configured path non-empty → check binary exists → exists → return configured path
                                                 → missing/not-executable
                                                     → log warning
                                                     → fall back to auto-detect for that binary
configured path empty → call get_ffmpeg_bin_path() → return auto-detected path
```

### PATCH /api/config validation

The existing `update_config` handler in `CoreAPI` is extended to validate `temp_dir.type`, `ffmpeg_bin.*`, and `paths.*` fields before applying the update. Invalid values raise `HTTPException(400)` with a descriptive message before any in-memory state is modified.

### Route config access

Routes access config via `app_context.akiratv.config`. If `app_context.akiratv` is `None` (e.g., during startup), routes fall back to the hard-coded defaults they currently use, preserving backward compatibility.

---

## Testing Strategy

### Unit tests

- `Config.default_config()` contains all three new top-level keys with correct defaults.
- `Config._merge_with_defaults()` correctly merges partial configs (missing `temp_dir`, missing `ffmpeg_bin`, missing `paths`).
- `Config.get_temp_dir_path()` returns the configured path when it exists; creates it when it does not; returns `./temp` fallback on permission error.
- `Config.get_ffmpeg_paths()` returns configured values when non-empty and valid; falls back to auto-detection for empty or invalid values.
- `Config.get_user_root()`, `get_collections_dir()`, `get_schedules_dir()`, `get_inventory_path()`, `get_covers_dir()`, `get_playlists_dir()` return correct sub-paths.
- `collections.get_video_duration()` accepts optional `ffprobe_path` and uses it in the subprocess call.
- `standby.create_standby_video()` and `add_end_card_to_video()` write intermediate files to the provided `temp_dir`.
- `SanityCheck.probe_file()` uses the provided `ffprobe_path` in the subprocess command.

### Property-based tests

Using `hypothesis` (Python). Minimum 100 iterations per property.

**Property 1** — `test_merge_always_produces_temp_dir_defaults`
- Generator: arbitrary dicts without a `temp_dir` key
- Assert: merged result has `temp_dir.type == "disk"` and `temp_dir.path == "./temp"`
- Tag: `Feature: temp-dir-configuration, Property 1: Config merge always produces temp_dir defaults`

**Property 2** — `test_config_save_reload_round_trip`
- Generator: valid `(type, path)` pairs where type ∈ {"disk", "ram"} and path is a non-empty string
- Assert: save to temp file, reload, `config.data["temp_dir"]` equals original
- Tag: `Feature: temp-dir-configuration, Property 2: Config save/reload round-trip preserves temp_dir`

**Property 3** — `test_invalid_temp_dir_type_rejected`
- Generator: arbitrary strings filtered to exclude `"disk"` and `"ram"`
- Assert: PATCH request returns HTTP 400
- Tag: `Feature: temp-dir-configuration, Property 3: Invalid temp_dir.type is always rejected`

**Property 4** — `test_worker_temp_dirs_cleaned_up`
- Generator: valid temp dir base paths (using `tmp_path` fixture variants)
- Assert: after `_cleanup_phase()`, the created subdirectory does not exist
- Tag: `Feature: temp-dir-configuration, Property 4: Worker temp directories are always cleaned up`

**Property 5** — `test_user_root_methods_return_sub_paths`
- Generator: arbitrary non-empty path strings for `user_root`
- Assert: all four path methods return paths whose string starts with the resolved `user_root`
- Tag: `Feature: temp-dir-configuration, Property 5: User root path methods return sub-paths of user_root`

**Property 6** — `test_probe_file_exception_includes_path`
- Generator: arbitrary strings that are not valid executable paths
- Assert: `probe_file(some_file, ffprobe_path=bad_path)` raises an exception containing `bad_path`
- Tag: `Feature: temp-dir-configuration, Property 6: probe_file exception includes the attempted binary path`

### Integration tests

- `PATCH /api/config` with valid `temp_dir`, `ffmpeg_bin`, `paths` objects returns HTTP 200 and updates in-memory config.
- `PATCH /api/config` with invalid `temp_dir.type` returns HTTP 400.
- Routes (`standby`, `guide`, `wizard`, `vod`, `fast_scheduler`, `playlist`) use `config.get_*()` methods rather than hard-coded paths (verified by mocking `app_context`).
