# Collection-Based Scheduling Implementation Plan

## Overview

Change the schedule.json format to store collection references + relative video paths instead of full video file paths. This makes schedules more portable and resilient to file location changes.

## Current System

### Collections Structure (Current)
Location: `user/collections/collections_{channel}.json`

**IMPORTANT**: Each "collection" = ONE movie (single video entry). The `name` field is the movie title.

```json
{
  "collections": [
    {
      "id": "a_working_man",
      "name": "Работещият мъж",  // Movie title
      "cover": "user/covers/a_working_man.jpg",
      "description": "...",
      "genre": ["Екшъ н", "Трилър"],
      "year": 2025,
      "videos": [
        { "path": "C:/Videos/tatkotv3/A Working Man.mp4", "duration": 6974.91 }
      ]
    }
  ]
}
```

### Current Schedule Format
Location: `user/schedules/schedule_{channel}.json`

```json
{
  "calendar": {
    "2026-02-27_friday": {
      "date": "2026-02-27",
      "day": "Friday",
      "description": "Auto-generated calendar schedule",
      "entries": [
        {
          "time": "01:34:54",
          "file": "C:/Videos/tatkotv3/steven seagal/Into The Sun.mp4",
          "channel": "TatkoTV",
          "source": "random"
        }
      ]
    }
  }
}
```

### Files Involved

1. **akiratv/simple_scheduler.py** (lines 1287, 1516) - Schedule generation
   - `_generate_random_schedule()` - picks random videos from collections
   - `_generate_sequential_schedule()` - plays videos in order
   - Creates entries with `"source": "random"`

2. **akiratv/scheduler.py** - Schedule loading for playback
   - `get_full_todays_schedule()` - loads today's entries
   - `get_current_schedule_for_channel()` - loads channel schedule

3. **akiratv/fast_scheduler.py** - Fast schedule generation/playback

4. **akiratv/api_server.py** - API endpoints for schedule management

---

## Proposed Solution

### Updated Collection Format

Add `folder_name` field to store base path, and make video paths relative:

```json
{
  "collections": [
    {
      "id": "into_the_sun",
      "name": "Into The Sun",  // Movie title (unchanged)
      "folder_name": "C:/Videos/tatkotv3/steven seagal/",  // NEW: Base folder
      "videos": [
        { "path": "Into The Sun.mp4", "duration": 5400 }  // RELATIVE path
      ]
    }
  ]
}
```

### New Schedule Format

Store `collection_id` only (since each collection = one video):

```json
{
  "calendar": {
    "2026-02-27_friday": {
      "entries": [
        {
          "time": "01:34:54",
          "collection_id": "into_the_sun",
          "channel": "TatkoTV",
          "source": "random"
        }
      ]
    }
  }
}
```

**Resolution at runtime:**
1. Look up collection by `collection_id`
2. Get `folder_name` from collection
3. Use first video in collection: `folder_name` + `videos[0].path` = full path

**No backward compatibility** - old schedules with full paths must be re-generated.

---

## Implementation Steps

### Phase 1: Create Migration Tool for Collections

**IMPORTANT**: Existing collections have absolute paths. Run migration before making other changes.

1. **Create migration script** - File: `akiratv/migrate_collections.py`
   - Load all collection JSON files from `user/collections/`
   - For each collection:
     - Extract folder from existing absolute path (e.g., "C:/Videos/tatkotv3/steven seagal/")
     - Add `folder_name` field
     - Convert video path to relative (just filename)
   - Save updated collections

```python
# Migration logic:
import os
from pathlib import Path

def migrate_collection(collection):
    videos = collection.get("videos", [])
    if videos and videos[0].get("path"):
        old_path = videos[0]["path"]
        # Extract folder and filename
        path_obj = Path(old_path)
        folder = str(path_obj.parent) + "/"  # "C:/Videos/tatkotv3/steven seagal/"
        filename = path_obj.name  # "Into The Sun.mp4"
        
        collection["folder_name"] = folder
        videos[0]["path"] = filename
    return collection
```

### Phase 2: Update Collection Creation

2. **Modify `akiratv/collection_wizard.py`** - When creating new collections, automatically set `folder_name` and use relative paths

3. **Modify `akiratv/collections.py`** - Update scan_folder to store folder_name and relative paths

### Phase 2: Update Schedule Generation

3. **Modify `simple_scheduler.py`**
   - Update `_generate_random_schedule()` (line ~1409)
   - Update `_generate_sequential_schedule()` (line ~1524)
   - Store `collection_id` only instead of full `file` path
   - Keep `fallback_file` for backward compatibility

4. **Modify `fast_scheduler.py`**
   - Update schedule entry creation to use collection references
   - Store collection_id only instead of full path

### Phase 3: Update Schedule Loading

5. **Modify `scheduler.py`**
   - Update `get_full_todays_schedule()` (line ~16)
   - Update `get_current_schedule_for_channel()` (line ~156)
   - Add function `resolve_collection_to_path(collection_id, video_filename)`
   - Fallback to `file` or `fallback_file` field if collection not found

6. **Update `fast_scheduler.py`**
   - Modify `get_current_entry()` to resolve collection references

### Phase 4: API Updates

7. **Modify `api_server.py`**
   - Update schedule loading endpoints to resolve paths
   - Ensure API responses include full video paths for playback

---

## Key Functions to Create/Modify

### New Function: resolve_collection_to_path()

```python
def resolve_collection_to_path(collection_id: str, collections: list) -> str:
    """
    Resolve collection_id to full video path.
    
    Since each collection = one video, we use the first video in the collection.
    
    Args:
        collection_id: The collection identifier (e.g., "into_the_sun")
        collections: List of collection dictionaries
    
    Returns:
        Full path to video file
    """
    for collection in collections:
        if collection.get("id") == collection_id:
            folder_name = collection.get("folder_name", "")
            videos = collection.get("videos", [])
            if videos:
                # Use first (and usually only) video in collection
                return folder_name + videos[0].get("path", "")
    return None  # Or raise exception
```

### Modify: _generate_random_schedule() in simple_scheduler.py

```python
# OLD (line ~1285):
entry = {
    "time": time_str,
    "file": video["path"],
    "channel": target_channel,
    "source": "random"
}

# NEW:
entry = {
    "time": time_str,
    "collection_id": collection.get("id"),
    "channel": target_channel,
    "source": "random"
}
```

---

## Testing Plan

1. **Migration Test**
   - Run migration tool on existing collections
   - Verify folder_name is added and paths are relative

2. **Integration Tests**
   - Generate new schedule with collection_id
   - Play schedule and verify correct videos play

3. **Verify no full paths in schedule**

---

## Files Summary

| File | Changes |
|------|---------|
| `akiratv/migrate_collections.py` | NEW - One-time migration script for existing collections |
| `akiratv/collection_wizard.py` | Add `folder_name` field when creating new collections |
| `akiratv/collections.py` | Update scan_folder to store folder_name and relative paths |
| `akiratv/simple_scheduler.py` | Use `collection_id` only in entries |
| `akiratv/scheduler.py` | Add resolve function |
| `akiratv/fast_scheduler.py` | Use collection references |
| `akiratv/api_server.py` | Resolve paths in API |

---

## Migration Strategy

**No backward compatibility** - Old schedules with full paths must be re-generated using the Simple Scheduler.

---

## Benefits

1. **No full paths in schedules** - Only `collection_id` stored, no absolute paths
2. **Portability**: Schedules are portable across systems
3. **Flexibility**: Move video folders without breaking schedules (update folder_name in collection)
4. **Efficiency**: Smaller schedule files (no redundant paths)

---

## Notes

- Each "collection" is one movie (single video entry)
- The `name` field in collection = movie title (used by XMLTV for programme title)
- The `folder_name` field is new - stores base path for resolving relative paths
- Schedule only needs `collection_id` - uses first video in collection
- Consider adding a `version` field to schedule.json for format versioning
