# Requirements Document

## Introduction

This feature adds a configurable temporary directory setting to AkiraTV, and configurable FFmpeg binary paths. Users can choose between a RAM-based temp directory (tmpfs/memory mount) or a regular disk-based temp directory, and can specify custom paths for the `ffmpeg` and `ffprobe` binaries instead of relying solely on auto-detection. Both settings are exposed in the web UI under the existing "Configuration" modal (Settings tab), persisted to `config.json`, and applied consistently across all workers (`LinearWorker`, `VODWorker`, `DynamicWorker`) and `standby.py`.

## Glossary

- **System**: The AkiraTV application as a whole.
- **Config**: The `Config` class in `akiratv/config.py` that loads, merges, and saves `config.json`.
- **ConfigAPI**: The `/api/config` REST endpoint set defined in `akiratv/routes/config.py`.
- **WebUI**: The browser-based control panel served from `akiratv/static/index.html` and `akiratv/static/app.js`.
- **Worker**: Any of `LinearWorker`, `VODWorker`, or `DynamicWorker` that spawns FFmpeg processes and creates temporary files.
- **TempDir**: A filesystem directory used by Workers to store transient files (trimmed clips, HLS segments) during active streaming.
- **RAM TempDir**: A TempDir located on a memory-backed filesystem (e.g., `/dev/shm` on Linux, or a user-specified tmpfs mount path).
- **Disk TempDir**: A TempDir located on a regular disk path (e.g., `./temp` relative to the application working directory).
- **temp_dir_config**: The `temp_dir` sub-object within `config.json` that stores the temp directory settings.
- **FFmpegBinConfig**: The `ffmpeg_bin` sub-object within `config.json` that stores optional override paths for the `ffmpeg` and `ffprobe` binaries.
- **Auto-detection**: The existing `get_ffmpeg_bin_path()` logic in `akiratv/collections.py` that searches for FFmpeg binaries in the bundled `akiratv/bin/` directory, the system PATH, and Windows fallback paths.

---

## Requirements

### Requirement 1: Default Temp Directory Configuration

**User Story:** As a developer, I want AkiraTV to ship with a sensible default temp directory configuration, so that the application works out of the box without manual setup.

#### Acceptance Criteria

1. THE Config SHALL include a `temp_dir` key in `DEFAULT_CONFIG` with `type` set to `"disk"` and `path` set to `"./temp"`.
2. WHEN `config.json` does not contain a `temp_dir` key, THE Config SHALL merge the default `temp_dir` values into the loaded configuration via the existing deep-merge logic.
3. THE Config SHALL expose a `get_temp_dir_path()` method that returns a `Path` object representing the resolved temp directory based on the current `temp_dir` configuration.

---

### Requirement 2: Persist Temp Directory Setting

**User Story:** As a user, I want my temp directory choice to be saved to `config.json`, so that the setting survives application restarts.

#### Acceptance Criteria

1. WHEN the ConfigAPI receives a PATCH request containing a `temp_dir` object with a valid `type` (`"disk"` or `"ram"`) and a non-empty `path` string, THE ConfigAPI SHALL update the in-memory configuration and return HTTP 200.
2. WHEN the ConfigAPI receives a PATCH request containing a `temp_dir.type` value other than `"disk"` or `"ram"`, THE ConfigAPI SHALL return HTTP 400 with a descriptive error message.
3. WHEN the `/api/config/save` endpoint is called after a temp directory update, THE Config SHALL write the updated `temp_dir` object to `config.json`.
4. WHEN `config.json` is reloaded, THE Config SHALL restore the previously saved `temp_dir` settings.

---

### Requirement 3: Web UI — Temp Directory Setting

**User Story:** As a user, I want to configure the temp directory from the web interface, so that I do not need to manually edit `config.json`.

#### Acceptance Criteria

1. THE WebUI SHALL display a "Temp Directory" sub-section inside the "Settings" tab of the Configuration modal.
2. THE WebUI SHALL render a dropdown control labeled "Temp Dir Mode" with options `"Disk"` (value `"disk"`) and `"RAM / tmpfs"` (value `"ram"`).
3. WHEN the user selects `"Disk"`, THE WebUI SHALL show a text input labeled "Temp Dir Path" pre-filled with the current `temp_dir.path` value.
4. WHEN the user selects `"RAM / tmpfs"`, THE WebUI SHALL show a text input labeled "Temp Dir Path" pre-filled with the current `temp_dir.path` value and a helper note explaining that the path must point to a mounted tmpfs/memory filesystem.
5. WHEN the Configuration modal is opened, THE WebUI SHALL populate the Temp Directory controls with values fetched from `GET /api/config`.
6. WHEN the user clicks "Save Configuration", THE WebUI SHALL include the `temp_dir` object in the PATCH request payload sent to `PATCH /api/config`.

---

### Requirement 4: LinearWorker Uses Configured Temp Directory

**User Story:** As a user, I want the linear channel worker to use the configured temp directory, so that trimmed clips and concat playlists are written to my chosen location.

#### Acceptance Criteria

1. WHEN `LinearWorker._create_temp_directory()` is called, THE LinearWorker SHALL resolve the temp directory base path by calling `self.config.get_temp_dir_path()` instead of using the hard-coded `Path("temp")` prefix.
2. THE LinearWorker SHALL create the resolved temp directory (including any missing parent directories) before writing any files to it.
3. WHEN the linear stream ends, THE LinearWorker SHALL delete the temp directory it created, regardless of whether the stream ended normally or with an error.

---

### Requirement 5: VODWorker Uses Configured Temp Directory

**User Story:** As a user, I want the VOD worker to use the configured temp directory, so that HLS segment staging files are written to my chosen location.

#### Acceptance Criteria

1. WHEN `VODWorker._create_temp_directory()` is called and `storage.type` is `"ram"`, THE VODWorker SHALL create the temp directory under the path returned by `self.config.get_temp_dir_path()` instead of using `tempfile.mkdtemp()`.
2. WHEN `VODWorker._create_temp_directory()` is called and `storage.type` is not `"ram"`, THE VODWorker SHALL create the temp directory under the path returned by `self.config.get_temp_dir_path()` instead of using `self.config.get_output_root() / f"temp_{self.channel}_{timestamp}"`.
3. THE VODWorker SHALL create the resolved temp directory (including any missing parent directories) before writing any files to it.
4. WHEN the VOD playback ends, THE VODWorker SHALL delete the temp directory it created, regardless of whether playback ended normally or with an error.

---

### Requirement 6: DynamicWorker Uses Configured Temp Directory

**User Story:** As a user, I want the dynamic channel worker to use the configured temp directory for any transient files, so that all workers respect the same temp directory setting.

#### Acceptance Criteria

1. WHEN `DynamicWorker` creates any transient files during standby, scheduled content, or VOD playback, THE DynamicWorker SHALL resolve the temp directory base path by calling `self.config.get_temp_dir_path()`.
2. IF `DynamicWorker` does not currently create a separate temp directory (it writes HLS output directly to `hls_dir`), THEN THE DynamicWorker SHALL require no changes for this requirement, and this criterion is satisfied by the absence of hard-coded temp paths.

---

### Requirement 7: Temp Directory Path Validation

**User Story:** As a user, I want the application to warn me if the configured temp directory is not accessible, so that I can fix the configuration before streaming fails.

#### Acceptance Criteria

1. WHEN `Config.get_temp_dir_path()` is called and the resolved path does not exist, THE Config SHALL attempt to create the directory (including parents).
2. IF the directory cannot be created due to a permission error or invalid path, THEN THE Config SHALL log a warning message that includes the attempted path and the error reason, and SHALL return the default disk temp path `./temp` as a fallback.
3. WHEN a Worker calls `get_temp_dir_path()` and the returned path is the fallback, THE Worker SHALL log a warning indicating that the configured temp directory was unavailable and the fallback is being used.

---

### Requirement 8: FFmpeg Binary Path Configuration

**User Story:** As a user, I want to specify custom paths for the `ffmpeg` and `ffprobe` binaries, so that I can use a specific FFmpeg installation instead of relying on auto-detection.

#### Acceptance Criteria

1. THE Config SHALL include an `ffmpeg_bin` key in `DEFAULT_CONFIG` with `ffmpeg_path` set to `""` and `ffprobe_path` set to `""`, where an empty string means auto-detection is used.
2. WHEN `config.json` does not contain an `ffmpeg_bin` key, THE Config SHALL merge the default `ffmpeg_bin` values into the loaded configuration via the existing deep-merge logic.
3. THE Config SHALL expose a `get_ffmpeg_paths()` method that returns a tuple `(ffmpeg_path: str, ffprobe_path: str)`.
4. WHEN `get_ffmpeg_paths()` is called and both `ffmpeg_bin.ffmpeg_path` and `ffmpeg_bin.ffprobe_path` are non-empty strings, THE Config SHALL return those configured values as the tuple.
5. WHEN `get_ffmpeg_paths()` is called and either `ffmpeg_bin.ffmpeg_path` or `ffmpeg_bin.ffprobe_path` is an empty string, THE Config SHALL call the existing `get_ffmpeg_bin_path()` auto-detection function and return its result for the missing value(s).
6. WHEN `get_ffmpeg_paths()` is called and a configured path is set but the binary at that path does not exist or is not executable, THE Config SHALL log a warning that includes the configured path and the reason it is unusable, and SHALL fall back to the auto-detected path for that binary.
7. WHEN `LinearWorker`, `VODWorker`, `DynamicWorker`, and `standby.py` invoke FFmpeg or FFprobe, THE respective component SHALL obtain the binary paths by calling `self.config.get_ffmpeg_paths()` instead of using the module-level `FFMPEG_PATH` or `FFPROBE_PATH` constants imported from `akiratv/collections.py`. THE dead hardcoded `FFPROBE_PATH = r"C:\ffmpeg\bin\ffprobe.exe"` constant at the top of `akiratv/collections.py` SHALL be removed. THE `get_video_duration()` function in `akiratv/collections.py` SHALL accept an optional `ffprobe_path: str = None` parameter; WHEN `ffprobe_path` is not provided, THE function SHALL default to `get_ffmpeg_bin_path()[1]`; WHEN callers have access to a config object, THEY SHALL pass `config.get_ffmpeg_paths()[1]` as the `ffprobe_path` argument.
8. WHEN the ConfigAPI receives a PATCH request containing an `ffmpeg_bin` object with `ffmpeg_path` and `ffprobe_path` string fields, THE ConfigAPI SHALL update the in-memory configuration and return HTTP 200.
9. WHEN the ConfigAPI receives a PATCH request containing an `ffmpeg_bin` object where either field is not a string, THE ConfigAPI SHALL return HTTP 400 with a descriptive error message.
10. THE WebUI SHALL display an "FFmpeg Binaries" sub-section inside the "Settings" tab of the Configuration modal.
11. THE WebUI SHALL render a text input labeled "FFmpeg Path" and a text input labeled "FFprobe Path", each pre-filled with the current `ffmpeg_bin.ffmpeg_path` and `ffmpeg_bin.ffprobe_path` values respectively.
12. THE WebUI SHALL display a helper note in the "FFmpeg Binaries" sub-section stating that leaving either field blank causes the application to use auto-detection.
13. WHEN the Configuration modal is opened, THE WebUI SHALL populate the FFmpeg Binaries controls with values fetched from `GET /api/config`.
14. WHEN the user clicks "Save Configuration", THE WebUI SHALL include the `ffmpeg_bin` object in the PATCH request payload sent to `PATCH /api/config`.

---

### Requirement 9: standby.py Uses Configured Temp Directory

**User Story:** As a user, I want the standby video generator to use the configured temp directory for its intermediate image files, so that all components respect the same temp directory setting.

#### Acceptance Criteria

1. THE `create_standby_video()` function in `standby.py` SHALL accept an optional `temp_dir: Path = None` parameter.
2. WHEN `temp_dir` is provided, THE `create_standby_video()` function SHALL use it as the base directory for intermediate image files instead of `Path("temp")`.
3. WHEN `temp_dir` is not provided, THE `create_standby_video()` function SHALL fall back to `Path("temp")` for backward compatibility.
4. THE `add_end_card_to_video()` function in `standby.py` SHALL accept an optional `temp_dir: Path = None` parameter with the same fallback behavior as criteria 2 and 3.
5. WHEN callers of `create_standby_video()` and `add_end_card_to_video()` have access to a config object, THEY SHALL pass `config.get_temp_dir_path()` as the `temp_dir` argument.

---

### Requirement 10: Configurable User Data Directory

**User Story:** As a user, I want to configure the root directory for user data (collections, schedules, inventory, covers), so that I can store my data on a different drive or path without editing source code.

#### Acceptance Criteria

1. THE Config SHALL expose a `get_user_root()` method that returns a `Path`, defaulting to `Path("user")` when no override is configured.
2. THE Config SHALL include a `paths` key in `DEFAULT_CONFIG` with `user_root` set to `"./user"` and `playlists_root` set to `"./playlists"`.
3. WHEN `config.json` does not contain a `paths` key, THE Config SHALL merge the default `paths` values into the loaded configuration via the existing deep-merge logic.
4. THE Config SHALL expose a `get_collections_dir()` method that returns `get_user_root() / "collections"`.
5. THE Config SHALL expose a `get_schedules_dir()` method that returns `get_user_root() / "schedules"`.
6. THE Config SHALL expose a `get_inventory_path()` method that returns `get_user_root() / "video_inventory.json"`.
7. THE Config SHALL expose a `get_covers_dir()` method that returns `get_user_root() / "covers"`.
8. THE Config SHALL expose a `get_playlists_dir()` method that returns a `Path` based on `paths.playlists_root`, defaulting to `Path("playlists")`.
9. WHEN `routes/standby.py` reads the video inventory file, THE StandbyRoute SHALL obtain the `Config` instance via `app_context` and call `config.get_inventory_path()` instead of using the hard-coded `Path("user/video_inventory.json")`.
10. WHEN `routes/guide.py` constructs schedule file paths or reads the collections directory, THE GuideRoute SHALL obtain the `Config` instance via `app_context` and call `config.get_schedules_dir()` and `config.get_collections_dir()` instead of using hard-coded `Path("user/schedules/...")` and `Path("user/collections")` strings.
11. WHEN `routes/wizard.py` reads or writes the collections directory or schedules directory, THE WizardRoute SHALL obtain the `Config` instance via `app_context` and call `config.get_collections_dir()` and `config.get_schedules_dir()` instead of using hard-coded `Path("user/collections")` and `Path("user/schedules")` strings.
12. WHEN `routes/vod.py` reads the collections directory, THE VODRoute SHALL obtain the `Config` instance via `app_context` and call `config.get_collections_dir()` instead of using the hard-coded `Path("user/collections")` string.
13. WHEN `routes/fast_scheduler.py` reads the collections directory, THE FastSchedulerRoute SHALL obtain the `Config` instance via `app_context` and call `config.get_collections_dir()` instead of using the hard-coded `Path("user/collections")` string.
14. WHEN `routes/playlist.py` creates or reads the playlists directory, THE PlaylistRoute SHALL obtain the `Config` instance via `app_context` and call `config.get_playlists_dir()` instead of using the hard-coded `Path("playlists")` string.
15. THE WebUI SHALL display a "Paths" sub-section inside the "Settings" tab of the Configuration modal, containing a text input labeled "User Data Root" (maps to `paths.user_root`) and a text input labeled "Playlists Root" (maps to `paths.playlists_root`).
16. WHEN the Configuration modal is opened, THE WebUI SHALL populate the Paths controls with values fetched from `GET /api/config`.
17. WHEN the user clicks "Save Configuration", THE WebUI SHALL include the `paths` object in the PATCH request payload sent to `PATCH /api/config`.
18. WHEN the ConfigAPI receives a PATCH request containing a `paths` object with `user_root` and/or `playlists_root` string fields, THE ConfigAPI SHALL update the in-memory configuration and return HTTP 200.
19. WHEN the ConfigAPI receives a PATCH request containing a `paths` object where either field is not a string, THE ConfigAPI SHALL return HTTP 400 with a descriptive error message.

---

### Requirement 11: SanityCheck Uses Configured FFprobe Path

**User Story:** As a developer, I want the SanityCheck diagnostic tool to use the configured ffprobe binary path, so that it works correctly on systems where ffprobe is not on the system PATH.

#### Acceptance Criteria

1. THE `probe_file()` function in `akiratv/workers/SanityCheck.py` SHALL accept an optional `ffprobe_path: str = "ffprobe"` parameter and use it as the executable in the subprocess command instead of the bare string `"ffprobe"`.
2. WHEN `probe_file()` is called without an explicit `ffprobe_path` argument, THE SanityCheck SHALL use `"ffprobe"` as the default, preserving backward compatibility for standalone use.
3. WHEN `SanityCheck` is invoked from within the application where a `Config` instance is available, THE calling code SHALL pass `config.get_ffmpeg_paths()[1]` as the `ffprobe_path` argument to `probe_file()`.
4. WHEN `SanityCheck.py` is run as a standalone script via `__main__`, THE SanityCheck SHALL attempt to import `get_ffmpeg_bin_path` from `akiratv.collections` and use its returned ffprobe path as the default; IF the import fails, THE SanityCheck SHALL fall back to `"ffprobe"`.
5. IF the resolved `ffprobe_path` binary does not exist or the subprocess call fails, THEN THE `probe_file()` function SHALL raise an exception with a message that includes the attempted binary path and the underlying error reason.
