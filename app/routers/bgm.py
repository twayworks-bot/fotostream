from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.services.bgm_manager import BGMManager
from app.schemas.bgm import BGMResponse, BGMListResponse

router = APIRouter(prefix="/bgm", tags=["BGM"])

@router.get("", response_model=BGMListResponse)
def list_bgm_tracks(mood: Optional[str] = None, db: Session = Depends(get_db)):
    """List all available BGM tracks with optional mood filter."""
    tracks = BGMManager.list_tracks(db, mood=mood)
    items = []
    for t in tracks:
        resp = BGMResponse.model_validate(t)
        resp.stream_url = f"{settings.url_prefix}/api/v1/bgm/{t.id}/stream"
        items.append(resp)
    return BGMListResponse(tracks=items, total=len(items))

@router.post("", response_model=BGMResponse, status_code=status.HTTP_201_CREATED)
async def register_bgm_track(
    file: UploadFile = File(...),
    title: str = Form(""),
    artist: str = Form("Unknown"),
    mood: str = Form("General"),
    source: str = Form("Pixabay Music"),
    license_info: str = Form("Free for Commercial Use"),
    db: Session = Depends(get_db)
):
    """Admin endpoint to register a new BGM track (e.g., downloaded from Pixabay Music)."""
    valid_exts = {".mp3", ".wav", ".aac", ".ogg", ".m4a"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in valid_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format: {ext}. Supported formats: {list(valid_exts)}"
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio file uploaded")

    track = BGMManager.register_track(
        db=db,
        title=title or Path(file.filename or "track").stem,
        artist=artist,
        mood=mood,
        source=source,
        license_info=license_info,
        file_bytes=content,
        original_filename=file.filename or "bgm.mp3"
    )

    resp = BGMResponse.model_validate(track)
    resp.stream_url = f"{settings.url_prefix}/api/v1/bgm/{track.id}/stream"
    return resp

@router.get("/{bgm_id}/stream")
def stream_bgm_audio(
    bgm_id: str,
    range_header: Optional[str] = Header(None, alias="Range"),
    db: Session = Depends(get_db)
):
    """Audio streaming endpoint for BGM preview."""
    track = BGMManager.get_track(db, bgm_id)
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BGM track not found")

    file_p = Path(track.file_path)
    if not file_p.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file missing on disk")

    file_size = file_p.stat().st_size

    def iter_audio():
        with open(file_p, "rb") as f:
            while chunk := f.read(64 * 1024):
                yield chunk

    media_type = "audio/mpeg" if file_p.suffix.lower() == ".mp3" else "audio/octet-stream"
    headers = {
        "Content-Length": str(file_size),
        "Accept-Ranges": "bytes",
        "Content-Type": media_type
    }
    return StreamingResponse(iter_audio(), media_type=media_type, headers=headers)

@router.delete("/{bgm_id}")
def delete_bgm_track(bgm_id: str, db: Session = Depends(get_db)):
    """Delete a BGM track."""
    success = BGMManager.delete_track(db, bgm_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BGM track not found")
    return {"message": "BGM track deleted successfully"}
