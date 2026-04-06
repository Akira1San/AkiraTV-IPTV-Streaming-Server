# AkiraTV Kotlin Rewrite Plan

## Overview

Rewrite AkiraTV from Python to **Kotlin** for Android TV boxes. This replaces the previous JavaScript/Node.js approach which was blocked by Android SELinux.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Android TV Box (MECOOL)                      │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │  AkiraTV App (Kotlin)                                   │   │
│   │                                                          │   │
│   │  ┌─────────────────┐    ┌──────────────────────────┐  │   │
│   │  │ Ktor HTTP       │    │ FFmpeg-kit                │  │   │
│   │  │ Server          │    │ HLS Segment Generator     │  │   │
│   │  │ - Web UI        │    │ - Creates .ts segments    │  │   │
│   │  │ - API Endpoints │    │ - Writes to USB           │  │   │
│   │  │ - Stream URLs   │    │ - Copy (no transcoding)   │  │   │
│   │  └─────────────────┘    └──────────────────────────┘  │   │
│   │                                                          │   │
│   │  ┌─────────────────┐    ┌──────────────────────────┐  │   │
│   │  │ Kotlin Core     │    │ USB Storage              │  │   │
│   │  │ - Channels      │◄──►│ - Input: videos          │  │   │
│   │  │ - Scheduling    │    │ - Output: HLS segments   │  │   │
│   │  │ - Config        │    │ - User: channels/sched   │  │   │
│   │  └─────────────────┘    └──────────────────────────┘  │   │
│   └──────────────────────────────────────────────────────────┘   │
│                              │                                     │
│                              ▼                                     │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │  Kodi on same TV                                         │   │
│   │  - Plays HLS streams from AkiraTV server                 │   │
│   │  - Access via: http://IP:8081/channel/{name}.m3u8        │   │
│   └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Why Kotlin + FFmpeg-kit?

| Problem | Solution |
|---------|----------|
| Node.js blocked by SELinux | Kotlin runs natively |
| FFmpeg binary blocked | FFmpeg-kit is a library, not binary |
| Python dependencies complex | Kotlin stdlib + minimal deps |
| ChaQuPy repository inaccessible | Kotlin has no such issue |

---

## Dependencies

### build.gradle.kts

```kotlin
dependencies {
    // Ktor - HTTP Server
    implementation("io.ktor:ktor-server-core:2.3.7")
    implementation("io.ktor:ktor-server-netty:2.3.7")
    implementation("io.ktor:ktor-server-content-negotiation:2.3.7")
    implementation("io.ktor:ktor-serialization-gson:2.3.7")
    implementation("io.ktor:ktor-server-partial-content:2.3.7")
    implementation("io.ktor:ktor-server-websockets:2.3.7")
    implementation("io.ktor:ktor-server-default-headers:2.3.7")
    implementation("io.ktor:ktor-server-cors:2.3.7")
    implementation("io.ktor:ktor-server-call-logging:2.3.7")
    
    // FFmpeg-kit - HLS Segment Generation
    implementation("com.arthenica:ffmpeg-kit-full:6.0-2")
    
    // JSON
    implementation("com.google.code.gson:gson:2.10.1")
    
    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.7.3")
    
    // AndroidX
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("androidx.activity:activity-ktx:1.8.2")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
    implementation("androidx.lifecycle:lifecycle-service:2.7.0")
    
    // Compose (existing)
    implementation(platform("androidx.compose:bom:2024.01.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling.preview")
    implementation("androidx.tv:tv-foundation:1.0.0")
    implementation("androidx.tv:tv-material:1.0.0")
}
```

---

## Implementation Tasks

### Phase 1: Project Setup

- [x] 1.1 Update build.gradle.kts with Ktor and FFmpeg-kit dependencies
- [x] 1.2 Create package structure: `com.akiratv.android.core`
- [x] 1.3 Create package structure: `com.akiratv.android.server`
- [x] 1.4 Create package structure: `com.akiratv.android.hls`
- [x] 1.5 Configure AndroidManifest.xml with required permissions

### Phase 2: Core Engine (Port from Python)

- [x] 2.1 Create `AkiraTVEngine.kt` - Main engine class
- [x] 2.2 Create `ChannelManager.kt` - Channel management
- [x] 2.3 Create `ConfigManager.kt` - Config loading/saving (JSON)
- [x] 2.4 Create `InventoryManager.kt` - Video library scanning
- [x] 2.5 Create `Scheduler.kt` - Scheduling logic
- [x] 2.6 Create `CollectionManager.kt` - Collection handling
- [x] 2.7 Create `VideoPositionManager.kt` - Resume positions
- [x] 2.8 Create `StatsManager.kt` - Viewer statistics

### Phase 3: HTTP Server (Ktor)

- [x] 3.1 Create `AkiraTVApplication.kt` - Ktor app configuration
- [x] 3.2 Create `ChannelRoutes.kt` - `/api/channels` endpoints
- [x] 3.3 Create `ConfigRoutes.kt` - `/api/config` endpoints
- [x] 3.4 Create `GuideRoutes.kt` - `/api/guide` endpoints
- [x] 3.5 Create `LibraryRoutes.kt` - `/api/library` endpoints
- [x] 3.6 Create `LifecycleRoutes.kt` - `/api/lifecycle` endpoints
- [x] 3.7 Create `MonitoringRoutes.kt` - `/api/monitoring` endpoints
- [x] 3.8 Create `VodRoutes.kt` - `/api/vod` endpoints
- [x] 3.9 Create `StaticContentRouting.kt` - Serve web UI from assets
- [x] 3.10 Create `WebSocketRouting.kt` - Real-time updates

### Phase 4: HLS Generation (FFmpeg-kit)

- [x] 4.1 Create `HlsSegmentGenerator.kt` - FFmpeg-kit wrapper
- [x] 4.2 Create `HlsSegmentWriter.kt` - Write segments to USB
- [x] 4.3 Implement copy-mode transcoding (no re-encode)
- [x] 4.4 Implement HLS playlist generation (.m3u8)
- [x] 4.5 Create channel streaming endpoints

### Phase 5: Android Integration

- [x] 5.1 Integrate existing `USBHelper.kt` for path detection
- [x] 5.2 Create `AkiraTVService.kt` - Foreground service
- [x] 5.3 Create `MainActivity.kt` - Start/Stop controls
- [x] 5.4 Integrate `SystemMonitor.kt` - Device monitoring
- [x] 5.5 Add startup receiver for auto-launch option

### Phase 6: Web UI

- [x] 6.1 Copy existing web UI files to assets
- [x] 6.2 Update API endpoints in JavaScript (if needed)
- [x] 6.3 Test web UI on Android

---

## API Endpoints to Implement

### Channels
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/channels` | List all channels |
| POST | `/api/channels` | Create channel |
| GET | `/api/channels/{name}` | Get channel info |
| PATCH | `/api/channels/{name}` | Update channel |
| DELETE | `/api/channels/{name}` | Delete channel |
| POST | `/api/channels/{name}/play` | Play video on channel |
| POST | `/api/channels/{name}/stop` | Stop channel |

### Config
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/config` | Get configuration |
| PATCH | `/api/config` | Update configuration |
| POST | `/api/config/save` | Save to disk |

### Guide
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/guide` | Get TV guide |
| GET | `/api/guide/weekly` | Get weekly guide |
| GET | `/api/guide/date/{date}` | Get guide for date |

### Lifecycle
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/lifecycle/start` | Start engine |
| POST | `/api/lifecycle/stop` | Stop engine |
| POST | `/api/lifecycle/restart` | Restart engine |
| GET | `/api/lifecycle/status` | Get status |

### Monitoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/monitoring/stats` | Get statistics |
| GET | `/api/monitoring/viewers` | Get viewer count |
| GET | `/api/monitoring/logs` | Get logs |

### Stream URLs
| Endpoint | Description |
|----------|-------------|
| `/stream/{channel}.m3u8` | HLS playlist |
| `/stream/{channel}/{segment}.ts` | HLS segment |

---

## FFmpeg-kit Usage

### HLS Generation Example

```kotlin
import com.arthenica.ffmpegkit.FFmpegKit
import com.arthenica.ffmpegkit.ReturnCode

class HlsSegmentGenerator {
    
    fun generateHlsSegments(
        inputPath: String,
        outputDir: String,
        segmentTime: Int = 6
    ): Boolean {
        // Copy mode: no transcoding, just remux to HLS
        val command = buildString {
            append("-i \"$inputPath\" ")
            append("-c:v copy ")       // Video: copy (no re-encode)
            append("-c:a copy ")       // Audio: copy (no re-encode)
            append("-f hls ")
            append("-hls_time $segmentTime ")
            append("-hls_list_size 4 ")
            append("-hls_segment_filename \"$outputDir/segment%03d.ts\" ")
            append("\"$outputDir/playlist.m3u8\"")
        }
        
        val session = FFmpegKit.execute(command)
        return ReturnCode.isSuccess(session.returnCode)
    }
    
    fun generateLiveHls(
        inputPath: String,
        outputDir: String,
        onSegment: (String) -> Unit
    ): Flow<String> = flow {
        // For live streaming, generate segments continuously
        val command = buildString {
            append("-re ")              // Read input at native frame rate
            append("-i \"$inputPath\" ")
            append("-c:v copy ")
            append("-c:a copy ")
            append("-f hls ")
            append("-hls_time 6 ")
            append("-hls_list_size 4 ")
            append("-hls_segment_filename \"$outputDir/segment%03d.ts\" ")
            append("\"$outputDir/playlist.m3u8\"")
        }
        
        FFmpegKit.executeAsync(command) { session ->
            // Handle completion
        }
    }
}
```

---

## USB Storage Paths

### Configuration

```kotlin
object StoragePaths {
    // USB paths (detected via USBHelper)
    lateinit var usbVideosPath: String
    lateinit var usbOutputPath: String  // HLS segments
    lateinit var usbUserPath: String     // channels, schedules
    
    fun initialize(context: Context) {
        val usbPath = USBHelper.getUSBPath(context)
        if (usbPath != null) {
            usbVideosPath = "$usbPath/AkiraTV/videos"
            usbOutputPath = "$usbPath/AkiraTV/output"
            usbUserPath = "$usbPath/AkiraTV/user"
        } else {
            // Fallback to internal storage
            usbVideosPath = "${context.filesDir}/videos"
            usbOutputPath = "${context.filesDir}/output"
            usbUserPath = "${context.filesDir}/user"
        }
    }
}
```

---

## File Structure

```
AkiraTV-Android/
├── app/
│   ├── src/main/
│   │   ├── java/com/akiratv/android/
│   │   │   ├── AkiraTVApplication.kt
│   │   │   ├── MainActivity.kt
│   │   │   ├── AkiraTVService.kt
│   │   │   │
│   │   │   ├── core/
│   │   │   │   ├── AkiraTVEngine.kt
│   │   │   │   ├── ChannelManager.kt
│   │   │   │   ├── ConfigManager.kt
│   │   │   │   ├── InventoryManager.kt
│   │   │   │   ├── Scheduler.kt
│   │   │   │   ├── CollectionManager.kt
│   │   │   │   ├── VideoPositionManager.kt
│   │   │   │   └── StatsManager.kt
│   │   │   │
│   │   │   ├── server/
│   │   │   │   ├── AkiraTVApplication.kt
│   │   │   │   ├── ChannelRoutes.kt
│   │   │   │   ├── ConfigRoutes.kt
│   │   │   │   ├── GuideRoutes.kt
│   │   │   │   ├── LifecycleRoutes.kt
│   │   │   │   ├── MonitoringRoutes.kt
│   │   │   │   ├── VodRoutes.kt
│   │   │   │   ├── StaticContentRouting.kt
│   │   │   │   └── WebSocketRouting.kt
│   │   │   │
│   │   │   └── hls/
│   │   │       ├── HlsSegmentGenerator.kt
│   │   │       ├── HlsSegmentWriter.kt
│   │   │       └── HlsPlaylistGenerator.kt
│   │   │
│   │   ├── assets/
│   │   │   ├── index.html
│   │   │   ├── app.js
│   │   │   ├── guide.html
│   │   │   ├── vod.html
│   │   │   ├── viewer.html
│   │   │   └── ... (other web UI files)
│   │   │
│   │   └── AndroidManifest.xml
│   │
│   └── build.gradle.kts
│
└── settings.gradle.kts
```

---

## Porting from Python

### Core Classes Mapping

| Python File | Kotlin Class | Status |
|-------------|--------------|--------|
| `core_api.py` | `AkiraTVEngine.kt` | Pending |
| `core.py` | `ChannelManager.kt` | Pending |
| `config.py` | `ConfigManager.kt` | Pending |
| `inventory.py` | `InventoryManager.kt` | Pending |
| `scheduler.py` | `Scheduler.kt` | Pending |
| `collections.py` | `CollectionManager.kt` | Pending |
| `video_positions.py` | `VideoPositionManager.kt` | Pending |
| `stats.py` | `StatsManager.kt` | Pending |

### Routes Mapping

| Python Route | Kotlin Route | Status |
|--------------|--------------|--------|
| `routes/channels.py` | `ChannelRoutes.kt` | Pending |
| `routes/config.py` | `ConfigRoutes.kt` | Pending |
| `routes/guide.py` | `GuideRoutes.kt` | Pending |
| `routes/lifecycle.py` | `LifecycleRoutes.kt` | Pending |
| `routes/monitoring.py` | `MonitoringRoutes.kt` | Pending |
| `routes/vod.py` | `VodRoutes.kt` | Pending |

---

## Testing

### Build
```batch
cd AkiraTV-Android
gradlew.bat assembleDebug
```

### Install
```batch
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### Verify FFmpeg-kit
```kotlin
// Check FFmpeg-kit is available
val version = FFmpegKitConfig.getVersion()
Log.d("AkiraTV", "FFmpeg version: $version")
```

---

## Build Errors to Fix

The following errors prevent compilation and need to be addressed:

### 1. ChannelType Redeclaration
- **Files**: `AkiraTVEngine.kt:27`, `ChannelManager.kt:23`
- **Error**: `Redeclaration: enum class ChannelType : Enum<ChannelType>`
- **Fix**: Remove duplicate enum definition - keep it in one file only

### 2. CollectionManager Escape Sequences
- **File**: `CollectionManager.kt` (lines 329, 332, 336)
- **Error**: `Unsupported escape sequence`
- **Fix**: Fix invalid escape sequences in strings (e.g., `\w` should be `\\w` or raw string)

### 3. AkiraTVApplication WebSocket pingInterval
- **File**: `AkiraTVApplication.kt:58`
- **Error**: `None of the following candidates is applicable: var DefaultWebSocketServerSession.pingInterval`
- **Fix**: Update WebSocket configuration syntax for Ktor version

### 4. ConfigRoutes Private Access
- **File**: `ConfigRoutes.kt:221`
- **Error**: `Cannot access 'config': it is private in 'ConfigManager'`
- **Fix**: Make config property public or add getter method

### 5. GuideRoutes Issues
- **File**: `GuideRoutes.kt`
- **Error**: `Modifier 'private' is not applicable to 'local variable'` (line 29)
- **Error**: `2 type arguments expected for interface Map<K, out V>` (line 244)
- **Fix**: Remove invalid private modifier, fix Map generic types

### 6. WebSocketRouting Missing Imports
- **File**: `WebSocketRouting.kt`
- **Errors**: `Unresolved reference: serialization`, `buildJsonObject`, `Json`, `jsonPrimitive`, `put`
- **Fix**: Add missing Ktor serialization imports:
  ```kotlin
  import io.ktor.serialization.kotlinx.json.json
  import kotlinx.serialization.json.buildJsonObject
  import kotlinx.serialization.json.jsonPrimitive
  import kotlinx.serialization.json.put
  ```

---

## Notes

- **Copy-only mode**: FFmpeg-kit uses `-c:v copy -c:a copy` to remux without transcoding
- **USB storage**: All data stored on USB for capacity and durability
- **Web UI**: Reuse existing HTML/JS from Python version
- **No ExoPlayer needed**: Kodi plays the HLS streams, not the app itself

---

## Building the APK

### Prerequisites
- Android Studio (or command-line tools)
- Java JDK 17+
- Android SDK with API 34 (Android 14)

### Build Commands

```batch
cd AkiraTV-Android
gradlew.bat assembleDebug
```

The APK will be at: `app/build/outputs/apk/debug/app-debug.apk`

### Install to Device
```batch
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### Clean Build
```batch
gradlew.bat clean assembleDebug
```

---

## Remaining Tasks (Post-Launch)

### 7. Web UI Serving
- **Status**: ✅ FIXED
- **Issue**: Server returned "AkiraTV Server Running" instead of index.html
- **Fix**: Removed duplicate "/" route in AkiraTVApplication.kt, staticContentRouting now handles it

### 8. Default Port Conflict
- **Status**: ✅ FIXED
- **Issue**: Used port 8081 (conflicts with PC server)
- **Fix**: Changed to port 8082 in AkiraTVApplication.kt and AkiraTVService.kt

### 9. USB Detection
- **Status**: ✅ FIXED
- **Issue**: Shows "Warning: No USB drive detected" when USB is present
- **Fix**: Enhanced USBHelper.kt fallback paths for Android TV boxes (MECOOL, Amlogic, etc.)

### 10. Web UI Integration
- **Status**: ✅ FIXED
- **Issue**: Static content routing wasn't serving index.html properly
- **Fix**: Reordered routing in AkiraTVApplication.kt - staticContentRouting now handles "/" first

### 11. Display IP Address
- **Status**: ✅ FIXED
- **Issue**: Hardcoded port 8081 in URL display
- **Fix**: MainActivity.kt now uses AkiraTVService.SERVER_PORT constant
- **Fix**: Add IP address display to MainActivity UI

---

*Last Updated: 2026-03-20*
