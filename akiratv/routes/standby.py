"""
Standby routes for AkiraTV API
Handles standby video creation
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
from collections import Counter
import json

from ..models import Response

router = APIRouter(prefix="/api/standby", tags=["Standby"])


def _create_standby():
    """Helper function to create standby videos"""
    from ..standby import create_standby_video
    
    # Create standby directory
    standby_dir = Path("assets/standby")
    standby_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all unique resolutions from inventory
    resolutions = []
    inventory_file = Path("user/video_inventory.json")
    
    if inventory_file.exists():
        with open(inventory_file, 'r', encoding='utf-8') as f:
            inventory_data = json.load(f)
        
        for item in inventory_data:
            video_tracks = item.get("video_tracks", [])
            if video_tracks and len(video_tracks) > 0:
                width = video_tracks[0].get("width")
                height = video_tracks[0].get("height")
                if width and height:
                    resolutions.append((width, height))
        
        if resolutions:
            resolution_counts = Counter(resolutions)
            resolutions = [
                (f"{width}x{height}", width, height)
                for (width, height), count in resolution_counts.most_common()
            ]
    
    # Fallback to common resolutions if inventory is empty
    if not resolutions:
        resolutions = [
            ("1920x1080", 1920, 1080),
            ("1280x720", 1280, 720),
            ("720x400", 720, 400)
        ]
    
    created_files = []
    codec = "h265"  # Default to h265
    
    # Create a standby video for each resolution
    for res_name, width, height in resolutions:
        output_path = standby_dir / f"standby_{res_name}.mp4"
        
        try:
            created_path = create_standby_video(
                duration=30,
                codec=codec,
                output_path=output_path,
                resolution=(width, height)
            )
            created_files.append(f"{res_name}: {created_path.name}")
        except Exception as e:
            print(f"Failed to create standby for {res_name}: {e}")
            continue
    
    # Also create a default standby (most common resolution)
    if resolutions:
        default_res = resolutions[0]  # Most common resolution
        default_path = standby_dir / "default_standby.mp4"
        try:
            create_standby_video(
                duration=30,
                codec=codec,
                output_path=default_path,
                resolution=(default_res[1], default_res[2])
            )
            created_files.append(f"default: {default_path.name}")
        except Exception as e:
            print(f"Failed to create default standby: {e}")
    
    return created_files


@router.post("/create", response_model=Response)
def create_standby_loop():
    """Create standby loop videos for all resolutions found in inventory"""
    try:
        # Run standby creation
        created_files = _create_standby()
        
        if created_files:
            files_list = "\n".join(created_files)
            return Response(
                success=True,
                message=f"Standby loops created successfully",
                data={
                    "created_files": created_files,
                    "directory": "assets/standby/",
                    "files_list": files_list
                }
            )
        else:
            raise HTTPException(status_code=500, detail="No standby files were created")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create standby loops: {str(e)}")
