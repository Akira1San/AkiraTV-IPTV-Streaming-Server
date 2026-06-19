# AkiraTV - Local IPTV Streaming Server

<div align="center">
  <img src="logo.png" alt="AkiraTV Logo" width="200"/>
  
  **Transform your video collection into professional IPTV channels**
  
  [![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
  [![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/yourusername/akiratv)
</div>

## 🌟 Features

### 📺 **Multi-Channel Linear TV Streaming**
- Create unlimited IPTV channels from your video collection
- Scheduled programming with weekly/daily schedules
- Live-TV seeking (join programs mid-stream)
- Continuous playback without bumpers or interruptions

### 🎬 **Multiple Channel Types**
- **Linear**: Traditional TV with scheduled programming
- **VOD**: Video-on-demand with API/UI control
- **Dynamic**: Standby loops + VOD interruptions + optional schedules

### 🌐 **Professional Web Interface**
- Modern, responsive dark theme UI
- Real-time channel management and monitoring
- Complete TV Guide with daily/weekly views
- Mobile-friendly design for phone/tablet access
- **Bilingual Support**: English/Bulgarian interface

### 📅 **Advanced TV Guide**
- Complete weekly program schedules (Monday-Sunday)
- Current/next program display with real-time updates
- Program highlighting and time indicators
- Responsive grid layout for all screen sizes

### 🔧 **Powerful Configuration**
- Per-channel transcoding and subtitle settings
- Global and channel-specific configurations
- Hardware acceleration support (NVENC, QSV, AMF)
- RAM-disk acceleration with ImDisk support

### 🎯 **Smart Streaming**
- HLS streaming with `-c copy` (zero CPU usage by default)
- Optional transcoding for bandwidth optimization
- Multiple streaming URLs (LAN, Tailscale)
- Kodi XMLTV/M3U integration

### 🚀 **Easy Deployment**
- One-click startup with batch files
- Network sharing via Tailscale for secure remote access
- RESTful API for automation and integration
- WebSocket support for real-time updates

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** with pip
- **FFmpeg** (for video processing)
- **Windows/Linux/macOS** (Windows batch files included)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/akiratv.git
   cd akiratv
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg**
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - **Linux**: `sudo apt install ffmpeg` (Ubuntu/Debian)
   - **macOS**: `brew install ffmpeg`

4. **Configure your channels**
   - Create channel schedules in `user/schedules/ schedule_name.json` and user/collections/ collection_name.json
   - Add channel logos to `user/channels/ "tv channel name"/ logo.png`

5. **Start AkiraTV**
   ```bash
   # Web Interface (recommended)
   ./launch_web.sh
   
   # Windows
   launch_web.bat
   
   # Old Tkinter desktop UI (legacy)
   # RUN_AkiraTV.sh
   ```

6. **Access the Web Interface**
   - Local: http://localhost:8000
   - Network: http://YOUR_IP:8000

## 📖 Usage Guide

### Creating Your First Channel

1. **Create a Collection**: Use the [Collection Manager](https://github.com/Akira1San/Collection-manager)
   to scan your video folder and generate a collection JSON file
2. **Create a Schedule**: Use [Day2](https://github.com/Akira1San/Day2) to build a programming
   schedule from your collection
3. **Start the Server**: Run `./launch_web.sh`
4. **Add Channels**: Open the web UI → **Configuration** → add your channels (stored in `config.json`)
5. **Press Stream**: Click **Start Streaming** in the control panel

### Channel Types Explained

#### 📺 Linear Channels
Traditional TV channels with scheduled programming:
```json
{
  "weekly": {
    "monday": [
      {
        "time": "20:00:00",
        "file": "/path/to/movie.mp4",
        "channel": "movies"
      }
    ]
  }
}
```

#### 🎬 VOD Channels
On-demand video playback controlled via API/UI:
- Play any video instantly
- Stop/start control
- Perfect for manual content control

#### 🔄 Dynamic Channels
Combines standby loops with VOD interruptions:
- Plays standby content when idle
- Accepts VOD interruptions
- Returns to standby after playback

### Web Interface Features

#### 🎮 Control Panel
- **Start/Stop/Restart**: Engine control
- **Clear Cache**: Remove temporary files
- **Clear Logs**: Clear log files (logs auto-rotate at 5MB, 3 backups kept)
- **Reload Schedules**: Update programming
- **Configuration**: Global settings
- **TV Guide**: Daily/weekly program guide
- **Viewer**: Watch channels in the browser
- **Video Library**: Browse and manage video files
- **Generate XMLTV**: Create Kodi-compatible files
- **Wizard**: Collection and scheduler setup tool -  abandon
- **Exit**: Stop engine and shut down the server

#### 📺 TV Guide
- **Daily View**: Current/next programs + today's schedule
- **Weekly View**: Complete Monday-Sunday programming
- **Real-time Updates**: Current program highlighting
- **Language Support**: English/Bulgarian interface

#### 📡 Channel Management
- **Enable/Disable**: Toggle channels on/off
- **Settings**: Per-channel transcoding/subtitles
- **Controls**: Stop/restart individual channels
- **URLs**: Copy streaming links for Kodi/VLC

#### 🎵 Playlist Controls
- **Play Now**: Instant video playback on VOD channels
- **Create Playlists**: Generate from video folders
- **Playlist Selection**: Choose and play from playlists
- **Standby Loops**: Create resolution-specific standby videos

## ⚙️ Configuration

### Basic Configuration (`config.json`)

```json
{
  "ffmpeg": {
    "transcoding": {
      "enabled": false,
      "bitrate": "auto",
      "video_quality": "source",
      "encoder": "auto"
    },
    "enable_subtitles": false
  },
  "storage": {
    "type": "disk",
    "disk_path": "./output"
  },
  "output": {
    "http": {
      "port": 8081,
      "bind": "0.0.0.0"
    }
  },
  "channels": {
    "movies": {
      "enabled": true,
      "type": "linear"
    }
  }
}
```

### Channel Schedule Format

```json
{
  "weekly": {
    "monday": [
      {
        "time": "00:00:00",
        "file": "C:/Videos/movie1.mp4",
        "channel": "movies",
        "source": "scheduled"
      },
      {
        "time": "02:30:00",
        "file": "C:/Videos/movie2.mp4",
        "channel": "movies",
        "source": "scheduled"
      }
    ],
    "tuesday": [...]
  }
}
```

### Transcoding Settings

AkiraTV supports multiple transcoding options:

- **Stream Copy** (Default): Zero CPU usage, original quality
- **Software Transcoding**: CPU-based encoding
- **Hardware Acceleration**: NVENC, QSV, AMF support

## 🌐 Network Access & Streaming URLs

AkiraTV provides multiple streaming URL options for different access scenarios:

### 📡 **Available Streaming URLs**

When you enable a channel, AkiraTV automatically generates multiple streaming URLs:

#### 🏠 **Local/LAN Access**
```
http://192.168.1.100:8081/hls/channelname/index.m3u8
```
- **Use for**: Local network streaming (same WiFi/Ethernet)
- **Best for**: Home devices, Kodi on local network
- **Bandwidth**: No internet bandwidth usage
- **Speed**: Fastest, direct connection

#### 🌐 **Tailscale Access** (Secure VPN)
```
http://100.64.1.2:8081/hls/channelname/index.m3u8
```
- **Use for**: Secure remote access via Tailscale VPN
- **Best for**: Personal devices anywhere in the world
- **Setup**: Install Tailscale on server and client devices
- **Security**: End-to-end encrypted, no public exposure
- **Learn more**: [tailscale.com](https://tailscale.com)

#### 🔒 **Localhost** (Development)
```
http://127.0.0.1:8081/hls/channelname/index.m3u8
```
- **Use for**: Local testing and development
- **Best for**: Same machine access only
- **Bandwidth**: No network usage

### 🎯 **Choosing the Right URL**

| Scenario | Recommended URL | Why |
|----------|----------------|-----|
| **Kodi on same network** | LAN (192.168.x.x) | Fastest, no internet needed |
| **Phone at home** | LAN (192.168.x.x) | Best performance, no data usage |
| **Remote access (secure)** | Tailscale | Encrypted, always works |
| **Testing locally** | Localhost | Development and testing |

### 🛠️ **Setup Instructions**

#### **Tailscale Setup** (Recommended for remote access)
1. **Install Tailscale** on your AkiraTV server:
   ```bash
   # Windows: Download from tailscale.com
   # Linux: curl -fsSL https://tailscale.com/install.sh | sh
   # macOS: brew install tailscale
   ```

2. **Connect your server**:
   ```bash
   sudo tailscale up
   ```

3. **Install Tailscale** on client devices (phone, laptop, etc.)

4. **Use Tailscale IP** in streaming URLs (usually starts with 100.x.x.x)

### 📱 **Mobile Access Examples**

#### **Kodi on Android/iOS**
```
M3U URL: http://192.168.1.100:8081/channels.m3u
XMLTV URL: http://192.168.1.100:8081/xmltv.xml
```

#### **VLC Media Player**
```
Network Stream: http://192.168.1.100:8081/hls/movies/index.m3u8
```

#### **Web Browser**
```
AkiraTV Interface: http://192.168.1.100:8000
```

### 🔐 **Security Considerations**

#### **LAN URLs** 🏠
- ✅ **Safe**: Only accessible on your local network
- ✅ **Fast**: Direct connection, no internet routing
- ❌ **Limited**: No remote access

#### **Tailscale URLs** 🌐
- ✅ **Secure**: End-to-end encrypted VPN
- ✅ **Private**: Not publicly accessible
- ✅ **Reliable**: Works from anywhere
- ❌ **Setup**: Requires Tailscale on all devices

### 🔐 **Network Access Diagram**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Your Device   │    │   AkiraTV Server │    │  Streaming URLs │
│                 │    │                  │    │                 │
│ 🏠 Same Network │◄──►│ 192.168.1.100    │◄──►│ LAN: :8081/hls  │
│ 📱 Phone/Tablet │    │                  │    │                 │
│ 📺 Kodi/VLC     │    │ Ports:           │    │ Web/API: :8000  │
└─────────────────┘    │ • 8000 (Web/API) │    └─────────────────┘
                       │ • 8081 (Stream)  │    └─────────────────┘
┌─────────────────┐    │ • 8000 (API)     │    
│ 🌐 Remote Access│    └──────────────────┘    ┌─────────────────┐
│                 │                            │ Tailscale VPN   │
│ Tailscale VPN   │◄──────────────────────────►│ 100.x.x.x:8081  │
│ (Secure)        │                            │ (Encrypted)     │
└─────────────────┘                            └─────────────────┘
```

### 💡 **Pro Tips**

1. **Use LAN URLs** for best performance at home
2. **Set up Tailscale** for secure remote access
3. **Copy URLs** directly from the web interface
4. **Test URLs** in VLC before configuring Kodi
5. **Check firewall settings** if URLs don't work

### 📋 **Quick Reference - URL Templates**

Copy and modify these templates for your setup:

```bash
# Replace YOUR_IP with your server's IP address
# Replace CHANNEL_NAME with your actual channel name

# LAN Streaming URLs
http://YOUR_IP:8081/hls/CHANNEL_NAME/index.m3u8
http://YOUR_IP:8081/channels.m3u
http://YOUR_IP:8081/xmltv.xml

# Web Interface
http://YOUR_IP:8000

# Tailscale URLs (replace TAILSCALE_IP)
http://TAILSCALE_IP:8081/hls/CHANNEL_NAME/index.m3u8
```

**Example with real values:**
```bash
# LAN (192.168.1.100)
http://192.168.1.100:8081/hls/movies/index.m3u8
http://192.168.1.100:8000

# Tailscale (100.64.1.2)  
http://100.64.1.2:8081/hls/movies/index.m3u8
```

### Local Network
- **Web/API Access**: `http://YOUR_IP:8000`
- **Mobile Access**: Same URL works on phones/tablets

### Remote Access
- **Tailscale**: VPN-based secure access
- **Port Forwarding**: Traditional router setup

### Kodi Integration
1. Generate XMLTV/M3U files via web interface
2. Configure IPTV Simple Client:
   - **M3U URL**: `http://YOUR_IP:8081/channels.m3u`
   - **XMLTV URL**: `http://YOUR_IP:8081/xmltv.xml`

## 🔧 Advanced Features

### API Integration

AkiraTV provides a comprehensive REST API:

```bash
# Get channel status
GET /api/channels

# Start/stop channels
POST /api/channels/{channel}/enable
POST /api/channels/{channel}/disable

# Play video on VOD channel
POST /api/channels/{channel}/play
{
  "video_path": "/path/to/video.mp4"
}

# Get TV guide
GET /api/guide
GET /api/guide/weekly
```

### Automation Scripts

- **Web UI Launcher**: `launch_web.sh` / `launch_web.bat`
- **Desktop UI Launcher**: `RUN_AkiraTV.sh` / `RUN_AkiraTV.bat` (old Tkinter UI, legacy)

### Directory Structure

```
akiratv/
├── akiratv/           # Core application
├── assets/            # Standby videos
├── user/              # User configuration
│   ├── channels/      # Channel logos
│   ├── collections/   # Video collections
│   ├── schedules/     # Programming schedules
│   └── covers/        # Video thumbnails
├── playlists/         # Generated playlists
├── output/            # HLS output (or RAM disk)
└── videos/            # Video storage
```

## 🛠️ Development

### Running from Source

```bash
# Install development dependencies
pip install -r requirements.txt

# Run the application
python -m akiratv

# Run web interface only
python launch_web.py
```

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📱 Mobile Support

AkiraTV's web interface is fully responsive:
- **Touch-friendly**: Optimized for mobile interaction
- **Responsive Design**: Adapts to all screen sizes
- **Network Access**: Access from any device on your network
- **Full Functionality**: All features available on mobile

## 🌍 Language Support

- **English**: Full interface translation
- **Bulgarian**: Complete Bulgarian localization
- **Persistent Preference**: Language choice saved across sessions
- **Easy Extension**: Translation system ready for additional languages

## 🔍 Troubleshooting

### Common Issues

**Server won't start**
- Check if ports 8000/8081 are available
- Verify Python and FFmpeg installation
- Check logs in `logs/` directory

**Videos won't play**
- Verify video file paths in schedules
- Check FFmpeg can process your video files
- Ensure proper file permissions

**High CPU usage**
- Disable transcoding for lower CPU usage
- Use hardware acceleration if available
- Check if multiple channels are transcoding simultaneously

**Network access issues**
- Verify firewall settings
- Check if server is binding to `0.0.0.0`
- Ensure network connectivity between devices

### Log Files
- **Application Logs**: `logs/worker.log` (auto-rotates at 5MB, keeps 3 backups)
- **Web Server**: Console output
- **Clear Logs**: Use the **Clear Logs** button in the web UI control panel

## 📄 License

Free AI Generated - vibe

## 🙏 Acknowledgments

- **FFmpeg**: Video processing engine
- **FastAPI**: Modern web framework
- **Vue.js**: Reactive web interface components
- **HLS.js**: HTML5 video streaming


---

<div align="center">
  <strong>Made with ❤️ for the IPTV community</strong>
  
  [⭐ Star this project](https://github.com/yourusername/akiratv) if you find it useful!
</div>
