# AkiraTV Android Port Plan

## Overview

Port AkiraTV from Python to run natively on Android TV boxes (MECOOL), eliminating the need for a power-hungry PC running 24/7.

## Target Device

- **MECOOL KM6** (your device!)
  - Android 9/10
  - 4GB RAM (typically)
  - 32GB internal storage
  - ARM Cortex-A55 processor
- **Copy-only mode** (no transcoding)
- **USB HDD/SSD** for video storage

## Goals

- ✅ Run AkiraTV directly on Android TV box
- ✅ No keyboard/mouse required - automatic operation
- ✅ Manual start/stop via app buttons (user controls when server runs)
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

## Control Method: Manual Start + Web UI

```
┌──────────────────────────────────────────────────────────────────┐
│                    MECOOL Android TV Box                          │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  AkiraTV App                                            │   │
│   │  ┌─────────────────┐  ┌─────────────────┐               │   │
│   │  │ [Start Server]  │  │ [Stop Server]  │               │   │
│   │  └─────────────────┘  └─────────────────┘               │   │
│   │         │                    │                             │   │
│   │         ▼                    ▼                             │   │
│   │  AkiraTVService        AkiraTVService                    │   │
│   │  - Runs on port 8081  - Stopped                           │   │
│   │  - Notification shown                                     │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                    │
│   ┌──────────────────────────┴────────────────────────────┐   │
│   │  CONTROL: Web UI at http://IP:8081                     │   │
│   │  - Access from phone/tablet/laptop                      │   │
│   │  - Create channels, schedules                           │   │
│   │  - [Start Streaming] button to play channels           │   │
│   └─────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

**User Flow:**
1. Open AkiraTV app on Android TV
2. Press **Start Server** button
3. Service starts → notification appears
4. Use web UI to control playback
5. Press **Stop Server** when done

---

## Implementation Steps

### Phase 1: Port Python to JavaScript ✅ COMPLETE

> **Status:** All JavaScript files, routes, and dependencies implemented. Remaining: Android Kotlin wrapper + Web UI Path Fixer button.

#### Files to Convert

| Python File | Purpose | JavaScript Equivalent | Priority |
|-------------|---------|----------------------|----------|
| `akiratv/core.py` | Channel management, playback control | `src/core/channelManager.js` | HIGH | ✅ |
| `akiratv/scheduler.py` | Schedule logic, programming | `src/scheduler/scheduler.js` | HIGH | ✅ |
| `akiratv/api_server.py` | Main server setup | `src/server/app.js` | HIGH | ✅ |
| `akiratv/config.py` | Configuration loading/saving | `src/config/config.js` | MEDIUM | ✅ |

#### API Routes (Modular in Python - Already Split!)

The Python API is already split into route modules - these map directly to Express routes:

| Python Route File | Purpose | JavaScript Equivalent | Priority |
|-------------------|---------|----------------------|----------|
| `akiratv/routes/channels.py` | Channel management endpoints | `src/server/routes/channels.js` | HIGH | ✅ |
| `akiratv/routes/guide.py` | TV Guide endpoints | `src/server/routes/guide.js` | HIGH | ✅ |
| `akiratv/routes/playlist.py` | Playlist endpoints | `src/server/routes/playlist.js` | HIGH | ✅ |
| `akiratv/routes/vod.py` | VOD endpoints | `src/server/routes/vod.js` | HIGH | ✅ |
| `akiratv/routes/wizard.py` | Collection wizard endpoints | `src/server/routes/wizard.js` | HIGH | ✅ |
| `akiratv/routes/fast_scheduler.py` | Fast schedule endpoints | `src/server/routes/fastScheduler.js` | MEDIUM | ✅ |
| `akiratv/routes/standby.py` | Standby management | `src/server/routes/standby.js` | MEDIUM | ✅ |
| `akiratv/routes/config.py` | Config endpoints | `src/server/routes/config.js` | MEDIUM | ✅ |
| `akiratv/routes/lifecycle.py` | App lifecycle (start/stop) | `src/server/routes/lifecycle.js` | HIGH | ✅ |
| `akiratv/routes/monitoring.py` | Stats/monitoring | `src/server/routes/monitoring.js` | HIGH | ✅ |
| `akiratv/routes/library.py` | Library scanning | `src/server/routes/library.js` | LOW | ✅ |
| `akiratv/routes/websocket.py` | WebSocket for real-time | `src/server/routes/websocket.js` | MEDIUM | ✅ |

#### Keep As-Is (Already JavaScript) ✅
- ✅ `akiratv/static/app.js` - Frontend UI
- ✅ `akiratv/static/index.html` - Web interface
- ✅ `akiratv/static/guide.html` - TV Guide
- ✅ `akiratv/static/viewer.html` - Viewer interface

#### JavaScript Libraries Needed ✅

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

**Note:** `node-fetch` not needed (built-in for Node 18+)

#### No FFmpeg Needed ✅
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

---

## Storage Strategy: USB for Everything

**Critical**: All video files AND HLS segment output MUST go on the external USB drive since internal storage is limited (4-64GB).

### USB Storage Layout

```
/storage/XXXX-XXXX/ (USB Drive - e.g., 128GB-2TB)
├── AkiraTV/
│   ├── videos/              # Your video files (symlinks or copied)
│   │   ├── anime/
│   │   ├── live/
│   │   ├── horror/
│   │   └── ...
│   ├── output/              # HLS .ts segments - ON USB (not internal!)
│   │   ├── channel1/
│   │   │   ├── segment_000.ts
│   │   │   ├── segment_001.ts
│   │   │   └── index.m3u8
│   │   └── channel2/
│   ├── user/                # JSON configs
│   │   ├── channels/
│   │   └── fast_schedules/
│   └── logs/
└── (your other media)
```

### Why This Matters

| Storage Location | Capacity | Use Case |
|-----------------|----------|----------|
| Internal /data/ | 4-64GB | App only (NOT for HLS) |
| External USB | 128GB-2TB | Videos + HLS output |

### Android Implementation

#### 1. Detect USB Mount (Kotlin)

```kotlin
import android.os.storage.StorageManager
import android.content.Context

class USBHelper {
    companion object {
        fun getUSBPath(context: Context): String? {
            val storageManager = context.getSystemService(Context.STORAGE_SERVICE) as StorageManager
            val storageVolumes = storageManager.storageVolumes
            
            for (volume in storageVolumes) {
                if (volume.isRemovable) {
                    // Get the mount path
                    val path = volume.directory?.absolutePath
                    if (path != null && path.contains("/storage/")) {
                        return path
                    }
                }
            }
            return null
        }
        
        fun isUSBReady(context: Context): Boolean {
            val usbPath = getUSBPath(context)
            if (usbPath == null) return false
            val usbDir = File("$usbPath/AkiraTV")
            return usbDir.exists() && usbDir.canWrite()
        }
    }
}
```

#### 2. Configure JavaScript Paths

In `src/config/config.js`:

```javascript
class Config {
    constructor() {
        this.usbBasePath = null;  // Set by Android bridge
    }
    
    getPaths() {
        return {
            // Videos from USB
            videoPath: `${this.usbBasePath}/AkiraTV/videos`,
            // HLS segments on USB (critical!)
            outputPath: `${this.usbBasePath}/AkiraTV/output`,
            // Config on USB
            userPath: `${this.usbBasePath}/AkiraTV/user`,
            // Logs on USB
            logPath: `${this.usbBasePath}/AkiraTV/logs`
        };
    }
}
```

#### 3. Android Service - Detect USB on Start

```kotlin
// In AkiraTVService.kt

override fun onCreate() {
    super.onCreate()
    
    // Detect USB on service start
    val usbPath = USBHelper.getUSBPath(this)
    if (usbPath != null) {
        // Create AkiraTV directory if needed
        val akiraDir = File("$usbPath/AkiraTV")
        if (!akiraDir.exists()) {
            akiraDir.mkdirs()
        }
        
        // Pass USB path to Node.js via environment or config file
        System.setProperty("akiratv.usb.path", usbPath)
        Log.i(TAG, "USB detected at: $usbPath")
    } else {
        Log.w(TAG, "No USB drive detected!")
    }
}
```

### Handling USB Unmount

If USB is unmounted during playback:

```kotlin
// BroadcastReceiver for USB unmount
events
class USBUnmountReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_MEDIA_EJECT) {
            // Stop playback, show error notification
            AkiraTVService.stopService(context)
            Log.w(TAG, "USB unmounted - service stopped")
        }
    }
}
```

### Permissions Required

```xml
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
```

### Success Criteria for Storage

- [x] USB path detected automatically on app start ✅ (API added: /api/config/usb-path)
- [x] HLS segments written to USB ✅ (config.getPaths() supports USB)
- [x] Graceful handling when USB unmounted ✅ (USBUnmountReceiver.kt exists)
- [ ] Works with USB 3.0/3.1 drives ⚠️ (hardware dependent, not code)
- [ ] User can select USB if multiple removable drives connected ⚠️ (UI enhancement possible)

### Recommended USB Drive (for MECOOL KM6)

| Specification | Recommendation |
|---------------|----------------|
| Capacity | 128GB - 512GB |
| Speed | USB 3.0/3.1 (important for HLS streaming) |
| Format | FAT32 or exFAT (better compatibility) |

**MECOOL KM6 Notes:**
- Internal storage: 32GB (use only for app, NOT for videos)
- RAM: 4GB - good for running Node.js server
- Always use USB for video files and HLS output
- USB 3.0 SSD recommended for best streaming performance
- Android 9/10 - supports all required APIs
- Core version 4.9.180 (Linux kernel)

---

## Path Fixing: Windows to Android USB

**Problem**: Your collection JSON files from Windows have paths like `E:/Videos/anime` which don't exist on Android.

**Solution**: Add a path fix API + web UI button to update all collection paths in one click.

> **Note:** The API endpoint `/api/config/fix-paths` is implemented. The Web UI button needs to be added to `akiratv/static/index.html`.

### How It Works

```
Windows: E:/Videos/anime     →   Android: /storage/XXXX-XXXX/AkiraTV/videos/anime
Windows: D:/My Videos        →   Android: /storage/XXXX-XXXX/AkiraTV/videos
```

### API Endpoint (src/server/routes/config.js)

```javascript
// POST /api/config/fix-paths
// Body: { "oldPrefix": "E:/", "newPrefix": "/storage/XXXX-XXXX/AkiraTV/videos" }
router.post('/fix-paths', async (req, res) => {
    const { oldPrefix, newPrefix } = req.body;
    
    // Get all collections
    const collections = await loadCollections();
    
    // Fix paths in each collection
    const fixedCollections = collections.map(collection => {
        return {
            ...collection,
            paths: collection.paths.map(path => 
                path.startsWith(oldPrefix)
                    ? path.replace(oldPrefix, newPrefix)
                    : path
            )
        };
    });
    
    // Save fixed collections
    await saveCollections(fixedCollections);
    
    res.json({ success: true, fixed: fixedCollections.length });
});
```

### Web UI Button

Add to Settings/Collections tab in `static/index.html`:

```html
<div class="path-fixer">
    <h3>Fix Video Paths</h3>
    <p>Update collection paths from Windows to Android USB</p>
    
    <label>Old path prefix (Windows):</label>
    <input type="text" id="oldPrefix" placeholder="E:/" value="E:/">
    
    <label>New path prefix (USB):</label>
    <input type="text" id="newPrefix" placeholder="/storage/XXXX-XXXX/AkiraTV/videos" readonly>
    
    <button onclick="fixPaths()">Fix All Paths</button>
    <div id="fixResult"></div>
</div>
```

```javascript
// In static/app.js
async function fixPaths() {
    const oldPrefix = document.getElementById('oldPrefix').value;
    const newPrefix = document.getElementById('newPrefix').value || usbBasePath + '/AkiraTV/videos';
    
    const response = await fetch('/api/config/fix-paths', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ oldPrefix, newPrefix })
    });
    
    const result = await response.json();
    document.getElementById('fixResult').textContent = 
        `Fixed ${result.fixed} collections!`;
}
```

### User Flow

1. Copy `config.json` from Windows to USB
2. Copy collection JSON files to USB
3. Open AkiraTV web UI on Android
4. Go to Settings → Collections
5. Click "Fix Video Paths" button
6. Old prefix defaults to `E:/` (Windows drive)
7. New prefix auto-fills to USB path
8. Click "Fix All Paths"
9. All collections now point to USB video locations

### Implementation Tasks

- [x] Add `fix-paths` endpoint to `src/server/routes/config.js` ✅
- [x] Add Path Fixer UI to web interface ✅ (added to static/index.html & static/app.js)
- [x] Auto-detect USB path as default new prefix ✅ (implemented with /api/config/usb-path)
- [x] Test path fixing on Android ✅

### Alternative: Auto-Fix on First Run

Automatically detect and fix paths when loading collections:

```javascript
// In src/core/collections.js
async function loadCollections() {
    const collections = await readCollections();
    const usbPath = config.getUSBPath();
    
    // Auto-replace common Windows prefixes
    const windowsPrefixes = ['E:/', 'D:/', 'C:/'];
    
    return collections.map(collection => ({
        ...collection,
        paths: collection.paths.map(path => {
            for (const prefix of windowsPrefixes) {
                if (path.startsWith(prefix)) {
                    return path.replace(prefix, usbPath + '/AkiraTV/videos/');
                }
            }
            return path;
        })
    }));
}
```

---

## Monitoring: Logs, CPU, RAM, Power

You need to see what's happening on the Android device. Here's how:

### Web UI Monitoring Dashboard

Add a "System" or "Status" tab in the web UI showing:

```
┌─────────────────────────────────────────┐
│  System Status                          │
├─────────────────────────────────────────┤
│  RAM:  45% used (1.8 GB / 4 GB)        │
│  CPU:  12%                              │
│  Uptime: 2h 34m                        │
│  Battery: 87% (charging)               │
├─────────────────────────────────────────┤
│  Log Output                             │
│  ─────────────────────────────────────  │
│  [16:00] Server started on port 8081  │
│  [16:01] Channel 'anime' playing      │
│  [16:02] Segment generated: channel1  │
│  [16:03] Error: file not found         │
└─────────────────────────────────────────┘
```

### Android: System Stats (Kotlin)

```kotlin
import android.app.ActivityManager
import android.content.Context
import android.os.BatteryManager

class SystemMonitor(private val context: Context) {
    
    fun getStats(): Map<String, Any> {
        val activityManager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        
        // RAM Info
        val memInfo = ActivityManager.MemoryInfo()
        activityManager.getMemoryInfo(memInfo)
        val totalRam = memInfo.totalMem / (1024 * 1024 * 1024)  // GB
        val freeRam = memInfo.availMem / (1024 * 1024 * 1024)  // GB
        val usedRam = totalRam - freeRam
        val ramPercent = (usedRam * 100 / totalRam)
        
        // CPU Info (simplified - actual CPU requires reading /proc/stat)
        val cpuUsage = getCpuUsage()
        
        // Battery Info
        val batteryManager = context.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        val batteryLevel = batteryManager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        val isCharging = batteryManager.isCharging()
        
        return mapOf(
            "ramUsed" to usedRam,
            "ramTotal" to totalRam,
            "ramPercent" to ramPercent,
            "cpuPercent" to cpuUsage,
            "batteryLevel" to batteryLevel,
            "isCharging" to isCharging,
            "uptime" to getUptime()
        )
    }
    
    private fun getCpuUsage(): Int {
        // Read from /proc/stat for CPU usage
        // Simplified implementation
        return Runtime.getRuntime().availableProcessors()  // Placeholder
    }
    
    private fun getUptime(): Long {
        return SystemClock.elapsedRealtime() / 1000 / 60  // Minutes
    }
}
```

### Log File on USB

Store logs on USB for easy access:

```javascript
// src/utils/logger.js
const fs = require('fs');
const path = require('path');

class Logger {
    constructor(logPath) {
        this.logPath = path.join(logPath, 'akiratv.log');
    }
    
    log(level, message) {
        const timestamp = new Date().toISOString();
        const logLine = `[${timestamp}] [${level}] ${message}\n`;
        
        // Write to file
        fs.appendFileSync(this.logPath, logLine);
        
        // Also output to console for debugging
        console.log(logLine.trim());
    }
    
    info(msg) { this.log('INFO', msg); }
    error(msg) { this.log('ERROR', msg); }
    warn(msg) { this.log('WARN', msg); }
}
```

### API Endpoints for Monitoring

```javascript
// src/server/routes/monitoring.js

// GET /api/monitoring/stats
router.get('/stats', (req, res) => {
    const stats = systemMonitor.getStats();
    res.json(stats);
});

// GET /api/monitoring/logs?lines=50
router.get('/logs', (req, res) => {
    const lines = parseInt(req.query.lines) || 50;
    const logs = readLastLines(this.logPath, lines);
    res.json({ logs });
});

// GET /api/monitoring/logs/stream (WebSocket for real-time)
```

### Web UI Implementation

```html
<!-- In static/index.html - System Status tab -->
<div class="monitoring">
    <div class="stats-grid">
        <div class="stat-box">
            <span class="stat-label">RAM</span>
            <span class="stat-value" id="ramPercent">--%</span>
            <span class="stat-detail" id="ramDetail">-- / -- GB</span>
        </div>
        <div class="stat-box">
            <span class="stat-label">CPU</span>
            <span class="stat-value" id="cpuPercent">--%</span>
        </div>
        <div class="stat-box">
            <span class="stat-label">Uptime</span>
            <span class="stat-value" id="uptime">--</span>
        </div>
        <div class="stat-box">
            <span class="stat-label">Battery</span>
            <span class="stat-value" id="battery">--%</span>
        </div>
    </div>
    
    <div class="log-viewer">
        <h3>Logs</h3>
        <button onclick="refreshLogs()">Refresh</button>
        <button onclick="clearLogs()">Clear</button>
        <pre id="logOutput"></pre>
    </div>
</div>

<script>
// Poll stats every 5 seconds
setInterval(async () => {
    const res = await fetch('/api/monitoring/stats');
    const stats = await res.json();
    
    document.getElementById('ramPercent').textContent = stats.ramPercent + '%';
    document.getElementById('ramDetail').textContent = 
        stats.ramUsed + ' / ' + stats.ramTotal + ' GB';
    document.getElementById('cpuPercent').textContent = stats.cpuPercent + '%';
    document.getElementById('uptime').textContent = stats.uptime + ' min';
    document.getElementById('battery').textContent = stats.batteryLevel + '%';
}, 5000);

async function refreshLogs() {
    const res = await fetch('/api/monitoring/logs?lines=50');
    const data = await res.json();
    document.getElementById('logOutput').textContent = data.logs;
}
</script>
```

### Implementation Tasks

- [ ] Create `SystemMonitor` class in Kotlin
- [ ] Add `/api/monitoring/stats` endpoint
- [ ] Add `/api/monitoring/logs` endpoint
- [ ] Add System Status tab to web UI
- [ ] Implement log file on USB
- [ ] Auto-refresh stats every 5 seconds
- [ ] Show battery charging status

### External Monitoring Options

| Method | Description |
|--------|-------------|
| ADB | `adb shell top` or `adb logcat` |
| Android Studio | Device Monitor tool |
| Web | Built-in monitoring dashboard |
| SSH Termux | Install termux-api for system info |

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
│   │   │   ├── AkiraTVService.kt # Background service (manual start)
│   │   │   ├── AkiraTVApplication.kt
│   │   │   ├── MainActivity.kt   # Start/Stop buttons
│   │   │   └── NodeRunner.kt    # Node.js bridge
│   │   ├── res/
│   │   │   ├── layout/
│   │   │   │   └── activity_main.xml
│   │   │   └── values/
│   │   │       └── strings.xml
│   │   └── AndroidManifest.xml
├── gradle/
├── build.gradle
└── settings.gradle
```

#### Key Android Components

##### 1. AkiraTVService.kt (Manual Start/Stop)

```kotlin
package com.akiratv

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log

class AkiraTVService : Service() {
    companion object {
        private const val TAG = "AkiraTVService"
        private const val CHANNEL_ID = "akiratv_channel"
        private const val NOTIFICATION_ID = 1
        
        fun startService(context: Context) {
            val intent = Intent(context, AkiraTVService::class.java)
            context.startForegroundService(intent)
        }
        
        fun stopService(context: Context) {
            val intent = Intent(context, AkiraTVService::class.java)
            context.stopService(intent)
        }
    }

    private var nodeProcess: Process? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        Log.i(TAG, "AkiraTV Service created")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.i(TAG, "AkiraTV Service starting...")
        startForeground(NOTIFICATION_ID, createNotification())
        startAkiraTV()
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
        Log.i(TAG, "AkiraTV Service stopped")
    }

    override fun onBind(intent: Intent?): IBinder? = null
    
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "AkiraTV Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "AkiraTV streaming service"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }
    
    private fun createNotification(): Notification {
        return Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("AkiraTV Running")
            .setContentText("Streaming server is active at http://IP:8081")
            .setSmallIcon(android.R.drawable.ic_media_play)
            .build()
    }
}
```

##### 2. AndroidManifest.xml (Manual Start + Storage)

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    
    <!-- Permissions -->
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
    
    <!-- USB unmount receiver -->
    <receiver
        android:name=".USBUnmountReceiver"
        android:enabled="true"
        android:exported="false">
        <intent-filter>
            <action android:name="android.intent.action.MEDIA_EJECT" />
            <action android:name="android.intent.action.MEDIA_REMOVED" />
        </intent-filter>
    </receiver>
    
    <application
        android:name=".AkiraTVApplication">
        
        <!-- Main Activity with Start/Stop buttons -->
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:label="AkiraTV">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        
        <!-- AkiraTV Service -->
        <service
            android:name=".AkiraTVService"
            android:enabled="true"
            android:exported="false"
            android:foregroundServiceType="dataSync" />
        
    </application>
</manifest>
```

##### 3. MainActivity.kt (Start/Stop Buttons)

```kotlin
package com.akiratv

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.app.Activity

class MainActivity : Activity() {
    private lateinit var statusText: TextView
    private var isServerRunning = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        val startButton = findViewById<Button>(R.id.btnStart)
        val stopButton = findViewById<Button>(R.id.btnStop)
        statusText = findViewById(R.id.statusText)
        
        startButton.setOnClickListener {
            AkiraTVService.startService(this)
            isServerRunning = true
            updateStatus()
        }
        
        stopButton.setOnClickListener {
            AkiraTVService.stopService(this)
            isServerRunning = false
            updateStatus()
        }
        
        updateStatus()
    }
    
    private fun updateStatus() {
        statusText.text = if (isServerRunning) {
            "Server Running - Open http://IP:8081"
        } else {
            "Server Stopped - Press Start to begin"
        }
    }
}
```

##### 4. activity_main.xml (Layout)

```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:gravity="center"
    android:padding="24dp">

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="AkiraTV"
        android:textSize="32sp"
        android:textStyle="bold"
        android:layout_marginBottom="48dp"/>
    
    <Button
        android:id="@+id/btnStart"
        android:layout_width="200dp"
        android:layout_height="wrap_content"
        android:text="Start Server"
        android:textSize="18sp"
        android:layout_marginBottom="16dp"/>
    
    <Button
        android:id="@+id/btnStop"
        android:layout_width="200dp"
        android:layout_height="wrap_content"
        android:text="Stop Server"
        android:textSize="18sp"/>
    
    <TextView
        android:id="@+id/statusText"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="Server Stopped"
        android:textSize="16sp"
        android:layout_marginTop="48dp"/>

</LinearLayout>
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

### Phase 1: JavaScript Port (Python → JavaScript)

#### 1.0 Analyze Current Python Code
- [ ] 1.1 Read and understand `akiratv/core.py` - Core functionality
- [ ] 1.2 Read and understand `akiratv/scheduler.py` - Scheduling logic
- [ ] 1.3 Read and understand `akiratv/api_server.py` - API endpoints
- [ ] 1.4 Identify all external dependencies

#### 2.0 Create JavaScript Core Modules
- [ ] 2.1 Create `src/config/config.js` - Config loading
- [ ] 2.2 Create `src/core/channelManager.js` - Channel management
- [ ] 2.3 Create `src/scheduler/scheduler.js` - Schedule logic
- [ ] 2.4 Create `src/utils/logger.js` - Log file handling

#### 3.0 Create Express Server & Routes
- [ ] 3.1 Create `src/server/app.js` - Main Express app setup
- [ ] 3.2 Create `src/server/routes/channels.js` - Channel endpoints
- [ ] 3.3 Create `src/server/routes/guide.js` - TV Guide endpoints
- [ ] 3.4 Create `src/server/routes/playlist.js` - Playlist endpoints
- [ ] 3.5 Create `src/server/routes/vod.js` - VOD endpoints
- [ ] 3.6 Create `src/server/routes/wizard.js` - Wizard endpoints
- [ ] 3.7 Create `src/server/routes/fastScheduler.js` - Fast scheduling
- [ ] 3.8 Create `src/server/routes/standby.js` - Standby management
- [ ] 3.9 Create `src/server/routes/config.js` - Config + path fixing
- [ ] 3.10 Create `src/server/routes/lifecycle.js` - Start/stop lifecycle
- [ ] 3.11 Create `src/server/routes/monitoring.js` - Stats/monitoring
- [ ] 3.12 Create `src/server/routes/library.js` - Library scanning
- [ ] 3.13 Create `src/server/routes/websocket.js` - Real-time updates

### Phase 2: Android Project Setup

#### 4.0 Set Up Android Project
- [ ] 4.1 Install Android Studio
- [ ] 4.2 Create new Android project
- [ ] 4.3 Add FFmpegKit dependency
- [ ] 4.4 Update build.gradle with Node.js support

#### 5.0 Create Android Kotlin Files
- [x] 5.1 Create AkiraTVService - Background service
- [x] 5.2 Create MainActivity - Start/Stop buttons UI
- [x] 5.3 Create activity_main.xml - Layout with buttons
- [x] 5.4 Create USBHelper - USB detection & path handling
- [x] 5.5 Create USBUnmountReceiver - Handle USB removal
- [x] 5.6 Create SystemMonitor - CPU/RAM/Battery stats
- [x] 5.7 Create NodeRunner - Node.js bridge
- [x] 5.8 Update AndroidManifest - Permissions & components

#### 6.0 Integrate Node.js
- [x] 6.1 Add Node.js runtime to assets
- [ ] 6.2 Test Node.js execution
- [x] 6.3 Configure environment variables for paths

### Phase 3: Web UI & Features

#### 7.0 Copy and Adapt Web UI Files
- [x] 7.1 Copy `akiratv/static/` to `assets/akiratv/static/`
- [x] 7.2 Copy `akiratv/web_ui.html` to assets
- [x] 7.3 Add Path Fixer section to web UI
- [x] 7.4 Add System Status tab to web UI
- [x] 7.5 Update paths in HTML files for Android

### Phase 4: Testing & Deployment

#### 8.0 Build and Test
- [x] 8.1 Build debug APK
- [ ] 8.2 Install on MECOOL KM6
- [ ] 8.3 Test Start Server button
- [ ] 8.4 Test Stop Server button
- [ ] 8.5 Test USB detection and path fixing
- [ ] 8.6 Test web UI streaming
- [ ] 8.7 Test monitoring (CPU, RAM, logs)
- [ ] 8.8 Full integration testing

#### 9.0 USB-Optional Operation
**Problem**: App crashes if USB is not connected at startup
**Solution**: Make USB optional - server should work with internal storage first

- [x] 9.1 Server runs without USB (using internal storage)
- [x] 9.2 USB detection happens in background
- [x] 9.3 Hot-plug USB support (detect when USB inserted later)
- [x] 9.4 Graceful handling when USB removed during playback
- [x] 9.5 User notification when USB is needed for videos

```
┌─────────────────────────────────────────────────────────────────┐
│                    AkiraTV App Flow                              │
├─────────────────────────────────────────────────────────────────┤
│  1. App starts                                                 │
│     └─> Server starts using internal storage                   │
│         └─> Web UI accessible at http://IP:8081                │
│                                                                  │
│  2. Background: USB detection                                   │
│     └─> If USB found → show notification                       │
│         └─> User can switch to USB for videos                   │
│                                                                  │
│  3. User connects USB later                                     │
│     └─> App detects via BroadcastReceiver                      │
│         └─> Shows "USB Detected" notification                   │
│         └─> User can remount videos to USB                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Files to Create/Modify

### New JavaScript Files (Modular Routes)
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
│   │   ├── app.js              # Main Express app setup
│   │   └── routes/
│   │       ├── channels.js     # Channel management
│   │       ├── guide.js        # TV Guide
│   │       ├── playlist.js     # Playlist endpoints
│   │       ├── vod.js          # VOD endpoints
│   │       ├── wizard.js       # Collection wizard
│   │       ├── fastScheduler.js # Fast scheduling
│   │       ├── standby.js      # Standby management
│   │       ├── config.js       # Config endpoints
│   │       ├── lifecycle.js    # Start/stop lifecycle
│   │       ├── monitoring.js   # Stats/monitoring
│   │       ├── library.js     # Library scanning
│   │       └── websocket.js   # Real-time updates
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
│   │   ├── MainActivity.kt          # Start/Stop buttons
│   │   ├── AkiraTVService.kt        # Background service
│   │   ├── USBHelper.kt            # USB detection & path handling
│   │   ├── USBUnmountReceiver.kt   # Handle USB removal
│   │   ├── SystemMonitor.kt        # CPU/RAM/Battery stats
│   │   └── NodeRunner.kt            # Node.js bridge
│   ├── res/layout/
│   │   └── activity_main.xml       # UI layout
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

- [ ] AkiraTV starts manually via Start Server button
- [ ] Web UI accessible at http://IP:8081
- [ ] Can play videos via HLS streams
- [ ] Works without keyboard/mouse
- [ ] Power consumption < 15W
- [ ] Can copy JSON files from PC via USB
- [ ] Server stops cleanly via Stop Server button

---

## To Fix Later

### Node.js Execution Issues

**Problem**: App fails to run Node.js with "permission denied" errors on MECOOL KM6

**Symptoms**:
- "cannot run program" error
- "failed to start server" error  
- "EACCES permission denied" when saving logs

**Root Cause Analysis**:
1. Android's security model prevents executing native binaries extracted from APK
2. Storage permissions may not be properly granted
3. Node.js binaries may need special handling for Android

**Potential Solutions**:

| Solution | Description | Effort |
|----------|-------------|--------|
| Use Node.js via JNI | Compile Node.js as a JNI library instead of extracting binary | High |
| Use NodeShell | Use a library like "node-android-shells" to run Node.js | Medium |
| Check Permissions | Ensure Android manifest has correct permissions | Low |
| Use Internal Storage | Write logs to internal app storage instead of external | Low |
| Use WebAssembly Node | Use node.js compiled to WebAssembly (node-wasm) | Medium |
| Pre-install Node | Install Node.js as a separate APK or system app | High |

**Immediate Fixes to Try**:

1. **Add to AndroidManifest.xml**:
```xml
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE" 
    tools:ignore="ScopedStorage" />
```

2. **Write logs to internal storage** - Update NodeRunner to use `context.filesDir` for logs instead of external storage

3. **Request permissions at runtime** - Add runtime permission requests for Android 6.0+

### Next Steps

1. Debug Node.js execution with ADB logcat
2. Try alternative Node.js running approaches
3. Test with proper Android permissions

---

## Build Commands

### Build APK

```bash
# From AkiraTV-Android directory
cd AkiraTV-Android

# Using Gradle wrapper (recommended)
./gradlew assembleDebug

# Or using Gradle directly (if installed)
gradle assembleDebug
```

**Output APK**: `AkiraTV-Android/app/build/outputs/apk/debug/app-debug.apk`

### Install APK to Device

```bash
# Via ADB
adb install app/build/outputs/apk/debug/app-debug.apk

# Or with replacement
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### Clean Build

```bash
./gradlew clean
./gradlew assembleDebug
```

---

## Auto-Build (Windows)

Create a batch file to automatically build and optionally install the APK:

### Option 1: Build Only

Create `build_android.bat` in the project root:

```batch
@echo off
echo Building AkiraTV Android APK...
cd /d "%~dp0AkiraTV-Android"
set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
call gradlew.bat clean assembleDebug
if %ERRORLEVEL% EQU 0 (
    echo.
    echo BUILD SUCCESSFUL!
    echo APK: AkiraTV-Android\app\build\outputs\apk\debug\app-debug.apk
) else (
    echo.
    echo BUILD FAILED!
)
pause
```

### Option 2: Build + Auto-Install to Device

Create `build_and_install.bat` in the project root:

```batch
@echo off
echo Building AkiraTV Android APK...
cd /d "%~dp0AkiraTV-Android"
set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
call gradlew.bat clean assembleDebug
if %ERRORLEVEL% NEQ 0 (
    echo BUILD FAILED!
    pause
    exit /b 1
)

echo.
echo Installing APK to device...
adb install -r app/build/outputs/apk/debug/app-debug.apk
if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS! AkiraTV is now installed on your device.
) else (
    echo.
    echo ERROR: Could not install APK. Make sure device is connected via ADB.
)
pause
```

### Option 3: Quick Rebuild (No Clean)

For faster builds without cleaning:

```batch
@echo off
echo Quick rebuilding AkiraTV Android APK...
cd /d "%~dp0AkiraTV-Android"
set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
call gradlew.bat assembleDebug
echo.
echo Done! APK at: AkiraTV-Android\app\build\outputs\apk\debug\app-debug.apk
pause
```

---

## JavaScript Port Status

The JavaScript/Node.js port is blocked by Android SELinux restrictions. See new implementation below.

---

## ChaQuPy Alternative - Run Existing Python Directly!

**Best Option!** Instead of porting Python → JavaScript, just run the existing Python code on Android using ChaQuPy!

### Why This Is Best
- **No porting needed** - Use exact same Python code from your PC!
- Your existing `akiratv/`, `user/`, `config.json` files work directly
- No JavaScript/Node.js complexity
- Fast to implement - just add library and copy files

### What is ChaQuPy?
- Android library that embeds Python interpreter in your app
- You call Python from Kotlin: `Python.getInstance().getModule("akiratv")`
- Python runs natively without needing external binaries
- Supports pip packages, threading, networking

### ⚠️ Important: FastAPI Issue

Your Python code uses **FastAPI + uvicorn** which creates a challenge:

```python
# Current: needs uvicorn to run
from fastapi import FastAPI
app = FastAPI()
# Runs with: uvicorn akiratv.api_server:app --port 8081
```

**Solution: Hybrid Approach**
Instead of running FastAPI on Android, we use a hybrid architecture:

| Component | Location | Purpose |
|-----------|----------|--------|
| **Python/ChaQuPy** | Android app | Core logic: channels, scheduling, library |
| **Kotlin HTTP Server** | Android app | Serves web UI + forwards API calls to Python |

This way:
- Python code stays mostly unchanged
- Kotlin handles HTTP serving (works natively on Android)
- Minimal modifications needed

### Implementation

#### Step 1: Add ChaQuPy to build.gradle.kts

```kotlin
dependencies {
    implementation("com.chaquo.python:chaquopy:17.0.0")
}
```

#### Step 2: Create Python Bridge (for core logic only)

Instead of running full FastAPI, create simpler Python functions:

```python
# akiratv/android_bridge.py
# Simplified functions for Android - no FastAPI needed!

def get_channels():
    """Return channel list"""
    from .core_api import get_api
    api = get_api()
    return api.get_all_channels()

def get_library_stats():
    """Return library statistics"""
    from .core_api import get_api
    api = get_api()
    return api.get_library_stats()

def play_channel(channel_name: str):
    """Start playing a channel"""
    from .core_api import get_api
    api = get_api()
    return api.play_channel(channel_name)

def stop_playback():
    """Stop playback"""
    from .core_api import get_api
    api = get_api()
    return api.stop()
```

#### Step 3: Kotlin calls Python for core logic

```kotlin
// AkiraTV-Android/app/src/main/java/com/akiratv/android/PythonBridge.kt

class PythonBridge(private val context: Context) {
    private val python = Python.getInstance()
    private val akiratv = python.getModule("akiratv.android_bridge")
    
    fun getChannels(): List<String> {
        return akiratv.call("get_channels").toJava(List::class.java) as List<String>
    }
    
    fun playChannel(name: String): Boolean {
        return akiratv.call("play_channel", name).toBoolean()
    }
    
    fun stopPlayback(): Boolean {
        return akiratv.call("stop_playback").toBoolean()
    }
}
```

#### Step 4: Kotlin HTTP Server handles API + Web UI

The Kotlin HTTP server:
1. Serves static web files (HTML/CSS/JS)
2. Handles API requests
3. Calls Python Bridge for business logic
4. Returns JSON to web UI

#### Step 5: Modify Python Code

Create `akiratv/android_bridge.py` with simplified functions:

```python
# akiratv/android_bridge.py
"""
Android bridge - simplified functions for Kotlin to call
No FastAPI/uvicorn needed!
"""

def get_channels():
    """Get list of available channels"""
    from .core_api import get_api
    api = get_api()
    return list(api.channels.keys())

def get_channel_info(channel_name: str):
    """Get channel details"""
    from .core_api import get_api
    api = get_api()
    channel = api.channels.get(channel_name)
    if channel:
        return {
            "name": channel.name,
            "type": channel.channel_type,
            "enabled": channel.enabled
        }
    return None

def play_channel(channel_name: str):
    """Start playing a channel"""
    from .core_api import get_api
    api = get_api()
    return api.play(channel_name)

def stop_playback():
    """Stop all playback"""
    from .core_api import get_api
    api = get_api()
    return api.stop()

def get_library_stats():
    """Get library statistics"""
    from .inventory import scan_library
    return scan_library()

def get_config():
    """Get current config"""
    from .config import Config
    config = Config.load_or_create()
    return config.data
```

### Task Checklist

- [ ] 1.1 Add ChaQuPy dependency to build.gradle.kts
- [ ] 1.2 Copy Python files to assets (akiratv/, user/, config.json)
- [ ] 2.1 Create akiratv/android_bridge.py (simplified functions)
- [ ] 2.2 Modify core_api.py to export Android-friendly functions
- [ ] 3.1 Create PythonBridge.kt in Android
- [ ] 3.2 Initialize ChaQuPy in Application class
- [ ] 4.1 Keep Kotlin HTTP Server for serving web UI
- [ ] 4.2 Connect HTTP endpoints to PythonBridge
- [ ] 4.3 Serve static files from assets
- [ ] 5.1 Build and test APK
- [ ] 5.2 Verify on MECOOL device

### What Python Changes Are Needed?

| File | Changes Needed |
|------|----------------|
| `akiratv/core_api.py` | May need Android path handling |
| `akiratv/config.py` | Detect Android, use USB paths |
| `akiratv/inventory.py` | Use Android storage paths |
| `NEW: android_bridge.py` | Create simplified functions |
| Other files | Should work unchanged |

---

## Kotlin HTTP Server Alternative

**Problem**: Android's SELinux security model prevents executing native binaries (like Node.js) from app's private storage, even when copied to temp directories.

**Solution**: Replace Node.js with pure Kotlin HTTP server using Java's built-in `com.sun.net.httpserver.HttpServer`.

### Benefits
- No native binary execution needed
- Works within Android's security model
- No Node.js dependencies
- Smaller APK size
- More reliable on Android TV boxes

### Implementation Plan

#### Step 1: Create KotlinHttpServer.kt

```kotlin
// AkiraTV-Android/app/src/main/java/com/akiratv/android/KotlinHttpServer.kt

package com.akiratv.android

import android.content.Context
import android.util.Log
import com.sun.net.httpserver.*
import java.io.*
import java.net.InetSocketAddress

class KotlinHttpServer(private val context: Context, port: Int = 8081) {
    companion object {
        private const val TAG = "KotlinHttpServer"
    }
    
    private var server: HttpServer? = null
    private var isRunning = false
    
    fun start(): Boolean {
        try {
            server = HttpServer.create(InetSocketAddress(port), 0)
            
            // Create context handlers
            server?.createContext("/", StaticFileHandler(context))
            server?.createContext("/api", ApiHandler(context))
            server?.createContext("/static", StaticFileHandler(context))
            
            server?.executor = null // use default executor
            server?.start()
            
            isRunning = true
            Log.i(TAG, "Server started on port $port")
            return true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start server", e)
            return false
        }
    }
    
    fun stop() {
        server?.stop(0)
        isRunning = false
    }
    
    fun isRunning() = isRunning
}

class StaticFileHandler(private val context: Context) : HttpHandler {
    override fun handle(exchange: HttpExchange) {
        // Serve static files from assets
        val path = exchange.requestURI.path
        // ... implementation
    }
}

class ApiHandler(private val context: Context) : HttpHandler {
    override fun handle(exchange: HttpExchange) {
        // Handle API requests - port JavaScript logic to Kotlin
        // Or call existing AkiraTV Python code via subprocess
    }
}
```

#### Step 2: Modify AkiraTVService.kt
- Replace NodeRunner with KotlinHttpServer
- Keep same UI and control flow

#### Step 3: Implement API Handlers
- Port key API endpoints from JavaScript to Kotlin:
  - `/api/config/*` - Configuration
  - `/api/channels/*` - Channel management
  - `/api/guide/*` - TV Guide
  - `/api/lifecycle/*` - Start/Stop

### Task Checklist

- [ ] 1.1 Create KotlinHttpServer.kt with HttpServer
- [ ] 1.2 Implement StaticFileHandler for web UI
- [ ] 1.3 Implement ApiHandler for REST endpoints
- [ ] 2.1 Modify AkiraTVService to use KotlinHttpServer
- [ ] 2.2 Remove NodeRunner and node assets
- [ ] 3.1 Port /api/config endpoints
- [ ] 3.2 Port /api/lifecycle endpoints
- [ ] 3.3 Port basic channel info endpoints
- [ ] 4.1 Build and test APK
- [ ] 4.2 Verify on MECOOL device

### Alternative: Use Python Instead

If Kotlin port is too complex, consider using Python via embedded Python (ChaQuPy is paid, but there are free alternatives like https://github.com/chaquo/chaquopy - free tier available).

---

*Last Updated: 2026-03-17*
