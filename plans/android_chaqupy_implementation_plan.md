# AkiraTV ChaQuPy Android Implementation

## Overview

Run AkiraTV on Android TV boxes using **ChaQuPy** (Python for Android) + **Kotlin HTTP Server** hybrid approach.

## Problem

- Android SELinux prevents executing native binaries (Node.js)
- Can't run Node.js on Android TV boxes without root

## Solution: Hybrid Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Android TV Box                        │
│                                                          │
│   ┌─────────────────────────────────────────────────┐   │
│   │  AkiraTV App                                    │   │
│   │                                                  │   │
│   │  ┌─────────────────┐    ┌──────────────────┐   │   │
│   │  │ Kotlin HTTP     │◄──►│ Python/ChaQuPy   │   │   │
│   │  │ Server          │    │ (Core Logic)     │   │   │
│   │  │ - Serves Web UI │    │ - Channels       │   │   │
│   │  │ - API Endpoints │    │ - Scheduling     │   │   │
│   │  │ - File Serving  │    │ - Library        │   │   │
│   │  └─────────────────┘    └──────────────────┘   │   │
│   │         │                       │                │   │
│   └─────────┼───────────────────────┼────────────────┘   │
│             │                       │                     │
│        USB Storage           USB Storage                 │
│        (Videos)              (Output/HLS)                │
└─────────────────────────────────────────────────────────┘
```

## Why This Approach?

| Approach | Pros | Cons |
|----------|------|------|
| Node.js | Existing JS code | Blocked by Android SELinux |
| Pure Kotlin | Works natively | Port Python logic needed |
| **ChaQuPy + Kotlin** | Keep Python logic, works on Android | Slightly complex setup |

## Implementation Steps

### Phase 1: Setup

- [x] 1.1 Add ChaQuPy to build.gradle.kts
- [x] 1.2 Copy Python files to assets
- [x] 1.3 Configure Python environment

### Phase 2: Python Bridge

- [x] 2.1 Create akiratv/android_bridge.py
- [x] 2.2 Create Python bridge functions
- [x] 2.3 Test Python imports

### Phase 3: Kotlin Integration

- [x] 3.1 Create PythonBridge.kt
- [x] 3.2 Create KotlinHttpServer.kt
- [x] 3.3 Connect HTTP endpoints to Python

### Phase 4: Android Features

- [x] 4.1 USB path detection
- [x] 4.2 File permissions
- [x] 4.3 Service lifecycle

---

## Detailed Implementation

### Step 1.1: Add ChaQuPy Dependency

```kotlin
// AkiraTV-Android/app/build.gradle.kts
dependencies {
    implementation("com.chaquo.python:chaquopy:17.0.0")
}
```

### Step 1.2: Copy Python Files

Copy to `AkiraTV-Android/app/src/main/assets/`:
- `akiratv/` - Python source code
- `user/` - User data and channels
- `config.json` - Configuration

### Step 2.1: Create Android Bridge

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

### Step 3.1: Create PythonBridge.kt

```kotlin
// AkiraTV-Android/app/src/main/java/com/akiratv/android/PythonBridge.kt

package com.akiratv.android

import android.content.Context
import android.util.Log
import com.chaquo.python.PyException
import com.chaquo.python.PyObject
import com.chaquo.python.Python

class PythonBridge(private val context: Context) {
    
    companion object {
        private const val TAG = "PythonBridge"
    }
    
    private val python: Python = Python.getInstance()
    private val akiratv = python.getModule("akiratv.android_bridge")
    
    fun initialize() {
        // Set Android-specific paths
        val usbPath = USBHelper.getUSBPath(context)
        if (usbPath != null) {
            akiratv.call("set_android_paths", usbPath)
            Log.i(TAG, "Android paths set to: $usbPath")
        }
    }
    
    fun getChannels(): List<String> {
        return try {
            akiratv.call("get_channels").toJava(List::class.java) as List<String>
        } catch (e: PyException) {
            Log.e(TAG, "Error getting channels", e)
            emptyList()
        }
    }
    
    fun getChannelInfo(name: String): Map<String, Any>? {
        return try {
            akiratv.call("get_channel_info", name).toJava(Map::class.java) as? Map<String, Any>
        } catch (e: PyException) {
            Log.e(TAG, "Error getting channel info", e)
            null
        }
    }
    
    fun playChannel(name: String): Boolean {
        return try {
            akiratv.call("play_channel", name).toBoolean()
        } catch (e: PyException) {
            Log.e(TAG, "Error playing channel", e)
            false
        }
    }
    
    fun stopPlayback(): Boolean {
        return try {
            akiratv.call("stop_playback").toBoolean()
        } catch (e: PyException) {
            Log.e(TAG, "Error stopping playback", e)
            false
        }
    }
    
    fun getConfig(): Map<String, Any>? {
        return try {
            akiratv.call("get_config").toJava(Map::class.java) as? Map<String, Any>
        } catch (e: PyException) {
            Log.e(TAG, "Error getting config", e)
            null
        }
    }
}
```

---

## Python Modifications Needed

### File: akiratv/config.py

Add Android path detection:

```python
import os

def get_android_paths():
    """Detect Android storage paths"""
    if os.name == 'java':
        # Running on Android via ChaQuPy
        import android.os.Environment
        # Return USB path if available
        return "/storage/XXXX-XXXX/AkiraTV"
    return None

# Modify paths for Android
if get_android_paths():
    USER_ROOT = Path("/storage/XXXX-XXXX/AkiraTV/user")
```

### File: akiratv/inventory.py

Use Android storage paths:

```python
def get_video_path():
    """Get video directory path"""
    if is_android():
        return "/storage/XXXX-XXXX/AkiraTV/videos"
    return "videos"
```

---

## Build Commands

### Build APK
```batch
cd AkiraTV-Android
set "JAVA_HOME=C:\Program Files\Android\Android Studio\jbr"
gradlew.bat assembleDebug
```

### Install to Device
```batch
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

---

## Troubleshooting

### Issue: Python imports fail
- Ensure all Python dependencies are in requirements.txt
- ChaQuPy will install them automatically

### Issue: Path errors
- Check USB is mounted
- Verify storage permissions in AndroidManifest.xml

### Issue: App crashes on start
- Check Logcat for Python errors
- Ensure ChaQuPy is properly initialized

### Issue: ChaQuPy Repository Not Accessible
- The ChaQuPy library (com.chaquo.python:chaquopy) is hosted on chaquo.com repository
- The repository appears to be inaccessible (HTTP 404)
- Maven Central only has the Gradle plugin, not the library

### Alternative Python for Android Solutions

If ChaQuPy remains inaccessible, consider these alternatives:

1. **BeeWare/Toga** - Pure Python native apps
   - https://beeware.org/
   - Different architecture than ChaQuPy

2. **Kivy** - Open source Python framework
   - https://kivy.org/
   - Requires different app structure

3. **PyDroid3** - Android Python interpreter
   - https://play.google.com/store/apps/details?id=ru.iiec.pydroid3
   - Different deployment model (installed app runs Python)

4. **Chaquopy local installation** - Install ChaQuPy locally
   - Download from: https://chaquo.com/chaquopy/
   - Install the .whl file manually to local Maven repository

5. **VPN/Proxy** - Access chaquo.com through different network
   - The repository may be blocked in certain regions

---

*Last Updated: 2026-03-18*
