"""
Configuration routes for AkiraTV API
Handles configuration management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from ..models import Response, ConfigUpdateRequest
from ..core_api import get_api
import os

router = APIRouter(prefix="/api/config", tags=["Configuration"])

def get_core_api():
    """Get CoreAPI instance"""
    return get_api()

@router.get("")
def get_config(api = Depends(get_core_api)):
    """Get full configuration"""
    return api.get_config()

@router.patch("", response_model=Response)
def update_config(request: ConfigUpdateRequest, api = Depends(get_core_api)):
    """Update configuration"""
    result = api.update_config(request.updates)
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])

@router.post("/save", response_model=Response)
def save_config(api = Depends(get_core_api)):
    """Save configuration to disk"""
    result = api.save_config()
    if result["success"]:
        return Response(success=True, message=result["message"])
    else:
        raise HTTPException(status_code=400, detail=result["error"])

@router.get("/defaults")
def get_default_config():
    """Get default configuration"""
    from ..config import Config
    return Config.default_config()

@router.get("/file")
def open_config_file():
    """Get config file path for opening"""
    config_path = os.path.abspath("config.json")
    return {
        "path": config_path,
        "exists": os.path.exists(config_path),
        "message": f"Config file location: {config_path}"
    }
