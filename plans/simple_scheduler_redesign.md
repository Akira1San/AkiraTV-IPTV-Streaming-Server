# Simple Scheduler UI Redesign Plan

## Overview
Redesign the simple scheduler UI with a new 4-column layout: `[Info] - [Collection] - [Added] - [Preview]`

## New Workflow
1. User loads a collection profile
2. User selects a collection from the list
3. User selects videos from the selected collection
4. User clicks "Add" to move selected videos to the Added list
5. User can repeat steps 2-4 to add videos from multiple collections
6. User clicks "Preview" to generate schedule from the Added list
7. User can save the generated schedule

## UI Layout

```
+----------------+----------------+----------------+----------------+
|     Info       |   Collection   |     Added      |    Preview     |
|                |                |                |                |
|  [Cover Image] | [Profile Sel]  | [Added Videos] | [Day Selector] |
|                |                |                |                |
|  Name:         | [Collections]  | [Remove]       | [Schedule]     |
|  Description   |                | [Remove All]   |                |
|  Genre         | [Videos]       |                | [Info]         |
|  Rating        |                | Count: X       |                |
|  Year          | [Add]          |                |                |
|                | [Add All]      |                |                |
|  Path:         |                |                |                |
|  Duration:     |                |                |                |
+----------------+----------------+----------------+----------------+
```

## Data Structures

### New Instance Variables
```python
self.added_videos = []  # List of video objects user has added
self.video_to_collection_map = {}  # Map video path -> collection object
self.selected_video = None  # Currently selected video for info panel
self.selected_collection = None  # Currently selected collection
```

### Video Object Structure
```python
{
    "path": "C:/Videos/horror/28 Days Later 2002.mp4",
    "duration": 6515.217042,
    "name": "28 Days Later 2002",
    "collection": {
        "id": "28_days_later_2002",
        "name": "28 Days Later 2002",
        "cover": "28_days_later_2002.jpg",
        "description": "",
        "genre": [],
        "rating": "NR",
        "year": 2026
    }
}
```

## Implementation Steps

### 1. Info Panel (Leftmost Column)
- **Cover Image Display**
  - Load image from `user/covers/{collection_id}.jpg` or `user/covers/{collection_id}.png`
  - Use `tkinter.PhotoImage` or `PIL.ImageTk.PhotoImage`
  - Display placeholder if no cover available

- **Metadata Display**
  - Name: Collection name
  - Description: Collection description
  - Genre: List of genres (comma-separated)
  - Rating: Collection rating
  - Year: Collection year
  - Path: Video file path
  - Duration: Formatted as HH:MM:SS

- **Update Logic**
  - Update when user selects a video from the collection list
  - Clear when no video is selected

### 2. Collection Panel (Second Column)
- **Profile Selection** (keep existing)
  - Quick Select dropdown
  - Manual profile entry
  - Load Profile button
  - Refresh button
  - Collection Wizard button

- **Collection List**
  - Show all collections from loaded profile
  - Single selection
  - When selected, populate video list

- **Video List**
  - Show videos from selected collection
  - Multi-select enabled
  - Display video filename

- **Add Buttons**
  - "Add" - Add selected videos to Added list
  - "Add All" - Add all videos from selected collection

### 3. Added Panel (Third Column)
- **Added Videos List**
  - Show all videos user has added
  - Multi-select enabled
  - Display format: "Collection Name - Video Filename"

- **Remove Buttons**
  - "Remove" - Remove selected videos from Added list
  - "Remove All" - Clear entire Added list

- **Count Display**
  - Show total number of videos in Added list

### 4. Preview Panel (Rightmost Column)
- **Day Selector** (keep existing)
  - Dropdown to select day to view

- **Preview List** (keep existing)
  - Show schedule entries for selected day
  - Format: "HH:MM:SS - Video Name"

- **Preview Info** (keep existing)
  - Show schedule generation info

## New Methods to Implement

### Info Panel Methods
```python
def update_info_panel(self, video_data):
    """Update info panel with selected video data"""
    # Update cover image
    # Update metadata labels
    pass

def load_cover_image(self, collection_id):
    """Load cover image from user/covers directory"""
    # Return PhotoImage or None
    pass

def format_duration(self, seconds):
    """Format duration in seconds to HH:MM:SS"""
    pass
```

### Collection Panel Methods
```python
def on_collection_select(self, event):
    """Handle collection selection - populate video list"""
    pass

def on_video_select(self, event):
    """Handle video selection - update info panel"""
    pass

def add_selected_videos(self):
    """Add selected videos to added list"""
    pass

def add_all_videos(self):
    """Add all videos from selected collection"""
    pass
```

### Added Panel Methods
```python
def remove_selected_videos(self):
    """Remove selected videos from added list"""
    pass

def remove_all_videos(self):
    """Clear entire added list"""
    pass

def update_added_list_display(self):
    """Update added videos listbox"""
    pass
```

### Modified Methods
```python
def preview_schedule(self, mode="random"):
    """Generate schedule from added_videos instead of selected collections"""
    # Use self.added_videos instead of building from selected collections
    pass

def create_widgets(self):
    """Redesign UI with 4-column layout"""
    # Create 4 frames instead of 2
    pass
```

## Key Changes Summary

### UI Changes
1. Replace 2-column layout with 4-column layout
2. Add Info panel for video metadata display
3. Add Added panel for user-selected videos
4. Move Preview panel to rightmost column

### Logic Changes
1. Schedule generation now uses `added_videos` list
2. Users can add videos from multiple collections
3. Video selection is now at video level, not collection level

### Data Flow
```
Load Profile -> Select Collection -> Select Videos -> Add to Added List -> Preview Schedule -> Save
```

## Testing Checklist
- [ ] Load profile and see collections
- [ ] Select collection and see videos
- [ ] Select video and see info panel update
- [ ] Add single video to added list
- [ ] Add multiple videos to added list
- [ ] Add all videos from collection
- [ ] Remove videos from added list
- [ ] Clear all videos from added list
- [ ] Generate random schedule from added videos
- [ ] Generate sequential schedule from added videos
- [ ] Preview different days
- [ ] Save schedule
- [ ] Test with episodic content detection enabled
- [ ] Test with multiple collections loaded
