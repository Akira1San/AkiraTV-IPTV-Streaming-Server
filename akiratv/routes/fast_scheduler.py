"""
Fast Scheduler routes for AkiraTV API
Handles fast schedule creation, management, and checkpoint operations
"""

import json
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, HTTPException

from ..models import Response, FastScheduleRequest
from ..fast_scheduler import FastScheduler

router = APIRouter(prefix="/api/fast-schedule", tags=["Fast Scheduler"])


# Global fast schedulers cache
fast_schedulers: Dict[str, FastScheduler] = {}


def get_fast_scheduler(channel_name: str) -> FastScheduler:
    """Get or create a FastScheduler instance for a channel"""
    if channel_name not in fast_schedulers:
        fast_schedulers[channel_name] = FastScheduler(channel_name)
    return fast_schedulers[channel_name]


@router.post("/{channel}/load-collections", response_model=Response)
def load_fast_schedule_collections(channel: str, request: FastScheduleRequest):
    """Load collections for fast scheduling"""
    try:
        scheduler = get_fast_scheduler(channel)
        result = scheduler.load_collections(request.collections)
        
        if result["success"]:
            return Response(
                success=True, 
                message=result["message"],
                data={"videos_loaded": result["videos_loaded"]}
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load collections: {str(e)}")


@router.post("/{channel}/generate", response_model=Response)
def generate_fast_schedule(channel: str, request: FastScheduleRequest):
    """Generate a fast schedule for a channel"""
    try:
        scheduler = get_fast_scheduler(channel)
        
        # Update settings if provided
        if request.schedule_hours:
            scheduler.schedule_length_hours = request.schedule_hours
        if request.bumper_frequency:
            scheduler.bumper_frequency = request.bumper_frequency
        if request.trailer_probability is not None:
            scheduler.trailer_probability = request.trailer_probability
        
        # Generate schedule
        result = scheduler.generate_schedule(request.start_time or "00:00")
        
        if result["success"]:
            # Auto-save checkpoint
            scheduler.save_checkpoint()
            
            return Response(
                success=True,
                message=result["message"],
                data={
                    "entries": result["entries"],
                    "videos": result.get("videos", 0),
                    "bumpers": result.get("bumpers", 0)
                }
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate schedule: {str(e)}")


@router.get("/{channel}/info")
def get_fast_schedule_info(channel: str):
    """Get fast schedule information for a channel"""
    try:
        scheduler = get_fast_scheduler(channel)
        info = scheduler.get_schedule_info()
        return {"success": True, "data": info}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get schedule info: {str(e)}")


@router.get("/{channel}/current")
def get_current_fast_schedule_entry(channel: str):
    """Get the current schedule entry that should be playing"""
    try:
        scheduler = get_fast_scheduler(channel)
        current_entry = scheduler.get_current_entry()
        resume_position = scheduler.get_resume_position(current_entry) if current_entry else 0.0
        
        return {
            "success": True,
            "data": {
                "current_entry": current_entry.__dict__ if current_entry else None,
                "resume_position": resume_position
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get current entry: {str(e)}")


@router.get("/{channel}/upcoming")
def get_upcoming_fast_schedule_entries(channel: str, count: int = 5):
    """Get upcoming schedule entries"""
    try:
        scheduler = get_fast_scheduler(channel)
        upcoming = scheduler.get_upcoming_entries(count)
        return {"success": True, "data": {"upcoming": upcoming}}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get upcoming entries: {str(e)}")


@router.post("/{channel}/save-checkpoint", response_model=Response)
def save_fast_schedule_checkpoint(channel: str):
    """Save fast schedule checkpoint"""
    try:
        scheduler = get_fast_scheduler(channel)
        result = scheduler.save_checkpoint()
        
        if result["success"]:
            return Response(success=True, message=result["message"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save checkpoint: {str(e)}")


@router.post("/{channel}/load-checkpoint", response_model=Response)
def load_fast_schedule_checkpoint(channel: str):
    """Load fast schedule checkpoint"""
    try:
        scheduler = get_fast_scheduler(channel)
        result = scheduler.load_checkpoint()
        
        if result["success"]:
            return Response(
                success=True, 
                message=result["message"],
                data={
                    "entries": result.get("entries", 0),
                    "saved_at": result.get("saved_at")
                }
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load checkpoint: {str(e)}")


@router.get("/collections")
def get_available_collections():
    """Get list of available collection files"""
    try:
        collections_dir = Path("user/collections")
        if not collections_dir.exists():
            return {"success": True, "data": {"collections": []}}
        
        collections = []
        for collection_file in collections_dir.glob("collections_*.json"):
            collection_name = collection_file.stem.replace("collections_", "")
            try:
                with open(collection_file, 'r', encoding='utf-8') as f:
                    collection_data = json.load(f)
                video_count = len(collection_data) if isinstance(collection_data, dict) else 0
                
                collections.append({
                    "name": collection_name,
                    "file": collection_file.name,
                    "video_count": video_count
                })
            except Exception as e:
                collections.append({
                    "name": collection_name,
                    "file": collection_file.name,
                    "video_count": 0,
                    "error": str(e)
                })
        
        return {"success": True, "data": {"collections": collections}}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get collections: {str(e)}")


@router.get("/{channel}/status")
def get_fast_schedule_status(channel: str):
    """Check if a channel is using Fast Scheduler and get its status"""
    try:
        from ..scheduler import get_current_fast_schedule_entry
        
        # Check if channel has a fast schedule
        result = get_current_fast_schedule_entry(channel)
        
        if result["success"]:
            return {
                "success": True,
                "data": {
                    "has_fast_schedule": True,
                    "current_entry": result["entry"],
                    "resume_position": result["resume_position"],
                    "message": result["message"]
                }
            }
        else:
            return {
                "success": True,
                "data": {
                    "has_fast_schedule": False,
                    "error": result["error"]
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get fast schedule status: {str(e)}")
