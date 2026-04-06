"""
Lifecycle routes for AkiraTV API
Handles engine start, stop, restart, and status endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from ..models import Response
from ..core_api import get_api

router = APIRouter(prefix="/api", tags=["Lifecycle"])

# Dependency for Core API access
def get_core_api():
    """Get CoreAPI instance"""
    return get_api()

@router.post("/start", response_model=Response)
def start_engine(api = Depends(get_core_api)):
    """Start AkiraTV engine"""
    result = api.start()
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=500, detail=result["error"])

@router.post("/stop", response_model=Response)
def stop_engine(api = Depends(get_core_api)):
    """Stop AkiraTV engine"""
    result = api.stop()
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=500, detail=result["error"])

@router.post("/restart", response_model=Response)
def restart_engine(api = Depends(get_core_api)):
    """Restart AkiraTV engine"""
    result = api.restart()
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=500, detail=result["error"])

@router.get("/status")
def get_status(api = Depends(get_core_api)):
    """Get engine status"""
    return {
        "is_running": api.is_running,
        "uptime": api.uptime,
        "stats": api.stats
    }
