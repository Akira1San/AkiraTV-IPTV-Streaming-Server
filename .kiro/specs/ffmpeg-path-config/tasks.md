# Implementation Plan: FFmpeg/FFprobe Configurable Binary Paths

## Overview

Three focused changes: extend the config schema with two optional path fields, update the path-resolution function to accept and validate overrides, and wire the initializer into `AkiraTV.__init__` before workers start.

## Tasks

- [ ] 1. Extend `config.py` with new path fields and helper method
  - [ ] 1.1 Add `path` and `ffprobe_path` to `DEFAULT_CONFIG["ffmpeg"]`
    - Insert `"path": None` and `"ffprobe_path": None` into the `"ffmpeg"` dict in `DEFAULT_CONFIG`, before `"hwaccel"`
    - No other fields in `DEFAULT_CONFIG` change
    - `_merge_with_defaults` already deep-merges, so legacy configs inherit `None` automatically
    - _Requirements: 1.1, 4.1, 4.3_

  - [ ] 1.2 Add `get_ffmpeg_paths()` method to `Config`
    - Return `(ffmpeg_path, ffprobe_path)` as `tuple[str | None, str | None]`
    - Coerce empty string `""` to `None` using `or None`
    - Handle missing keys gracefully (`.get()` with `None` default)
    - _Requirements: 1.2, 1.3, 1.4, 1.5_

  - [ ]* 1.3 Write property tests for `Config.get_ffmpeg_paths()`
    - **Property 6: get_ffmpeg_paths Null/Empty Coercion** — for any config where `ffmpeg.path`/`ffmpeg.ffprobe_path` are `null`, `""`, or absent, `get_ffmpeg_paths()` returns `None` for those fields and never raises
    - **Property 3: Backward Compatibility** — for any config dict lacking the new keys, `_merge_with_defaults` produces a merged dict where both keys exist as `None` and `get_ffmpeg_paths()` returns `(None, None)`
    - **Validates: Requirements 1.3, 1.4, 1.5, 4.1, 4.2, 4.3**
    - Use `hypothesis` with `st.fixed_dictionaries` / `st.none()` / `st.text()` strategies

- [ ] 2. Update `collections.py` with override support and `init_ffmpeg_paths`
  - [ ] 2.1 Extend `get_ffmpeg_bin_path()` to accept optional override parameters
    - Add `ffmpeg_override: str | None = None` and `ffprobe_override: str | None = None` parameters
    - For each binary independently: if override is provided, check `os.path.exists` and `os.access(path, os.X_OK)`
    - If override is valid → log `INFO` (path taken from config) and use it; skip remaining steps for that binary
    - If override is invalid → log `WARNING` with path value and reason, fall through to existing four-step chain
    - Existing bundled → system PATH → Windows default → bare string fallback remains intact for each binary
    - Log `INFO` when auto-detection succeeds, indicating which step resolved the path
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 6.1, 6.2, 6.3_

  - [ ]* 2.2 Write property tests for `get_ffmpeg_bin_path()`
    - **Property 1: Override Priority** — for any path string that exists on disk and is executable, `get_ffmpeg_bin_path(path, path)` returns exactly that path for both binaries
    - **Property 2: Graceful Fallback on Invalid Path** — for any non-empty string that is not an existing executable file, passing it as override produces a result ≠ that string and the result is a non-empty string
    - **Property 4: Independent Resolution** — overriding `ffmpeg_override` does not affect the resolved `ffprobe` path and vice versa
    - **Property 5: No Crash on Any Config** — calling `get_ffmpeg_bin_path` with any combination of `None` / arbitrary strings never raises an exception and always returns two non-empty strings
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 5.3**
    - Use `hypothesis` with `tmp_path` fixtures and `st.text()` / `st.none()` strategies; mock filesystem for invalid-path cases

  - [ ] 2.3 Add `init_ffmpeg_paths(config)` function
    - Declare `global FFMPEG_PATH, FFPROBE_PATH` at the top of the function
    - Call `config.get_ffmpeg_paths()` to retrieve overrides
    - Call `get_ffmpeg_bin_path(ffmpeg_override, ffprobe_override)` and assign results to the module-level constants
    - Wrap in a broad `except Exception` to satisfy Requirement 5.3 — log the error and fall back to `get_ffmpeg_bin_path(None, None)`
    - _Requirements: 5.2, 5.3_

- [ ] 3. Checkpoint — ensure unit tests pass before wiring
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Wire `init_ffmpeg_paths` into `AkiraTV.__init__`
  - [ ] 4.1 Call `init_ffmpeg_paths(self.config)` in `core.py`
    - Import `init_ffmpeg_paths` from `akiratv.collections` at the top of `core.py` (or inline import inside `__init__`)
    - Insert the call immediately after `self.config = Config.load_or_create()` and before `self.transcoding_service = TranscodingService(...)`
    - No other changes to `core.py`
    - _Requirements: 5.1, 5.2_

- [ ] 5. Final checkpoint — ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests use `hypothesis`; no new dependencies are needed beyond what the project already uses
- `get_ffmpeg_bin_path` resolves each binary independently — the two override parameters are fully orthogonal

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["1.3", "2.1"] },
    { "id": 3, "tasks": ["2.2", "2.3"] },
    { "id": 4, "tasks": ["4.1"] }
  ]
}
```
