# AkiraTV Android Port Plan

## Overview

Port AkiraTV from Python to run natively on Android TV boxes (MECOOL), eliminating the need for a power-hungry PC running 24/7.

## Target Device

- **MECOOL Android TV Box**
- **Copy-only mode** (no transcoding)
- **USB HDD** for video storage

## Goals

- ✅ Run AkiraTV directly on Android TV box
- ✅ No keyboard/mouse required - automatic operation
- ✅ Starts automatically on device boot
- ✅ Low power consumption (~5-10W vs 50-200W for PC)
- ✅ Installs as a regular Android APK
- ✅ Control via Web UI only (no custom Android UI needed)
- ✅ Use existing PC workflow for creating channels/schedules

---

## FFmpeg Requirement: NOT NEEDED

**FFmpeg is NOT required** because:
- Copy-only mode (direct streaming)
- No transcoding needed
- MECOOL supports most video formats natively
- HLS segments created via Node.js (no FFmpeg needed)

---

## Control Method: Web UI Only

```
┌──────────────────────────────────────────────────────────────────┐
│                    MECOOL Android TV Box                          │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  AkiraTV App (Background Service)                       │   │
│   │  - Starts on boot                                       │   │
│   │  - Runs Node.js server on port 8081                    │   │
│   │  - Shows notification "AkiraTV Running"                │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                    │
│   ┌──────────────────────────┴────────────────────────────┐   │
│   │  CONTROL: Web UI at http://IP:8081                     │   │
│   │  - Access from phone/tablet/laptop                     │   │
│   │  - Create channels, schedules, control playback         │   │
│   └─────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

Control AkiraTV from any device on your network using the existing web interface.

---

## Implementation Steps

### Phase 1: Port Python to JavaScript

#### Files to Convert

| Python File | Purpose | JavaScript Equivalent | Priority |
|-------------|---------|----------------------|----------|
| `akiratv/core.py` | Channel management, playback control | `src/core/channelManager.js` | HIGH |
| `akiratv/scheduler.py` | Schedule logic, programming | `src/scheduler/scheduler.js` | HIGH |
| `akiratv/api_server.py` | HTTP API endpoints | `src/server/apiRoutes.js` | HIGH |
| `akiratv/config.py` | Configuration loading/saving | `src/config/config.js` | MEDIUM |

#### Keep As-Is (Already JavaScript)
- `akiratv/static/app.js` - Frontend UI
- `akiratv/static/index.html` - Web interface
- `akiratv/static/guide.html` - TV Guide
- `akiratv/static/viewer.html` - Viewer interface

#### JavaScript Libraries Needed

```json
{
  "name": "akiratv-android",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.2",
    "ws": "^8.14.2",
    "cron-parser": "^4.9.0",
    "chokidar": "^3.5.3",
    "axios": "^1.6.0",
    "node-fetch": "^3.3.2",
    "mime-types": "^2.1.35",
    "find-my-way": "^7.7.0"
  }
}
```

#### No FFmpeg Needed
- Remove `fluent-ffmpeg` dependency
- Copy-only mode: serve files directly
- HLS segmentation: use Node.js streams

---

## Video Path & Collection Workflow

### USB Storage on Android

USB drives on Android are typically mounted at:
- `/storage/XXXX-XXXX/` - Most common
- `/mnt/usb/`
- `/storage/usb0/`

### Using Your Existing Method

```
PC (Collection Wizard)              MECOOL Android TV Box
┌──────────────────┐               ┌──────────────────┐
│ Create channels  │   ───────►   │ Copy JSON files  │
│ Create schedule  │    (USB)     │ to user/         │
│ Export JSON      │               │                  │
└──────────────────┘               └──────────────────┘
```

**Your workflow stays the same:**
1. Use PC to run Collection Wizard
2. Copy JSON files to USB drive
3. Plug USB into MECOOL
4. Copy files to app's user directory
5. Web UI accesses them normally

### Android Storage Structure

```
/storage/emulated/0/AkiraTV/
├── user/
│   ├── channels/
│   │   ├── live/
│   │   ├── anime/
│   │   └── horror/
│   ├── fast_schedules/
│   │   └── fast_schedule_*.json
│   └── config.json
├── output/          (HLS segments)
└── logs/
```

---

### Phase 2: Create Android Project

#### Project Structure

```
AkiraTV-Android/
├── app/
│   ├── src/main/
│   │   ├── assets/
│   │   │   ├── akiratv/         # Ported JavaScript files
│   │   │   │   ├── src/
│   │   │   │   ├── package.json
│   │   │   │   ├── user/        # User data (channels, config)
│   │   │   │   └── static/      # Web UI files
│   │   │   └── nodejs/          # Node.js runtime
│   │   ├── java/com/akiratv/
│   │   │   ├── AkiraTVService.kt # Background service (auto-start)
│   │   │   ├── AkiraTVApplication.kt
│   │   │   ├── BootReceiver.kt   # Boot completed receiver
│   │   │   └── NodeRunner.kt    # Node.js bridge
│   │   ├── res/
│   │   └── AndroidManifest.xml
├── gradle/
├── build.gradle
└── settings.gradle
```

#### Key Android Components

##### 1. AkiraTVService.kt (Auto-start on Boot)

```kotlin
package com.akiratv

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log

class AkiraTVService : Service() {
    companion object {
        private const val TAG = "AkiraTVService"
    }

    private var nodeProcess: Process? = null

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "AkiraTV Service starting...")
        startAkiraTV()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY // Restart if killed
    }

    private fun startAkiraTV() {
        // Extract assets if first run
        // Start Node.js with AkiraTV
        // Run as foreground service with notification
    }

    override fun onDestroy() {
        nodeProcess?.destroy()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
```

##### 2. AndroidManifest.xml (Boot Permission)

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    
    <!-- Boot completed permission -->
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />
    
    <application
        android:name=".AkiraTVApplication">
        
        <!-- Auto-start on boot -->
        <receiver
            android:name=".BootReceiver"
            android:enabled="true"
            android:exported="false">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
            </intent-filter>
        </receiver>
        
        <!-- AkiraTV Service -->
        <service
            android:name=".AkiraTVService"
            android:enabled="true"
            android:exported="false"
            android:foregroundServiceType="dataSync" />
        
    </application>
</manifest>
```

##### 3. BootReceiver.kt

```kotlin
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            val serviceIntent = Intent(context, AkiraTVService::class.java)
            context.startForegroundService(serviceIntent)
        }
    }
}
```

### Phase 3: FFmpeg Integration

#### Using FFmpegKit (Recommended)

```kotlin
// FFmpeg wrapper
object FFmpegHelper {
    
    fun transcode(input: String, output: String, callback: (Boolean) -> Unit) {
        FFmpegKit.executeAsync(
            "-i $input -c:v libx264 -preset fast -c:a aac $output",
            { session ->
                val returnCode = session.returnCode
                callback(returnCode.isValueSuccess)
            }
        )
    }
    
    fun createHLS(input: String, outputDir: String, callback: (String?) -> Unit) {
        val outputPath = "$outputDir/index.m3u8"
        FFmpegKit.executeAsync(
            "-i $input -c:v libx264 -preset fast -hls_time 10 -hls_segment_filename $outputDir/segment_%03d.ts $outputPath",
            { session ->
                callback(outputPath)
            }
        )
    }
}
```

#### Node.js FFmpeg Bridge

```javascript
// src/utils/ffmpeg.js
const { spawn } = require('child_process');

class FFmpegHelper {
    constructor(androidFFmpegPath = '/data/data/com.akiratv/files/ffmpeg') {
        this.ffmpegPath = androidFFmpegPath;
    }
    
    transcode(input, output, options = {}) {
        return new Promise((resolve, reject) => {
            const args = [
                '-i', input,
                '-c:v', 'libx264', '-preset', 'fast',
                '-c:a', 'aac',
                '-y', output
            ];
            
            const proc = spawn(this.ffmpegPath, args);
            let outputData = '';
            
            proc.stderr.on('data', (data) => outputData += data);
            proc.on('close', (code) => {
                if (code === 0) resolve(output);
                else reject(new Error(`FFmpeg exited with code ${code}`));
            });
        });
    }
}

module.exports = FFmpegHelper;
```

---

## Step-by-Step Implementation Plan

### Step 1: Analyze Current Python Code
- [ ] Read and understand `akiratv/core.py` - Core functionality
- [ ] Read and understand `akiratv/scheduler.py` - Scheduling logic
- [ ] Read and understand `akiratv/api_server.py` - API endpoints
- [ ] Identify all external dependencies

### Step 2: Create JavaScript Core
- [ ] Create `src/config/config.js` - Config loading
- [ ] Create `src/core/channelManager.js` - Channel management
- [ ] Create `src/scheduler/scheduler.js` - Schedule logic
- [ ] Create `src/server/apiRoutes.js` - Express routes

### Step 3: Set Up Android Project
- [ ] Install Android Studio
- [ ] Create new Android project
- [ ] Add FFmpegKit dependency
- [ ] Create AkiraTVService
- [ ] Add BootReceiver

### Step 4: Integrate Node.js
- [ ] Add Node.js runtime to assets
- [ ] Create Node.js bridge in Kotlin
- [ ] Test Node.js execution

### Step 5: Copy Web UI Files
- [ ] Copy `akiratv/static/` to `assets/akiratv/static/`
- [ ] Copy `akiratv/web_ui.html` to assets
- [ ] Update paths in HTML files

### Step 6: Testing
- [ ] Build debug APK
- [ ] Install on Android TV box
- [ ] Test auto-start on boot
- [ ] Test all functionality

---

## Files to Create/Modify

### New JavaScript Files
```
akiratv-js/
├── src/
│   ├── config/
│   │   └── config.js
│   ├── core/
│   │   ├── channelManager.js
│   │   ├── playback.js
│   │   └── collections.js
│   ├── scheduler/
│   │   ├── scheduler.js
│   │   └── fastScheduler.js
│   ├── server/
│   │   ├── app.js
│   │   └── routes/
│   │       ├── channels.js
│   │       ├── schedule.js
│   │       └── playlist.js
│   ├── workers/
│   │   ├── transcoding.js
│   │   └── metadata.js
│   └── utils/
│       ├── ffmpeg.js
│       ├── fileSystem.js
│       └── logger.js
├── static/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── user/
│   └── config.json
├── package.json
└── server.js
```

### Android Files
```
AkiraTV-Android/
├── app/src/main/
│   ├── java/com/akiratv/
│   │   ├── AkiraTVApplication.kt
│   │   ├── MainActivity.kt
│   │   ├── AkiraTVService.kt
│   │   ├── BootReceiver.kt
│   │   └── NodeRunner.kt
│   └── assets/
│       └── akiratv/
│           ├── (copied JS files)
│           └── (copied static files)
```

---

## Estimated Timeline

| Phase | Task | Effort |
|-------|------|--------|
| 1 | Port core to JavaScript | 8-16 hours |
| 2 | Set up Android project | 4-6 hours |
| 3 | Integrate Node.js | 4-8 hours |
| 4 | Testing & debugging | 8-16 hours |
| **Total** | | **24-46 hours** |

---

## Build Options (To Decide Later)

| Option | Description |
|--------|-------------|
| AIDE | Compile directly on Android TV box (no PC needed) |
| GitHub Actions | Auto-build APK from code push |
| External build | Find someone to build the APK |

---

## Success Criteria

- [ ] AkiraTV starts automatically on Android boot
- [ ] Web UI accessible at http://IP:8081
- [ ] Can play videos via HLS streams
- [ ] Works without keyboard/mouse
- [ ] Power consumption < 15W
- [ ] Can copy JSON files from PC via USB
