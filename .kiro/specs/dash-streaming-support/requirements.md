# Requirements Document

## Introduction

This document defines the requirements for adding DASH (Dynamic Adaptive Streaming over HTTP) streaming support to AkiraTV. DASH will be introduced as a second streaming mode alongside the existing HLS implementation, enabling better cross-platform compatibility for web browsers and smart TVs. The feature covers configuration schema extensions, FFmpeg argument generation, HTTP server routing, worker-level integration, error handling, and testing requirements.

## Feature Overview

**Feature Name:** dash-streaming-support

**Description:** Add DASH (Dynamic Adaptive Streaming over HTTP) streaming support to AkiraTV as a second streaming mode alongside the existing HLS implementation, enabling better cross-platform compatibility for web browsers and smart TVs.

---

## Requirements

### 1. Configuration Schema Extension

#### 1.1 DASH Configuration Section

**Requirement:** The system shall provide a DASH configuration section within the output configuration.

**Acceptance Criteria:**

- [ ] 1.1.1 When the configuration is loaded, the system shall provide a `dash` object within the `output` section of the configuration.
- [ ] 1.1.2 The `dash` configuration object shall include a `segment_duration` property with a default value of 6 seconds.
- [ ] 1.1.3 The `dash` configuration object shall include a `fragment_duration` property with a default value of 6 seconds.
- [ ] 1.1.4 The `dash` configuration object shall include a `min_buffer_time` property with a default value of 2.0 seconds.
- [ ] 1.1.5 The `dash` configuration object shall include a `playlist_size` property with a default value of 4.
- [ ] 1.1.6 When a user creates a new configuration file, the system shall include the `dash` section with default values in the generated file.

#### 1.2 Output Mode Selection

**Requirement:** The system shall support selecting between HLS and DASH streaming modes via configuration.

**Acceptance Criteria:**

- [ ] 1.2.1 The system shall accept `http_hls` as a valid value for the `output.mode` configuration property.
- [ ] 1.2.2 The system shall accept `http_dash` as a valid value for the `output.mode` configuration property.
- [ ] 1.2.3 The system shall accept `ram_http` as a valid value for the `output.mode` configuration property (existing behavior).
- [ ] 1.2.4 When `output.mode` is set to an unrecognized value, the system shall log an error and default to `http_hls`.
- [ ] 1.2.5 When the configuration is loaded without an `output.mode` property, the system shall default to `http_hls`.

#### 1.3 Configuration Backward Compatibility

**Requirement:** The system shall maintain backward compatibility with existing HLS configurations.

**Acceptance Criteria:**

- [ ] 1.3.1 When an existing configuration file without a `dash` section is loaded, the system shall not raise an error.
- [ ] 1.3.2 When an existing configuration file is loaded, the system shall merge user configuration with default values for any missing properties.
- [ ] 1.3.3 When `output.mode` is set to `http_hls`, the system shall continue to use the existing HLS streaming behavior without modification.
- [ ] 1.3.4 When the configuration is saved, the system shall preserve all existing configuration values including the new `dash` section.

---

### 2. FFmpeg Argument Building for DASH

#### 2.1 DASH Output Format

**Requirement:** The system shall generate FFmpeg arguments for DASH streaming when configured.

**Acceptance Criteria:**

- [ ] 2.1.1 When `output.mode` is set to `http_dash`, the system shall include `-f dash` in the FFmpeg arguments.
- [ ] 2.1.2 The system shall include `-seg_duration` argument with the value from `output.dash.segment_duration` configuration.
- [ ] 2.1.3 The system shall include `-frag_duration` argument with the value from `output.dash.fragment_duration` configuration.
- [ ] 2.1.4 The system shall include `-window_size` argument with the value from `output.dash.playlist_size` configuration.
- [ ] 2.1.5 The system shall set the output manifest path to `{output_dir}/manifest.mpd`.
- [ ] 2.1.6 The system shall configure segment naming pattern as `seg_$Number$.m4s`.
- [ ] 2.1.7 The system shall configure initialization segment naming as `init.mp4`.

#### 2.2 DASH Encoding Parameters

**Requirement:** The system shall use appropriate encoding parameters for DASH streaming.

**Acceptance Criteria:**

- [ ] 2.2.1 The system shall include `-c:v libx264` for video encoding when transcoding is enabled.
- [ ] 2.2.2 The system shall include `-c:a aac` for audio encoding when transcoding is enabled.
- [ ] 2.2.3 The system shall include `-bf 1` to limit B-frames for DASH compatibility.
- [ ] 2.2.4 The system shall include `-keyint_min` and `-g` arguments based on the segment duration for proper keyframe alignment.
- [ ] 2.2.5 The system shall include `-sc_threshold 0` to disable scene change detection for consistent segment boundaries.
- [ ] 2.2.6 When transcoding is disabled, the system shall use `-c:v copy -c:a copy` for stream copy mode.

#### 2.3 DASH Adaptation Sets

**Requirement:** The system shall configure proper adaptation sets for DASH manifests.

**Acceptance Criteria:**

- [ ] 2.3.1 The system shall include `-adaptation_sets` argument specifying video streams.
- [ ] 2.3.2 The system shall include `-adaptation_sets` argument specifying audio streams.
- [ ] 2.3.3 The generated MPD manifest shall contain both video and audio adaptation sets when both streams are present.

---

### 3. HTTP Server DASH File Handling

#### 3.1 DASH Route Configuration

**Requirement:** The HTTP server shall serve DASH manifests and segments with appropriate routes.

**Acceptance Criteria:**

- [ ] 3.1.1 The HTTP server shall register a route handler for DASH files at `/dash/{path:.+}`.
- [ ] 3.1.2 The HTTP server shall route requests for `.mpd` files to the DASH handler.
- [ ] 3.1.3 The HTTP server shall route requests for `.m4s` files to the DASH handler.
- [ ] 3.1.4 The HTTP server shall route requests for DASH initialization segments (`init.mp4`) to the DASH handler.

#### 3.2 MPD Manifest Serving

**Requirement:** The HTTP server shall serve DASH MPD manifests with correct headers.

**Acceptance Criteria:**

- [ ] 3.2.1 When an MPD manifest is requested and exists, the server shall return HTTP 200 status.
- [ ] 3.2.2 The server shall set `Content-Type: application/dash+xml` for MPD manifest responses.
- [ ] 3.2.3 The server shall include `Access-Control-Allow-Origin: *` header for cross-origin playback.
- [ ] 3.2.4 The server shall set `Cache-Control: no-cache, no-store, must-revalidate` for manifest responses.
- [ ] 3.2.5 When an MPD manifest is requested and does not exist, the server shall return HTTP 404 status.

#### 3.3 DASH Segment Serving

**Requirement:** The HTTP server shall serve DASH media segments with correct headers.

**Acceptance Criteria:**

- [ ] 3.3.1 When an `.m4s` segment is requested and exists, the server shall return HTTP 200 status.
- [ ] 3.3.2 The server shall set `Content-Type: video/mp4` for segment responses.
- [ ] 3.3.3 The server shall include `Access-Control-Allow-Origin: *` header for segment responses.
- [ ] 3.3.4 When a segment file has size 0 (being written), the server shall retry reading up to 20 times with 0.5s delay.
- [ ] 3.3.5 When a segment file cannot be read after retries, the server shall return HTTP 503 status.

#### 3.4 Initialization Segment Serving

**Requirement:** The HTTP server shall serve DASH initialization segments correctly.

**Acceptance Criteria:**

- [ ] 3.4.1 When `init.mp4` is requested and exists, the server shall return HTTP 200 status.
- [ ] 3.4.2 The server shall set `Content-Type: video/mp4` for initialization segment responses.
- [ ] 3.4.3 The server shall include CORS headers for initialization segment responses.

---

### 4. Worker-Level Streaming Mode Detection

#### 4.1 LinearWorker DASH Support

**Requirement:** The LinearWorker shall support DASH streaming based on configuration.

**Acceptance Criteria:**

- [ ] 4.1.1 When `output.mode` is `http_dash`, LinearWorker shall build DASH FFmpeg arguments instead of HLS.
- [ ] 4.1.2 The LinearWorker shall use the configured `output.dash` settings for DASH streaming.
- [ ] 4.1.3 The LinearWorker shall create the output directory for DASH segments if it does not exist.
- [ ] 4.1.4 The LinearWorker shall pass transcoding arguments to the DASH FFmpeg builder when transcoding is enabled.
- [ ] 4.1.5 When `output.mode` is `http_hls`, LinearWorker shall continue to use existing HLS behavior unchanged.

#### 4.2 VODWorker DASH Support

**Requirement:** The VODWorker shall support DASH streaming based on configuration.

**Acceptance Criteria:**

- [ ] 4.2.1 When `output.mode` is `http_dash`, VODWorker shall build DASH FFmpeg arguments instead of HLS.
- [ ] 4.2.2 The VODWorker shall use the configured `output.dash` settings for DASH streaming.
- [ ] 4.2.3 The VODWorker shall handle subtitle integration with DASH streaming when transcoding is enabled.
- [ ] 4.2.4 The VODWorker shall properly manage DASH segment copying from temp to output directory.
- [ ] 4.2.5 When `output.mode` is `http_hls`, VODWorker shall continue to use existing HLS behavior unchanged.

#### 4.3 DynamicWorker DASH Support

**Requirement:** The DynamicWorker shall support DASH streaming based on configuration.

**Acceptance Criteria:**

- [ ] 4.3.1 When `output.mode` is `http_dash`, DynamicWorker shall build DASH FFmpeg arguments instead of HLS.
- [ ] 4.3.2 The DynamicWorker shall use the configured `output.dash` settings for DASH streaming.
- [ ] 4.3.3 The DynamicWorker shall handle DASH streaming during standby mode.
- [ ] 4.3.4 The DynamicWorker shall handle DASH streaming during VOD interruption mode.
- [ ] 4.3.5 The DynamicWorker shall handle DASH streaming during scheduled content mode.
- [ ] 4.3.6 When `output.mode` is `http_hls`, DynamicWorker shall continue to use existing HLS behavior unchanged.

#### 4.4 BaseWorker Integration

**Requirement:** The BaseWorker shall provide shared utilities for DASH streaming.

**Acceptance Criteria:**

- [ ] 4.4.1 The BaseWorker shall support DASH output directory initialization.
- [ ] 4.4.2 The BaseWorker shall properly handle FFmpeg process monitoring for DASH streams.
- [ ] 4.4.3 The BaseWorker watchdog shall work with DASH FFmpeg processes.

---

### 5. Transcoding Integration

#### 5.1 Transcoding Service DASH Compatibility

**Requirement:** The TranscodingService shall work with DASH streaming.

**Acceptance Criteria:**

- [ ] 5.1.1 The TranscodingService shall provide encoding arguments compatible with DASH output format.
- [ ] 5.1.2 When transcoding is disabled, the system shall use copy mode for both video and audio in DASH streaming.
- [ ] 5.1.3 When transcoding is enabled with hardware acceleration (NVENC, QSV, AMF), the system shall generate DASH-compatible output.
- [ ] 5.1.4 The system shall apply video scaling filters when configured, maintaining DASH compatibility.

#### 5.2 Subtitle Integration

**Requirement:** The system shall support subtitle integration with DASH streaming when transcoding is enabled.

**Acceptance Criteria:**

- [ ] 5.2.1 When subtitles are enabled and an external subtitle file exists, the system shall embed subtitles into the video stream for DASH output.
- [ ] 5.2.2 The system shall calculate appropriate subtitle font scaling based on output resolution for DASH streams.
- [ ] 5.2.3 When no subtitle file is found, the system shall proceed with DASH streaming without subtitles.

---

### 6. Error Handling and Recovery

#### 6.1 Configuration Errors

**Requirement:** The system shall handle configuration errors gracefully.

**Acceptance Criteria:**

- [ ] 6.1.1 When `output.mode` is `http_dash` but no `dash` configuration section exists, the system shall use default DASH values and log a warning.
- [ ] 6.1.2 When `output.dash.segment_duration` is outside the valid range (1-30), the system shall clamp to valid range and log a warning.
- [ ] 6.1.3 When `output.dash.playlist_size` is less than 2, the system shall use minimum value of 2 and log a warning.

#### 6.2 FFmpeg Errors

**Requirement:** The system shall handle FFmpeg errors during DASH streaming.

**Acceptance Criteria:**

- [ ] 6.2.1 When FFmpeg exits with non-zero status during DASH streaming, the system shall log the error with context.
- [ ] 6.2.2 When FFmpeg fails to generate DASH segments, the system shall log detailed error output from FFmpeg stderr.
- [ ] 6.2.3 When the watchdog detects FFmpeg is frozen, the system shall kill the process and log the timeout event.

#### 6.3 HTTP Server Errors

**Requirement:** The HTTP server shall handle errors gracefully when serving DASH content.

**Acceptance Criteria:**

- [ ] 6.3.1 When a requested DASH file does not exist, the server shall return HTTP 404 without crashing.
- [ ] 6.3.2 When a permission error occurs reading a DASH file, the server shall retry up to 20 times before returning HTTP 503.
- [ ] 6.3.3 When an unexpected error occurs serving DASH content, the server shall log the error and return appropriate HTTP status.

#### 6.4 Segment Write Conflicts

**Requirement:** The system shall handle concurrent access to segments being written by FFmpeg.

**Acceptance Criteria:**

- [ ] 6.4.1 When a client requests a segment that FFmpeg is currently writing, the server shall wait for the write to complete.
- [ ] 6.4.2 When a segment remains at size 0 after maximum retries, the server shall return HTTP 503.
- [ ] 6.4.3 The server shall not serve partial or corrupted segment data.

---

### 7. Segment and Manifest Management

#### 7.1 Segment File Naming

**Requirement:** The system shall generate DASH segments with consistent naming conventions.

**Acceptance Criteria:**

- [ ] 7.1.1 The system shall name media segments following the pattern `seg_{number}.m4s`.
- [ ] 7.1.2 The system shall name the initialization segment `init.mp4`.
- [ ] 7.1.3 The system shall name the manifest file `manifest.mpd`.

#### 7.2 Segment Cleanup

**Requirement:** The system shall manage segment cleanup to prevent disk space exhaustion.

**Acceptance Criteria:**

- [ ] 7.2.1 The system shall maintain a sliding window of segments based on `playlist_size` configuration.
- [ ] 7.2.2 The system shall delete old segments that fall outside the sliding window.
- [ ] 7.2.3 The system shall preserve the initialization segment (`init.mp4`) during cleanup.

#### 7.3 Manifest Updates

**Requirement:** The system shall update the DASH manifest as new segments are generated.

**Acceptance Criteria:**

- [ ] 7.3.1 The MPD manifest shall reflect only the segments within the sliding window.
- [ ] 7.3.2 The manifest shall be regenerated when segments are added or removed.
- [ ] 7.3.3 The manifest shall include proper DASH namespace declarations.

---

### 8. Logging and Monitoring

#### 8.1 DASH Streaming Logs

**Requirement:** The system shall provide informative logging for DASH streaming operations.

**Acceptance Criteria:**

- [ ] 8.1.1 The system shall log when DASH streaming mode is activated for a channel.
- [ ] 8.1.2 The system shall log the FFmpeg command used for DASH streaming at startup.
- [ ] 8.1.3 The system shall log when DASH segments are created (optional, debug level).
- [ ] 8.1.4 The system shall log errors specific to DASH streaming with appropriate severity.

#### 8.2 Now Playing Tracking

**Requirement:** The system shall track currently playing content for DASH streams.

**Acceptance Criteria:**

- [ ] 8.2.1 The system shall update the now playing status when streaming via DASH.
- [ ] 8.2.2 The system shall log "NOW PLAYING" messages for DASH streams similar to HLS.
- [ ] 8.2.3 The stats API shall report currently playing content for DASH channels.

---

### 9. Testing Requirements

#### 9.1 Unit Tests

**Requirement:** The system shall have comprehensive unit test coverage for DASH functionality.

**Acceptance Criteria:**

- [ ] 9.1.1 Unit tests shall cover DASH configuration parsing and validation.
- [ ] 9.1.2 Unit tests shall cover DASH FFmpeg argument building.
- [ ] 9.1.3 Unit tests shall cover HTTP server DASH file serving.
- [ ] 9.1.4 Unit tests shall cover mode selection logic in workers.
- [ ] 9.1.5 Unit test coverage for new DASH code paths shall be at least 90%.

#### 9.2 Integration Tests

**Requirement:** The system shall have integration tests for DASH streaming end-to-end.

**Acceptance Criteria:**

- [ ] 9.2.1 Integration tests shall verify complete DASH streaming pipeline for LinearWorker.
- [ ] 9.2.2 Integration tests shall verify complete DASH streaming pipeline for VODWorker.
- [ ] 9.2.3 Integration tests shall verify complete DASH streaming pipeline for DynamicWorker.
- [ ] 9.2.4 Integration tests shall verify HTTP server serves valid MPD manifests.
- [ ] 9.2.5 Integration tests shall verify DASH playback with reference player (dash.js or similar).

#### 9.3 Property-Based Tests

**Requirement:** The system shall have property-based tests for DASH configuration validation.

**Acceptance Criteria:**

- [ ] 9.3.1 Property tests shall verify segment duration is always within valid bounds.
- [ ] 9.3.2 Property tests shall verify output path always contains channel name.
- [ ] 9.3.3 Property tests shall verify mode selection returns correct format flag.

---

### 10. Documentation Requirements

#### 10.1 Configuration Documentation

**Requirement:** The system shall provide documentation for DASH configuration options.

**Acceptance Criteria:**

- [ ] 10.1.1 Documentation shall describe all DASH configuration properties and their defaults.
- [ ] 10.1.2 Documentation shall provide example configurations for DASH streaming.
- [ ] 10.1.3 Documentation shall explain the differences between HLS and DASH modes.
- [ ] 10.1.4 Documentation shall include migration instructions for existing users.

#### 10.2 API Documentation

**Requirement:** The system shall document the DASH streaming API endpoints.

**Acceptance Criteria:**

- [ ] 10.2.1 Documentation shall describe the DASH manifest endpoint URL format.
- [ ] 10.2.2 Documentation shall describe the DASH segment endpoint URL format.
- [ ] 10.2.3 Documentation shall list the HTTP headers returned for DASH content.

---

## Dependencies

### External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| FFmpeg | 4.0+ | DASH muxer support |
| FFmpeg | 5.0+ (recommended) | Advanced DASH features |

### Internal Dependencies

| Component | Location | Purpose |
|-----------|----------|---------|
| Config | `akiratv/config.py` | Configuration management |
| TranscodingService | `akiratv/workers/transcoding.py` | Encoding argument generation |
| HttpServer | `akiratv/server/http_server.py` | HTTP file serving |
| LinearWorker | `akiratv/workers/linear_worker.py` | Linear channel streaming |
| VODWorker | `akiratv/workers/vod_worker.py` | VOD channel streaming |
| DynamicWorker | `akiratv/workers/dynamic_worker.py` | Dynamic channel streaming |
| BaseWorker | `akiratv/workers/base_worker.py` | Shared worker functionality |

---

## Glossary

| Term | Definition |
|------|------------|
| DASH | Dynamic Adaptive Streaming over HTTP - ISO standard for adaptive bitrate streaming |
| MPD | Media Presentation Description - XML manifest for DASH streams |
| HLS | HTTP Live Streaming - Apple's adaptive streaming protocol |
| M3U8 | Playlist format for HLS streams |
| Segment | Individual media chunk (`.ts` for HLS, `.m4s` for DASH) |
| Manifest | Metadata file describing available segments (M3U8 for HLS, MPD for DASH) |
| Adaptation Set | Group of representations of the same content in DASH |
