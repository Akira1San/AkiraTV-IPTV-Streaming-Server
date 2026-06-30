# Live Channel + HLS Encryption

## 1. Live Channel Worker ✅

### Goal
Allow OBS Studio to stream live content to AkiraTV and appear as an HLS channel.

### Architecture (no extra tools needed)

```
OBS Studio --TCP(mpegts)--> FFmpeg LiveWorker --HLS--> output/<channel>/index.m3u8 --> Viewers
```

- OBS outputs MPEG-TS over TCP using its built-in **Custom Output (FFmpeg)**
- The LiveWorker's FFmpeg listens on a TCP port with `?listen=1`
- No RTMP server, no MediaMTX, no extra dependencies

### LiveWorker FFmpeg command

```bash
ffmpeg -i tcp://0.0.0.0:1234?listen=1 \
       -c copy \
       -f hls \
       -hls_time 6 \
       -hls_list_size 20 \
       -hls_flags delete_segments+append_list+omit_endlist \
       -hls_segment_filename output/<channel>/seg_%04d.ts \
       output/<channel>/index.m3u8
```

FFmpeg blocks on `tcp://0.0.0.0:PORT?listen=1` until OBS connects, then starts transcoding.

### Port allocation

Each live channel needs a unique TCP port. Ports are allocated from a configurable range (default: 20000-20099) or set manually in the channel config.

### Files to create

**`akiratv/workers/live_worker.py`** — New worker class

```python
class LiveWorker(BaseWorker):
    def __init__(self, channel, config, logger, transcoding_service, port):
        super().__init__(channel, config, logger)
        self.port = port
        self.transcoding_service = transcoding_service
        self.stream_url = f"tcp://0.0.0.0:{port}?listen=1"

    def run(self):
        if not self.initialize_worker():
            return
        self.logger.info(f"Live worker for {self.channel} listening on port {self.port}")
        args = self._build_ffmpeg_args()
        self._execute_ffmpeg(args)
        self.logger.info(f"Live worker for {self.channel} stopped (OBS disconnected).")

    def _build_ffmpeg_args(self):
        hls_path = self.config.get_hls_output_path(self.channel)
        hls_conf = self.config.data["output"]["hls"]
        playlist = (hls_path / "index.m3u8").as_posix()

        encoding_args = self.transcoding_service.get_encoding_args(
            input_path=None, channel=self.channel
        )

        return [
            FFMPEG_PATH,
            "-v", "verbose",
            "-i", self.stream_url,
            "-map", "0:v:0?", "-map", "0:a:0?",
            *encoding_args,
            "-f", "hls",
            "-hls_time", str(hls_conf["segment_time"]),
            "-hls_list_size", str(hls_conf["playlist_size"]),
            "-hls_flags", "delete_segments+append_list+omit_endlist",
            "-hls_segment_filename", str(hls_path / "seg_%04d.ts"),
            playlist
        ]
```

### Files to modify

**`akiratv/core.py`**
- Import `LiveWorker`
- Handle `channel_type == "live"` in `start()` channel loop
- Add `_start_live_channel(channel_name)`:
  - Read port from channel config (or auto-assign from range)
  - Create LiveWorker with daemon thread
  - Use the existing auto-restart pattern (like linear workers) so if OBS disconnects → FFmpeg exits → worker restarts → waits for OBS again

**config.json channel entry format:**
```json
"my_live_channel": {
    "enabled": true,
    "type": "live",
    "port": 20001
}
```

If no port specified, auto-assign from a range (e.g. 20000 + channel index).

### OBS Setup
1. In OBS: **Settings → Output → Output Mode: Advanced**
2. Switch to the **Output Recording** tab (or use **Advanced** output mode)
3. Set **Type** to **Custom Output (FFmpeg)**
4. Configure:
   - **FFmpeg Output URL**: `tcp://127.0.0.1:20001`
   - **Container Format**: `mpegts`
   - **Video Encoder**: `copy` (or `libx264` if transcoding needed)
   - **Audio Encoder**: `copy` (or `aac`)
5. Click **Start Recording** (OBS starts sending MPEG-TS over TCP)
6. In AkiraTV: enable the live channel → **Start Streaming**

### How the port is displayed to the user
- The channel config lists the TCP port
- In the web UI, the live channel card shows a note like "Connect OBS to tcp://YOUR_IP:20001"
- The HLS URL is the same as any other channel: `http://YOUR_IP:8081/hls/channel/index.m3u8`

### Auto-restart behaviour
- When OBS stops streaming, FFmpeg exits (TCP connection closes)
- The auto-restart wrapper (same pattern as LinearWorker) restarts the LiveWorker after a short delay
- FFmpeg blocks on `tcp://0.0.0.0:PORT?listen=1` again, waiting for OBS to reconnect
- This means OBS can be started/stopped freely without restarting AkiraTV

### Future improvements
- Add OBS connection status in the web UI (connected/disconnected)
- Allow configuring the port from the web UI
- Support multiple live channels simultaneously (each on a different port)

---

## 2. HLS AES-128 Encryption

### Goal
Add optional AES-128 encryption to HLS segments so the stream cannot be played without the decryption key.

### How HLS encryption works
- FFmpeg encrypts each TS segment with AES-128 using a 16-byte key
- An `#EXT-X-KEY:METHOD=AES-128,URI="http://server/key"` tag is added to the playlist
- The player downloads the key from the URI and decrypts segments
- The key can be a static file or served dynamically (e.g., only to authenticated users)

### Key generation

Generate a random 16-byte AES key:
```bash
openssl rand 16 > /path/to/akiratv/keys/channel_name.key
```

### Key info file format

FFmpeg uses a key info file with 3 lines:
```
<key_uri>       # URL the player uses to fetch the key (e.g. http://server:8000/api/key/channel_name)
<key_file_path> # local path to the 16-byte key file
<iv>            # optional 16-byte hex IV (leave blank for auto)
```

### Files to modify

**`akiratv/routes/config.py`** — Add key serving endpoint:
```python
@router.get("/key/{channel}")
def get_key(channel: str):
    key_path = Path("keys") / f"{channel}.key"
    if not key_path.exists():
        raise HTTPException(status_code=404)
    return FileResponse(key_path, media_type="application/octet-stream")
```

**`akiratv/workers/base_worker.py`** — Add optional encryption to `_build_ffmpeg_args` (or to every worker's build method):
```python
if self.config.is_encrypted(self.channel):
    args += ["-hls_key_info_file", str(self.config.get_key_info_path(self.channel))]
```

**`akiratv/config.py`** — Add encryption config methods:
```python
def is_encrypted(self, channel: str) -> bool:
    return self.data.get("channels", {}).get(channel, {}).get("encrypted", False)

def get_key_info_path(self, channel: str) -> Path:
    return Path("keys") / f"{channel}.keyinfo"
```

**config.json channel entry format (extended):**
```json
"my_channel": {
    "enabled": true,
    "type": "linear",
    "encrypted": true
}
```

### Setup script

A helper script `scripts/setup-encryption.sh` that:
1. Creates `keys/` directory
2. Generates a random key for each encrypted channel
3. Creates the key info file with correct paths

### Player compatibility
- VLC: ✅ works (enter the playlist URL, it fetches the key automatically)
- Kodi: ✅ works with IPTV Simple Client
- Browser HLS.js: ✅ works with `hls.js` library
- QuickTime: ❌ does not support encrypted HLS
- The key URI can be served over HTTPS for transport security

### Security notes
- AES-128 HLS encryption prevents casual access but is not DRM
- The key URL is in the playlist (plaintext) — anyone who can read the playlist can fetch the key
- For stronger protection, add auth to the `/api/key/{channel}` endpoint (check referrer, require token, etc.)
- For real security, use a VPN (Tailscale already supported)

---

## 3. Implementation Order

1. **Now Playing Dashboard** (frontend only, quick win)
   - Add HTML section + JS update function
   - Reuses existing API data

2. **Stream Health Panel** (frontend + small backend endpoint)
   - Add `/api/health` endpoint
   - Add HTML section + JS update function

3. **Live Channel Worker ✅** (new worker, standalone)
   - Create `live_worker.py`
   - Add `_start_live_channel()` to `core.py` with auto-restart
   - Add port auto-assignment
   - Test with OBS → TCP → FFmpeg → HLS

4. **HLS Encryption** (modifies existing workers, needs testing on all types)
   - Add key serving endpoint
   - Modify `BaseWorker` or each worker to support `-hls_key_info_file`
   - Add encryption config to `config.py`
   - Test on linear, VOD, dynamic, and live channels

5. **Kodi Push Integration** (small, standalone)
   - Add `notify_kodi()` function
   - Integrate into XMLTV generation route
   - Add config fields

6. **VAAPI Hardware Encoding** (modifies transcoding module)
   - Add VAAPI encoder option to `transcoding.py`
   - Add VAAPI to config and web UI dropdown
   - Test on Linux with Intel/AMD GPU

7. **Time-shift / DVR** (larger, depends on other features being stable)
   - Modify HLS flags in all workers
   - DVR playlist manager service
   - Viewer page controls (pause, seek, live button)
   - Storage management (auto-delete old segments)

---

## 4. Kodi Push Integration ✅

### Goal
After XMLTV/M3U generation, automatically notify Kodi to reload its channel list and EPG data — so schedule changes appear instantly instead of waiting for the next poll interval.

### Problem
Currently, Kodi IPTV Simple Client polls the XMLTV/M3U URLs at a fixed interval (default: every 4-24 hours). When schedules change:
- User clicks "Generate XMLTV" in AkiraTV
- Kodi doesn't see the update until its next poll
- User must manually restart the IPTV Simple Client addon in Kodi

### Solution
Kodi exposes a JSON-RPC API on port 8080 (by default). After XMLTV regeneration, AkiraTV sends two commands:

```bash
POST http://kodi_ip:8080/jsonrpc
{"jsonrpc":"2.0","method":"PVR.TriggerChannelUpdate","id":1}
{"jsonrpc":"2.0","method":"PVR.TriggerEPGUpdate","id":2}
```

### Files to modify

**`akiratv/api_server.py`** — Add `notify_kodi()` call at the end of `generate_xmltv()`:

```python
def notify_kodi(config):
    """Notify Kodi to reload channels and EPG via JSON-RPC."""
    kodi_conf = config.get("kodi", {})
    if not kodi_conf.get("enabled"):
        return
    url = f"http://{kodi_conf['host']}:{kodi_conf['port']}/jsonrpc"
    requests_post = __import__("requests").post  # noqa
    import requests
    payloads = [
        {"jsonrpc": "2.0", "method": "PVR.TriggerChannelUpdate", "id": 1},
        {"jsonrpc": "2.0", "method": "PVR.TriggerEPGUpdate", "id": 2},
    ]
    for payload in payloads:
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception:
            pass  # Kodi might be offline
```

Then call it before returning from `generate_xmltv()`:
```python
notify_kodi(config)
```

**`config.json`** — Add Kodi configuration:
```json
"kodi": {
    "enabled": true,
    "host": "192.168.1.50",
    "port": 8080
}
```

### OBS Integration

When the Live Channel Worker starts/stops, optionally notify Kodi to update its channel list:
```python
if self.config.data.get("kodi", {}).get("enabled"):
    notify_kodi(self.config.data)
```

### Web UI

Optional: Add Kodi configuration fields (host, port, enabled) to the Configuration panel in the web UI.

### JSON-RPC details

Kodi's JSON-RPC API v6:
- Port: `8080` (default), configurable in Kodi → Settings → Services → Control → Allow remote control
- Endpoint: `POST http://<kodi_ip>:<port>/jsonrpc`
- Content-Type: `application/json`
- Auth: optional (if Kodi has a password set, use HTTP basic auth with user `kodi`)

Relevant methods:
| Method | Purpose |
|---|---|
| `PVR.TriggerChannelUpdate` | Reload channel list from M3U |
| `PVR.TriggerEPGUpdate` | Reload EPG data from XMLTV |
| `PVR.GetChannelGroups` | Fetch channel groups (to verify connection) |

### Kodi setup (one-time)

1. Kodi → Settings → Services → Control → Allow remote control on port 8080 ✅
2. IPTV Simple Client → Configure M3U URL and XMLTV URL (as currently)
3. AkiraTV config → add Kodi IP address
4. Generate XMLTV once → Kodi updates instantly

### Effect

| Before | After |
|---|---|
| Generate XMLTV → Kodi sees changes in 1-4 hours | Generate XMLTV → Kodi sees changes in ~2 seconds |

### Dependencies

- `requests` library (already used in other parts of AkiraTV? If not, it's in `requirements.txt` already)

---

## 5. Hardware Encoding via VAAPI

### Goal
Add VAAPI support for hardware-accelerated transcoding on Linux. Currently supports NVENC (Nvidia), QSV (Intel), AMF (AMD) — VAAPI is the missing standard Linux API that works with Intel, AMD, and some Nvidia GPUs.

### How VAAPI works
- VAAPI (Video Acceleration API) is the standard hardware video acceleration API for Linux
- FFmpeg uses it via `-vaapi_device /dev/dri/renderD128` and `-hwaccel vaapi`
- Supported encoders: `h264_vaapi`, `hevc_vaapi`, `mpeg2_vaapi`, `vp9_vaapi`
- Works with: Intel integrated GPUs, AMD dedicated/integrated GPUs, Nvidia (via NVDEC + VAAPI interop)

### Check if VAAPI is available

```bash
# Check if render device exists
ls -l /dev/dri/

# Check VAAPI support in FFmpeg
ffmpeg -hide_banner -encoders | grep vaapi

# Check VAAPI drivers
vainfo
```

### Files to modify

**`akiratv/workers/transcoding.py`** — Add VAAPI encoder option:

```python
# In get_encoding_args() or a similar method
if encoder == "vaapi":
    vaapi_device = "/dev/dri/renderD128"
    
    # Must use hardware frames
    args = [
        "-vaapi_device", vaapi_device,
        "-hwaccel", "vaapi",
        "-hwaccel_output_format", "vaapi",
    ]
    
    if not encoding_config.get("enabled"):
        return args  # Just hwaccel, no transcode
    
    # Transcoding with VAAPI
    video_quality = encoding_config.get("video_quality", "balanced")
    if video_quality == "high":
        global_quality = 18
    elif video_quality == "balanced":
        global_quality = 23
    else:
        global_quality = 28
    
    args += [
        "-c:v", "h264_vaapi",
        "-global_quality", str(global_quality),
        "-c:a", "aac",
        "-b:a", "128k",
    ]
    return args
```

**`akiratv/config.py`** — Add VAAPI to the transcoding encoder options:
```python
encoder = encoding_config.get("encoder", "auto")
# ... existing NVENC/QSV/AMF checks ...
if encoder == "vaapi" or (encoder == "auto" and is_vaapi_available()):
    use_vaapi()
```

### Config format

```json
"ffmpeg": {
    "transcoding": {
        "enabled": true,
        "encoder": "vaapi",
        "video_quality": "balanced"
    }
}
```

### Web UI
Add "VAAPI" to the encoder dropdown in Configuration → Transcoding settings.

### Testing

```bash
# Test VAAPI transcode directly
ffmpeg -vaapi_device /dev/dri/renderD128 -hwaccel vaapi \
  -hwaccel_output_format vaapi -i input.mp4 \
  -c:v h264_vaapi -global_quality 23 -c:a copy \
  -f hls -hls_time 6 output.m3u8

# Check if output is actually using GPU
ffmpeg -vaapi_device /dev/dri/renderD128 ... 2>&1 | grep "hwaccel"
```

---

## 6. Now Playing Dashboard

### Goal
Add a visible panel on the main dashboard showing what's currently streaming on each channel — video title, time remaining, viewer count. The data exists in `AKIRATV_STATS` but isn't displayed prominently.

### What to show

```
┌─────────────────────────────────────────────────┐
│  📺 NOW PLAYING                                  │
├────────────┬───────────────────┬───────┬─────────┤
│ Channel    │ Now Playing       │ Time  │ Viewers │
├────────────┼───────────────────┼───────┼─────────┤
│ 🎬 Movies  │ Die Hard          │ 45:23 │    2    │
│ 📺 TatkoTV │ The Simpsons S3E1 │ 12:07 │    1    │
│ 🔴 Live    │ [LIVE] OBS Stream │ 1:02  │    0    │
└────────────┴───────────────────┴───────┴─────────┘
```

### Files to modify

**`akiratv/static/index.html`** — Add a "Now Playing" section after the control panel:
```html
<div class="section">
    <div class="section-title">📺 Now Playing</div>
    <div id="nowPlayingGrid" class="now-playing-grid">
        <!-- populated by JS -->
    </div>
</div>
```

**`akiratv/static/styles.css`** — Add styles for the grid.

**`akiratv/static/app.js`** — Add function to fetch and display now-playing data:

```javascript
async function updateNowPlaying() {
    try {
        const status = await apiCall('/api/status');
        // status.stats.now_playing, status.stats.next_program
        const channels = await apiCall('/api/channels');
        
        const grid = document.getElementById('nowPlayingGrid');
        grid.innerHTML = channels.channels.map(ch => {
            return `
                <div class="now-playing-card">
                    <div class="np-channel">${ch.name}</div>
                    <div class="np-title">${ch.now_playing || 'Waiting for schedule...'}</div>
                    <div class="np-meta">
                        <span>👁️ ${ch.viewers ?? 0}</span>
                        <span>⏱️ ${ch.uptime || '--:--'}</span>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        // silently fail, update will retry
    }
}

// Update every 5 seconds
setInterval(updateNowPlaying, 5000);
```

**`akiratv/core_api.py`** — Ensure `get_channels()` returns `now_playing` and `viewers` per channel (already partially exists in stats).

### Data source
- `core_api.py` already tracks per-channel stats via `AKIRATV_STATS` and `ACTIVE_CONNECTIONS`
- The `/api/channels` endpoint can include each channel's current status
- For time remaining: calculate from video duration (from collection) minus how long it's been playing

### Update interval
- Refresh the now-playing grid every 5 seconds (same as the status bar)
- No visible flicker — just update text content in-place

---

## 7. Stream Health Panel

### Goal
Add a dashboard panel showing all channels, their FFmpeg process status (running/stopped/frozen), uptime, and a restart button per channel. Currently you have to check logs or inspect each channel card individually.

### What to show

```
┌─────────────────────────────────────────────────────────┐
│  ❤️ Stream Health                                        │
├────────────┬──────────┬─────────┬────────┬──────────────┤
│ Channel    │ Status   │ Uptime  │ Viewer │ Action       │
├────────────┼──────────┼─────────┼────────┼──────────────┤
│ 🎬 Movies  │ 🟢 Live  │ 2:34:12 │ 2      │ [Restart]    │
│ 📺 TatkoTV │ 🟡 Idle  │ 0:12:05 │ 0      │ [Restart]    │
│ 🔴 Live    │ 🔴 Down  │ 0:00:00 │ 0      │ [Start]      │
└────────────┴─────────────────────────────────────────────┘
```

### Files to modify

**`akiratv/static/index.html`** — Add a "Stream Health" section.

**`akiratv/static/app.js`** — Add `updateStreamHealth()` function.

**`akiratv/routes/lifecycle.py`** — Add a new endpoint `GET /api/health` that returns per-channel status:

```python
@router.get("/health")
def stream_health(api = Depends(get_core_api)):
    """Get detailed per-channel health status"""
    channels = api.get_channels()
    health_data = []
    for ch in channels:
        health_data.append({
            "name": ch.name,
            "type": ch.type,
            "status": ch.status,        # "running", "stopped", "error"
            "uptime": ch.uptime,
            "viewers": ch.viewers,
            "has_process": ch.process_alive,
            "last_error": ch.last_error
        })
    return {"channels": health_data, "total": len(health_data), "healthy": sum(1 for h in health_data if h["status"] == "running")}
```

**`akiratv/core_api.py`** (or wherever channel data is managed) — Ensure per-channel status is tracked:
- `worker.is_running` → channel status
- Worker watchdog → detect frozen processes
- Track `last_error` and `uptime` per channel

### Status definitions

| Status | Meaning |
|---|---|
| 🟢 Live | FFmpeg running, segments being produced |
| 🟡 Idle | Worker alive but waiting (live worker waiting for OBS, linear worker between restarts) |
| 🔴 Down | Worker process exited unexpectedly |
| ⚫ Disabled | Channel not enabled in config |

### Actions per channel
- **Restart** — `POST /api/channels/{channel}/restart` (already exists in `channels.py` for linear channels)
- **Enable/Disable** — `POST /api/channels/{channel}/enable` / `POST /api/channels/{channel}/disable`
- **View Logs** — link to recent log entries for this channel

### Auto-refresh
- Health data refreshes every 10 seconds
- Status color changes are animated (CSS transition) for visual attention
- If a channel goes from 🟢 to 🔴, flash the row briefly

### Future: Alerts
- Optional desktop notification or web UI toast when a channel goes down
- "Restart all failed channels" button
- Historical health data (uptime percentage per channel over last 24h)
