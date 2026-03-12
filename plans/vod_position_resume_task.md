# VOD Start Position & Resume Playback Task

## Overview

Implement the ability to start VOD video playback from a specific position (e.g., 30 minutes) and automatically resume from where the user left off when returning to watch a video later.

## Problem Statement

Currently, when playing a video from the VOD library:
1. Videos always start from the beginning
2. No way to start from a specific position like 30:00
3. If user stops watching mid-video and returns another day, they must re-watch from the beginning

## Solution

Allow users to:
1. **Specify start position** - Manually enter a start time (e.g., "30:00")
2. **Auto-resume** - Automatically continue from where they left off
3. **Fresh start option** - Option to start over if desired

## Implementation Tasks

### Phase 1: Backend - Data Model & API

- [ ] **1.1** Update `akiratv/models.py` - Add `start_position` field to `PlayNowRequest`
  ```python
  class PlayNowRequest(BaseModel):
      video_path: str = Field(..., description="Full path to video file")
      start_position: Optional[float] = Field(0, description="Start position in seconds")
  ```

- [ ] **1.2** Update `akiratv/routes/channels.py` - Pass `start_position` to `api.play_now()`

- [ ] **1.3** Update `akiratv/core_api.py` - Pass start_position to VOD worker via command queue

### Phase 2: Backend - VOD Worker

- [ ] **2.1** Modify `akiratv/workers/vod_worker.py` - Accept start_position in command tuple
  - Update `run()` method to extract position from queue command
  - Pass position to `_play_video()` and `_build_ffmpeg_args()`

- [ ] **2.2** Modify `_build_ffmpeg_args()` in `vod_worker.py` - Add `-ss` parameter to FFmpeg
  ```python
  if start_position > 0:
      args.extend(["-ss", str(start_position)])
  ```
  - Place `-ss` BEFORE `-i` for faster seeking (input seeking vs output seeking)

### Phase 3: Backend - Position Persistence

- [ ] **3.1** Create `akiratv/video_positions.py` - New module for managing video watch positions
  ```python
  # Functions needed:
  # - load_positions() -> Dict[str, float]
  # - save_position(video_path: str, position_seconds: float)
  # - get_position(video_path: str) -> float
  # - remove_position(video_path: str)
  ```

- [ ] **3.2** Create storage file: `user/video_positions.json`
  ```json
  {
    "C:/Videos/movie.mp4": 1800.5,
    "C:/Videos/show.mp4": 45.0
  }
  ```

- [ ] **3.3** Add API endpoints in `akiratv/routes/vod.py`:
  - `GET /api/vod/positions` - Get all saved positions
  - `GET /api/vod/position/{video_path}` - Get position for specific video
  - `POST /api/vod/position` - Save position for a video
  - `DELETE /api/vod/position/{video_path}` - Clear position for a video

### Phase 4: Frontend - UI Updates

- [ ] **4.1** Update `akiratv/static/vod.js` - Modify `playVideo()` function
  - Fetch saved position before playing
  - Show "Resume from X:XX?" dialog if position exists
  - Allow manual position input

- [ ] **4.2** Update `akiratv/static/vod.html` - Add position input UI
  - Add input field for manual start time (e.g., "MM:SS" or "HH:MM:SS")
  - Add "Resume" / "Start Over" buttons in modal

- [ ] **4.3** Add periodic position saving
  - Call save endpoint every 30 seconds during playback
  - Save final position when video stops

### Phase 5: Testing & Refinement

- [ ] **5.1** Test starting from specific time (e.g., 30:00)
- [ ] **5.2** Test resume functionality after closing browser
- [ ] **5.3** Test "Start Over" clears saved position
- [ ] **5.4** Edge cases: video shorter than position, corrupted position data

## Technical Notes

### FFmpeg Seeking
- Use input seeking (`-ss` before `-i`) for faster performance
- Alternative: output seeking (`-ss` after `-i`) for more accurate frame but slower

### Position Storage
- Save as seconds (float) for precision
- Auto-cleanup: remove positions for videos that no longer exist

### User Experience
- Default: If saved position exists, prompt user with "Resume from X:XX?" or "Start Over"
- Manual input: Accept formats like "30", "30:00", "1:30:00"

## Related Files

- `akiratv/models.py` - Request models
- `akiratv/routes/channels.py` - Channel play API
- `akiratv/routes/vod.py` - VOD endpoints (extend)
- `akiratv/core_api.py` - Core API
- `akiratv/workers/vod_worker.py` - VOD playback worker
- `akiratv/video_positions.py` - NEW: Position management
- `akiratv/static/vod.js` - VOD UI JavaScript
- `akiratv/static/vod.html` - VOD UI HTML

## References

- Existing seek implementation in `linear_worker.py:103-105`
- Existing seek implementation in `dynamic_worker.py:195`
- Fast Scheduler checkpoint system (`fast_scheduler.py:306`)
