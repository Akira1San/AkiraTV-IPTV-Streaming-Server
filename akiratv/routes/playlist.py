"""
Playlist routes for AkiraTV API
Handles playlist creation, video retrieval, and playback
"""

from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path

from ..models import Response
from ..core_api import get_api

router = APIRouter(prefix="/api/playlist", tags=["Playlist"])


def get_core_api():
    """Get CoreAPI instance"""
    return get_api()


@router.post("/create", response_model=Response)
def create_playlist(folder_path: str):
    """Create playlist from video folder"""
    try:
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            raise HTTPException(status_code=400, detail="Invalid folder path")
        
        # Create playlists directory
        playlists_dir = Path("playlists")
        playlists_dir.mkdir(exist_ok=True)
        
        # Find all video files
        video_extensions = [".mp4", ".mkv", ".avi", ".mov", ".m4v", ".wmv", ".flv"]
        video_files = []
        for ext in video_extensions:
            video_files.extend(folder.rglob(f"*{ext}"))
        
        video_files = sorted(video_files)
        
        if not video_files:
            raise HTTPException(status_code=400, detail="No video files found in folder")
        
        # Generate live.m3u playlist
        live_playlist_path = playlists_dir / "live.m3u"
        with open(live_playlist_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for video in video_files:
                f.write(f"#EXTINF:-1,{video.stem}\n{video}\n")
        
        return Response(
            success=True,
            message=f"Playlist created with {len(video_files)} videos",
            data={
                "playlist_path": str(live_playlist_path),
                "video_count": len(video_files),
                "videos": [{"name": v.stem, "path": str(v)} for v in video_files]
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create playlist: {str(e)}")


@router.get("/videos")
def get_playlist_videos():
    """Get videos from current playlist"""
    try:
        live_playlist_path = Path("playlists") / "live.m3u"
        if not live_playlist_path.exists():
            return {"videos": [], "message": "No playlist found"}
        
        videos = []
        with open(live_playlist_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            current_title = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF:"):
                    # Extract title from #EXTINF:-1,Title
                    current_title = line.split(",", 1)[1] if "," in line else "Unknown"
                elif line and not line.startswith("#") and current_title:
                    videos.append({
                        "name": current_title,
                        "path": line
                    })
                    current_title = None
        
        return {"videos": videos, "count": len(videos)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read playlist: {str(e)}")


@router.post("/play-selected", response_model=Response)
def play_selected_video(channel: str, video_name: str):
    """Play selected video from playlist"""
    try:
        # Find video path in playlist
        live_playlist_path = Path("playlists") / "live.m3u"
        if not live_playlist_path.exists():
            raise HTTPException(status_code=404, detail="No playlist found")
        
        video_path = None
        with open(live_playlist_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                if line.strip().startswith("#EXTINF:") and video_name in line:
                    # Next line should be the path
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and not next_line.startswith("#"):
                            video_path = next_line
                            break
        
        if not video_path:
            raise HTTPException(status_code=404, detail=f"Video '{video_name}' not found in playlist")
        
        if not Path(video_path).exists():
            raise HTTPException(status_code=404, detail=f"Video file not found: {video_path}")
        
        # Play the video
        api = get_core_api()
        result = api.play_now(channel, video_path)
        
        if result["success"]:
            return Response(success=True, message=f"Now playing: {Path(video_path).name}")
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to play video: {str(e)}")
