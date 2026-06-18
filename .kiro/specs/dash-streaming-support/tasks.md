# Implementation Plan: DASH Streaming Support

## Overview

Implement DASH (Dynamic Adaptive Streaming over HTTP) streaming support as an alternative to HLS, following the design document and requirements.

---

## Tasks

### Phase 1: Configuration Schema Extension

### 1.1 Add DASH configuration to default config

- [ ] 1.1.1 Add `dash` section to `DEFAULT_CONFIG` in `akiratv/config.py` with default values (segment_duration: 6, fragment_duration: 6, min_buffer_time: 2.0, playlist_size: 4)
- [ ] 1.1.2 Update `_write_default()` to include DASH section in generated config files
- [ ] 1.1.3 Verify existing configs without `dash` section load without errors

### 1.2 Add streaming mode validation

- [ ] 1.2.1 Add `get_dash_config()` method to `Config` class that returns DASH config with defaults
- [ ] 1.2.2 Add `validate_streaming_mode()` method to validate `output.mode` values
- [ ] 1.2.3 Add `get_streaming_output_path()` method that works with both HLS and DASH modes

### 1.3 Write unit tests for configuration

- [ ] 1.3.1 Test DASH config defaults are applied when missing
- [ ] 1.3.2 Test mode validation accepts http_hls, http_dash, ram_http
- [ ] 1.3.3 Test invalid mode defaults to http_hls with warning

---

## Phase 2: FFmpeg Argument Building

### 2.1 Create DASH arguments builder module

- [ ] 2.1.1 Create `akiratv/workers/dash_builder.py` with `build_dash_ffmpeg_args()` function
- [ ] 2.1.2 Implement segment duration and fragment duration configuration
- [ ] 2.1.3 Implement playlist window size configuration
- [ ] 2.1.4 Implement adaptation sets configuration for video and audio

### 2.2 Implement DASH encoding parameters

- [ ] 2.2.1 Add video encoding args (`-c:v libx264`, `-bf 1`, `-keyint_min`, `-g`, `-sc_threshold 0`)
- [ ] 2.2.2 Add audio encoding args (`-c:a aac`)
- [ ] 2.2.3 Support stream copy mode when transcoding is disabled
- [ ] 2.2.4 Support hardware acceleration encoders (NVENC, QSV, AMF) for DASH

### 2.3 Write unit tests for DASH builder

- [ ] 2.3.1 Test DASH args are generated correctly with default config
- [ ] 2.3.2 Test DASH args with custom segment duration
- [ ] 2.3.3 Test DASH args with transcoding enabled vs disabled
- [ ] 2.3.4 Test output path contains correct manifest filename

---

## Phase 3: HTTP Server DASH Handling

### 3.1 Add DASH route handler

- [ ] 3.1.1 Add `dash_handler()` method to `HttpServer` class
- [ ] 3.1.2 Register route `/dash/{path:.+}` in `setup_routes()`
- [ ] 3.1.3 Implement path resolution for DASH files

### 3.2 Implement MPD manifest serving

- [ ] 3.2.1 Serve `.mpd` files with `Content-Type: application/dash+xml`
- [ ] 3.2.2 Add CORS headers for DASH manifest responses
- [ ] 3.2.3 Set appropriate cache headers for manifests
- [ ] 3.2.4 Return HTTP 404 for missing manifests

### 3.3 Implement DASH segment serving

- [ ] 3.3.1 Serve `.m4s` segments with `Content-Type: video/mp4`
- [ ] 3.3.2 Serve `init.mp4` initialization segments correctly
- [ ] 3.3.3 Implement retry logic for segments being written (size 0 check)
- [ ] 3.3.4 Add CORS headers for segment responses

### 3.4 Write unit tests for HTTP server

- [ ] 3.4.1 Test MPD manifest returns correct content type
- [ ] 3.4.2 Test segment returns correct content type
- [ ] 3.4.3 Test missing file returns 404
- [ ] 3.4.4 Test retry logic for locked segments

---

## Phase 4: LinearWorker DASH Support

### 4.1 Update LinearWorker for DASH

- [ ] 4.1.1 Modify `_build_ffmpeg_args()` to check `output.mode` and call appropriate builder
- [ ] 4.1.2 Add `_build_dash_args()` method to LinearWorker
- [ ] 4.1.3 Integrate transcoding service with DASH builder
- [ ] 4.1.4 Verify HLS path unchanged when mode is http_hls

### 4.2 Test LinearWorker DASH streaming

- [ ] 4.2.1 Test LinearWorker produces DASH output when mode is http_dash
- [ ] 4.2.2 Test LinearWorker still produces HLS when mode is http_hls
- [ ] 4.2.3 Test segment cleanup works for DASH segments

---

## Phase 5: VODWorker DASH Support

### 5.1 Update VODWorker for DASH

- [ ] 5.1.1 Modify `_build_ffmpeg_args()` to check `output.mode` and call appropriate builder
- [ ] 5.1.2 Add DASH-specific args building with subtitle support
- [ ] 5.1.3 Update segment copy thread to handle DASH segments (.m4s) and manifest (.mpd)
- [ ] 5.1.4 Verify HLS path unchanged when mode is http_hls

### 5.2 Test VODWorker DASH streaming

- [ ] 5.2.1 Test VODWorker produces DASH output when mode is http_dash
- [ ] 5.2.2 Test VODWorker subtitle integration with DASH
- [ ] 5.2.3 Test segment copy from temp to output directory for DASH

---

## Phase 6: DynamicWorker DASH Support

### 6.1 Update DynamicWorker for DASH

- [ ] 6.1.1 Modify `_play_scheduled_content()` to support DASH mode
- [ ] 6.1.2 Modify `_start_standby()` to support DASH mode
- [ ] 6.1.3 Modify `_switch_to_vod()` to support DASH mode
- [ ] 6.1.4 Verify HLS path unchanged when mode is http_hls

### 6.2 Test DynamicWorker DASH streaming

- [ ] 6.2.1 Test DynamicWorker scheduled content with DASH
- [ ] 6.2.2 Test DynamicWorker standby mode with DASH
- [ ] 6.2.3 Test DynamicWorker VOD interruption with DASH

---

## Phase 7: Integration Testing

### 7.1 End-to-end DASH streaming tests

- [ ] 7.1.1 Test complete LinearWorker pipeline with DASH mode
- [ ] 7.1.2 Test complete VODWorker pipeline with DASH mode
- [ ] 7.1.3 Test complete DynamicWorker pipeline with DASH mode

### 7.2 DASH playback verification

- [ ] 7.2.1 Verify MPD manifest is valid XML
- [ ] 7.2.2 Verify segments are playable with ffprobe
- [ ] 7.2.3 Test playback with dash.js reference player

### 7.3 Mode switching tests

- [ ] 7.3.1 Test switching from HLS to DASH mode via config reload
- [ ] 7.3.2 Test switching from DASH to HLS mode via config reload
- [ ] 7.3.3 Verify no server restart required for mode switch

---

## Phase 8: Error Handling and Recovery

### 8.1 Configuration error handling

- [ ] 8.1.1 Handle missing DASH config section gracefully with defaults
- [ ] 8.1.2 Validate and clamp segment_duration to valid range (1-30)
- [ ] 8.1.3 Validate and clamp playlist_size to minimum of 2

### 8.2 FFmpeg error handling

- [ ] 8.2.1 Log DASH-specific FFmpeg errors with context
- [ ] 8.2.2 Handle watchdog timeout for frozen DASH processes
- [ ] 8.2.3 Implement graceful fallback behavior on encoding failure

### 8.3 HTTP server error handling

- [ ] 8.3.1 Return appropriate HTTP status codes for DASH errors
- [ ] 8.3.2 Implement retry logic with exponential backoff for locked files
- [ ] 8.3.3 Prevent serving partial or corrupted segment data

---

## Phase 9: Documentation

### 9.1 Update configuration documentation

- [ ] 9.1.1 Document DASH configuration properties in README or config guide
- [ ] 9.1.2 Add example DASH configuration to sample config
- [ ] 9.1.3 Document differences between HLS and DASH modes

### 9.2 Update API documentation

- [ ] 9.2.1 Document DASH endpoint URLs
- [ ] 9.2.2 Document HTTP headers for DASH content
- [ ] 9.2.3 Add migration guide for existing HLS users

---

## Task Summary

| Phase | Description | Tasks |
|-------|-------------|-------|
| 1 | Configuration Schema Extension | 9 |
| 2 | FFmpeg Argument Building | 11 |
| 3 | HTTP Server DASH Handling | 12 |
| 4 | LinearWorker DASH Support | 7 |
| 5 | VODWorker DASH Support | 7 |
| 6 | DynamicWorker DASH Support | 7 |
| 7 | Integration Testing | 8 |
| 8 | Error Handling and Recovery | 9 |
| 9 | Documentation | 6 |
| **Total** | | **76** |

---

## Task Dependency Graph

```json
{
  "waves": [
    {
      "wave": 1,
      "tasks": ["1.1.1", "1.1.2", "1.1.3", "1.2.1", "1.2.2", "1.2.3", "1.3.1", "1.3.2", "1.3.3"]
    },
    {
      "wave": 2,
      "tasks": ["2.1.1", "2.1.2", "2.1.3", "2.1.4", "2.2.1", "2.2.2", "2.2.3", "2.2.4", "2.3.1", "2.3.2", "2.3.3", "2.3.4", "3.1.1", "3.1.2", "3.1.3", "3.2.1", "3.2.2", "3.2.3", "3.2.4", "3.3.1", "3.3.2", "3.3.3", "3.3.4", "3.4.1", "3.4.2", "3.4.3", "3.4.4"]
    },
    {
      "wave": 3,
      "tasks": ["4.1.1", "4.1.2", "4.1.3", "4.1.4", "4.2.1", "4.2.2", "4.2.3", "5.1.1", "5.1.2", "5.1.3", "5.1.4", "5.2.1", "5.2.2", "5.2.3", "6.1.1", "6.1.2", "6.1.3", "6.1.4", "6.2.1", "6.2.2", "6.2.3", "8.1.1", "8.1.2", "8.1.3", "8.2.1", "8.2.2", "8.2.3", "8.3.1", "8.3.2", "8.3.3"]
    },
    {
      "wave": 4,
      "tasks": ["7.1.1", "7.1.2", "7.1.3", "7.2.1", "7.2.2", "7.2.3", "7.3.1", "7.3.2", "7.3.3"]
    },
    {
      "wave": 5,
      "tasks": ["9.1.1", "9.1.2", "9.1.3", "9.2.1", "9.2.2", "9.2.3"]
    }
  ]
}
```

---

## Notes

- **No new dependencies required** — DASH support uses the existing FFmpeg installation. Verify DASH muxer is available with `ffmpeg -formats | grep dash`.
- **Backward compatibility is mandatory** — all changes must leave existing HLS behavior completely unchanged when `output.mode` is `http_hls`.
- **Stream copy mode** — when transcoding is disabled, DASH uses `-c:v copy -c:a copy`. Note that stream copy with DASH requires the source to already be in a fragmented MP4-compatible format; if FFmpeg errors occur, transcoding must be enabled.
- **Hardware encoders** — NVENC, QSV, and AMF all produce DASH-compatible output. Test each encoder path independently.
- **Segment write race condition** — the HTTP server retry logic (20 retries × 0.5s) is critical for smooth playback. Do not reduce retry count.
- **Testing reference player** — use [dash.js](https://reference.dashif.org/dash.js/) for browser-based playback verification.
