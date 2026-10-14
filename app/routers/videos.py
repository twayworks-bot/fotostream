from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.video import Video
from app.schemas.video import VideoResponse, VideoListResponse
from app.services.stream_manager import create_video_range_response

router = APIRouter(prefix="/videos", tags=["Videos"])

def format_bytes(size: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def format_duration(seconds: float) -> str:
    """Format seconds into MM:SS string."""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

@router.get("", response_model=VideoListResponse)
def list_videos(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """List completed synthesized videos."""
    videos = db.query(Video).order_by(Video.created_at.desc()).offset(skip).limit(limit).all()
    total = db.query(Video).count()

    items = []
    for v in videos:
        vr = VideoResponse.model_validate(v)
        vr.file_size_formatted = format_bytes(v.file_size)
        vr.duration_formatted = format_duration(v.duration)
        vr.thumbnail_url = f"{settings.url_prefix}/api/v1/videos/{v.id}/thumbnail"
        items.append(vr)

    return VideoListResponse(videos=items, total=total)

@router.get("/{video_id}", response_model=VideoResponse)
def get_video_detail(video_id: str, db: Session = Depends(get_db)):
    """Retrieve details for a specific video."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    vr = VideoResponse.model_validate(video)
    vr.file_size_formatted = format_bytes(video.file_size)
    vr.duration_formatted = format_duration(video.duration)
    vr.thumbnail_url = f"{settings.url_prefix}/api/v1/videos/{video.id}/thumbnail"
    return vr

@router.get("/{video_id}/stream")
async def stream_video(
    video_id: str,
    range_header: Optional[str] = Header(None, alias="Range"),
    db: Session = Depends(get_db)
):
    """
    Video streaming endpoint supporting HTTP 206 Partial Content and
    enforcing maximum 10 concurrent streaming sessions limit.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    file_path = Path(video.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video file missing on disk")

    # Increment view count
    video.view_count += 1
    db.commit()

    return await create_video_range_response(
        file_path=file_path,
        range_header=range_header,
        media_type="video/mp4"
    )

@router.get("/{video_id}/thumbnail")
def get_video_thumbnail(video_id: str, db: Session = Depends(get_db)):
    """Retrieve video thumbnail image."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video or not video.thumbnail_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found")

    thumb_p = Path(video.thumbnail_path)
    if not thumb_p.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail file missing on disk")

    return FileResponse(thumb_p, media_type="image/jpeg")

@router.get("/{video_id}/download")
def download_video(video_id: str, db: Session = Depends(get_db)):
    """Direct video file download."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    file_p = Path(video.file_path)
    if not file_p.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video file missing on disk")

    return FileResponse(
        file_p,
        media_type="video/mp4",
        filename=f"{video.title.replace(' ', '_')}.mp4"
    )

@router.delete("/{video_id}")
def delete_video(video_id: str, db: Session = Depends(get_db)):
    """Delete a video and its stored files."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    # Delete physical files
    v_path = Path(video.file_path)
    if v_path.exists():
        try:
            v_path.unlink()
        except OSError:
            pass

    if video.thumbnail_path:
        t_path = Path(video.thumbnail_path)
        if t_path.exists():
            try:
                t_path.unlink()
            except OSError:
                pass

    db.delete(video)
    db.commit()
    return {"message": "Video deleted successfully"}
