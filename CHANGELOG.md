# Changelog

All notable changes to AkiraTV will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-01-30

### Added
- **Complete Web Interface Redesign**
  - Modern, responsive dark theme UI
  - Mobile-friendly design for phone/tablet access
  - Real-time channel management and monitoring
  - Professional control panel with all engine functions

- **Advanced TV Guide System**
  - Daily view with current/next program display
  - Weekly view showing complete Monday-Sunday schedules
  - Real-time program highlighting and time indicators
  - Responsive grid layout adapting to all screen sizes

- **Bilingual Interface Support**
  - English/Bulgarian language switcher
  - Complete translation system with localStorage persistence
  - All UI elements, messages, and notifications translated
  - Easy extension system for additional languages

- **Enhanced Channel Management**
  - Per-channel transcoding and subtitle settings
  - Individual channel start/stop/restart controls
  - Channel enable/disable toggles with immediate config persistence
  - Channel creation with type selection (Linear/VOD/Dynamic)
  - Channel deletion with confirmation dialogs

- **Professional Streaming URLs**
  - Multiple URL variants (LAN, Tailscale, Ngrok)
  - Real streaming server URLs instead of API server URLs
  - One-click URL copying for Kodi/VLC integration
  - Automatic IP detection and URL generation

- **Comprehensive Playlist Controls**
  - Play Now functionality for VOD channels
  - Playlist creation from video folders
  - Playlist selection and video playback
  - Standby loop generation for all resolutions
  - Stop controls for active playback

- **RESTful API Enhancement**
  - Complete FastAPI-based REST API
  - WebSocket support for real-time updates
  - Comprehensive endpoint coverage for all functions
  - API documentation with Swagger UI
  - Channel-specific operations and settings

- **Network and Mobile Access**
  - Server binding to 0.0.0.0 for network access
  - Mobile-optimized interface design
  - Touch-friendly controls and navigation
  - Responsive layouts for all screen sizes

### Improved
- **Performance Optimization**
  - Zero CPU usage when idle (no auto-reload in production)
  - Efficient WebSocket connections without polling
  - Optimized API calls and data loading
  - Reduced server resource usage

- **User Experience**
  - Intuitive channel management workflow
  - Clear visual feedback for all actions
  - Professional toast notifications system
  - Loading states and error handling

- **Configuration Management**
  - Immediate config.json persistence
  - Per-channel setting overrides
  - Global and channel-specific configurations
  - Settings validation and error handling

### Fixed
- **API Server CPU Usage**
  - Eliminated high CPU usage from uvicorn auto-reload
  - Removed unnecessary WebSocket polling
  - Optimized server startup and shutdown

- **Channel Loading Issues**
  - Fixed working directory problems
  - Corrected config.json loading paths
  - Resolved channel visibility issues

- **Mobile Access Problems**
  - Fixed server binding for network access
  - Resolved mobile browser compatibility
  - Corrected responsive design issues

### Technical Details
- **Framework**: FastAPI with uvicorn server
- **Frontend**: Vanilla JavaScript with modern ES6+ features
- **Styling**: CSS Grid and Flexbox for responsive layouts
- **API**: RESTful endpoints with comprehensive error handling
- **WebSocket**: Real-time updates without polling
- **Storage**: localStorage for user preferences
- **Internationalization**: Complete i18n system with translation functions

### Migration Notes
- Web interface now runs on port 8001 by default
- API server provides all functionality previously in main application
- Configuration format remains compatible with previous versions
- All existing channel schedules and settings are preserved

## [1.x.x] - Previous Versions

### Legacy Features
- Core IPTV streaming functionality
- FFmpeg-based video processing
- HLS output generation
- Basic channel scheduling
- Command-line interface
- Batch file automation scripts

---

For older versions and detailed commit history, see the [Git log](https://github.com/yourusername/akiratv/commits/main).