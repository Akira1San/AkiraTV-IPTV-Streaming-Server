# Collection-Based Scheduling Implementation Plan

## Overview

Change the schedule.json format to use collection_id references instead of full video file paths. **Collections format remains unchanged** - only schedule format changes.

**IMPORTANT**: Old schedules with full file paths must be regenerated after implementation.

## Current System

### Collections Structure (UNCHANGED)
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

**Collections remain unchanged** - they continue to store absolute paths in `videos[].path`.

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

### Collections Format (UNCHANGED)
Collections remain as they are - no changes needed.

### New Schedule Format

Store `collection_id` only (no video paths in schedule):

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

**Path Resolution at runtime:**
1. Look up collection by `collection_id`
2. Get absolute path from `videos[0].path` in collection
3. NO fallback - if collection not found, log error and skip entry

**IMPORTANT**: No backward compatibility in schedule format. Old schedules with full paths must be regenerated using the Simple Scheduler.

---

## Implementation Steps

### Phase 1: Update Schedule Generation

[x] 1. **Modify `akiratv/simple_scheduler.py`**
   - [x] Update `_generate_random_schedule()` (line ~1285)
   - [x] Update `_generate_sequential_schedule()` (line ~1524)
   - [x] Store `collection_id` only in new schedule entries (NO file path)

```python
# New schedule entry format:
entry = {
    "time": time_str,
    "collection_id": collection.get("id"),  # ONLY the ID reference
    "channel": target_channel,
    "source": "random"
}
# NO file or fallback_file field - paths stay in collections
```

[ ] 2. **Modify `akiratv/fast_scheduler.py`**
   - [ ] Update schedule entry creation to use collection_id only

### Phase 2: Update Schedule Loading

[x] 3. **Modify `akiratv/scheduler.py`**
   - [x] Update `get_full_todays_schedule()` (line ~16)
   - [x] Update `get_current_schedule_for_channel()` (line ~156)
   - [x] Add function `resolve_collection_to_path(collection_id)`
   - [x] Runtime resolution: look up collection by ID, get path from collection
   - [x] If collection not found: log error, skip entry (no backward compat)

[ ] 4. **Update `fast_scheduler.py`**
   - [ ] Modify `get_current_entry()` to resolve collection references
   - [ ] Apply same resolution logic

### Phase 3: API Updates

[x] 5. **Modify `akiratv/api_server.py`**
   - [x] Update schedule loading endpoints to resolve paths
   - [x] Ensure API responses include full video paths for playback

---

## Key Functions to Create/Modify

### New Function: resolve_collection_to_path()

```python
def resolve_collection_to_path(collection_id: str, collections: list) -> str:
    """
    Resolve collection_id to full video path.
    
    Since each collection = one video, we use the first video in the collection.
    NO fallback to file paths - if collection not found, return None.
    
    Args:
        collection_id: The collection identifier (e.g., "into_the_sun")
        collections: List of collection dictionaries
    
    Returns:
        Full path to video file, or None if not found
    """
    for collection in collections:
        if collection.get("id") == collection_id:
            videos = collection.get("videos", [])
            if videos:
                # Use first (and usually only) video in collection
                return videos[0].get("path", "")
    return None  # Collection not found - will be logged/skipped
```

### Old Schedule Entry Format (MUST BE REGENERATED)

Old schedules have full paths in `file` field - these must be regenerated:

```json
{
  "time": "01:34:54",
  "file": "C:/Videos/tatkotv3/Into The Sun.mp4",
  "channel": "TatkoTV",
  "source": "random"
}
```

**Action required**: Run Simple Scheduler to regenerate old schedules with `collection_id` format.

---

## Testing Plan

1. **Backward Compatibility Test**
   - Note: Old schedules with full paths will NOT work - must be regenerated
   - Generate new schedule with `collection_id` only
   - Verify videos play correctly via collection lookup

---

## Files Summary

| File | Changes |
|------|---------|
| `akiratv/simple_scheduler.py` | Use `collection_id` only in entries |
| `akiratv/scheduler.py` | Add resolve function |
| `akiratv/fast_scheduler.py` | Use collection_id references |
| `akiratv/api_server.py` | Resolve paths in API |

## Migration Strategy

**Old schedules MUST be regenerated** - Schedules with full paths in `file` field will no longer work. Use Simple Scheduler to regenerate all schedules after implementing changes.

---

## Benefits

1. **No video paths in schedules** - Only `collection_id` stored, completely portable
2. **Clean separation** - Collections hold paths, schedules only hold references
3. **Smaller schedule files** - No redundant path storage
4. **Future-proof** - Can update collection paths without breaking schedules

---

## Drawbacks / Considerations

### 1. Old Schedules Break
- Existing schedules with `file` paths will stop working
- Must regenerate ALL schedules via Simple Scheduler after deployment
- If you have manually edited schedules, those changes are lost

### 2. Collection Dependency
- If a collection is deleted/renamed, scheduled entries fail silently
- Need to regenerate schedule after deleting collections
- More complex error handling needed in scheduler

### 3. Runtime Lookup Overhead

**What happens now vs what will happen:**

**CURRENT (no overhead):**
```json
{
  "time": "01:34:54",
  "file": "C:/Videos/tatkotv3/Into The Sun.mp4",
  "channel": "TatkoTV"
}
```
Scheduler reads `file` directly - O(1) access, no processing needed.

**NEW (with lookup):**
```json
{
  "time": "01:34:54",
  "collection_id": "into_the_sun",
  "channel": "TatkoTV"
}
```
Scheduler must:
1. Load collections JSON from disk (or use cached)
2. Loop through collections to find matching ID
3. Extract path from `videos[0].path`

**Performance impact:**
- Collection lookup: O(n) where n = number of collections
- For 1000 collections, ~1000 iterations per schedule entry
- Disk I/O if collections not cached

**When it happens:**
- When schedule is loaded at startup
- When getting next scheduled item
- NOT during video playback (only at schedule resolution time)

**Reality check:**
- Even with 1000 collections, loop takes <1ms
- Collections can be cached in memory after first load
- Schedule is loaded once, not per-video
- This overhead is negligible for typical use (<100 collections)

### 4. No Manual Schedule Editing
- Can't manually add/edit schedule entries without a collection ID
- Reduces flexibility for one-off scheduling

### Mitigation Strategies

| Drawback | Mitigation |
|----------|------------|
| Old schedules break | One-time regeneration after deployment |
| Collection dependency | Add validation on schedule load, warn user |
| Runtime lookup | Cache collections in memory |
| No manual editing | Can add a "direct file" mode later if needed |

---

## Notes

- Each "collection" is one movie (single video entry)
- The `name` field in collection = movie title (used by XMLTV for programme title)
- Schedule uses `collection_id` to reference collections
- Video paths stay in collections (absolute paths)
- NO fallback paths in schedule - must regenerate old schedules
- Consider adding a `version` field to schedule.json for format versioning
