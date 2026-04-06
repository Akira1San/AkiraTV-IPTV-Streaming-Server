# Linux Cross-Platform Paths Plan

## Overview
Make AkiraTV run on Linux by converting Windows-specific paths and implementing a Linux RAM disk solution equivalent to Windows ImDisk.

---

## 1. Linux RAM Disk Solution

### Problem
- On Windows: ImDisk Toolkit creates a virtual RAM disk at `R:/akiratv`
- On Linux: Need equivalent for storing HLS segments in RAM

### Linux Options

| Option | Description | Implementation |
|--------|-------------|----------------|
| **tmpfs** | Built-in Linux kernel feature, uses RAM/swap | `mount -t tmpfs -o size=512M tmpfs /home/akira/akiratv` |
| **ramfs** | Older alternative, similar to tmpfs | `mount -t ramfs -o size=512M ramfs /home/akira/akiratv` |
| **script-based** | Create mount point and mount automatically | Add to `/etc/fstab` or startup script |

### Recommended Approach
Use **tmpfs** with a startup script:
```bash
# Create mount point
sudo mkdir -p /home/akira/akiratv

# Mount as tmpfs (temporary, lost on reboot)
sudo mount -t tmpfs -o size=512M tmpfs /home/akira/akiratv

# Or add to /etc/fstab for persistent mount:
tmpfs /home/akira/akiratv tmpfs defaults,size=512M 0 0
```

---

## 2. Files to Modify

### config.json
| Setting | Windows Value | Linux Value |
|---------|---------------|-------------|
| `storage.ram_path` | `R:/akiratv` | `/home/akira/akiratv` |
| `storage.disk_path` | `./output` | `./output` (unchanged) |

### akiratv/collections.py
| Setting | Windows Value | Linux Value |
|---------|---------------|-------------|
| `FFPROBE_PATH` | `C:\ffmpeg\bin\ffprobe.exe` | `ffprobe` (system command) |

**Solution**: Make FFPROBE_PATH cross-platform by:
1. First trying system command `ffprobe` (works on both)
2. Falling back to hardcoded Windows path if not found

### akiratv/scheduler.py
- Comment on line 8 mentions Windows path but code uses `Path()` - already cross-platform ✅

### UI Files (optional updates)
- `akiratv/static/wizard.js` - Update placeholder examples
- `akiratv/static/app.js` - Update example paths

---

## 3. Implementation Tasks

### Task 1: Create Linux RAM Disk Setup Script
- [x] Create `setup_ramdisk.sh` script
- [x] Document tmpfs setup instructions
- [ ] Add to project documentation

### Task 2: Update config.json ✅ COMPLETED
- [x] Change `ram_path` to Linux path (`/home/akira/akiratv`)
- [x] Keep `disk_path` as `./output`

### Task 3: Fix collections.py for Cross-Platform ✅ COMPLETED
- [x] Make FFPROBE_PATH detect system automatically
- [x] Add fallback logic for both Windows and Linux

### Task 4: Update UI Hints (Optional)
- [ ] Update wizard.js with Linux path examples
- [ ] Update app.js with Linux path examples

---

## 4. Testing Checklist

- [ ] Verify tmpfs mounts correctly on Linux
- [ ] Test HLS segment generation to RAM disk
- [ ] Test collections.py with ffprobe on Linux
- [ ] Verify config loads correctly with new paths
- [ ] Test channel playback from Linux RAM path

---

## 5. Notes

- **Persistence**: RAM disk contents are lost on reboot - this is expected behavior
- **Size**: Choose appropriate size (e.g., 512MB-1GB) based on available RAM
- **Permissions**: Ensure user has write access to mount point
- **Backup**: Consider adding auto-backup of critical data before reboot