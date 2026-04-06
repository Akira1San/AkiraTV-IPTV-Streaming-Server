# Android Kotlin Phase 1 - Remaining Tasks

## Overview

Phase 1 of the Android Kotlin rewrite has been completed and the project now **compiles successfully**. This document outlines the current state and remaining tasks for full API parity with the Python version.

## Build Status

✅ **BUILD SUCCESSFUL** - The Android project compiles with `gradlew assembleDebug`

## Completed Phase 1 Tasks ✅

| Task | Status | File |
|------|--------|------|
| 1.1 Update build.gradle.kts with Ktor and FFmpeg-kit | ✅ Complete | `app/build.gradle.kts` |
| 1.2 Create package structure: `com.akiratv.android.core` | ✅ Complete | `core/` directory |
| 1.3 Create package structure: `com.akiratv.android.server` | ✅ Complete | `server/` directory |
| 1.4 Create package structure: `com.akiratv.android.hls` | ✅ Complete | `hls/` directory |
| 1.5 Configure AndroidManifest.xml | ✅ Complete | `AndroidManifest.xml` |

## Fixes Applied

The following compilation errors were fixed:

1. **Scheduler.kt** - Added `getGuide()` method for TV guide functionality
2. **StatsManager.kt** - Added `getStats()` extension function for monitoring
3. **AkiraTVApplication.kt** - Fixed HLS ContentType, added getStats import
4. **InventoryManager.kt** - Added `getVideoByName()` method
5. **VodRoutes.kt** - Fixed method calls and parameters
6. **StaticContentRouting.kt** - Fixed routing extension function
7. **WebSocketRouting.kt** - Simplified to placeholder (routes inlined)
8. **build.gradle.kts** - Added packaging exclusions for Netty dependencies

## Incomplete Route Files ⚠️

The following route files exist but need full implementation:

### Route Files Status

| Route File | Status | Notes |
|------------|--------|-------|
| `ChannelRoutes.kt` | ⚠️ Placeholder | Routes inlined in AkiraTVApplication.kt |
| `ConfigRoutes.kt` | ⚠️ Placeholder | Routes inlined in AkiraTVApplication.kt |
| `GuideRoutes.kt` | ⚠️ Placeholder | Routes inlined in AkiraTVApplication.kt |
| `HlsRoutes.kt` | ⚠️ Placeholder | Routes inlined in AkiraTVApplication.kt |
| `LibraryRoutes.kt` | ⚠️ Placeholder | Not yet implemented |
| `LifecycleRoutes.kt` | ⚠️ Placeholder | Routes inlined in AkiraTVApplication.kt |
| `MonitoringRoutes.kt` | ⚠️ Placeholder | Routes inlined in AkiraTVApplication.kt |
| `VodRoutes.kt` | ⚠️ Partial | Basic implementation exists, needs enhancement |
| `StaticContentRouting.kt` | ⚠️ Partial | Basic implementation exists |
| `WebSocketRouting.kt` | ⚠️ Placeholder | Simplified to placeholder |

## API Endpoints Summary

### Currently Implemented in AkiraTVApplication.kt

| Method | Endpoint | Status |
|--------|----------|--------|
| GET | `/api/channels` | ✅ Implemented |
| GET | `/api/channels/{name}` | ✅ Implemented |
| GET | `/api/config` | ✅ Implemented |
| GET | `/api/library` | ✅ Implemented |
| GET | `/api/guide` | ✅ Implemented |
| POST | `/api/lifecycle/start` | ✅ Implemented |
| POST | `/api/lifecycle/stop` | ✅ Implemented |
| GET | `/api/lifecycle/status` | ✅ Implemented |
| GET | `/api/monitoring/stats` | ✅ Implemented |
| GET | `/stream/{channel}.m3u8` | ✅ Implemented (stub) |
| GET | `/health` | ✅ Implemented |

### Endpoints Still Needed

From the Python API, these endpoints need implementation:

- **Channels**: `/api/channels/urls`, `/api/channels/{ch}/enable`, `/api/channels/{ch}/disable`, `/api/channels/{ch}/play`, `/api/channels/{ch}/stop`, `/api/channels/{ch}/start`, `/api/channels/{ch}/restart`, `/api/channels/{ch}/reload-schedule`, DELETE `/api/channels/{ch}`
- **Config**: PATCH `/api/config`, POST `/api/config/save`, GET `/api/config/defaults`
- **Guide**: GET `/api/guide/weekly`, GET `/api/guide/date/{date}`
- **VOD**: GET `/api/vod/library`, GET `/api/vod/video/{id}`, `/api/vod/positions`, `/api/vod/position/{path}`
- **Library**: POST `/api/library/scan`, GET `/api/library/collections`
- **WebSocket**: Full WebSocket implementation needed

## Next Steps

### Priority 1: Complete ChannelRoutes
Implement full channel management endpoints for:
- Channel enable/disable
- Channel play/stop
- Channel URL generation

### Priority 2: HLS Streaming
Implement proper HLS segment generation:
- Connect `HlsSegmentGenerator` to streaming endpoints
- Implement live HLS for channel playback

### Priority 3: WebSocket
Implement real-time updates via WebSocket:
- Channel status updates
- Playback notifications

### Priority 4: VOD Enhancement
Complete VOD functionality:
- Video library from collections
- Video position persistence
- Video details

## Files Modified

```
AkiraTV-Android/
├── app/
│   ├── build.gradle.kts                    # Added packaging exclusions
│   └── src/main/java/com/akiratv/android/
│       ├── core/
│       │   ├── Scheduler.kt                # Added getGuide()
│       │   ├── StatsManager.kt             # Added getStats()
│       │   └── InventoryManager.kt         # Added getVideoByName()
│       └── server/
│           ├── AkiraTVApplication.kt        # Fixed ContentType, imports
│           ├── StaticContentRouting.kt     # Fixed routing
│           ├── VodRoutes.kt               # Fixed method calls
│           └── WebSocketRouting.kt        # Simplified placeholder
```

## Notes

- Routes are currently inlined in `AkiraTVApplication.kt` for simplicity
- Full route modularization can be done later
- WebSocket implementation simplified to HTTP endpoints for now
- HLS streaming is stubbed - needs FFmpeg integration

---

*Last Updated: 2026-03-19*
*Build Status: ✅ SUCCESSFUL*
