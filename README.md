# AkiraTV - Local IPTV Streaming Server

<div align="center">
  <img src="logo.png" alt="AkiraTV Logo" width="200"/>
  
  **Transform your video collection into professional IPTV channels**
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
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
- Multiple streaming URLs (LAN, Tailscale, Ngrok)
- Kodi XMLTV/M3U integration

### 🚀 **Easy Deployment**
- One-click startup with batch files
- Network sharing via Ngrok for global access
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
   - Edit `config.json` to add your video directories
   - Create channel schedules in `user/schedules/`
   - Add channel logos to `user/channels/`

5. **Start AkiraTV**
   ```bash
   # Windows
   RUN_AkiraTV.bat
   
   # Linux/macOS
   python -m akiratv
   ```

6. **Access the Web Interface**
   - Local: http://localhost:8001
   - Network: http://YOUR_IP:8001

## 📖 Usage Guide

### Creating Your First Channel

1. **Add Videos**: Place your video files in a directory
2. **Create Channel**: Use the web interface to add a new channel
3. **Configure Schedule**: Create a schedule file in `user/schedules/`
4. **Add Logo**: Place channel logo in `user/channels/CHANNEL_NAME/`
5. **Enable Channel**: Toggle the channel on in the web interface

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
- **Reload Schedules**: Update programming
- **Configuration**: Global settings
- **Generate XMLTV**: Create Kodi-compatible files

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

See [README_TRANSCODING.txt](README_TRANSCODING.txt) for detailed transcoding guide.

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

#### 🌍 **Ngrok Access** (Public Tunnel)
```
http://abc123.ngrok-free.app/hls/channelname/index.m3u8
```
- **Use for**: Temporary public access, sharing with friends
- **Best for**: Quick sharing, testing, demonstrations
- **Setup**: Install ngrok and create tunnel
- **Security**: Public URL, consider authentication
- **Learn more**: [ngrok.com](https://ngrok.com)

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
| **Sharing with friends** | Ngrok | Easy setup, temporary sharing |
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

#### **Ngrok Setup** (For public access)
1. **Install ngrok**:
   ```bash
   # Download from ngrok.com and extract
   # Add to PATH or use full path
   ```

2. **Create tunnel**:
   ```bash
   ngrok http 8081
   ```

3. **Use the generated URL** (e.g., `abc123.ngrok-free.app`)

4. **For permanent URLs**: Upgrade to ngrok paid plan

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
AkiraTV Interface: http://192.168.1.100:8001
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

#### **Ngrok URLs** 🌍
- ✅ **Easy**: Quick public access
- ✅ **Shareable**: Send URL to friends
- ❌ **Public**: Anyone with URL can access
- ❌ **Temporary**: Free URLs change frequently

### � **Network Access Diagram**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Your Device   │    │   AkiraTV Server │    │  Streaming URLs │
│                 │    │                  │    │                 │
│ 🏠 Same Network │◄──►│ 192.168.1.100    │◄──►│ LAN: :8081/hls  │
│ 📱 Phone/Tablet │    │                  │    │                 │
│ 📺 Kodi/VLC     │    │ Ports:           │    │ Web: :8001      │
└─────────────────┘    │ • 8001 (Web UI)  │    │ API: :8000      │
                       │ • 8081 (Stream)  │    └─────────────────┘
┌─────────────────┐    │ • 8000 (API)     │    
│ 🌐 Remote Access│    └──────────────────┘    ┌─────────────────┐
│                 │                            │ Tailscale VPN   │
│ Tailscale VPN   │◄──────────────────────────►│ 100.x.x.x:8081  │
│ (Secure)        │                            │ (Encrypted)     │
└─────────────────┘                            └─────────────────┘

┌─────────────────┐                            ┌─────────────────┐
│ 🌍 Public Access│                            │ Ngrok Tunnel    │
│                 │◄──────────────────────────►│ abc.ngrok.app   │
│ Ngrok Tunnel    │                            │ (Temporary)     │
│ (Share/Demo)    │                            └─────────────────┘
└─────────────────┘
```

### 💡 **Pro Tips**

1. **Use LAN URLs** for best performance at home
2. **Set up Tailscale** for secure remote access
3. **Use Ngrok** only for temporary sharing
4. **Copy URLs** directly from the web interface
5. **Test URLs** in VLC before configuring Kodi
6. **Check firewall settings** if URLs don't work

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
http://YOUR_IP:8001

# Tailscale URLs (replace TAILSCALE_IP)
http://TAILSCALE_IP:8081/hls/CHANNEL_NAME/index.m3u8

# Ngrok URLs (replace NGROK_SUBDOMAIN)
http://NGROK_SUBDOMAIN.ngrok-free.app/hls/CHANNEL_NAME/index.m3u8
```

**Example with real values:**
```bash
# LAN (192.168.1.100)
http://192.168.1.100:8081/hls/movies/index.m3u8
http://192.168.1.100:8001

# Tailscale (100.64.1.2)  
http://100.64.1.2:8081/hls/movies/index.m3u8

# Ngrok (abc123.ngrok-free.app)
http://abc123.ngrok-free.app/hls/movies/index.m3u8
```

### Local Network
- **LAN Access**: `http://YOUR_IP:8001`
- **Mobile Access**: Same URL works on phones/tablets

### Remote Access
- **Ngrok**: Tunnel for global access
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

- **Collection Wizard**: `collection_wizard.bat`
- **Simple Scheduler**: `simple_scheduler.bat`
- **Daypart Scheduler**: `Daypart_scheduler.bat`

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

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

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
- Check if ports 8000/8001/8081 are available
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
- **Application Logs**: `logs/worker.log`
- **Scheduler Logs**: `daypart_scheduler.log`
- **Web Server**: Console output

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/akiratv/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/akiratv/discussions)
- **Documentation**: [Wiki](https://github.com/yourusername/akiratv/wiki)

## 🙏 Acknowledgments

- **FFmpeg**: Video processing engine
- **FastAPI**: Modern web framework
- **Vue.js**: Reactive web interface components
- **HLS.js**: HTML5 video streaming
- **Community**: Contributors and users

---

<div align="center">
  <strong>Made with ❤️ for the IPTV community</strong>
  
  [⭐ Star this project](https://github.com/yourusername/akiratv) if you find it useful!
</div>