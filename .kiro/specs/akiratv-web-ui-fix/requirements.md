# Requirements Document

## Introduction

This specification addresses critical issues with the AkiraTV web UI and establishes it as the primary interface for managing the streaming system. The current web UI only displays 2 channels ("MyAkiraTV" and "live") when 11 channels are configured, and lacks comprehensive management capabilities present in the desktop interface.

## Glossary

- **AkiraTV_System**: The complete streaming engine including backend API, channel workers, and configuration management
- **Web_UI**: The HTML/CSS/JavaScript frontend interface served at the root endpoint
- **Channel_Discovery**: The process of identifying all available channels from config.json and schedule files
- **Channel_Worker**: Individual streaming processes that handle content delivery for each channel
- **Core_API**: The Python API layer that interfaces between the web UI and the AkiraTV engine
- **Schedule_File**: JSON files in user/schedules/ that define programming schedules for linear channels
- **Config_Channel**: Channel definitions stored in the main config.json file
- **HLS_Stream**: HTTP Live Streaming output format used for video delivery
- **VOD_Channel**: Video-on-demand channel type that allows immediate video playback
- **Linear_Channel**: Traditional TV-style channel that follows a predetermined schedule
- **Dynamic_Channel**: Channel type that supports both scheduled and on-demand content

## Requirements

### Requirement 1: Fix Channel Discovery

**User Story:** As a system administrator, I want all configured channels to appear in the web UI, so that I can manage the complete streaming system.

#### Acceptance Criteria

1. WHEN the web UI loads channel data, THE AkiraTV_System SHALL discover channels from both config.json and user/schedules/ directory
2. WHEN schedule files exist in user/schedules/, THE Channel_Discovery SHALL include channels with schedule_*.json files even if not in config.json
3. WHEN a channel exists in both config.json and has a schedule file, THE AkiraTV_System SHALL merge the configuration data
4. WHEN the /api/channels endpoint is called, THE Core_API SHALL return all 11 configured channels with correct status information
5. WHEN channels are discovered, THE AkiraTV_System SHALL preserve channel type, enabled status, and configuration settings

### Requirement 2: Enhanced Channel Management

**User Story:** As a system administrator, I want comprehensive channel management controls, so that I can configure and control all channels without using the desktop interface.

#### Acceptance Criteria

1. WHEN viewing a channel in the web UI, THE Web_UI SHALL display channel name, type, enabled status, current status, and streaming URL
2. WHEN a channel is enabled, THE Web_UI SHALL provide toggle controls to enable/disable channels with immediate visual feedback
3. WHEN managing channel settings, THE Web_UI SHALL allow modification of transcoding settings, subtitle options, and channel type
4. WHEN changes are made to channel configuration, THE AkiraTV_System SHALL persist changes to config.json immediately
5. WHEN a channel configuration is updated, THE Web_UI SHALL reflect changes without requiring page refresh

### Requirement 3: Real-time Channel Status

**User Story:** As a system administrator, I want real-time status updates for all channels, so that I can monitor system health and performance.

#### Acceptance Criteria

1. WHEN a channel worker starts or stops, THE Web_UI SHALL update the channel status indicator within 2 seconds
2. WHEN displaying channel information, THE Web_UI SHALL show current viewer count, uptime, and now-playing information
3. WHEN the streaming engine status changes, THE Web_UI SHALL update the global status badge and statistics
4. WHEN WebSocket connection is active, THE AkiraTV_System SHALL broadcast channel status changes to all connected clients
5. WHEN network connectivity is lost, THE Web_UI SHALL display connection status and attempt automatic reconnection

### Requirement 4: Advanced Channel Controls

**User Story:** As a content manager, I want advanced channel control features, so that I can manage content playback and scheduling effectively.

#### Acceptance Criteria

1. WHEN managing a VOD_Channel, THE Web_UI SHALL provide file browser interface for selecting videos to play immediately
2. WHEN managing a Linear_Channel, THE Web_UI SHALL display current schedule information and allow schedule modifications
3. WHEN managing a Dynamic_Channel, THE Web_UI SHALL support both scheduled programming and immediate video playback
4. WHEN controlling channel playback, THE Web_UI SHALL provide start, stop, restart, and skip controls for individual channels
5. WHEN viewing channel logs, THE Web_UI SHALL display recent activity and error messages for troubleshooting

### Requirement 5: Configuration Management Interface

**User Story:** As a system administrator, I want a complete configuration management interface, so that I can modify all system settings through the web UI.

#### Acceptance Criteria

1. WHEN accessing system configuration, THE Web_UI SHALL provide forms for modifying FFmpeg settings, storage configuration, and output settings
2. WHEN updating configuration values, THE AkiraTV_System SHALL validate settings and provide immediate feedback on errors
3. WHEN saving configuration changes, THE AkiraTV_System SHALL create backup copies and allow rollback to previous configurations
4. WHEN configuration changes require restart, THE Web_UI SHALL clearly indicate restart requirements and provide restart controls
5. WHEN importing/exporting configuration, THE Web_UI SHALL support JSON file upload/download for configuration management

### Requirement 6: Enhanced User Experience

**User Story:** As a user, I want an intuitive and responsive web interface, so that I can efficiently manage the streaming system from any device.

#### Acceptance Criteria

1. WHEN using the web UI on mobile devices, THE Web_UI SHALL provide responsive design that adapts to screen size and touch input
2. WHEN performing actions, THE Web_UI SHALL provide loading indicators, progress feedback, and clear success/error messages
3. WHEN navigating the interface, THE Web_UI SHALL maintain consistent styling, keyboard shortcuts, and accessibility features
4. WHEN displaying large amounts of data, THE Web_UI SHALL implement pagination, filtering, and search capabilities
5. WHEN errors occur, THE Web_UI SHALL display helpful error messages with suggested solutions and recovery actions

### Requirement 7: System Monitoring and Diagnostics

**User Story:** As a system administrator, I want comprehensive monitoring and diagnostic tools, so that I can troubleshoot issues and optimize performance.

#### Acceptance Criteria

1. WHEN viewing system status, THE Web_UI SHALL display CPU usage, memory consumption, disk space, and network statistics
2. WHEN monitoring streams, THE Web_UI SHALL show bitrate information, viewer statistics, and stream health metrics
3. WHEN accessing logs, THE Web_UI SHALL provide real-time log viewing with filtering, search, and export capabilities
4. WHEN diagnosing issues, THE Web_UI SHALL include system health checks and automated diagnostic tools
5. WHEN performance issues occur, THE Web_UI SHALL provide alerts and recommendations for optimization

### Requirement 8: Library and Content Management

**User Story:** As a content manager, I want integrated library management tools, so that I can organize and manage video content effectively.

#### Acceptance Criteria

1. WHEN browsing the video library, THE Web_UI SHALL display file listings with metadata, thumbnails, and duration information
2. WHEN organizing content, THE Web_UI SHALL support folder navigation, file operations, and batch actions
3. WHEN adding new content, THE Web_UI SHALL provide upload capabilities and automatic metadata extraction
4. WHEN managing schedules, THE Web_UI SHALL offer drag-and-drop schedule editing with visual timeline interface
5. WHEN validating content, THE Web_UI SHALL check file integrity, format compatibility, and encoding requirements

### Requirement 9: Security and Access Control

**User Story:** As a system administrator, I want security controls and access management, so that I can protect the system from unauthorized access.

#### Acceptance Criteria

1. WHEN accessing the web UI, THE AkiraTV_System SHALL support authentication mechanisms and session management
2. WHEN managing user permissions, THE Web_UI SHALL provide role-based access control for different user types
3. WHEN logging system access, THE AkiraTV_System SHALL maintain audit logs of all configuration changes and user actions
4. WHEN securing communications, THE AkiraTV_System SHALL support HTTPS encryption and secure WebSocket connections
5. WHEN detecting suspicious activity, THE AkiraTV_System SHALL implement rate limiting and intrusion detection measures

### Requirement 10: Data Persistence and Backup

**User Story:** As a system administrator, I want reliable data persistence and backup capabilities, so that I can protect against data loss and system failures.

#### Acceptance Criteria

1. WHEN configuration changes are made, THE AkiraTV_System SHALL automatically create timestamped backup copies
2. WHEN system data is modified, THE AkiraTV_System SHALL ensure atomic operations and data consistency
3. WHEN backup operations are performed, THE Web_UI SHALL provide backup scheduling, restoration, and verification tools
4. WHEN data corruption is detected, THE AkiraTV_System SHALL provide recovery mechanisms and data repair utilities
5. WHEN exporting system data, THE AkiraTV_System SHALL support complete system state export for migration purposes