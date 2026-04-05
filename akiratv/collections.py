# akiratv/collections.py
import json
import re
from pathlib import Path
from datetime import datetime
import subprocess

# akiratv/collections.py
import subprocess
import shutil
import sys
from pathlib import Path

def get_ffprobe_path() -> str:
    """
    Get the ffprobe executable path in a cross-platform way.
    - First tries system 'ffprobe' command (works on Linux and Windows if in PATH)
    - Falls back to Windows default path if not found
    """
    # Try system ffprobe first (works on both Linux and Windows)
    system_ffprobe = shutil.which("ffprobe")
    if system_ffprobe:
        return system_ffprobe
    
    # Fallback to Windows default path
    windows_path = r"C:\ffmpeg\bin\ffprobe.exe"
    if Path(windows_path).exists():
        return windows_path
    
    # Last resort: return system command anyway (will fail with clear error)
    print(f"[WARNING] ffprobe not found. Please install ffmpeg or set path manually.")
    return "ffprobe"

# 🔑 Cross-platform FFprobe path
FFPROBE_PATH = get_ffprobe_path()

def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    try:
        # Normalize path
        safe_path = str(video_path).replace("\\", "/")
        
        # 🔑 CRITICAL: Use -of csv=p=0 to get ONLY the number
        result = subprocess.run(
            [
                FFPROBE_PATH,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",  # ← This gives clean numeric output
                safe_path
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
        # Clean output (remove newlines/spaces)
        duration_str = result.stdout.strip()
        if duration_str:
            return float(duration_str)
        else:
            print(f"⚠️  Empty duration output for: {safe_path}")
            return None
    except Exception as e:
        print(f"[ERROR] FFprobe failed for {video_path}: {e}")
        return None

# Predefined tags (user can add custom ones)
DEFAULT_TAGS = [
    "horror", "action", "comedy", "drama", "sci-fi", "fantasy",
    "thriller", "romance", "anime", "animation", "documentary",
    "western", "war", "musical", "crime", "adventure", "80s", "90s"
]

def scan_folder(folder_path: str, existing_collections=None):
    """Scan folder and merge with existing collections."""
    folder = Path(folder_path)
    if not folder.exists():
        return []

    # Find all video files
    video_files = []
    for ext in [".mp4", ".mkv", ".avi", ".mov", ".webm"]:
        video_files.extend(folder.rglob(f"*{ext}"))

    # Group into collections
    new_collections = {}
    for file in video_files:
        # Extract base name (remove chunks, years, quality tags)
        stem = file.stem
        # Remove chunk suffixes
        match = re.match(r"^(.+?)(?:_(?:part|chunk))?_?\d+$", stem, re.IGNORECASE)
        base = match.group(1) if match else stem
        # Clean name: remove year, resolution, etc.
        clean = re.sub(r"[.\s]\d{4}[.\s]", " ", base)  # Remove .1986.
        clean = re.sub(r"[.\s](1080p|720p|2160p|4K|BluRay|WEBRip).*", "", clean)
        clean = re.sub(r"[._]", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        if not clean:
            clean = file.stem

        # Generate ID (lowercase, no spaces)
        collection_id = re.sub(r"[^a-z0-9]", "_", clean.lower())

        # Find existing collection
        existing = None
        if existing_collections:
            for col in existing_collections:
                if col["id"] == collection_id:
                    existing = col
                    break

        if collection_id not in new_collections:
            new_collections[collection_id] = {
                "id": collection_id,
                "name": clean,
                "videos": [],
                "tags": existing["tags"] if existing else [],
                "time_slots": existing["time_slots"] if existing else ["prime"],
                "folder": str(folder)
            }

        # Add video
        video_entry = {
            "path": str(file).replace("\\", "/"),
            "year": None,  # ← Initialize to None
            "duration": None
        }

        # Try to extract year
        year_match = re.search(r"(\d{4})", file.parent.name + file.name)
        if year_match:
            year_val = int(year_match.group(1))
            if 1900 < year_val < 2030:
                video_entry["year"] = year_val  # ← Only set if valid

        # Get duration (this should work now)
        video_entry["duration"] = get_video_duration(file)

        new_collections[collection_id]["videos"].append(video_entry)

    return list(new_collections.values())

def load_collections(path="collections.json"):
    if Path(path).exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"collections": [], "last_scan": None}

def save_collections(data, path="collections.json"):
    data["last_scan"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_collections(profile_name="collections"):
    """Load collections from specified profile in user/collections directory.
    
    This function is used by simple_scheduler and daypart_scheduler_mixin.
    It looks for collection files in the following order:
    1. user/collections/{profile_name}.json
    2. user/collections/collections_{profile_name}.json
    3. akiratv/{profile_name}.json (fallback)
    4. akiratv/collections_{profile_name}.json (fallback)
    """
    import json
    try:
        # Get the script's directory and resolve paths
        script_dir = Path(__file__).resolve().parent
        base_dir = script_dir.parent
        collections_dir = base_dir / "user" / "collections"
        
        # Try to find the collection file in the collections directory
        profile_file = collections_dir / f"{profile_name}.json"
        
        # If not found, try with the "collections_" prefix
        if not profile_file.exists():
            profile_file = collections_dir / f"collections_{profile_name}.json"
        
        # If still not found, try in the script's directory as a fallback
        if not profile_file.exists():
            profile_file = script_dir / f"{profile_name}.json"
            if not profile_file.exists():
                profile_file = script_dir / f"collections_{profile_name}.json"
        
        # If the file exists, load it
        if profile_file.exists():
            with open(profile_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("collections", [])
        else:
            print(f"Collection file not found: {profile_file}")
            return []
    except Exception as e:
        print(f"Error loading collections: {e}")
        return []