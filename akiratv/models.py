"""
Pydantic models for AkiraTV API
Request and response models for FastAPI endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class PlayNowRequest(BaseModel):
    video_path: str = Field(..., description="Full path to video file")
    start_position: Optional[float] = Field(0, description="Start position in seconds")


class ConfigUpdateRequest(BaseModel):
    updates: Dict[str, Any] = Field(..., description="Configuration updates")


class ChannelUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    transcoding: Optional[str] = None  # "global" | "enabled" | "disabled"
    subtitles: Optional[str] = None    # "global" | "enabled" | "disabled"
    type: Optional[str] = None         # "linear" | "vod" | "dynamic" | "live"


class FastScheduleRequest(BaseModel):
    collections: Optional[List[str]] = None  # Collection names to load
    start_time: Optional[str] = "00:00"      # Start time HH:MM
    schedule_hours: Optional[int] = 24       # Hours of content to generate
    bumper_frequency: Optional[int] = 3      # Insert bumper every N videos
    trailer_probability: Optional[float] = 0.3  # Probability of showing trailers


class Response(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Any] = None
