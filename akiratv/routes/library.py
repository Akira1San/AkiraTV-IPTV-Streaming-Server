"""
Library management routes for AkiraTV API
Handles library statistics and scanning operations
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from ..core_api import get_api
from ..models import Response

router = APIRouter(prefix="/api/library", tags=["Library"])

def get_core_api():
    """Get CoreAPI instance"""
    return get_api()

@router.get("/stats")
def get_library_stats(api = Depends(get_core_api)):
    """Get library statistics"""
    stats = api.get_library_stats()
    if stats is None:
        raise HTTPException(status_code=503, detail="Engine not running")
    return stats.to_dict()

@router.post("/scan", response_model=Response)
def scan_library(path: Optional[str] = None, api = Depends(get_core_api)):
    """Trigger library scan"""
    result = api.scan_library(path)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])
