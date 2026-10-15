from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    title: str
    filename: str
    file_size: int
    file_size_formatted: Optional[str] = None
    duration: float
    duration_formatted: Optional[str] = None
    resolution: str
    stream_url: str
    hls_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    view_count: int
    created_at: datetime

class VideoListResponse(BaseModel):
    videos: List[VideoResponse]
    total: int
