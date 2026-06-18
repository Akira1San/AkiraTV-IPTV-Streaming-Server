# Requirements Document

## Introduction

This feature adds two optional fields — `ffmpeg.path` and `ffmpeg.ffprobe_path` — to AkiraTV's `config.json`. When set to a valid, executable path, these fields override the existing auto-detection logic so users can point AkiraTV at specific FFmpeg/FFprobe binaries (e.g., a custom build, a versioned install, or a non-standard location). When absent, null, or empty, the existing four-step auto-detection chain runs unchanged, preserving full backward compatibility with all existing installations.

## Glossary

- **Config**: The `Config` class in `akiratv/config.py` that loads, merges, and exposes `config.json` data.
- **PathResolver**: The `get_ffmpeg_bin_path()` function in `akiratv/collections.py` that resolves the final `FFMPEG_PATH` and `FFPROBE_PATH` values.
- **Initializer**: The `init_ffmpeg_paths(config)` function in `akiratv/collections.py` that reads override paths from config and sets the module-level constants.
- **Core**: The `AkiraTV` class in `akiratv/core.py` that orchestrates startup.
- **FFMPEG_PATH**: The module-level constant in `akiratv/collections.py` consumed by all workers.
- **FFPROBE_PATH**: The module-level constant in `akiratv/collections.py` consumed by all workers and `get_video_duration()`.
- **Auto-detection**: The existing four-step fallback chain: bundled binary → system PATH → Windows default → bare string.
- **Override path**: A non-null, non-empty string value supplied in `config.json` under `ffmpeg.path` or `ffmpeg.ffprobe_path`.
- **Legacy config**: A `config.json` that predates this feature and contains no `path` or `ffprobe_path` keys under `ffmpeg`.

---

## Requirements

### Requirement 1: Config Schema Extension

**User Story:** As a user, I want to add `ffmpeg.path` and `ffmpeg.ffprobe_path` fields to `config.json`, so that I can point AkiraTV at specific FFmpeg/FFprobe binaries without modifying source code.

#### Acceptance Criteria

1. THE Config SHALL include `ffmpeg.path` and `ffmpeg.ffprobe_path` as optional fields in `DEFAULT_CONFIG`, defaulting to `null`.
2. WHEN `config.json` contains explicit string values for `ffmpeg.path` and `ffmpeg.ffprobe_path`, THE Config SHALL expose those values via `get_ffmpeg_paths()`.
3. WHEN `config.json` contains `null` values for `ffmpeg.path` or `ffmpeg.ffprobe_path`, THE Config SHALL return `None` for those fields from `get_ffmpeg_paths()`.
4. WHEN `config.json` contains empty string values for `ffmpeg.path` or `ffmpeg.ffprobe_path`, THE Config SHALL return `None` for those fields from `get_ffmpeg_paths()`.
5. WHEN `config.json` is a legacy config that does not contain `ffmpeg.path` or `ffmpeg.ffprobe_path` keys, THE Config SHALL return `(None, None)` from `get_ffmpeg_paths()`.

---

### Requirement 2: Override Path Resolution

**User Story:** As a user, I want AkiraTV to use my configured FFmpeg/FFprobe paths when they are valid, so that my custom binaries are used for all streaming operations.

#### Acceptance Criteria

1. WHEN `ffmpeg.path` is set to a non-empty string that exists on disk and is executable, THE PathResolver SHALL return that path as `FFMPEG_PATH`.
2. WHEN `ffmpeg.ffprobe_path` is set to a non-empty string that exists on disk and is executable, THE PathResolver SHALL return that path as `FFPROBE_PATH`.
3. THE PathResolver SHALL resolve `FFMPEG_PATH` and `FFPROBE_PATH` independently, such that overriding one path does not affect the resolution of the other.
4. WHEN only `ffmpeg.path` is overridden and `ffmpeg.ffprobe_path` is null, THE PathResolver SHALL use the override for `FFMPEG_PATH` and run auto-detection for `FFPROBE_PATH`.
5. WHEN only `ffmpeg.ffprobe_path` is overridden and `ffmpeg.path` is null, THE PathResolver SHALL use the override for `FFPROBE_PATH` and run auto-detection for `FFMPEG_PATH`.

---

### Requirement 3: Graceful Fallback on Invalid Override

**User Story:** As a user, I want AkiraTV to continue starting up even if my configured path is wrong, so that a misconfiguration does not prevent streaming.

#### Acceptance Criteria

1. WHEN a configured `ffmpeg.path` does not exist on disk, THE PathResolver SHALL log a `WARNING` message and fall back to auto-detection for `FFMPEG_PATH`.
2. WHEN a configured `ffmpeg.ffprobe_path` does not exist on disk, THE PathResolver SHALL log a `WARNING` message and fall back to auto-detection for `FFPROBE_PATH`.
3. WHEN a configured `ffmpeg.path` exists on disk but is not executable, THE PathResolver SHALL log a `WARNING` message and fall back to auto-detection for `FFMPEG_PATH`.
4. WHEN a configured `ffmpeg.ffprobe_path` exists on disk but is not executable, THE PathResolver SHALL log a `WARNING` message and fall back to auto-detection for `FFPROBE_PATH`.
5. IF a configured path is invalid, THEN THE PathResolver SHALL never use that path as the resolved binary and SHALL always produce a non-empty string result.

---

### Requirement 4: Backward Compatibility

**User Story:** As an existing AkiraTV user, I want my current `config.json` to continue working without any changes, so that upgrading does not break my setup.

#### Acceptance Criteria

1. WHEN `config.json` does not contain `ffmpeg.path` or `ffmpeg.ffprobe_path` keys, THE Config._merge_with_defaults SHALL populate those keys with `null` in the merged result.
2. WHEN `get_ffmpeg_paths()` returns `(None, None)`, THE PathResolver SHALL produce the same `FFMPEG_PATH` and `FFPROBE_PATH` values as the pre-feature auto-detection logic.
3. THE Config._merge_with_defaults SHALL preserve all existing `ffmpeg` section fields (e.g., `hwaccel`, `transcoding`) when merging a legacy config that lacks the new path keys.

---

### Requirement 5: Startup Wiring

**User Story:** As a developer, I want `init_ffmpeg_paths` to be called at startup before any workers are created, so that all workers use the correct binary paths from the moment they start.

#### Acceptance Criteria

1. WHEN `AkiraTV.__init__` is called, THE Core SHALL call `init_ffmpeg_paths(config)` after `Config.load_or_create()` returns and before `TranscodingService` is instantiated.
2. WHEN `init_ffmpeg_paths(config)` is called, THE Initializer SHALL set the module-level `FFMPEG_PATH` and `FFPROBE_PATH` constants in `akiratv/collections.py`.
3. IF `init_ffmpeg_paths` encounters any error condition (invalid path, missing file, permission error), THEN THE Initializer SHALL handle it gracefully without raising an exception, ensuring `FFMPEG_PATH` and `FFPROBE_PATH` are always set to non-empty strings after the call completes.

---

### Requirement 6: Diagnostic Logging

**User Story:** As a user, I want AkiraTV to log which FFmpeg/FFprobe paths were selected and why, so that I can diagnose misconfiguration without reading source code.

#### Acceptance Criteria

1. WHEN an override path is used, THE PathResolver SHALL log an `INFO` message indicating the path was taken from config.
2. WHEN auto-detection selects a path, THE PathResolver SHALL log an `INFO` message indicating which detection step succeeded (bundled binary, system PATH, Windows default, or bare string fallback).
3. WHEN an override path is rejected due to not existing or not being executable, THE PathResolver SHALL log a `WARNING` message that includes the configured path value and the reason for rejection.
