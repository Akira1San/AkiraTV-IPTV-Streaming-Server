# AkiraTV Fast Scheduler

## Overview

The Fast Scheduler is a revolutionary dynamic scheduling system for AkiraTV that creates TV schedules on-the-fly from your video collections without requiring JSON files. It provides intelligent crash recovery, automatic bumpers/trailers, and seamless integration with existing channel workers.

## Key Features

### 🚀 Dynamic Scheduling
- **No JSON Files Required**: Creates schedules directly from collection libraries
- **On-the-Fly Generation**: Builds schedules dynamically based on available content
- **Flexible Duration**: Generate schedules from 1 hour to 7 days (168 hours)
- **Smart Shuffling**: Randomizes content for variety while respecting settings

### 💾 Intelligent Storage
- **Dictionary-Based**: Stores schedule entries as `{time, video_name, path, duration}` objects
- **In-Memory Performance**: Fast access to schedule data
- **Checkpoint System**: Automatic persistence for crash recovery
- **State Management**: Tracks current position and playback state

### 🔄 Crash Recovery
- **Resume Position Calculation**: Automatically determines where to resume after crashes
- **Time-Based Recovery**: Uses current time to calculate exact resume position
- **Seamless Restart**: No manual intervention required after server restarts
- **State Preservation**: Maintains schedule integrity across interruptions

### 🎬 Advanced Features
- **Automatic Bumpers**: Insert promotional content every N videos
- **Dynamic Trailers**: Show trailers before content with configurable probability
- **Metadata Support**: Rich video information and descriptions
- **Multi-Collection**: Combine content from multiple collection libraries

## Architecture

### System Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Interface │    │  Fast Scheduler  │    │ Linear Worker   │
│                 │    │                  │    │                 │
│ • Channel Setup │───▶│ • Schedule Gen   │───▶│ • Video Playback│
│ • Collection    │    │ • Entry Storage  │    │ • Stream Output │
│   Selection     │    │ • Resume Logic   │    │ • HLS Generation│
│ • Settings      │    │ • Checkpoints    │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌────────▼────────┐             │
         │              │   Scheduler     │             │
         │              │   Integration   │             │
         └──────────────▶│                 │◀────────────┘
                        │ • Fast Check    │
                        │ • JSON Fallback │
                        │ • Entry Format  │
                        └─────────────────┘
```

### Data Flow

1. **Schedule Creation**:
   - User selects channel and collections via web interface
   - Fast Scheduler loads videos from collection files
   - System generates schedule entries with timestamps
   - Checkpoint saved automatically

2. **Schedule Consumption**:
   - Linear worker requests schedule from scheduler.py
   - scheduler.py checks Fast Scheduler first, then JSON files
   - Schedule entries converted to worker-compatible format
   - Worker begins playback with current/future entries

3. **Crash Recovery**:
   - Worker restarts and requests current schedule
   - Fast Scheduler calculates resume position based on current time
   - Worker resumes playback at correct position in current video
   - Schedule continues seamlessly

## Usage Guide

### Creating a Fast Schedule

1. **Access Web Interface**:
   - Open AkiraTV web UI (`http://localhost:8001`)
   - Navigate to "Collection & Scheduler Wizard" section
   - Click "⚡ Fast Schedule" button

2. **Configure Schedule**:
   - **Select Channel**: Choose target channel for the schedule
   - **Select Collections**: Pick which video collections to use
   - **Set Start Time**: Choose when the schedule begins (HH:MM format)
   - **Schedule Duration**: Set how many hours of content to generate
   - **Bumper Frequency**: Configure bumper insertion (every N videos)
   - **Trailer Probability**: Set chance of showing trailers (0-100%)

3. **Generate Schedule**:
   - Click "Generate Schedule" button
   - System loads collections and creates schedule entries
   - Checkpoint automatically saved for persistence
   - Channel ready for streaming

### Starting a Fast Scheduled Channel

1. **Channel Setup**:
   - Ensure channel type is set to "Linear"
   - Fast Schedule must be created first
   - No JSON schedule file required

2. **Start Streaming**:
   - Use normal channel start procedures
   - Worker automatically detects Fast Schedule
   - Playback begins at current schedule position
   - Resume position calculated if restarting

### Managing Fast Schedules

#### Via Web Interface
- **View Status**: Check current playing entry and upcoming content
- **Regenerate**: Create new schedule with different settings
- **Save Checkpoint**: Manual checkpoint creation
- **Load Checkpoint**: Restore previous schedule state

#### Via API Endpoints
```http
# Get schedule information
GET /api/fast-schedule/{channel}/info

# Get current playing entry
GET /api/fast-schedule/{channel}/current

# Get upcoming entries
GET /api/fast-schedule/{channel}/upcoming?count=5

# Generate new schedule
POST /api/fast-schedule/{channel}/generate
{
  "collections": ["collection1", "collection2"],
  "start_time": "09:00",
  "schedule_hours": 24,
  "bumper_frequency": 3,
  "trailer_probability": 0.3
}

# Save/Load checkpoints
POST /api/fast-schedule/{channel}/save-checkpoint
POST /api/fast-schedule/{channel}/load-checkpoint
```

## Configuration Options

### Schedule Settings

| Setting | Description | Default | Range |
|---------|-------------|---------|-------|
| **Start Time** | When schedule begins | 00:00 | 00:00-23:59 |
| **Schedule Hours** | Duration of generated content | 24 | 1-168 |
| **Bumper Frequency** | Insert bumper every N videos | 3 | 1-10 |
| **Trailer Probability** | Chance of showing trailers | 30% | 0-100% |

### Collection Format Support

The Fast Scheduler supports both collection formats:

#### New Format (AkiraTV Collections)
```json
{
  "collections": [
    {
      "id": "movie_id",
      "name": "Movie Name",
      "description": "Movie description",
      "genre": ["Action", "Drama"],
      "rating": "PG-13",
      "year": 2023,
      "videos": [
        {
          "path": "/path/to/movie.mp4",
          "duration": 7200.5
        }
      ]
    }
  ]
}
```

#### Legacy Format
```json
{
  "movie_name": {
    "path": "/path/to/movie.mp4",
    "duration": 7200.5,
    "metadata": {...}
  }
}
```

## Technical Details

### Schedule Entry Structure

Each schedule entry contains:

```python
@dataclass
class ScheduleEntry:
    time: str           # HH:MM format
    video_name: str     # Display name
    video_path: str     # Full file path
    duration: float     # Duration in seconds
    entry_type: str     # "content", "bumper", "trailer"
    metadata: dict      # Additional information
```

### Checkpoint Format

Checkpoints store complete scheduler state:

```json
{
  "state": {
    "channel_name": "channel_name",
    "current_entry": {...},
    "current_position": 0.0,
    "schedule_entries": [...],
    "last_update": "2026-02-01T12:00:00",
    "is_running": false
  },
  "available_videos": [...],
  "bumpers": [...],
  "trailers": [...],
  "settings": {...},
  "saved_at": "2026-02-01T12:00:00"
}
```

### Resume Position Calculation

The system calculates resume positions using:

```python
def get_resume_position(entry: ScheduleEntry) -> float:
    current_time = datetime.now()
    entry_start = parse_time(entry.time)
    elapsed_seconds = (current_time - entry_start).total_seconds()
    return max(0, min(elapsed_seconds, entry.duration))
```

## Integration with Existing Systems

### Scheduler Integration

The Fast Scheduler integrates with `scheduler.py`:

```python
def get_current_schedule_for_channel(channel: str):
    # 1. Check Fast Scheduler first
    fast_scheduler = FastScheduler(channel)
    if fast_scheduler.has_checkpoint():
        return fast_scheduler.get_schedule_entries()
    
    # 2. Fallback to JSON files
    return load_json_schedule(channel)
```

### Worker Compatibility

Fast Scheduler entries are converted to worker-compatible format:

```python
# Fast Scheduler Entry
{
    "time": "14:30",
    "video_name": "Movie Title",
    "video_path": "/path/to/movie.mp4",
    "duration": 7200.5,
    "entry_type": "content",
    "metadata": {...}
}

# Worker Format
{
    "time": "14:30",
    "video": "/path/to/movie.mp4",
    "display_name": "Movie Title",
    "duration": 7200.5,
    "type": "content",
    "metadata": {...}
}
```

## Troubleshooting

### Common Issues

#### No Videos Loaded
- **Cause**: Collection files not found or invalid format
- **Solution**: Check collection file paths and JSON format
- **Debug**: Check logs for collection loading errors

#### Schedule Not Found by Worker
- **Cause**: Checkpoint not saved or Fast Scheduler not integrated
- **Solution**: Regenerate schedule and ensure checkpoint is saved
- **Debug**: Check `get_current_schedule_for_channel()` function

#### Resume Position Incorrect
- **Cause**: System time issues or entry time format problems
- **Solution**: Verify system time and entry time format (HH:MM)
- **Debug**: Check resume position calculation logic

#### Bumpers/Trailers Not Playing
- **Cause**: No bumper/trailer files configured
- **Solution**: Add bumper and trailer video files to Fast Scheduler
- **Note**: Feature requires additional setup for bumper/trailer content

### Debug Information

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger('akiratv.fast_scheduler').setLevel(logging.DEBUG)
```

Check checkpoint files:
```bash
# Checkpoint location
user/fast_schedules/fast_schedule_{channel_name}.json
```

## Performance Considerations

### Memory Usage
- Schedule entries stored in memory for fast access
- Checkpoint files provide persistence without memory overhead
- Large collections (1000+ videos) may require more RAM

### Generation Speed
- Schedule generation is near-instantaneous for most collections
- Time complexity: O(n) where n is number of videos
- Checkpoint save/load operations are fast (< 1 second)

### Scalability
- Supports multiple channels with independent schedules
- Each channel maintains separate Fast Scheduler instance
- No cross-channel interference or resource conflicts

## Future Enhancements

### Planned Features
- **Smart Bumper Generation**: Auto-create bumpers from video metadata
- **Advanced Scheduling**: Time-based content rules (morning shows, evening movies)
- **Content Filtering**: Genre-based scheduling and content restrictions
- **Analytics Integration**: Track viewing patterns and optimize schedules
- **Multi-Day Patterns**: Weekly recurring patterns with daily variations

### API Improvements
- **Bulk Operations**: Manage multiple channels simultaneously
- **Schedule Templates**: Save and reuse schedule configurations
- **Real-time Updates**: Live schedule modifications without restart
- **Export/Import**: Share schedules between AkiraTV instances

## Conclusion

The Fast Scheduler revolutionizes AkiraTV channel management by eliminating the complexity of JSON schedule files while providing advanced features like crash recovery and dynamic content insertion. Its seamless integration with existing workers ensures compatibility while opening new possibilities for intelligent, automated TV scheduling.

For additional support or feature requests, consult the AkiraTV documentation or community forums.