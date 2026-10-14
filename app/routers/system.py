from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.video import Video
from app.models.bgm import BGMTrack
from app.services.task_queue import task_queue
from app.services.stream_manager import stream_registry
from app.schemas.system import SystemStatusResponse, WorkerStatus, StreamStatus

router = APIRouter(prefix="/system", tags=["System"])

@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(db: Session = Depends(get_db)):
    """Check system health, active encoding slots, and streaming sessions."""
    total_videos = db.query(Video).count()
    total_bgm = db.query(BGMTrack).count()
    ffmpeg_ok = settings.abs_ffmpeg_path.exists()

    return SystemStatusResponse(
        status="healthy",
        workers=WorkerStatus(
            active=task_queue.active_workers,
            max=task_queue.max_concurrent,
            queued=task_queue.queue.qsize()
        ),
        streams=StreamStatus(
            active=stream_registry.current_streams,
            max=stream_registry.max_streams
        ),
        total_videos=total_videos,
        total_bgm_tracks=total_bgm,
        ffmpeg_available=ffmpeg_ok
    )
