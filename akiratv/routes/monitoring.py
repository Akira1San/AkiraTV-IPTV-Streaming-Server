"""
Monitoring and statistics routes for AkiraTV API
Handles live statistics, viewer tracking, and log access
"""
from fastapi import APIRouter, HTTPException, Depends

from ..core_api import get_api
from ..viewer_tracker import viewer_tracker

router = APIRouter(prefix="/api", tags=["Monitoring"])

def get_core_api():
    """Get CoreAPI instance"""
    return get_api()

@router.get("/stats")
def get_stats(api = Depends(get_core_api)):
    """Get live statistics"""
    return api.stats

@router.get("/viewers")
def get_viewers(api = Depends(get_core_api)):
    """Get active viewer count"""
    return {"viewers": api.get_viewers()}

@router.get("/viewers/detail")
def get_viewer_details():
    """Get detailed viewer information with IPs and channels."""
    viewer_tracker.cleanup_stale()  # Clean up before returning
    return {
        "total": viewer_tracker.total_viewers,
        "viewers": viewer_tracker.get_viewer_list(),
        "per_channel": viewer_tracker.get_counts()
    }

@router.get("/viewers/channel/{channel_name}")
def get_channel_viewers(channel_name: str):
    """Get viewers for a specific channel."""
    viewer_tracker.cleanup_stale()
    viewers = viewer_tracker.get_channel_viewers(channel_name)
    return {
        "channel": channel_name,
        "viewers": viewers,
        "count": len(viewers)
    }

@router.get("/logs")
def get_logs(limit: int = 100, api = Depends(get_core_api)):
    """Get recent log entries"""
    logs = api.get_logs(limit)
    return {"logs": logs, "count": len(logs)}
