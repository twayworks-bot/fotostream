from pydantic import BaseModel

class WorkerStatus(BaseModel):
    active: int
    max: int
    queued: int

class StreamStatus(BaseModel):
    active: int
    max: int

class SystemStatusResponse(BaseModel):
    status: str = "healthy"
    workers: WorkerStatus
    streams: StreamStatus
    total_videos: int
    total_bgm_tracks: int
    ffmpeg_available: bool
