"""
VOD (Video on Demand) routes for AkiraTV API
Handles video library and video details endpoints
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter(prefix="/api/vod", tags=["VOD"])

@router.get("/library")
def get_vod_library():
    """Get video library from all collections"""
    try:
        collections_dir = Path("user/collections")
        videos = []
        collections = []
        
        if not collections_dir.exists():
            return {"videos": [], "collections": []}
        
        # Load all collection files
        for collection_file in collections_dir.glob("collections_*.json"):
            try:
                with open(collection_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                collection_name = collection_file.stem.replace('collections_', '')
                collections.append(collection_name)
                
                for item in data.get('collections', []):
                    # Extract video info
                    for video_data in item.get('videos', []):
                        video = {
                            'id': item['id'],
                            'name': item['name'],
                            'description': item.get('description', ''),
                            'cover': item.get('cover'),
                            'genre': item.get('genre', []),
                            'rating': item.get('rating', 'NR'),
                            'year': item.get('year'),
                            'duration': video_data.get('duration'),
                            'path': video_data['path'],
                            'collection': collection_name
                        }
                        videos.append(video)
                        
            except Exception as e:
                print(f"Error loading collection file {collection_file}: {e}")
                continue
        
        return {
            "success": True,
            "videos": videos,
            "collections": collections
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load video library: {str(e)}")

@router.get("/video/{video_id}")
def get_video_details(video_id: str):
    """Get detailed information about a specific video"""
    try:
        # This would be implemented to get specific video details
        # For now, return basic info
        return {"success": True, "video": {}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get video details: {str(e)}")
