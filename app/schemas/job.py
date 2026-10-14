from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class JobBase(BaseModel):
    title: str = "My Photo Slideshow"

class JobCreateResponse(BaseModel):
    job_id: str
    title: str
    status: str
    resolution: str = "1080p"
    image_count: int
    message: str

class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    status: str
    progress: int
    resolution: str = "1080p"
    image_count: int
    grid_rows: Optional[int] = None
    grid_cols: Optional[int] = None
    bgm_id: Optional[str] = None
    bgm_filename: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    video_id: Optional[str] = None
    stream_url: Optional[str] = None

class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    queued_count: int
    processing_count: int
    total: int
