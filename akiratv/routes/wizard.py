"""
Wizard routes for AkiraTV API
Contains endpoints for collection wizard functionality
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import json
from pathlib import Path
from datetime import datetime

from ..models import Response

router = APIRouter(prefix="/api/wizard", tags=["Wizard"])


def get_video_duration(video_path: str) -> float:
    """Get video duration using FFprobe"""
    try:
        import subprocess
        import json
        
        # Use ffprobe to get video duration
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration = float(data.get('format', {}).get('duration', 0))
            print(f"   📹 Duration for {video_path}: {duration:.2f}s")
            return duration
        else:
            print(f"   ⚠️ FFprobe failed for {video_path}: {result.stderr}")
            return 0
            
    except Exception as e:
        print(f"   ⚠️ Could not get duration for {video_path}: {e}")
        return 0


def get_core_api():
    """Get CoreAPI instance only when needed"""
    from ..core_api import get_api
    api = None
    if api is None:
        api = get_api()
    return api


@router.post("/log", response_model=Response)
def log_wizard_event(request: dict):
    """Log wizard events to file"""
    try:
        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Create wizard log file
        log_file = logs_dir / "wizard.log"
        
        # Format log entry
        timestamp = request.get("timestamp", datetime.now().isoformat())
        level = request.get("level", "info").upper()
        message = request.get("message", "")
        data = request.get("data", {})
        
        log_entry = f"[{timestamp}] [{level}] {message}"
        if data:
            log_entry += f" | Data: {json.dumps(data, ensure_ascii=False)}"
        log_entry += "\n"
        
        # Append to log file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        return Response(success=True, message="Log entry written")
        
    except Exception as e:
        # Don't fail the wizard if logging fails
        print(f"Failed to write wizard log: {e}")
        return Response(success=False, error=str(e))


@router.post("/scan-folder", response_model=Response)
def scan_folder_for_videos(request: dict):
    """Scan folder for video files"""
    try:
        folder_path = request.get("folder_path")
        if not folder_path:
            raise HTTPException(status_code=400, detail="folder_path is required")
        
        folder = Path(folder_path)
        if not folder.exists():
            raise HTTPException(status_code=400, detail=f"Folder does not exist: {folder_path}")
        
        if not folder.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {folder_path}")
        
        # Video file extensions
        video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.m4v', '.wmv', '.flv', '.webm', '.mpg', '.mpeg', '.ts', '.m2ts'}
        
        videos = []
        total_size = 0
        
        print(f"[SEARCH] Scanning folder: {folder_path}")
        
        # Scan for video files
        for file_path in folder.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                try:
                    file_size = file_path.stat().st_size
                    videos.append({
                        'name': file_path.name,
                        'path': str(file_path),
                        'size': file_size,
                        'format': file_path.suffix[1:].upper(),
                        'relative_path': str(file_path.relative_to(folder))
                    })
                    total_size += file_size
                    print(f"[FOLDER] Found video: {file_path.name}")
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    continue
        
        # Sort by name
        videos.sort(key=lambda x: x['name'].lower())
        
        print(f"[OK] Scan complete: {len(videos)} videos found, {total_size} bytes total")
        
        return Response(
            success=True,
            message=f"Found {len(videos)} video files",
            data={
                "videos": videos,
                "total_size": total_size,
                "folder_path": str(folder),
                "video_count": len(videos)
            }
        )
        
    except Exception as e:
        print(f"[ERROR] Folder scan error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to scan folder: {str(e)}")


@router.post("/collection/check", response_model=Response)
def check_collection_exists(request: dict):
    """Check if a collection already exists"""
    try:
        collection_name = request.get("collection_name", "").strip()
        if not collection_name:
            return Response(success=True, data={"exists": False})
        
        # Convert collection name to potential channel names and check for existing files
        potential_channel_name = collection_name.lower().replace(' ', '_').replace('-', '_')
        potential_channel_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in potential_channel_name)
        potential_channel_name = '_'.join(potential_channel_name.split('_'))  # Clean up multiple underscores
        
        collections_dir = Path("user/collections")
        
        # Check for various possible collection file names
        possible_files = [
            collections_dir / f"collections_{potential_channel_name}.json",
            collections_dir / f"collections_{collection_name.lower().replace(' ', '_')}.json",
            collections_dir / f"collections_{collection_name.lower()}.json"
        ]
        
        exists = any(file.exists() for file in possible_files)
        
        return Response(
            success=True,
            data={
                "exists": exists,
                "collection_name": collection_name,
                "potential_files": [str(f) for f in possible_files if f.exists()]
            }
        )
        
    except Exception as e:
        print(f"[ERROR] Collection check error: {str(e)}")
        return Response(success=True, data={"exists": False})  # Fail gracefully


@router.post("/collection/create", response_model=Response)
def create_collection_wizard(request: dict):
    """Create collection file from wizard (collections only, no channel creation)"""
    try:
        # Extract data from request
        collection_name = request.get("collection_name")
        channel_name = request.get("channel_name")
        folder_path = request.get("folder_path")
        collection_data = request.get("collection_data", {})
        overwrite_existing = request.get("overwrite_existing", False)
        
        print(f"[WIZARD] Creating collection via wizard:")
        print(f"   Collection: {collection_name}")
        print(f"   Channel: {channel_name}")
        print(f"   Folder: {folder_path}")
        print(f"   Overwrite: {overwrite_existing}")
        
        # Validate inputs
        if not collection_name or not collection_name.strip():
            raise HTTPException(status_code=400, detail="Collection name is required")
        
        if not channel_name or not channel_name.strip():
            raise HTTPException(status_code=400, detail="Channel name is required")
        
        # Verify channel exists
        api = get_core_api()
        existing_channels = api.get_channels()
        channel_names = [ch.name for ch in existing_channels]
        
        if channel_name not in channel_names:
            raise HTTPException(
                status_code=400, 
                detail=f"Channel '{channel_name}' does not exist. Available channels: {', '.join(channel_names) if channel_names else 'None'}. Please create the channel first using 'Add Channel'."
            )
        
        print(f"[OK] Channel '{channel_name}' exists and is available.")
        
        # Create collections directory
        collections_dir = Path("user/collections")
        collections_dir.mkdir(parents=True, exist_ok=True)
        
        # Create collection file
        collection_file = collections_dir / f"collections_{channel_name}.json"
        
        # Check if collection file already exists
        if collection_file.exists() and not overwrite_existing:
            raise HTTPException(
                status_code=409, 
                detail=f"Collection file already exists: {collection_file.name}. Use overwrite_existing=true to replace it."
            )
        
        # Prepare collection data in the correct AkiraTV format
        collections = []
        
        for video in collection_data.get("videos", []):
            # Generate collection ID from video name
            video_name = video.get("name", "")
            collection_id = video_name.lower()
            # Clean up the ID - remove file extension and special characters
            collection_id = collection_id.rsplit('.', 1)[0]  # Remove extension
            collection_id = ''.join(c if c.isalnum() else '_' for c in collection_id)  # Replace special chars
            collection_id = '_'.join(collection_id.split())  # Replace spaces with underscores
            
            # Generate display name from video name
            display_name = video_name.rsplit('.', 1)[0]  # Remove extension
            # Clean up display name - remove common prefixes and improve formatting
            display_name = display_name.replace('encoded_', '').replace('_', ' ')
            display_name = ' '.join(word.capitalize() for word in display_name.split())
            
            # Convert Windows path to forward slashes for AkiraTV
            video_path = video.get("path", "").replace("\\", "/")
            
            # Try to get video duration using FFprobe
            duration = get_video_duration(video_path)
            
            collection_entry = {
                "id": collection_id,
                "name": display_name,
                "cover": None,
                "description": "",
                "genre": [],
                "year": 2026,  # Could be extracted from filename or metadata
                "videos": [
                    {
                        "path": video_path,
                        "duration": duration
                    }
                ]
            }
            collections.append(collection_entry)
        
        # Create the proper AkiraTV collections format
        collection_content = {
            "collections": collections
        }
        
        print(f"[FOLDER] Writing collection file: {collection_file}")
        print(f"   Collections count: {len(collections)}")
        print(f"   Sample collection: {collections[0] if collections else 'None'}")
        
        # Write collection file
        with open(collection_file, 'w', encoding='utf-8') as f:
            json.dump(collection_content, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Collection file created successfully")
        
        return Response(
            success=True,
            message=f"Collection '{collection_name}' created successfully for channel '{channel_name}'",
            data={
                "collection_file": str(collection_file),
                "channel_name": channel_name,
                "collections_count": len(collections),
                "video_count": sum(len(c["videos"]) for c in collections),
                "overwrite_existing": overwrite_existing
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"[ERROR] Collection creation error: {str(e)}")
        print(f"   Request data: {request}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create collection: {str(e)}")


@router.post("/schedule/create", response_model=Response)
def create_schedule_wizard(
    channel_name: str,
    schedule_type: str,
    schedule_data: dict
):
    """Create schedule from wizard"""
    try:
        # Validate inputs
        if not channel_name.strip():
            raise HTTPException(status_code=400, detail="Channel name is required")
        
        if schedule_type not in ['weekly', 'daily']:
            raise HTTPException(status_code=400, detail="Invalid schedule type")
        
        # Check if channel exists
        api = get_core_api()
        channel = api.get_channel(channel_name)
        if not channel:
            raise HTTPException(status_code=404, detail=f"Channel '{channel_name}' not found")
        
        # Create schedules directory
        schedules_dir = Path("user/schedules")
        schedules_dir.mkdir(parents=True, exist_ok=True)
        
        # Create schedule file
        schedule_file = schedules_dir / f"schedule_{channel_name}.json"
        
        # Prepare schedule content
        schedule_content = {
            "channel": channel_name,
            "type": schedule_type,
            "created": schedule_data.get("created", ""),
            "weekly": schedule_data.get("weekly", {}),
            "metadata": {
                "total_slots": sum(len(day_schedule) for day_schedule in schedule_data.get("weekly", {}).values()),
                "days_with_schedule": len(schedule_data.get("weekly", {})),
                "created_by": "wizard"
            }
        }
        
        # Write schedule file
        with open(schedule_file, 'w', encoding='utf-8') as f:
            json.dump(schedule_content, f, indent=2, ensure_ascii=False)
        
        # Reload schedule for the channel
        reload_result = api.reload_schedule(channel_name)
        if not reload_result["success"]:
            print(f"Warning: Failed to reload schedule for {channel_name}: {reload_result.get('error')}")
        
        return Response(
            success=True,
            message=f"Schedule created successfully for channel '{channel_name}'",
            data={
                "schedule_file": str(schedule_file),
                "channel_name": channel_name,
                "schedule_type": schedule_type,
                "total_slots": schedule_content["metadata"]["total_slots"],
                "days_with_schedule": schedule_content["metadata"]["days_with_schedule"]
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")
