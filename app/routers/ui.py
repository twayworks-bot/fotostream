from pathlib import Path
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.bgm import BGMTrack

router = APIRouter(tags=["UI"])

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(request: Request, db: Session = Depends(get_db)):
    """Render main web dashboard for fotostream."""
    bgm_tracks = db.query(BGMTrack).order_by(BGMTrack.is_preset.desc(), BGMTrack.created_at.desc()).all()
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "prefix": settings.clean_prefix,
            "url_prefix": settings.url_prefix,
            "max_images": settings.MAX_IMAGES_COUNT,
            "max_video_size_mb": settings.MAX_VIDEO_SIZE_MB,
            "max_duration_sec": settings.MAX_VIDEO_DURATION_SEC,
            "max_workers": settings.MAX_CONCURRENT_JOBS,
            "max_streams": settings.MAX_CONCURRENT_STREAMS,
            "bgm_tracks": bgm_tracks
        }
    )

