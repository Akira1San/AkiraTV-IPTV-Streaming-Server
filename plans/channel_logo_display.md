# Channel Logo Display Feature

## Summary
Implement channel logo display functionality during video playback with support for custom positioning, size, and opacity.

## Current Status
✅ **Planning Complete** - Ready for implementation

## Requirements
- Display channel logo during video playback
- Allow user to choose logo position (upper right, upper left, lower right, lower left, center)
- Configure logo size and opacity
- Support per-channel settings with global defaults
- Integrate with existing configuration system

## Architecture

### Configuration Structure
Add to `config.json`:
```json
{
  "channels": {
    "myAkiraTV": {
      "enabled": true,
      "type": "linear",
      "logo": {
        "enabled": true,
        "path": "path/to/logo.png",
        "position": "upper_right",
        "size": 100,
        "opacity": 0.8
      }
    }
  },
  "global": {
    "logo": {
      "enabled": true,
      "position": "upper_right",
      "size": 100,
      "opacity": 0.8
    }
  }
}
```

### Position Options
- `upper_right` - Top right corner
- `upper_left` - Top left corner  
- `lower_right` - Bottom right corner
- `lower_left` - Bottom left corner
- `center` - Center of screen

### FFmpeg Implementation
Use FFmpeg overlay filter:
```bash
ffmpeg -i input.mp4 -i logo.png -filter_complex \
"[1:v]scale=100:100[logo];[0:v][logo]overlay=x=W-w-10:y=10:opacity=0.8" \
-c:a copy output.mp4
```

## Implementation Steps

### 1. Configuration
- [ ] Update `akiratv/config.py` with logo configuration structure
- [ ] Add default logo settings to DEFAULT_CONFIG
- [ ] Add methods to get/set logo config

### 2. API
- [ ] Modify `akiratv/core_api.py` to handle logo config management
- [ ] Add `get_channel_logo_config()` method
- [ ] Add `update_channel_logo_config()` method

### 3. UI
- [ ] Add UI controls for logo settings in `akiratv/ui/main.py`
- [ ] Add logo settings to `akiratv/ui/tabs.py`
- [ ] Create logo settings dialog for channel configuration

### 4. Transcoder
- [ ] Modify `akiratv/transcoder.py` to apply logo overlay
- [ ] Handle per-channel logo settings
- [ ] Calculate FFmpeg filter parameters based on position

### 5. Testing
- [ ] Test with various configurations
- [ ] Verify functionality with both global and per-channel settings
- [ ] Test with different logo sizes and opacities

## Files to Modify
- `akiratv/config.py` - Configuration management
- `akiratv/core_api.py` - API methods
- `akiratv/ui/main.py` - Main UI controls
- `akiratv/ui/tabs.py` - Settings tab controls
- `akiratv/transcoder.py` - FFmpeg integration

## Estimated Timeline
- **Phase 1 (Core Functionality)**: 2-3 hours
- **Phase 2 (UI Implementation)**: 1-2 hours  
- **Phase 3 (Testing)**: 1-2 hours

## Notes
- Currently works with **transcoding mode only**
- Copy mode support would require client-side overlay technology
- HLS EXT-X-OVERLAY could be a future enhancement

## Future Enhancements
- Support for animated logos
- Logo animation transitions
- Timed logo display (on/off at specific times)
- Support for copy mode via HLS extensions
