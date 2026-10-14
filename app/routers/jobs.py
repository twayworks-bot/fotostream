import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.job import Job
from app.models.video import Video
from app.models.bgm import BGMTrack
from app.schemas.job import JobCreateResponse, JobResponse, JobListResponse
from app.services.task_queue import task_queue
from app.services.grid_calculator import calculate_best_grid

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_synthesis_job(
    images: List[UploadFile] = File(...),
    title: str = Form("My Photo Slideshow"),
    resolution: str = Form("1080p"),
    bgm_id: Optional[str] = Form(None),
    bgm_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Upload up to 49 images and optional BGM, then enqueue synthesis job with specified resolution.
    Resolution options: 720p, 1080p (standard default), 1440p, 1920p.
    """
    valid_resolutions = {"720p", "1080p", "1440p", "1920p"}
    res_normalized = resolution.lower().strip()
    if res_normalized not in valid_resolutions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid resolution '{resolution}'. Supported options: {list(valid_resolutions)}"
        )

    if len(images) < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least 1 image is required")
    if len(images) > settings.MAX_IMAGES_COUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {settings.MAX_IMAGES_COUNT} images can be uploaded simultaneously. Received {len(images)}"
        )

    valid_img_exts = {".jpg", ".jpeg", ".png", ".webp"}
    for img in images:
        ext = Path(img.filename or "").suffix.lower()
        if ext not in valid_img_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image format for '{img.filename}'. Supported formats: {list(valid_img_exts)}"
            )

    job_id = str(uuid.uuid4())
    job_upload_dir = settings.abs_upload_dir / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)

    # Save images in sequence
    for idx, img in enumerate(images):
        ext = Path(img.filename or "").suffix.lower() or ".jpg"
        save_filename = f"img_{idx:03d}_{Path(img.filename or 'photo').stem}{ext}"
        content = await img.read()
        with open(job_upload_dir / save_filename, "wb") as f:
            f.write(content)

    # Handle direct BGM upload if provided
    uploaded_bgm_filename: Optional[str] = None
    if bgm_file and bgm_file.filename:
        bgm_ext = Path(bgm_file.filename).suffix.lower()
        if bgm_ext in {".mp3", ".wav", ".aac", ".ogg", ".m4a"}:
            uploaded_bgm_filename = f"bgm_upload{bgm_ext}"
            bgm_content = await bgm_file.read()
            with open(job_upload_dir / uploaded_bgm_filename, "wb") as f:
                f.write(bgm_content)

    rows, cols = calculate_best_grid(len(images))

    job = Job(
        id=job_id,
        title=title.strip() or "My Photo Slideshow",
        status="QUEUED",
        progress=0,
        resolution=res_normalized,
        image_count=len(images),
        grid_rows=rows,
        grid_cols=cols,
        bgm_id=bgm_id if bgm_id and bgm_id.strip() else None,
        bgm_filename=uploaded_bgm_filename
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Enqueue to background worker
    await task_queue.enqueue_job(job_id)

    return JobCreateResponse(
        job_id=job.id,
        title=job.title,
        status=job.status,
        resolution=job.resolution,
        image_count=job.image_count,
        message=f"Job registered in queue. Resolution: {job.resolution}, Grid: {rows}x{cols}."
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get the current progress and details of a synthesis job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    resp = JobResponse.model_validate(job)
    if job.video:
        resp.video_id = job.video.id
        resp.stream_url = job.video.stream_url
    return resp

@router.get("", response_model=JobListResponse)
def list_jobs(limit: int = 50, db: Session = Depends(get_db)):
    """List recent synthesis jobs and queue metrics."""
    jobs = db.query(Job).order_by(Job.created_at.desc()).limit(limit).all()
    queued_count = db.query(Job).filter(Job.status == "QUEUED").count()
    processing_count = db.query(Job).filter(Job.status == "PROCESSING").count()

    job_responses = []
    for j in jobs:
        jr = JobResponse.model_validate(j)
        if j.video:
            jr.video_id = j.video.id
            jr.stream_url = j.video.stream_url
        job_responses.append(jr)

    return JobListResponse(
        jobs=job_responses,
        queued_count=queued_count,
        processing_count=processing_count,
        total=len(job_responses)
    )

@router.delete("/{job_id}")
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """Cancel a pending or queued job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status in ["QUEUED", "PROCESSING"]:
        job.status = "CANCELED"
        job.error_message = "Canceled by user"
        db.commit()
        return {"message": "Job canceled"}

    return {"message": f"Job already in {job.status} status"}
