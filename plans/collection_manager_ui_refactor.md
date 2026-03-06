# Collection Manager UI Refactoring Plan

## Overview
Refactor the button arrangement in `akiratv/collection_wizard.py` to group buttons by functionality, making the UI more intuitive and organized.

## Backup Files Created
- `akiratv/collection_wizard.py.backup_before_ui_refactor`
- `akiratv/metadata_fetcher.py.backup_before_ui_refactor`

---

## Current Button Layout Analysis

### Row 1 - Profile Quick Select
| Component | Function |
|-----------|----------|
| Quick Channel Name dropdown | Select from available profiles |
| Refresh button | Refresh profile list |

### Row 2 - Profile Management
| Component | Function |
|-----------|----------|
| Profile Name entry | Manual profile name input |
| Load Profile button | Load profile by name |
| Browse... button | Browse for collection file |
| Save button | Save current collections |
| Save As button | Save with new name |

### Row 3 - Folder & Actions (Mixed)
| Component | Function |
|-----------|----------|
| Video Folder entry | Folder path input |
| Browse button | Browse for folder |
| **Right side buttons:** | |
| Load Collections | Load collection file |
| Re-Scan Folder | Rescan video folder |
| [REFRESH] Update Collection | Update selected collection |
| [WEB] Fetch Metadata | Fetch online metadata |
| 📄 Export INI | Export to INI file |
| ☀️ Light Mode | Toggle theme |

### Row 4 - Selection Buttons (inside list frame)
| Component | Function |
|-----------|----------|
| Select All | Select all collections |
| Unselect All | Clear selection |
| Remove | Remove selected |

### Row 5 - Detail Frame
| Component | Function |
|-----------|----------|
| Save Fields | Save metadata fields |

---

## Proposed New Layout

### Row 1 - Profile Management
```
[Quick Channel Name dropdown] [Refresh] | [Profile Name entry] [Load Profile] [Browse...] [Save] [Save As]
```

### Row 2 - Browser Section (Folder & Collection Operations)
```
Video Folder: [entry] [Browse] | [Scan Folder] [Re-Scan] [Load Collection]
```

### Row 3 - Actions Section (Metadata & Export)
```
Actions: [Fetch Metadata] [Update Collection] [Export INI] | [☀️ Light Mode]
```

### Row 4 - Selection Buttons (unchanged)
```
[Select All] [Unselect All] [Remove]
```

### Row 5 - Detail Frame (unchanged)
```
[Save Fields]
```

---

## Button Grouping by Functionality

### Group 1: Profile Operations
- Quick Channel Name dropdown
- Refresh
- Profile Name entry
- Load Profile
- Browse...
- Save
- Save As

### Group 2: Browser/Folder Operations
- Video Folder entry
- Browse (folder)
- Scan Folder (renamed from "Re-Scan Folder")
- Load Collection

### Group 3: Actions
- Fetch Metadata
- Update Collection
- Export INI

### Group 4: UI/Selection
- Light Mode toggle
- Select All / Unselect All / Remove

---

## Implementation Changes

### Code Changes Required in `create_widgets()` method:

1. **Restructure `top_frame`** to separate folder operations from action buttons
2. **Create new `action_frame`** for metadata and export buttons
3. **Add visual separators** between button groups
4. **Rename buttons** for clarity:
   - "Re-Scan Folder" → "Scan Folder"
   - "Load Collections" → "Load Collection"

### Visual Improvements:
- Add `ttk.Separator` between button groups
- Consider using `ttk.LabelFrame` for each group
- Maintain consistent padding and spacing

---

## Mockup

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Quick Channel: [dropdown    ] [Refresh]  Profile: [entry    ]              │
│               [Load Profile] [Browse...] [Save] [Save As]                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Video Folder: [path entry                                    ] [Browse]    │
│               [Scan Folder] [Re-Scan] [Load Collection]                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Actions: [Fetch Metadata] [Update Collection] [Export INI]    [☀️ Light]   │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌─────────────────────────────┐ ┌──────────────┐              │
│ │  Cover   │ │ Collections                 │ │    Tags      │              │
│ │  Preview │ │ [Select All][Unselect][Rem] │ │  [x] Action  │              │
│ │          │ │ ┌─────────────────────────┐ │ │  [ ] Comedy  │              │
│ │          │ │ │ Collection 1            │ │ │  [x] Drama   │              │
│ │          │ │ │ Collection 2            │ │ │  ...        │              │
│ │          │ │ └─────────────────────────┘ │ │              │              │
│ └──────────┘ └─────────────────────────────┘ └──────────────┘              │
├─────────────────────────────────────────────────────────────────────────────┤
│ Collection Details:                                                         │
│ ID:          [readonly entry                                           ]    │
│ Name:        [entry                                                    ]    │
│ Cover:       [entry                                                    ]    │
│ Description: [entry                                                    ]    │
│ ...                                                                         │
│ [Save Fields]                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Files to Modify
- `akiratv/collection_wizard.py` - Main UI file

## Files to Keep Unchanged
- `akiratv/metadata_fetcher.py` - No UI changes needed
- `akiratv/collections.py` - No UI changes needed

---

## Testing Checklist
- [ ] All buttons still function correctly
- [ ] Keyboard navigation works
- [ ] Theme toggle still works
- [ ] Tooltips display correctly
- [ ] Window resizing behaves properly
- [ ] No visual overlaps or alignment issues
